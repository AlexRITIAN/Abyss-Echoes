from __future__ import annotations

from dataclasses import replace

from abyss_echoes.loot import config
from abyss_echoes.loot.models import (
    BuildContext,
    DropEvaluation,
    ItemStaticProfile,
    ProtectionFlags,
    ReasonRecord,
    ScoreBreakdown,
)



def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))



def validate_static_item_invariants(item: ItemStaticProfile) -> None:
    if item.is_ancestral and item.item_power != 900:
        raise ValueError("ancestral items must have item_power 900")
    if item.star_affix_count > 0 and not item.is_ancestral:
        raise ValueError("star affixes require ancestral items")
    if item.source_boss is not None and item.source_type != "regional_boss":
        raise ValueError("source_boss is only valid for regional_boss items")
    if item.legendary_tier == "boss_legendary" and item.source_type != "regional_boss":
        raise ValueError("boss_legendary items must come from regional_boss")



def _tag_overlap_score(effect_tags: list[str], build_tags: list[str], weight: float) -> float:
    if not effect_tags or not build_tags:
        return 0.0
    overlap = len(set(effect_tags) & set(build_tags))
    return overlap * weight



def _affix_match_score(item: ItemStaticProfile, build: BuildContext) -> tuple[float, float]:
    positive = 0.0
    negative = 0.0
    preferred = set(build.preferred_affix_families)
    avoided = set(build.avoided_affix_families)
    for affix in item.affixes:
        if affix.affix_family in preferred:
            positive += 16.0 * affix.normalized_roll
        if affix.affix_family in avoided:
            negative += 12.0 * max(0.25, affix.normalized_roll)
        if affix.is_core_for_current_item_type:
            positive += 12.0 * affix.normalized_roll
        if affix.is_star:
            positive += 10.0
    return positive, negative



def _candidate_power_score(item: ItemStaticProfile) -> float:
    affix_roll_score = sum(affix.normalized_roll * 8.0 for affix in item.affixes)
    effect_score = sum(config.POWER_BAND_SCORES.get(effect.power_band, 0.0) for effect in item.legendary_effects)
    return item.item_power + affix_roll_score + effect_score + item.star_affix_count * 10.0 + (12.0 if item.is_ancestral else 0.0)



def score_current_build_fit(item: ItemStaticProfile, build: BuildContext) -> float:
    score = 0.0
    if item.primary_element == build.current_element:
        score += 22.0
    elif item.primary_element == "neutral":
        score += 8.0

    positive_affix, negative_affix = _affix_match_score(item, build)
    score += positive_affix - negative_affix

    for effect in item.legendary_effects:
        score += _tag_overlap_score(effect.build_tags, build.current_build_tags, 18.0)
        if effect.effect_scope == "rulebreaking" and set(effect.build_tags) & set(build.current_build_tags):
            score += 8.0

    return clamp_score(score)



def score_same_slot_upgrade(item: ItemStaticProfile, build: BuildContext) -> float:
    equipped = build.equipped.get(item.slot)
    candidate_score = _candidate_power_score(item)
    if equipped is None or equipped.equipped_item_id is None:
        return clamp_score(65.0 + max(0.0, candidate_score - 800.0) * 0.05)

    tag_bonus = len(set(equipped.build_tags) & {tag for effect in item.legendary_effects for tag in effect.build_tags}) * 5.0
    delta = candidate_score - equipped.effective_power_score + tag_bonus
    return clamp_score(50.0 + delta * 0.28)



def score_future_build_fit(item: ItemStaticProfile, build: BuildContext) -> float:
    score = 0.0
    if item.primary_element != build.current_element and item.primary_element != "neutral":
        score += 8.0

    for effect in item.legendary_effects:
        score += _tag_overlap_score(effect.build_tags, build.future_build_tags, 20.0)
        if effect.power_band in {"branch", "core", "chase"} and set(effect.build_tags) & set(build.future_build_tags):
            score += 6.0
        if effect.is_rulebreaking and build.future_build_tags:
            score += 4.0

    for affix in item.affixes:
        if affix.affix_family.endswith("_damage"):
            score += 8.0 * affix.normalized_roll

    return clamp_score(score)



def score_source_rarity(item: ItemStaticProfile) -> float:
    score = config.RARITY_SOURCE_SCORES.get(item.rarity, 0.0)
    score += config.SOURCE_TYPE_SCORES.get(item.source_type, 0.0)
    score += config.LEGENDARY_TIER_SCORES.get(item.legendary_tier, 0.0)
    if item.is_ancestral:
        score += 16.0
    if item.star_affix_count > 0:
        score += 8.0 + item.star_affix_count * 4.0
    for effect in item.legendary_effects:
        score += config.POWER_BAND_SCORES.get(effect.power_band, 0.0)
        if effect.is_boss_identity_effect:
            score += 8.0
        if effect.is_rulebreaking:
            score += 10.0
    return clamp_score(score)



def score_salvage_value(item: ItemStaticProfile) -> float:
    score = 0.0
    if item.rarity == "common":
        score += 8.0
    elif item.rarity == "magic":
        score += 16.0
    elif item.rarity == "rare":
        score += 26.0
    else:
        score += 38.0
    if item.legendary_tier != "none":
        score += 10.0
    if item.is_ancestral:
        score += 12.0
    if item.rarity in {"common", "magic"} and item.item_power <= 120 and not item.legendary_effects:
        score += 16.0
    return clamp_score(score)



def score_workshop_potential(item: ItemStaticProfile) -> float:
    score = 0.0
    state = item.workshop_state
    if state.can_strengthen and state.strengthen_level < config.MAX_STRENGTHEN_LEVEL:
        score += 18.0
    if state.can_reroll and state.reroll_count == 0:
        score += 12.0
    if state.can_refine and state.refine_count == 0:
        score += 10.0
    if state.can_extract and any(effect.extractable for effect in item.legendary_effects):
        score += 8.0
    if item.is_ancestral:
        score += 6.0
    return clamp_score(score)



def normalize_score_breakdown(scores: ScoreBreakdown) -> ScoreBreakdown:
    return ScoreBreakdown(
        current_build_fit=clamp_score(scores.current_build_fit),
        same_slot_upgrade_score=clamp_score(scores.same_slot_upgrade_score),
        future_build_fit=clamp_score(scores.future_build_fit),
        source_rarity_score=clamp_score(scores.source_rarity_score),
        salvage_value_score=clamp_score(scores.salvage_value_score),
        workshop_potential_score=clamp_score(scores.workshop_potential_score),
    )



def compute_protection_flags(item: ItemStaticProfile) -> ProtectionFlags:
    protected_by_boss_identity = item.source_type in config.PROTECTED_SOURCE_TYPES or any(
        effect.is_boss_identity_effect for effect in item.legendary_effects
    )
    protected_by_ancestral = item.is_ancestral and item.item_power == 900
    protected_by_star_affix = item.star_affix_count > 0 or any(affix.is_star for affix in item.affixes)
    protected_by_rulebreaking = any(effect.is_rulebreaking or effect.effect_scope == "rulebreaking" for effect in item.legendary_effects)
    protected_by_chase = any(effect.power_band == "chase" for effect in item.legendary_effects)
    protected_source = any(
        [
            protected_by_boss_identity,
            protected_by_ancestral,
            protected_by_star_affix,
            protected_by_rulebreaking,
            protected_by_chase,
        ]
    )
    return ProtectionFlags(
        protected_source=protected_source,
        protected_by_boss_identity=protected_by_boss_identity,
        protected_by_ancestral=protected_by_ancestral,
        protected_by_star_affix=protected_by_star_affix,
        protected_by_rulebreaking=protected_by_rulebreaking,
        protected_by_chase=protected_by_chase,
    )



def assign_verdict(item: ItemStaticProfile, scores: ScoreBreakdown, protections: ProtectionFlags) -> str:
    thresholds = config.VERDICT_THRESHOLDS
    verdict = "trash"

    if protections.protected_by_chase or protections.protected_by_rulebreaking:
        if scores.source_rarity_score >= thresholds["lock_rarity"] or item.is_first_discovery:
            verdict = "lock_candidate"
        else:
            verdict = "situational"
    elif scores.current_build_fit >= thresholds["current_fit_upgrade"] and scores.same_slot_upgrade_score >= thresholds["slot_upgrade"]:
        verdict = "upgrade_candidate"
    elif item.is_first_discovery and item.legendary_tier != "none":
        verdict = "lock_candidate"
    elif scores.current_build_fit >= thresholds["current_fit_keep"]:
        verdict = "situational"
    elif scores.future_build_fit >= thresholds["future_fit_keep"]:
        verdict = "situational"
    elif (
        item.legendary_tier == "world_legendary"
        and any(effect.extractable for effect in item.legendary_effects)
        and not protections.protected_source
    ):
        verdict = "salvage_candidate"
    elif scores.salvage_value_score >= thresholds["salvage_candidate"] and scores.source_rarity_score <= thresholds["trash_cutoff"]:
        verdict = "salvage_candidate"
    else:
        verdict = "trash"

    if protections.protected_source and verdict in {"trash", "salvage_candidate"}:
        verdict = config.PROTECTED_SOURCE_VERDICT_FLOOR
    return verdict



def should_auto_lock(item: ItemStaticProfile, evaluation: DropEvaluation) -> bool:
    return evaluation.verdict == "lock_candidate" or item.locked or item.is_first_discovery or evaluation.protections.protected_by_star_affix or evaluation.protections.protected_by_chase



def should_auto_salvage(item: ItemStaticProfile, evaluation: DropEvaluation) -> bool:
    if evaluation.verdict != "salvage_candidate":
        return False
    if evaluation.protections.protected_source:
        return False
    if item.is_first_discovery or item.locked:
        return False
    return True



def choose_workshop_action(item: ItemStaticProfile, evaluation: DropEvaluation) -> str:
    state = item.workshop_state
    if evaluation.protections.protected_by_boss_identity or evaluation.protections.protected_by_rulebreaking:
        extract_allowed = False
    else:
        extract_allowed = state.can_extract and any(effect.extractable for effect in item.legendary_effects)

    if evaluation.verdict in {"upgrade_candidate", "lock_candidate"} and state.can_strengthen and state.strengthen_level < config.MAX_STRENGTHEN_LEVEL:
        return "strengthen"
    if evaluation.verdict == "situational" and state.can_reroll and state.reroll_count == 0 and evaluation.scores.current_build_fit >= config.VERDICT_THRESHOLDS["current_fit_keep"]:
        return "reroll"
    if evaluation.verdict == "salvage_candidate" and extract_allowed and item.legendary_tier == "world_legendary":
        return "extract"
    if evaluation.verdict == "situational" and state.can_refine and state.refine_count == 0 and item.is_ancestral:
        return "refine"
    return "none"



def generate_reason_records(item: ItemStaticProfile, evaluation: DropEvaluation) -> list[ReasonRecord]:
    reasons: list[ReasonRecord] = []
    scores = evaluation.scores
    protections = evaluation.protections
    if protections.protected_by_boss_identity:
        reasons.append(ReasonRecord(code="protected.boss", category="warning", weight=95.0))
    if protections.protected_by_ancestral:
        reasons.append(ReasonRecord(code="protected.ancestral", category="warning", weight=90.0))
    if protections.protected_by_star_affix:
        reasons.append(ReasonRecord(code="protected.star", category="warning", weight=91.0))
    if protections.protected_by_rulebreaking:
        reasons.append(ReasonRecord(code="protected.rulebreaking", category="warning", weight=94.0))
    if protections.protected_by_chase:
        reasons.append(ReasonRecord(code="protected.chase", category="warning", weight=93.0))
    if scores.current_build_fit >= config.VERDICT_THRESHOLDS["current_fit_keep"]:
        reasons.append(ReasonRecord(code="fit.current", category="current", weight=scores.current_build_fit))
    if scores.same_slot_upgrade_score >= config.VERDICT_THRESHOLDS["slot_upgrade"]:
        reasons.append(ReasonRecord(code="fit.slot_upgrade", category="current", weight=scores.same_slot_upgrade_score))
    if scores.future_build_fit >= config.VERDICT_THRESHOLDS["future_fit_keep"]:
        reasons.append(ReasonRecord(code="fit.future", category="future", weight=scores.future_build_fit))
    if evaluation.verdict == "salvage_candidate":
        reasons.append(ReasonRecord(code="salvage.materials", category="salvage", weight=scores.salvage_value_score))
    if evaluation.workshop_action != "none":
        reasons.append(ReasonRecord(code=f"workshop.{evaluation.workshop_action}", category="workshop", weight=scores.workshop_potential_score))
    if item.is_first_discovery:
        reasons.append(ReasonRecord(code="discovery.first", category="warning", weight=88.0))
    return sorted(reasons, key=lambda reason: reason.weight, reverse=True)



def evaluate_drop(item: ItemStaticProfile, build: BuildContext) -> DropEvaluation:
    validate_static_item_invariants(item)
    protections = compute_protection_flags(item)
    scores = ScoreBreakdown(
        current_build_fit=score_current_build_fit(item, build),
        same_slot_upgrade_score=score_same_slot_upgrade(item, build),
        future_build_fit=score_future_build_fit(item, build),
        source_rarity_score=score_source_rarity(item),
        salvage_value_score=score_salvage_value(item),
        workshop_potential_score=score_workshop_potential(item),
    )
    normalized_scores = normalize_score_breakdown(scores)
    verdict = assign_verdict(item, normalized_scores, protections)
    evaluation = DropEvaluation(
        item_id=item.item_id,
        scores=normalized_scores,
        protections=protections,
        verdict=verdict,
        auto_lock_suggested=False,
        auto_salvage_suggested=False,
    )
    evaluation = replace(
        evaluation,
        auto_lock_suggested=should_auto_lock(item, evaluation),
        auto_salvage_suggested=should_auto_salvage(item, evaluation),
    )
    evaluation = replace(evaluation, workshop_action=choose_workshop_action(item, evaluation))
    evaluation = replace(evaluation, reasons=generate_reason_records(item, evaluation))
    return evaluation
