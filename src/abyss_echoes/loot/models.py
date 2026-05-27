from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from abyss_echoes.loot.config import MAX_STRENGTHEN_LEVEL

Element: TypeAlias = Literal["fire", "ice", "lightning", "neutral"]
Rarity: TypeAlias = Literal["common", "magic", "rare", "legendary", "unique"]
Slot: TypeAlias = Literal[
    "weapon",
    "offhand",
    "amulet",
    "ring_1",
    "ring_2",
    "head",
    "chest",
    "legs",
    "hands",
    "shoulders",
    "bracers",
]
SourceType: TypeAlias = Literal["world_drop", "abyss_drop", "regional_boss", "crafted_output"]
LegendaryTier: TypeAlias = Literal["none", "world_legendary", "boss_legendary", "special_unique"]
EffectScope: TypeAlias = Literal["numeric", "mechanic", "rulebreaking"]
PowerBand: TypeAlias = Literal["bridge", "branch", "core", "chase"]
Verdict: TypeAlias = Literal[
    "trash",
    "salvage_candidate",
    "situational",
    "upgrade_candidate",
    "lock_candidate",
]
PresentationLayer: TypeAlias = Literal["L1_interrupt", "L2_attention", "L3_folded", "L4_silent"]
WorkshopAction: TypeAlias = Literal["none", "strengthen", "reroll", "refine", "extract"]
ReasonCategory: TypeAlias = Literal["rarity", "current", "future", "salvage", "workshop", "warning"]


@dataclass(slots=True)
class AffixProfile:
    affix_family: str
    affix_key: str
    value: float
    min_roll: float
    max_roll: float
    normalized_roll: float
    is_star: bool = False
    is_core_for_current_item_type: bool = False


@dataclass(slots=True)
class LegendaryEffectProfile:
    effect_id: str
    name: str
    effect_scope: EffectScope
    granted_by: LegendaryTier
    power_band: PowerBand
    build_tags: list[str] = field(default_factory=list)
    is_boss_identity_effect: bool = False
    is_rulebreaking: bool = False
    extractable: bool = False
    imprintable: bool = False


@dataclass(slots=True)
class WorkshopState:
    strengthen_level: int = 0
    reroll_count: int = 0
    refine_count: int = 0
    imprinted_effect_id: str | None = None
    can_strengthen: bool = True
    can_reroll: bool = True
    can_refine: bool = True
    can_extract: bool = False
    can_imprint: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.strengthen_level <= MAX_STRENGTHEN_LEVEL:
            raise ValueError(f"strengthen_level must be between 0 and {MAX_STRENGTHEN_LEVEL}")
        if self.reroll_count < 0:
            raise ValueError("reroll_count must be non-negative")
        if self.refine_count < 0:
            raise ValueError("refine_count must be non-negative")


@dataclass(slots=True)
class ItemStaticProfile:
    item_id: str
    name: str
    slot: Slot
    rarity: Rarity
    item_power: int
    is_ancestral: bool
    star_affix_count: int
    source_type: SourceType
    source_boss: str | None = None
    legendary_tier: LegendaryTier = "none"
    primary_element: Element = "neutral"
    affixes: list[AffixProfile] = field(default_factory=list)
    legendary_effects: list[LegendaryEffectProfile] = field(default_factory=list)
    workshop_state: WorkshopState = field(default_factory=WorkshopState)
    is_first_discovery: bool = False
    locked: bool = False
    enchanted: bool = False


@dataclass(slots=True)
class EquippedItemReference:
    slot: Slot
    equipped_item_id: str | None
    effective_power_score: float
    build_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BuildContext:
    player_level: int
    current_element: Element
    main_skill_id: str
    secondary_skill_id: str
    passive_skill_ids: list[str]
    current_build_tags: list[str] = field(default_factory=list)
    future_build_tags: list[str] = field(default_factory=list)
    preferred_affix_families: list[str] = field(default_factory=list)
    avoided_affix_families: list[str] = field(default_factory=list)
    equipped: dict[Slot, EquippedItemReference] = field(default_factory=dict)
    unlocked_boss_paths: list[str] = field(default_factory=list)
    discovered_legendary_effect_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScoreBreakdown:
    current_build_fit: float
    same_slot_upgrade_score: float
    future_build_fit: float
    source_rarity_score: float
    salvage_value_score: float
    workshop_potential_score: float


@dataclass(slots=True)
class ProtectionFlags:
    protected_source: bool = False
    protected_by_boss_identity: bool = False
    protected_by_ancestral: bool = False
    protected_by_star_affix: bool = False
    protected_by_rulebreaking: bool = False
    protected_by_chase: bool = False


@dataclass(slots=True)
class ReasonRecord:
    code: str
    category: ReasonCategory
    weight: float


@dataclass(slots=True)
class DropEvaluation:
    item_id: str
    scores: ScoreBreakdown
    protections: ProtectionFlags
    verdict: Verdict
    auto_lock_suggested: bool
    auto_salvage_suggested: bool
    workshop_action: WorkshopAction = "none"
    reasons: list[ReasonRecord] = field(default_factory=list)
    duplicate_group_id: str | None = None
    representative_item_id: str | None = None


@dataclass(slots=True)
class PresentationBadge:
    text: str
    priority: int


@dataclass(slots=True)
class PresentationLine:
    label: str
    value: str
    priority: int = 0


@dataclass(slots=True)
class DropPresentation:
    item_id: str
    layer: PresentationLayer
    title_line: str
    subtitle_line: str | None = None
    badges: list[PresentationBadge] = field(default_factory=list)
    summary_lines: list[PresentationLine] = field(default_factory=list)
    reason_lines: list[str] = field(default_factory=list)
    recommended_action_line: str | None = None
    folded_group_label: str | None = None
    folded_children_count: int = 0
