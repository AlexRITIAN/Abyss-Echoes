from abyss_echoes.loot.evaluator import evaluate_drop

from .factories import make_affix, make_build, make_effect, make_item



def test_high_current_fit_and_slot_delta_becomes_upgrade_candidate() -> None:
    build = make_build(
        current_element="fire",
        current_build_tags=["burn", "ignite"],
        preferred_affix_families=["damage", "fire_damage", "crit"],
        equipped={
            "weapon": make_build().equipped["weapon"].__class__(
                slot="weapon",
                equipped_item_id="old.weapon",
                effective_power_score=780.0,
                build_tags=["burn", "ignite"],
            )
        },
    )
    item = make_item(
        slot="weapon",
        item_power=870,
        source_type="abyss_drop",
        primary_element="fire",
        affixes=[
            make_affix(family="damage", normalized_roll=0.95, is_core=True),
            make_affix(family="fire_damage", normalized_roll=0.9, is_core=True),
            make_affix(family="crit", normalized_roll=0.85),
        ],
        legendary_effects=[make_effect(build_tags=["burn", "ignite"], power_band="core")],
    )

    evaluation = evaluate_drop(item, build)

    assert evaluation.scores.current_build_fit >= 70
    assert evaluation.scores.same_slot_upgrade_score >= 60
    assert evaluation.verdict == "upgrade_candidate"



def test_future_fit_can_preserve_offbuild_item() -> None:
    build = make_build(
        current_element="fire",
        current_build_tags=["burn"],
        future_build_tags=["chain", "shock"],
        preferred_affix_families=["damage"],
        equipped={
            "amulet": make_build().equipped["weapon"].__class__(
                slot="amulet",
                equipped_item_id="old.amulet",
                effective_power_score=880.0,
                build_tags=["burn"],
            )
        },
    )
    item = make_item(
        slot="amulet",
        primary_element="lightning",
        affixes=[make_affix(family="lightning_damage", normalized_roll=0.85)],
        legendary_effects=[make_effect(build_tags=["chain", "shock"], power_band="branch")],
    )

    evaluation = evaluate_drop(item, build)

    assert evaluation.scores.current_build_fit < evaluation.scores.future_build_fit
    assert evaluation.scores.future_build_fit >= 55
    assert evaluation.verdict == "situational"
