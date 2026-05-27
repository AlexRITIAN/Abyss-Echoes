---
doc_type: ui_optimization_spec
project: Abyss Echoes
feature: cli-interface-optimization
status: draft
primary_language: python
source_of_truth: true
ai_readability: high
schema_version: 1
keywords:
  - cli-ui
  - terminal-ui
  - auto-battler
  - battle-readability
  - inventory-ux
  - codex
  - information-hierarchy
  - curses
normative_rules:
  - The project remains a Python CLI game and does not switch to a graphical UI framework.
  - The existing three-column terminal layout remains the primary presentation model.
  - UI optimization prioritizes readability and decision support over adding new gameplay systems.
  - Battle screens must emphasize current state, key events, and short summaries rather than raw log volume.
  - Left, center, and right panels must have distinct responsibilities and should not duplicate full-detail content.
  - Inventory management and item codex must keep legendary aspect descriptions consistent.
  - Equipment recommendation output must include both numeric comparison and a short natural-language verdict.
  - Long-form detail belongs in focused views; high-frequency panels must stay compact.
  - Existing gameplay rules, item systems, party rules, and progression systems are not changed by this document.
  - Implementation should proceed in small verified slices, with tests added before behavior changes.
---

# Abyss Echoes CLI UI Optimization Spec

## 1. Goal

Improve the usability, readability, and perceived production quality of the existing Abyss Echoes terminal interface without changing the core gameplay loop or replacing the current curses-style CLI structure.

This document defines how the interface should present battle state, party state, inventory decisions, and codex information so the game feels easier to read and more intentional.

## 2. Scope

### 2.1 In scope
- Main menu information hierarchy
- Left / center / right panel responsibilities
- Battle readability improvements
- Party and hero information layout improvements
- Inventory and equipment comparison UX improvements
- Item codex and rules-text consistency improvements
- Shared text templates for item / recommendation / summary output
- Incremental implementation priorities for the existing `src/abyss_echoes/cli.py`

### 2.2 Out of scope
- Replacing the CLI with a graphical frontend
- Rewriting the combat engine
- Changing balance formulas as part of the UI pass
- Adding new progression systems
- Adding set bonuses or new item subsystems
- Changing the 5-hero party model
- Re-theming the game

## 3. Current State Summary

The current CLI already includes:
- a working three-column terminal structure
- a main action menu
- stage preview and threat analysis
- battle playback with per-log HP snapshots
- party and hero views
- codex views for heroes and items
- manual inventory management with equip / unequip
- candidate-vs-equipped score comparison
- affix comparison
- legendary aspect description rendering in inventory and item codex

The current problem is **not missing core functionality**.
The current problem is that information is often presented as feature-complete text output rather than as a layered player-facing interface.

## 4. Core UI Design Principles

1. **Readability first**
   - The player should understand what matters within 1-2 seconds.
   - Dense output is acceptable only in focused detail views.

2. **Decision support over raw data volume**
   - The UI should help the player decide what to do next.
   - Numeric output alone is not sufficient when a short verdict would clarify the result.

3. **Stable information hierarchy**
   - Left panel = persistent state summary
   - Center panel = current task / current view
   - Right panel = candidate list / auxiliary navigation

4. **Short summaries plus expandable detail**
   - High-frequency panels should stay compact.
   - Long explanations belong in focused views such as hero detail, inventory detail, and codex detail.

5. **Template consistency**
   - Similar information must use the same labels and structure across inventory, codex, recommendations, and battle summaries.

6. **No system bloat during UI optimization**
   - The purpose of this pass is interface quality, not new gameplay depth.

## 5. Reference Inspirations

This spec intentionally borrows patterns from successful games with similar UI problems:

### 5.1 Darkest Dungeon
Borrow:
- battle readability
- constant party visibility
- status readability
- strong event clarity

### 5.2 Loop Hero
Borrow:
- fast candidate-vs-equipped judgment
- compact equipment comparison
- low-friction gear decisions during an auto-battle-oriented loop

### 5.3 Slay the Spire
Borrow:
- rules-text consistency
- keyword-style templating
- short, scannable effect descriptions

### 5.4 Battle Brothers
Borrow:
- roster/detail separation
- clear progression from squad overview to unit-specific inspection
- practical equipment-management presentation

### 5.5 Into the Breach
Borrow:
- danger communication
- short prediction-like summaries
- emphasis on "why this is dangerous right now"

## 6. Panel Responsibility Model

## 6.1 Left panel responsibility
The left panel is the **persistent state summary panel**.

It should answer:
- Where am I?
- What resources do I have?
- What is the current encounter?
- What is the current condition of both teams?
- What is the current high-level situation?

It should **not** attempt to show full descriptions, long recommendations, or full detailed item text.

### Left panel required sections
1. Save / resource summary
2. Stage summary
3. Allied team compact list
4. Enemy team compact list
5. One-line situation summary

## 6.2 Center panel responsibility
The center panel is the **active focus panel**.

It should answer:
- What am I looking at right now?
- What is the primary content for this mode?
- What is the most important explanation or decision information?

Examples:
- stage intelligence detail
- battle log and battle summary
- party detail
- hero detail
- inventory management detail
- codex detail

## 6.3 Right panel responsibility
The right panel is the **auxiliary list / selection panel**.

It should answer:
- What are the current candidates or selectable items?
- Which one is currently highlighted?

Examples:
- inventory list during inventory mode
- equipped list during inventory mode
- default backpack summary outside focused inventory mode
- future hero list helper for hero-detail browsing
- future codex category/item quick list if needed

The right panel should avoid duplicating the full detail body already visible in the center panel.

## 7. Main Menu Optimization

## 7.1 Problem
The current menu is functionally complete but appears as a flat command list.
This makes the interface feel tool-like instead of product-like.

## 7.2 Desired behavior
The menu should be grouped by purpose so the player can quickly infer the structure of the game.

## 7.3 Required grouping
The menu should be rendered in conceptual groups:

### Battle
- 开始战斗
- 关卡情报
- 下一关

### Team
- 队伍详情
- 全部英雄
- 升级建议
- 自动装备
- 装备管理

### Knowledge
- 游戏百科

### System
- 保存存档
- 重新读取
- 重置存档
- 退出游戏

## 7.4 Non-goal
This grouping does not require changing action IDs or engine behavior.
It is a presentation change only.

## 8. Left Panel Specification

## 8.1 Left panel content model
The left panel should use this top-to-bottom structure:

1. save summary
2. resource summary
3. current stage summary
4. ally compact roster
5. enemy compact roster
6. situation summary

## 8.2 Compact roster line format
Each unit line should remain short and scannable.

Preferred style:
```text
- 1 狂战士 前排 HP84/110 Lv7
- 2 圣殿守卫 前排 HP120/120 Lv7
- 3 星术师 后排 HP62/80 Lv6
```

Rules:
- slot index must remain visible
- position must remain visible
- HP must remain visible
- allied level should remain visible
- avoid long prose inside roster rows

## 8.3 Situation summary
The left panel should end with one short high-level sentence.

Examples:
- 局势：前排稳定，后排承压。
- 局势：敌方后排脆弱，可优先击穿。
- 局势：治疗压力较高，注意持久战。

The situation line is a summary, not a recommendation block.

## 8.4 De-emphasized fields
The following should be shortened or deprioritized if panel space is tight:
- overly verbose encounter theming text
- repeated metadata already shown in the center panel
- long multi-line narrative summaries

## 9. Battle View Specification

## 9.1 Goal
The battle view should make it easy to understand:
- who acted
- what happened
- which state changed
- what the current situation means

## 9.2 Two-layer battle presentation
The center battle view should be composed of:
1. **event lines**
2. **round summary lines**

### Event lines
Examples:
- `[ACT] 狂战士 使用 裂甲猛击`
- `[DMG] 狂战士 对 灰烬祭司 造成 24 点伤害`
- `[HEAL] 圣职者 为 圣殿守卫 回复 18 点生命`
- `[BUFF] 狂战士 获得 暴怒`
- `[KILL] 灰烬祭司 被击倒`

### Round summary lines
Examples:
- `回合摘要：我方前排稳定，敌后排术士残血。`
- `危险提示：星术师被双目标锁定。`
- `战况判断：敌方爆发期已过。`

## 9.3 Required battle-summary fields
At minimum, battle summaries should be able to express:
- current pressure side
- fragile allied target if any
- fragile enemy target if any
- whether the fight is trending stable or dangerous

## 9.4 Logging rule
The system should not rely on raw log count as a readability strategy.
Battle readability is improved by structure, not by volume.

## 9.5 Non-goal
This spec does not require converting the replay architecture into live simulation rendering.
Existing HP snapshot playback remains valid.

## 10. Stage Intelligence View Specification

## 10.1 Goal
The stage view should explain the upcoming encounter clearly enough that the player can make pre-battle decisions.

## 10.2 Required sections
1. stage id / unlocked progression
2. encounter name and type
3. threat summary
4. party summary
5. recommendation block

## 10.3 Recommendation block rules
Recommendations should remain short, imperative, and decision-oriented.

Examples:
- 优先保护后排。
- 注意敌方灼烧叠加。
- 先击杀高爆发术士。

Recommendations should not become a wall of theory text.

## 11. Party View Specification

## 11.1 Goal
The party view should quickly communicate:
- who is in the active party
- what role each member plays
- how developed they are
- who needs attention next

## 11.2 Party view structure
Each party member block should prefer this order:
1. slot / hero / position
2. role summary
3. level and progression state
4. equipment status or equipment score summary
5. short recommendation if meaningful

## 11.3 Example format
```text
- 1 狂战士（前排）Lv7
  职责：爆发输出
  装备：评分 82
  建议：武器可升级
```

## 11.4 Team summary block
The view should end with a short team-level summary.
Examples:
- 当前队伍前排稳定，后排输出充足。
- 当前短板：游侠装备偏弱。

## 12. Hero List and Hero Detail Specification

## 12.1 Hero list goal
The hero list should act as a roster overview, not a data dump.

## 12.2 Hero list preferred line format
Each hero line should combine progression and role in one scannable line.

Example:
```text
- 狂战士：Lv7 上阵 / 爆发前排 / 装备 82 / 可升级
```

## 12.3 Hero detail section order
Hero detail should use this normalized order:
1. hero name
2. role / position identity
3. progression block
4. equipment block
5. skill block
6. recommendation block

### Progression block
- 等级
- 经验
- 状态
- 专精

### Equipment block
- equipped item summary by slot
- optional future score summary

### Skill block
- 普攻等级
- 主动等级
- 被动等级

### Recommendation block
- current best upgrade if any
- preferred stats or direction if available

## 13. Inventory Management Specification

## 13.1 Goal
Inventory management should feel like a deliberate decision screen rather than a raw bag viewer.

## 13.2 Existing behavior to preserve
The following existing interaction rules remain required:
- target hero is selected from the current party order
- filtered inventory uses recommended heroes when available
- `Tab` switches between inventory and equipped focus
- `Enter` equips or unequips contextually
- replaced items return to inventory
- selected item detail includes legendary aspect description

## 13.3 Required inventory detail sections
Inventory detail should use this stable order:
1. basic info
2. main stats
3. affixes
4. legendary aspect
5. recommended heroes
6. comparison block
7. verdict block

## 13.4 Verdict block
In addition to numeric comparison, the interface must show a short natural-language verdict.

Examples:
- `结论：推荐立即替换。`
- `结论：评分更高，但会损失速度。`
- `结论：更适合圣殿守卫，不适合当前英雄。`
- `结论：收益有限，可暂缓更换。`

This verdict is required because numeric deltas alone are not enough for fast scan-based decisions.

## 13.5 Recommendation-strength model
Recommended heroes may later be displayed with strength labels.
Preferred future format:
- `推荐英雄：狂战士（高），游侠（中）`

This is a future enhancement, not a current requirement.

## 13.6 Comparison block requirements
The comparison block must preserve:
- candidate score
- equipped score
- score delta
- main stat comparison
- affix comparison

Optional future enhancement:
- legendary aspect comparison

## 14. Codex and Rules-Text Specification

## 14.1 Goal
The codex should function as a readable rules reference, not only as a database browser.

## 14.2 Item codex section order
Item codex detail should use this normalized order:
1. title / item identity
2. rarity / slot / power
3. main stats
4. affixes
5. legendary aspect name
6. legendary aspect description
7. optional future usage guidance

## 14.3 Preferred effect-text structure
Whenever a legendary effect can be decomposed clearly, the long description should trend toward this structure:
- 名称
- 触发
- 效果

Example:
```text
传奇特效：余烬回能
触发：攻击带有减益的目标时
效果：回复 5 点能量
```

If implementation remains single-line for now, the wording should still support future decomposition.

## 14.4 Consistency rule
Inventory detail and item codex detail must use the same source of truth for legendary aspect names and descriptions.

## 15. Shared Text Template Rules

## 15.1 Required labels
The interface should standardize the following labels:
- `触发：`
- `效果：`
- `持续：`
- `条件：`
- `推荐：`
- `结论：`
- `当前装备：`
- `候选评分：`
- `当前装备评分：`
- `提升值：`
- `回合摘要：`
- `危险提示：`

## 15.2 Recommendation output format
Recommendation-oriented output should prefer:
1. recommendation subject
2. numeric evidence
3. short verdict

Example:
```text
推荐：
- 英雄：狂战士
- 候选评分：88.00
- 当前装备评分：71.00
- 提升值：17.00
- 结论：推荐立即替换。
```

## 15.3 Avoided style
Avoid mixing flavor-text-like wording with rules text in the same block.
Rules text should remain direct, testable, and scannable.

## 16. Screen-by-Screen Behavioral Summary

## 16.1 Main menu
Purpose:
- orient the player
- present grouped actions
- show what type of activity each action belongs to

## 16.2 Stage intelligence
Purpose:
- explain the next fight
- summarize threats
- suggest short strategic adjustments

## 16.3 Battle playback
Purpose:
- show key events
- show evolving HP state through existing snapshots
- add compact summaries for meaning, not just sequence

## 16.4 Party view
Purpose:
- summarize current active team
- show responsibility and upgrade need

## 16.5 Hero list / detail
Purpose:
- move cleanly from roster overview to focused inspection

## 16.6 Inventory management
Purpose:
- support quick equip decisions with confidence
- show both explanation and direct action affordances

## 16.7 Codex
Purpose:
- explain systems consistently
- support lookup without repeating full gameplay screens

## 17. Implementation Mapping to Current Code

## 17.1 Primary files
Most of the first implementation pass should stay in:
- `src/abyss_echoes/cli.py`
- `tests/engine/test_battle.py`

Potential supporting text helpers may remain in:
- `src/abyss_echoes/i18n.py`

## 17.2 Current functions likely to change
- `render_menu`
- `render_stage`
- `render_party`
- `render_heroes`
- `render_hero_detail`
- `render_hero_recommendation`
- `render_item_codex_detail`
- `render_inventory_detail`
- `render_item_score_comparison`
- `left_panel_lines`
- `right_panel_lines`
- battle playback center-text assembly in `TerminalUI`

## 17.3 Existing functions to preserve conceptually
- `render_inventory_management`
- `inventory_items_for_hero`
- codex navigation handlers
- inventory navigation handlers
- snapshot-based battle playback behavior

## 18. Implementation Priorities

## 18.1 Priority P1
Highest-value changes with immediate UX gain:
1. add battle round summaries / danger hints
2. compress and refocus left panel content
3. add natural-language verdict lines to equipment comparison

## 18.2 Priority P2
Structural readability pass:
4. reorganize party view and hero detail layout
5. normalize item codex and inventory detail text templates
6. group main menu actions by conceptual category

## 18.3 Priority P3
Future polish:
7. add stronger prediction-style danger hints
8. add recommendation strength labels for heroes/items
9. add broader shared helper functions for reusable detail formatting
10. add optional color/highlight refinements when readability improves materially

## 19. Testing Strategy

## 19.1 Required method
Implementation should use TDD-style slices:
1. add a failing render or behavior test
2. run the targeted test and observe failure
3. implement minimal change
4. rerun targeted test
5. rerun broader suite

## 19.2 Test targets
Likely tests should cover:
- left panel compact content shape
- battle summary line appearance
- verdict line appearance in comparison output
- menu grouping output
- normalized codex/detail section order
- no regression in inventory focus behavior

## 19.3 Non-goal
Do not try to test visual beauty.
Tests should verify stable textual structure, required labels, and preserved behavior.

## 20. Non-Negotiable Rules

1. The UI remains terminal-first and Python-based.
2. The existing three-panel mental model is preserved.
3. UI changes must not silently change gameplay rules.
4. High-frequency panels stay compact.
5. Long descriptions stay in focused views.
6. Inventory detail and codex detail remain textually consistent for legendary effects.
7. Recommendation screens must include both numbers and short verdicts.
8. Work should be implemented incrementally with verification after each slice.

## 21. Suggested First Execution Slice

The first implementation slice after this document should include exactly:
1. battle round summary lines in the center panel
2. left panel compression and explicit situation line
3. verdict output in `render_item_score_comparison(...)`

This slice is recommended because it improves the player's most frequent decision surfaces without requiring broad architectural changes.
