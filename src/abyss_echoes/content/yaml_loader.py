from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from abyss_echoes.content.schema import (
    ActiveSkillUpgradeUnlock,
    BossContent,
    BossDefinition,
    BossFailureRewards,
    BossRankRow,
    CraftCostRow,
    DropConfig,
    EconomyConfig,
    EndgameDropTable,
    FloorBandFragmentYield,
    KeyEconomy,
    LevelingRarityWeights,
    MageRpgContentBundle,
    MaterialSourceRule,
    PassivePoolCounts,
    PassiveSlotUnlock,
    ProgressionConfig,
    SkillLevelCaps,
    SkillTemplateRow,
    StarAffixRules,
    StreakBonus,
)

MAGE_RPG_CONTENT_DIR = Path(__file__).resolve().parent / "mage_rpg"


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at {path}, got {type(data).__name__}")
    return data


def load_skill_tables(base_dir: Path | None = None) -> tuple[list[SkillTemplateRow], list[SkillTemplateRow]]:
    content_dir = base_dir or MAGE_RPG_CONTENT_DIR
    payload = _read_yaml(content_dir / "skills.yaml")
    main_rows = [SkillTemplateRow(**row) for row in payload.get("main_skills", [])]
    secondary_rows = [SkillTemplateRow(**row) for row in payload.get("secondary_skills", [])]
    return main_rows, secondary_rows


def load_progression_config(base_dir: Path | None = None) -> ProgressionConfig:
    content_dir = base_dir or MAGE_RPG_CONTENT_DIR
    payload = _read_yaml(content_dir / "progression.yaml")
    passive_counts = PassivePoolCounts(**payload["passive_pool_counts"])
    passive_slots = [PassiveSlotUnlock(**row) for row in payload.get("passive_slots", [])]
    skill_caps = SkillLevelCaps(**payload["skill_level_caps"])
    upgrade_unlocks = [ActiveSkillUpgradeUnlock(**row) for row in payload.get("active_skill_upgrade_unlocks", [])]
    return ProgressionConfig(
        passive_pool_counts=passive_counts,
        passive_slots=passive_slots,
        skill_level_caps=skill_caps,
        active_skill_upgrade_unlocks=upgrade_unlocks,
    )


def load_boss_content(base_dir: Path | None = None) -> BossContent:
    content_dir = base_dir or MAGE_RPG_CONTENT_DIR
    payload = _read_yaml(content_dir / "bosses.yaml")
    bosses = [BossDefinition(**row) for row in payload.get("bosses", [])]
    rank_rows = [BossRankRow(**row) for row in payload.get("boss_rank_table", [])]
    failure_rewards = BossFailureRewards(**payload["boss_failure_rewards"])
    return BossContent(
        bosses=bosses,
        boss_rank_table=rank_rows,
        boss_failure_rewards=failure_rewards,
    )


def load_drop_config(base_dir: Path | None = None) -> DropConfig:
    content_dir = base_dir or MAGE_RPG_CONTENT_DIR
    payload = _read_yaml(content_dir / "drops.yaml")
    leveling_rows = [LevelingRarityWeights(**row) for row in payload.get("leveling_rarity_weights", [])]
    endgame_rows = [EndgameDropTable(**row) for row in payload.get("endgame_drop_tables", [])]
    star_rules = StarAffixRules(**payload["star_affix_rules"])
    return DropConfig(
        leveling_rarity_weights=leveling_rows,
        endgame_drop_tables=endgame_rows,
        star_affix_rules=star_rules,
    )


def load_economy_config(base_dir: Path | None = None) -> EconomyConfig:
    content_dir = base_dir or MAGE_RPG_CONTENT_DIR
    payload = _read_yaml(content_dir / "economy.yaml")
    key_payload = payload["key_economy"]
    key_economy = KeyEconomy(
        fragments_per_key=key_payload["fragments_per_key"],
        abyss_fragment_yield=[FloorBandFragmentYield(**row) for row in key_payload.get("abyss_fragment_yield", [])],
        highest_floor_streak_bonus=StreakBonus(**key_payload["highest_floor_streak_bonus"]),
        balance_tag=key_payload.get("balance_tag", "mvp_locked"),
    )
    strengthening = [CraftCostRow(**row) for row in payload.get("strengthening_costs", [])]
    enchant = [CraftCostRow(**row) for row in payload.get("enchant_costs", [])]
    imprint = [CraftCostRow(**row) for row in payload.get("imprint_costs", [])]
    sources = [MaterialSourceRule(**row) for row in payload.get("material_sources", [])]
    return EconomyConfig(
        key_economy=key_economy,
        strengthening_costs=strengthening,
        enchant_costs=enchant,
        imprint_costs=imprint,
        material_sources=sources,
    )


def load_mage_rpg_content_bundle(base_dir: Path | None = None) -> MageRpgContentBundle:
    content_dir = base_dir or MAGE_RPG_CONTENT_DIR
    main_skills, secondary_skills = load_skill_tables(content_dir)
    return MageRpgContentBundle(
        main_skills=main_skills,
        secondary_skills=secondary_skills,
        progression=load_progression_config(content_dir),
        boss_content=load_boss_content(content_dir),
        drop_config=load_drop_config(content_dir),
        economy_config=load_economy_config(content_dir),
    )
