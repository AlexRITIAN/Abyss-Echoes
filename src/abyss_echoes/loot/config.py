from __future__ import annotations

MAX_STRENGTHEN_LEVEL = 8
MAX_BADGES = 4
MAX_REASON_LINES = 3

PROTECTED_SOURCE_TYPES = {"regional_boss"}
PROTECTED_SOURCE_VERDICT_FLOOR = "situational"
PROTECTED_SOURCE_LAYER_FLOOR = "L2_attention"

RARITY_SOURCE_SCORES = {
    "common": 5.0,
    "magic": 15.0,
    "rare": 30.0,
    "legendary": 55.0,
    "unique": 70.0,
}

SOURCE_TYPE_SCORES = {
    "world_drop": 0.0,
    "abyss_drop": 8.0,
    "regional_boss": 22.0,
    "crafted_output": -10.0,
}

LEGENDARY_TIER_SCORES = {
    "none": 0.0,
    "world_legendary": 10.0,
    "boss_legendary": 24.0,
    "special_unique": 30.0,
}

POWER_BAND_SCORES = {
    "bridge": 5.0,
    "branch": 8.0,
    "core": 14.0,
    "chase": 20.0,
}

VERDICT_THRESHOLDS = {
    "current_fit_upgrade": 70.0,
    "slot_upgrade": 60.0,
    "current_fit_keep": 52.0,
    "future_fit_keep": 55.0,
    "lock_rarity": 80.0,
    "salvage_candidate": 32.0,
    "trash_cutoff": 24.0,
}

BADGE_PRIORITY = {
    "[BOSS]": 100,
    "[ANC]": 95,
    "[STAR]": 94,
    "[RULE]": 93,
    "[CHASE]": 92,
    "[NEW]": 90,
    "[DUP]": 89,
    "[LOCK]": 80,
    "[UP]": 79,
    "[KEEP]": 78,
    "[SALV]": 77,
    "[TRASH]": 76,
    "[NOW]": 65,
    "[FUTURE]": 64,
    "[WORK]": 63,
}

PRESENTATION_ORDER = {
    "L1_interrupt": 1,
    "L2_attention": 2,
    "L3_folded": 3,
    "L4_silent": 4,
}

PRESENTATION_BY_VERDICT = {
    "lock_candidate": "L1_interrupt",
    "upgrade_candidate": "L2_attention",
    "situational": "L3_folded",
    "salvage_candidate": "L3_folded",
    "trash": "L4_silent",
}

VERDICT_LABELS = {
    "lock_candidate": "锁定候选",
    "upgrade_candidate": "升级候选",
    "situational": "条件保留",
    "salvage_candidate": "分解候选",
    "trash": "垃圾",
}

SOURCE_LABELS = {
    "world_drop": "世界掉落",
    "abyss_drop": "深渊掉落",
    "regional_boss": "区域 Boss",
    "crafted_output": "工坊产出",
}

SLOT_LABELS = {
    "weapon": "weapon",
    "offhand": "offhand",
    "amulet": "amulet",
    "ring_1": "ring_1",
    "ring_2": "ring_2",
    "head": "head",
    "chest": "chest",
    "legs": "legs",
    "hands": "hands",
    "shoulders": "shoulders",
    "bracers": "bracers",
}
