from __future__ import annotations

from abyss_echoes.loot import config
from abyss_echoes.loot.models import (
    DropEvaluation,
    DropPresentation,
    ItemStaticProfile,
    PresentationBadge,
    PresentationLine,
)


REASON_TEXT = {
    "protected.boss": "Boss 专属来源，至少保留到关注层。",
    "protected.ancestral": "900 先祖底材，不能视为普通垃圾。",
    "protected.star": "含星词缀，默认禁止自动分解。",
    "protected.rulebreaking": "规则突破件，不可进入普通萃取/刻印路线。",
    "protected.chase": "命名级 chase 物品，来源价值高。",
    "fit.current": "当前 build 适配度较高。",
    "fit.slot_upgrade": "同槽位存在明确升级空间。",
    "fit.future": "更适合未来分支，可作为 offbuild 保留。",
    "salvage.materials": "本件更偏材料价值。",
    "workshop.strengthen": "建议进入强化流程。",
    "workshop.reroll": "建议尝试单条洗练。",
    "workshop.refine": "建议作为后续精修候选。",
    "workshop.extract": "建议萃取普通传奇特效。",
    "discovery.first": "首次发现，优先保留。",
}



def choose_presentation_layer(item: ItemStaticProfile, evaluation: DropEvaluation) -> str:
    layer = config.PRESENTATION_BY_VERDICT[evaluation.verdict]
    if evaluation.protections.protected_source and config.PRESENTATION_ORDER[layer] > config.PRESENTATION_ORDER[config.PROTECTED_SOURCE_LAYER_FLOOR]:
        return config.PROTECTED_SOURCE_LAYER_FLOOR
    return layer



def build_title_line(item: ItemStaticProfile, evaluation: DropEvaluation) -> str:
    verdict_label = config.VERDICT_LABELS[evaluation.verdict]
    return f"{item.name} · {config.SLOT_LABELS.get(item.slot, item.slot)} · {verdict_label}"



def build_subtitle_line(item: ItemStaticProfile, evaluation: DropEvaluation) -> str:
    source_label = config.SOURCE_LABELS.get(item.source_type, item.source_type)
    ancestral_label = " / 900先祖" if item.is_ancestral else ""
    star_label = f" / 星{item.star_affix_count}" if item.star_affix_count > 0 else ""
    return f"{source_label} / {item.rarity} / IP {item.item_power}{ancestral_label}{star_label}"



def _badge_texts(item: ItemStaticProfile, evaluation: DropEvaluation) -> list[str]:
    badge_texts: list[str] = []
    if item.source_type == "regional_boss":
        badge_texts.append("[BOSS]")
    if item.is_ancestral:
        badge_texts.append("[ANC]")
    if item.star_affix_count > 0:
        badge_texts.append("[STAR]")
    if evaluation.protections.protected_by_rulebreaking:
        badge_texts.append("[RULE]")
    if evaluation.protections.protected_by_chase:
        badge_texts.append("[CHASE]")
    if item.is_first_discovery:
        badge_texts.append("[NEW]")

    verdict_badge = {
        "lock_candidate": "[LOCK]",
        "upgrade_candidate": "[UP]",
        "situational": "[KEEP]",
        "salvage_candidate": "[SALV]",
        "trash": "[TRASH]",
    }[evaluation.verdict]
    badge_texts.append(verdict_badge)

    if evaluation.scores.current_build_fit >= config.VERDICT_THRESHOLDS["current_fit_keep"]:
        badge_texts.append("[NOW]")
    elif evaluation.scores.future_build_fit >= config.VERDICT_THRESHOLDS["future_fit_keep"]:
        badge_texts.append("[FUTURE]")

    if evaluation.workshop_action != "none":
        badge_texts.append("[WORK]")
    return badge_texts



def build_presentation_badges(item: ItemStaticProfile, evaluation: DropEvaluation) -> list[PresentationBadge]:
    deduped: list[str] = []
    for text in _badge_texts(item, evaluation):
        if text not in deduped:
            deduped.append(text)
    badges = [PresentationBadge(text=text, priority=config.BADGE_PRIORITY.get(text, 0)) for text in deduped]
    badges.sort(key=lambda badge: badge.priority, reverse=True)
    return badges[: config.MAX_BADGES]



def build_summary_lines(item: ItemStaticProfile, evaluation: DropEvaluation) -> list[PresentationLine]:
    slot_delta = round(evaluation.scores.same_slot_upgrade_score - 50.0)
    summary = [
        PresentationLine(label="verdict", value=config.VERDICT_LABELS[evaluation.verdict], priority=100),
        PresentationLine(label="now", value=f"{evaluation.scores.current_build_fit:.0f}", priority=90),
        PresentationLine(label="future", value=f"{evaluation.scores.future_build_fit:.0f}", priority=80),
        PresentationLine(label="slot_delta", value=f"{slot_delta:+.0f}", priority=70),
    ]
    if evaluation.workshop_action != "none":
        summary.append(PresentationLine(label="workshop", value=evaluation.workshop_action, priority=60))
    return summary



def compress_reason_lines(evaluation: DropEvaluation) -> list[str]:
    lines: list[str] = []
    for reason in evaluation.reasons:
        text = REASON_TEXT.get(reason.code)
        if text and text not in lines:
            lines.append(text)
        if len(lines) >= config.MAX_REASON_LINES:
            break
    return lines



def build_recommended_action_line(item: ItemStaticProfile, evaluation: DropEvaluation) -> str | None:
    if evaluation.auto_lock_suggested:
        return "建议动作：自动加锁"
    if evaluation.auto_salvage_suggested:
        return "建议动作：加入待分解"
    if evaluation.workshop_action != "none":
        return f"建议动作：{evaluation.workshop_action}"
    if evaluation.verdict == "trash":
        return "建议动作：静默归类为垃圾"
    return "建议动作：先保留观察"



def build_drop_presentation(item: ItemStaticProfile, evaluation: DropEvaluation) -> DropPresentation:
    return DropPresentation(
        item_id=item.item_id,
        layer=choose_presentation_layer(item, evaluation),
        title_line=build_title_line(item, evaluation),
        subtitle_line=build_subtitle_line(item, evaluation),
        badges=build_presentation_badges(item, evaluation),
        summary_lines=build_summary_lines(item, evaluation),
        reason_lines=compress_reason_lines(evaluation),
        recommended_action_line=build_recommended_action_line(item, evaluation),
    )
