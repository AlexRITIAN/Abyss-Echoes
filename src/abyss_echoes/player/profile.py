from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from abyss_echoes.engine.content_loader import load_heroes
from abyss_echoes.engine.models import BattleRewards, ItemDefinition, LootItem
from abyss_echoes.i18n import (
    hero_name,
    localize_loot_name,
    party_status_name,
    position_name,
    rarity_name,
    role_name,
    slot_name,
    specialization_name,
)

DEFAULT_PARTY = [
    ("steel_guardian", "frontline"),
    ("berserker", "frontline"),
    ("hunter_ranger", "backline"),
    ("arcane_scholar", "backline"),
    ("sacred_priest", "backline"),
]
DEFAULT_SAVE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "save.json"
PARTY_SIZE = 5
FRONTLINE_LIMIT = 2
BACKLINE_LIMIT = 3
BASE_LEVEL_XP = 100
LEVEL_XP_STEP = 50
MAX_HERO_LEVEL = 50
SPECIALIZATION_UNLOCK_LEVEL = 6
HERO_TEMPLATES = load_heroes()
ALL_HERO_IDS = tuple(HERO_TEMPLATES.keys())
ROLE_SPECIALIZATIONS = {
    "tank": ("bulwark", "sentinel"),
    "melee_dps": ("slayer", "duelist"),
    "ranged_dps": ("deadeye", "barrage"),
    "mage": ("spellweaver", "frostbound"),
    "support": ("oracle", "chorister"),
}
ROLE_STAT_WEIGHTS = {
    "tank": {"max_hp": 0.07, "armor": 1.5, "resist": 1.3, "speed": 0.4, "shield_bonus": 45.0, "energy_gain_bonus": 16.0},
    "melee_dps": {"atk": 1.7, "crit_rate": 120.0, "crit_damage": 45.0, "damage_bonus": 52.0, "speed": 0.7, "damage_vs_debuffed": 32.0},
    "ranged_dps": {"atk": 1.6, "crit_rate": 118.0, "crit_damage": 42.0, "damage_bonus": 50.0, "speed": 0.9, "damage_vs_debuffed": 28.0},
    "mage": {"mag": 1.7, "crit_rate": 85.0, "damage_bonus": 54.0, "speed": 0.8, "energy_gain_bonus": 20.0, "resist": 0.5},
    "support": {"mag": 1.2, "heal_bonus": 90.0, "energy_gain_bonus": 42.0, "speed": 0.9, "resist": 0.6, "max_hp": 0.03},
}
ROLE_SLOT_BONUS = {
    "tank": {"chest": 18.0, "helmet": 14.0, "pants": 14.0, "boots": 8.0},
    "melee_dps": {"weapon": 22.0, "gloves": 12.0, "ring": 10.0, "boots": 6.0},
    "ranged_dps": {"weapon": 20.0, "gloves": 12.0, "ring": 11.0, "boots": 8.0},
    "mage": {"weapon": 20.0, "amulet": 14.0, "ring": 10.0, "boots": 8.0},
    "support": {"amulet": 20.0, "boots": 10.0, "ring": 8.0, "weapon": 12.0},
}
RARITY_SCORE_BONUS = {"magic": 4.0, "rare": 10.0, "legendary": 18.0}
AFFIX_STAT_MAP = {
    "hp_pct": "max_hp",
    "atk_pct": "atk",
    "mag_pct": "mag",
    "armor_flat": "armor",
    "resist_flat": "resist",
    "speed_flat": "speed",
    "crit_rate": "crit_rate",
    "crit_damage": "crit_damage",
    "energy_gain_bonus": "energy_gain_bonus",
    "heal_bonus": "heal_bonus",
    "shield_bonus": "shield_bonus",
    "damage_vs_debuffed": "damage_vs_debuffed",
    "damage_bonus": "damage_bonus",
}


def build_default_hero_progress() -> dict[str, dict[str, int]]:
    return {hero_id: {"level": 1, "xp": 0} for hero_id in ALL_HERO_IDS}


@dataclass(slots=True)
class PlayerProfile:
    gold: int = 0
    materials: int = 0
    inventory: list[LootItem] = field(default_factory=list)
    hero_loadouts: dict[str, dict[str, LootItem]] = field(default_factory=dict)
    party: list[tuple[str, str]] = field(default_factory=lambda: list(DEFAULT_PARTY))
    current_stage: int = 1
    highest_stage_unlocked: int = 1
    hero_progress: dict[str, dict[str, int]] = field(default_factory=build_default_hero_progress)
    hero_specializations: dict[str, str] = field(default_factory=dict)
    extracted_aspects: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.party = list(self.party)
        self._validate_party(self.party)
        self.hero_progress = self._normalize_hero_progress(self.hero_progress)
        self.hero_specializations = self._normalize_hero_specializations(self.hero_specializations)

    def collect_rewards(self, rewards: BattleRewards) -> None:
        self.gold += rewards.gold
        self.materials += rewards.materials
        self.inventory.extend(rewards.loot)

    def equip_item(self, hero_id: str, item_id: str) -> LootItem:
        item = self._remove_inventory_item(item_id)
        hero_slots = self.hero_loadouts.setdefault(hero_id, {})
        previous = hero_slots.get(item.slot)
        if previous is not None:
            self.inventory.append(previous)
        hero_slots[item.slot] = item
        return item

    def unequip_item(self, hero_id: str, slot: str) -> LootItem:
        hero_slots = self.hero_loadouts.setdefault(hero_id, {})
        if slot not in hero_slots:
            raise ValueError(f"hero {hero_id} has no item equipped in slot {slot}")
        item = hero_slots.pop(slot)
        self.inventory.append(item)
        return item

    def salvage_inventory_item(self, item_id: str, materials_gain: int = 1) -> LootItem:
        if materials_gain < 0:
            raise ValueError("materials_gain must be non-negative")
        item = self._remove_inventory_item(item_id)
        self.materials += materials_gain
        return item

    def extract_inventory_aspect(self, item_id: str) -> LootItem:
        item = self._remove_inventory_item(item_id)
        if not item.legendary_aspect:
            raise ValueError("item has no extractable legendary aspect")
        self.extracted_aspects.append(item.legendary_aspect)
        return item

    def add_hero_xp(self, hero_id: str, amount: int) -> dict[str, int | str]:
        self._validate_hero_id(hero_id)
        if amount < 0:
            raise ValueError("xp amount must be non-negative")
        progress = self.hero_progress.setdefault(hero_id, {"level": 1, "xp": 0})
        level = int(progress.get("level", 1))
        xp = int(progress.get("xp", 0))
        xp_remaining = amount
        levels_gained = 0

        while xp_remaining > 0 and level < MAX_HERO_LEVEL:
            threshold = self.xp_to_next_level(level)
            needed = threshold - xp
            if xp_remaining >= needed:
                xp_remaining -= needed
                level += 1
                xp = 0
                levels_gained += 1
            else:
                xp += xp_remaining
                xp_remaining = 0

        if level >= MAX_HERO_LEVEL:
            level = MAX_HERO_LEVEL
            xp = 0

        progress["level"] = level
        progress["xp"] = xp
        return {
            "hero_id": hero_id,
            "levels_gained": levels_gained,
            "level": level,
            "xp": xp,
            "xp_added": amount,
        }

    def grant_party_xp(self, amount: int) -> dict[str, dict[str, int | str]]:
        return {hero_id: self.add_hero_xp(hero_id, amount) for hero_id, _position in self.party}

    def hero_level(self, hero_id: str) -> int:
        self._validate_hero_id(hero_id)
        return int(self.hero_progress.get(hero_id, {}).get("level", 1))

    def hero_xp(self, hero_id: str) -> int:
        self._validate_hero_id(hero_id)
        return int(self.hero_progress.get(hero_id, {}).get("xp", 0))

    def hero_status(self, hero_id: str) -> str:
        self._validate_hero_id(hero_id)
        return "party" if any(member_id == hero_id for member_id, _position in self.party) else "bench"

    def xp_to_next_level(self, level_or_hero_id: int | str) -> int:
        level = self.hero_level(level_or_hero_id) if isinstance(level_or_hero_id, str) else int(level_or_hero_id)
        return BASE_LEVEL_XP + max(0, level - 1) * LEVEL_XP_STEP

    def available_specializations(self, hero_id: str) -> list[str]:
        self._validate_hero_id(hero_id)
        if self.hero_level(hero_id) < SPECIALIZATION_UNLOCK_LEVEL:
            return []
        return list(ROLE_SPECIALIZATIONS.get(HERO_TEMPLATES[hero_id].role, ()))

    def hero_specialization(self, hero_id: str) -> str:
        self._validate_hero_id(hero_id)
        return self.hero_specializations.get(hero_id, "")

    def choose_specialization(self, hero_id: str, specialization: str) -> str:
        self._validate_hero_id(hero_id)
        available = self.available_specializations(hero_id)
        if specialization not in available:
            raise ValueError(f"specialization {specialization} is not unlocked for {hero_id}")
        self.hero_specializations[hero_id] = specialization
        return specialization

    def skill_ranks(self, hero_id: str) -> dict[str, int]:
        self._validate_hero_id(hero_id)
        level = self.hero_level(hero_id)
        return {
            "basic": 1 + int(level >= 10) + int(level >= 20),
            "active": 1 + int(level >= 5) + int(level >= 15),
            "passive": 1 + int(level >= 5) + int(level >= 18),
        }

    def build_team(self, engine) -> list:
        team = []
        for index, (hero_id, position) in enumerate(self.party, start=1):
            equipped_ids = []
            for item in self.hero_loadouts.get(hero_id, {}).values():
                if item.item_id not in engine.items:
                    engine.items[item.item_id] = ItemDefinition(
                        item_id=item.item_id,
                        slot=item.slot,
                        rarity=item.rarity,
                        item_power=item.item_power,
                        main_stat=item.main_stat,
                        affixes=item.affixes,
                        legendary_aspect=item.legendary_aspect,
                    )
                equipped_ids.append(item.item_id)
            team.append(
                engine.build_unit(
                    hero_id,
                    team_id="ally",
                    formation_index=index,
                    position=position,
                    equipment_ids=equipped_ids,
                    hero_level=self.hero_level(hero_id),
                    specialization=self.hero_specialization(hero_id),
                    skill_ranks=self.skill_ranks(hero_id),
                )
            )
        return team

    def inventory_lines(self) -> list[str]:
        if not self.inventory:
            return ["- 背包为空"]
        return [
            f"- {item.item_id}: {localize_loot_name(item.display_name)} [{rarity_name(item.rarity)}] 部位={slot_name(item.slot)} 战力={item.item_power}"
            for item in self.inventory
        ]

    def loadout_lines(self) -> list[str]:
        lines: list[str] = []
        for hero_id, _position in self.party:
            slots = self.hero_loadouts.get(hero_id, {})
            if not slots:
                lines.append(f"- {hero_name(hero_id)}：暂无装备")
                continue
            slot_text = ", ".join(
                f"{slot_name(slot)}={localize_loot_name(item.display_name)}" for slot, item in sorted(slots.items())
            )
            lines.append(f"- {hero_name(hero_id)}：{slot_text}")
        return lines

    def score_loot_for_hero(self, hero_id: str, item: LootItem) -> float:
        self._validate_hero_id(hero_id)
        hero = HERO_TEMPLATES[hero_id]
        role = hero.role
        weights = ROLE_STAT_WEIGHTS.get(role, {})
        score = float(item.item_power) * 0.35 + RARITY_SCORE_BONUS.get(item.rarity, 0.0)
        score += ROLE_SLOT_BONUS.get(role, {}).get(item.slot, 0.0)
        if hero_id in item.recommended_hero_ids:
            score += 8.0

        for stat_name, value in item.main_stat.items():
            score += self._score_stat_value(weights, str(stat_name), value)
        for affix in item.affixes:
            score += self._score_affix(role, affix)
        if item.legendary_aspect:
            score += 6.0
        return round(score, 2)

    def recommend_upgrade_for_hero(self, hero_id: str) -> dict[str, Any] | None:
        self._validate_hero_id(hero_id)
        best: dict[str, Any] | None = None
        for item in self.inventory:
            candidate_score = self.score_loot_for_hero(hero_id, item)
            equipped = self.hero_loadouts.get(hero_id, {}).get(item.slot)
            equipped_score = self.score_loot_for_hero(hero_id, equipped) if equipped is not None else 0.0
            score_delta = round(candidate_score - equipped_score, 2)
            verdict = "upgrade" if score_delta > 0 else "sidegrade"
            candidate = {
                "hero_id": hero_id,
                "item_id": item.item_id,
                "display_name": item.display_name,
                "slot": item.slot,
                "score": candidate_score,
                "equipped_score": equipped_score,
                "score_delta": score_delta,
                "verdict": verdict,
            }
            if best is None or candidate["score_delta"] > best["score_delta"]:
                best = candidate
        if best is None or float(best["score_delta"]) <= 0:
            return None
        return best

    def auto_equip_best_upgrade(self, hero_id: str) -> dict[str, Any] | None:
        recommendation = self.recommend_upgrade_for_hero(hero_id)
        if recommendation is None:
            return None
        equipped_item = self.equip_item(hero_id, str(recommendation["item_id"]))
        return {
            **recommendation,
            "equipped_item_id": equipped_item.item_id,
            "equipped_display_name": equipped_item.display_name,
        }

    def best_upgrade_lines(self) -> list[str]:
        lines = ["最佳升级建议："]
        recommendations = []
        for hero_id, _position in self.party:
            recommendation = self.recommend_upgrade_for_hero(hero_id)
            if recommendation is not None:
                recommendations.append(recommendation)
        if not recommendations:
            return ["最佳升级建议：", "- 当前没有正收益升级"]
        recommendations.sort(key=lambda entry: float(entry["score_delta"]), reverse=True)
        for recommendation in recommendations:
            lines.extend(
                [
                    f"- {hero_name(str(recommendation['hero_id']))}：{localize_loot_name(str(recommendation['display_name']))}",
                    f"  部位：{slot_name(str(recommendation['slot']))}",
                    f"  候选评分：{recommendation['score']:.2f}",
                    f"  当前装备评分：{recommendation['equipped_score']:.2f}",
                    f"  提升值：{recommendation['score_delta']:.2f}",
                    f"  结论：{'升级' if recommendation['verdict'] == 'upgrade' else '平替'}",
                ]
            )
        return lines

    def roster_lines(self) -> list[str]:
        active = {hero_id: position for hero_id, position in self.party}
        lines: list[str] = []
        for hero_id in ALL_HERO_IDS:
            hero = HERO_TEMPLATES[hero_id]
            level = self.hero_level(hero_id)
            xp = self.hero_xp(hero_id)
            xp_to_next = self.xp_to_next_level(level)
            specialization = self.hero_specialization(hero_id) or "none"
            if hero_id in active:
                lines.append(
                    f"- {hero_name(hero_id)}：职业={role_name(hero.role)} 推荐站位={position_name(hero.preferred_position)} 状态={party_status_name('party')} 当前站位={position_name(active[hero_id])} 等级={level} 经验={xp}/{xp_to_next} 专精={specialization_name(specialization)}"
                )
            else:
                lines.append(
                    f"- {hero_name(hero_id)}：职业={role_name(hero.role)} 推荐站位={position_name(hero.preferred_position)} 状态={party_status_name('bench')} 等级={level} 经验={xp}/{xp_to_next} 专精={specialization_name(specialization)}"
                )
        return lines

    def party_summary(self) -> str:
        role_counts = Counter(HERO_TEMPLATES[hero_id].role for hero_id, _position in self.party)
        frontline_count = sum(1 for _hero_id, position in self.party if position == "frontline")
        backline_count = sum(1 for _hero_id, position in self.party if position == "backline")
        ordered_roles = ["tank", "melee_dps", "ranged_dps", "mage", "support"]
        role_text = ", ".join(f"{role_name(role)}={role_counts.get(role, 0)}" for role in ordered_roles)
        return (
            f"前排={frontline_count}/{FRONTLINE_LIMIT}, "
            f"后排={backline_count}/{BACKLINE_LIMIT}, "
            f"{role_text}"
        )

    def assign_party_member(self, hero_id: str, position: str, slot_index: int) -> None:
        self._validate_hero_id(hero_id)
        self._validate_position(position)
        if slot_index < 0 or slot_index >= PARTY_SIZE:
            raise ValueError(f"slot_index must be between 0 and {PARTY_SIZE - 1}")
        updated_party = list(self.party)
        updated_party = [(member_id, member_pos) for member_id, member_pos in updated_party if member_id != hero_id]
        while len(updated_party) < PARTY_SIZE:
            updated_party.append(("", "backline"))
        updated_party[slot_index] = (hero_id, position)
        compacted = [entry for entry in updated_party if entry[0]]
        self._validate_party(compacted)
        self.party = compacted

    def move_party_member(self, hero_id: str, position: str) -> None:
        self._validate_position(position)
        updated_party = list(self.party)
        for idx, (member_id, _member_pos) in enumerate(updated_party):
            if member_id == hero_id:
                updated_party[idx] = (hero_id, position)
                self._validate_party(updated_party)
                self.party = updated_party
                return
        raise ValueError(f"hero {hero_id} is not currently in party")

    def swap_party_positions(self, hero_a: str, hero_b: str) -> None:
        updated_party = list(self.party)
        index_a = next((idx for idx, (hero_id, _position) in enumerate(updated_party) if hero_id == hero_a), None)
        index_b = next((idx for idx, (hero_id, _position) in enumerate(updated_party) if hero_id == hero_b), None)
        if index_a is None or index_b is None:
            raise ValueError("both heroes must already be in party")
        hero_a_entry = updated_party[index_a]
        hero_b_entry = updated_party[index_b]
        updated_party[index_a] = (hero_a_entry[0], hero_b_entry[1])
        updated_party[index_b] = (hero_b_entry[0], hero_a_entry[1])
        self._validate_party(updated_party)
        self.party = updated_party

    def record_stage_result(self, stage: int, victory: bool) -> bool:
        if not victory:
            self.current_stage = max(1, min(stage, self.highest_stage_unlocked))
            return False
        next_stage = stage + 1
        self.highest_stage_unlocked = max(self.highest_stage_unlocked, next_stage)
        self.current_stage = next_stage
        return True

    def set_stage(self, stage: int) -> int:
        self.current_stage = max(1, min(stage, self.highest_stage_unlocked))
        return self.current_stage

    def to_dict(self) -> dict[str, Any]:
        return {
            "gold": self.gold,
            "materials": self.materials,
            "inventory": [self._loot_to_dict(item) for item in self.inventory],
            "hero_loadouts": {
                hero_id: {slot: self._loot_to_dict(item) for slot, item in slots.items()}
                for hero_id, slots in self.hero_loadouts.items()
            },
            "party": [[hero_id, position] for hero_id, position in self.party],
            "current_stage": self.current_stage,
            "highest_stage_unlocked": self.highest_stage_unlocked,
            "hero_progress": self.hero_progress,
            "hero_specializations": self.hero_specializations,
            "extracted_aspects": list(self.extracted_aspects),
        }

    def save(self, path: Path | str = DEFAULT_SAVE_PATH) -> Path:
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))
        return save_path

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlayerProfile":
        inventory = [cls._loot_from_dict(entry) for entry in payload.get("inventory", [])]
        hero_loadouts = {
            hero_id: {slot: cls._loot_from_dict(item_payload) for slot, item_payload in slots.items()}
            for hero_id, slots in payload.get("hero_loadouts", {}).items()
        }
        party = [tuple(entry) for entry in payload.get("party", DEFAULT_PARTY)]
        return cls(
            gold=int(payload.get("gold", 0)),
            materials=int(payload.get("materials", 0)),
            inventory=inventory,
            hero_loadouts=hero_loadouts,
            party=party,
            current_stage=int(payload.get("current_stage", 1)),
            highest_stage_unlocked=int(payload.get("highest_stage_unlocked", 1)),
            hero_progress=cls._coerce_hero_progress_payload(payload.get("hero_progress", {})),
            hero_specializations=cls._coerce_hero_specializations_payload(payload.get("hero_specializations", {})),
            extracted_aspects=[str(aspect_id) for aspect_id in payload.get("extracted_aspects", [])],
        )

    @classmethod
    def load(cls, path: Path | str = DEFAULT_SAVE_PATH) -> "PlayerProfile":
        save_path = Path(path)
        if not save_path.exists():
            return create_default_profile()
        payload = json.loads(save_path.read_text())
        return cls.from_dict(payload)

    @staticmethod
    def _loot_to_dict(item: LootItem) -> dict[str, Any]:
        return {
            "item_id": item.item_id,
            "display_name": item.display_name,
            "slot": item.slot,
            "rarity": item.rarity,
            "item_power": item.item_power,
            "main_stat": item.main_stat,
            "affixes": item.affixes,
            "legendary_aspect": item.legendary_aspect,
            "recommended_hero_ids": list(item.recommended_hero_ids),
            "strengthen_level": item.strengthen_level,
            "reroll_count": item.reroll_count,
            "refine_count": item.refine_count,
        }

    @staticmethod
    def _loot_from_dict(payload: dict[str, Any]) -> LootItem:
        return LootItem(
            item_id=str(payload["item_id"]),
            display_name=str(payload["display_name"]),
            slot=str(payload["slot"]),
            rarity=str(payload["rarity"]),
            item_power=int(payload["item_power"]),
            main_stat=dict(payload.get("main_stat", {})),
            affixes=list(payload.get("affixes", [])),
            legendary_aspect=payload.get("legendary_aspect"),
            recommended_hero_ids=[str(hero_id) for hero_id in payload.get("recommended_hero_ids", [])],
            strengthen_level=int(payload.get("strengthen_level", 0)),
            reroll_count=int(payload.get("reroll_count", 0)),
            refine_count=int(payload.get("refine_count", 0)),
        )

    @staticmethod
    def _coerce_hero_progress_payload(payload: Any) -> dict[str, dict[str, int]]:
        if not isinstance(payload, dict):
            return {}
        coerced: dict[str, dict[str, int]] = {}
        for hero_id, progress in payload.items():
            if isinstance(progress, dict):
                coerced[str(hero_id)] = {
                    "level": int(progress.get("level", 1)),
                    "xp": int(progress.get("xp", 0)),
                }
        return coerced

    @staticmethod
    def _coerce_hero_specializations_payload(payload: Any) -> dict[str, str]:
        if not isinstance(payload, dict):
            return {}
        return {str(hero_id): str(specialization) for hero_id, specialization in payload.items() if specialization}

    def _normalize_hero_progress(self, payload: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
        normalized = build_default_hero_progress()
        for hero_id, progress in payload.items():
            if hero_id not in HERO_TEMPLATES:
                continue
            normalized[hero_id] = {
                "level": max(1, min(int(progress.get("level", 1)), MAX_HERO_LEVEL)),
                "xp": max(0, int(progress.get("xp", 0))),
            }
        return normalized

    def _normalize_hero_specializations(self, payload: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for hero_id, specialization in payload.items():
            if hero_id not in HERO_TEMPLATES:
                continue
            if specialization in ROLE_SPECIALIZATIONS.get(HERO_TEMPLATES[hero_id].role, ()):
                normalized[hero_id] = specialization
        return normalized

    def _score_stat_value(self, weights: dict[str, float], stat_name: str, value: Any) -> float:
        weight = float(weights.get(stat_name, 0.0))
        return weight * float(value)

    def _score_affix(self, role: str, affix: dict[str, Any]) -> float:
        affix_type = str(affix.get("type", ""))
        value = affix.get("value", 0)
        weights = ROLE_STAT_WEIGHTS.get(role, {})
        stat_name = AFFIX_STAT_MAP.get(affix_type, affix_type)
        return self._score_stat_value(weights, stat_name, value)

    def _remove_inventory_item(self, item_id: str) -> LootItem:
        for index, item in enumerate(self.inventory):
            if item.item_id == item_id:
                return self.inventory.pop(index)
        raise ValueError(f"item {item_id} not found in inventory")

    def _validate_hero_id(self, hero_id: str) -> None:
        if hero_id not in HERO_TEMPLATES:
            raise ValueError(f"unknown hero_id: {hero_id}")

    def _validate_position(self, position: str) -> None:
        if position not in {"frontline", "backline"}:
            raise ValueError("position must be 'frontline' or 'backline'")

    def _validate_party(self, party: list[tuple[str, str]]) -> None:
        if len(party) != PARTY_SIZE:
            raise ValueError(f"party must contain exactly {PARTY_SIZE} heroes")
        hero_ids = [hero_id for hero_id, _position in party]
        if len(set(hero_ids)) != len(hero_ids):
            raise ValueError("party cannot contain duplicate heroes")
        for hero_id, position in party:
            self._validate_hero_id(hero_id)
            self._validate_position(position)
        frontline_count = sum(1 for _hero_id, position in party if position == "frontline")
        backline_count = sum(1 for _hero_id, position in party if position == "backline")
        if frontline_count > FRONTLINE_LIMIT:
            raise ValueError("frontline limit exceeded")
        if backline_count > BACKLINE_LIMIT:
            raise ValueError("backline limit exceeded")


def create_default_profile() -> PlayerProfile:
    return PlayerProfile()
