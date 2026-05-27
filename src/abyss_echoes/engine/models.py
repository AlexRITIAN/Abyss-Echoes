from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from abyss_echoes.i18n import (
    encounter_name,
    encounter_type_name,
    hero_name,
    localize_loot_name,
    rarity_name,
    slot_name,
    theme_name,
    winner_name,
)

Role = Literal["tank", "melee_dps", "ranged_dps", "mage", "support"]
Position = Literal["frontline", "backline"]
DamageType = Literal["physical", "magical", "pure"]

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


@dataclass(slots=True)
class SkillEffect:
    effect_type: str
    value: float | int | None = None
    chance: float = 1.0
    duration: int = 0
    target: str | None = None
    status_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillDefinition:
    skill_id: str
    name: str
    skill_type: str
    targeting: str
    damage_type: DamageType | None
    ratio: float | None
    energy_cost: int = 0
    effects: list[SkillEffect] = field(default_factory=list)


@dataclass(slots=True)
class HeroTemplate:
    hero_id: str
    name: str
    role: Role
    preferred_position: Position
    base_hp: int
    base_atk: int
    base_mag: int
    base_armor: int
    base_resist: int
    base_speed: int
    base_crit_rate: float
    base_crit_damage: float
    basic_skill_id: str
    active_skill_id: str
    passive_skill_id: str


@dataclass(slots=True)
class StatusEffect:
    status_id: str
    source_unit_id: str
    duration: int
    stacks: int = 1
    magnitude: float = 0.0


@dataclass(slots=True)
class ItemDefinition:
    item_id: str
    slot: str
    rarity: str
    item_power: int
    main_stat: dict[str, int | float]
    affixes: list[dict[str, int | float | str]] = field(default_factory=list)
    legendary_aspect: str | None = None


@dataclass(slots=True)
class LootItem:
    item_id: str
    display_name: str
    slot: str
    rarity: str
    item_power: int
    main_stat: dict[str, int | float]
    affixes: list[dict[str, int | float | str]] = field(default_factory=list)
    legendary_aspect: str | None = None
    recommended_hero_ids: list[str] = field(default_factory=list)
    strengthen_level: int = 0
    reroll_count: int = 0
    refine_count: int = 0

    def summary_line(self) -> str:
        recommended = ", ".join(hero_name(hero_id) for hero_id in self.recommended_hero_ids) if self.recommended_hero_ids else "无"
        return f"  * {localize_loot_name(self.display_name)} [{rarity_name(self.rarity)}] 部位={slot_name(self.slot)} 战力={self.item_power} 推荐={recommended}"


@dataclass(slots=True)
class BattleRewards:
    gold: int
    materials: int
    loot: list[LootItem] = field(default_factory=list)


@dataclass(slots=True)
class StageEncounter:
    stage: int
    name: str
    theme: str
    encounter_type: str
    enemy_team: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class BattleLogEntry:
    tag: str
    message: str
    hp_snapshot: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class BattleResult:
    winner: str
    rounds: int
    logs: list[BattleLogEntry]
    rewards: BattleRewards | None = None
    encounter_name: str = ""
    encounter_type: str = ""
    encounter_theme: str = ""
    enemy_summary: str = ""
    analysis: dict[str, Any] | None = None

    def render(self) -> str:
        lines = [f"胜者：{winner_name(self.winner)}", f"回合数：{self.rounds}"]
        if self.encounter_name:
            lines.append(f"遭遇：{encounter_name(self.encounter_name)} [{encounter_type_name(self.encounter_type)}]")
        if self.encounter_theme:
            lines.append(f"主题：{theme_name(self.encounter_theme)}")
        if self.enemy_summary:
            lines.append(f"敌方阵容：{self.enemy_summary}")
        if self.rewards is not None:
            lines.extend(
                [
                    "",
                    "战利品：",
                    f"- 金币：{self.rewards.gold}",
                    f"- 材料：{self.rewards.materials}",
                ]
            )
            if self.rewards.loot:
                lines.append("- 掉落一览：")
                for loot in self.rewards.loot:
                    lines.append(loot.summary_line())
        if self.analysis:
            action_order = self.analysis.get("action_order_snapshot", [])
            skill_casts = self.analysis.get("skill_casts", [])
            lines.extend(
                [
                    "",
                    "战斗分析：",
                    f"- 最高伤害：{self.analysis.get('top_damage', '无')}",
                    f"- 最高治疗：{self.analysis.get('top_healing', '无')}",
                    f"- 首个倒下：{self.analysis.get('first_fall', '无')}",
                    f"- 行动顺序快照：{', '.join(action_order) if action_order else '无'}",
                    f"- 技能施放统计：{', '.join(skill_casts) if skill_casts else '无'}",
                    f"- 原因总结：{self.analysis.get('reason_summary', '无')}",
                ]
            )
        lines.extend(["", "战斗日志："])
        lines.extend(f"[{entry.tag}] {entry.message}" for entry in self.logs)
        return "\n".join(lines)


@dataclass(slots=True)
class UnitStats:
    max_hp: int
    atk: int
    mag: int
    armor: int
    resist: int
    speed: int
    crit_rate: float
    crit_damage: float
    heal_bonus: float = 0.0
    energy_gain_bonus: float = 0.0
    damage_bonus: float = 0.0
    shield_bonus: float = 0.0
    damage_vs_debuffed_bonus: float = 0.0


@dataclass(slots=True)
class BattleUnit:
    unit_id: str
    team_id: str
    formation_index: int
    position: Position
    hero: HeroTemplate
    stats: UnitStats
    current_hp: int
    shield: int = 0
    energy: int = 0
    action_gauge: int = 0
    alive: bool = True
    statuses: list[StatusEffect] = field(default_factory=list)
    equipment_ids: list[str] = field(default_factory=list)
    legendary_aspects: list[str] = field(default_factory=list)
    specialization: str = ""
    skill_ranks: dict[str, int] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.hero.name

    def hp_ratio(self) -> float:
        if self.stats.max_hp <= 0:
            return 0.0
        return max(self.current_hp, 0) / self.stats.max_hp

    def has_status(self, status_id: str) -> bool:
        return any(status.status_id == status_id and status.duration > 0 for status in self.statuses)
