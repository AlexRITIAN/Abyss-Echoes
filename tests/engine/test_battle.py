import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

import abyss_echoes.cli as cli_module
from abyss_echoes.cli import (
    TerminalUI,
    battle_command_from_key,
    display_width,
    fit_display_text,
    render_codex_home,
    render_best_upgrades,
    render_hero_codex_detail,
    render_hero_detail,
    render_hero_recommendation,
    render_inventory_detail,
    render_inventory_management,
    render_item_codex_detail,
    render_menu,
    render_hero_specialization,
    render_heroes,
    render_party,
    render_stage,
    render_threat_summary,
    run_battle_session,
)
from abyss_echoes.engine.battle import BattleEngine, run_demo_battle
from abyss_echoes.engine.models import BattleRewards, LootItem, StatusEffect
from abyss_echoes.i18n import hero_name
from abyss_echoes.player.profile import PlayerProfile, create_default_profile


class HeadlessTerminalUI(TerminalUI):
    def render(self, stdscr) -> None:
        return


class FakeWindow:
    def __init__(self, keys: list[int] | None = None) -> None:
        self.keys = list(keys or [])
        self.nodelay_state: list[bool] = []

    def getch(self) -> int:
        if self.keys:
            return self.keys.pop(0)
        return -1

    def nodelay(self, enabled: bool) -> None:
        self.nodelay_state.append(enabled)


class FakeRenderWindow:
    def __init__(self, width: int = 20, height: int = 5) -> None:
        self.width = width
        self.height = height
        self.calls: list[tuple[int, int, str, int]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return (self.height, self.width)

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        self.calls.append((y, x, text, attr))


class FakeInputWindow:
    def __init__(self, key: int = ord("q")) -> None:
        self.key = key
        self.keypad_calls: list[bool] = []

    def keypad(self, enabled: bool) -> None:
        self.keypad_calls.append(enabled)

    def getch(self) -> int:
        return self.key


def test_demo_battle_produces_winner_and_logs() -> None:
    result = run_demo_battle(seed=7)
    assert result.winner in {"ally", "enemy"}
    assert result.rounds > 0
    assert result.logs
    assert any(entry.tag == "ACT" for entry in result.logs)


def test_demo_battle_is_deterministic_with_seed() -> None:
    result_a = run_demo_battle(seed=7)
    result_b = run_demo_battle(seed=7)
    assert result_a.winner == result_b.winner
    assert result_a.rounds == result_b.rounds
    assert [entry.message for entry in result_a.logs[:10]] == [entry.message for entry in result_b.logs[:10]]


def test_demo_battle_finishes_under_target_round_budget() -> None:
    result = run_demo_battle(seed=7)
    assert result.winner == "ally"
    assert result.rounds <= 45
    assert result.rewards is not None
    assert result.rewards.gold >= 100
    assert 1 <= len(result.rewards.loot) <= 2


def test_demo_battle_rewards_are_deterministic_with_seed() -> None:
    result_a = run_demo_battle(seed=7)
    result_b = run_demo_battle(seed=7)

    assert result_a.rewards is not None
    assert result_b.rewards is not None
    assert result_a.rewards.gold == result_b.rewards.gold
    assert result_a.rewards.materials == result_b.rewards.materials
    assert [loot.display_name for loot in result_a.rewards.loot] == [loot.display_name for loot in result_b.rewards.loot]


def test_demo_battle_turn_logs_show_speed_hp_and_energy() -> None:
    result = run_demo_battle(seed=7)

    turn_log = next(entry.message for entry in result.logs if entry.tag == "TURN")
    assert "回合：" in turn_log
    assert "速度 " in turn_log
    assert "生命 " in turn_log
    assert "能量 " in turn_log
    assert "/100" in turn_log
    assert "我方" in turn_log or "敌方" in turn_log


def test_battle_command_from_key_supports_skip_and_quit() -> None:
    assert battle_command_from_key(ord("s")) == "skip"
    assert battle_command_from_key(ord("S")) == "skip"
    assert battle_command_from_key(ord("q")) == "quit"
    assert battle_command_from_key(ord("Q")) == "quit"
    assert battle_command_from_key(ord("x")) is None


def test_display_width_counts_chinese_as_double_width() -> None:
    assert display_width("ABC") == 3
    assert display_width("全部英雄") == 8


def test_fit_display_text_avoids_splitting_double_width_characters() -> None:
    assert fit_display_text("全部英雄", 7) == "全部英"
    assert fit_display_text("全部英雄", 8) == "全部英雄"


def test_safe_addstr_pads_line_to_clear_old_content(tmp_path) -> None:
    ui = HeadlessTerminalUI(engine=BattleEngine(seed=7), profile=create_default_profile(), save_path=tmp_path / "save.json")
    window = FakeRenderWindow(width=20, height=5)

    ui.safe_addstr(window, 1, 1, "全部英雄", max_width=10, fill_width=10)

    assert window.calls[-1][2] == "全部英雄  "


def test_left_panel_lines_show_enemy_slots_and_hp_bars(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")

    lines = ui.left_panel_lines()
    joined = "\n".join(lines)
    allies = profile.build_team(engine)
    enemies = engine.build_enemy_team_for_stage(profile.current_stage)

    assert "我方队伍：" in joined
    assert "敌方队伍：" in joined
    assert "槽位" not in joined
    assert "- 1：" in joined
    assert hero_name(profile.party[0][0]) in joined
    assert hero_name(engine.get_stage_encounter(profile.current_stage).enemy_team[0]["hero_id"]) in joined
    assert f"{allies[0].current_hp}/{allies[0].stats.max_hp}" in joined
    assert f"{enemies[0].current_hp}/{enemies[0].stats.max_hp}" in joined


def test_left_panel_lines_use_live_battle_hp_when_battle_units_exist(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")
    allies = profile.build_team(engine)
    enemies = engine.build_enemy_team_for_stage(profile.current_stage)
    cast(Any, ui).current_battle_allies = allies
    cast(Any, ui).current_battle_enemies = enemies
    allies[0].current_hp -= 123
    enemies[0].current_hp -= 77

    joined = "\n".join(ui.left_panel_lines())

    assert f"{allies[0].current_hp}/{allies[0].stats.max_hp}" in joined
    assert f"{enemies[0].current_hp}/{enemies[0].stats.max_hp}" in joined


def test_left_panel_lines_show_compact_resources_and_situation_summary(tmp_path) -> None:
    ui = HeadlessTerminalUI(engine=BattleEngine(seed=7), profile=create_default_profile(), save_path=tmp_path / "save.json")

    joined = "\n".join(ui.left_panel_lines())

    assert "资源：金币 0 / 材料 0" in joined
    assert "局势：" in joined
    assert "主题：" not in joined


def test_play_battle_updates_left_panel_hp_during_playback(tmp_path, monkeypatch) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")
    ui.log_delay = 0
    window = FakeWindow()
    hp_timeline: list[tuple[int, ...]] = []
    original_render = ui.render
    original_render_battle_frame = ui.render_battle_frame

    def record_hp() -> None:
        if ui.current_battle_allies is not None:
            hp_timeline.append(tuple(unit.current_hp for unit in ui.current_battle_allies))

    def recording_render(stdscr) -> None:
        record_hp()
        original_render(stdscr)

    def recording_render_battle_frame(stdscr) -> None:
        record_hp()
        original_render_battle_frame(stdscr)

    monkeypatch.setattr(ui, "render", recording_render)
    monkeypatch.setattr(ui, "render_battle_frame", recording_render_battle_frame)

    ui.play_battle(cast(Any, window))

    assert hp_timeline
    baseline_team = create_default_profile().build_team(BattleEngine(seed=7))
    baseline_hp = tuple(unit.stats.max_hp for unit in baseline_team)
    assert hp_timeline[0] == baseline_hp
    assert any(snapshot != baseline_hp for snapshot in hp_timeline[1:])
    assert any(any(current_hp < max_hp for current_hp, max_hp in zip(snapshot, baseline_hp)) for snapshot in hp_timeline[1:])


def test_stage_battle_turn_logs_start_from_round_one() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()

    result = engine.run_stage_battle(profile.build_team(engine), stage=1)

    turn_logs = [entry.message for entry in result.logs if entry.tag == "TURN"]
    assert turn_logs
    assert turn_logs[0].startswith("第 1 回合：")


def test_play_battle_does_not_full_render_for_each_log_entry(tmp_path, monkeypatch) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")
    ui.log_delay = 0
    window = FakeWindow()
    render_calls: list[bool] = []
    incremental_calls: list[bool] = []

    monkeypatch.setattr(ui, "render", lambda stdscr: render_calls.append(True))
    monkeypatch.setattr(ui, "render_battle_frame", lambda stdscr: incremental_calls.append(True), raising=False)

    ui.play_battle(cast(Any, window))

    assert len(render_calls) == 2
    assert incremental_calls


def test_play_battle_appends_round_summary_and_danger_hint(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")
    ui.log_delay = 0

    ui.play_battle(cast(Any, FakeWindow()))

    assert any("回合摘要：" in line for _tag, line in ui.center_entries)
    assert any("危险提示：" in line for _tag, line in ui.center_entries)


def test_draw_log_line_uses_team_colors_for_names_across_tags(tmp_path, monkeypatch) -> None:
    ui = HeadlessTerminalUI(engine=BattleEngine(seed=7), profile=create_default_profile(), save_path=tmp_path / "save.json")
    window = FakeRenderWindow(width=120, height=6)
    cast(Any, ui).highlight_name_teams = {"钢铁守护者": "ally", "圣殿守卫": "enemy"}

    monkeypatch.setattr(cli_module.curses, "has_colors", lambda: True)
    monkeypatch.setattr(cli_module.curses, "color_pair", lambda pair_id: pair_id * 100)
    monkeypatch.setattr(cli_module.curses, "A_BOLD", 1)

    ui.draw_log_line(cast(Any, window), 1, 1, 100, "ACT", "钢铁守护者 对 圣殿守卫 施放【盾击】。")
    ui.draw_log_line(cast(Any, window), 2, 1, 100, "DMG", "钢铁守护者 的【盾击】对 圣殿守卫 造成 88 点伤害。")

    ally_calls = [call for call in window.calls if "钢铁守护者" in call[2]]
    enemy_calls = [call for call in window.calls if "圣殿守卫" in call[2]]

    assert ally_calls
    assert enemy_calls
    assert ally_calls[0][3] == ally_calls[-1][3]
    assert enemy_calls[0][3] == enemy_calls[-1][3]
    assert ally_calls[0][3] != enemy_calls[0][3]
    assert ally_calls[0][3] != ui.tag_attr("ACT")
    assert enemy_calls[0][3] != ui.tag_attr("DMG")


def test_run_uses_more_readable_non_default_blue_for_info_text(tmp_path, monkeypatch) -> None:
    ui = HeadlessTerminalUI(engine=BattleEngine(seed=7), profile=create_default_profile(), save_path=tmp_path / "save.json")
    window = FakeInputWindow()
    init_pair_calls: list[tuple[int, int, int]] = []

    monkeypatch.setattr(ui, "render", lambda stdscr: None)
    monkeypatch.setattr(cli_module.curses, "has_colors", lambda: True)
    monkeypatch.setattr(cli_module.curses, "curs_set", lambda _value: None)
    monkeypatch.setattr(cli_module.curses, "start_color", lambda: None)
    monkeypatch.setattr(cli_module.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(cli_module.curses, "init_pair", lambda pair_id, fg, bg: init_pair_calls.append((pair_id, fg, bg)))

    ui.run(cast(Any, window))

    pair_7_call = next(call for call in init_pair_calls if call[0] == 7)
    assert pair_7_call[1] != cli_module.curses.COLOR_BLUE


def test_codex_home_lists_hero_and_item_categories() -> None:
    text = render_codex_home(selected_index=1)

    assert "游戏百科" in text
    assert "角色图鉴" in text
    assert "> 装备图鉴" in text


def test_render_menu_groups_actions_by_category() -> None:
    text = render_menu()

    assert "操作菜单：" in text
    assert "【战斗】" in text
    assert "【队伍】" in text
    assert "【知识】" in text
    assert "【系统】" in text
    assert text.index("【战斗】") < text.index("开始战斗") < text.index("【队伍】")
    assert text.index("【队伍】") < text.index("队伍详情") < text.index("【知识】")
    assert text.index("【知识】") < text.index("游戏百科") < text.index("【系统】")


def test_hero_codex_detail_shows_base_stats_and_skills() -> None:
    text = render_hero_codex_detail("steel_guardian")

    assert "角色详情：钢铁守护者" in text
    assert "基础属性：" in text
    assert "技能：" in text
    assert "普攻：盾击" in text


def test_item_codex_detail_shows_main_stats_affixes_and_aspect() -> None:
    text = render_item_codex_detail("ember_staff")

    assert "装备详情：" in text
    assert "传奇" in text
    assert "主属性：" in text
    assert "词缀：" in text
    assert "传奇特效：余烬回能" in text


def test_item_codex_detail_uses_normalized_legendary_effect_labels() -> None:
    text = render_item_codex_detail("ember_staff")

    assert "传奇特效：余烬回能" in text
    assert "触发：攻击带有减益的目标时" in text
    assert "效果：回复 5 点能量。" in text
    assert text.index("传奇特效：余烬回能") < text.index("触发：攻击带有减益的目标时") < text.index("效果：回复 5 点能量。")


def test_terminal_ui_can_enter_and_exit_codex_views(tmp_path) -> None:
    ui = HeadlessTerminalUI(engine=BattleEngine(seed=7), profile=create_default_profile(), save_path=tmp_path / "save.json")

    ui.open_codex()
    assert ui.is_codex_active is True
    assert any("游戏百科" in line for _tag, line in ui.center_entries)

    ui.codex_enter()
    assert ui.codex_view == "heroes"
    assert any("角色详情：" in line for _tag, line in ui.center_entries)

    ui.codex_back()
    assert ui.codex_view == "root"

    ui.codex_back()
    assert ui.is_codex_active is False
    assert any("当前关卡：" in line for _tag, line in ui.center_entries)


def test_render_inventory_detail_shows_full_loot_information() -> None:
    loot = LootItem(
        item_id="loot_weapon_new",
        display_name="Nightglass Pike",
        slot="weapon",
        rarity="rare",
        item_power=132,
        main_stat={"atk": 30},
        affixes=[{"type": "crit_rate", "value": 0.06}],
        recommended_hero_ids=["berserker"],
    )

    text = render_inventory_detail(loot)

    assert "背包物品详情：夜璃 长枪" in text
    assert "编号：loot_weapon_new" in text
    assert "部位：武器" in text
    assert "主属性：" in text
    assert "攻击：30" in text
    assert "词缀：" in text
    assert "暴击率：6%" in text
    assert "推荐：狂战士" in text


def test_render_inventory_detail_uses_same_legendary_effect_labels_as_codex() -> None:
    loot = LootItem(
        item_id="loot_weapon_legendary",
        display_name="Emberwake Staff",
        slot="weapon",
        rarity="legendary",
        item_power=145,
        main_stat={"mag": 22},
        affixes=[{"type": "mag_pct", "value": 0.12}],
        legendary_aspect="embers_feed_energy",
        recommended_hero_ids=["arcane_scholar"],
    )

    text = render_inventory_detail(loot)

    assert "传奇特效：余烬回能" in text
    assert "触发：攻击带有减益的目标时" in text
    assert "效果：回复 5 点能量。" in text
    assert "推荐：奥术学者" in text


def test_render_inventory_management_shows_selected_item_and_hero() -> None:
    profile = create_default_profile()
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
        )
    )

    text = render_inventory_management(profile, selected_item_index=0, selected_hero_index=1)

    assert "装备管理" in text
    assert "> 夜璃 长枪" in text
    assert "目标英雄：狂战士" in text
    assert "按 Enter 将当前物品装备给目标英雄" in text


def test_render_inventory_management_uses_shared_inventory_and_shows_comparison_for_selected_hero() -> None:
    profile = create_default_profile()
    profile.hero_loadouts.setdefault("berserker", {})["weapon"] = LootItem(
        item_id="loot_weapon_old",
        display_name="Stormforged Pike",
        slot="weapon",
        rarity="magic",
        item_power=98,
        main_stat={"atk": 10},
        affixes=[],
        recommended_hero_ids=["berserker"],
    )
    profile.inventory.extend(
        [
            LootItem(
                item_id="loot_weapon_new",
                display_name="Nightglass Pike",
                slot="weapon",
                rarity="rare",
                item_power=132,
                main_stat={"atk": 30},
                affixes=[{"type": "crit_rate", "value": 0.06}],
                recommended_hero_ids=["berserker"],
            ),
            LootItem(
                item_id="loot_priest_only",
                display_name="Saintsworn Charm",
                slot="amulet",
                rarity="rare",
                item_power=128,
                main_stat={"heal_bonus": 0.12},
                affixes=[{"type": "energy_gain_bonus", "value": 0.08}],
                recommended_hero_ids=["sacred_priest"],
            ),
        ]
    )

    text = render_inventory_management(profile, selected_item_index=0, selected_hero_index=1)

    assert "> 夜璃 长枪" in text
    assert "圣誓 符坠" in text
    assert "评分对比：" in text
    assert "候选评分：" in text
    assert "当前装备评分：" in text
    assert "提升值：" in text
    assert "攻击：30 vs 10 (+20)" in text
    assert "词缀对比：" in text
    assert "暴击率：6% vs 0% (+6%)" in text
    assert "结论：" in text


def test_render_inventory_management_equipped_focus_shows_unequip_target() -> None:
    profile = create_default_profile()
    profile.hero_loadouts.setdefault("berserker", {})["weapon"] = LootItem(
        item_id="loot_weapon_old",
        display_name="Stormforged Pike",
        slot="weapon",
        rarity="magic",
        item_power=98,
        main_stat={"atk": 10},
        affixes=[],
        recommended_hero_ids=["berserker"],
    )

    text = render_inventory_management(profile, selected_hero_index=1, focus="equipped", selected_equipped_index=0)

    assert "当前视图：已装备" in text
    assert "已装备列表：" in text
    assert "Enter 卸下当前装备" in text
    assert "> 风暴铸造 长枪" in text


def test_render_inventory_management_shows_loot_verdict_panel_and_salvage_tab() -> None:
    profile = create_default_profile()
    profile.inventory.extend(
        [
            LootItem(
                item_id="loot_weapon_fire",
                display_name="Emberwake Staff",
                slot="weapon",
                rarity="legendary",
                item_power=150,
                main_stat={"mag": 24},
                affixes=[
                    {"type": "damage_bonus", "value": 0.12},
                    {"type": "energy_gain_bonus", "value": 0.08},
                ],
                legendary_aspect="embers_feed_energy",
                recommended_hero_ids=["arcane_scholar"],
            ),
            LootItem(
                item_id="loot_ring_junk",
                display_name="Iron Ring",
                slot="ring",
                rarity="magic",
                item_power=90,
                main_stat={"crit_rate": 0.01},
                affixes=[{"type": "heal_bonus", "value": 0.04}],
            ),
        ]
    )

    text = render_inventory_management(profile, selected_item_index=0, selected_hero_index=3)

    assert "掉落面板：" in text
    assert "推荐动作：" in text
    assert "待分解：1" in text
    assert "升级候选" in text or "条件保留" in text


def test_battle_summary_lines_include_loot_panel_summary(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()

    output = run_battle_session(engine, profile, save_path=tmp_path / "profile.json")

    assert "掉落决策：" in output
    assert "静默垃圾" in output


def test_inventory_enter_auto_salvages_salvage_candidate_item(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    save_path = tmp_path / "save.json"
    profile = create_default_profile()
    salvage_item = LootItem(
        item_id="loot_ring_junk",
        display_name="Iron Ring",
        slot="ring",
        rarity="magic",
        item_power=90,
        main_stat={"crit_rate": 0.01},
        affixes=[{"type": "heal_bonus", "value": 0.04}],
    )
    profile.inventory.append(salvage_item)
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=save_path)
    ui.open_inventory_manager()

    ui.inventory_enter()

    assert not profile.inventory
    assert profile.materials >= 1
    assert any("已标记并分解" in line for _tag, line in ui.center_entries)



def test_inventory_management_shows_workshop_hint_for_actionable_item() -> None:
    profile = create_default_profile()
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_fire",
            display_name="Emberwake Staff",
            slot="weapon",
            rarity="legendary",
            item_power=150,
            main_stat={"mag": 24},
            affixes=[
                {"type": "damage_bonus", "value": 0.12},
                {"type": "energy_gain_bonus", "value": 0.08},
            ],
            legendary_aspect="embers_feed_energy",
            recommended_hero_ids=["arcane_scholar"],
        )
    )

    text = render_inventory_management(profile, selected_item_index=0, selected_hero_index=3)

    assert "工坊" in text
    assert "W" in text



def test_inventory_apply_workshop_strengthen_updates_item_in_place_and_saves(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    save_path = tmp_path / "save.json"
    profile = create_default_profile()
    item = LootItem(
        item_id="loot_weapon_fire",
        display_name="Emberwake Staff",
        slot="weapon",
        rarity="legendary",
        item_power=150,
        main_stat={"mag": 24},
        affixes=[
            {"type": "damage_bonus", "value": 0.12},
            {"type": "energy_gain_bonus", "value": 0.08},
        ],
        legendary_aspect="embers_feed_energy",
        recommended_hero_ids=["arcane_scholar"],
    )
    profile.inventory.append(item)
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=save_path)
    ui.open_inventory_manager()

    ui.inventory_apply_workshop_action()

    assert profile.inventory[0].strengthen_level == 1
    assert profile.inventory[0].item_power > 150
    reloaded = PlayerProfile.load(save_path)
    assert reloaded.inventory[0].strengthen_level == 1
    assert any("强化" in line for _tag, line in ui.center_entries)



def test_inventory_apply_workshop_extract_removes_item_and_records_aspect(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    save_path = tmp_path / "save.json"
    profile = create_default_profile()
    item = LootItem(
        item_id="loot_extract_me",
        display_name="Predator Fang",
        slot="ring",
        rarity="legendary",
        item_power=105,
        main_stat={"crit_rate": 0.01},
        affixes=[{"type": "thorns", "value": 0.01}],
        legendary_aspect="predator_fury",
    )
    profile.inventory.append(item)
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=save_path)
    ui.open_inventory_manager()

    ui.inventory_apply_workshop_action()

    assert not profile.inventory
    assert "predator_fury" in profile.extracted_aspects
    reloaded = PlayerProfile.load(save_path)
    assert "predator_fury" in reloaded.extracted_aspects
    assert any("萃取" in line for _tag, line in ui.center_entries)



def test_quitting_during_battle_saves_without_clearing_stage(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    save_path = tmp_path / "save.json"
    profile = create_default_profile()
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=save_path)
    ui.log_delay = 0
    window = FakeWindow(keys=[ord("q")])

    ui.play_battle(window)

    assert ui.should_exit is True
    assert profile.current_stage == 1
    assert profile.highest_stage_unlocked == 1
    assert profile.gold == 0
    assert profile.materials == 0
    saved = PlayerProfile.load(save_path)
    assert saved.current_stage == 1
    assert saved.highest_stage_unlocked == 1
    assert saved.gold == 0


def test_generate_loot_item_returns_valid_equipment() -> None:
    engine = BattleEngine(seed=7)

    loot = engine.generate_loot_item(victory=True)

    assert loot.slot in {"weapon", "helmet", "chest", "gloves", "pants", "boots", "amulet", "ring"}
    assert loot.rarity in {"magic", "rare", "legendary"}
    assert loot.item_power >= 100
    assert loot.main_stat
    assert loot.display_name
    assert 1 <= len(loot.affixes) <= 3


def test_build_unit_applies_equipment_main_stats_and_affixes() -> None:
    engine = BattleEngine(seed=7)

    unit = engine.build_unit(
        "steel_guardian",
        team_id="ally",
        formation_index=1,
        position="frontline",
        equipment_ids=["swift_boots", "guard_plate"],
    )

    assert unit.stats.max_hp == 1580
    assert unit.current_hp == 1580
    assert unit.stats.armor == 80
    assert unit.stats.speed == 114
    assert unit.stats.energy_gain_bonus == 0.08
    assert unit.stats.shield_bonus == 0.10
    assert unit.equipment_ids == ["swift_boots", "guard_plate"]


def test_legendary_aspect_embers_feed_energy_on_debuffed_hit() -> None:
    engine = BattleEngine(seed=7)
    actor = engine.build_unit(
        "arcane_scholar",
        team_id="ally",
        formation_index=1,
        position="backline",
        equipment_ids=["ember_staff"],
    )
    target = engine.build_unit(
        "thorn_brute",
        team_id="enemy",
        formation_index=1,
        position="frontline",
    )
    target.statuses.append(
        StatusEffect(
            status_id="burn",
            source_unit_id=actor.unit_id,
            duration=2,
            magnitude=0.05,
        )
    )

    basic_skill = engine.skills[actor.hero.basic_skill_id]
    actor.energy = 0
    engine._use_skill(actor, basic_skill, [actor], [target])

    assert actor.energy == 30
    assert actor.legendary_aspects == ["embers_feed_energy"]


def test_player_profile_collects_rewards_into_inventory() -> None:
    profile = create_default_profile()
    rewards = BattleRewards(
        gold=125,
        materials=4,
        loot=[
            LootItem(
                item_id="loot_ring_1001",
                display_name="Stormforged Ring",
                slot="ring",
                rarity="rare",
                item_power=120,
                main_stat={"crit_rate": 0.05},
                affixes=[{"type": "crit_damage", "value": 0.14}],
            )
        ],
    )

    profile.collect_rewards(rewards)

    assert profile.gold == 125
    assert profile.materials == 4
    assert profile.inventory[0].display_name == "Stormforged Ring"


def test_player_profile_equip_item_moves_it_from_inventory_to_hero_loadout() -> None:
    profile = create_default_profile()
    loot = LootItem(
        item_id="loot_boots_1001",
        display_name="Emberwake Treads",
        slot="boots",
        rarity="rare",
        item_power=122,
        main_stat={"speed": 14},
        affixes=[{"type": "energy_gain_bonus", "value": 0.08}],
    )
    profile.inventory.append(loot)

    profile.equip_item("steel_guardian", loot.item_id)

    assert not profile.inventory
    assert profile.hero_loadouts["steel_guardian"]["boots"].item_id == loot.item_id


def test_player_profile_unequip_item_returns_it_to_inventory() -> None:
    profile = create_default_profile()
    loot = LootItem(
        item_id="loot_chest_1002",
        display_name="Nightglass Cuirass",
        slot="chest",
        rarity="rare",
        item_power=126,
        main_stat={"max_hp": 160},
        affixes=[{"type": "shield_bonus", "value": 0.10}],
    )
    profile.hero_loadouts.setdefault("steel_guardian", {})["chest"] = loot

    returned = profile.unequip_item("steel_guardian", "chest")

    assert returned.item_id == loot.item_id
    assert profile.inventory[0].item_id == loot.item_id
    assert "chest" not in profile.hero_loadouts["steel_guardian"]


def test_player_profile_build_team_uses_equipped_item_ids() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    loot = LootItem(
        item_id="loot_boots_1001",
        display_name="Emberwake Treads",
        slot="boots",
        rarity="rare",
        item_power=122,
        main_stat={"speed": 14},
        affixes=[{"type": "energy_gain_bonus", "value": 0.08}],
    )
    profile.inventory.append(loot)
    profile.equip_item("steel_guardian", loot.item_id)

    team = profile.build_team(engine)

    steel_guardian = next(unit for unit in team if unit.hero.hero_id == "steel_guardian")
    assert loot.item_id in steel_guardian.equipment_ids


def test_player_profile_round_trips_through_dict_serialization() -> None:
    profile = create_default_profile()
    loot = LootItem(
        item_id="loot_amulet_3001",
        display_name="Saintsworn Amulet",
        slot="amulet",
        rarity="legendary",
        item_power=145,
        main_stat={"heal_bonus": 0.11},
        affixes=[{"type": "heal_bonus", "value": 0.09}],
        legendary_aspect="saints_resolve",
    )
    profile.inventory.append(loot)
    profile.equip_item("sacred_priest", loot.item_id)
    profile.gold = 250
    profile.materials = 9

    payload = profile.to_dict()
    restored = PlayerProfile.from_dict(payload)

    assert restored.gold == 250
    assert restored.materials == 9
    assert restored.hero_loadouts["sacred_priest"]["amulet"].display_name == "Saintsworn Amulet"
    assert restored.party == profile.party


def test_player_profile_save_and_load_json_file(tmp_path) -> None:
    profile = create_default_profile()
    loot = LootItem(
        item_id="loot_ring_4002",
        display_name="Nightglass Ring",
        slot="ring",
        rarity="rare",
        item_power=123,
        main_stat={"crit_rate": 0.06},
        affixes=[{"type": "crit_damage", "value": 0.18}],
    )
    profile.inventory.append(loot)
    profile.gold = 180
    path = tmp_path / "profile.json"

    profile.save(path)
    loaded = PlayerProfile.load(path)

    assert path.exists()
    assert loaded.gold == 180
    assert loaded.inventory[0].item_id == loot.item_id


def test_player_profile_load_returns_default_when_file_missing(tmp_path) -> None:
    path = tmp_path / "missing-profile.json"

    loaded = PlayerProfile.load(path)

    assert loaded.gold == 0
    assert loaded.materials == 0
    assert loaded.party == create_default_profile().party


def test_execute_action_can_reset_save_to_default_profile(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    save_path = tmp_path / "save.json"
    profile = create_default_profile()
    profile.gold = 321
    profile.materials = 17
    profile.current_stage = 3
    profile.highest_stage_unlocked = 4
    profile.save(save_path)
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=save_path)
    ui.menu_index = next(index for index, action in enumerate(cli_module.MENU_ACTIONS) if action.action_id == "reset_save")

    assert ui.execute_action(cast(Any, FakeWindow())) is True
    assert ui.profile.gold == 0
    assert ui.profile.materials == 0
    assert ui.profile.current_stage == 1
    assert ui.profile.highest_stage_unlocked == 1
    assert any("已重置存档" in line for _tag, line in ui.center_entries)

    saved = PlayerProfile.load(save_path)
    assert saved.gold == 0
    assert saved.materials == 0
    assert saved.current_stage == 1
    assert saved.highest_stage_unlocked == 1


def test_player_profile_save_writes_json_shape(tmp_path) -> None:
    profile = create_default_profile()
    path = tmp_path / "profile.json"

    profile.save(path)
    payload = json.loads(path.read_text())

    assert payload["gold"] == 0
    assert payload["materials"] == 0
    assert isinstance(payload["inventory"], list)
    assert isinstance(payload["hero_loadouts"], dict)
    assert isinstance(payload["party"], list)


def test_execute_action_can_open_inventory_management_mode(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
        )
    )
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")
    ui.menu_index = next(index for index, action in enumerate(cli_module.MENU_ACTIONS) if action.action_id == "inventory")

    assert ui.execute_action(cast(Any, FakeWindow())) is True
    assert getattr(ui, "is_inventory_active", False) is True
    assert any("装备管理" in line for _tag, line in ui.center_entries)


def test_stage_scaled_enemy_team_gets_stronger_on_higher_stage() -> None:
    engine = BattleEngine(seed=7)

    stage_1 = engine.build_enemy_team_for_stage(stage=1)
    stage_5 = engine.build_enemy_team_for_stage(stage=5)

    assert sum(unit.stats.max_hp for unit in stage_5) > sum(unit.stats.max_hp for unit in stage_1)
    assert sum(unit.stats.atk + unit.stats.mag for unit in stage_5) > sum(unit.stats.atk + unit.stats.mag for unit in stage_1)


def test_stage_battle_rewards_scale_with_stage() -> None:
    engine = BattleEngine(seed=7)
    allies = create_default_profile().build_team(engine)

    result_stage_1 = engine.run_stage_battle(allies, stage=1)
    result_stage_4 = engine.run_stage_battle(allies, stage=4)

    assert result_stage_1.rewards is not None
    assert result_stage_4.rewards is not None
    assert result_stage_4.rewards.gold >= 100
    assert result_stage_4.rewards.materials >= 3
    assert all(loot.item_power >= 112 for loot in result_stage_4.rewards.loot)


def test_player_profile_progresses_stage_after_stage_victory() -> None:
    profile = create_default_profile()

    advanced = profile.record_stage_result(stage=1, victory=True)

    assert advanced is True
    assert profile.current_stage == 2
    assert profile.highest_stage_unlocked == 2


def test_player_profile_does_not_advance_stage_on_failure() -> None:
    profile = create_default_profile()

    advanced = profile.record_stage_result(stage=1, victory=False)

    assert advanced is False
    assert profile.current_stage == 1
    assert profile.highest_stage_unlocked == 1


def test_player_profile_stage_state_persists_in_save_file(tmp_path) -> None:
    profile = create_default_profile()
    profile.current_stage = 3
    profile.highest_stage_unlocked = 4
    path = tmp_path / "profile.json"

    profile.save(path)
    loaded = PlayerProfile.load(path)

    assert loaded.current_stage == 3
    assert loaded.highest_stage_unlocked == 4


def test_player_profile_roster_lines_include_active_and_bench_heroes() -> None:
    profile = create_default_profile()

    lines = profile.roster_lines()

    assert any("钢铁守护者" in line and "上阵" in line for line in lines)
    assert any("影刃" in line and "待命" in line for line in lines)
    assert len(lines) == 15


def test_player_profile_can_assign_bench_hero_into_party() -> None:
    profile = create_default_profile()

    profile.assign_party_member("shadow_blade", "frontline", slot_index=1)

    assert profile.party[1] == ("shadow_blade", "frontline")
    assert all(hero_id != "shadow_blade" for idx, (hero_id, _pos) in enumerate(profile.party) if idx != 1)


def test_player_profile_rejects_too_many_frontliners() -> None:
    profile = create_default_profile()

    profile.assign_party_member("shadow_blade", "frontline", slot_index=1)

    try:
        profile.move_party_member("hunter_ranger", "frontline")
    except ValueError as exc:
        assert "frontline limit" in str(exc)
    else:
        raise AssertionError("expected frontline validation error")


def test_player_profile_swap_party_positions_keeps_formation_valid() -> None:
    profile = create_default_profile()

    profile.swap_party_positions("berserker", "hunter_ranger")

    assert ("berserker", "backline") in profile.party
    assert ("hunter_ranger", "frontline") in profile.party


def test_player_profile_party_state_persists_in_save_file(tmp_path) -> None:
    profile = create_default_profile()
    profile.assign_party_member("shadow_blade", "frontline", slot_index=1)
    profile.move_party_member("hunter_ranger", "backline")
    path = tmp_path / "profile.json"

    profile.save(path)
    loaded = PlayerProfile.load(path)

    assert loaded.party[1] == ("shadow_blade", "frontline")
    assert any(hero_id == "hunter_ranger" and position == "backline" for hero_id, position in loaded.party)


def test_stage_encounter_templates_mark_elite_and_boss_fights() -> None:
    engine = BattleEngine(seed=7)

    stage_2 = engine.get_stage_encounter(stage=2)
    stage_3 = engine.get_stage_encounter(stage=3)
    stage_5 = engine.get_stage_encounter(stage=5)

    assert stage_2.encounter_type == "normal"
    assert stage_3.encounter_type == "elite"
    assert stage_5.encounter_type == "boss"
    assert stage_5.name
    assert len(stage_5.enemy_team) == 5


def test_stage_encounter_summary_mentions_theme_and_enemy_roles() -> None:
    engine = BattleEngine(seed=7)

    summary = engine.describe_stage_encounter(stage=4)

    assert "第 4 关" in summary
    assert "主题：" in summary
    assert "遭遇：" in summary
    assert "敌方阵容：" in summary


def test_run_stage_battle_attaches_encounter_metadata_to_battle_result() -> None:
    engine = BattleEngine(seed=7)
    allies = create_default_profile().build_team(engine)

    result = engine.run_stage_battle(allies, stage=5)

    assert result.encounter_name
    assert result.encounter_type == "boss"
    assert result.enemy_summary


def test_render_stage_includes_current_stage_encounter_preview() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.current_stage = 5
    profile.highest_stage_unlocked = 5

    rendered = render_stage(profile, engine)

    assert "当前关卡：5" in rendered
    assert "遭遇：" in rendered
    assert "首领" in rendered
    assert "敌方阵容：" in rendered


def test_run_battle_session_output_includes_encounter_label(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.current_stage = 3
    profile.highest_stage_unlocked = 3

    output = run_battle_session(engine, profile, save_path=tmp_path / "profile.json")

    assert "第 3 关" in output
    assert "遭遇：" in output
    assert "精英" in output


def test_stage_analysis_includes_threat_tags() -> None:
    engine = BattleEngine(seed=7)

    analysis = engine.analyze_stage_encounter(stage=5)

    assert analysis["encounter_type"] == "boss"
    assert "high_burst" in analysis["threat_tags"]
    assert "boss_pressure" in analysis["threat_tags"]
    assert analysis["frontliners"] == 2
    assert analysis["backliners"] == 3


def test_player_profile_party_summary_reports_role_balance() -> None:
    profile = create_default_profile()

    summary = profile.party_summary()

    assert "前排=2/2" in summary
    assert "后排=3/3" in summary
    assert "坦克=1" in summary
    assert "辅助=1" in summary


def test_stage_recommendations_mention_missing_support_tools() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.assign_party_member("shadow_blade", "backline", slot_index=4)

    recommendations = engine.generate_stage_recommendations(profile, stage=5)

    assert any("辅助" in line for line in recommendations)
    assert any("首领" in line for line in recommendations)


def test_render_stage_includes_party_summary_and_recommendations() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.current_stage = 5
    profile.highest_stage_unlocked = 5

    rendered = render_stage(profile, engine)

    assert "队伍摘要：" in rendered
    assert "推荐策略：" in rendered
    assert "威胁标签：" in rendered


def test_run_battle_session_includes_prebattle_advice_block(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.current_stage = 5
    profile.highest_stage_unlocked = 5

    output = run_battle_session(engine, profile, save_path=tmp_path / "profile.json")

    assert "战前分析：" in output
    assert "推荐策略：" in output
    assert "威胁标签：" in output


def test_player_profile_collects_hero_xp_and_levels_up() -> None:
    profile = create_default_profile()

    progress = profile.add_hero_xp("steel_guardian", 260)

    assert progress["levels_gained"] >= 1
    assert profile.hero_progress["steel_guardian"]["level"] >= 2
    assert profile.hero_progress["steel_guardian"]["xp"] >= 0


def test_build_team_applies_hero_level_scaling() -> None:
    engine = BattleEngine(seed=7)
    base_profile = create_default_profile()
    leveled_profile = create_default_profile()
    leveled_profile.hero_progress["steel_guardian"]["level"] = 4

    base_unit = next(unit for unit in base_profile.build_team(engine) if unit.hero.hero_id == "steel_guardian")
    leveled_unit = next(unit for unit in leveled_profile.build_team(engine) if unit.hero.hero_id == "steel_guardian")

    assert leveled_unit.stats.max_hp > base_unit.stats.max_hp
    assert leveled_unit.stats.atk >= base_unit.stats.atk
    assert leveled_unit.stats.armor >= base_unit.stats.armor


def test_player_profile_hero_progress_persists_in_save_file(tmp_path) -> None:
    profile = create_default_profile()
    profile.add_hero_xp("arcane_scholar", 180)
    path = tmp_path / "profile.json"

    profile.save(path)
    loaded = PlayerProfile.load(path)

    assert loaded.hero_progress["arcane_scholar"]["level"] >= 2
    assert "hero_progress" in json.loads(path.read_text())


def test_render_heroes_lists_scannable_role_equipment_and_upgrade_summary() -> None:
    profile = create_default_profile()
    profile.add_hero_xp("steel_guardian", 90)
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
            recommended_hero_ids=["berserker"],
        )
    )

    rendered = render_heroes(profile)

    assert "英雄列表：" in rendered
    assert "钢铁守护者" in rendered
    assert "Lv1" in rendered
    assert "上阵" in rendered
    assert "前排承伤保护" in rendered
    assert "装备" in rendered
    assert "可升级" in rendered


def test_render_party_shows_role_gear_and_team_shortfall_summary() -> None:
    profile = create_default_profile()
    profile.hero_progress["berserker"]["level"] = 7
    profile.hero_loadouts.setdefault("berserker", {})["weapon"] = LootItem(
        item_id="loot_weapon_old",
        display_name="Old Pike",
        slot="weapon",
        rarity="magic",
        item_power=104,
        main_stat={"atk": 16},
        affixes=[{"type": "crit_rate", "value": 0.02}],
        recommended_hero_ids=["berserker"],
    )
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
            recommended_hero_ids=["berserker"],
        )
    )

    rendered = render_party(profile)

    assert "当前队伍：" in rendered
    assert "- 2 狂战士（前排）Lv7" in rendered
    assert "职责：近战爆发输出" in rendered
    assert "装备：评分" in rendered
    assert "建议：武器可升级" in rendered
    assert "当前短板：" in rendered
    assert "装备可提升。" in rendered


def test_render_hero_detail_shows_progress_and_party_status() -> None:
    profile = create_default_profile()
    profile.add_hero_xp("hunter_ranger", 120)

    rendered = render_hero_detail(profile, "hunter_ranger")

    assert "猎风游侠" in rendered
    assert "等级：" in rendered
    assert "经验：" in rendered
    assert "状态：上阵" in rendered


def test_render_hero_detail_uses_normalized_sections_and_recommendation_block() -> None:
    profile = create_default_profile()
    profile.hero_progress["hunter_ranger"]["level"] = 6
    profile.choose_specialization("hunter_ranger", "deadeye")
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
            recommended_hero_ids=["hunter_ranger"],
        )
    )

    rendered = render_hero_detail(profile, "hunter_ranger")

    assert rendered.startswith("猎风游侠")
    assert rendered.index("成长：") < rendered.index("装备：") < rendered.index("技能：") < rendered.index("推荐：")
    assert "状态：上阵" in rendered
    assert "专精：神射" in rendered
    assert "普攻等级：" in rendered
    assert "主动等级：" in rendered
    assert "被动等级：" in rendered
    assert "当前升级：" in rendered
    assert "方向：" in rendered


def test_specialization_unlocks_skill_ranks_after_level_threshold() -> None:
    profile = create_default_profile()
    profile.hero_progress["steel_guardian"]["level"] = 6

    unlocked = profile.available_specializations("steel_guardian")

    assert len(unlocked) == 2
    assert profile.skill_ranks("steel_guardian")["active"] >= 2
    assert profile.skill_ranks("steel_guardian")["passive"] >= 2


def test_choose_specialization_persists_choice_and_applies_combat_bonus() -> None:
    engine = BattleEngine(seed=7)
    base_profile = create_default_profile()
    spec_profile = create_default_profile()
    spec_profile.hero_progress["steel_guardian"]["level"] = 6
    spec_profile.choose_specialization("steel_guardian", "bulwark")

    base_unit = next(unit for unit in base_profile.build_team(engine) if unit.hero.hero_id == "steel_guardian")
    spec_unit = next(unit for unit in spec_profile.build_team(engine) if unit.hero.hero_id == "steel_guardian")

    assert spec_profile.hero_specialization("steel_guardian") == "bulwark"
    assert spec_unit.stats.max_hp > base_unit.stats.max_hp
    assert spec_unit.stats.armor >= base_unit.stats.armor


def test_specialization_data_persists_in_save_file(tmp_path) -> None:
    profile = create_default_profile()
    profile.hero_progress["arcane_scholar"]["level"] = 6
    profile.choose_specialization("arcane_scholar", "spellweaver")
    path = tmp_path / "profile.json"

    profile.save(path)
    loaded = PlayerProfile.load(path)

    assert loaded.hero_specialization("arcane_scholar") == "spellweaver"
    payload = json.loads(path.read_text())
    assert "hero_specializations" in payload


def test_render_hero_specialization_shows_skill_ranks_and_choices() -> None:
    profile = create_default_profile()
    profile.hero_progress["arcane_scholar"]["level"] = 6

    rendered = render_hero_specialization(profile, "arcane_scholar")

    assert "专精" in rendered
    assert "可选专精：" in rendered
    assert "技能等级：" in rendered
    assert "主动=2" in rendered


def test_render_hero_detail_includes_specialization_summary() -> None:
    profile = create_default_profile()
    profile.hero_progress["hunter_ranger"]["level"] = 6
    profile.choose_specialization("hunter_ranger", "deadeye")

    rendered = render_hero_detail(profile, "hunter_ranger")

    assert "专精：神射" in rendered
    assert "技能等级：" in rendered


def test_boss_reward_loot_has_targeted_recommendations_and_higher_rarity_weight() -> None:
    engine = BattleEngine(seed=7)

    loot = engine.generate_loot_item(victory=True, encounter_type="boss", encounter_theme="Chrono Dragon Siege", party_roles=["tank", "mage", "support"])

    assert loot.rarity in {"rare", "legendary"}
    assert loot.recommended_hero_ids
    assert any(hero_id in {"steel_guardian", "arcane_scholar", "sacred_priest"} for hero_id in loot.recommended_hero_ids)


def test_frozen_theme_biases_control_or_speed_affixes() -> None:
    engine = BattleEngine(seed=7)

    loot = engine.generate_loot_item(victory=True, encounter_type="elite", encounter_theme="Frozen Court", party_roles=["mage", "support"])

    affix_types = {str(affix["type"]) for affix in loot.affixes}
    assert affix_types & {"speed_flat", "energy_gain_bonus", "resist_flat"}


def test_party_recommendations_on_loot_match_party_members() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()

    loot = engine.generate_loot_item(victory=True, encounter_type="normal", encounter_theme="Bulwark Phalanx", party_roles=[engine.heroes[hero_id].role for hero_id, _ in profile.party])

    assert loot.recommended_hero_ids
    assert all(profile.hero_status(hero_id) == "party" for hero_id in loot.recommended_hero_ids)


def test_battle_result_render_includes_loot_recommendations() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.current_stage = 5
    profile.highest_stage_unlocked = 5

    output = run_battle_session(engine, profile, save_path=Path("/tmp/abyss-targeted-drop-test.json"))

    assert "推荐=" in output
    assert "掉落一览：" in output


def test_gear_score_prefers_role_aligned_weapon_stats() -> None:
    profile = create_default_profile()
    atk_weapon = LootItem(
        item_id="loot_weapon_atk_1",
        display_name="Slayer Pike",
        slot="weapon",
        rarity="rare",
        item_power=126,
        main_stat={"atk": 28},
        affixes=[{"type": "crit_rate", "value": 0.05}],
    )
    mag_weapon = LootItem(
        item_id="loot_weapon_mag_1",
        display_name="Oracle Staff",
        slot="weapon",
        rarity="rare",
        item_power=126,
        main_stat={"mag": 28},
        affixes=[{"type": "heal_bonus", "value": 0.08}],
    )

    berserker_score = profile.score_loot_for_hero("berserker", atk_weapon)
    priest_score = profile.score_loot_for_hero("sacred_priest", mag_weapon)

    assert berserker_score > profile.score_loot_for_hero("berserker", mag_weapon)
    assert priest_score > profile.score_loot_for_hero("sacred_priest", atk_weapon)


def test_recommend_upgrade_for_hero_marks_upgrade_over_equipped_item() -> None:
    profile = create_default_profile()
    old_weapon = LootItem(
        item_id="loot_weapon_old",
        display_name="Old Pike",
        slot="weapon",
        rarity="magic",
        item_power=104,
        main_stat={"atk": 16},
        affixes=[{"type": "crit_rate", "value": 0.02}],
    )
    new_weapon = LootItem(
        item_id="loot_weapon_new",
        display_name="Nightglass Pike",
        slot="weapon",
        rarity="rare",
        item_power=132,
        main_stat={"atk": 30},
        affixes=[{"type": "crit_rate", "value": 0.06}],
    )
    profile.hero_loadouts.setdefault("berserker", {})["weapon"] = old_weapon
    profile.inventory.append(new_weapon)

    recommendation = profile.recommend_upgrade_for_hero("berserker")

    assert recommendation is not None
    assert recommendation["item_id"] == "loot_weapon_new"
    assert recommendation["slot"] == "weapon"
    assert recommendation["verdict"] == "upgrade"
    assert float(recommendation["score_delta"]) > 0


def test_auto_equip_best_upgrade_moves_item_into_loadout() -> None:
    profile = create_default_profile()
    new_weapon = LootItem(
        item_id="loot_weapon_new",
        display_name="Nightglass Pike",
        slot="weapon",
        rarity="rare",
        item_power=132,
        main_stat={"atk": 30},
        affixes=[{"type": "crit_rate", "value": 0.06}],
    )
    profile.inventory.append(new_weapon)

    result = profile.auto_equip_best_upgrade("berserker")

    assert result is not None
    assert result["equipped_item_id"] == "loot_weapon_new"
    assert profile.hero_loadouts["berserker"]["weapon"].item_id == "loot_weapon_new"
    assert all(item.item_id != "loot_weapon_new" for item in profile.inventory)


def test_inventory_enter_equips_selected_item_to_selected_hero(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
        )
    )
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")

    ui.open_inventory_manager()
    ui.inventory_hero_index = 1
    ui.inventory_enter()

    assert "weapon" in profile.hero_loadouts["berserker"]
    assert profile.hero_loadouts["berserker"]["weapon"].item_id == "loot_weapon_new"
    assert not any(item.item_id == "loot_weapon_new" for item in profile.inventory)
    assert any("已为 狂战士 装备 夜璃 长枪" in line for _tag, line in ui.center_entries)


def test_inventory_enter_unequips_selected_equipped_item(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.hero_loadouts.setdefault("berserker", {})["weapon"] = LootItem(
        item_id="loot_weapon_old",
        display_name="Stormforged Pike",
        slot="weapon",
        rarity="magic",
        item_power=98,
        main_stat={"atk": 10},
        affixes=[],
        recommended_hero_ids=["berserker"],
    )
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")

    ui.open_inventory_manager()
    ui.inventory_hero_index = 1
    ui.inventory_toggle_focus()
    ui.inventory_enter()

    assert "weapon" not in profile.hero_loadouts["berserker"]
    assert any(item.item_id == "loot_weapon_old" for item in profile.inventory)
    assert any("已从 狂战士 卸下 风暴铸造 长枪" in line for _tag, line in ui.center_entries)


def test_right_panel_lines_show_shared_inventory_for_selected_hero(tmp_path) -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.inventory.extend(
        [
            LootItem(
                item_id="loot_weapon_new",
                display_name="Nightglass Pike",
                slot="weapon",
                rarity="rare",
                item_power=132,
                main_stat={"atk": 30},
                affixes=[{"type": "crit_rate", "value": 0.06}],
                recommended_hero_ids=["berserker"],
            ),
            LootItem(
                item_id="loot_priest_only",
                display_name="Saintsworn Charm",
                slot="amulet",
                rarity="rare",
                item_power=128,
                main_stat={"heal_bonus": 0.12},
                affixes=[{"type": "energy_gain_bonus", "value": 0.08}],
                recommended_hero_ids=["sacred_priest"],
            ),
        ]
    )
    ui = HeadlessTerminalUI(engine=engine, profile=profile, save_path=tmp_path / "save.json")

    ui.open_inventory_manager()
    ui.inventory_hero_index = 1
    ui.refresh_inventory_manager()
    lines = ui.right_panel_lines()

    assert lines[0] == "共享背包（当前装备目标：狂战士）："
    assert any(line.startswith("> loot_weapon_new:") for line in lines)
    assert any("loot_priest_only" in line for line in lines)


def test_best_upgrade_lines_lists_multiple_hero_upgrades() -> None:
    profile = create_default_profile()
    profile.inventory.extend(
        [
            LootItem(
                item_id="loot_weapon_new",
                display_name="Nightglass Pike",
                slot="weapon",
                rarity="rare",
                item_power=132,
                main_stat={"atk": 30},
                affixes=[{"type": "crit_rate", "value": 0.06}],
            ),
            LootItem(
                item_id="loot_amulet_new",
                display_name="Saintsworn Charm",
                slot="amulet",
                rarity="rare",
                item_power=128,
                main_stat={"heal_bonus": 0.12},
                affixes=[{"type": "energy_gain_bonus", "value": 0.08}],
            ),
        ]
    )

    lines = profile.best_upgrade_lines()

    assert any("狂战士" in line for line in lines)
    assert any("圣职祭司" in line for line in lines)
    assert any("升级" in line for line in lines)


def test_render_recommendation_views_include_evidence_and_verdict_structure() -> None:
    profile = create_default_profile()
    profile.inventory.append(
        LootItem(
            item_id="loot_weapon_new",
            display_name="Nightglass Pike",
            slot="weapon",
            rarity="rare",
            item_power=132,
            main_stat={"atk": 30},
            affixes=[{"type": "crit_rate", "value": 0.06}],
        )
    )

    hero_view = render_hero_recommendation(profile, "berserker")
    roster_view = render_best_upgrades(profile)

    assert "推荐：" in hero_view
    assert "英雄：狂战士" in hero_view
    assert "候选评分：" in hero_view
    assert "当前装备评分：" in hero_view
    assert "提升值：" in hero_view
    assert "结论：" in hero_view
    assert "最佳升级建议：" in roster_view
    assert "狂战士" in roster_view
    assert "候选评分：" in roster_view
    assert "结论：" in roster_view


def test_battle_logs_energy_and_action_order_telemetry() -> None:
    result = run_demo_battle(seed=7)

    assert any(entry.tag == "TURN" and "速度" in entry.message for entry in result.logs)
    assert any(entry.tag == "NRG" and "能量" in entry.message for entry in result.logs)


def test_battle_result_render_includes_telemetry_and_analysis_sections() -> None:
    result = run_demo_battle(seed=7)
    rendered = result.render()

    assert "战斗分析：" in rendered
    assert "行动顺序快照：" in rendered
    assert "最高伤害：" in rendered
    assert "最高治疗：" in rendered


def test_battle_engine_has_no_fatigue_damage_at_action_start() -> None:
    engine = BattleEngine(seed=7)
    actor = engine.build_unit("arcane_scholar", "ally", 1, "backline")
    engine.analysis_state = {
        "damage_by_unit": Counter(),
        "healing_by_unit": Counter(),
        "skill_casts": Counter(),
        "action_order": [],
        "first_fall": "",
    }
    engine._tracked_units = [actor]

    engine.current_round = 1
    baseline_hp = actor.current_hp
    engine._process_start_of_action(actor)
    hp_after_round_one = actor.current_hp

    engine.current_round = 30
    engine._process_start_of_action(actor)

    assert actor.current_hp == hp_after_round_one == baseline_hp
    assert not any(entry.tag == "FAT" for entry in engine.logs)


def test_stage_battle_analysis_mentions_first_fall_and_skill_usage() -> None:
    engine = BattleEngine(seed=7)
    allies = create_default_profile().build_team(engine)

    result = engine.run_stage_battle(allies, stage=1)

    assert result.analysis is not None
    assert result.analysis.get("first_fall")
    assert result.analysis.get("top_damage")
    assert result.analysis.get("skill_casts")


def test_run_battle_session_surfaces_energy_and_speed_explanations() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()

    output = run_battle_session(engine, profile, save_path=Path("/tmp/abyss-battle-telemetry.json"))

    assert "战斗分析：" in output
    assert "行动顺序快照：" in output
    assert "最高伤害：" in output
    assert "速度" in output


def test_stage_analysis_surfaces_enemy_mechanic_tags_and_explanations() -> None:
    engine = BattleEngine(seed=7)

    analysis = engine.analyze_stage_encounter(2)

    assert "backline_pressure" in analysis["threat_tags"]
    assert "enemy_mechanics" in analysis
    assert any("后排" in line for line in analysis["enemy_mechanics"])


def test_render_stage_includes_threat_summary_block() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()
    profile.current_stage = 2
    profile.highest_stage_unlocked = 2

    rendered = render_stage(profile, engine)

    assert "威胁概览：" in rendered
    assert "后排" in rendered


def test_battle_result_analysis_contains_reason_summary() -> None:
    engine = BattleEngine(seed=7)
    allies = create_default_profile().build_team(engine)

    result = engine.run_stage_battle(allies, stage=1)

    assert result.analysis is not None
    assert result.analysis.get("reason_summary")
    assert any(keyword in str(result.analysis["reason_summary"]) for keyword in {"阵线", "速度", "治疗", "伤害", "后排"})


def test_render_threat_summary_formats_mechanics() -> None:
    lines = render_threat_summary(
        {
            "threat_tags": ["backline_pressure", "sustain"],
            "enemy_mechanics": [
                "Enemy backliners can directly pressure your backline.",
                "Enemy sustain can extend the fight through healing or shielding.",
            ],
        }
    )

    assert "威胁概览：" in lines
    assert "后排威胁" in lines
    assert "Enemy backliners" in lines


def test_run_battle_session_surfaces_post_battle_reason_summary() -> None:
    engine = BattleEngine(seed=7)
    profile = create_default_profile()

    output = run_battle_session(engine, profile, save_path=Path("/tmp/abyss-threat-summary.json"))

    assert "威胁概览：" in output
    assert "原因总结：" in output
