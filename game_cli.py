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
    base = [
        Unit("mob_1", f"{map_name}行尸", 800, 800, 75, 30, 1.0, 1.0, 85, 0.05),
        Unit("mob_2", f"{map_name}毒咒者", 700, 700, 55, 65, 0.9, 1.1, 95, 0.06),
        Unit("mob_3", f"{map_name}守墓者", 900, 900, 80, 20, 0.95, 1.0, 80, 0.04),
    ]
    return base


def do_damage(caster: Unit, target: Unit, mult: float, scale: str):
    main = caster.attack if scale == "attack" else caster.spell
    dmg = main * mult * random.uniform(0.9, 1.1)
    if random.random() < caster.crit:
        dmg *= 1.5
        crit = True
    else:
        crit = False
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
                    sk = {"id": "enemy_hit", "name": "腐化打击", "multiplier": 0.85, "scalesWith": "attack", "energyGain": 8, "type": "basic", "baseCastTimeSeconds": 0}

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


def show_party(save, heroes):
    by_id = {h["id"]: h for h in heroes["heroes"]}
    print("阵容：")
    print("前排：" + " / ".join(by_id[x]["name"] for x in save["party"]["front"]))
    print("后排：" + " / ".join(by_id[x]["name"] for x in save["party"]["back"]))


def main():
    rules = load_json("data/game-rules.json")
    heroes = load_json("data/heroes.json")
    skills = load_json("data/skills.json")
    speed_cfg = load_json("data/speed-system.json")
    save = load_json("save/player-save.initial.json")
    content = load_json("data/content.json")

    print("深渊回响 CLI（WSL 命令行版）")
    print("输入：开始游戏 / 查看阵容 / 进入地图 <地图名> / 退出")

    while True:
        cmd = input("\n> ").strip()
        if cmd == "退出":
            print("已退出游戏。")
            return
        if cmd == "开始游戏":
            print(f"欢迎，{save['name']}！已载入存档 {save['playerId']}。")
            show_party(save, heroes)
            print("可选地图：" + "、".join(m["name"] for m in content["maps"] if m["id"] in save["progress"]["unlockedMaps"]))
        elif cmd == "查看阵容":
            show_party(save, heroes)
        elif cmd.startswith("进入地图"):
            map_name = cmd.replace("进入地图", "", 1).strip()
            maps = {m["name"]: m for m in content["maps"]}
            if map_name not in maps:
                print("未知地图。")
                continue
            team = make_team(save, heroes)
            enemies = generate_enemies(map_name)
            print(battle(team, enemies, heroes, skills, speed_cfg, map_name))
        else:
            print("未知命令。")


if __name__ == "__main__":
    main()
