from abyss_echoes.loot.evaluator import evaluate_drop
from abyss_echoes.loot.presentation import build_drop_presentation

from .factories import make_affix, make_build, make_effect, make_item



def test_trash_item_goes_to_l4_silent() -> None:
    item = make_item(
        rarity="common",
        legendary_tier="none",
        slot="bracers",
        item_power=620,
        source_type="world_drop",
        primary_element="ice",
        affixes=[make_affix(family="thorns", normalized_roll=0.1)],
        legendary_effects=[],
    )

    evaluation = evaluate_drop(item, make_build())
    presentation = build_drop_presentation(item, evaluation)

    assert evaluation.verdict == "trash"
    assert presentation.layer == "L4_silent"



def test_protected_item_uses_attention_floor_in_presentation() -> None:
    item = make_item(
        source_type="regional_boss",
        source_boss="ash_guardian",
        legendary_tier="boss_legendary",
        primary_element="ice",
        affixes=[make_affix(family="thorns", normalized_roll=0.2)],
        legendary_effects=[
            make_effect(
                granted_by="boss_legendary",
                build_tags=["freeze"],
                is_boss_identity_effect=True,
            )
        ],
    )

    evaluation = evaluate_drop(item, make_build(current_build_tags=["burn"], future_build_tags=[]))
    presentation = build_drop_presentation(item, evaluation)

    assert presentation.layer == "L2_attention"
    assert any(badge.text == "[BOSS]" for badge in presentation.badges)
