---
doc_type: game_design_spec
project: Abyss Echoes
feature: single-character-mage-loot-rpg
status: draft
primary_language: zh-CN
source_of_truth: true
ai_readability: high
schema_version: 1
keywords:
  - action-rpg
  - auto-battle
  - mage
  - loot
  - abyss
  - boss-farming
  - fire
  - ice
  - lightning
supersedes_docs:
  - docs/ai-context/abyss-echoes-redesign-v2.md
  - docs/ai-context/cli-auto-battler-design.md
compatible_with_docs:
  - docs/ai-context/cli-ui-optimization.md
normative_rules:
  - 项目当前主方向是单角色刷宝养成，不是队伍型长期养成。
  - 初始职业只做法师，不做多职业并行实现。
  - 初始版本不做专精系统，改为火、冰、电三系技能树与技能配置。
  - 战斗为完全自动战斗，不提供战中手动操作。
  - 战斗开始时角色能量默认为全满。
  - 自动施法逻辑优先释放次要技能；若能量不足则释放主技能。
  - 角色固定装备 1 个主技能、1 个次要技能、5 个被动技能。
  - 初始版本鼓励单元素主修；主技能与次要技能前期必须同元素。
  - 后期仅允许通过特殊传奇打破主技能与次要技能的同元素限制。
  - 装备系统是核心玩法之一，必须保留刷装、对比、替换、毕业追求。
  - 不引入装备套装系统。
  - 角色等级上限为 70。
  - 70 级后进入终局掉落阶段，核心终局装等为 850 与 900。
  - 900 装等装备为先祖装备；先祖词缀数值范围为 850 的两倍。
  - 星词缀要求该词缀达到严格满值；星词缀只允许出现在 900 先祖装备上。
  - 普通世界掉落产出通用装备；区域 Boss 掉落 Boss 专属传奇；深渊产出钥匙碎片与高质量通用掉落。
  - 区域 Boss 需要消耗深渊钥匙挑战。
  - 装备后处理只能修整掉落，不能替代掉落本身。
  - 不允许通过工坊把 850 升级为 900。
  - 不允许通过工坊制造星词缀。
---

# Abyss Echoes 单角色法师刷宝养成设计文档

## 1. Goal

将 Abyss Echoes 重构为一个 **单角色、自动战斗、刷装备驱动** 的法师成长游戏。玩家围绕一个法师角色，在火、冰、电三系中构筑 build，通过世界区域、深渊、区域 Boss 的循环获取更高品质装备、传奇特效、Boss 专属与终局先祖装备，并逐步推进更高深渊与更高 Boss 难度。

该文档是当前版本的 **AI 可读 source-of-truth 草案**。目标是让未来 AI 代理可以直接读取本文件，理解：
- 游戏主循环
- 法师职业规则
- 技能与被动结构
- 掉落与装备系统
- 深渊/Boss 循环
- 后处理系统边界
- UI 信息架构

## 2. Scope

### 2.1 In scope
- 单角色主玩法
- 初始职业：法师
- 火 / 冰 / 电 三元素玩法身份
- 自动战斗规则
- 主技能 / 次要技能 / 被动技能配置
- 技能解锁与技能点成长节奏
- 装备槽位与词缀池
- 稀有度、装等、先祖、星词缀规则
- 世界掉落 / 深渊 / 区域 Boss / 专属传奇循环
- 强化 / 洗练 / 萃取 / 刻印等后处理系统
- CLI 信息架构与主要页面组织

### 2.2 Out of scope
- 多职业并行实现
- 专精系统
- 队伍型 5 人长期养成
- 手动战中操作
- 套装系统
- 850 -> 900 工坊升级
- 星词缀工坊制造
- 无限传奇图鉴
- PvP
- 图形化前端

## 3. Core Principles

1. **掉落爽优先**
   - 掉落必须持续提供期待。
   - 传奇、Boss 专属、先祖、星词缀必须具备强识别度。

2. **养成爽并重**
   - 升级要解锁内容，不只是堆面板。
   - 玩家必须感受到技能、被动、装备三层同时成长。

3. **单元素主修清晰**
   - 火法、冰法、电法必须一眼能看出差异。
   - 初始版本不鼓励平均点三系。

4. **主技能是引擎，次要技能是招牌**
   - 主技能负责产能与铺垫。
   - 次要技能负责耗能、爆发与 build 宣言。

5. **后处理只修整，不替代掉落**
   - 洗练只能救差一点的装备。
   - 毕业装必须主要来自掉落。

6. **CLI 必须帮助筛垃圾**
   - 系统自动做初筛，玩家只做确认。
   - 不允许因为装备系统太重而让管理成为主要负担。

## 4. System Overview

## 4.1 High-level game loop

```text
进入游戏
-> 查看角色当前 build / 装备 / 资源 / 推荐行动
-> 选择战斗来源（世界区域 / 深渊 / 区域 Boss）
-> 进行自动战斗
-> 结算并显示重点掉落
-> 处理装备（装备 / 锁定 / 待分解 / 分解）
-> 如有需要，进入工坊强化 / 洗练 / 萃取 / 刻印
-> 角色整体变强
-> 挑战更高深渊或更高 Rank Boss
-> 重复
```

## 4.2 Endgame loop

```text
世界区域补基础 850
-> 深渊推进并获取钥匙碎片
-> 合成钥匙
-> 挑战区域 Boss
-> 获取 Boss 专属传奇 / 高质量终局底材
-> build 成型或升级
-> 返回深渊挑战更高层
-> 解锁更高 Boss Rank
-> 追逐 900 先祖 / 星词缀 / 多星先祖传奇
```

## 5. Core Combat Rules

## 5.1 Base combat mode
- 战斗为完全自动。
- 无战中主动操作。
- 战斗开始时能量默认全满。
- 战斗结束后进入结算与掉落界面。

## 5.2 Skill priority rule

```text
if current_energy >= secondary_skill_cost:
    cast secondary_skill
else:
    cast main_skill
```

### Clarifications
- 主技能负责生成能量。
- 次要技能负责消耗能量。
- 后期特殊传奇可以改写部分资源规则，但默认规则仍然成立。

## 5.3 Combat identity by element
- 火：燃烧 / 引爆
- 冰：冻结 / 防御
- 电：连锁 / 回能

## 6. Character Model

## 6.1 Character shape
- 单角色
- 初始职业只做法师
- 角色等级上限 70
- 70 级后进入终局刷装阶段

## 6.2 Combat loadout
角色固定携带：
- 1 个主技能
- 1 个次要技能
- 5 个被动技能

## 6.3 Element rules
- 初始版本鼓励单元素主修。
- 前期主技能与次要技能必须同元素。
- 后期允许极少数传奇打破该限制。

## 7. Skills

## 7.1 Main skill rules
- 主技能的主要职责是产能。
- 主技能同时负责施加元素前置状态。
- 主技能不是一次性过渡技能，必须在后期特定 build 中继续有价值。

## 7.2 Secondary skill rules
- 次要技能的主要职责是耗能与兑现 build。
- 次要技能应比主技能更像“流派宣言”。
- 玩家更常通过次要技能识别当前流派，例如：爆燃火法、冻结冰法、过载电法。

## 7.3 Passive skill rules
- 被动技能与技能树分离。
- 被动技能通过固定技能槽装配。
- 被动技能自由搭配，不做槽位职责限制。
- 被动技能是 build 组件，不能只是小面板词缀。

## 7.4 Main skill pool

### Template 1: 魔弹型（稳定产能）
- 火花术
- 冰刺术
- 电弧术

### Template 2: 扩散型（清图 / 铺状态）
- 余烬喷发
- 寒霜脉冲
- 链式放电

### Template 3: 引擎型（build 上限）
- 焚流术
- 霜界刻印
- 风暴引线

### Main skill shared upgrade groups
每个主技能都有 3 组强化节点：
1. 形态组
2. 元素状态组
3. 循环联动组

每组：
- 3 个节点
- 节点互斥
- 每组只能选 1 个

## 7.5 Secondary skill pool

### Template 1: 核心兑现型
- 爆燃术
- 冰封术
- 过载术

### Template 2: 范围清场型
- 烈焰新星
- 寒霜环
- 链暴术

### Template 3: 终局机制型
- 灾焰降临
- 绝对零域
- 雷暴核心

### Secondary skill shared upgrade groups
每个次要技能都有 3 组强化节点：
1. 形态组
2. 节奏组
3. 机制组

每组：
- 3 个节点
- 节点互斥
- 每组只能选 1 个

## 7.6 Passive pools

### Fire passive pool
- 余烬专注
- 爆燃大师
- 燎原之火
- 持续炙烤
- 灰烬回流
- 炽焰护幕

### Ice passive pool
- 寒意渗透
- 碎冰律令
- 深寒蔓延
- 寒霜壁垒
- 低温折磨
- 静霜调息

### Lightning passive pool
- 电荷聚焦
- 过载本能
- 感电扩张
- 雷暴节律
- 惊雷回授
- 导体护层

### Generic passive pool
- 奥能扩容
- 法力导流
- 秘法屏障
- 元素庇护
- 精准施法
- 猎首者

## 8. Skill Growth and Unlock Schedule

## 8.1 Skill point rule
- 每升一级获得 1 点技能点。
- 技能点为全职业共用池。
- 当前版本不拆成多种点数资源。

## 8.2 Level caps
- 主技能最高 10 级
- 次要技能最高 10 级
- 被动技能最高 5 级

## 8.3 Active skill upgrade unlock thresholds
对任意主动技能：
- 技能 3 级：解锁强化组 1
- 技能 5 级：解锁强化组 2
- 技能 8 级：解锁强化组 3

## 8.4 Passive slot unlock schedule
- Lv4：第 1 个被动槽
- Lv10：第 2 个被动槽
- Lv20：第 3 个被动槽
- Lv35：第 4 个被动槽
- Lv50：第 5 个被动槽

## 8.5 Skill unlock schedule
### Main skills
- Lv1：主技能模板 1
- Lv15：主技能模板 2
- Lv35：主技能模板 3

### Secondary skills
- Lv3：次要技能模板 1
- Lv22：次要技能模板 2
- Lv40：次要技能模板 3

## 8.6 Progression phases

### Phase A: Lv1-Lv14
目标：形成最基础的产能 -> 耗能循环

### Phase B: Lv15-Lv34
目标：解锁第二套主动技能，build 开始分流

### Phase C: Lv35-Lv49
目标：解锁第三套主动技能，形成后期 build 雏形

### Phase D: Lv50-Lv70
目标：补全 5 个被动槽，打磨完整 build，为终局 farming 做准备

## 8.7 First-pass combat numeric baseline

### Numeric classification convention
- **hard rule**：实现时不可轻易改动，会直接改变玩法结构。
- **MVP locked baseline**：首版实现默认采用的正式数值基线。
- **post-playtest tunable value**：首版可先按文档落地，但联调/实测后允许调参。

### Shared resource rules
- 基础最大能量：100
- 战斗开场能量：100
- 主技能以稳定循环为第一目标，单次释放产能必须高于 0
- 次要技能单次释放后，默认不允许出现负能量

### Main skill template baseline
| Template | 代表定位 | 基础总伤害系数 | 基础产能 | 推荐命中形态 |
| --- | --- | --- | --- | --- |
| Template 1 | 稳定产能 | 0.90 | 18 | 单体 / 窄线 |
| Template 2 | 清图铺状态 | 1.35 | 14 | 小范围 / 连锁 3 目标 |
| Template 3 | build 引擎 | 1.80 | 10 | 条件触发 / 延迟爆发 |

### Secondary skill template baseline
| Template | 代表定位 | 基础总伤害系数 | 基础耗能 | 补充说明 |
| --- | --- | --- | --- | --- |
| Template 1 | 核心兑现 | 3.00 | 40 | 最稳定的爆发按钮 |
| Template 2 | 范围清场 | 4.80 | 65 | 清图效率高于单体 |
| Template 3 | 终局机制 | 7.20 | 100 | 终局 build 核心兑现技 |

### Skill level scaling rule
- 主技能每升 1 级：伤害系数 `+9%` 当前基值。
- 主技能在 Lv3 / Lv6 / Lv9：额外 `+1` 产能。
- 次要技能每升 1 级：伤害系数 `+12%` 当前基值。
- 次要技能在 Lv4 / Lv7 / Lv10：基础耗能 `-2`。
- 被动技能 Lv1 为完整效果基线，Lv2-Lv5 每级额外提高该被动基础效果的 `15%`。

### Reference output at max level
| Skill type | Template | Lv10 参考总伤害系数 | Lv10 参考资源值 |
| --- | --- | --- | --- |
| Main | Template 1 | 1.63 | 21 产能 |
| Main | Template 2 | 2.45 | 17 产能 |
| Main | Template 3 | 3.27 | 13 产能 |
| Secondary | Template 1 | 6.24 | 34 耗能 |
| Secondary | Template 2 | 9.98 | 59 耗能 |
| Secondary | Template 3 | 14.98 | 94 耗能 |

### Numeric implementation status
- 以下数值表默认视为 **MVP locked baseline**，实现阶段可直接落成数据表默认值。
- 后续平衡只允许在不破坏主技能产能 / 次要技能兑现的结构前提下微调。
- 若后续测试发现过强或过弱，优先调整 `伤害系数`，其次调整 `产能/耗能`，最后才调整解锁节奏。

### Passive numeric budget rule
- 纯输出被动 Lv1 的标准预算：约等于 `+12%` 单一条件输出收益。
- 输出 + 循环混合被动 Lv1 的标准预算：`+8%` 输出收益 + 1 个中等循环组件。
- 纯防御被动 Lv1 的标准预算：约等于 `+10%` 有条件减伤或 `+18%` 屏障相关收益。
- 通用被动的总预算必须低于同等级单元素专属被动约 `15%-20%`，以保证单元素主修激励成立。

## 9. Equipment System

## 9.1 Rarity rules
- 普通（白色）：2 条词缀
- 魔法（蓝色）：3 条词缀
- 稀有（黄色）：4 条词缀
- 传奇（橙色）：4 条词缀 + 1 条传奇特效

## 9.2 Endgame item levels
- 角色 70 级后进入终局掉落阶段
- 终局装等：850 与 900
- 850：普遍终局掉落
- 900：先祖装备
- 900 词缀范围为 850 的 2 倍

## 9.3 Star affix rules
- 星词缀要求该词缀达到严格满值
- 星词缀只允许出现在 900 先祖装备上
- 装备有几条星词缀，名称显示几颗星

## 9.4 Equipment slot pool
### Core build slots
- 武器
- 副手
- 项链
- 戒指 1
- 戒指 2

### Armor / support slots
- 头部
- 胸部
- 腿部
- 手部
- 肩部
- 护腕

## 9.5 Slot responsibilities

### Weapon
- 最高攻击价值
- 主输出词缀
- 技能相关传奇优先

### Off-hand
- 平衡 build 槽
- 循环 / 防御 / 技能辅助

### Amulet
- 高价值综合槽
- 高级循环 / 元素总增益 / Boss 场景收益

### Rings
- 元素词缀与循环词缀高频承载位
- 适合输出 / 循环细调

### Head / Chest / Legs
- 防御与通用词缀为主
- 不承担主要输出构筑职责

### Hands
- 输出型护甲位
- 攻击词缀最多可出现 4 条

### Shoulders
- 平衡功能位
- 攻击词缀最多可出现 2 条

### Bracers
- 小型 build 功能位
- 攻击词缀最多可出现 2 条

## 9.6 Affix categories
内部设计使用 4 类词缀：
1. 攻击类
2. 防御类
3. 循环 / 通用类
4. 元素专属类

### Attack affixes
- 法术伤害提高
- 主技能伤害提高
- 次要技能伤害提高
- 暴击率
- 暴击伤害
- 对精英伤害
- 对 Boss 伤害
- 施法速度
- 对受控目标伤害
- 对带元素异常目标伤害

### Defense affixes
- 最大生命
- 伤害减免
- 对精英伤害减免
- 对 Boss 伤害减免
- 屏障强度
- 拥有屏障时减伤
- 元素抗性
- 低生命时减伤
- 受控状态抗性
- 被命中后短时获得防御提升

### Cycle / generic affixes
- 最大能量
- 主技能产能提高
- 次要技能耗能降低
- 命中带本元素状态目标时回能
- 击杀回复能量
- 开场能量增益
- 施放次要技能后获得短时护盾
- 施放主技能后下次次要技能增伤
- 次要技能命中后短时施法速度提高

### Fire affixes
- 火焰伤害提高
- 燃烧伤害提高
- 燃烧持续时间提高
- 对燃烧目标伤害提高
- 引爆伤害提高
- 火系次要技能对燃烧目标额外收益

### Ice affixes
- 冰霜伤害提高
- 寒冷积累提高
- 冻结持续时间提高
- 对受寒目标伤害提高
- 对冻结目标伤害提高
- 拥有屏障时冰系技能收益提高

### Lightning affixes
- 闪电伤害提高
- 感电强度提高
- 对感电目标伤害提高
- 过载伤害提高
- 连锁技能收益提高
- 感电/连锁命中时额外回能收益

## 10. Legendary System

## 10.1 Legendary tiers by role
### Tier 1: 数值放大型
- 简单增强某一技能或玩法
- 可用于前中期 build 起步

### Tier 2: 机制增强型
- 改技能表现
- 改状态交互
- 是中后期主要 build 差异来源

### Tier 3: 规则突破型
- 改写技能搭配或资源逻辑
- 是终局 chase item

## 10.2 World-drop legendary responsibilities

### 10.2.1 Responsibility boundary
世界掉落普通传奇负责：
- build 起步
- 元素内部玩法分流
- 前中期与中后期桥梁件
- 数值放大型与部分机制增强型传奇

世界掉落普通传奇必须让玩家在未刷到 Boss 专属前，也能把某元素“玩起来、玩顺、玩出方向”。

### 10.2.2 Hard limits
世界掉落普通传奇不得负责：
- 终局命名级 build 身份
- 资源规则改写
- 状态语义改写
- 技能调度法则改写
- 跨元素合法化
- 单件形成终局闭环

设计判断尺子：
- “增强既有玩法” -> 优先归普通传奇
- “改写玩法法则” -> 优先归 Boss 专属

### 10.2.3 World-drop legendary pool structure
每个元素的普通传奇池统一分为三层：
- 起步件 x2
- 分流件 x2
- 桥梁件 x2

统一目标：
- 起步件负责建立该元素的基础状态与循环手感
- 分流件负责让同元素内部出现两条以上清晰路线
- 桥梁件负责把普通传奇阶段引向区域 Boss 终局流

### 10.2.4 Fire world-drop legendary pool
- `灰烬余温`：燃烧起步件
- `焚痕手记`：主技能燃烧收益件
- `爆燃引线`：引爆分流件
- `炽域碎星`：范围爆燃件
- `熔流节拍`：技能循环桥梁件
- `余烬催化环`：余烬过渡桥梁件

### 10.2.5 Ice world-drop legendary pool
- `寒意铭卷`：冻结起步件
- `冰裂札记`：碎裂起步件
- `寒壁护符`：屏障分流件
- `凝霜导片`：冻结扩散件
- `霜守之印`：防守转收益桥梁件
- `裂寒回声`：碎裂循环桥梁件

### 10.2.6 Lightning world-drop legendary pool
- `雷痕札记`：感电起步件
- `静电容片`：回能节奏件
- `弧链刻片`：连锁清场件
- `雷幕余振`：感电扩散件
- `过载线圈`：过载预热件
- `风暴节拍仪`：主次技能节奏桥梁件

## 10.3 Regional Boss exclusive responsibilities

### 10.3.1 Pool structure
每位区域 Boss 专属池统一包含：
- 4 件强机制件
- 3 件规则突破件
- 1 件命名级 chase item

### 10.3.2 Boss-exclusive permissions
区域 Boss 专属优先承担：
- 强机制件
- 规则突破件
- 元素终局核心件
- 命名级 chase item
- 终局 build 身份定义件
- 资源规则改写件
- 状态语义改写件
- 技能调度改写件
- 跨元素合法化件
- 单件闭环件

### 10.3.3 Boss-exclusive boundaries
区域 Boss 专属不负责：
- 前期起步
- 通用补丁式增伤
- 可被工坊复制的来源身份

设计目标：
- 火 Boss 掉火系规则
- 冰 Boss 掉冰系规则
- 电 Boss 掉电系规则

区域 Boss 不应只是掉“同元素装备”，而应掉“该元素的终局玩法法则”。

## 10.4 Bosses
### 灰烬监护者
主题：火 / 燃烧 / 引爆

#### 专属池结构
- 强机制件：`灰烬吞脉`、`灼界回响`、`炽痕刻印`、`焚风余潮`
- 规则突破件：`熔烬法典`、`灰王敕令`、`炽心逆流`
- 命名级 chase：`灰烬王冕`

#### 主要路线
- 吞噬爆燃流：`灰烬吞脉` + `熔烬法典`
- 扩散爆燃流：`灼界回响` + `灰王敕令`
- 余烬循环流：`焚风余潮` + `炽心逆流`
- 终局皇冠流：`灰烬王冕`

### 霜狱看守者
主题：冰 / 冻结 / 屏障 / 碎冰

#### 专属池结构
- 强机制件：`霜痕棱刺`、`狱霜回壁`、`寒狱迸裂`、`静寒蓄势`
- 规则突破件：`零度律典`、`霜狱回声`、`极寒护契`
- 命名级 chase：`霜狱棱冠`

#### 主要路线
- 冻结碎裂流：`寒狱迸裂` + `零度律典`
- 壁垒碎冰流：`狱霜回壁` + `极寒护契`
- 扩散碎裂流：`霜痕棱刺` + `霜狱回声`
- 终局皇冠流：`霜狱棱冠`

### 风暴执政官
主题：电 / 感电 / 连锁 / 回能

#### 专属池结构
- 强机制件：`雷痕导体`、`弧链增幅器`、`风暴储容`、`雷幕回振`
- 规则突破件：`风暴律令`、`执政回路`、`过载逆潮`
- 命名级 chase：`风暴心核`

#### 主要路线
- 感电过载流：`雷痕导体` + `过载逆潮`
- 连锁风暴流：`弧链增幅器` + `风暴律令`
- 高频循环流：`风暴储容` + `执政回路`
- 终局心核流：`风暴心核`

## 10.5 Rule-breaking legendary examples

### 10.5.1 Boss-exclusive rulebreaking whitelist
以下效果保留给 Boss 专属或 chase 级规则突破件：
- 允许主技能与次要技能跨元素搭配
- 次要技能释放后自动追加一次主技能
- 改写次要技能的资源逻辑
- 元素状态互相转换或连锁
- 改写状态语义本身
- 改写连锁 / 引爆 / 碎裂 / 过载的底层法则
- 单件形成可持续终局闭环

### 10.5.2 World-drop blacklist mirror
以上效果不得下放至普通传奇。

工坊同样不得复制以上效果：
- Boss 专属不可被萃取
- 规则突破件不可被萃取
- Boss 身份与规则突破效果不可被刻印

## 11. Content Sources and Drop Responsibilities

## 11.1 World areas
职责：
- 升级与基础发育
- 通用装备掉落
- 通用传奇
- 金币与基础材料

世界区域不掉 Boss 专属传奇。

## 11.2 Abyss
职责：
- 主推进轴
- 稳定产出钥匙碎片
- 掉通用高质量装备
- 掉少量深渊专属传奇
- 解锁更高 Boss Rank

## 11.3 Regional Bosses
职责：
- 消耗深渊钥匙进入
- 掉 Boss 专属传奇
- 掉高质量元素相关底材
- 是定向 farm 主舞台

## 12. Key and Boss Loop

## 12.1 Key model
- 深渊掉落钥匙碎片
- 碎片合成通用深渊钥匙
- 钥匙不区分元素类型

## 12.2 Boss access
- 区域 Boss 永久可见
- 入场消耗 1 把深渊钥匙

## 12.3 Boss failure rule
- 失败消耗钥匙
- 失败给予少量保底奖励
- 不返还钥匙

## 12.4 Boss rank unlock rule
- 随深渊层级推进解锁更高 Boss Rank
- 更高 Rank 提供更高装等、更高传奇与先祖概率

## 12.5 Key fragment numeric baseline
- `100` 个钥匙碎片合成 `1` 把深渊钥匙。
- Lv70+ 深渊每次通关固定掉落钥匙碎片，不使用纯随机整钥匙模型。
- 本节数值视为 **MVP locked baseline**；若后续测试调整，优先只改碎片产量，不改碎片合成门槛。

### Abyss fragment yield by floor band
| Abyss floor band | 基础钥匙碎片 | 首通额外奖励 |
| --- | --- | --- |
| 1-9 | 12 | +12 |
| 10-19 | 16 | +16 |
| 20-39 | 20 | +20 |
| 40-59 | 24 | +24 |
| 60-79 | 28 | +28 |
| 80+ | 32 | +32 |

### Fragment bonus rules
- 每连续完成 `3` 次当前已解锁最高层深渊：额外奖励 `+10` 钥匙碎片。
- 若本次深渊为首通新最高层：额外奖励 `+8` 深渊残渣。
- 深渊失败不掉钥匙碎片，但保留推进记录。

## 12.6 Boss rank numeric table
| Boss Rank | 解锁所需深渊层 | Boss 生命倍率 | Boss 伤害倍率 | Boss 专属传奇概率 | 900 先祖概率 |
| --- | --- | --- | --- | --- | --- |
| 1 | 5 | 1.00 | 1.00 | 18% | 2% |
| 2 | 15 | 1.35 | 1.12 | 22% | 4% |
| 3 | 30 | 1.80 | 1.25 | 26% | 6% |
| 4 | 45 | 2.35 | 1.40 | 30% | 9% |
| 5 | 60 | 3.05 | 1.58 | 34% | 12% |
| 6 | 80 | 3.90 | 1.78 | 38% | 16% |

### Boss rank implementation note
- `解锁所需深渊层`、`Boss 生命倍率`、`Boss 伤害倍率` 视为 **MVP locked baseline**。
- `Boss 专属传奇概率` 与 `900 先祖概率` 视为 **post-playtest tunable values**。

### Boss rank reward rules
- Rank 越高，Boss 专属传奇的平均特效 roll 越接近上限。
- Rank 4 起，Boss 专属传奇有 `15%` 概率直接以 900 先祖形态掉落。
- Rank 6 是当前首版数值上限，不再额外细分 Rank 7+。

## 12.7 Boss failure consolation baseline
- Boss 挑战失败时仍消耗 `1` 把深渊钥匙。
- 失败保底奖励：`25` 钥匙碎片、`1-2` 个 Boss 精华、少量金币。
- 同一 Boss 当日首次失败：额外给予 `+10` 钥匙碎片，用于降低试错挫败感。
- 失败保底是 **体验保护规则**，优先保证存在，不要求保底材料数值永久锁死。

## 13. Drop Progression

## 13.1 Leveling phase drop model (Lv1-Lv19)
- 单次战斗掉落件数：`2-4`
- 稀有度权重：白 `68%` / 蓝 `25%` / 黄 `6%` / 橙 `1%`
- 重点是建立快速换装快感，传奇仅作为早期惊喜

## 13.2 Mid phase drop model (Lv20-Lv49)
- 单次战斗掉落件数：`3-5`
- 稀有度权重：白 `20%` / 蓝 `40%` / 黄 `32%` / 橙 `8%`
- build 进入初步成型阶段，传奇开始承担模板定向强化职责

## 13.3 Pre-endgame drop model (Lv50-Lv69)
- 单次战斗掉落件数：`3-5`
- 稀有度权重：白 `5%` / 蓝 `25%` / 黄 `50%` / 橙 `20%`
- 传奇成为关键 build 件来源，为 70+ farming 准备首批机制件

## 13.4 Endgame drop model (Lv70+)
- 只掉 `850 / 900` 终局装等
- 基础装等权重：`850 = 92%`，`900 = 8%`
- 星词缀只在 `900` 上出现
- 900 装备单条词缀出现星的基础概率：`6%`
- 900 装备双星及以上应保持极稀有：目标占全部 900 掉落的 `<= 8%`

## 13.5 Content source probabilities by role
### World 70+
- 每次完成掉落件数：`3-4`
- 传奇概率：`10%`
- 850 概率：`98%`
- 900 概率：`2%`
- Boss 专属：无

### Abyss 70+
- 每次完成掉落件数：`4-6`
- 传奇概率：`16%`
- 850 概率：`94%`
- 900 概率：`6%`
- 钥匙碎片：按 12.5 表稳定产出
- 深渊专属传奇概率：`3%`

### Boss 70+
- 每次完成奖励结构：`1` 个 Boss 奖励位 + `2-3` 个常规掉落位
- Boss 奖励位：按 Boss Rank 表结算 Boss 专属传奇与 900 概率
- 常规掉落位传奇概率：`18%`
- 常规掉落位 850 概率：`90%`
- 常规掉落位 900 概率：`10%`

## 13.6 Endgame target time budget
- 纯刷世界区域时，目标平均 `45-60` 分钟获得 `1` 件可考虑替换的 850 传奇。
- 刷当前合适层级深渊时，目标平均 `20-30` 分钟获得 `1` 把深渊钥匙。
- 刷目标 Boss 时，目标平均 `30-45` 分钟看到 `1` 件 Boss 专属传奇。
- `900` 先祖传奇必须明显慢于普通传奇，目标平均获取时间约为普通 850 传奇的 `4-6` 倍。
- 本节是 **post-playtest tunable target**，用于校验 farming 节奏是否健康，不要求首版精确命中。

## 14. Gear Post-processing

## 14.1 Guiding rule
后处理只能修整掉落，不能替代掉落。

## 14.2 Upgrade / strengthening
- 所有装备统一最高可强化至 `+8`
- 强化只提升底材完成度，不改变掉落来源身份
- 强化不改变词缀种类、数量、是否先祖、是否星
- 强化不允许把桥梁件抬升为规则突破件

### Strengthening multiplier baseline
| 强化等级 | 主属性倍率 |
| --- | --- |
| +0 | 1.00 |
| +1 | 1.04 |
| +2 | 1.08 |
| +3 | 1.12 |
| +4 | 1.16 |
| +5 | 1.20 |
| +6 | 1.24 |
| +7 | 1.28 |
| +8 | 1.32 |

### Strengthening cost baseline
| Target level | Gold | Arcane Shards | 额外材料 |
| --- | --- | --- | --- |
| +1 到 +4 | 12,000 | 8 | 无 |
| +5 到 +8 | 28,000 | 16 | 无 |

- 强化等级上限与成本阶梯视为 **MVP locked baseline**。
- 若后续经济过紧或过松，优先调整金币与碎片成本，不调整强化上限。

## 14.3 Reroll / enchant
- 每件装备只能洗 1 条词缀
- 洗练后装备标记为已洗练
- 洗练结果不能成为星词缀
- 洗练不能改变 850 / 900 层级
- 洗练不能改变来源层级
- 洗练不能把普通传奇洗成 Boss 身份件
- 洗练不能把桥梁件洗成规则突破件

### Enchant cost baseline
| Item tier | Gold | Arcane Shards | Legendary Embers |
| --- | --- | --- | --- |
| Rare 850 | 35,000 | 12 | 0 |
| Legendary 850 | 80,000 | 24 | 1 |
| Legendary 900 | 150,000 | 40 | 2 |

- 洗练次数限制是 **hard rule**；洗练成本是 **post-playtest tunable value**。

### Enchant result rules
- 每次洗练从该部位合法词缀池中重新抽取 `1` 条词缀。
- 洗练后的新词缀数值在其合法范围内随机，但不能达到星词缀门槛。
- 同一装备第 `2` 次尝试洗练不被允许。
- 洗练只允许修正“差一点可用”的装备，不承担创造终局身份的职责。

## 14.4 Extraction / imprinting
- 仅普通传奇特效可被萃取
- 仅普通传奇特效可被刻印到合法部位底材上
- 首版使用单次萃取 / 单次刻印，不做无限图鉴
- 刻印结果不应高于原始特效 roll
- 刻印只提供普通传奇的弱化复制体验，不复制来源身份

### 14.4.1 Extraction / imprinting hard rules
- Boss 专属不可萃取
- Boss 专属不可刻印
- 规则突破件不可萃取
- 规则突破件不可刻印
- 工坊不得复制 Boss 来源身份
- 工坊不得通过萃取 / 刻印制造终局闭环

### Extraction / imprint cost baseline
| Action | Gold | Legendary Embers | Boss Essence |
| --- | --- | --- | --- |
| 萃取普通传奇特效 | 60,000 | 1 | 0 |
| 刻印到 850 底材 | 50,000 | 1 | 0 |
| 刻印到 900 底材 | 95,000 | 2 | 0 |

- Boss 专属与规则突破件不可进入萃取 / 刻印体系是 **hard rule**。
- 萃取 / 刻印成本是 **post-playtest tunable value**。

## 14.5 Materials
- 金币
- 奥术碎片
- 传奇余烬
- 深渊残渣 / Boss 精华

### Material source baseline
- 金币：所有战斗稳定产出；世界区域效率最高。
- 奥术碎片：分解蓝 / 黄装为主来源。
- 传奇余烬：分解传奇装备为主来源。
- 深渊残渣：深渊结算与层级首通奖励。
- Boss 精华：区域 Boss 击败或失败保底奖励。

## 14.5.1 Economy status labels
- 材料来源归属是 **MVP locked baseline**。
- 单次产量、分解产出数量、金币曲线是 **post-playtest tunable values**。

## 14.6 Explicitly forbidden
- 不允许 850 升 900
- 不允许人工制造星词缀
- 不允许全词缀重铸
- 不允许工坊绕过 Boss 专属首次获取
- 不允许萃取 Boss 专属
- 不允许刻印 Boss 专属
- 不允许萃取规则突破件
- 不允许刻印规则突破件
- 不允许通过工坊复制 Boss 来源身份
- 不允许通过工坊制造终局闭环

## 15. Inventory and Loot UX Requirements

## 15.1 Loot result view must use four decision layers
掉落结算界面必须以“帮助玩家快速决策”为首要目标，而不是完整打印所有掉落。

四层展示如下：

1. `L1_interrupt`
   - 必须打断玩家注意力的高价值掉落
   - 典型对象：`lock_candidate`
   - 必须完整展开显示

2. `L2_attention`
   - 应该展示给玩家，但不必像 L1 那样强打断
   - 典型对象：`upgrade_candidate`
   - 以及所有受保护的 `situational` 物品

3. `L3_folded`
   - 默认折叠显示的保留候选 / 分解候选
   - 典型对象：`situational`、`salvage_candidate`
   - 只显示分组摘要，按需展开

4. `L4_silent`
   - 默认静默处理的低价值掉落
   - 典型对象：`trash`
   - 不逐件显示，只在结算末尾给数量摘要

实现原则：
- CLI 默认输出必须是“决策面板”，不是“数据库 dump”
- 高价值掉落优先于完整性
- 玩家主动追查时，系统才展开折叠层与静默层明细

## 15.2 Important loot markers
重要掉落必须使用稳定的短标签体系，优先展示来源与风险，再展示结论。

来源 / 稀缺标签：
- `[BOSS]`
- `[ANC]`
- `[STAR]`
- `[RULE]`
- `[CHASE]`
- `[NEW]`
- `[DUP]`

结论标签：
- `[LOCK]`
- `[UP]`
- `[KEEP]`
- `[SALV]`
- `[TRASH]`

适配 / 对比标签：
- `[NOW]`
- `[FUTURE]`
- `[DELTA+X]`
- `[WORK]`

标签规则：
- 同一物品优先展示不超过 4 个主标签
- 来源/保护类标签优先级高于 build 适配类标签
- 星词缀数量必须可被一眼识别

## 15.3 Inventory tabs
- 全部
- 关注
- 升级候选
- 条件保留
- 传奇
- 先祖
- 已锁定
- 待分解

## 15.4 Protected items
以下物品属于 protected-source 或 protected-state，不得直接进入 `trash` 或自动分解建议：
- 已装备
- 已锁定
- Boss 专属
- 900 先祖
- 星词缀装备
- 规则突破件
- chase item

minimum floor 规则：
- 任意 protected-source 物品，最终 `verdict` 最低不得低于 `situational`
- 任意 protected-source 物品，默认展示层最低不得低于 `L2_attention`

## 15.5 Auto-junk rule
系统只允许自动标记垃圾，不允许自动销毁。

补充规则：
- `auto_junk` 仅允许作用于 `trash`
- `auto_salvage_suggested` 仅允许作用于 `salvage_candidate`
- protected-source 永不自动分解建议
- 首次掉落 / 图鉴首件永不自动分解建议

## 16. CLI Interface Requirements

## 16.1 Top-level navigation
- 开始战斗
- 角色
- 装备
- 工坊
- 仓库
- 系统

## 16.2 Start battle subpages
- 世界区域
- 深渊
- 区域 Boss

## 16.3 Character subpages
- 概览
- 技能配置
- 技能树
- 属性详情

## 16.4 Equipment subpages
- 已装备
- 升级候选
- 槽位对比

## 16.5 Workshop subpages
- 强化
- 洗练
- 萃取
- 刻印

## 16.6 Home screen requirements
首页必须展示：
- 当前角色与 build 摘要
- 当前深渊层级
- 当前 Boss 进度
- 当前资源
- 当前建议行动

## 16.7 Loot review commands
CLI 必须提供统一的掉落审阅入口，支持按 verdict 和重复组追查。

建议命令集合：
- `drops`
- `drops lock`
- `drops up`
- `drops keep`
- `drops salv`
- `drops trash`
- `drops dup <group_id>`
- `drops item <item_id>`

## 16.8 Loot summary order
一次掉落结算结束后，CLI 输出顺序必须固定为：
1. `L1_interrupt`
2. `L2_attention`
3. protected-source `situational`
4. `L3_folded` 保留候选摘要
5. `L3_folded` 分解候选摘要
6. `L4_silent` 低价值摘要
7. 推荐动作摘要

## 16.9 Loot item display template
单件掉落的默认展示应包含：
- 标题行：标签 + 物品名
- 副标题行：槽位 / 装等 / 来源
- 核心评分行：`NOW` / `FUTURE` / `DELTA` / `RARITY`
- 2~5 条压缩 reason
- 1 条推荐动作

L1 物品必须完整展开。
L2 物品默认展开简版。
L3 物品默认折叠。
L4 物品默认只参与末尾统计。

## 16.10 Deduplication rule
CLI 必须支持重复件和近似件的折叠展示，以降低刷屏噪音。

exact duplicate group 判定建议至少参考以下字段：
- `slot`
- `rarity`
- `item_power`
- `source_type`
- `source_boss`
- `legendary_effect_ids`
- `affix_family set`
- `star_affix_count`

near duplicate group 判定建议至少满足：
- 同槽位
- 同传奇特效或同 archetype
- build tags 高度重合
- 评分差异较小

protected-source 物品允许“组内压缩”，但不允许被完全隐藏。

## 17. Minimal Canonical Data Model

```python
from dataclasses import dataclass, field
from typing import Literal

Element = Literal["fire", "ice", "lightning", "neutral"]
Rarity = Literal["common", "magic", "rare", "legendary", "unique"]
Slot = Literal[
    "weapon", "offhand", "amulet", "ring_1", "ring_2",
    "head", "chest", "legs", "hands", "shoulders", "bracers"
]
SourceType = Literal["world_drop", "abyss_drop", "regional_boss", "crafted_output"]
LegendaryTier = Literal["none", "world_legendary", "boss_legendary", "special_unique"]
EffectScope = Literal["numeric", "mechanic", "rulebreaking"]
PowerBand = Literal["bridge", "branch", "core", "chase"]
Verdict = Literal[
    "trash",
    "salvage_candidate",
    "situational",
    "upgrade_candidate",
    "lock_candidate",
]
PresentationLayer = Literal["L1_interrupt", "L2_attention", "L3_folded", "L4_silent"]
WorkshopAction = Literal["none", "strengthen", "reroll", "refine", "extract"]
ReasonCategory = Literal["rarity", "current", "future", "salvage", "workshop", "warning"]

@dataclass(slots=True)
class EquippedSkills:
    main_skill_id: str
    secondary_skill_id: str
    passive_skill_ids: list[str]  # len == 5

@dataclass(slots=True)
class CharacterState:
    level: int
    current_element: Element
    skill_points_unspent: int
    equipped_skills: EquippedSkills
    abyss_floor: int
    unlocked_boss_ranks: dict[str, int]

@dataclass(slots=True)
class AffixProfile:
    affix_family: str
    affix_key: str
    value: float
    min_roll: float
    max_roll: float
    normalized_roll: float
    is_star: bool = False
    is_core_for_current_item_type: bool = False

@dataclass(slots=True)
class LegendaryEffectProfile:
    effect_id: str
    name: str
    effect_scope: EffectScope
    granted_by: LegendaryTier
    power_band: PowerBand
    build_tags: list[str] = field(default_factory=list)
    is_boss_identity_effect: bool = False
    is_rulebreaking: bool = False
    extractable: bool = False
    imprintable: bool = False

@dataclass(slots=True)
class WorkshopState:
    strengthen_level: int = 0
    reroll_count: int = 0
    refine_count: int = 0
    imprinted_effect_id: str | None = None
    can_strengthen: bool = True
    can_reroll: bool = True
    can_refine: bool = True
    can_extract: bool = False
    can_imprint: bool = False

@dataclass(slots=True)
class ItemStaticProfile:
    item_id: str
    name: str
    slot: Slot
    rarity: Rarity
    item_power: int
    is_ancestral: bool
    star_affix_count: int
    source_type: SourceType
    source_boss: str | None = None
    legendary_tier: LegendaryTier = "none"
    primary_element: Element = "neutral"
    affixes: list[AffixProfile] = field(default_factory=list)
    legendary_effects: list[LegendaryEffectProfile] = field(default_factory=list)
    workshop_state: WorkshopState = field(default_factory=WorkshopState)
    is_first_discovery: bool = False
    locked: bool = False
    enchanted: bool = False

@dataclass(slots=True)
class EquippedItemReference:
    slot: Slot
    equipped_item_id: str | None
    effective_power_score: float
    build_tags: list[str] = field(default_factory=list)

@dataclass(slots=True)
class BuildContext:
    player_level: int
    current_element: Element
    main_skill_id: str
    secondary_skill_id: str
    passive_skill_ids: list[str]
    current_build_tags: list[str] = field(default_factory=list)
    future_build_tags: list[str] = field(default_factory=list)
    preferred_affix_families: list[str] = field(default_factory=list)
    avoided_affix_families: list[str] = field(default_factory=list)
    equipped: dict[Slot, EquippedItemReference] = field(default_factory=dict)
    unlocked_boss_paths: list[str] = field(default_factory=list)
    discovered_legendary_effect_ids: list[str] = field(default_factory=list)

@dataclass(slots=True)
class ScoreBreakdown:
    current_build_fit: float
    same_slot_upgrade_score: float
    future_build_fit: float
    source_rarity_score: float
    salvage_value_score: float
    workshop_potential_score: float

@dataclass(slots=True)
class ProtectionFlags:
    protected_source: bool = False
    protected_by_boss_identity: bool = False
    protected_by_ancestral: bool = False
    protected_by_star_affix: bool = False
    protected_by_rulebreaking: bool = False
    protected_by_chase: bool = False

@dataclass(slots=True)
class ReasonRecord:
    code: str
    category: ReasonCategory
    weight: float

@dataclass(slots=True)
class DropEvaluation:
    item_id: str
    scores: ScoreBreakdown
    protections: ProtectionFlags
    verdict: Verdict
    auto_lock_suggested: bool
    auto_salvage_suggested: bool
    workshop_action: WorkshopAction = "none"
    reasons: list[ReasonRecord] = field(default_factory=list)
    duplicate_group_id: str | None = None
    representative_item_id: str | None = None

@dataclass(slots=True)
class PresentationBadge:
    text: str
    priority: int

@dataclass(slots=True)
class PresentationLine:
    label: str
    value: str
    priority: int = 0

@dataclass(slots=True)
class DropPresentation:
    item_id: str
    layer: PresentationLayer
    title_line: str
    subtitle_line: str | None = None
    badges: list[PresentationBadge] = field(default_factory=list)
    summary_lines: list[PresentationLine] = field(default_factory=list)
    reason_lines: list[str] = field(default_factory=list)
    recommended_action_line: str | None = None
    folded_group_label: str | None = None
    folded_children_count: int = 0

@dataclass(slots=True)
class ResourceState:
    gold: int
    arcane_shards: int
    legendary_embers: int
    abyss_residue: int
    key_fragments: int
    abyss_keys: int
```

## 17.0.1 Static invariants
以下数据约束属于 hard rule：
- `is_ancestral == true` 时，`item_power` 必须为 900
- `star_affix_count > 0` 时，`is_ancestral` 必须为 true
- `source_boss` 只允许出现在 `source_type == regional_boss` 的物品上
- `boss_legendary` 必须来自 `regional_boss`
- `extractable/imprintable` 必须由特效权限决定，不能由 UI 推断

## 17.0.2 Canonical evaluator order
掉落 evaluator 的固定顺序如下：
1. validate static item invariants
2. compute protection flags
3. compute raw score breakdown
4. normalize scores
5. assign verdict
6. assign auto-lock / auto-salvage
7. choose workshop action
8. generate reason records
9. apply duplicate grouping
10. build presentation model

顺序不可颠倒的关键原因：
- protection flags 必须先于 verdict
- verdict 必须先于 workshop action
- reason records 必须在 verdict 之后生成
- presentation 层不得反向修改业务判断

## 17.1 Canonical implementation table shapes

```python
from typing import Literal, TypedDict

SkillType = Literal["main", "secondary", "passive"]
BalanceTag = Literal["hard_rule", "mvp_locked", "post_playtest_tunable"]
DropSource = Literal["world", "abyss", "boss"]

class SkillTemplateRow(TypedDict):
    skill_id: str
    skill_type: SkillType
    element: Literal["fire", "ice", "lightning"]
    template_index: int
    unlock_level: int
    base_damage_coeff: float
    energy_delta: int  # main > 0, secondary < 0
    targeting: str
    balance_tag: BalanceTag

class BossRankRow(TypedDict):
    rank: int
    unlock_abyss_floor: int
    hp_multiplier: float
    damage_multiplier: float
    exclusive_legendary_drop_rate: float
    ancestral_900_drop_rate: float
    balance_tag: BalanceTag

class EndgameDropTable(TypedDict):
    table_id: str
    source: DropSource
    drops_per_clear: str
    legendary_rate: float | None
    item_power_850_rate: float
    item_power_900_rate: float
    notes: list[str]
    balance_tag: BalanceTag

class CraftCostRow(TypedDict):
    action_id: str
    gold: int
    arcane_shards: int
    legendary_embers: int
    boss_essence: int
    balance_tag: BalanceTag

class LegendaryPoolRow(TypedDict):
    item_id: str
    display_name: str
    source_family: str
    element: Literal["fire", "ice", "lightning"]
    permission_tier: Literal["world_drop", "boss_strong_mechanic", "boss_rulebreaking", "boss_chase"]
    power_band: Literal["bridge", "branch", "core", "chase"]
    extractable: bool
    imprintable: bool
    build_tags: list[str]
    balance_tag: BalanceTag
```

## 17.2 Active skill implementation table (MVP)

### Main skills
```yaml
main_skills:
  - skill_id: fire_sparkshot
    display_name: 火花术
    skill_type: main
    element: fire
    template_index: 1
    unlock_level: 1
    base_damage_coeff: 0.90
    energy_gain: 18
    targeting: single_target
    apply_tags: [burn_setup]
    balance_tag: mvp_locked
  - skill_id: ice_spikeshot
    display_name: 冰刺术
    skill_type: main
    element: ice
    template_index: 1
    unlock_level: 1
    base_damage_coeff: 0.90
    energy_gain: 18
    targeting: single_target
    apply_tags: [chill_setup]
    balance_tag: mvp_locked
  - skill_id: lightning_arcshot
    display_name: 电弧术
    skill_type: main
    element: lightning
    template_index: 1
    unlock_level: 1
    base_damage_coeff: 0.90
    energy_gain: 18
    targeting: single_target
    apply_tags: [shock_setup]
    balance_tag: mvp_locked
  - skill_id: fire_ember_burst
    display_name: 余烬喷发
    skill_type: main
    element: fire
    template_index: 2
    unlock_level: 15
    base_damage_coeff: 1.35
    energy_gain: 14
    targeting: small_aoe
    apply_tags: [burn_setup, spread]
    balance_tag: mvp_locked
  - skill_id: ice_frost_pulse
    display_name: 寒霜脉冲
    skill_type: main
    element: ice
    template_index: 2
    unlock_level: 15
    base_damage_coeff: 1.35
    energy_gain: 14
    targeting: small_aoe
    apply_tags: [chill_setup, defensive_trigger]
    balance_tag: mvp_locked
  - skill_id: lightning_chain_cast
    display_name: 链式放电
    skill_type: main
    element: lightning
    template_index: 2
    unlock_level: 15
    base_damage_coeff: 1.35
    energy_gain: 14
    targeting: chain_3
    apply_tags: [shock_setup, chain]
    balance_tag: mvp_locked
  - skill_id: fire_flux_channel
    display_name: 焚流术
    skill_type: main
    element: fire
    template_index: 3
    unlock_level: 35
    base_damage_coeff: 1.80
    energy_gain: 10
    targeting: delayed_burst
    apply_tags: [burn_setup, engine]
    balance_tag: mvp_locked
  - skill_id: ice_sigil_domain
    display_name: 霜界刻印
    skill_type: main
    element: ice
    template_index: 3
    unlock_level: 35
    base_damage_coeff: 1.80
    energy_gain: 10
    targeting: delayed_zone
    apply_tags: [chill_setup, engine]
    balance_tag: mvp_locked
  - skill_id: lightning_storm_fuse
    display_name: 风暴引线
    skill_type: main
    element: lightning
    template_index: 3
    unlock_level: 35
    base_damage_coeff: 1.80
    energy_gain: 10
    targeting: delayed_chain
    apply_tags: [shock_setup, engine]
    balance_tag: mvp_locked
```

### Secondary skills
```yaml
secondary_skills:
  - skill_id: fire_ignite_blast
    display_name: 爆燃术
    skill_type: secondary
    element: fire
    template_index: 1
    unlock_level: 3
    base_damage_coeff: 3.00
    energy_cost: 40
    targeting: single_target
    consume_tags: [burn]
    balance_tag: mvp_locked
  - skill_id: ice_freeze_spike
    display_name: 冰封术
    skill_type: secondary
    element: ice
    template_index: 1
    unlock_level: 3
    base_damage_coeff: 3.00
    energy_cost: 40
    targeting: single_target
    consume_tags: [chill, freeze]
    balance_tag: mvp_locked
  - skill_id: lightning_overload_strike
    display_name: 过载术
    skill_type: secondary
    element: lightning
    template_index: 1
    unlock_level: 3
    base_damage_coeff: 3.00
    energy_cost: 40
    targeting: single_target
    consume_tags: [shock, overload]
    balance_tag: mvp_locked
  - skill_id: fire_nova_ring
    display_name: 烈焰新星
    skill_type: secondary
    element: fire
    template_index: 2
    unlock_level: 22
    base_damage_coeff: 4.80
    energy_cost: 65
    targeting: medium_aoe
    consume_tags: [burn, explode]
    balance_tag: mvp_locked
  - skill_id: ice_frost_ring
    display_name: 寒霜环
    skill_type: secondary
    element: ice
    template_index: 2
    unlock_level: 22
    base_damage_coeff: 4.80
    energy_cost: 65
    targeting: medium_aoe
    consume_tags: [chill, freeze]
    balance_tag: mvp_locked
  - skill_id: lightning_chain_surge
    display_name: 链暴术
    skill_type: secondary
    element: lightning
    template_index: 2
    unlock_level: 22
    base_damage_coeff: 4.80
    energy_cost: 65
    targeting: chain_5
    consume_tags: [shock, chain]
    balance_tag: mvp_locked
  - skill_id: fire_cataclysm_drop
    display_name: 灾焰降临
    skill_type: secondary
    element: fire
    template_index: 3
    unlock_level: 40
    base_damage_coeff: 7.20
    energy_cost: 100
    targeting: large_aoe
    consume_tags: [burn, explode]
    balance_tag: mvp_locked
  - skill_id: ice_absolute_zero
    display_name: 绝对零域
    skill_type: secondary
    element: ice
    template_index: 3
    unlock_level: 40
    base_damage_coeff: 7.20
    energy_cost: 100
    targeting: large_zone
    consume_tags: [freeze, shatter]
    balance_tag: mvp_locked
  - skill_id: lightning_tempest_core
    display_name: 雷暴核心
    skill_type: secondary
    element: lightning
    template_index: 3
    unlock_level: 40
    base_damage_coeff: 7.20
    energy_cost: 100
    targeting: chain_storm
    consume_tags: [shock, overload]
    balance_tag: mvp_locked
```

## 17.3 Passive and progression implementation constants

```yaml
passive_pool_counts:
  fire: 6
  ice: 6
  lightning: 6
  generic: 6
  total: 24
  balance_tag: mvp_locked

passive_slots:
  - unlock_level: 4
    slot_count: 1
  - unlock_level: 10
    slot_count: 2
  - unlock_level: 20
    slot_count: 3
  - unlock_level: 35
    slot_count: 4
  - unlock_level: 50
    slot_count: 5

skill_level_caps:
  main: 10
  secondary: 10
  passive: 5

active_skill_upgrade_unlocks:
  - skill_level: 3
    unlock_group: 1
  - skill_level: 5
    unlock_group: 2
  - skill_level: 8
    unlock_group: 3
```

## 17.4 Boss and rank implementation tables

```yaml
bosses:
  - boss_id: ashen_warden
    display_name: 灰烬监护者
    element: fire
    exclusive_family: fire_boss_exclusive
    arena_tag: burn_explode_arena
    balance_tag: mvp_locked
  - boss_id: frost_gaoler
    display_name: 霜狱看守者
    element: ice
    exclusive_family: ice_boss_exclusive
    arena_tag: freeze_barrier_arena
    balance_tag: mvp_locked
  - boss_id: storm_archon
    display_name: 风暴执政官
    element: lightning
    exclusive_family: lightning_boss_exclusive
    arena_tag: shock_chain_arena
    balance_tag: mvp_locked

boss_rank_table:
  - rank: 1
    unlock_abyss_floor: 5
    hp_multiplier: 1.00
    damage_multiplier: 1.00
    exclusive_legendary_drop_rate: 0.18
    ancestral_900_drop_rate: 0.02
    balance_tag: mvp_locked
  - rank: 2
    unlock_abyss_floor: 15
    hp_multiplier: 1.35
    damage_multiplier: 1.12
    exclusive_legendary_drop_rate: 0.22
    ancestral_900_drop_rate: 0.04
    balance_tag: mvp_locked
  - rank: 3
    unlock_abyss_floor: 30
    hp_multiplier: 1.80
    damage_multiplier: 1.25
    exclusive_legendary_drop_rate: 0.26
    ancestral_900_drop_rate: 0.06
    balance_tag: mvp_locked
  - rank: 4
    unlock_abyss_floor: 45
    hp_multiplier: 2.35
    damage_multiplier: 1.40
    exclusive_legendary_drop_rate: 0.30
    ancestral_900_drop_rate: 0.09
    balance_tag: post_playtest_tunable
  - rank: 5
    unlock_abyss_floor: 60
    hp_multiplier: 3.05
    damage_multiplier: 1.58
    exclusive_legendary_drop_rate: 0.34
    ancestral_900_drop_rate: 0.12
    balance_tag: post_playtest_tunable
  - rank: 6
    unlock_abyss_floor: 80
    hp_multiplier: 3.90
    damage_multiplier: 1.78
    exclusive_legendary_drop_rate: 0.38
    ancestral_900_drop_rate: 0.16
    balance_tag: post_playtest_tunable

boss_failure_rewards:
  key_cost: 1
  fragment_refund_flat: 25
  first_daily_fail_bonus_fragments: 10
  boss_essence_min: 1
  boss_essence_max: 2
  balance_tag: hard_rule

boss_exclusive_pool_structure:
  strong_mechanic_count: 4
  rulebreaking_count: 3
  chase_count: 1
  balance_tag: hard_rule

boss_exclusive_pools:
  ashen_warden:
    strong_mechanics: [灰烬吞脉, 灼界回响, 炽痕刻印, 焚风余潮]
    rulebreaking: [熔烬法典, 灰王敕令, 炽心逆流]
    chase: [灰烬王冕]
  frost_gaoler:
    strong_mechanics: [霜痕棱刺, 狱霜回壁, 寒狱迸裂, 静寒蓄势]
    rulebreaking: [零度律典, 霜狱回声, 极寒护契]
    chase: [霜狱棱冠]
  storm_archon:
    strong_mechanics: [雷痕导体, 弧链增幅器, 风暴储容, 雷幕回振]
    rulebreaking: [风暴律令, 执政回路, 过载逆潮]
    chase: [风暴心核]
```

## 17.5 Drop table implementation baselines

```yaml
leveling_rarity_weights:
  - phase_id: lv_1_19
    drops_per_clear: [2, 4]
    rarity_weights:
      common: 0.68
      magic: 0.25
      rare: 0.06
      legendary: 0.01
    balance_tag: mvp_locked
  - phase_id: lv_20_49
    drops_per_clear: [3, 5]
    rarity_weights:
      common: 0.20
      magic: 0.40
      rare: 0.32
      legendary: 0.08
    balance_tag: mvp_locked
  - phase_id: lv_50_69
    drops_per_clear: [3, 5]
    rarity_weights:
      common: 0.05
      magic: 0.25
      rare: 0.50
      legendary: 0.20
    balance_tag: mvp_locked

endgame_drop_tables:
  - table_id: world_70_plus
    source: world
    drops_per_clear: [3, 4]
    legendary_rate: 0.10
    item_power_850_rate: 0.98
    item_power_900_rate: 0.02
    boss_exclusive_rate: 0.00
    notes: [general_gear_only]
    balance_tag: mvp_locked
  - table_id: abyss_70_plus
    source: abyss
    drops_per_clear: [4, 6]
    legendary_rate: 0.16
    item_power_850_rate: 0.94
    item_power_900_rate: 0.06
    abyss_exclusive_legendary_rate: 0.03
    notes: [high_quality_general_gear, key_fragments_from_separate_table]
    balance_tag: mvp_locked
  - table_id: boss_70_plus_regular_slots
    source: boss
    drops_per_clear: [2, 3]
    legendary_rate: 0.18
    item_power_850_rate: 0.90
    item_power_900_rate: 0.10
    notes: [boss_reward_slot_resolved_by_rank_table]
    balance_tag: post_playtest_tunable

star_affix_rules:
  only_item_power: 900
  per_affix_star_rate: 0.06
  multi_star_share_cap_within_900_drops: 0.08
  balance_tag: post_playtest_tunable

world_legendary_pool_structure:
  per_element:
    starter: 2
    branch: 2
    bridge: 2
  total_per_element: 6
  balance_tag: hard_rule

world_legendary_pools:
  fire: [灰烬余温, 焚痕手记, 爆燃引线, 炽域碎星, 熔流节拍, 余烬催化环]
  ice: [寒意铭卷, 冰裂札记, 寒壁护符, 凝霜导片, 霜守之印, 裂寒回声]
  lightning: [雷痕札记, 静电容片, 弧链刻片, 雷幕余振, 过载线圈, 风暴节拍仪]
```

## 17.6 Key economy and workshop implementation baselines

```yaml
key_economy:
  fragments_per_key: 100
  abyss_fragment_yield:
    - floor_band: [1, 9]
      base_fragments: 12
      first_clear_bonus: 12
    - floor_band: [10, 19]
      base_fragments: 16
      first_clear_bonus: 16
    - floor_band: [20, 39]
      base_fragments: 20
      first_clear_bonus: 20
    - floor_band: [40, 59]
      base_fragments: 24
      first_clear_bonus: 24
    - floor_band: [60, 79]
      base_fragments: 28
      first_clear_bonus: 28
    - floor_band: [80, 999]
      base_fragments: 32
      first_clear_bonus: 32
  highest_floor_streak_bonus:
    clears_required: 3
    bonus_fragments: 10
  balance_tag: mvp_locked

strengthening_costs:
  - action_id: strengthen_plus_1_to_4
    gold: 12000
    arcane_shards: 8
    legendary_embers: 0
    boss_essence: 0
    balance_tag: mvp_locked
  - action_id: strengthen_plus_5_to_8
    gold: 28000
    arcane_shards: 16
    legendary_embers: 0
    boss_essence: 0
    balance_tag: mvp_locked

enchant_costs:
  - action_id: enchant_rare_850
    gold: 35000
    arcane_shards: 12
    legendary_embers: 0
    boss_essence: 0
    balance_tag: post_playtest_tunable
  - action_id: enchant_legendary_850
    gold: 80000
    arcane_shards: 24
    legendary_embers: 1
    boss_essence: 0
    balance_tag: post_playtest_tunable
  - action_id: enchant_legendary_900
    gold: 150000
    arcane_shards: 40
    legendary_embers: 2
    boss_essence: 0
    balance_tag: post_playtest_tunable

imprint_costs:
  - action_id: extract_normal_legendary
    gold: 60000
    arcane_shards: 0
    legendary_embers: 1
    boss_essence: 0
    balance_tag: post_playtest_tunable
  - action_id: imprint_to_850
    gold: 50000
    arcane_shards: 0
    legendary_embers: 1
    boss_essence: 0
    balance_tag: post_playtest_tunable
  - action_id: imprint_to_900
    gold: 95000
    arcane_shards: 0
    legendary_embers: 2
    boss_essence: 0
    balance_tag: post_playtest_tunable

workshop_permission_notes:
  strengthening_max_level: 8
  boss_exclusive_extractable: false
  boss_exclusive_imprintable: false
  rulebreaking_extractable: false
  rulebreaking_imprintable: false
  ordinary_legendary_extractable: true
  imprint_copies_weakened_identity_only: true
  balance_tag: hard_rule
```

## 18. Canonical Pseudocode

### 18.1 Combat skill selection

```python
if current_energy >= secondary_skill_cost:
    cast(secondary_skill)
else:
    cast(main_skill)
```

### 18.2 Endgame play loop

```python
while player_wants_to_progress:
    if needs_base_gear_or_materials:
        run_world_area()
    elif abyss_keys == 0:
        run_abyss_for_key_fragments()
    elif build_needs_boss_exclusive:
        run_regional_boss(target_boss)
    else:
        push_higher_abyss()

    inspect_loot_summary()
    lock_or_equip_relevant_items()
    mark_junk_items()
    dismantle_marked_items()

    if item_is_good_but_not_perfect:
        enchant_one_affix(item)

    if item_is_world_legendary and legendary_power_is_useful_but_base_is_bad:
        extract_world_legendary_power(item)
        imprint_world_legendary_power_on_better_base()

    strengthen_long_term_items()
```

### 18.3 Loot handling invariants

```python
if item.is_boss_exclusive or item.has_rulebreaking_effect:
    deny_extraction()
    deny_imprinting()

if item.is_protected_source:
    verdict_floor = "situational"
    presentation_floor = "L2_attention"

if item.verdict == "trash":
    allow_auto_junk()
else:
    disallow_auto_junk()
```

## 19. Implementation Priorities

### Phase 1: Core combat loop
- 单角色战斗模型
- 法师基础资源循环
- 1 主技能 + 1 次要技能
- 自动施法优先级规则

### Phase 2: Fire/Ice/Lightning first pass
- 一级主技能池
- 一级次要技能池
- 第一批被动池
- 元素状态实现

### Phase 3: Equipment first playable version
- 装备槽位
- 稀有度
- 基础词缀池
- 传奇特效骨架
- 装备对比与评分

### Phase 4: Progression scaffolding
- 技能点
- 技能解锁节奏
- 被动槽解锁
- Lv1-70 成长

### Phase 5: Endgame loop
- 深渊
- 钥匙碎片
- 区域 Boss
- Boss 专属传奇
- 850 / 900 / 先祖 / 星词缀

### Phase 6: Gear post-processing and UX
- 强化
- 洗练
- 萃取与刻印
- 背包筛选
- 自动垃圾标记
- 掉落摘要 UI

## 20. Non-Negotiable Rules

1. 当前主玩法是单角色法师刷宝养成，不是队伍型长期养成。
2. 初始版本只实现法师，不并行实现其他职业。
3. 初始版本不做专精，使用火、冰、电技能树与技能配置。
4. 战斗保持完全自动，战斗开始默认能量全满。
5. 自动战斗优先施放次要技能，能量不足时施放主技能。
6. 角色固定配置 1 主技能、1 次要技能、5 被动技能。
7. 初始版本鼓励单元素主修；前期主/次技能必须同元素。
8. 只有特殊传奇才允许打破主/次技能同元素限制。
9. 角色等级上限为 70。
10. 70 级后核心掉落层为 850 与 900；900 是先祖装备。
11. 星词缀必须是严格满值，并且只允许出现在 900 先祖装备上。
12. 世界区域掉通用装备，深渊掉钥匙碎片与高质量通用装备，区域 Boss 掉 Boss 专属传奇。
13. 装备后处理只能修整掉落，不能替代掉落本身。
14. 不允许把 850 工坊升级成 900。
15. 不允许工坊制造星词缀。
16. Boss 专属与规则突破件不可萃取、不可刻印。
17. 工坊不得复制 Boss 来源身份，也不得制造终局闭环。
18. 掉落结算必须使用四层决策展示：L1_interrupt / L2_attention / L3_folded / L4_silent。
19. protected-source 物品最低 verdict 为 situational，最低展示层为 L2_attention。
20. 不引入装备套装系统。
21. CLI 必须帮助玩家自动筛垃圾，而不是要求玩家手工逐件审阅所有掉落。
