from __future__ import annotations

import curses
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from abyss_echoes.engine.battle import BattleEngine
from abyss_echoes.engine.content_loader import load_heroes, load_items
from abyss_echoes.i18n import (
    affix_name,
    aspect_description,
    aspect_name,
    encounter_name,
    encounter_type_name,
    hero_name,
    localize_loot_name,
    party_status_name,
    position_name,
    rarity_name,
    role_name,
    skill_name,
    specialization_name,
    slot_name,
    threat_tag_name,
    verdict_name,
    winner_name,
)
from abyss_echoes.engine.models import BattleLogEntry, LootItem
from abyss_echoes.loot import (
    AffixProfile,
    BuildContext,
    EquippedItemReference,
    ItemStaticProfile,
    LegendaryEffectProfile,
    WorkshopState,
    build_drop_presentation,
    evaluate_drop,
)
from abyss_echoes.loot import config as loot_config
from abyss_echoes.player.profile import DEFAULT_SAVE_PATH, PlayerProfile, create_default_profile

MAX_WORKSHOP_STRENGTHEN_LEVEL = 8

HEROES = load_heroes()
ITEMS = load_items()
MENU_COLUMNS = 5
BATTLE_LOG_DELAY_SECONDS = max(0.0, float(os.getenv("ABYSS_BATTLE_LOG_DELAY", "0.5")))
STAT_LABELS = {
    "max_hp": "生命",
    "atk": "攻击",
    "mag": "法强",
    "armor": "护甲",
    "resist": "抗性",
    "speed": "速度",
    "crit_rate": "暴击率",
    "crit_damage": "暴击伤害",
    "heal_bonus": "治疗加成",
    "energy_gain_bonus": "能量获取",
    "damage_bonus": "伤害加成",
    "shield_bonus": "护盾加成",
    "damage_vs_debuffed_bonus": "易伤增伤",
    "damage_vs_debuffed": "易伤增伤",
    "hp_pct": "生命百分比",
    "atk_pct": "攻击百分比",
    "mag_pct": "法强百分比",
    "armor_flat": "护甲",
    "resist_flat": "抗性",
    "speed_flat": "速度",
}
TAG_LABELS = {
    "TURN": "回合",
    "ACT": "技能",
    "DMG": "伤害",
    "DOT": "持续",
    "HEAL": "治疗",
    "SHLD": "护盾",
    "NRG": "能量",
    "ENG": "消耗",
    "SPD": "速度",
    "CTRL": "控制",
    "KILL": "击倒",
    "ASP": "特效",
    "BUFF": "状态",
    "FAT": "疲劳",
    "SYS": "系统",
    "INFO": "信息",
}


@dataclass(frozen=True, slots=True)
class MenuAction:
    action_id: str
    label: str


MENU_ACTIONS = [
    MenuAction("battle", "开始战斗"),
    MenuAction("stage", "关卡情报"),
    MenuAction("party", "队伍详情"),
    MenuAction("codex", "游戏百科"),
    MenuAction("heroes", "全部英雄"),
    MenuAction("upgrades", "升级建议"),
    MenuAction("auto_equip", "自动装备"),
    MenuAction("inventory", "装备管理"),
    MenuAction("next_stage", "下一关"),
    MenuAction("save", "保存存档"),
    MenuAction("reload", "重新读取"),
    MenuAction("reset_save", "重置存档"),
    MenuAction("quit", "退出游戏"),
]

BATTLE_STATUS_HINT = "战斗中：S 跳过剩余过程并直接结算，Q 中断战斗并保存退出。"
BATTLE_ABORT_HINT = "中断后本关按未通过处理，不发放本场奖励。"
ALLY_NAME_COLOR = 9
ENEMY_NAME_COLOR = 10
INFO_NAME_COLOR = 11
ENCYCLOPEDIA_ROOT_OPTIONS = ["角色图鉴", "装备图鉴"]
BACKSPACE_KEYS = (curses.KEY_BACKSPACE, 127, 8)


def render_threat_summary(analysis: dict[str, object]) -> str:
    raw_tags = analysis.get("threat_tags")
    if isinstance(raw_tags, list):
        threat_tags = [threat_tag_name(str(tag)) for tag in raw_tags]
    else:
        threat_tags = []
    raw_mechanics = analysis.get("enemy_mechanics")
    if isinstance(raw_mechanics, list):
        enemy_mechanics = [str(line) for line in raw_mechanics if isinstance(line, str)]
    else:
        enemy_mechanics = []
    lines = ["威胁概览：", f"- 标签：{', '.join(threat_tags) if threat_tags else '无'}"]
    lines.extend(f"- {line}" for line in enemy_mechanics)
    return "\n".join(lines)


def stat_label(stat_name: str) -> str:
    return STAT_LABELS.get(stat_name, affix_name(stat_name))


def role_summary(role: str) -> str:
    summaries = {
        "tank": "前排承伤保护",
        "melee_dps": "近战爆发输出",
        "ranged_dps": "后排持续输出",
        "mage": "法术范围压制",
        "support": "治疗与节奏支援",
    }
    return summaries.get(role, role_name(role))


def hero_build_direction(role: str) -> str:
    directions = {
        "tank": "优先补生命、护甲与抗性。",
        "melee_dps": "优先补攻击、暴击与速度。",
        "ranged_dps": "优先补攻击、暴击与速度。",
        "mage": "优先补法强、速度与伤害加成。",
        "support": "优先补治疗、能量获取与速度。",
    }
    return directions.get(role, "优先补核心主属性与关键词缀。")


def split_aspect_description(aspect: str | None) -> tuple[str, str]:
    if not aspect:
        return ("无", "无")
    description = aspect_description(aspect).strip()
    if not description:
        return ("无", "无")
    if "，" in description:
        trigger, effect = description.split("，", 1)
        return (trigger, effect)
    return ("无", description)


def legendary_effect_lines(aspect: str | None) -> list[str]:
    trigger, effect = split_aspect_description(aspect)
    return [f"触发：{trigger}", f"效果：{effect}"]


def hero_equipment_score(profile: PlayerProfile, hero_id: str) -> float:
    equipped_items = profile.hero_loadouts.get(hero_id, {}).values()
    return round(sum(profile.score_loot_for_hero(hero_id, item) for item in equipped_items), 2)


def format_stat_value(value: int | float) -> str:
    if isinstance(value, float) and abs(value) < 1:
        return f"{value:.0%}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def catalog_item_name(item_id: str) -> str:
    return localize_loot_name(item_id.replace("_", " ").title())


def render_hero_codex_detail(hero_id: str) -> str:
    if hero_id not in HEROES:
        raise ValueError(f"unknown hero_id: {hero_id}")
    hero_template = HEROES[hero_id]
    return "\n".join(
        [
            f"角色详情：{hero_name(hero_id, hero_template.name)}",
            f"职业：{role_name(hero_template.role)}",
            f"推荐站位：{position_name(hero_template.preferred_position)}",
            "基础属性：",
            f"- 生命：{hero_template.base_hp}",
            f"- 攻击：{hero_template.base_atk}",
            f"- 法强：{hero_template.base_mag}",
            f"- 护甲：{hero_template.base_armor}",
            f"- 抗性：{hero_template.base_resist}",
            f"- 速度：{hero_template.base_speed}",
            f"- 暴击率：{hero_template.base_crit_rate:.0%}",
            f"- 暴击伤害：{hero_template.base_crit_damage:.0%}",
            "技能：",
            f"- 普攻：{skill_name(hero_template.basic_skill_id)}",
            f"- 主动：{skill_name(hero_template.active_skill_id)}",
            f"- 被动：{skill_name(hero_template.passive_skill_id)}",
        ]
    )


def render_item_codex_detail(item_id: str) -> str:
    if item_id not in ITEMS:
        raise ValueError(f"unknown item_id: {item_id}")
    item = ITEMS[item_id]
    main_stat_lines = [f"- {stat_label(str(name))}：{format_stat_value(value)}" for name, value in item.main_stat.items()]
    affix_lines = (
        [f"- {affix_name(str(affix.get('type', 'unknown')))}：{format_stat_value(affix.get('value', 0))}" for affix in item.affixes]
        if item.affixes
        else ["- 无"]
    )
    aspect_line = aspect_name(item.legendary_aspect) if item.legendary_aspect else "无"
    return "\n".join(
        [
            f"装备详情：{catalog_item_name(item_id)}",
            f"编号：{item_id}",
            f"稀有度：{rarity_name(item.rarity)}",
            f"部位：{slot_name(item.slot)}",
            f"战力：{item.item_power}",
            "主属性：",
            *main_stat_lines,
            "词缀：",
            *affix_lines,
            f"传奇特效：{aspect_line}",
            *legendary_effect_lines(item.legendary_aspect),
        ]
    )


def render_codex_home(selected_index: int = 0) -> str:
    lines = ["游戏百科", "请选择图鉴分类："]
    for index, label in enumerate(ENCYCLOPEDIA_ROOT_OPTIONS):
        prefix = ">" if index == selected_index else " "
        lines.append(f"{prefix} {label}")
    lines.extend(["", "回车进入，Backspace 返回主界面。"])
    return "\n".join(lines)


def render_hero_codex(selected_index: int = 0) -> str:
    hero_ids = list(HEROES.keys())
    selected_hero_id = hero_ids[selected_index]
    lines = ["角色图鉴（上下方向键切换，Backspace 返回分类）", "角色列表："]
    for index, hero_id in enumerate(hero_ids):
        prefix = ">" if index == selected_index else " "
        lines.append(f"{prefix} {hero_name(hero_id)} [{role_name(HEROES[hero_id].role)}]")
    lines.extend(["", render_hero_codex_detail(selected_hero_id)])
    return "\n".join(lines)


def render_item_codex(selected_index: int = 0) -> str:
    item_ids = list(ITEMS.keys())
    selected_item_id = item_ids[selected_index]
    lines = ["装备图鉴（上下方向键切换，Backspace 返回分类）", "装备列表："]
    for index, item_id in enumerate(item_ids):
        item = ITEMS[item_id]
        prefix = ">" if index == selected_index else " "
        lines.append(f"{prefix} {catalog_item_name(item_id)} [{slot_name(item.slot)}/{rarity_name(item.rarity)}]")
    lines.extend(["", render_item_codex_detail(selected_item_id)])
    return "\n".join(lines)


def display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def fit_display_text(text: str, max_width: int, pad: bool = False) -> str:
    if max_width <= 0:
        return ""
    result: list[str] = []
    width = 0
    for char in text:
        char_width = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1)
        if width + char_width > max_width:
            break
        result.append(char)
        width += char_width
    if pad and width < max_width:
        result.append(" " * (max_width - width))
    return "".join(result)


def wrap_display_text(text: str, max_width: int) -> list[str]:
    if max_width <= 0:
        return [""]
    if not text:
        return [""]
    lines: list[str] = []
    current: list[str] = []
    current_width = 0
    for char in text:
        char_width = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1)
        if current and current_width + char_width > max_width:
            lines.append("".join(current))
            current = [char]
            current_width = char_width
            continue
        current.append(char)
        current_width += char_width
    if current:
        lines.append("".join(current))
    return lines


def panel_unit_line(slot_index: int, unit_name: str, position: str, current_hp: int, max_hp: int, level: int | None = None) -> str:
    level_text = f" Lv{level}" if level is not None else ""
    return f"- {slot_index}：{unit_name} [{position_name(position)}]{level_text} HP {max(current_hp, 0)}/{max_hp}"


def build_situation_summary(ally_units: list, enemy_units: list, threat_tags: list[str]) -> str:
    def fragile_unit_names(units: list) -> list[str]:
        names: list[str] = []
        for unit in units:
            max_hp = max(1, int(unit.stats.max_hp))
            if unit.current_hp / max_hp <= 0.4:
                names.append(hero_name(unit.hero.hero_id, unit.name))
        return names

    fragile_allies = fragile_unit_names(ally_units)
    fragile_enemies = fragile_unit_names(enemy_units)
    if fragile_allies and fragile_enemies:
        return f"局势：{fragile_allies[0]} 与 {fragile_enemies[0]} 都在残血，胜负即将分出。"
    if fragile_allies:
        return f"局势：{fragile_allies[0]} 承压明显，需要稳住阵线。"
    if fragile_enemies:
        return f"局势：敌方 {fragile_enemies[0]} 残血，可优先击穿。"
    tag_set = set(threat_tags)
    if "backline_pressure" in tag_set:
        return "局势：敌方持续施压后排，需优先保护核心输出。"
    if "sustain" in tag_set:
        return "局势：敌方续航较强，注意别被拖入持久战。"
    if "aoe_pressure" in tag_set:
        return "局势：敌方范围压制明显，需要尽快结束战斗。"
    return "局势：双方阵线完整，节奏将由先手与爆发决定。"


def render_menu() -> str:
    return "\n".join(
        [
            "操作菜单：",
            "【战斗】",
            "  开始战斗      进入当前关卡战斗",
            "  关卡情报      查看当前地图、敌方与威胁",
            "  下一关        切换到下一已解锁关卡",
            "",
            "【队伍】",
            "  队伍详情      查看当前上阵队伍",
            "  全部英雄      查看全英雄练度与状态",
            "  升级建议      查看全队最优装备升级",
            "  自动装备      自动为全队装备当前最佳升级",
            "  装备管理      查看背包详情并手动分配装备",
            "",
            "【知识】",
            "  游戏百科      浏览所有角色与装备详情",
            "",
            "【系统】",
            "  保存存档      将当前进度写入磁盘",
            "  重新读取      从磁盘重新读取存档",
            "  重置存档      清空当前进度并恢复默认初始存档",
            "  退出游戏      退出终端界面",
        ]
    )


def render_profile(profile: PlayerProfile) -> str:
    party_levels = [profile.hero_level(hero_id) for hero_id, _position in profile.party]
    lines = [
        f"金币：{profile.gold}",
        f"材料：{profile.materials}",
        f"当前关卡：{profile.current_stage}",
        f"已解锁最高关卡：{profile.highest_stage_unlocked}",
        "上阵队伍：",
    ]
    lines.extend(
        f"- 槽位 {idx + 1}：{hero_name(hero_id)}（{position_name(position)}）"
        for idx, (hero_id, position) in enumerate(profile.party)
    )
    lines.append(f"队伍摘要：{profile.party_summary()}")
    lines.append(f"队伍等级：平均 {sum(party_levels) / len(party_levels):.1f}，最高 {max(party_levels)}")
    return "\n".join(lines)


def render_stage(profile: PlayerProfile, engine: BattleEngine) -> str:
    encounter_preview = engine.describe_stage_encounter(profile.current_stage)
    threat_analysis = engine.analyze_stage_encounter(profile.current_stage)
    recommendations = engine.generate_stage_recommendations(profile, profile.current_stage)
    recommendation_lines = [f"- {line}" for line in recommendations]
    return "\n".join(
        [
            f"当前关卡：{profile.current_stage}",
            f"已解锁最高关卡：{profile.highest_stage_unlocked}",
            "",
            encounter_preview,
            "",
            render_threat_summary(threat_analysis),
            "",
            f"队伍摘要：{profile.party_summary()}",
            "推荐策略：",
            *recommendation_lines,
        ]
    )


def render_party(profile: PlayerProfile) -> str:
    lines = ["当前队伍："]
    weakest_recommendation: dict[str, float | str] | None = None
    for idx, (hero_id, position) in enumerate(profile.party, start=1):
        hero_template = HEROES[hero_id]
        recommendation = profile.recommend_upgrade_for_hero(hero_id)
        recommendation_delta = float(recommendation["score_delta"]) if recommendation is not None else 0.0
        weakest_delta = float(weakest_recommendation["score_delta"]) if weakest_recommendation is not None else 0.0
        if recommendation is not None and (weakest_recommendation is None or recommendation_delta > weakest_delta):
            weakest_recommendation = recommendation
        lines.extend(
            [
                f"- {idx} {hero_name(hero_id)}（{position_name(position)}）Lv{profile.hero_level(hero_id)}",
                f"  职责：{role_summary(hero_template.role)}",
                f"  成长：经验 {profile.hero_xp(hero_id)}/{profile.xp_to_next_level(hero_id)} / 专精 {specialization_name(profile.hero_specialization(hero_id) or 'none')}",
                f"  装备：评分 {hero_equipment_score(profile, hero_id):.2f}",
                (
                    f"  建议：{slot_name(str(recommendation['slot']))}可升级"
                    if recommendation is not None
                    else "  建议：当前无明显装备升级"
                ),
            ]
        )
    if weakest_recommendation is not None:
        lines.append(f"当前短板：{hero_name(str(weakest_recommendation['hero_id']))}装备可提升。")
    else:
        lines.append("当前队伍前排稳定，后排输出充足。")
    return "\n".join(lines)


def render_heroes(profile: PlayerProfile) -> str:
    lines = ["英雄列表："]
    for hero_id in profile.hero_progress:
        progress = profile.hero_progress[hero_id]
        hero_template = HEROES[hero_id]
        spec = specialization_name(profile.hero_specialization(hero_id) or "none")
        recommendation = profile.recommend_upgrade_for_hero(hero_id)
        lines.extend(
            [
                f"- {hero_name(hero_id)} Lv{progress['level']} [{party_status_name(profile.hero_status(hero_id))}]",
                f"  职责：{role_summary(hero_template.role)}",
                f"  成长：经验 {progress['xp']}/{profile.xp_to_next_level(hero_id)} / 专精 {spec}",
                f"  装备：评分 {hero_equipment_score(profile, hero_id):.2f}",
                (
                    f"  建议：{slot_name(str(recommendation['slot']))}可升级"
                    if recommendation is not None
                    else "  建议：当前无明显装备升级"
                ),
            ]
        )
    return "\n".join(lines)


def render_hero_specialization(profile: PlayerProfile, hero_id: str) -> str:
    if hero_id not in HEROES:
        raise ValueError(f"unknown hero_id: {hero_id}")
    hero_template = HEROES[hero_id]
    available = [specialization_name(name) for name in profile.available_specializations(hero_id)]
    selected = specialization_name(profile.hero_specialization(hero_id) or "none")
    ranks = profile.skill_ranks(hero_id)
    return "\n".join(
        [
            f"专精：{selected}",
            f"英雄：{hero_name(hero_id, hero_template.name)}",
            "解锁等级：6",
            f"可选专精：{', '.join(available) if available else '未解锁'}",
            f"技能等级：普攻={ranks['basic']} 主动={ranks['active']} 被动={ranks['passive']}",
        ]
    )


def render_hero_detail(profile: PlayerProfile, hero_id: str) -> str:
    if hero_id not in HEROES:
        raise ValueError(f"unknown hero_id: {hero_id}")
    hero_template = HEROES[hero_id]
    level = profile.hero_level(hero_id)
    xp = profile.hero_xp(hero_id)
    gear = profile.hero_loadouts.get(hero_id, {})
    gear_text = (
        ", ".join(f"{slot_name(slot)}={localize_loot_name(item.display_name)}" for slot, item in sorted(gear.items()))
        if gear
        else "无"
    )
    specialization = specialization_name(profile.hero_specialization(hero_id) or "none")
    ranks = profile.skill_ranks(hero_id)
    recommendation = profile.recommend_upgrade_for_hero(hero_id)
    recommendation_lines = (
        [
            f"当前升级：{localize_loot_name(str(recommendation['display_name']))}",
            f"候选评分：{float(recommendation['score']):.2f}",
            f"当前装备评分：{float(recommendation['equipped_score']):.2f}",
            f"提升值：{float(recommendation['score_delta']):.2f}",
            f"方向：{hero_build_direction(hero_template.role)}",
        ]
        if recommendation is not None
        else ["当前升级：无", f"方向：{hero_build_direction(hero_template.role)}"]
    )
    return "\n".join(
        [
            hero_name(hero_id, hero_template.name),
            f"定位：{role_name(hero_template.role)} / {position_name(hero_template.preferred_position)}",
            "成长：",
            f"等级：{level}",
            f"经验：{xp}/{profile.xp_to_next_level(hero_id)}",
            f"状态：{party_status_name(profile.hero_status(hero_id))}",
            f"专精：{specialization}",
            "装备：",
            f"当前装备：{gear_text}",
            f"装备评分：{hero_equipment_score(profile, hero_id):.2f}",
            "技能：",
            f"技能等级：普攻={ranks['basic']} 主动={ranks['active']} 被动={ranks['passive']}",
            f"普攻等级：{ranks['basic']}",
            f"主动等级：{ranks['active']}",
            f"被动等级：{ranks['passive']}",
            "推荐：",
            *recommendation_lines,
        ]
    )


def render_hero_recommendation(profile: PlayerProfile, hero_id: str) -> str:
    if hero_id not in HEROES:
        raise ValueError(f"unknown hero_id: {hero_id}")
    hero_template = HEROES[hero_id]
    recommendation = profile.recommend_upgrade_for_hero(hero_id)
    hero_label = hero_name(hero_id)
    if recommendation is None:
        return "\n".join(
            [
                "推荐：",
                f"英雄：{hero_label}",
                f"方向：{hero_build_direction(hero_template.role)}",
                "当前升级：无",
                "结论：背包中没有正收益升级。",
            ]
        )
    return "\n".join(
        [
            "推荐：",
            f"英雄：{hero_label}",
            f"方向：{hero_build_direction(hero_template.role)}",
            f"候选物品：{localize_loot_name(str(recommendation['display_name']))}",
            f"部位：{slot_name(str(recommendation['slot']))}",
            f"候选评分：{recommendation['score']:.2f}",
            f"当前装备评分：{recommendation['equipped_score']:.2f}",
            f"提升值：{recommendation['score_delta']:.2f}",
            f"结论：{verdict_name(str(recommendation['verdict']))}",
        ]
    )


def render_best_upgrades(profile: PlayerProfile) -> str:
    return "\n".join(profile.best_upgrade_lines())


def render_inventory_detail(item: LootItem) -> str:
    main_stat_lines = [f"- {stat_label(str(name))}：{format_stat_value(value)}" for name, value in item.main_stat.items()]
    affix_lines = (
        [f"- {affix_name(str(affix.get('type', 'unknown')))}：{format_stat_value(float(affix.get('value', 0)))}" for affix in item.affixes]
        if item.affixes
        else ["- 无"]
    )
    aspect_line = aspect_name(item.legendary_aspect) if item.legendary_aspect else "无"
    recommended = ", ".join(hero_name(hero_id) for hero_id in item.recommended_hero_ids) if item.recommended_hero_ids else "无"
    return "\n".join(
        [
            f"背包物品详情：{localize_loot_name(item.display_name)}",
            f"编号：{item.item_id}",
            f"稀有度：{rarity_name(item.rarity)}",
            f"部位：{slot_name(item.slot)}",
            f"战力：{item.item_power}",
            "主属性：",
            *main_stat_lines,
            "词缀：",
            *affix_lines,
            f"传奇特效：{aspect_line}",
            *legendary_effect_lines(item.legendary_aspect),
            f"推荐：{recommended}",
        ]
    )


def shared_inventory_items(profile: PlayerProfile) -> list[LootItem]:
    return list(profile.inventory)



def loot_slot_to_profile_slot(slot: str) -> str:
    slot_map = {
        "helmet": "head",
        "gloves": "hands",
        "pants": "legs",
        "ring": "ring_1",
        "boots": "bracers",
    }
    return slot_map.get(slot, slot)



def profile_slot_to_loot_slot(slot: str) -> str:
    slot_map = {
        "head": "helmet",
        "hands": "gloves",
        "legs": "pants",
        "ring_1": "ring",
        "ring_2": "ring",
        "bracers": "boots",
    }
    return slot_map.get(slot, slot)



def infer_primary_element(item: LootItem) -> str:
    name_blob = f"{item.display_name} {item.legendary_aspect or ''}".lower()
    if any(token in name_blob for token in ("ember", "fire", "burn")):
        return "fire"
    if any(token in name_blob for token in ("frost", "ice", "cold")):
        return "ice"
    if any(token in name_blob for token in ("storm", "lightning", "volt")):
        return "lightning"
    return "neutral"



def infer_build_tags_for_hero(profile: PlayerProfile, hero_id: str) -> list[str]:
    hero = HEROES[hero_id]
    tags = [hero.role]
    specialization = profile.hero_specialization(hero_id)
    if specialization:
        tags.append(specialization)
    if hero.role == "mage":
        tags.extend(["mage", infer_mage_direction_from_loadout(profile, hero_id)])
    elif hero.role == "support":
        tags.extend(["support", "healing"])
    elif hero.role == "tank":
        tags.extend(["defense", "survival"])
    else:
        tags.extend([hero.role, "damage"])
    return list(dict.fromkeys(tag for tag in tags if tag))



def infer_future_build_tags_for_hero(profile: PlayerProfile, hero_id: str) -> list[str]:
    hero = HEROES[hero_id]
    if hero.role == "mage":
        current = infer_mage_direction_from_loadout(profile, hero_id)
        future_tags = {"fire", "ice", "lightning"}
        future_tags.discard(current)
        return sorted(future_tags)
    if hero.role == "support":
        return ["barrier", "healing"]
    if hero.role == "tank":
        return ["defense", "thorns"]
    return ["damage", "crit"]



def infer_mage_direction_from_loadout(profile: PlayerProfile, hero_id: str) -> str:
    loadout = profile.hero_loadouts.get(hero_id, {})
    counts = {"fire": 0, "ice": 0, "lightning": 0}
    for item in loadout.values():
        element = infer_primary_element(item)
        if element in counts:
            counts[element] += 1
    return max(counts, key=counts.get) if any(counts.values()) else "fire"



def loot_item_to_static_profile(item: LootItem) -> ItemStaticProfile:
    rarity_map = {"magic": "magic", "rare": "rare", "legendary": "legendary"}
    source_type = "regional_boss" if item.legendary_aspect == "saints_resolve" else "abyss_drop"
    legendary_tier = "world_legendary" if item.legendary_aspect else "none"
    affixes: list[AffixProfile] = []
    star_count = 0
    for affix in item.affixes:
        affix_key = str(affix.get("type", "unknown"))
        raw_value = float(affix.get("value", 0.0))
        normalized_roll = max(0.05, min(1.0, abs(raw_value) / 0.14 if abs(raw_value) <= 1 else abs(raw_value) / 30.0))
        is_star = bool(affix.get("is_star", False))
        if is_star:
            star_count += 1
        affixes.append(
            AffixProfile(
                affix_family=affix_key,
                affix_key=affix_key,
                value=raw_value,
                min_roll=0.0,
                max_roll=max(raw_value, 1.0),
                normalized_roll=normalized_roll,
                is_star=is_star,
                is_core_for_current_item_type=affix_key in {"damage_bonus", "energy_gain_bonus", "crit_rate", "heal_bonus"},
            )
        )
    effects: list[LegendaryEffectProfile] = []
    if item.legendary_aspect:
        build_tags = []
        effect_scope = "numeric"
        power_band = "core"
        is_rulebreaking = False
        is_boss_identity = source_type == "regional_boss"
        if item.legendary_aspect == "embers_feed_energy":
            build_tags = ["mage", "fire"]
        elif item.legendary_aspect == "barrier_haste":
            build_tags = ["support", "barrier"]
        elif item.legendary_aspect == "predator_fury":
            build_tags = ["damage", "crit"]
        elif item.legendary_aspect == "saints_resolve":
            build_tags = ["support", "healing"]
            effect_scope = "rulebreaking"
            power_band = "chase"
            is_rulebreaking = True
        effects.append(
            LegendaryEffectProfile(
                effect_id=item.legendary_aspect,
                name=aspect_name(item.legendary_aspect),
                effect_scope=effect_scope,
                granted_by=legendary_tier,
                power_band=power_band,
                build_tags=build_tags,
                is_boss_identity_effect=is_boss_identity,
                is_rulebreaking=is_rulebreaking,
                extractable=not is_boss_identity and not is_rulebreaking,
                imprintable=not is_boss_identity and not is_rulebreaking,
            )
        )
    is_ancestral = item.item_power >= 900
    return ItemStaticProfile(
        item_id=item.item_id,
        name=localize_loot_name(item.display_name),
        slot=loot_slot_to_profile_slot(item.slot),
        rarity=rarity_map.get(item.rarity, "magic"),
        item_power=900 if is_ancestral else item.item_power,
        is_ancestral=is_ancestral,
        star_affix_count=star_count,
        source_type=source_type,
        source_boss="regional_boss" if source_type == "regional_boss" else None,
        legendary_tier=legendary_tier,
        primary_element=infer_primary_element(item),
        affixes=affixes,
        legendary_effects=effects,
        workshop_state=WorkshopState(
            strengthen_level=0,
            can_strengthen=True,
            can_reroll=True,
            can_refine=is_ancestral,
            can_extract=bool(item.legendary_aspect) and source_type != "regional_boss",
            can_imprint=bool(item.legendary_aspect) and source_type != "regional_boss",
        ),
        is_first_discovery=False,
        locked=False,
        enchanted=False,
    )



def build_loot_context_for_hero(profile: PlayerProfile, hero_id: str) -> BuildContext:
    equipped: dict[str, EquippedItemReference] = {}
    hero_loadout = profile.hero_loadouts.get(hero_id, {})
    for slot, item in hero_loadout.items():
        mapped_slot = loot_slot_to_profile_slot(slot)
        equipped[mapped_slot] = EquippedItemReference(
            slot=mapped_slot,
            equipped_item_id=item.item_id,
            effective_power_score=profile.score_loot_for_hero(hero_id, item),
            build_tags=infer_build_tags_for_hero(profile, hero_id),
        )
    current_element = infer_primary_element(next(iter(hero_loadout.values()))) if hero_loadout else (
        infer_mage_direction_from_loadout(profile, hero_id) if HEROES[hero_id].role == "mage" else "neutral"
    )
    return BuildContext(
        player_level=profile.hero_level(hero_id),
        current_element=current_element,
        main_skill_id=f"{hero_id}_main",
        secondary_skill_id=f"{hero_id}_secondary",
        passive_skill_ids=[f"{hero_id}_passive_1", f"{hero_id}_passive_2"],
        current_build_tags=infer_build_tags_for_hero(profile, hero_id),
        future_build_tags=infer_future_build_tags_for_hero(profile, hero_id),
        preferred_affix_families=list(dict.fromkeys(infer_build_tags_for_hero(profile, hero_id) + ["damage_bonus", "crit_rate", "energy_gain_bonus", "heal_bonus"])),
        avoided_affix_families=["heal_bonus"] if HEROES[hero_id].role in {"melee_dps", "ranged_dps"} else [],
        equipped=equipped,
        unlocked_boss_paths=[],
        discovered_legendary_effect_ids=[],
    )



def evaluate_loot_item_for_hero(profile: PlayerProfile, hero_id: str, item: LootItem):
    static_item = loot_item_to_static_profile(item)
    context = build_loot_context_for_hero(profile, hero_id)
    evaluation = evaluate_drop(static_item, context)
    presentation = build_drop_presentation(static_item, evaluation)
    return static_item, evaluation, presentation



def salvage_candidate_count(profile: PlayerProfile, hero_id: str) -> int:
    count = 0
    for item in profile.inventory:
        _static_item, evaluation, _presentation = evaluate_loot_item_for_hero(profile, hero_id, item)
        if evaluation.auto_salvage_suggested or evaluation.verdict == "salvage_candidate":
            count += 1
    return count



def equipped_items_for_hero(profile: PlayerProfile, hero_id: str) -> list[LootItem]:
    return [item for _slot, item in sorted(profile.hero_loadouts.get(hero_id, {}).items())]



def format_stat_delta(value: int | float) -> str:
    return f"{value:+g}" if isinstance(value, int) else f"{format_stat_value(value) if value < 0 else '+' + format_stat_value(value)}"


def build_score_comparison_verdict(
    hero_id: str,
    candidate_item: LootItem,
    equipped_item: LootItem | None,
    score_delta: float,
    negative_labels: list[str],
) -> str:
    if equipped_item is None and score_delta > 0:
        return "结论：当前槽位为空，推荐立即装备。"
    if score_delta <= 0:
        return "结论：收益有限，可暂缓更换。"
    if candidate_item.recommended_hero_ids and hero_id not in candidate_item.recommended_hero_ids:
        return "结论：更适合其他角色，不建议当前英雄使用。"
    if negative_labels:
        return f"结论：评分更高，但会损失{negative_labels[0]}。"
    if score_delta >= 40:
        return "结论：推荐立即替换。"
    if score_delta >= 15:
        return "结论：稳定提升，建议更换。"
    return "结论：收益有限，可视情况更换。"


def build_battle_round_summary(result) -> str:
    analysis = result.analysis or {}
    reason_summary = str(analysis.get("reason_summary") or "").strip()
    if reason_summary:
        return reason_summary
    if result.winner == "ally":
        return "我方稳住了阵线，并逐步拿下主动权。"
    if result.winner == "enemy":
        return "敌方抢到了关键节奏，我方未能稳住战线。"
    return "战线来回拉扯，局势一度相当胶着。"


def build_battle_danger_hint(result) -> str:
    analysis = result.analysis or {}
    first_fall = str(analysis.get("first_fall") or "无")
    top_damage = str(analysis.get("top_damage") or "无")
    top_healing = str(analysis.get("top_healing") or "无")
    if first_fall != "无":
        return f"{first_fall} 最先倒下，是本场最早的破口。"
    if top_damage != "无":
        return f"重点留意 {top_damage} 的爆发压制。"
    if top_healing != "无":
        return f"{top_healing} 的续航显著影响了战斗节奏。"
    return "暂无单一危险点，先手与集火仍是关键。"



def render_item_score_comparison(profile: PlayerProfile, hero_id: str, candidate_item: LootItem, equipped_item: LootItem | None) -> str:
    candidate_score = profile.score_loot_for_hero(hero_id, candidate_item)
    equipped_score = profile.score_loot_for_hero(hero_id, equipped_item) if equipped_item is not None else 0.0
    score_delta = round(candidate_score - equipped_score, 2)
    stat_keys = list(candidate_item.main_stat.keys())
    for stat_name in equipped_item.main_stat.keys() if equipped_item is not None else []:
        if stat_name not in stat_keys:
            stat_keys.append(stat_name)

    candidate_affixes: dict[str, float] = {}
    for affix in candidate_item.affixes:
        affix_type = str(affix.get("type", "unknown"))
        candidate_affixes[affix_type] = candidate_affixes.get(affix_type, 0.0) + float(affix.get("value", 0))

    equipped_affixes: dict[str, float] = {}
    if equipped_item is not None:
        for affix in equipped_item.affixes:
            affix_type = str(affix.get("type", "unknown"))
            equipped_affixes[affix_type] = equipped_affixes.get(affix_type, 0.0) + float(affix.get("value", 0))

    affix_keys = list(candidate_affixes.keys())
    for affix_type in equipped_affixes.keys():
        if affix_type not in affix_keys:
            affix_keys.append(affix_type)

    lines = [
        "评分对比：",
        f"候选评分：{candidate_score:.2f}",
        f"当前装备评分：{equipped_score:.2f}",
        f"提升值：{score_delta:.2f}",
        "主属性对比：",
    ]
    negative_labels: list[str] = []
    for stat_name in stat_keys:
        candidate_value = float(candidate_item.main_stat.get(stat_name, 0))
        equipped_value = float(equipped_item.main_stat.get(stat_name, 0)) if equipped_item is not None else 0.0
        delta = candidate_value - equipped_value
        if delta < 0:
            negative_labels.append(stat_label(str(stat_name)))
        lines.append(
            f"- {stat_label(str(stat_name))}：{format_stat_value(candidate_value)} vs {format_stat_value(equipped_value)} ({format_stat_delta(delta)})"
        )

    lines.append("词缀对比：")
    if not affix_keys:
        lines.append("- 无")
        lines.append(build_score_comparison_verdict(hero_id, candidate_item, equipped_item, score_delta, negative_labels))
        return "\n".join(lines)

    for affix_type in affix_keys:
        candidate_value = candidate_affixes.get(affix_type, 0.0)
        equipped_value = equipped_affixes.get(affix_type, 0.0)
        delta = candidate_value - equipped_value
        if delta < 0:
            negative_labels.append(affix_name(affix_type))
        lines.append(
            f"- {affix_name(affix_type)}：{format_stat_value(candidate_value)} vs {format_stat_value(equipped_value)} ({format_stat_delta(delta)})"
        )
    lines.append(build_score_comparison_verdict(hero_id, candidate_item, equipped_item, score_delta, negative_labels))
    return "\n".join(lines)



def render_loot_decision_panel(profile: PlayerProfile, hero_id: str, item: LootItem) -> str:
    _static_item, evaluation, presentation = evaluate_loot_item_for_hero(profile, hero_id, item)
    badge_text = " ".join(badge.text for badge in presentation.badges)
    lines = [
        "掉落面板：",
        presentation.title_line,
    ]
    if presentation.subtitle_line:
        lines.append(presentation.subtitle_line)
    if badge_text:
        lines.append(f"徽章：{badge_text}")
    lines.append(f"展示层：{presentation.layer}")
    lines.append(f"推荐动作：{presentation.recommended_action_line or '建议动作：先保留观察'}")
    if presentation.reason_lines:
        lines.append("原因：")
        lines.extend(f"- {line}" for line in presentation.reason_lines)
    return "\n".join(lines)



def inventory_workshop_hint(profile: PlayerProfile, hero_id: str, item: LootItem) -> str:
    _static_item, evaluation, _presentation = evaluate_loot_item_for_hero(profile, hero_id, item)
    if evaluation.workshop_action == "none":
        return ""
    action_labels = {
        "strengthen": "强化",
        "reroll": "洗练",
        "refine": "精修",
        "extract": "萃取",
    }
    action_text = action_labels.get(evaluation.workshop_action, evaluation.workshop_action)
    return f"按 W 进入工坊执行推荐动作（{action_text}）"



def workshop_target_hero_id(profile: PlayerProfile, fallback_hero_id: str, item: LootItem) -> str:
    party_hero_ids = [hero_id for hero_id, _position in profile.party]
    for hero_id in item.recommended_hero_ids:
        if hero_id in party_hero_ids:
            return hero_id
    return fallback_hero_id



def apply_workshop_action_to_item(item: LootItem, action: str) -> LootItem:
    if action == "strengthen":
        if item.strengthen_level >= MAX_WORKSHOP_STRENGTHEN_LEVEL:
            raise ValueError("strengthen level already at +8")
        item.strengthen_level += 1
        item.item_power += 5
        return item
    if action == "reroll":
        item.reroll_count += 1
        return item
    if action == "refine":
        item.refine_count += 1
        return item
    if action == "extract":
        return item
    raise ValueError(f"unsupported workshop action: {action}")



def build_loot_summary_lines(profile: PlayerProfile, hero_id: str, loot_items: list[LootItem]) -> list[str]:
    if not loot_items:
        return ["掉落决策：无"]
    layer_counts = {layer: 0 for layer in loot_config.PRESENTATION_ORDER}
    verdict_counts = {"upgrade_candidate": 0, "situational": 0, "salvage_candidate": 0, "trash": 0, "lock_candidate": 0}
    for item in loot_items:
        _static_item, evaluation, presentation = evaluate_loot_item_for_hero(profile, hero_id, item)
        layer_counts[presentation.layer] = layer_counts.get(presentation.layer, 0) + 1
        verdict_counts[evaluation.verdict] = verdict_counts.get(evaluation.verdict, 0) + 1
    summary = (
        f"掉落决策：中断 {layer_counts['L1_interrupt']} / 关注 {layer_counts['L2_attention']} / 折叠 {layer_counts['L3_folded']} / 静默垃圾 {layer_counts['L4_silent']}"
    )
    verdict_line = (
        f"升级候选 {verdict_counts['upgrade_candidate']}，条件保留 {verdict_counts['situational']}，分解候选 {verdict_counts['salvage_candidate']}，垃圾 {verdict_counts['trash']}"
    )
    return [summary, verdict_line]



def render_inventory_management(
    profile: PlayerProfile,
    selected_item_index: int = 0,
    selected_hero_index: int = 0,
    focus: str = "inventory",
    selected_equipped_index: int = 0,
) -> str:
    hero_ids = [hero_id for hero_id, _position in profile.party] or list(HEROES.keys())
    selected_hero_id = hero_ids[selected_hero_index % len(hero_ids)]
    filtered_inventory = shared_inventory_items(profile)
    equipped_items = equipped_items_for_hero(profile, selected_hero_id)
    focus_label = "已装备" if focus == "equipped" else "背包"
    lines = [
        "装备管理（上下切换条目，左右切换目标英雄，Tab 切换背包/已装备，Enter 执行，W 工坊，Backspace 返回）",
        f"目标英雄：{hero_name(selected_hero_id)}",
        f"当前视图：{focus_label}",
        f"待分解：{salvage_candidate_count(profile, selected_hero_id)}",
    ]
    if focus == "equipped":
        lines.append("Enter 卸下当前装备")
        lines.extend(["", "已装备列表："])
        if not equipped_items:
            lines.append("- 当前英雄暂无已装备物品")
            return "\n".join(lines)
        selected_equipped = equipped_items[selected_equipped_index % len(equipped_items)]
        for index, item in enumerate(equipped_items):
            prefix = ">" if index == selected_equipped_index % len(equipped_items) else " "
            lines.append(
                f"{prefix} {localize_loot_name(item.display_name)} [{slot_name(item.slot)}/{rarity_name(item.rarity)}] 战力={item.item_power}"
            )
        lines.extend(["", render_inventory_detail(selected_equipped)])
        return "\n".join(lines)

    lines.append("按 Enter 将当前物品装备给目标英雄（分解候选会直接分解）")
    if not filtered_inventory:
        lines.extend(["", "背包为空"])
        return "\n".join(lines)

    selected_item = filtered_inventory[selected_item_index % len(filtered_inventory)]
    workshop_hero_id = workshop_target_hero_id(profile, selected_hero_id, selected_item)
    workshop_hint = inventory_workshop_hint(profile, workshop_hero_id, selected_item)
    equipped_item = profile.hero_loadouts.get(selected_hero_id, {}).get(selected_item.slot)
    equipped_text = localize_loot_name(equipped_item.display_name) if equipped_item is not None else "无"
    lines.extend(
        [
            f"当前槽位装备：{equipped_text}",
            *( [workshop_hint] if workshop_hint else [] ),
            "",
            "背包列表：",
        ]
    )
    for index, item in enumerate(filtered_inventory):
        prefix = ">" if index == selected_item_index % len(filtered_inventory) else " "
        _static_item, evaluation, _presentation = evaluate_loot_item_for_hero(profile, selected_hero_id, item)
        verdict_label = loot_config.VERDICT_LABELS.get(evaluation.verdict, evaluation.verdict)
        lines.append(
            f"{prefix} {localize_loot_name(item.display_name)} [{slot_name(item.slot)}/{rarity_name(item.rarity)}] 战力={item.item_power} · {verdict_label}"
        )
    lines.extend(
        [
            "",
            render_inventory_detail(selected_item),
            "",
            render_item_score_comparison(profile, selected_hero_id, selected_item, equipped_item),
            "",
            render_loot_decision_panel(profile, selected_hero_id, selected_item),
        ]
    )
    return "\n".join(lines)


def autosave_profile(profile: PlayerProfile, save_path: Path) -> Path:
    return profile.save(save_path)


def battle_command_from_key(key: int) -> str | None:
    if key in (ord("s"), ord("S")):
        return "skip"
    if key in (ord("q"), ord("Q")):
        return "quit"
    return None


def best_party_upgrade(profile: PlayerProfile) -> dict[str, object] | None:
    recommendations: list[dict[str, object]] = []
    for hero_id, _position in profile.party:
        recommendation = profile.recommend_upgrade_for_hero(hero_id)
        if recommendation is not None:
            recommendations.append(recommendation)
    if not recommendations:
        return None
    return max(recommendations, key=lambda entry: float(entry["score_delta"]))


def build_battle_summary_lines(
    result,
    stage: int,
    current_stage: int,
    advanced: bool,
    xp_gain: int,
    xp_results: dict[str, dict[str, int | str]],
    profile: PlayerProfile | None = None,
) -> list[tuple[str, str]]:
    stage_line = (
        f"第 {stage} 关已通关，当前已推进到第 {current_stage} 关。"
        if advanced
        else f"第 {stage} 关挑战失败，当前仍停留在第 {current_stage} 关。"
    )
    lines: list[tuple[str, str]] = [
        ("SYS", stage_line),
        ("SYS", f"战斗结果：{winner_name(result.winner)}获胜，共 {result.rounds} 回合。"),
    ]
    if result.rewards is not None:
        lines.extend(
            [
                ("SYS", f"获得金币 {result.rewards.gold}。"),
                ("SYS", f"获得材料 {result.rewards.materials}。"),
            ]
        )
        if profile is not None:
            summary_hero_id = profile.party[0][0] if profile.party else "steel_guardian"
            for line in build_loot_summary_lines(profile, summary_hero_id, result.rewards.loot):
                lines.append(("SYS", line))
        for loot in result.rewards.loot:
            lines.append(("SYS", loot.summary_line()))
    if xp_results:
        lines.append(("SYS", f"全队获得 {xp_gain} 点经验。"))
        for hero_id, details in xp_results.items():
            lines.append(
                (
                    "SYS",
                    f"{hero_name(hero_id)}：等级 {details['level']}，当前经验 {details['xp']}（本次 +{details['xp_added']}）",
                )
            )
    lines.extend(
        [
            ("INFO", f"回合摘要：{build_battle_round_summary(result)}"),
            ("INFO", f"危险提示：{build_battle_danger_hint(result)}"),
        ]
    )
    if result.analysis:
        lines.extend(
            [
                ("INFO", f"最高伤害：{result.analysis.get('top_damage', '无')}"),
                ("INFO", f"最高治疗：{result.analysis.get('top_healing', '无')}"),
                ("INFO", f"首个倒下：{result.analysis.get('first_fall', '无')}"),
                ("INFO", f"行动顺序快照：{', '.join(result.analysis.get('action_order_snapshot', [])) or '无'}"),
                ("INFO", f"技能施放统计：{', '.join(result.analysis.get('skill_casts', [])) or '无'}"),
                ("INFO", f"原因总结：{result.analysis.get('reason_summary', '无')}"),
            ]
        )
    return lines


def run_battle_session(engine: BattleEngine, profile: PlayerProfile, save_path: Path = DEFAULT_SAVE_PATH) -> str:
    stage = profile.current_stage
    encounter_preview = engine.describe_stage_encounter(stage)
    threat_analysis = engine.analyze_stage_encounter(stage)
    recommendations = engine.generate_stage_recommendations(profile, stage)
    allies = profile.build_team(engine)
    result = engine.run_stage_battle(allies, stage=stage)
    xp_gain = 0
    xp_results: dict[str, dict[str, int | str]] = {}
    if result.rewards is not None:
        profile.collect_rewards(result.rewards)
        xp_gain = 60 + max(0, stage - 1) * 20
        xp_results = profile.grant_party_xp(xp_gain)
    advanced = profile.record_stage_result(stage=stage, victory=result.winner == "ally")
    autosave_profile(profile, save_path)
    advice_block = "\n".join(
        [
            "战前分析：",
            encounter_preview,
            render_threat_summary(threat_analysis),
            f"队伍摘要：{profile.party_summary()}",
            "推荐策略：",
            *[f"- {line}" for line in recommendations],
        ]
    )
    summary_block = "\n".join(message for _tag, message in build_battle_summary_lines(result, stage, profile.current_stage, advanced, xp_gain, xp_results, profile=profile))
    return f"第 {stage} 关\n{advice_block}\n\n{summary_block}\n\n{result.render()}"


class TerminalUI:
    def __init__(self, engine: BattleEngine, profile: PlayerProfile, save_path: Path) -> None:
        self.engine = engine
        self.profile = profile
        self.save_path = save_path
        self.menu_index = 0
        self.log_delay = BATTLE_LOG_DELAY_SECONDS
        self.is_battle_active = False
        self.is_codex_active = False
        self.is_inventory_active = False
        self.codex_view = "root"
        self.codex_root_index = 0
        self.codex_hero_index = 0
        self.codex_item_index = 0
        self.inventory_item_index = 0
        self.inventory_equipped_index = 0
        self.inventory_hero_index = 0
        self.inventory_focus = "inventory"
        self.should_exit = False
        self.center_entries: list[tuple[str, str]] = []
        self.current_battle_allies = None
        self.current_battle_enemies = None
        self.highlight_name_teams: dict[str, str] = {}
        self.set_center_text(
            [
                "欢迎来到《深渊回响》。",
                "界面说明：左侧显示队伍与地图，中间显示战斗信息，右侧显示背包，下方用方向键选择操作。",
                render_stage(self.profile, self.engine),
            ]
        )

    def set_center_text(self, blocks: list[str], tag: str = "INFO") -> None:
        self.center_entries = []
        for block in blocks:
            for line in str(block).splitlines():
                self.center_entries.append((tag, line))

    def append_center(self, tag: str, message: str) -> None:
        self.center_entries.append((tag, message))

    def apply_battle_log_snapshot(self, entry: BattleLogEntry) -> None:
        if self.current_battle_allies is None or self.current_battle_enemies is None:
            return
        for unit in [*self.current_battle_allies, *self.current_battle_enemies]:
            if unit.unit_id in entry.hp_snapshot:
                unit.current_hp = max(0, int(entry.hp_snapshot[unit.unit_id]))

    def battle_units_by_team(self, team_id: str) -> list:
        battle_units = self.current_battle_allies if team_id == "ally" else self.current_battle_enemies
        if battle_units is not None:
            return battle_units
        if team_id == "ally":
            return self.profile.build_team(self.engine)
        return self.engine.build_enemy_team_for_stage(self.profile.current_stage)

    def refresh_highlight_name_teams(self) -> None:
        ally_names = {hero_name(unit.hero.hero_id, unit.name) for unit in self.battle_units_by_team("ally")}
        enemy_names = {hero_name(unit.hero.hero_id, unit.name) for unit in self.battle_units_by_team("enemy")}
        self.highlight_name_teams = {name: "ally" for name in ally_names}
        self.highlight_name_teams.update({name: "enemy" for name in enemy_names})

    def left_panel_lines(self) -> list[str]:
        encounter = self.engine.get_stage_encounter(self.profile.current_stage)
        analysis = self.engine.analyze_stage_encounter(self.profile.current_stage)
        ally_units = self.battle_units_by_team("ally")
        enemy_units = self.battle_units_by_team("enemy")
        self.refresh_highlight_name_teams()
        threat_tags = [str(tag) for tag in analysis.get("threat_tags", []) if isinstance(tag, str)]
        lines = [
            f"存档：{self.save_path.name}",
            f"资源：金币 {self.profile.gold} / 材料 {self.profile.materials}",
            "",
            "当前地图：",
            f"- 关卡：第 {self.profile.current_stage} 关 / 已解锁 {self.profile.highest_stage_unlocked}",
            f"- 遭遇：{encounter_name(encounter.name)} [{encounter_type_name(encounter.encounter_type)}]",
            f"- 威胁：{', '.join(threat_tag_name(tag) for tag in threat_tags) or '无'}",
            "",
            "我方队伍：",
        ]
        for idx, unit in enumerate(ally_units, start=1):
            lines.append(
                panel_unit_line(
                    idx,
                    hero_name(unit.hero.hero_id, unit.name),
                    unit.position,
                    unit.current_hp,
                    unit.stats.max_hp,
                    self.profile.hero_level(unit.hero.hero_id),
                )
            )
        lines.append("")
        lines.append("敌方队伍：")
        for idx, unit in enumerate(enemy_units, start=1):
            lines.append(panel_unit_line(idx, hero_name(unit.hero.hero_id, unit.name), unit.position, unit.current_hp, unit.stats.max_hp))
        lines.append("")
        lines.append(build_situation_summary(ally_units, enemy_units, threat_tags))
        return lines

    def right_panel_lines(self) -> list[str]:
        if self.is_inventory_active:
            hero_ids = self.inventory_target_hero_ids()
            selected_hero_id = hero_ids[self.inventory_hero_index % len(hero_ids)]
            lines = [f"共享背包（当前装备目标：{hero_name(selected_hero_id)}）："]
            filtered_inventory = shared_inventory_items(self.profile)
            if filtered_inventory:
                selected_index = self.inventory_item_index % len(filtered_inventory)
                for index, item in enumerate(filtered_inventory):
                    prefix = ">" if self.inventory_focus == "inventory" and index == selected_index else "-"
                    lines.append(
                        f"{prefix} {item.item_id}: {localize_loot_name(item.display_name)} [{rarity_name(item.rarity)}] 部位={slot_name(item.slot)} 战力={item.item_power}"
                    )
            else:
                lines.append("- 背包为空")
            lines.extend(["", "已装备："])
            equipped_items = equipped_items_for_hero(self.profile, selected_hero_id)
            if equipped_items:
                selected_equipped = self.inventory_equipped_index % len(equipped_items)
                for index, item in enumerate(equipped_items):
                    prefix = ">" if self.inventory_focus == "equipped" and index == selected_equipped else "-"
                    lines.append(
                        f"{prefix} {slot_name(item.slot)}={localize_loot_name(item.display_name)}"
                    )
            else:
                lines.append("- 暂无装备")
            return lines
        inventory_lines = self.profile.inventory_lines()
        loadout_lines = self.profile.loadout_lines()
        return ["背包：", *inventory_lines, "", "已装备：", *loadout_lines]

    def menu_lines(self) -> list[list[MenuAction]]:
        rows: list[list[MenuAction]] = []
        for start in range(0, len(MENU_ACTIONS), MENU_COLUMNS):
            rows.append(MENU_ACTIONS[start : start + MENU_COLUMNS])
        return rows

    def execute_action(self, stdscr: curses.window) -> bool:
        action = MENU_ACTIONS[self.menu_index].action_id
        if action == "battle":
            self.play_battle(stdscr)
            return not self.should_exit
        if action == "stage":
            self.set_center_text([render_stage(self.profile, self.engine)])
            return True
        if action == "party":
            self.set_center_text([render_party(self.profile), "", render_profile(self.profile)])
            return True
        if action == "codex":
            self.open_codex()
            return True
        if action == "heroes":
            self.set_center_text([render_heroes(self.profile)])
            return True
        if action == "upgrades":
            self.set_center_text([render_best_upgrades(self.profile)])
            return True
        if action == "auto_equip":
            recommendation = best_party_upgrade(self.profile)
            if recommendation is None:
                self.set_center_text(["自动装备：当前背包中没有可用的正收益升级。"])
                return True
            equipped = self.profile.auto_equip_best_upgrade(str(recommendation["hero_id"]))
            autosave_profile(self.profile, self.save_path)
            if equipped is None:
                self.set_center_text(["自动装备失败：未找到可装备物品。"])
                return True
            self.set_center_text(
                [
                    f"已为 {hero_name(str(equipped['hero_id']))} 自动装备 {localize_loot_name(str(equipped['equipped_display_name']))}。",
                    render_best_upgrades(self.profile),
                ]
            )
            return True
        if action == "inventory":
            self.open_inventory_manager()
            return True
        if action == "next_stage":
            new_stage = self.profile.set_stage(self.profile.current_stage + 1)
            autosave_profile(self.profile, self.save_path)
            self.set_center_text([f"已切换到第 {new_stage} 关。", render_stage(self.profile, self.engine)])
            return True
        if action == "save":
            autosave_profile(self.profile, self.save_path)
            self.set_center_text([f"存档已保存到：{self.save_path}"])
            return True
        if action == "reload":
            self.profile = PlayerProfile.load(self.save_path)
            self.set_center_text(["已重新读取存档。", render_profile(self.profile), "", render_stage(self.profile, self.engine)])
            return True
        if action == "reset_save":
            self.profile = create_default_profile()
            autosave_profile(self.profile, self.save_path)
            self.set_center_text(["已重置存档并恢复到初始进度。", render_profile(self.profile), "", render_stage(self.profile, self.engine)])
            return True
        if action == "quit":
            return False
        return True

    def play_battle(self, stdscr: curses.window) -> None:
        stage = self.profile.current_stage
        threat_analysis = self.engine.analyze_stage_encounter(stage)
        recommendations = self.engine.generate_stage_recommendations(self.profile, stage)
        self.should_exit = False
        self.is_battle_active = True
        self.center_entries = []
        self.append_center("SYS", f"开始第 {stage} 关战斗：{encounter_name(self.engine.get_stage_encounter(stage).name)}。")
        self.append_center("INFO", render_threat_summary(threat_analysis))
        for line in recommendations:
            self.append_center("INFO", f"推荐：{line}")
        allies = self.profile.build_team(self.engine)
        enemies = self.engine.build_enemy_team_for_stage(stage)
        self.current_battle_allies = allies
        self.current_battle_enemies = enemies
        self.refresh_highlight_name_teams()
        self.render(stdscr)
        result = self.engine.run_stage_battle(allies, stage=stage, enemies=enemies)
        playback_action = "complete"
        stdscr.nodelay(True)
        try:
            for entry in result.logs:
                command = self.read_battle_command(stdscr)
                if command == "quit":
                    playback_action = "quit"
                    break
                if command == "skip":
                    playback_action = "skip"
                    break
                self.apply_battle_log_snapshot(entry)
                self.append_center(entry.tag, entry.message)
                self.render_battle_frame(stdscr)
                command = self.read_battle_command(stdscr, wait_seconds=self.log_delay)
                if command == "quit":
                    playback_action = "quit"
                    break
                if command == "skip":
                    playback_action = "skip"
                    break
        finally:
            stdscr.nodelay(False)
            self.is_battle_active = False
            self.current_battle_allies = None
            self.current_battle_enemies = None

        if playback_action == "quit":
            self.profile.record_stage_result(stage=stage, victory=False)
            autosave_profile(self.profile, self.save_path)
            self.should_exit = True
            return

        if playback_action == "skip":
            self.append_center("SYS", "已跳过剩余战斗过程，直接显示结算。")
        xp_gain = 0
        xp_results: dict[str, dict[str, int | str]] = {}
        if result.rewards is not None:
            self.profile.collect_rewards(result.rewards)
            xp_gain = 60 + max(0, stage - 1) * 20
            xp_results = self.profile.grant_party_xp(xp_gain)
        advanced = self.profile.record_stage_result(stage=stage, victory=result.winner == "ally")
        autosave_profile(self.profile, self.save_path)
        if playback_action == "skip":
            for entry in result.logs:
                self.append_center(entry.tag, entry.message)
            self.render(stdscr)
        for tag, message in build_battle_summary_lines(result, stage, self.profile.current_stage, advanced, xp_gain, xp_results, profile=self.profile):
            self.append_center(tag, message)
        self.render(stdscr)

    def render_battle_frame(self, stdscr: curses.window) -> None:
        if not hasattr(stdscr, "getmaxyx") or not hasattr(stdscr, "derwin"):
            self.render(stdscr)
            return
        rows, cols = stdscr.getmaxyx()
        if rows < 24 or cols < 100:
            self.render(stdscr)
            return
        bottom_h = 7
        left_w = max(32, cols // 4)
        right_w = max(32, cols // 4)
        center_w = cols - left_w - right_w
        top_h = rows - bottom_h

        left = stdscr.derwin(top_h, left_w, 0, 0)
        center = stdscr.derwin(top_h, center_w, 0, left_w)
        self.draw_text_panel(left, "队伍与地图", self.left_panel_lines())
        self.draw_center_panel(center, "战斗信息", self.center_entries, flush=False)
        curses.doupdate()

    def read_battle_command(self, stdscr: curses.window, wait_seconds: float = 0.0) -> str | None:
        deadline = time.monotonic() + max(0.0, wait_seconds)
        while True:
            command = battle_command_from_key(stdscr.getch())
            if command is not None:
                return command
            if time.monotonic() >= deadline:
                return None
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    def open_codex(self) -> None:
        self.is_codex_active = True
        self.codex_view = "root"
        self.refresh_codex()

    def refresh_codex(self) -> None:
        if self.codex_view == "root":
            self.set_center_text([render_codex_home(self.codex_root_index)])
            return
        if self.codex_view == "heroes":
            self.set_center_text([render_hero_codex(self.codex_hero_index)])
            return
        self.set_center_text([render_item_codex(self.codex_item_index)])

    def inventory_target_hero_ids(self) -> list[str]:
        return [hero_id for hero_id, _position in self.profile.party] or list(HEROES.keys())

    def open_inventory_manager(self) -> None:
        self.is_inventory_active = True
        self.inventory_item_index = 0
        self.inventory_equipped_index = 0
        self.inventory_hero_index = 0
        self.inventory_focus = "inventory"
        self.refresh_inventory_manager()

    def refresh_inventory_manager(self) -> None:
        self.set_center_text(
            [
                render_inventory_management(
                    self.profile,
                    self.inventory_item_index,
                    self.inventory_hero_index,
                    focus=self.inventory_focus,
                    selected_equipped_index=self.inventory_equipped_index,
                )
            ]
        )

    def inventory_move_item(self, delta: int) -> None:
        hero_ids = self.inventory_target_hero_ids()
        selected_hero_id = hero_ids[self.inventory_hero_index % len(hero_ids)]
        if self.inventory_focus == "equipped":
            equipped_items = equipped_items_for_hero(self.profile, selected_hero_id)
            if equipped_items:
                self.inventory_equipped_index = (self.inventory_equipped_index + delta) % len(equipped_items)
            self.refresh_inventory_manager()
            return
        filtered_inventory = shared_inventory_items(self.profile)
        if filtered_inventory:
            self.inventory_item_index = (self.inventory_item_index + delta) % len(filtered_inventory)
        self.refresh_inventory_manager()

    def inventory_move_hero(self, delta: int) -> None:
        hero_ids = self.inventory_target_hero_ids()
        self.inventory_hero_index = (self.inventory_hero_index + delta) % len(hero_ids)
        self.inventory_item_index = 0
        self.inventory_equipped_index = 0
        self.refresh_inventory_manager()

    def inventory_toggle_focus(self) -> None:
        self.inventory_focus = "equipped" if self.inventory_focus == "inventory" else "inventory"
        self.refresh_inventory_manager()

    def inventory_enter(self) -> None:
        hero_ids = self.inventory_target_hero_ids()
        selected_hero_id = hero_ids[self.inventory_hero_index % len(hero_ids)]
        if self.inventory_focus == "equipped":
            equipped_items = equipped_items_for_hero(self.profile, selected_hero_id)
            if not equipped_items:
                self.refresh_inventory_manager()
                return
            selected_item = equipped_items[self.inventory_equipped_index % len(equipped_items)]
            unequipped_item = self.profile.unequip_item(selected_hero_id, selected_item.slot)
            autosave_profile(self.profile, self.save_path)
            if equipped_items_for_hero(self.profile, selected_hero_id):
                self.inventory_equipped_index = min(
                    self.inventory_equipped_index, len(equipped_items_for_hero(self.profile, selected_hero_id)) - 1
                )
            else:
                self.inventory_equipped_index = 0
                self.inventory_focus = "inventory"
            self.set_center_text(
                [
                    f"已从 {hero_name(selected_hero_id)} 卸下 {localize_loot_name(unequipped_item.display_name)}",
                    "",
                    render_inventory_management(
                        self.profile,
                        self.inventory_item_index,
                        self.inventory_hero_index,
                        focus=self.inventory_focus,
                        selected_equipped_index=self.inventory_equipped_index,
                    ),
                ]
            )
            return
        filtered_inventory = shared_inventory_items(self.profile)
        if not filtered_inventory:
            self.refresh_inventory_manager()
            return
        selected_item = filtered_inventory[self.inventory_item_index % len(filtered_inventory)]
        _static_item, evaluation, _presentation = evaluate_loot_item_for_hero(self.profile, selected_hero_id, selected_item)
        if evaluation.auto_salvage_suggested or evaluation.verdict == "salvage_candidate":
            salvaged_item = self.profile.salvage_inventory_item(selected_item.item_id, materials_gain=1)
            autosave_profile(self.profile, self.save_path)
            remaining_inventory = shared_inventory_items(self.profile)
            if remaining_inventory:
                self.inventory_item_index = min(self.inventory_item_index, len(remaining_inventory) - 1)
            else:
                self.inventory_item_index = 0
            self.set_center_text(
                [
                    f"已标记并分解 {localize_loot_name(salvaged_item.display_name)}，获得 1 材料。",
                    "",
                    render_inventory_management(
                        self.profile,
                        self.inventory_item_index,
                        self.inventory_hero_index,
                        focus=self.inventory_focus,
                        selected_equipped_index=self.inventory_equipped_index,
                    ),
                ]
            )
            return
        equipped_item = self.profile.equip_item(selected_hero_id, selected_item.item_id)
        autosave_profile(self.profile, self.save_path)
        remaining_inventory = shared_inventory_items(self.profile)
        if remaining_inventory:
            self.inventory_item_index = min(self.inventory_item_index, len(remaining_inventory) - 1)
        else:
            self.inventory_item_index = 0
        self.set_center_text(
            [
                f"已为 {hero_name(selected_hero_id)} 装备 {localize_loot_name(equipped_item.display_name)}",
                "",
                render_inventory_management(
                    self.profile,
                    self.inventory_item_index,
                    self.inventory_hero_index,
                    focus=self.inventory_focus,
                    selected_equipped_index=self.inventory_equipped_index,
                ),
            ]
        )

    def inventory_apply_workshop_action(self) -> None:
        if self.inventory_focus != "inventory":
            self.refresh_inventory_manager()
            return
        hero_ids = self.inventory_target_hero_ids()
        selected_hero_id = hero_ids[self.inventory_hero_index % len(hero_ids)]
        filtered_inventory = shared_inventory_items(self.profile)
        if not filtered_inventory:
            self.refresh_inventory_manager()
            return
        selected_item = filtered_inventory[self.inventory_item_index % len(filtered_inventory)]
        workshop_hero_id = workshop_target_hero_id(self.profile, selected_hero_id, selected_item)
        _static_item, evaluation, _presentation = evaluate_loot_item_for_hero(self.profile, workshop_hero_id, selected_item)
        action = evaluation.workshop_action
        if action == "none":
            self.refresh_inventory_manager()
            return
        action_labels = {
            "strengthen": "强化",
            "reroll": "洗练",
            "refine": "精修",
            "extract": "萃取",
        }
        if action == "extract":
            operated_item = self.profile.extract_inventory_aspect(selected_item.item_id)
        else:
            operated_item = apply_workshop_action_to_item(selected_item, action)
        autosave_profile(self.profile, self.save_path)
        remaining_inventory = shared_inventory_items(self.profile)
        if remaining_inventory:
            self.inventory_item_index = min(self.inventory_item_index, len(remaining_inventory) - 1)
        else:
            self.inventory_item_index = 0
        self.set_center_text(
            [
                f"已执行{action_labels.get(action, action)}：{localize_loot_name(operated_item.display_name)}",
                "",
                render_inventory_management(
                    self.profile,
                    self.inventory_item_index,
                    self.inventory_hero_index,
                    focus=self.inventory_focus,
                    selected_equipped_index=self.inventory_equipped_index,
                ),
            ]
        )

    def inventory_back(self) -> None:
        self.is_inventory_active = False
        self.set_center_text([render_stage(self.profile, self.engine)])

    def codex_move(self, delta: int) -> None:
        if self.codex_view == "root":
            self.codex_root_index = (self.codex_root_index + delta) % len(ENCYCLOPEDIA_ROOT_OPTIONS)
        elif self.codex_view == "heroes":
            self.codex_hero_index = (self.codex_hero_index + delta) % len(HEROES)
        else:
            self.codex_item_index = (self.codex_item_index + delta) % len(ITEMS)
        self.refresh_codex()

    def codex_enter(self) -> None:
        if self.codex_view != "root":
            return
        self.codex_view = "heroes" if self.codex_root_index == 0 else "items"
        self.refresh_codex()

    def codex_back(self) -> None:
        if self.codex_view == "root":
            self.is_codex_active = False
            self.set_center_text([render_stage(self.profile, self.engine)])
            return
        self.codex_view = "root"
        self.refresh_codex()

    def run(self, stdscr: curses.window) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_GREEN, -1)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
            curses.init_pair(7, curses.COLOR_CYAN, -1)
            curses.init_pair(8, curses.COLOR_WHITE, -1)
            curses.init_pair(ALLY_NAME_COLOR, 208, -1)
            curses.init_pair(ENEMY_NAME_COLOR, curses.COLOR_RED, -1)
            curses.init_pair(INFO_NAME_COLOR, 39, -1)
        while True:
            self.render(stdscr)
            key = stdscr.getch()
            if self.is_codex_active:
                if key in (ord("q"), ord("Q")):
                    break
                if key in (curses.KEY_UP, curses.KEY_LEFT):
                    self.codex_move(-1)
                elif key in (curses.KEY_DOWN, curses.KEY_RIGHT):
                    self.codex_move(1)
                elif key in (10, 13, curses.KEY_ENTER):
                    self.codex_enter()
                elif key in BACKSPACE_KEYS:
                    self.codex_back()
                continue
            if self.is_inventory_active:
                if key in (ord("q"), ord("Q")):
                    break
                if key == curses.KEY_UP:
                    self.inventory_move_item(-1)
                elif key == curses.KEY_DOWN:
                    self.inventory_move_item(1)
                elif key == curses.KEY_LEFT:
                    self.inventory_move_hero(-1)
                elif key == curses.KEY_RIGHT:
                    self.inventory_move_hero(1)
                elif key == 9:
                    self.inventory_toggle_focus()
                elif key in (ord("w"), ord("W")):
                    self.inventory_apply_workshop_action()
                elif key in (10, 13, curses.KEY_ENTER):
                    self.inventory_enter()
                elif key in BACKSPACE_KEYS:
                    self.inventory_back()
                continue
            if key == curses.KEY_LEFT and self.menu_index > 0:
                self.menu_index -= 1
            elif key == curses.KEY_RIGHT and self.menu_index < len(MENU_ACTIONS) - 1:
                self.menu_index += 1
            elif key == curses.KEY_UP and self.menu_index - MENU_COLUMNS >= 0:
                self.menu_index -= MENU_COLUMNS
            elif key == curses.KEY_DOWN and self.menu_index + MENU_COLUMNS < len(MENU_ACTIONS):
                self.menu_index += MENU_COLUMNS
            elif key in (ord("q"), ord("Q")):
                break
            elif key in (10, 13, curses.KEY_ENTER):
                if not self.execute_action(stdscr):
                    break

    def render(self, stdscr: curses.window) -> None:
        stdscr.erase()
        rows, cols = stdscr.getmaxyx()
        if rows < 24 or cols < 100:
            stdscr.addstr(1, 2, "终端窗口过小，请至少调整到 100x24。")
            stdscr.refresh()
            return
        bottom_h = 7
        left_w = max(32, cols // 4)
        right_w = max(32, cols // 4)
        center_w = cols - left_w - right_w
        top_h = rows - bottom_h

        left = stdscr.derwin(top_h, left_w, 0, 0)
        center = stdscr.derwin(top_h, center_w, 0, left_w)
        right = stdscr.derwin(top_h, right_w, 0, left_w + center_w)
        bottom = stdscr.derwin(bottom_h, cols, top_h, 0)

        self.draw_text_panel(left, "队伍与地图", self.left_panel_lines())
        self.draw_center_panel(center, "战斗信息", self.center_entries)
        self.draw_text_panel(right, "背包", self.right_panel_lines())
        self.draw_menu_panel(bottom)
        stdscr.refresh()

    def draw_text_panel(self, win: curses.window, title: str, lines: list[str]) -> None:
        win.erase()
        win.box()
        self.safe_addstr(win, 0, 2, f" {title} ", curses.A_BOLD)
        y = 1
        width = max(10, win.getmaxyx()[1] - 2)
        for line in lines:
            wrapped = wrap_display_text(line, width - 1)
            for item in wrapped:
                if y >= win.getmaxyx()[0] - 1:
                    break
                self.safe_addstr(win, y, 1, item, max_width=width - 1, fill_width=width - 1)
                y += 1
            if y >= win.getmaxyx()[0] - 1:
                break
        win.noutrefresh()

    def draw_center_panel(self, win: curses.window, title: str, entries: list[tuple[str, str]], flush: bool = True) -> None:
        win.erase()
        win.box()
        self.safe_addstr(win, 0, 2, f" {title} ", curses.A_BOLD)
        inner_h, inner_w = win.getmaxyx()[0] - 2, win.getmaxyx()[1] - 2
        visible_entries = entries[-inner_h:]
        for idx, (tag, message) in enumerate(visible_entries, start=1):
            self.draw_log_line(win, idx, 1, inner_w, tag, message)
        win.noutrefresh()
        if flush:
            curses.doupdate()

    def draw_menu_panel(self, win: curses.window) -> None:
        win.erase()
        win.box()
        self.safe_addstr(win, 0, 2, " 操作 ", curses.A_BOLD)
        if self.is_battle_active:
            self.safe_addstr(win, 1, 2, BATTLE_STATUS_HINT, max_width=win.getmaxyx()[1] - 4, fill_width=win.getmaxyx()[1] - 4)
            self.safe_addstr(win, 2, 2, BATTLE_ABORT_HINT, max_width=win.getmaxyx()[1] - 4, fill_width=win.getmaxyx()[1] - 4)
            win.noutrefresh()
            return
        if self.is_codex_active:
            self.safe_addstr(win, 1, 2, "百科中：上下方向键切换，回车进入分类，Backspace 返回。", max_width=win.getmaxyx()[1] - 4, fill_width=win.getmaxyx()[1] - 4)
            self.safe_addstr(win, 2, 2, "在角色/装备列表中移动选择后，详情会立即显示。", max_width=win.getmaxyx()[1] - 4, fill_width=win.getmaxyx()[1] - 4)
            win.noutrefresh()
            return
        if self.is_inventory_active:
            self.safe_addstr(win, 1, 2, "装备管理中：上下切换条目，左右切换英雄，Tab 切换背包/已装备，Enter 执行，Backspace 返回。", max_width=win.getmaxyx()[1] - 4, fill_width=win.getmaxyx()[1] - 4)
            self.safe_addstr(win, 2, 2, "背包视图可手动装备并显示评分对比；已装备视图可手动卸装，右侧会高亮当前条目。", max_width=win.getmaxyx()[1] - 4, fill_width=win.getmaxyx()[1] - 4)
            win.noutrefresh()
            return
        inner_width = win.getmaxyx()[1] - 4
        self.safe_addstr(win, 1, 2, "方向键移动，回车确认，Q 退出。", max_width=inner_width, fill_width=inner_width)
        y = 3
        x = 2
        for index, action in enumerate(MENU_ACTIONS):
            label = f" {action.label} "
            label_width = display_width(label)
            attr = curses.A_BOLD if index == self.menu_index else curses.A_NORMAL
            if curses.has_colors() and index == self.menu_index:
                attr |= curses.color_pair(1)
            if x + label_width >= win.getmaxyx()[1] - 1:
                y += 1
                x = 2
            if y >= win.getmaxyx()[0] - 1:
                break
            self.safe_addstr(win, y, x, label, attr, max_width=win.getmaxyx()[1] - x - 1)
            x += label_width + 2
            if (index + 1) % MENU_COLUMNS == 0:
                y += 1
                x = 2
        win.noutrefresh()

    def draw_log_line(self, win: curses.window, y: int, x: int, width: int, tag: str, message: str) -> None:
        tag_label = TAG_LABELS.get(tag, tag)
        prefix = f"[{tag_label}] "
        prefix_attr = self.tag_attr(tag)
        self.safe_addstr(win, y, x, "", max_width=width, fill_width=width)
        self.safe_addstr(win, y, x, prefix, prefix_attr, max_width=width)
        remaining = width - display_width(prefix)
        if remaining <= 0:
            return
        cursor = x + display_width(prefix)
        for segment, attr in self.build_log_segments(tag, message):
            available = x + width - cursor
            if available <= 0:
                break
            clipped = fit_display_text(segment, available)
            self.safe_addstr(win, y, cursor, clipped, attr, max_width=available)
            cursor += display_width(clipped)

    def build_log_segments(self, tag: str, message: str) -> list[tuple[str, int]]:
        segments = re.split(r"(【[^】]+】|暴击|\d+)", message)
        output: list[tuple[str, int]] = []
        for segment in segments:
            if not segment:
                continue
            output.extend(self.segment_text_with_team_colors(segment, self.base_segment_attr(tag, segment)))
        return output

    def base_segment_attr(self, tag: str, segment: str) -> int:
        attr = self.tag_attr(tag)
        if segment.startswith("【") and segment.endswith("】"):
            return curses.color_pair(3) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        if segment.isdigit():
            if tag in {"DMG", "DOT", "KILL"}:
                return curses.color_pair(2) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
            if tag in {"HEAL", "SHLD"}:
                return curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
            return curses.color_pair(4) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        if segment == "暴击":
            return curses.color_pair(4) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        return attr

    def segment_text_with_team_colors(self, segment: str, default_attr: int) -> list[tuple[str, int]]:
        if not segment or not self.highlight_name_teams:
            return [(segment, default_attr)]
        matches = []
        for name, team_id in self.highlight_name_teams.items():
            start = segment.find(name)
            if start >= 0:
                matches.append((start, len(name), name, team_id))
        if not matches:
            return [(segment, default_attr)]
        matches.sort(key=lambda item: (item[0], -item[1]))
        output: list[tuple[str, int]] = []
        cursor = 0
        for start, length, name, team_id in matches:
            if start < cursor:
                continue
            if start > cursor:
                output.append((segment[cursor:start], default_attr))
            output.append((name, self.team_name_attr(team_id)))
            cursor = start + length
        if cursor < len(segment):
            output.append((segment[cursor:], default_attr))
        return output

    def team_name_attr(self, team_id: str) -> int:
        if not curses.has_colors():
            return curses.A_BOLD
        if team_id == "ally":
            return curses.color_pair(ALLY_NAME_COLOR) | curses.A_BOLD
        if team_id == "enemy":
            return curses.color_pair(ENEMY_NAME_COLOR) | curses.A_BOLD
        return curses.color_pair(INFO_NAME_COLOR) | curses.A_BOLD

    def tag_attr(self, tag: str) -> int:
        if not curses.has_colors():
            return curses.A_NORMAL
        if tag in {"DMG", "DOT"}:
            return curses.color_pair(2)
        if tag in {"ACT", "SPD"}:
            return curses.color_pair(3)
        if tag in {"HEAL", "SHLD"}:
            return curses.color_pair(5)
        if tag in {"KILL", "ASP"}:
            return curses.color_pair(6)
        if tag in {"NRG", "ENG", "BUFF"}:
            return curses.color_pair(4)
        if tag in {"TURN", "SYS"}:
            return curses.color_pair(8) | curses.A_BOLD
        return curses.color_pair(7)

    def safe_addstr(
        self,
        win: curses.window,
        y: int,
        x: int,
        text: str,
        attr: int = 0,
        max_width: int | None = None,
        fill_width: int | None = None,
    ) -> None:
        max_y, max_x = win.getmaxyx()
        if y < 0 or y >= max_y or x < 0 or x >= max_x:
            return
        available_width = max_x - x
        if max_width is not None:
            available_width = min(available_width, max_width)
        rendered = fit_display_text(text, available_width)
        if fill_width is not None:
            rendered = fit_display_text(rendered, fill_width, pad=True)
        try:
            win.addstr(y, x, rendered, attr)
        except curses.error:
            return


def main() -> None:
    """Run the Chinese curses UI."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("请在支持方向键的交互式终端中运行：./abyss 或 abyss")
        return

    engine = BattleEngine(seed=7)
    save_path = DEFAULT_SAVE_PATH
    profile = PlayerProfile.load(save_path)
    ui = TerminalUI(engine=engine, profile=profile, save_path=save_path)
    curses.wrapper(ui.run)


if __name__ == "__main__":
    main()
