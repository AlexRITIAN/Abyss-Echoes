from __future__ import annotations

import json
from pathlib import Path

from abyss_echoes.engine.models import CONTENT_DIR, HeroTemplate, ItemDefinition, SkillDefinition, SkillEffect


def _read_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_heroes() -> dict[str, HeroTemplate]:
    heroes: dict[str, HeroTemplate] = {}
    for payload in _read_json(CONTENT_DIR / "heroes.json"):
        heroes[payload["hero_id"]] = HeroTemplate(**payload)
    return heroes


def load_skills() -> dict[str, SkillDefinition]:
    skills: dict[str, SkillDefinition] = {}
    for payload in _read_json(CONTENT_DIR / "skills.json"):
        effects = [SkillEffect(**effect) for effect in payload.pop("effects", [])]
        skills[payload["skill_id"]] = SkillDefinition(**payload, effects=effects)
    return skills


def load_items() -> dict[str, ItemDefinition]:
    items: dict[str, ItemDefinition] = {}
    for payload in _read_json(CONTENT_DIR / "items.json"):
        items[payload["item_id"]] = ItemDefinition(**payload)
    return items
