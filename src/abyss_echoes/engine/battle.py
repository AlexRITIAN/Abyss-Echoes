from __future__ import annotations

from collections import Counter
from dataclasses import replace
from random import Random
from typing import Any, Iterable

from abyss_echoes.engine.content_loader import load_heroes, load_items, load_skills
from abyss_echoes.engine.models import (
    BattleLogEntry,
    BattleResult,
    BattleRewards,
    BattleUnit,
    ItemDefinition,
    LootItem,
    SkillDefinition,
    StageEncounter,
    StatusEffect,
    UnitStats,
)
from abyss_echoes.i18n import (
    aspect_name,
    encounter_name,
    encounter_type_name,
    hero_name,
    localize_loot_name,
    position_name,
    role_name,
    skill_name,
    status_name,
    theme_name,
    threat_tag_name,
)

ENERGY_ON_BASIC = 25
ENERGY_ON_HIT = 5
ENERGY_ON_KILL = 15
MAX_ENERGY = 100
GAUGE_THRESHOLD = 1000
MAX_ROUNDS = 80
FATIGUE_START_ROUND = 9
FATIGUE_HP_BURN_PER_ROUND = 0.0
FATIGUE_DAMAGE_STEP = 0.11
FATIGUE_HEAL_REDUCTION_STEP = 0.05

LOOT_SLOTS = ["weapon", "helmet", "chest", "gloves", "pants", "boots", "amulet", "ring"]
RARITY_WEIGHTS = [("magic", 0.60), ("rare", 0.32), ("legendary", 0.08)]
SLOT_MAIN_STATS: dict[str, list[tuple[str, float | int, float | int]]] = {
    "weapon": [("atk", 18, 32), ("mag", 18, 32)],
    "helmet": [("max_hp", 100, 180), ("resist", 8, 18)],
    "chest": [("max_hp", 120, 220), ("armor", 10, 24)],
    "gloves": [("atk", 10, 20), ("crit_rate", 0.03, 0.08)],
    "pants": [("max_hp", 90, 180), ("armor", 8, 18)],
    "boots": [("speed", 8, 16), ("max_hp", 60, 120)],
    "amulet": [("mag", 12, 22), ("heal_bonus", 0.05, 0.14)],
    "ring": [("crit_rate", 0.03, 0.08), ("damage_bonus", 0.04, 0.12)],
}
AFFIX_POOL: list[tuple[str, float | int, float | int]] = [
    ("hp_pct", 0.05, 0.14),
    ("atk_pct", 0.05, 0.14),
    ("mag_pct", 0.05, 0.14),
    ("armor_flat", 6, 18),
    ("resist_flat", 6, 18),
    ("speed_flat", 4, 10),
    ("crit_rate", 0.02, 0.06),
    ("crit_damage", 0.08, 0.22),
    ("energy_gain_bonus", 0.04, 0.10),
    ("heal_bonus", 0.04, 0.12),
    ("shield_bonus", 0.04, 0.12),
    ("damage_vs_debuffed", 0.05, 0.14),
]
LEGENDARY_ASPECT_POOL = [
    "embers_feed_energy",
    "barrier_haste",
    "predator_fury",
    "saints_resolve",
]
RARITY_AFFIX_COUNT = {"magic": 1, "rare": 2, "legendary": 3}
RARITY_POWER_BONUS = {"magic": 0, "rare": 12, "legendary": 28}
STAGE_REWARD_GOLD_BONUS = 14
STAGE_REWARD_MATERIAL_BONUS = 1
STAGE_ITEM_POWER_BONUS = 4
STAGE_ENEMY_HP_STEP = 0.10
STAGE_ENEMY_DAMAGE_STEP = 0.08
STAGE_ENEMY_SPEED_STEP = 0.02
ELITE_HP_BONUS = 0.12
ELITE_DAMAGE_BONUS = 0.10
BOSS_HP_BONUS = 0.28
BOSS_DAMAGE_BONUS = 0.18
BOSS_SPEED_BONUS = 0.05
TARGETED_SLOT_WEIGHTS = {
    "tank": ["chest", "helmet", "pants", "boots", "weapon", "amulet", "ring", "gloves"],
    "melee_dps": ["weapon", "gloves", "boots", "ring", "chest", "helmet", "pants", "amulet"],
    "ranged_dps": ["weapon", "gloves", "ring", "boots", "amulet", "helmet", "pants", "chest"],
    "mage": ["weapon", "amulet", "ring", "boots", "gloves", "helmet", "pants", "chest"],
    "support": ["amulet", "boots", "ring", "weapon", "helmet", "chest", "pants", "gloves"],
}
THEME_AFFIX_BIAS = {
    "Frozen Court": ["speed_flat", "resist_flat", "energy_gain_bonus"],
    "Chrono Dragon Siege": ["energy_gain_bonus", "crit_rate", "speed_flat"],
    "Bulwark Phalanx": ["hp_pct", "armor_flat", "shield_bonus"],
    "Infernal Bombardment": ["damage_vs_debuffed", "crit_damage", "atk_pct"],
    "Assassin Volley": ["crit_rate", "speed_flat", "crit_damage"],
}
ROLE_RECOMMENDATION_DEFAULTS = {
    "tank": "steel_guardian",
    "melee_dps": "berserker",
    "ranged_dps": "hunter_ranger",
    "mage": "arcane_scholar",
    "support": "sacred_priest",
}

STAGE_THEME_ROTATION = [
    {
        "theme": "Bulwark Phalanx",
        "encounter_type": "normal",
        "name": "Iron Wall Patrol",
        "enemy_team": [
            {"hero_id": "temple_warden", "position": "frontline", "equipment_ids": ["guard_plate"]},
            {"hero_id": "thorn_brute", "position": "frontline"},
            {"hero_id": "war_song_bard", "position": "backline"},
            {"hero_id": "frost_witch", "position": "backline", "equipment_ids": ["ember_staff"]},
            {"hero_id": "repeater_engineer", "position": "backline", "equipment_ids": ["swift_boots"]},
        ],
    },
    {
        "theme": "Assassin Volley",
        "encounter_type": "normal",
        "name": "Night Ambush Cell",
        "enemy_team": [
            {"hero_id": "thorn_brute", "position": "frontline"},
            {"hero_id": "shadow_blade", "position": "frontline"},
            {"hero_id": "hunter_ranger", "position": "backline"},
            {"hero_id": "repeater_engineer", "position": "backline", "equipment_ids": ["swift_boots"]},
            {"hero_id": "war_song_bard", "position": "backline"},
        ],
    },
    {
        "theme": "Frozen Court",
        "encounter_type": "elite",
        "name": "Frostwitch Honor Guard",
        "enemy_team": [
            {"hero_id": "temple_warden", "position": "frontline", "equipment_ids": ["guard_plate"]},
            {"hero_id": "thorn_brute", "position": "frontline"},
            {"hero_id": "frost_witch", "position": "backline", "equipment_ids": ["ember_staff"]},
            {"hero_id": "void_hexer", "position": "backline"},
            {"hero_id": "war_song_bard", "position": "backline"},
        ],
    },
    {
        "theme": "Infernal Bombardment",
        "encounter_type": "normal",
        "name": "Demolition Battery",
        "enemy_team": [
            {"hero_id": "halberd_commander", "position": "frontline"},
            {"hero_id": "thorn_brute", "position": "frontline"},
            {"hero_id": "demolitionist", "position": "backline"},
            {"hero_id": "frost_witch", "position": "backline"},
            {"hero_id": "war_song_bard", "position": "backline"},
        ],
    },
    {
        "theme": "Chrono Dragon Siege",
        "encounter_type": "boss",
        "name": "Chrono Sage Ascendant",
        "enemy_team": [
            {"hero_id": "temple_warden", "position": "frontline", "equipment_ids": ["guard_plate"]},
            {"hero_id": "halberd_commander", "position": "frontline"},
            {"hero_id": "chrono_sage", "position": "backline"},
            {"hero_id": "void_hexer", "position": "backline"},
            {"hero_id": "demolitionist", "position": "backline"},
        ],
    },
]


_DOT_STATS = {
    "burn": ("灼烧", "max_hp"),
    "bleed": ("流血", "max_hp"),
    "erosion": ("腐蚀", "current_hp"),
}


class BattleEngine:
    def __init__(self, seed: int = 7) -> None:
        self.seed = seed
        self.random = Random(seed)
        self.heroes = load_heroes()
        self.skills = load_skills()
        self.items = load_items()
        self.logs: list[BattleLogEntry] = []
        self.current_round = 0
        self.analysis_state: dict[str, Any] = {}
        self._tracked_units: list[BattleUnit] = []

    def build_unit(
        self,
        hero_id: str,
        team_id: str,
        formation_index: int,
        position: str,
        equipment_ids: list[str] | None = None,
        hero_level: int = 1,
        specialization: str = "",
        skill_ranks: dict[str, int] | None = None,
    ) -> BattleUnit:
        hero = self.heroes[hero_id]
        equipped_items = self._resolve_items(equipment_ids or [])
        stats = self._build_stats(
            hero,
            equipped_items,
            hero_level=hero_level,
            specialization=specialization,
            skill_ranks=skill_ranks or {},
        )
        legendary_aspects = [item.legendary_aspect for item in equipped_items if item.legendary_aspect]
        return BattleUnit(
            unit_id=f"{team_id}_{formation_index}",
            team_id=team_id,
            formation_index=formation_index,
            position=position,
            hero=hero,
            stats=stats,
            current_hp=stats.max_hp,
            equipment_ids=[item.item_id for item in equipped_items],
            legendary_aspects=legendary_aspects,
            specialization=specialization,
            skill_ranks=dict(skill_ranks or {}),
        )

    def get_stage_encounter(self, stage: int) -> StageEncounter:
        stage = max(1, stage)
        template = STAGE_THEME_ROTATION[(stage - 1) % len(STAGE_THEME_ROTATION)]
        return StageEncounter(
            stage=stage,
            name=str(template["name"]),
            theme=str(template["theme"]),
            encounter_type=str(template["encounter_type"]),
            enemy_team=[dict(entry) for entry in template["enemy_team"]],
        )

    def describe_stage_encounter(self, stage: int) -> str:
        encounter = self.get_stage_encounter(stage)
        analysis = self.analyze_stage_encounter(stage)
        threat_tags = list(analysis["threat_tags"])
        return "\n".join(
            [
                f"第 {encounter.stage} 关",
                f"遭遇：{encounter_name(encounter.name)} [{encounter_type_name(encounter.encounter_type)}]",
                f"主题：{theme_name(encounter.theme)}",
                f"敌方阵容：{analysis['enemy_summary']}",
                f"威胁标签：{', '.join(threat_tag_name(tag) for tag in threat_tags) if threat_tags else '无'}",
            ]
        )

    def analyze_stage_encounter(self, stage: int):
        encounter = self.get_stage_encounter(stage)
        role_counts: Counter[str] = Counter()
        frontliners = 0
        backliners = 0
        enemy_labels: list[str] = []
        threat_tags: set[str] = set()
        enemy_mechanics: list[str] = []
        control_skills = {"freeze", "stun", "slow"}
        has_backline_pressure = False
        has_aoe_pressure = False
        has_energy_support = False
        has_shield_or_heal = False

        for entry in encounter.enemy_team:
            hero = self.heroes[str(entry["hero_id"])]
            role_counts[hero.role] += 1
            enemy_labels.append(f"{hero_name(hero.hero_id)}({role_name(hero.role)}/{position_name(str(entry['position']))})")
            if entry["position"] == "frontline":
                frontliners += 1
            else:
                backliners += 1
            skill_ids = [hero.basic_skill_id, hero.active_skill_id, hero.passive_skill_id]
            if any(
                effect.status_id in control_skills
                for skill_id in skill_ids
                for effect in self.skills[skill_id].effects
                if effect.status_id is not None
            ):
                threat_tags.add("control")
            for skill_id in skill_ids:
                skill = self.skills[skill_id]
                if skill.targeting == "enemy_backline":
                    has_backline_pressure = True
                if skill.targeting == "all_enemies":
                    has_aoe_pressure = True
                if any(effect.effect_type == "energy" or effect.effect_type == "action_gauge" for effect in skill.effects):
                    has_energy_support = True
                if any(effect.effect_type in {"heal", "shield"} for effect in skill.effects):
                    has_shield_or_heal = True

        burst_roles = role_counts.get("ranged_dps", 0) + role_counts.get("mage", 0)
        if burst_roles >= 2:
            threat_tags.add("high_burst")
        if role_counts.get("support", 0) >= 1:
            threat_tags.add("sustain")
        if frontliners >= 2 and role_counts.get("tank", 0) >= 1:
            threat_tags.add("frontline_wall")
        if encounter.encounter_type == "elite":
            threat_tags.add("elite_spike")
        if encounter.encounter_type == "boss":
            threat_tags.add("boss_pressure")
        if has_backline_pressure:
            threat_tags.add("backline_pressure")
            enemy_mechanics.append("敌方后排具有直切能力，会直接威胁我方后排。")
        if has_aoe_pressure:
            threat_tags.add("aoe_pressure")
            enemy_mechanics.append("敌方法师或爆破手拥有群体压制能力。")
        if has_energy_support:
            threat_tags.add("tempo_support")
            enemy_mechanics.append("敌方辅助会通过能量或行动条加速队伍节奏。")
        if has_shield_or_heal:
            enemy_mechanics.append("敌方存在治疗或护盾，战斗会被明显拉长。")
        if "control" in threat_tags:
            enemy_mechanics.append("敌方控制会通过减速、眩晕或冰冻拖慢我方节奏。")

        return {
            "stage": encounter.stage,
            "encounter_name": encounter.name,
            "encounter_type": encounter.encounter_type,
            "encounter_theme": encounter.theme,
            "enemy_summary": ", ".join(enemy_labels),
            "frontliners": frontliners,
            "backliners": backliners,
            "role_counts": dict(role_counts),
            "threat_tags": sorted(threat_tags),
            "enemy_mechanics": enemy_mechanics,
        }

    def generate_stage_recommendations(self, profile, stage: int) -> list[str]:
        analysis = self.analyze_stage_encounter(stage)
        party_roles = Counter(self.heroes[hero_id].role for hero_id, _position in profile.party)
        recommendations: list[str] = []

        if analysis["encounter_type"] == "boss":
            recommendations.append("首领关压力很高，建议预留更长的爆发窗口。")
        elif analysis["encounter_type"] == "elite":
            recommendations.append("精英关中段强度会明显抬升，需提前准备。")

        threat_tags = set(analysis["threat_tags"])
        if "high_burst" in threat_tags:
            recommendations.append("敌方爆发偏高，前排要够硬，避免脆皮后排暴露。")
        if "control" in threat_tags:
            recommendations.append("敌方带控制，速度属性和辅助稳定性会更重要。")
        if "backline_pressure" in threat_tags:
            recommendations.append("敌方会威胁后排，建议保护核心输出并提高先手干扰能力。")
        if "tempo_support" in threat_tags:
            recommendations.append("敌方有节奏支援，速度和爆发时机比平时更关键。")
        if "sustain" in threat_tags and party_roles.get("support", 0) == 0:
            recommendations.append("当前队伍没有辅助，面对敌方续航时会比较吃力。")
        if party_roles.get("tank", 0) == 0:
            recommendations.append("当前队伍没有坦克，建议先补回前排核心再推进。")
        if not recommendations:
            recommendations.append("当前阵容较稳定，优先提升装备和关卡成长战力即可。")
        return recommendations

    def build_enemy_team_for_stage(self, stage: int) -> list[BattleUnit]:
        encounter = self.get_stage_encounter(stage)
        enemy_team = []
        for idx, entry in enumerate(encounter.enemy_team, start=1):
            enemy_team.append(
                self.build_unit(
                    str(entry["hero_id"]),
                    "enemy",
                    idx,
                    str(entry["position"]),
                    equipment_ids=list(entry.get("equipment_ids", [])),
                )
            )
        self._apply_stage_scaling(enemy_team, stage, encounter.encounter_type)
        return enemy_team

    def run_stage_battle(self, allies: list[BattleUnit], stage: int, enemies: list[BattleUnit] | None = None) -> BattleResult:
        encounter = self.get_stage_encounter(stage)
        battle_enemies = enemies if enemies is not None else self.build_enemy_team_for_stage(stage)
        result = self.run_battle(allies, battle_enemies)
        if result.rewards is not None:
            result.rewards.gold += max(0, stage - 1) * STAGE_REWARD_GOLD_BONUS
            result.rewards.materials += max(0, stage - 1) * STAGE_REWARD_MATERIAL_BONUS
            party_roles = [unit.hero.role for unit in allies]
            party_hero_ids = [unit.hero.hero_id for unit in allies]
            for loot in result.rewards.loot:
                loot.item_power += max(0, stage - 1) * STAGE_ITEM_POWER_BONUS
                self._retarget_loot_item(
                    loot,
                    encounter_type=encounter.encounter_type,
                    encounter_theme=encounter.theme,
                    party_roles=party_roles,
                    party_hero_ids=party_hero_ids,
                )
        result.encounter_name = encounter.name
        result.encounter_type = encounter.encounter_type
        result.encounter_theme = encounter.theme
        result.enemy_summary = self._encounter_enemy_summary(encounter)
        return result

    def run_battle(self, allies: list[BattleUnit], enemies: list[BattleUnit]) -> BattleResult:
        self.logs = []
        self.current_round = 0
        self._tracked_units = [*allies, *enemies]
        self.analysis_state = {
            "damage_by_unit": Counter(),
            "healing_by_unit": Counter(),
            "skill_casts": Counter(),
            "action_order": [],
            "first_fall": "",
        }
        self._prime_opening_action_gauges(allies, enemies)
        rounds = 0
        while rounds < MAX_ROUNDS and self._team_alive(allies) and self._team_alive(enemies):
            rounds += 1
            self.current_round = rounds
            for unit in self._alive_units(allies, enemies):
                unit.action_gauge += self._effective_speed(unit)
            ready_units = sorted(
                [unit for unit in self._alive_units(allies, enemies) if unit.action_gauge >= GAUGE_THRESHOLD],
                key=lambda unit: (-unit.action_gauge, -self._effective_speed(unit), unit.formation_index),
            )
            if not ready_units:
                continue
            for actor in ready_units:
                if not actor.alive:
                    continue
                effective_speed = self._effective_speed(actor)
                actor_label = self._battle_unit_label(actor)
                self._append_log(
                    BattleLogEntry(
                        "TURN",
                        f"第 {rounds} 回合：{actor_label} 行动，速度 {effective_speed}，生命 {max(actor.current_hp, 0)}/{actor.stats.max_hp}，能量 {actor.energy}/{MAX_ENERGY}。",
                    )
                )
                self.analysis_state["action_order"].append(f"第{rounds}回合:{actor_label}@{effective_speed}")
                actor.action_gauge -= GAUGE_THRESHOLD
                self._process_start_of_action(actor)
                if not actor.alive:
                    continue
                if actor.has_status("stun") or actor.has_status("freeze"):
                    self._append_log(BattleLogEntry("CTRL", f"{actor_label} 无法行动。"))
                    self._decrement_statuses(actor)
                    continue
                friends = allies if actor.team_id == "ally" else enemies
                opponents = enemies if actor.team_id == "ally" else allies
                active_skill = self.skills[actor.hero.active_skill_id]
                if actor.energy >= active_skill.energy_cost and self._should_cast_active(actor, friends, opponents):
                    spent = active_skill.energy_cost
                    self._use_skill(actor, active_skill, friends, opponents)
                    actor.energy = max(0, actor.energy - active_skill.energy_cost)
                    self._append_log(BattleLogEntry("NRG", f"{actor_label} 消耗 {spent} 点能量，当前能量 {actor.energy}/{MAX_ENERGY}。"))
                else:
                    self._use_skill(actor, self.skills[actor.hero.basic_skill_id], friends, opponents)
                self._trigger_passive(actor, friends, opponents)
                self._decrement_statuses(actor)
                self._remove_dead(allies, enemies)
                if not self._team_alive(allies) or not self._team_alive(enemies):
                    break
        winner = self._determine_winner(allies, enemies)
        rewards = self._generate_rewards(winner == "ally")
        analysis = self._build_battle_analysis()
        return BattleResult(winner=winner, rounds=rounds, logs=self.logs, rewards=rewards, analysis=analysis)

    def _prime_opening_action_gauges(self, allies: list[BattleUnit], enemies: list[BattleUnit]) -> None:
        alive_units = self._alive_units(allies, enemies)
        if not alive_units:
            return
        fastest_speed = max((self._effective_speed(unit) for unit in alive_units), default=0)
        if fastest_speed <= 0:
            return
        while alive_units and not any(unit.action_gauge + self._effective_speed(unit) >= GAUGE_THRESHOLD for unit in alive_units):
            for unit in alive_units:
                unit.action_gauge += self._effective_speed(unit)
            alive_units = self._alive_units(allies, enemies)
    def _append_log(self, entry: BattleLogEntry) -> None:
        hp_snapshot = {unit.unit_id: max(unit.current_hp, 0) for unit in self._tracked_units}
        self.logs.append(BattleLogEntry(entry.tag, entry.message, hp_snapshot=hp_snapshot))

    def _battle_unit_label(self, unit: BattleUnit) -> str:
        team_label = "我方" if unit.team_id == "ally" else "敌方"
        return f"{hero_name(unit.hero.hero_id, unit.name)}（{team_label}{position_name(unit.position)}）"

    def _build_battle_analysis(self) -> dict[str, Any]:
        damage_counter: Counter[str] = self.analysis_state.get("damage_by_unit", Counter())
        healing_counter: Counter[str] = self.analysis_state.get("healing_by_unit", Counter())
        skill_counter: Counter[str] = self.analysis_state.get("skill_casts", Counter())
        action_order = list(self.analysis_state.get("action_order", []))[:6]
        top_damage = "无"
        if damage_counter:
            name, amount = damage_counter.most_common(1)[0]
            top_damage = f"{name} ({amount})"
        top_healing = "无"
        if healing_counter:
            name, amount = healing_counter.most_common(1)[0]
            top_healing = f"{name} ({amount})"
        skill_casts = [f"{name} ×{count}" for name, count in skill_counter.most_common(5)]
        reason_bits: list[str] = []
        first_fall = self.analysis_state.get("first_fall") or "无"
        if first_fall != "无":
            lower_fall = str(first_fall)
            if any(keyword in lower_fall for keyword in {"守护者", "守卫", "暴徒", "统领"}):
                reason_bits.append(f"{first_fall} 最先倒下，阵线很快被撕开。")
            else:
                reason_bits.append(f"{first_fall} 过早阵亡，后排承压明显。")
        if action_order:
            first_actor = action_order[0].split(":", 1)[-1]
            reason_bits.append(f"开局速度优势由 {first_actor} 抢到先手。")
        if top_healing != "无":
            reason_bits.append(f"{top_healing} 的治疗量显著影响了战斗节奏。")
        if top_damage != "无":
            reason_bits.append(f"{top_damage} 成为本场主要伤害来源。")
        reason_summary = " ".join(reason_bits[:3]) or "本场节奏较平稳，没有出现单一决定性拐点。"
        return {
            "top_damage": top_damage,
            "top_healing": top_healing,
            "first_fall": first_fall,
            "action_order_snapshot": action_order,
            "skill_casts": skill_casts,
            "reason_summary": reason_summary,
        }

    def generate_loot_item(
        self,
        victory: bool = True,
        encounter_type: str = "normal",
        encounter_theme: str = "",
        party_roles: list[str] | None = None,
        party_hero_ids: list[str] | None = None,
    ) -> LootItem:
        slot = self._choose_targeted_slot(party_roles or [])
        rarity = self._roll_rarity(victory, encounter_type=encounter_type)
        base_power = self.random.randint(100, 128) + RARITY_POWER_BONUS[rarity]
        main_stat_name, low, high = self.random.choice(SLOT_MAIN_STATS[slot])
        main_stat_value = self._roll_stat_value(low, high)
        affix_count = RARITY_AFFIX_COUNT[rarity]
        affixes = self._roll_affixes(affix_count, exclude={main_stat_name}, encounter_theme=encounter_theme)
        aspect = self.random.choice(LEGENDARY_ASPECT_POOL) if rarity == "legendary" else None
        item_id = f"loot_{slot}_{rarity}_{self.random.randint(1000, 9999)}"
        display_name = self._build_loot_name(slot, rarity, aspect)
        return LootItem(
            item_id=item_id,
            display_name=display_name,
            slot=slot,
            rarity=rarity,
            item_power=base_power,
            main_stat={main_stat_name: main_stat_value},
            affixes=affixes,
            legendary_aspect=aspect,
            recommended_hero_ids=self._recommend_heroes_for_loot(slot, main_stat_name, party_roles or [], party_hero_ids or []),
        )

    def _generate_rewards(self, victory: bool) -> BattleRewards:
        gold = self.random.randint(118, 168) if victory else self.random.randint(60, 96)
        materials = self.random.randint(3, 6) if victory else self.random.randint(1, 3)
        loot_count = 1 + (1 if victory and self.random.random() < 0.35 else 0)
        loot = [self.generate_loot_item(victory=victory) for _ in range(loot_count)]
        return BattleRewards(gold=gold, materials=materials, loot=loot)

    def _roll_rarity(self, victory: bool, encounter_type: str = "normal") -> str:
        roll = self.random.random()
        adjusted = roll if victory else min(0.98, roll + 0.12)
        if encounter_type == "elite":
            adjusted = max(0.08, adjusted - 0.10)
        elif encounter_type == "boss":
            adjusted = max(0.14, adjusted - 0.18)
        threshold = 0.0
        for rarity, weight in RARITY_WEIGHTS:
            threshold += weight
            if adjusted <= threshold:
                return rarity
        return "legendary"

    def _roll_stat_value(self, low: float | int, high: float | int) -> float | int:
        value = low + (high - low) * self.random.random()
        if isinstance(low, int) and isinstance(high, int):
            return int(round(value))
        return round(float(value), 2)

    def _roll_affixes(
        self,
        count: int,
        exclude: set[str],
        encounter_theme: str = "",
    ) -> list[dict[str, int | float | str]]:
        candidates = [entry for entry in AFFIX_POOL if entry[0] not in exclude]
        chosen: list[tuple[str, float | int, float | int]] = []
        theme_bias = [entry for entry in candidates if entry[0] in THEME_AFFIX_BIAS.get(encounter_theme, [])]
        if theme_bias:
            chosen.append(self.random.choice(theme_bias))
            candidates = [entry for entry in candidates if entry[0] != chosen[0][0]]
        remaining = min(count - len(chosen), len(candidates))
        if remaining > 0:
            chosen.extend(self.random.sample(candidates, k=remaining))
        affixes: list[dict[str, int | float | str]] = []
        for affix_type, low, high in chosen:
            affixes.append({"type": affix_type, "value": self._roll_stat_value(low, high)})
        return affixes

    def _choose_targeted_slot(self, party_roles: list[str]) -> str:
        for role in party_roles:
            weighted_slots = TARGETED_SLOT_WEIGHTS.get(role)
            if weighted_slots:
                return self.random.choice(weighted_slots[:4])
        return self.random.choice(LOOT_SLOTS)

    def _recommend_heroes_for_loot(
        self,
        slot: str,
        main_stat_name: str,
        party_roles: list[str],
        party_hero_ids: list[str],
    ) -> list[str]:
        if not party_hero_ids:
            role_to_heroes: dict[str, list[str]] = {role: [] for role in party_roles}
            for role in party_roles:
                default_hero = ROLE_RECOMMENDATION_DEFAULTS.get(role)
                if default_hero:
                    role_to_heroes.setdefault(role, []).append(default_hero)
            for hero_id, hero in self.heroes.items():
                if hero.role in role_to_heroes and not role_to_heroes[hero.role]:
                    role_to_heroes[hero.role].append(hero_id)
            recommended = [hero_ids[0] for hero_ids in role_to_heroes.values() if hero_ids]
            return recommended[:2]

        preferred_roles = self._preferred_roles_for_loot(slot, main_stat_name)
        recommended: list[str] = []
        for hero_id in party_hero_ids:
            hero = self.heroes[hero_id]
            if hero.role in preferred_roles:
                recommended.append(hero_id)
        if recommended:
            return recommended[:2]
        return party_hero_ids[:2]

    def _preferred_roles_for_loot(self, slot: str, main_stat_name: str) -> set[str]:
        if slot in {"chest", "helmet", "pants"} or main_stat_name in {"max_hp", "armor", "resist"}:
            return {"tank"}
        if slot in {"amulet"} or main_stat_name in {"heal_bonus"}:
            return {"support", "mage"}
        if slot in {"weapon"} and main_stat_name == "mag":
            return {"mage", "support"}
        if slot in {"weapon", "gloves", "ring"} or main_stat_name in {"atk", "crit_rate", "damage_bonus"}:
            return {"melee_dps", "ranged_dps"}
        if slot == "boots":
            return {"support", "ranged_dps", "mage"}
        return set()

    def _retarget_loot_item(
        self,
        loot: LootItem,
        encounter_type: str,
        encounter_theme: str,
        party_roles: list[str],
        party_hero_ids: list[str],
    ) -> None:
        if encounter_type == "boss" and loot.rarity == "magic":
            loot.rarity = "rare"
            loot.item_power += RARITY_POWER_BONUS["rare"]
        elif encounter_type == "elite" and loot.rarity == "magic" and self.random.random() < 0.5:
            loot.rarity = "rare"
            loot.item_power += RARITY_POWER_BONUS["rare"]
        if encounter_theme and not any(str(affix.get("type")) in THEME_AFFIX_BIAS.get(encounter_theme, []) for affix in loot.affixes):
            bias_type = self.random.choice(THEME_AFFIX_BIAS.get(encounter_theme, ["speed_flat"]))
            for affix_type, low, high in AFFIX_POOL:
                if affix_type == bias_type:
                    loot.affixes = [dict(loot.affixes[0])] if loot.affixes else []
                    loot.affixes.append({"type": affix_type, "value": self._roll_stat_value(low, high)})
                    break
        main_stat_name = next(iter(loot.main_stat.keys()))
        loot.recommended_hero_ids = self._recommend_heroes_for_loot(
            loot.slot,
            str(main_stat_name),
            party_roles,
            party_hero_ids,
        )

    def _build_loot_name(self, slot: str, rarity: str, aspect: str | None) -> str:
        prefix_map = {
            "magic": ["暮影", "铁铸", "雾辉", "灰烬"],
            "rare": ["风暴铸造", "王影", "夜璃", "烬醒"],
            "legendary": ["神话", "虚触", "圣誓", "龙醒"],
        }
        slot_names = {
            "weapon": "武器",
            "helmet": "头盔",
            "chest": "胸甲",
            "gloves": "护手",
            "pants": "腿甲",
            "boots": "战靴",
            "amulet": "护符",
            "ring": "戒指",
        }
        prefix = self.random.choice(prefix_map[rarity])
        suffix = "·余烬" if aspect == "embers_feed_energy" else ""
        return f"{prefix}{slot_names[slot]}{suffix}"

    def _determine_winner(self, allies: list[BattleUnit], enemies: list[BattleUnit]) -> str:
        ally_alive = self._team_alive(allies)
        enemy_alive = self._team_alive(enemies)
        if ally_alive and not enemy_alive:
            return "ally"
        if enemy_alive and not ally_alive:
            return "enemy"

        ally_score = sum(max(unit.current_hp, 0) + unit.shield for unit in allies)
        enemy_score = sum(max(unit.current_hp, 0) + unit.shield for unit in enemies)
        return "ally" if ally_score >= enemy_score else "enemy"

    def _fatigue_damage_bonus(self) -> float:
        if self.current_round <= FATIGUE_START_ROUND:
            return 0.0
        return (self.current_round - FATIGUE_START_ROUND) * FATIGUE_DAMAGE_STEP

    def _fatigue_heal_penalty(self) -> float:
        if self.current_round <= FATIGUE_START_ROUND:
            return 0.0
        return min(0.80, (self.current_round - FATIGUE_START_ROUND) * FATIGUE_HEAL_REDUCTION_STEP)

    def _resolve_items(self, equipment_ids: list[str]) -> list[ItemDefinition]:
        return [self.items[item_id] for item_id in equipment_ids if item_id in self.items]

    def _build_stats(
        self,
        hero,
        items: list[ItemDefinition],
        hero_level: int = 1,
        specialization: str = "",
        skill_ranks: dict[str, int] | None = None,
    ) -> UnitStats:
        stats = UnitStats(
            max_hp=hero.base_hp,
            atk=hero.base_atk,
            mag=hero.base_mag,
            armor=hero.base_armor,
            resist=hero.base_resist,
            speed=hero.base_speed,
            crit_rate=hero.base_crit_rate,
            crit_damage=hero.base_crit_damage,
        )
        self._apply_level_scaling(stats, hero_level)
        self._apply_skill_rank_scaling(stats, skill_ranks or {})
        self._apply_specialization_scaling(stats, hero.role, specialization)
        for item in items:
            self._apply_stat_block(stats, item.main_stat)
            for affix in item.affixes:
                self._apply_affix(stats, str(affix.get("type")), affix.get("value", 0))
        stats.max_hp = max(1, int(stats.max_hp))
        stats.atk = max(1, int(stats.atk))
        stats.mag = max(0, int(stats.mag))
        stats.armor = max(0, int(stats.armor))
        stats.resist = max(0, int(stats.resist))
        stats.speed = max(1, int(stats.speed))
        return stats

    def _apply_level_scaling(self, stats: UnitStats, hero_level: int) -> None:
        bonus_levels = max(0, int(hero_level) - 1)
        if bonus_levels == 0:
            return
        stats.max_hp = int(round(stats.max_hp * (1 + 0.08 * bonus_levels)))
        stats.atk = int(round(stats.atk * (1 + 0.05 * bonus_levels)))
        stats.mag = int(round(stats.mag * (1 + 0.05 * bonus_levels)))
        stats.armor += bonus_levels * 3
        stats.resist += bonus_levels * 3
        stats.speed += bonus_levels

    def _apply_skill_rank_scaling(self, stats: UnitStats, skill_ranks: dict[str, int]) -> None:
        basic_rank = max(1, int(skill_ranks.get("basic", 1)))
        active_rank = max(1, int(skill_ranks.get("active", 1)))
        passive_rank = max(1, int(skill_ranks.get("passive", 1)))
        stats.atk = int(round(stats.atk * (1 + 0.02 * (basic_rank - 1))))
        stats.mag = int(round(stats.mag * (1 + 0.03 * (active_rank - 1))))
        stats.max_hp = int(round(stats.max_hp * (1 + 0.03 * (passive_rank - 1))))

    def _apply_specialization_scaling(self, stats: UnitStats, role: str, specialization: str) -> None:
        if not specialization:
            return
        match specialization:
            case "bulwark":
                stats.max_hp = int(round(stats.max_hp * 1.12))
                stats.armor += 8
            case "sentinel":
                stats.max_hp = int(round(stats.max_hp * 1.06))
                stats.resist += 10
                stats.speed += 4
            case "slayer":
                stats.atk = int(round(stats.atk * 1.12))
                stats.crit_damage += 0.10
            case "duelist":
                stats.atk = int(round(stats.atk * 1.08))
                stats.speed += 6
                stats.crit_rate += 0.04
            case "deadeye":
                stats.atk = int(round(stats.atk * 1.10))
                stats.crit_rate += 0.05
            case "barrage":
                stats.atk = int(round(stats.atk * 1.06))
                stats.speed += 5
                stats.damage_bonus += 0.08
            case "spellweaver":
                stats.mag = int(round(stats.mag * 1.12))
                stats.damage_bonus += 0.10
            case "frostbound":
                stats.mag = int(round(stats.mag * 1.08))
                stats.resist += 8
                stats.speed += 3
            case "oracle":
                stats.mag = int(round(stats.mag * 1.08))
                stats.heal_bonus += 0.12
            case "chorister":
                stats.mag = int(round(stats.mag * 1.05))
                stats.energy_gain_bonus += 0.10
                stats.speed += 4
            case _:
                if role == "tank":
                    stats.max_hp = int(round(stats.max_hp * 1.04))

    def _apply_stat_block(self, stats: UnitStats, values: dict[str, int | float]) -> None:
        for key, value in values.items():
            amount = float(value)
            if key == "max_hp":
                stats.max_hp += int(amount)
            elif key == "atk":
                stats.atk += int(amount)
            elif key == "mag":
                stats.mag += int(amount)
            elif key == "armor":
                stats.armor += int(amount)
            elif key == "resist":
                stats.resist += int(amount)
            elif key == "speed":
                stats.speed += int(amount)
            elif key == "crit_rate":
                stats.crit_rate += amount
            elif key == "crit_damage":
                stats.crit_damage += amount
            elif key == "heal_bonus":
                stats.heal_bonus += amount
            elif key == "energy_gain_bonus":
                stats.energy_gain_bonus += amount
            elif key == "damage_bonus":
                stats.damage_bonus += amount
            elif key == "shield_bonus":
                stats.shield_bonus += amount

    def _apply_affix(self, stats: UnitStats, affix_type: str, value: int | float | str) -> None:
        amount = float(value)
        match affix_type:
            case "hp_pct":
                stats.max_hp = int(round(stats.max_hp * (1 + amount)))
            case "atk_pct":
                stats.atk = int(round(stats.atk * (1 + amount)))
            case "mag_pct":
                stats.mag = int(round(stats.mag * (1 + amount)))
            case "armor_flat":
                stats.armor += int(amount)
            case "resist_flat":
                stats.resist += int(amount)
            case "speed_flat":
                stats.speed += int(amount)
            case "crit_rate":
                stats.crit_rate += amount
            case "crit_damage":
                stats.crit_damage += amount
            case "energy_gain_bonus":
                stats.energy_gain_bonus += amount
            case "heal_bonus":
                stats.heal_bonus += amount
            case "shield_bonus":
                stats.shield_bonus += amount
            case "damage_vs_debuffed":
                stats.damage_vs_debuffed_bonus += amount
            case _:
                return

    def _apply_stage_scaling(self, units: list[BattleUnit], stage: int, encounter_type: str = "normal") -> None:
        if stage <= 1 and encounter_type == "normal":
            return
        hp_multiplier = 1 + max(0, stage - 1) * STAGE_ENEMY_HP_STEP
        damage_multiplier = 1 + max(0, stage - 1) * STAGE_ENEMY_DAMAGE_STEP
        speed_multiplier = 1 + max(0, stage - 1) * STAGE_ENEMY_SPEED_STEP
        if encounter_type == "elite":
            hp_multiplier += ELITE_HP_BONUS
            damage_multiplier += ELITE_DAMAGE_BONUS
        elif encounter_type == "boss":
            hp_multiplier += BOSS_HP_BONUS
            damage_multiplier += BOSS_DAMAGE_BONUS
            speed_multiplier += BOSS_SPEED_BONUS
        for unit in units:
            unit.stats.max_hp = int(round(unit.stats.max_hp * hp_multiplier))
            unit.current_hp = unit.stats.max_hp
            unit.stats.atk = int(round(unit.stats.atk * damage_multiplier))
            unit.stats.mag = int(round(unit.stats.mag * damage_multiplier))
            unit.stats.speed = int(round(unit.stats.speed * speed_multiplier))

    def _encounter_enemy_summary(self, encounter: StageEncounter) -> str:
        labels = []
        for entry in encounter.enemy_team:
            hero = self.heroes[str(entry["hero_id"])]
            labels.append(f"{hero_name(hero.hero_id)}({role_name(hero.role)}/{position_name(str(entry['position']))})")
        return ", ".join(labels)

    def _alive_units(self, allies: list[BattleUnit], enemies: list[BattleUnit]) -> list[BattleUnit]:
        return [unit for unit in [*allies, *enemies] if unit.alive]

    def _team_alive(self, units: Iterable[BattleUnit]) -> bool:
        return any(unit.alive for unit in units)

    def _effective_speed(self, unit: BattleUnit) -> int:
        speed = unit.stats.speed
        for status in unit.statuses:
            if status.duration <= 0:
                continue
            if status.status_id == "haste":
                speed = int(speed * (1 + status.magnitude))
            elif status.status_id == "slow":
                speed = int(speed * max(0.1, 1 - status.magnitude))
        return max(1, speed)

    def _should_cast_active(self, actor: BattleUnit, allies: list[BattleUnit], enemies: list[BattleUnit]) -> bool:
        role = actor.hero.role
        if role == "support":
            low_allies = [unit for unit in allies if unit.alive and unit.hp_ratio() < 0.65]
            return len(low_allies) >= 2 or any(unit.hp_ratio() < 0.45 for unit in allies if unit.alive)
        if role == "tank":
            return actor.hp_ratio() < 0.85 or len([unit for unit in allies if unit.alive and unit.position == "frontline"]) == 1
        if role == "mage":
            return len([unit for unit in enemies if unit.alive]) >= 3 or any(unit.has_status("burn") for unit in enemies if unit.alive)
        if role == "melee_dps":
            return any(unit.alive and unit.hp_ratio() < 0.45 for unit in enemies)
        if role == "ranged_dps":
            return any(unit.alive and unit.hp_ratio() < 0.55 for unit in enemies)
        return True

    def _ensure_analysis_state(self) -> None:
        if "skill_casts" not in self.analysis_state:
            self.analysis_state["damage_by_unit"] = Counter()
            self.analysis_state["healing_by_unit"] = Counter()
            self.analysis_state["skill_casts"] = Counter()
            self.analysis_state["action_order"] = []
            self.analysis_state["first_fall"] = ""

    def _use_skill(self, actor: BattleUnit, skill: SkillDefinition, allies: list[BattleUnit], enemies: list[BattleUnit]) -> None:
        self._ensure_analysis_state()
        targets = self._choose_targets(actor, skill, allies, enemies)
        actor_label = hero_name(actor.hero.hero_id, actor.name)
        skill_label = skill_name(skill.skill_id, skill.name)
        self._append_log(BattleLogEntry("ACT", f"{actor_label} 施放【{skill_label}】。"))
        self.analysis_state["skill_casts"][skill_label] += 1
        for effect in skill.effects:
            if self.random.random() > effect.chance:
                continue
            effect_targets = self._resolve_effect_targets(actor, effect, targets, allies, enemies)
            if effect.effect_type == "damage":
                for target in effect_targets:
                    self._apply_damage(actor, target, effect, skill)
                if skill.skill_type == "basic" and effect_targets:
                    before_energy = actor.energy
                    actor.energy = min(MAX_ENERGY, actor.energy + self._energy_with_bonus(actor, ENERGY_ON_BASIC))
                    if actor.energy != before_energy:
                        self._append_log(
                            BattleLogEntry(
                                "NRG",
                                f"{actor_label} 回复 {actor.energy - before_energy} 点能量，当前能量 {actor.energy}/{MAX_ENERGY}。",
                            )
                        )
            elif effect.effect_type == "heal":
                for target in effect_targets:
                    self._apply_heal(actor, target, effect)
            elif effect.effect_type == "shield":
                for target in effect_targets:
                    self._apply_shield(actor, target, effect)
            elif effect.effect_type == "status":
                for target in effect_targets:
                    self._apply_status(actor, target, effect)
            elif effect.effect_type == "energy":
                for target in effect_targets:
                    amount = int(effect.value or 0)
                    before_energy = target.energy
                    target.energy = min(MAX_ENERGY, target.energy + amount)
                    target_label = hero_name(target.hero.hero_id, target.name)
                    self._append_log(BattleLogEntry("ENG", f"{target_label} 获得 {amount} 点能量。"))
                    if target.energy != before_energy:
                        self._append_log(BattleLogEntry("NRG", f"{target_label} 当前能量提升至 {target.energy}/{MAX_ENERGY}。"))
            elif effect.effect_type == "action_gauge":
                for target in effect_targets:
                    amount = int(effect.value or 0)
                    target.action_gauge += amount
                    target_label = hero_name(target.hero.hero_id, target.name)
                    self._append_log(BattleLogEntry("SPD", f"{target_label} 获得 {amount} 点行动条。"))

    def _energy_with_bonus(self, actor: BattleUnit, amount: int) -> int:
        return int(round(amount * (1 + actor.stats.energy_gain_bonus)))

    def _resolve_effect_targets(self, actor, effect, chosen_targets, allies, enemies):
        if effect.target == "self":
            return [actor]
        if effect.target == "lowest_hp_ally":
            living = [unit for unit in allies if unit.alive]
            return [min(living, key=lambda unit: unit.hp_ratio())] if living else []
        if effect.target == "all_allies":
            return [unit for unit in allies if unit.alive]
        if effect.target == "all_enemies":
            return [unit for unit in enemies if unit.alive]
        return chosen_targets

    def _choose_targets(self, actor: BattleUnit, skill: SkillDefinition, allies: list[BattleUnit], enemies: list[BattleUnit]) -> list[BattleUnit]:
        if skill.targeting == "self":
            return [actor]
        if skill.targeting == "all_allies":
            return [unit for unit in allies if unit.alive]
        if skill.targeting == "lowest_hp_ally":
            living = [unit for unit in allies if unit.alive]
            return [min(living, key=lambda unit: unit.hp_ratio())] if living else []
        if skill.targeting == "all_enemies":
            return [unit for unit in enemies if unit.alive]
        if skill.targeting == "frontline_enemies":
            front = [unit for unit in enemies if unit.alive and unit.position == "frontline"]
            return front or [unit for unit in enemies if unit.alive]
        if skill.targeting == "enemy_backline":
            back = [unit for unit in enemies if unit.alive and unit.position == "backline"]
            if back:
                return [min(back, key=lambda unit: unit.hp_ratio())]
        if skill.targeting == "lowest_hp_enemy":
            living = [unit for unit in enemies if unit.alive]
            return [min(living, key=lambda unit: unit.hp_ratio())] if living else []
        frontline = [unit for unit in enemies if unit.alive and unit.position == "frontline"]
        valid = frontline or [unit for unit in enemies if unit.alive]
        return [min(valid, key=lambda unit: unit.hp_ratio())] if valid else []

    def _apply_damage(self, actor: BattleUnit, target: BattleUnit, effect, skill: SkillDefinition) -> None:
        if not target.alive:
            return
        actor_label = hero_name(actor.hero.hero_id, actor.name)
        target_label = hero_name(target.hero.hero_id, target.name)
        skill_label = skill_name(skill.skill_id, skill.name)
        ratio = float(effect.value if effect.value is not None else skill.ratio or 0)
        if skill.damage_type == "physical":
            base = actor.stats.atk * ratio
            mitigation = 100 / (100 + max(0, target.stats.armor))
        elif skill.damage_type == "magical":
            base = actor.stats.mag * ratio
            mitigation = 100 / (100 + max(0, target.stats.resist))
        else:
            base = (actor.stats.atk + actor.stats.mag) / 2 * ratio
            mitigation = 1.0
        damage_bonus = actor.stats.damage_bonus
        if any(status.duration > 0 for status in target.statuses):
            damage_bonus += actor.stats.damage_vs_debuffed_bonus
        damage_bonus += self._fatigue_damage_bonus()
        damage = int(base * mitigation * (1 + damage_bonus))
        if self.random.random() < actor.stats.crit_rate:
            damage = int(damage * actor.stats.crit_damage)
            crit_text = " crit"
        else:
            crit_text = ""
        shield_absorbed = min(target.shield, damage)
        if shield_absorbed:
            target.shield -= shield_absorbed
            damage -= shield_absorbed
        total_damage = shield_absorbed + damage
        target.current_hp -= damage
        self.analysis_state["damage_by_unit"][actor_label] += max(0, total_damage)
        shield_text = f"，其中 {shield_absorbed} 被护盾吸收" if shield_absorbed else ""
        crit_suffix = "（暴击）" if crit_text else ""
        self._append_log(
            BattleLogEntry("DMG", f"{actor_label} 的【{skill_label}】对 {target_label} 造成 {total_damage} 点伤害{shield_text}{crit_suffix}。")
        )
        if skill.skill_type != "basic":
            self._append_log(BattleLogEntry("ENG", f"{actor_label} 为【{skill_label}】消耗了 {skill.energy_cost} 点能量。"))
        if target.current_hp <= 0:
            target.alive = False
            if not self.analysis_state.get("first_fall"):
                self.analysis_state["first_fall"] = target_label
            before_energy = actor.energy
            actor.energy = min(MAX_ENERGY, actor.energy + ENERGY_ON_KILL)
            self._append_log(BattleLogEntry("KILL", f"{target_label} 被击倒。"))
            if actor.energy != before_energy:
                self._append_log(BattleLogEntry("NRG", f"{actor_label} 击杀回能 {actor.energy - before_energy}，当前能量 {actor.energy}/{MAX_ENERGY}。"))
        elif damage > 0:
            before_energy = target.energy
            target.energy = min(MAX_ENERGY, target.energy + ENERGY_ON_HIT)
            if target.energy != before_energy:
                self._append_log(BattleLogEntry("NRG", f"{target_label} 受击回能 {target.energy - before_energy}，当前能量 {target.energy}/{MAX_ENERGY}。"))
        self._trigger_on_hit_aspects(actor, target, skill)

    def _trigger_on_hit_aspects(self, actor: BattleUnit, target: BattleUnit, skill: SkillDefinition) -> None:
        if not target.alive and skill.skill_type == "basic":
            return
        actor_label = hero_name(actor.hero.hero_id, actor.name)
        if "embers_feed_energy" in actor.legendary_aspects and any(status.duration > 0 for status in target.statuses):
            actor.energy = min(100, actor.energy + 5)
            self._append_log(BattleLogEntry("ASP", f"{actor_label} 触发【{aspect_name('embers_feed_energy')}】，回复 5 点能量。"))
        if "barrier_haste" in actor.legendary_aspects and actor.shield > 0:
            actor.action_gauge += 60
            self._append_log(BattleLogEntry("ASP", f"{actor_label} 触发【{aspect_name('barrier_haste')}】，行动条推进 60。"))
        if "predator_fury" in actor.legendary_aspects and target.hp_ratio() < 0.5:
            actor.energy = min(100, actor.energy + 4)
            self._append_log(BattleLogEntry("ASP", f"{actor_label} 触发【{aspect_name('predator_fury')}】，回复 4 点能量。"))

    def _apply_heal(self, actor: BattleUnit, target: BattleUnit, effect) -> None:
        ratio = float(effect.value or 0)
        amount = int(actor.stats.mag * ratio * (1 + actor.stats.heal_bonus) * (1 - self._fatigue_heal_penalty()))
        if amount <= 0:
            return
        actor_label = hero_name(actor.hero.hero_id, actor.name)
        target_label = hero_name(target.hero.hero_id, target.name)
        target.current_hp = min(target.stats.max_hp, target.current_hp + amount)
        self.analysis_state["healing_by_unit"][actor_label] += amount
        self._append_log(BattleLogEntry("HEAL", f"{actor_label} 为 {target_label} 回复了 {amount} 点生命。"))
        if "saints_resolve" in actor.legendary_aspects and target.hp_ratio() < 0.5:
            shield = max(1, int(amount * 0.35))
            target.shield += shield
            self._append_log(BattleLogEntry("ASP", f"{target_label} 触发【{aspect_name('saints_resolve')}】，获得 {shield} 点护盾。"))

    def _apply_shield(self, actor: BattleUnit, target: BattleUnit, effect) -> None:
        ratio = float(effect.value or 0)
        amount = int(target.stats.max_hp * ratio * (1 + actor.stats.shield_bonus))
        if amount <= 0:
            return
        target_label = hero_name(target.hero.hero_id, target.name)
        target.shield += amount
        self._append_log(BattleLogEntry("SHLD", f"{target_label} 获得 {amount} 点护盾。"))

    def _apply_status(self, actor: BattleUnit, target: BattleUnit, effect) -> None:
        status = StatusEffect(
            status_id=effect.status_id or "unknown",
            source_unit_id=actor.unit_id,
            duration=effect.duration,
            magnitude=float(effect.value or 0),
        )
        target.statuses.append(status)
        target_label = hero_name(target.hero.hero_id, target.name)
        self._append_log(BattleLogEntry("BUFF", f"{target_label} 获得【{status_name(status.status_id)}】效果，持续 {status.duration} 次行动。"))

    def _process_start_of_action(self, actor: BattleUnit) -> None:
        actor_label = hero_name(actor.hero.hero_id, actor.name)
        for status in list(actor.statuses):
            if status.duration <= 0:
                continue
            dot_name, dot_base = _DOT_STATS.get(status.status_id, (None, None))
            if dot_name is None:
                continue
            if dot_base == "current_hp":
                damage = max(1, int(actor.current_hp * status.magnitude))
            else:
                damage = max(1, int(actor.stats.max_hp * status.magnitude))
            actor.current_hp -= damage
            self._append_log(BattleLogEntry("DOT", f"{actor_label} 因【{status_name(status.status_id)}】受到 {damage} 点伤害。"))
            if actor.current_hp <= 0:
                actor.alive = False
                if not self.analysis_state.get("first_fall"):
                    self.analysis_state["first_fall"] = actor_label
                self._append_log(BattleLogEntry("KILL", f"{actor_label} 被持续伤害击倒。"))
                break

    def _trigger_passive(self, actor: BattleUnit, allies: list[BattleUnit], enemies: list[BattleUnit]) -> None:
        passive_id = actor.hero.passive_skill_id
        if passive_id == "afterglow_blessing":
            return
        if passive_id == "murder_fervor" and any(not unit.alive and unit.current_hp <= 0 for unit in enemies):
            actor.energy = min(100, actor.energy + 5)
        if passive_id == "echo_of_encouragement":
            if any(unit.energy == 0 for unit in allies if unit.alive):
                actor.energy = min(100, actor.energy + 4)
        if passive_id == "armor_reverb":
            if actor.hp_ratio() < 0.7:
                actor.shield += 5

    def _decrement_statuses(self, actor: BattleUnit) -> None:
        refreshed: list[StatusEffect] = []
        for status in actor.statuses:
            if status.duration > 1:
                refreshed.append(replace(status, duration=status.duration - 1))
        actor.statuses = refreshed

    def _remove_dead(self, allies: list[BattleUnit], enemies: list[BattleUnit]) -> None:
        for unit in [*allies, *enemies]:
            if unit.current_hp <= 0:
                unit.alive = False


def build_demo_enemy_team(engine: BattleEngine) -> list[BattleUnit]:
    return engine.build_enemy_team_for_stage(stage=1)


def build_demo_teams(engine: BattleEngine) -> tuple[list[BattleUnit], list[BattleUnit]]:
    ally_team = [
        engine.build_unit("steel_guardian", "ally", 1, "frontline", equipment_ids=["swift_boots", "guard_plate"]),
        engine.build_unit("berserker", "ally", 2, "frontline"),
        engine.build_unit("hunter_ranger", "ally", 3, "backline"),
        engine.build_unit("arcane_scholar", "ally", 4, "backline", equipment_ids=["ember_staff"]),
        engine.build_unit("sacred_priest", "ally", 5, "backline"),
    ]
    enemy_team = build_demo_enemy_team(engine)
    return ally_team, enemy_team


def run_demo_battle(seed: int = 7) -> BattleResult:
    engine = BattleEngine(seed=seed)
    allies, enemies = build_demo_teams(engine)
    return engine.run_battle(allies, enemies)

