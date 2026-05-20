#!/usr/bin/env python3
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


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


def generate_enemies(map_name: str):
    return [
        Unit("mob_1", f"{map_name}行尸", 800, 800, 75, 30, 1.0, 1.0, 85, 0.05),
        Unit("mob_2", f"{map_name}毒咒者", 700, 700, 55, 65, 0.9, 1.1, 95, 0.06),
        Unit("mob_3", f"{map_name}守墓者", 900, 900, 80, 20, 0.95, 1.0, 80, 0.04),
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


def battle(team, enemies, heroes, skills, speed_cfg, map_name):
    tick_s = speed_cfg["tick"]["tickSeconds"]
    atb_coef = speed_cfg["atb"]["coefficient"]
    hero_def = {h["id"]: h for h in heroes["heroes"]}
    skill_book = {s["id"]: s for s in skills["skills"]}
    log = [f"⚔️ 战斗开始：{map_name}"]
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
                    sk = {
                        "id": "enemy_hit",
                        "name": "腐化打击",
                        "multiplier": 0.85,
                        "scalesWith": "attack",
                        "energyGain": 8,
                        "type": "basic",
                        "baseCastTimeSeconds": 0,
                    }

                if sk.get("type") == "active":
                    u.energy -= sk.get("energyCost", 0)
                    u.cooldowns[sk["id"]] = sk.get("cooldownSeconds", 0)

                mult = sk.get("multiplier", 1.0)
                hits = sk.get("hits", 1)
                scale = sk.get("scalesWith", "attack")
                total = 0.0
                crit_any = False
                for _ in range(hits):
                    dmg, crit = do_damage(u, target, mult, scale)
                    total += dmg
                    crit_any = crit_any or crit
                    if target.hp <= 0:
                        break
                u.energy = min(100, u.energy + sk.get("energyGain", 0))
                if sk.get("type") == "basic":
                    u.basic_timer = max(u.basic_timer, 1.0 / max(0.1, u.attack_speed))

                mm = int(seconds // 60)
                ss = int(seconds % 60)
                log.append(f"⏱ {mm:02d}:{ss:02d} {u.name}释放【{sk['name']}】 造成 {total:.0f} 伤害" + ("（暴击）" if crit_any else ""))

                if target.hp <= 0:
                    log.append(f"💀 {target.name} 倒下")
                    if target in targets:
                        targets.remove(target)

    if team and not enemies:
        result = "✅ 战斗胜利"
        drops = ["铁块 x3", "奥术尘埃 x1"]
        if random.random() < 0.2:
            drops.append("🟠 传奇装备：风暴低语法杖")
    else:
        result = "❌ 战斗失败"
        drops = []

    log.append(result)
    log.append(f"耗时：{seconds:.1f}秒")
    log.append("掉落：" + ("、".join(drops) if drops else "无"))
    return "\n".join(log)


def print_panel(title: str, lines: list[str]):
    width = max(48, len(title) + 6, *(len(line) + 4 for line in lines))
    top = "┌" + "─" * (width - 2) + "┐"
    sep = "├" + "─" * (width - 2) + "┤"
    bottom = "└" + "─" * (width - 2) + "┘"
    print(top)
    print(f"│ {title.center(width - 4)} │")
    print(sep)
    for line in lines:
        print(f"│ {line.ljust(width - 4)} │")
    print(bottom)


def show_party(save, heroes):
    by_id = {h["id"]: h for h in heroes["heroes"]}
    lines = [
        "前排：" + " / ".join(by_id[x]["name"] for x in save["party"]["front"]),
        "后排：" + " / ".join(by_id[x]["name"] for x in save["party"]["back"]),
    ]
    print_panel("👥 当前阵容", lines)


def choose_menu(prompt: str, options: list[str]) -> int:
    print_panel("🎮 操作菜单", [f"{idx + 1}. {name}" for idx, name in enumerate(options)])
    while True:
        raw = input(f"{prompt}（输入数字）> ").strip()
        if raw.isdigit():
            val = int(raw)
            if 1 <= val <= len(options):
                return val
        print("请输入有效数字，例如：1")


def main():
    heroes = load_json("data/heroes.json")
    skills = load_json("data/skills.json")
    speed_cfg = load_json("data/speed-system.json")
    save = load_json("save/player-save.initial.json")
    content = load_json("data/content.json")

    unlocked = [m for m in content["maps"] if m["id"] in save["progress"]["unlockedMaps"]]

    print_panel("深渊回响 CLI · TUI 模式", [
        f"欢迎你，{save['name']}（存档：{save['playerId']}）",
        "使用数字选择操作，更直观更方便。",
    ])

    while True:
        choice = choose_menu("请选择操作", ["开始游戏", "查看阵容", "进入地图", "退出"])

        if choice == 1:
            print_panel("📜 存档信息", [
                f"玩家：{save['name']}",
                f"存档 ID：{save['playerId']}",
                "可选地图：" + "、".join(m["name"] for m in unlocked),
            ])
        elif choice == 2:
            show_party(save, heroes)
        elif choice == 3:
            map_idx = choose_menu("选择地图", [m["name"] for m in unlocked])
            map_name = unlocked[map_idx - 1]["name"]
            team = make_team(save, heroes)
            enemies = generate_enemies(map_name)
            result = battle(team, enemies, heroes, skills, speed_cfg, map_name)
            print_panel("⚔️ 战斗日志", result.split("\n"))
        elif choice == 4:
            print("已退出游戏。")
            return


if __name__ == "__main__":
    main()
