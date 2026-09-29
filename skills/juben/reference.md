# 剧本杀 · 主持参考

给 Agent 用。每局新编角色本与线索，不要反复同一真凶故事。

## roles-json

```json
[
  {
    "id": "host",
    "name": "房东",
    "public": "别墅主人，声称当晚在书房写作。",
    "private": "……（动机、当晚行动、是否真凶等，仅自己可见）……",
    "is_murderer": false
  },
  {
    "id": "guest",
    "name": "远房亲戚",
    "public": "刚回来争遗产。",
    "private": "……你才是下手的人……",
    "is_murderer": true
  },
  {
    "id": "maid",
    "name": "女佣",
    "public": "负责二楼打扫。",
    "private": "……听到争执但不敢说……",
    "is_murderer": false
  }
]
```

必须恰好 1 个 `is_murderer: true`。玩家 `user-role` 用角色 `id`。

## clues-json

```json
[
  {"id": "p1", "text": "花瓶碎在走廊，缺口朝向楼梯。", "holder": null},
  {"id": "p2", "text": "书房台历停在案发日。", "holder": null},
  {"id": "u1", "text": "你袖口有未洗掉的墨渍。", "holder": "guest"},
  {"id": "m1", "text": "你捡到一把不属于自己的钥匙。", "holder": "maid"}
]
```

- `holder: null`：进入公开线索池，搜证阶段 `draw` 抽取
- `holder: 角色id`：该角色私有线索，出现在 `myrole` / `npcrole`

## 阶段节奏

- intro：每人 1～3 句，不直指凶手
- search：建议 draw 至公开线索足够（或池空）再讨论
- discuss：可追问矛盾，仍不剧透
- vote：你为 NPC 投票时按人设（平民投可疑者；真凶可搅局）

## 烂本（丢弃）

- 零线索、多真凶、玩家角色没有任何可说的私密信息
- 公开案情直接写明凶手
- 与单人探案完全同构（无角色本/无投票）
