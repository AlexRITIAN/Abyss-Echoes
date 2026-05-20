#!/usr/bin/env python3
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"

BATTLE_LINE_DELAY = 0.25


def load_json(rel: str):
    with (DOCS / rel).open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Unit:
    id: str
    name: str
    hp_max: float
    hp: float
    attack: float
    spell: float
    attack_speed: float
    cast_speed: float
    speed: float
    crit: float
    atb: float = 0.0
    basic_timer: float = 0.0
    energy: float = 0.0
    cooldowns: dict = field(default_factory=dict)


def make_team(save, heroes):
    by_id = {h["id"]: h for h in heroes["heroes"]}
    ids = save["party"]["front"] + save["party"]["back"]
    team = []
    for hid in ids:
        h = by_id[hid]
        b = h["baseStats"]
        team.append(Unit(
            id=hid,
            name=h["name"],
            hp_max=float(b["hp"]),
            hp=float(b["hp"]),
            attack=float(b["attack"]),
            spell=float(b["spellPower"]),
            attack_speed=float(b["attackSpeed"]),
            cast_speed=float(b["castSpeed"]),
            speed=float(b["speed"]),
            crit=float(b["critChance"]),
        ))
    return team


def generate_enemies(map_name: str, level_scale: float = 1.0, is_boss: bool = False):
    boss_scale = 1.35 if is_boss else 1.0
    scale = level_scale * boss_scale
    suffix = "魔王" if is_boss else ""
    return [
        Unit("mob_1", f"{map_name}行尸{suffix}", 800 * scale, 800 * scale, 75 * scale, 30 * scale, 1.0, 1.0, 85, 0.05),
        Unit("mob_2", f"{map_name}毒咒者{suffix}", 700 * scale, 700 * scale, 55 * scale, 65 * scale, 0.9, 1.1, 95, 0.06),
        Unit("mob_3", f"{map_name}守墓者{suffix}", 900 * scale, 900 * scale, 80 * scale, 20 * scale, 0.95, 1.0, 80, 0.04),
    ]


def do_damage(caster: Unit, target: Unit, mult: float, scale: str):
    main = caster.attack if scale == "attack" else caster.spell
    dmg = main * mult * random.uniform(0.9, 1.1)
    crit = random.random() < caster.crit
    if crit:
        dmg *= 1.5
    target.hp -= dmg
    return dmg, crit


def choose_skill(unit: Unit, skill_book, hero_def):
    active = skill_book[hero_def["activeSkill"]]
    if unit.energy >= active.get("energyCost", 9999) and unit.cooldowns.get(active["id"], 0) <= 0:
        return active
    return skill_book[hero_def["basicSkill"]]


def battle(team, enemies, heroes, skills, speed_cfg, battle_name):
    tick_s = speed_cfg["tick"]["tickSeconds"]
    atb_coef = speed_cfg["atb"]["coefficient"]
    hero_def = {h["id"]: h for h in heroes["heroes"]}
    skill_book = {s["id"]: s for s in skills["skills"]}
    log = [f"⚔️ 战斗开始：{battle_name}"]
    seconds = 0.0

    while team and enemies and seconds < 45:
        seconds += tick_s
        for side in (team, enemies):
            for u in list(side):
                if u.hp <= 0:
                    side.remove(u)
                    continue
                u.atb += u.speed * atb_coef
                u.basic_timer = max(0.0, u.basic_timer - tick_s)
                for k in list(u.cooldowns):
                    u.cooldowns[k] = max(0.0, u.cooldowns[k] - tick_s)
                if u.atb < 100:
                    continue
                u.atb -= 100
                targets = enemies if u in team else team
                if not targets:
                    break
                target = min(targets, key=lambda x: x.hp)
                if u in team:
                    sk = choose_skill(u, skill_book, hero_def[u.id])
                else:
                    sk = {"id": "enemy_hit", "name": "腐化打击", "multiplier": 0.85, "scalesWith": "attack", "energyGain": 8, "type": "basic"}
                if sk.get("type") == "active":
                    u.energy -= sk.get("energyCost", 0)
                    u.cooldowns[sk["id"]] = sk.get("cooldownSeconds", 0)
                total, crit_any = 0.0, False
                for _ in range(sk.get("hits", 1)):
                    dmg, crit = do_damage(u, target, sk.get("multiplier", 1.0), sk.get("scalesWith", "attack"))
                    total += dmg
                    crit_any = crit_any or crit
                    if target.hp <= 0:
                        break
                u.energy = min(100, u.energy + sk.get("energyGain", 0))
                mm, ss = int(seconds // 60), int(seconds % 60)
                log.append(f"⏱ {mm:02d}:{ss:02d} {u.name}释放【{sk['name']}】 造成 {total:.0f} 伤害" + ("（暴击）" if crit_any else ""))
                if target.hp <= 0:
                    log.append(f"💀 {target.name} 倒下")
                    if target in targets:
                        targets.remove(target)

    win = bool(team and not enemies)
    log.append("✅ 战斗胜利" if win else "❌ 战斗失败")
    log.append(f"耗时：{seconds:.1f}秒")
    return log, win


def print_panel(title: str, lines: list[str]):
    width = max(64, len(title) + 6, *(len(line) + 4 for line in lines))
    top = "┌" + "─" * (width - 2) + "┐"
    sep = "├" + "─" * (width - 2) + "┤"
    bottom = "└" + "─" * (width - 2) + "┘"
    print(top)
    print(f"│ {title.center(width - 4)} │")
    print(sep)
    for line in lines:
        print(f"│ {line.ljust(width - 4)} │")
    print(bottom)


def clear_screen():
    print("[2J[H", end="")


def render_tui(title: str, menu_lines: list[str], hint: str = ""):
    clear_screen()
    print_panel("深渊回响 · 指挥终端", [title, "", *menu_lines, "", hint])


def stream_lines(lines: list[str], delay: float = BATTLE_LINE_DELAY):
    for line in lines:
        print(line)
        time.sleep(delay)


def show_party(save, heroes):
    by_id = {h["id"]: h for h in heroes["heroes"]}
    print_panel("👥 当前阵容", [
        "前排：" + " / ".join(by_id[x]["name"] for x in save["party"]["front"]),
        "后排：" + " / ".join(by_id[x]["name"] for x in save["party"]["back"]),
    ])


def choose_menu(prompt: str, options: list[str]) -> int:
    render_tui(prompt, [f"{i + 1}. {name}" for i, name in enumerate(options)], "输入数字并回车")
    while True:
        raw = input(f"{prompt}（输入数字）> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        print("请输入有效数字，例如：1")


def run_magic_tower(save, heroes, skills, speed_cfg, state):
    base = state["max_unlocked_floor"]
    max_pick = min(200, base + 5)
    floors = [f"第{n}层" for n in range(base, max_pick + 1)]
    pick = choose_menu("选择挑战层数", floors)
    floor = base + pick - 1
    print_panel("🗼 魔塔挑战", [f"当前选择：第{floor}层", "每层共5轮，第5轮为Boss。"])

    for wave in range(1, 6):
        is_boss = wave == 5
        scale = 1 + (floor - 1) * 0.06 + (wave - 1) * 0.03
        team = make_team(save, heroes)
        enemies = generate_enemies("魔塔", level_scale=scale, is_boss=is_boss)
        log, win = battle(team, enemies, heroes, skills, speed_cfg, f"魔塔 第{floor}层 第{wave}轮" + ("（Boss）" if is_boss else ""))
        stream_lines(log)
        if not win:
            print(f"挑战止步于第{floor}层第{wave}轮。")
            return
    state["max_unlocked_floor"] = max(state["max_unlocked_floor"], min(200, floor + 1))
    print(f"🎉 成功通关第{floor}层！下次可从第{state['max_unlocked_floor']}层开始，最多上选5层。")


def main():
    heroes = load_json("data/heroes.json")
    skills = load_json("data/skills.json")
    speed_cfg = load_json("data/speed-system.json")
    save = load_json("save/player-save.initial.json")
    content = load_json("data/content.json")
    unlocked = [m for m in content["maps"] if m["id"] in save["progress"]["unlockedMaps"]]
    tower_state = {"max_unlocked_floor": 1}

    render_tui(
        f"欢迎你，{save['name']}（存档：{save['playerId']}）",
        ["游戏已自动开始（命令行启动即进入主菜单）", f"可选地图：{'、'.join(m['name'] for m in unlocked)}"],
        "按回车继续"
    )
    input()

    while True:
        options = ["查看阵容", "进入地图", "挑战魔塔", "退出"]
        choice = choose_menu("请选择操作", options)
        selected = options[choice - 1]
        if selected == "查看阵容":
            show_party(save, heroes)
        elif selected == "进入地图":
            map_idx = choose_menu("选择地图", [m["name"] for m in unlocked])
            map_name = unlocked[map_idx - 1]["name"]
            team = make_team(save, heroes)
            enemies = generate_enemies(map_name)
            log, _ = battle(team, enemies, heroes, skills, speed_cfg, map_name)
            stream_lines(log)
        elif selected == "挑战魔塔":
            run_magic_tower(save, heroes, skills, speed_cfg, tower_state)
        else:
            print("已退出游戏。")
            return


if __name__ == "__main__":
    main()
