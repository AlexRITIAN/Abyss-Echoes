import pytest

from abyss_echoes.loot.evaluator import evaluate_drop
from abyss_echoes.loot.models import WorkshopState

from .factories import make_affix, make_build, make_effect, make_item



def test_boss_item_never_chooses_extract_action() -> None:
    item = make_item(
        source_type="regional_boss",
        source_boss="storm_archon",
        legendary_tier="boss_legendary",
        affixes=[make_affix(family="thorns", normalized_roll=0.1)],
        legendary_effects=[
            make_effect(
                granted_by="boss_legendary",
                scope="rulebreaking",
                power_band="chase",
                build_tags=["storm_loop"],
                is_rulebreaking=True,
                extractable=True,
                imprintable=True,
            )
        ],
        workshop_state=WorkshopState(can_extract=True, can_imprint=True),
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))

    assert evaluation.workshop_action != "extract"



def test_upgrade_candidate_prefers_strengthen_when_below_plus_eight() -> None:
    item = make_item(
        slot="weapon",
        primary_element="fire",
        item_power=875,
        affixes=[
            make_affix(family="damage", normalized_roll=0.9, is_core=True),
            make_affix(family="fire_damage", normalized_roll=0.92, is_core=True),
        ],
        legendary_effects=[make_effect(build_tags=["burn"], power_band="core")],
        workshop_state=WorkshopState(strengthen_level=3),
    )

    evaluation = evaluate_drop(item, make_build())

    assert evaluation.verdict == "upgrade_candidate"
    assert evaluation.workshop_action == "strengthen"



def test_situational_item_can_choose_reroll() -> None:
    item = make_item(
        slot="amulet",
        primary_element="fire",
        item_power=860,
        affixes=[make_affix(family="damage", normalized_roll=0.8, is_core=True)],
        legendary_effects=[make_effect(build_tags=["burn"], power_band="branch")],
        workshop_state=WorkshopState(reroll_count=0, can_reroll=True, can_strengthen=False),
    )

    evaluation = evaluate_drop(item, make_build())

    assert evaluation.verdict == "situational"
    assert evaluation.workshop_action == "reroll"



def test_ancestral_situational_item_can_choose_refine() -> None:
    item = make_item(
        is_ancestral=True,
        item_power=900,
        primary_element="ice",
        affixes=[make_affix(family="chain_damage", normalized_roll=0.85)],
        legendary_effects=[make_effect(build_tags=["chain"], power_band="branch")],
        workshop_state=WorkshopState(refine_count=0, can_refine=True, can_strengthen=False, can_reroll=False),
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=["chain"]))

    assert evaluation.verdict == "situational"
    assert evaluation.workshop_action == "refine"



def test_salvage_candidate_world_legendary_can_choose_extract() -> None:
    item = make_item(
        rarity="legendary",
        legendary_tier="world_legendary",
        item_power=110,
        affixes=[make_affix(family="thorns", normalized_roll=0.1)],
        legendary_effects=[make_effect(build_tags=["thorns"], extractable=True, power_band="bridge")],
        workshop_state=WorkshopState(can_extract=True, can_strengthen=False, can_reroll=False, can_refine=False),
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))

    assert evaluation.verdict == "salvage_candidate"
    assert evaluation.workshop_action == "extract"



def test_workshop_state_rejects_strengthen_above_plus_eight() -> None:
    with pytest.raises(ValueError):
        WorkshopState(strengthen_level=9)



def test_workshop_state_rejects_negative_counts() -> None:
    with pytest.raises(ValueError):
        WorkshopState(reroll_count=-1)

    with pytest.raises(ValueError):
        WorkshopState(refine_count=-1)



def test_workshop_state_allows_plus_eight_cap() -> None:
    state = WorkshopState(strengthen_level=8)

    assert state.strengthen_level == 8



def test_rulebreaking_item_never_chooses_extract_even_when_salvage_candidate() -> None:
    item = make_item(
        rarity="legendary",
        legendary_tier="world_legendary",
        item_power=105,
        affixes=[make_affix(family="thorns", normalized_roll=0.1)],
        legendary_effects=[
            make_effect(
                scope="rulebreaking",
                build_tags=["offbuild"],
                is_rulebreaking=True,
                extractable=True,
                power_band="bridge",
            )
        ],
        workshop_state=WorkshopState(can_extract=True, can_strengthen=False, can_reroll=False, can_refine=False),
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))

    assert evaluation.workshop_action != "extract"
    assert evaluation.verdict in {"situational", "lock_candidate"}
