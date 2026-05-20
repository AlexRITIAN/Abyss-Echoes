# 深渊回响 Abyss Echoes

聊天窗口中的刷装型自动战斗 RPG。

核心玩法：

- 5 名英雄上阵
- 前排 / 后排站位
- 战斗完全自动进行
- 每名英雄拥有：普攻、1 个主动技能、1 个被动技能
- 英雄定位：坦克、物理近战、物理远程、魔法远程、辅助
- 装备系统借鉴暗黑式：品质、词条、威能、暗金、神话、淬炼、精铸、腐化
- 终局玩法：Boss Farm、无限深渊、赛季机制

推荐运行方式：

1. 读取 `data/game-rules.json`
2. 读取 `data/heroes.json`
3. 读取 `data/skills.json`
4. 读取 `data/equipment-system.json`
5. 读取 `save/player-save.initial.json`
6. 根据玩家输入进行战斗、掉落、换装、推进

聊天命令建议：

```text
开始游戏
查看阵容
查看背包
进入地图 腐化墓穴
挑战Boss 雷鸣主教
自动装备 雷霆术士
保存进度
```



## 启动方式

现在支持直接使用 `abyss` 启动游戏（无需手动输入 `python3 game_cli.py`）。

```bash
# 在仓库根目录
./abyss

# 可选：加入 PATH 后可在任意目录直接运行 abyss
ln -sf "$(pwd)/abyss" ~/.local/bin/abyss
```

## v1.1 更新

新增速度系统：`docs/speed-system.md` 与 `data/speed-system.json`。战斗模式升级为 ATB 半实时自动战斗。
