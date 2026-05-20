# 速度系统（Speed System）

《深渊回响》正式采用 **ATB 半实时自动战斗**，不使用固定回合顺序。

## 三种速度

| 属性 | 英文 | 作用 |
|---|---|---|
| 行动速度 | SPD / speed | 决定行动条增长、先手和行动频率 |
| 攻击速度 | ASP / attackSpeed | 决定普攻间隔 |
| 施法速度 | CSP / castSpeed | 决定主动技能施法时间 |

## ATB规则

- 每秒 10 Tick。
- 每个单位拥有 0~100 的 ATB。
- 每 Tick 增长：`ATB += speed * 0.1`。
- ATB 达到 100 后行动。
- 启用溢出机制，例如 ATB=118 时行动后保留 18。

## 普攻频率

```text
AttackInterval = 1 / attackSpeed
```

例如 attackSpeed=2.0，表示每 0.5 秒可进行一次普攻。

## 施法时间

```text
FinalCastTime = BaseCastTime / castSpeed
```

施法速度只影响主动技能释放时间，不影响冷却。

## 控制联动

- 冻结：ATB停止增长，施法和普攻计时暂停。
- 眩晕：ATB可以增长，但无法行动。
- 减速：降低SPD。
- 感电：默认降低ASP，部分威能可改造成额外雷击。

## 设计结论

速度系统让高速触发流、先手控制流、慢速核爆流都可以成立。它是自动战斗爽感的核心。
