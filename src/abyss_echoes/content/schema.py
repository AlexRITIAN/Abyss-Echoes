from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BalanceTag = Literal["hard_rule", "mvp_locked", "post_playtest_tunable"]
Element = Literal["fire", "ice", "lightning"]
SkillType = Literal["main", "secondary", "passive"]
DropSource = Literal["world", "abyss", "boss"]


@dataclass(slots=True)
class SkillTemplateRow:
    skill_id: str
    display_name: str
    skill_type: SkillType
    element: Element
    template_index: int
    unlock_level: int
    base_damage_coeff: float
    targeting: str
    balance_tag: BalanceTag
    energy_gain: int = 0
    energy_cost: int = 0
    apply_tags: list[str] = field(default_factory=list)
    consume_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PassivePoolCounts:
    fire: int
    ice: int
    lightning: int
    generic: int
    total: int
    balance_tag: BalanceTag


@dataclass(slots=True)
class PassiveSlotUnlock:
    unlock_level: int
    slot_count: int


@dataclass(slots=True)
class SkillLevelCaps:
    main: int
    secondary: int
    passive: int


@dataclass(slots=True)
class ActiveSkillUpgradeUnlock:
    skill_level: int
    unlock_group: int


@dataclass(slots=True)
class ProgressionConfig:
    passive_pool_counts: PassivePoolCounts
    passive_slots: list[PassiveSlotUnlock] = field(default_factory=list)
    skill_level_caps: SkillLevelCaps | None = None
    active_skill_upgrade_unlocks: list[ActiveSkillUpgradeUnlock] = field(default_factory=list)


@dataclass(slots=True)
class BossDefinition:
    boss_id: str
    display_name: str
    element: Element
    exclusive_family: str
    arena_tag: str
    balance_tag: BalanceTag


@dataclass(slots=True)
class BossRankRow:
    rank: int
    unlock_abyss_floor: int
    hp_multiplier: float
    damage_multiplier: float
    exclusive_legendary_drop_rate: float
    ancestral_900_drop_rate: float
    balance_tag: BalanceTag


@dataclass(slots=True)
class BossFailureRewards:
    key_cost: int
    fragment_refund_flat: int
    first_daily_fail_bonus_fragments: int
    boss_essence_min: int
    boss_essence_max: int
    balance_tag: BalanceTag


@dataclass(slots=True)
class BossContent:
    bosses: list[BossDefinition] = field(default_factory=list)
    boss_rank_table: list[BossRankRow] = field(default_factory=list)
    boss_failure_rewards: BossFailureRewards | None = None


@dataclass(slots=True)
class LevelingRarityWeights:
    phase_id: str
    drops_per_clear: list[int]
    rarity_weights: dict[str, float]
    balance_tag: BalanceTag


@dataclass(slots=True)
class EndgameDropTable:
    table_id: str
    source: DropSource
    drops_per_clear: list[int]
    legendary_rate: float | None
    item_power_850_rate: float
    item_power_900_rate: float
    notes: list[str] = field(default_factory=list)
    balance_tag: BalanceTag = "mvp_locked"
    boss_exclusive_rate: float | None = None
    abyss_exclusive_legendary_rate: float | None = None


@dataclass(slots=True)
class StarAffixRules:
    only_item_power: int
    per_affix_star_rate: float
    multi_star_share_cap_within_900_drops: float
    balance_tag: BalanceTag


@dataclass(slots=True)
class DropConfig:
    leveling_rarity_weights: list[LevelingRarityWeights] = field(default_factory=list)
    endgame_drop_tables: list[EndgameDropTable] = field(default_factory=list)
    star_affix_rules: StarAffixRules | None = None


@dataclass(slots=True)
class FloorBandFragmentYield:
    floor_band: list[int]
    base_fragments: int
    first_clear_bonus: int


@dataclass(slots=True)
class StreakBonus:
    clears_required: int
    bonus_fragments: int


@dataclass(slots=True)
class KeyEconomy:
    fragments_per_key: int
    abyss_fragment_yield: list[FloorBandFragmentYield] = field(default_factory=list)
    highest_floor_streak_bonus: StreakBonus | None = None
    balance_tag: BalanceTag = "mvp_locked"


@dataclass(slots=True)
class CraftCostRow:
    action_id: str
    gold: int
    arcane_shards: int
    legendary_embers: int
    boss_essence: int
    balance_tag: BalanceTag


@dataclass(slots=True)
class MaterialSourceRule:
    material_id: str
    primary_source: str
    notes: list[str] = field(default_factory=list)
    balance_tag: BalanceTag = "mvp_locked"


@dataclass(slots=True)
class EconomyConfig:
    key_economy: KeyEconomy | None = None
    strengthening_costs: list[CraftCostRow] = field(default_factory=list)
    enchant_costs: list[CraftCostRow] = field(default_factory=list)
    imprint_costs: list[CraftCostRow] = field(default_factory=list)
    material_sources: list[MaterialSourceRule] = field(default_factory=list)


@dataclass(slots=True)
class MageRpgContentBundle:
    main_skills: list[SkillTemplateRow] = field(default_factory=list)
    secondary_skills: list[SkillTemplateRow] = field(default_factory=list)
    progression: ProgressionConfig | None = None
    boss_content: BossContent | None = None
    drop_config: DropConfig | None = None
    economy_config: EconomyConfig | None = None

    def skill_rows(self) -> list[SkillTemplateRow]:
        return [*self.main_skills, *self.secondary_skills]
