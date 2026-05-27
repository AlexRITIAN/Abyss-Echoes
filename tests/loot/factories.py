from __future__ import annotations

from abyss_echoes.loot.models import (
    AffixProfile,
    BuildContext,
    EquippedItemReference,
    ItemStaticProfile,
    LegendaryEffectProfile,
    WorkshopState,
)


def make_affix(
    *,
    family: str = "damage",
    key: str | None = None,
    value: float = 10.0,
    min_roll: float = 0.0,
    max_roll: float = 20.0,
    normalized_roll: float = 0.5,
    is_star: bool = False,
    is_core: bool = False,
) -> AffixProfile:
    return AffixProfile(
        affix_family=family,
        affix_key=key or family,
        value=value,
        min_roll=min_roll,
        max_roll=max_roll,
        normalized_roll=normalized_roll,
        is_star=is_star,
        is_core_for_current_item_type=is_core,
    )



def make_effect(
    *,
    effect_id: str = "effect.test",
    name: str = "测试特效",
    scope: str = "numeric",
    granted_by: str = "world_legendary",
    power_band: str = "bridge",
    build_tags: list[str] | None = None,
    is_boss_identity_effect: bool = False,
    is_rulebreaking: bool = False,
    extractable: bool = False,
    imprintable: bool = False,
) -> LegendaryEffectProfile:
    return LegendaryEffectProfile(
        effect_id=effect_id,
        name=name,
        effect_scope=scope,
        granted_by=granted_by,
        power_band=power_band,
        build_tags=list(build_tags or []),
        is_boss_identity_effect=is_boss_identity_effect,
        is_rulebreaking=is_rulebreaking,
        extractable=extractable,
        imprintable=imprintable,
    )



def make_item(**overrides: object) -> ItemStaticProfile:
    is_ancestral = bool(overrides.get("is_ancestral", False))
    star_affix_count = int(overrides.get("star_affix_count", 0))
    item_power = int(overrides.get("item_power", 900 if is_ancestral else 850))
    workshop_state = overrides.get("workshop_state")
    if not isinstance(workshop_state, WorkshopState):
        workshop_state = WorkshopState()

    return ItemStaticProfile(
        item_id=str(overrides.get("item_id", "item.test")),
        name=str(overrides.get("name", "测试装备")),
        slot=str(overrides.get("slot", "weapon")),
        rarity=str(overrides.get("rarity", "legendary")),
        item_power=item_power,
        is_ancestral=is_ancestral,
        star_affix_count=star_affix_count,
        source_type=str(overrides.get("source_type", "world_drop")),
        source_boss=overrides.get("source_boss"),
        legendary_tier=str(overrides.get("legendary_tier", "world_legendary" if str(overrides.get("rarity", "legendary")) == "legendary" else "none")),
        primary_element=str(overrides.get("primary_element", "neutral")),
        affixes=list(overrides.get("affixes", [])),
        legendary_effects=list(overrides.get("legendary_effects", [])),
        workshop_state=workshop_state,
        is_first_discovery=bool(overrides.get("is_first_discovery", False)),
        locked=bool(overrides.get("locked", False)),
        enchanted=bool(overrides.get("enchanted", False)),
    )



def make_build(**overrides: object) -> BuildContext:
    equipped = overrides.get("equipped")
    if equipped is None:
        equipped = {
            "weapon": EquippedItemReference(
                slot="weapon",
                equipped_item_id="equipped.weapon",
                effective_power_score=850.0,
                build_tags=["burn"],
            )
        }

    return BuildContext(
        player_level=int(overrides.get("player_level", 70)),
        current_element=str(overrides.get("current_element", "fire")),
        main_skill_id=str(overrides.get("main_skill_id", "firebolt")),
        secondary_skill_id=str(overrides.get("secondary_skill_id", "inferno")),
        passive_skill_ids=list(overrides.get("passive_skill_ids", ["p1", "p2", "p3", "p4", "p5"])),
        current_build_tags=list(overrides.get("current_build_tags", ["burn"])),
        future_build_tags=list(overrides.get("future_build_tags", ["chain"])),
        preferred_affix_families=list(overrides.get("preferred_affix_families", ["damage", "fire_damage"])),
        avoided_affix_families=list(overrides.get("avoided_affix_families", ["thorns"])),
        equipped=equipped,
        unlocked_boss_paths=list(overrides.get("unlocked_boss_paths", [])),
        discovered_legendary_effect_ids=list(overrides.get("discovered_legendary_effect_ids", [])),
    )
