from abyss_echoes.loot.evaluator import evaluate_drop

from .factories import make_affix, make_build, make_effect, make_item



def test_boss_item_never_falls_to_trash() -> None:
    item = make_item(
        source_type="regional_boss",
        source_boss="ash_guardian",
        legendary_tier="boss_legendary",
        primary_element="ice",
        affixes=[make_affix(family="thorns", normalized_roll=0.1)],
        legendary_effects=[
            make_effect(
                granted_by="boss_legendary",
                power_band="core",
                build_tags=["freeze"],
                is_boss_identity_effect=True,
            )
        ],
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))

    assert evaluation.protections.protected_source is True
    assert evaluation.verdict in {"situational", "upgrade_candidate", "lock_candidate"}



def test_ancestral_item_never_auto_salvages() -> None:
    item = make_item(
        is_ancestral=True,
        item_power=900,
        primary_element="ice",
        affixes=[make_affix(family="thorns", normalized_roll=0.1)],
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))

    assert evaluation.protections.protected_by_ancestral is True
    assert evaluation.auto_salvage_suggested is False



def test_star_affix_item_never_auto_salvages() -> None:
    item = make_item(
        is_ancestral=True,
        item_power=900,
        star_affix_count=1,
        affixes=[make_affix(family="thorns", normalized_roll=1.0, is_star=True)],
        legendary_effects=[make_effect(build_tags=["freeze"])],
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))

    assert evaluation.protections.protected_by_star_affix is True
    assert evaluation.auto_salvage_suggested is False
