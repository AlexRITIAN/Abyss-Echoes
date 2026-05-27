---
doc_type: game_design_spec
project: Abyss Echoes
feature: python-cli-auto-battler
status: draft
primary_language: python
source_of_truth: true
ai_readability: high
schema_version: 1
keywords:
  - cli-game
  - auto-battler
  - python
  - hero-system
  - equipment-system
  - speed-system
  - energy-system
  - no-skill-cooldown
normative_rules:
  - Battle is fully automatic after lineup selection.
  - Each team deploys exactly 5 heroes.
  - Heroes have roles: tank, melee_dps, ranged_dps, mage, support.
  - Heroes have positions: frontline or backline.
  - Each hero has exactly 1 basic attack, 1 active skill, and 1 passive skill.
  - Active skills do not use cooldowns.
  - Active skills can be cast whenever energy is full and the acting hero AI chooses to cast.
  - Basic attacks are the primary way to gain energy.
  - Speed controls action frequency through an action gauge system.
---

# CLI Auto-Battler Design Spec

## 1. Goal

Build a Python command-line auto-battler where the player selects 5 heroes, arranges them into frontline/backline positions, equips gear inspired by Diablo 4, and watches battles resolve automatically through a speed-based action gauge system.

## 2. Scope

### 2.1 In scope for MVP
- Python implementation
- CLI presentation
- 5v5 auto-battle
- 5 roles
- 15 heroes total
- Equipment system with rarity, affixes, and legendary aspects
- Speed system
- Energy system
- Active skill with no cooldown
- Basic attack, active skill, passive skill for every hero
- Battle logs suitable for terminal output

### 2.2 Out of scope for MVP
- Multiplayer / PvP
- Real-time graphics
- Skill trees
- Summons / pets
- Complex elemental counter system
- Large-scale procedural dungeons

## 3. Core Design Principles

1. **Readability first**: combat logs and rules must be easy to inspect in text.
2. **Data-driven content**: heroes, skills, items, and affixes should live in structured data files.
3. **Build variety**: equipment should change combat loops, not only increase numbers.
4. **Fast iteration**: rules should be easy to tune in Python.
5. **Deterministic structure**: systems and headings should be easy for AI agents to parse.

## 4. High-Level Game Loop

1. Player manages roster.
2. Player selects 5 heroes.
3. Player assigns positions.
4. Player equips items.
5. Battle starts.
6. Combat resolves automatically.
7. Player receives loot and progression rewards.
8. Player upgrades roster and repeats.

## 5. Team Composition Rules

## 5.1 Team size
- Each team has exactly 5 heroes.

## 5.2 Position limits
- Frontline: max 2 heroes
- Backline: max 3 heroes

## 5.3 Recommended layout
- Frontline: tank, melee_dps
- Backline: ranged_dps, mage, support

## 5.4 Role definitions
- `tank`: absorbs damage, protects team, may taunt or shield
- `melee_dps`: physical single-target or cleave damage, usually frontline
- `ranged_dps`: physical backline sustained damage
- `mage`: magical AoE, debuffs, or damage-over-time
- `support`: healing, buffs, energy support, action-gauge support

## 6. Battle System Summary

## 6.1 Combat mode
- Fully automatic
- No manual actions during battle
- Battle ends when all heroes on one team are dead

## 6.2 Resource model
Each hero uses:
- HP
- action_gauge
- energy
- statuses

Important change from earlier drafts:
- **There is no active-skill cooldown system.**
- An active skill is available whenever `energy >= 100` and the hero has a valid target or valid cast condition.

## 6.3 Action gauge system
Each hero has an action gauge.

Rule:
```text
action_gauge += speed
if action_gauge >= 1000:
    hero gets one action
    action_gauge -= 1000
```

### 6.3.1 Action priority when multiple heroes are ready
Sort by:
1. higher `action_gauge`
2. higher `speed`
3. lower fixed formation index

## 6.4 Energy system
### 6.4.1 Energy range
- `0` to `100`

### 6.4.2 Energy gain sources
Recommended default values:
- basic attack hit: `+25`
- taking direct damage: `+5`
- killing an enemy: `+15`
- optional affix/passive bonus: variable

### 6.4.3 Active skill release rule
A hero may cast its active skill when all of the following are true:
- `energy >= 100`
- hero is not stunned / frozen / otherwise unable to act
- a legal target or legal cast condition exists
- AI decides active skill is preferred over basic attack

### 6.4.4 Energy consumption
- Active skill consumes all required energy
- MVP default: subtract `100` energy on cast

## 6.5 Turn execution order
When a hero acts:
1. process start-of-action status effects
2. if incapacitated, skip action
3. decide between active skill and basic attack
4. select target(s)
5. resolve damage / healing / shield / buffs / debuffs
6. trigger passive and reactive effects
7. process end-of-action status updates
8. check deaths and victory condition

## 7. Positioning Rules

## 7.1 Frontline rules
- Frontline heroes are the default target for melee basic attacks.
- Tanks and melee_dps usually belong here.
- Frontline heroes absorb pressure and protect backline access.

## 7.2 Backline rules
- Backline heroes are protected while at least one frontline ally is alive.
- Ranged_dps, mage, and support usually belong here.
- If frontline is dead, backline becomes fully targetable.

## 7.3 Targeting rules
### 7.3.1 Global priority
1. taunt target if one exists
2. frontline if any frontline target is alive
3. backline otherwise

### 7.3.2 Melee basic attacks
- cannot target enemy backline while enemy frontline is alive unless a skill explicitly allows it

### 7.3.3 Ranged and magical attacks
- follow AI targeting rules
- may target backline only if allowed by skill logic or when frontline is gone

## 8. Combat Formulas

## 8.1 Physical damage
```text
raw_damage = attacker.atk * skill_ratio
mitigation = 100 / (100 + target.armor)
final_damage = raw_damage * mitigation * damage_bonus * crit_multiplier
```

## 8.2 Magical damage
```text
raw_damage = attacker.mag * skill_ratio
mitigation = 100 / (100 + target.resist)
final_damage = raw_damage * mitigation * damage_bonus * crit_multiplier
```

## 8.3 Healing
```text
final_heal = caster.mag * heal_ratio * (1 + heal_bonus)
```

## 8.4 Damage-over-time
- DOT does not crit in MVP.
```text
dot_damage = source_stat * ratio * mitigation
```

## 8.5 Shield
- Shield is a separate value tracked on the unit.
- Incoming damage is applied to shield first, then HP.

## 9. Core Stats

Every hero instance should support these stats:
- `max_hp`
- `atk`
- `mag`
- `armor`
- `resist`
- `speed`
- `crit_rate`
- `crit_damage`
- `heal_bonus`
- `energy_gain_bonus`
- `damage_bonus`
- `shield_bonus`

## 10. Status Effects for MVP

Recommended initial set:
- `shield`
- `taunt`
- `shred_armor`
- `burn`
- `ignite`
- `bleed`
- `haste`
- `slow`
- `stun`
- `freeze`
- `weaken`
- `erosion`

## 11. AI Rules

## 11.1 Generic action choice
```text
if energy >= 100 and active_skill_should_cast(hero, battle_state):
    cast active skill
else:
    basic attack
```

## 11.2 Role-level heuristics
### tank
- cast active if self HP is low
- cast active if team frontline is under pressure
- otherwise basic attack nearest valid frontline target

### melee_dps
- cast active if a kill is likely
- otherwise focus frontline or marked low-HP target

### ranged_dps
- prefer finishing low-HP targets
- otherwise focus current enemy frontline anchor

### mage
- cast active when 3 or more enemies are alive or enough debuffed targets exist

### support
- cast active when healing or team buff value is high enough

## 12. Equipment System

## 12.1 Equipment slots
- weapon
- helmet
- chest
- gloves
- pants
- boots
- amulet
- ring_1
- ring_2

## 12.2 Item rarity
- common
- magic
- rare
- legendary
- unique

## 12.3 Item structure
Each item contains:
- slot
- rarity
- item_power
- main_stat
- affixes
- optional legendary_aspect

## 12.4 Affix philosophy
Affixes should influence:
- damage output
- survivability
- speed
- energy gain
- healing
- damage against specific target states
- shield scaling

## 12.5 MVP affix pool
- hp_pct
- atk_pct
- mag_pct
- armor_flat
- resist_flat
- speed_flat
- crit_rate
- crit_damage
- energy_gain_bonus
- heal_bonus
- shield_bonus
- damage_vs_frontline
- damage_vs_backline
- damage_vs_debuffed
- incoming_heal_bonus

## 12.6 Legendary aspect philosophy
Legendary aspects should change combat patterns, not only increase stats.

Example directions:
- tank: gain speed while shielded
- melee_dps: gain bonus energy after crit or kill
- ranged_dps: extra projectile on every third basic attack
- mage: gain energy when DOT ticks on enemies
- support: overflow healing converts to shield

## 13. Hero Roster

## 13.1 Tanks
### steel_guardian
- role: tank
- position: frontline
- basic: `shield_strike` -> 100% ATK physical, 20% taunt for 1 action, +25 energy
- active: `fortress_stand` -> self shield for 22% max HP, taunt enemy frontline for 2 actions, reduce incoming damage by 25%
- passive: `armor_reverb` -> when taking direct damage, deal retaliation equal to 35% of armor and gain +5 energy

### temple_warden
- role: tank
- position: frontline
- basic: `holy_hammer` -> 95% ATK physical, lowest-HP ally gains small shield, +25 energy
- active: `sacred_shelter` -> team gains 15% damage reduction for 2 actions, backline gains extra shield
- passive: `loyal_intercept` -> chance to share damage taken by backline ally, stacking self defense

### thorn_brute
- role: tank
- position: frontline
- basic: `thorn_fist` -> 105% ATK physical, more damage below 60% HP, +25 energy
- active: `thorn_tide` -> stronger thorns for 3 actions, apply bleed to all enemies
- passive: `bloodbone_rage` -> missing HP grants attack and speed, stacking up to cap

## 13.2 Melee DPS
### berserker
- role: melee_dps
- position: frontline
- basic: `rending_slash` -> 110% ATK physical, bonus damage vs targets under 50% HP, +25 energy
- active: `blood_combo` -> 3 hits of 85% ATK, kill grants follow-up hit on another enemy
- passive: `murder_fervor` -> on kill gain +15 energy and +20% speed for 2 actions

### shadow_blade
- role: melee_dps
- position: frontline
- basic: `shadow_assault` -> 95% ATK physical on lowest-HP valid target, +15% crit rate, +25 energy
- active: `night_execution` -> hit enemy backline for 220% ATK, guaranteed crit below 40% target HP
- passive: `dusk_steps` -> crit grants speed, avoiding damage before next action grants extra energy on next basic

### halberd_commander
- role: melee_dps
- position: frontline
- basic: `halberd_thrust` -> 100% ATK physical, chance to pierce and damage rear target, +25 energy
- active: `formation_breaker` -> 140% ATK to all frontline enemies and apply 2 armor shred stacks
- passive: `command_pressure` -> bonus damage vs debuffed or frontline targets

## 13.3 Ranged DPS
### hunter_ranger
- role: ranged_dps
- position: backline
- basic: `piercing_arrow` -> 95% ATK physical, 30% chance for extra 40% ATK arrow, +25 energy
- active: `arrow_storm` -> 80% ATK to all enemies, main target gets 2 armor shred stacks
- passive: `precise_hunt` -> crit bonus vs healthy targets, crit damage bonus vs low-HP targets

### repeater_engineer
- role: ranged_dps
- position: backline
- basic: `double_bolt` -> two hits of 75% ATK, each hit gives +15 energy
- active: `overdrive_barrage` -> 6 random hits of 55% ATK, same target max 3 hits
- passive: `clockwork_overload` -> every third basic adds one extra 80% ATK hit

### demolitionist
- role: ranged_dps
- position: backline
- basic: `firebomb` -> 90% ATK physical, chance to apply ignite, +25 energy
- active: `blast_volley` -> 85% ATK to all enemies, ignite targets take bonus explosion damage
- passive: `powder_festival` -> each ignited enemy increases own crit rate, stacking up to cap

## 13.4 Mages
### arcane_scholar
- role: mage
- position: backline
- basic: `arcane_bolt` -> 100% MAG magic, 25% burn chance, +25 energy
- active: `meteor_rite` -> 90% MAG to all enemies, burn targets take bonus damage
- passive: `elemental_resonance` -> more magic damage per debuffed enemy, stacking up to cap

### frost_witch
- role: mage
- position: backline
- basic: `frost_spike` -> 95% MAG magic, chance to apply slow, +25 energy
- active: `glacial_tempest` -> 80% MAG to all enemies, guaranteed slow, chance to freeze
- passive: `cold_domain` -> extra damage vs slowed targets and crit bonus vs frozen targets

### void_hexer
- role: mage
- position: backline
- basic: `void_mark` -> 85% MAG magic, applies weaken, +25 energy
- active: `abyss_curse` -> apply erosion to all enemies for 2 actions
- passive: `curse_echo` -> gain energy whenever enemy debuffs tick, up to per-action cap

## 13.5 Supports
### sacred_priest
- role: support
- position: backline
- basic: `holy_wave` -> 70% MAG damage to enemy, heal lowest-HP ally for 40% MAG, +25 energy
- active: `grace_prayer` -> team heal for 120% MAG and grant haste for 2 actions
- passive: `afterglow_blessing` -> allies under 50% HP receive more healing

### war_song_bard
- role: support
- position: backline
- basic: `rally_chord` -> 75% MAG damage and grant +8 energy to highest-ATK ally, +25 energy to self
- active: `victory_anthem` -> team gains damage bonus and immediate energy
- passive: `echo_of_encouragement` -> ally active-skill casts grant self energy

### chrono_sage
- role: support
- position: backline
- basic: `time_pulse` -> 80% MAG damage and grant action gauge to slowest ally, +25 energy
- active: `timeline_sync` -> increase team action gauge, boost selected ally skill tempo through energy/gauge support
- passive: `foresight_loop` -> active-skill events may grant self energy and minor healing support

## 14. Recommended Team Archetypes

## 14.1 Balanced team
- steel_guardian
- berserker
- hunter_ranger
- arcane_scholar
- sacred_priest

## 14.2 Fast-cycle team
- temple_warden
- shadow_blade
- repeater_engineer
- frost_witch
- chrono_sage

## 14.3 DOT / debuff team
- thorn_brute
- halberd_commander
- demolitionist
- void_hexer
- war_song_bard

## 15. Data Model

## 15.1 HeroTemplate
```python
from dataclasses import dataclass
from typing import Literal

Role = Literal["tank", "melee_dps", "ranged_dps", "mage", "support"]
Position = Literal["frontline", "backline"]

@dataclass
class HeroTemplate:
    hero_id: str
    name: str
    role: Role
    preferred_position: Position
    base_hp: int
    base_atk: int
    base_mag: int
    base_armor: int
    base_resist: int
    base_speed: int
    base_crit_rate: float
    base_crit_damage: float
    basic_skill_id: str
    active_skill_id: str
    passive_skill_id: str
```

## 15.2 BattleUnit
```python
from dataclasses import dataclass, field

@dataclass
class BattleUnit:
    unit_id: str
    team_id: str
    formation_index: int
    hero_id: str
    current_hp: int
    max_hp: int
    shield: int = 0
    energy: int = 0
    action_gauge: int = 0
    alive: bool = True
    statuses: list = field(default_factory=list)
    equipment_ids: list[str] = field(default_factory=list)
```

## 15.3 SkillDefinition
```python
from dataclasses import dataclass
from typing import Literal

SkillType = Literal["basic", "active", "passive"]
Targeting = Literal[
    "single_enemy",
    "all_enemies",
    "single_ally",
    "all_allies",
    "self",
    "frontline_enemies",
    "lowest_hp_enemy",
    "lowest_hp_ally",
]

@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    skill_type: SkillType
    targeting: Targeting
    ratio: float | None
    damage_type: str | None
    energy_cost: int = 0
```

## 15.4 StatusEffect
```python
from dataclasses import dataclass

@dataclass
class StatusEffect:
    status_id: str
    source_unit_id: str
    duration_actions: int
    stacks: int = 1
    magnitude: float = 0.0
```

## 15.5 ItemDefinition
```python
from dataclasses import dataclass, field

@dataclass
class ItemDefinition:
    item_id: str
    slot: str
    rarity: str
    item_power: int
    main_stat: dict
    affixes: list[dict] = field(default_factory=list)
    legendary_aspect: str | None = None
```

## 16. Battle Engine Pseudocode

```python
while not battle_over:
    for unit in alive_units:
        unit.action_gauge += unit.speed

    ready_units = [u for u in alive_units if u.action_gauge >= 1000]
    ready_units.sort(key=lambda u: (-u.action_gauge, -u.speed, u.formation_index))

    for actor in ready_units:
        if not actor.alive:
            continue

        actor.action_gauge -= 1000
        process_start_of_action(actor, battle_state)

        if not actor.alive:
            continue

        if is_incapacitated(actor):
            process_end_of_action(actor, battle_state)
            continue

        if actor.energy >= 100 and should_cast_active(actor, battle_state):
            cast_active_skill(actor, battle_state)
            actor.energy -= 100
        else:
            perform_basic_attack(actor, battle_state)

        process_reactions(actor, battle_state)
        process_end_of_action(actor, battle_state)
        remove_dead_units(battle_state)

        if victory_reached(battle_state):
            battle_over = True
            break
```

## 17. CLI Output Requirements

The CLI should display:
- ally frontline status
- ally backline status
- enemy frontline status
- enemy backline status
- current action log
- winner and loot summary after battle

Recommended log lines:
```text
[ACT] Arcane Scholar uses Meteor Rite
[DMG] Enemy Skeleton Guard takes 182 magic damage
[DOT] Enemy Bone Archer suffers 48 burn damage
[HEAL] Sacred Priest restores 84 HP to Berserker
[KILL] Bone Archer is defeated
```

## 18. Content Storage Recommendation

Use data files so AI and code can both parse them easily.

Recommended layout:
```text
docs/
  ai-context/
    cli-auto-battler-design.md
src/
  abyss_echoes/
    engine/
    content/
      heroes.yaml
      skills.yaml
      items.yaml
      status_effects.yaml
tests/
  engine/
```

## 19. Python Tech Recommendation

Recommended stack:
- Python 3.11+
- dataclasses
- enum
- pathlib
- pydantic or plain validation layer (optional)
- rich for CLI output
- pytest for battle-engine testing
- yaml/json for content definitions

## 20. Implementation Priorities

### Phase 1
- base stats
- action gauge
- energy system
- basic attacks
- active skills with no cooldown
- passive hooks
- battle victory detection

### Phase 2
- status effects
- target selection AI
- 15-hero roster
- battle log rendering

### Phase 3
- equipment generation
- affixes
- legendary aspects
- progression rewards

### Phase 4
- save/load
- stage progression
- balance tools and simulation runs

## 21. Non-Negotiable Rules

These rules should be treated as implementation invariants unless explicitly changed later:

1. Active skills have **no cooldown**.
2. Active skills require **full energy**.
3. Energy is gained mainly through **basic attacks**.
4. Speed affects **action frequency**, not damage directly.
5. Frontline protects backline by default.
6. Every hero has exactly **1 basic + 1 active + 1 passive**.
7. Equipment should support **build diversity**, not only stat inflation.
8. MVP implementation target is **Python CLI**.
