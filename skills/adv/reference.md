# 文字冒险 · 主持参考

给 Agent 用。每局现编剧情图，不要反复复用同一张图。

## scenario-json 结构

```json
{
  "start": "intro",
  "nodes": {
    "intro": {
      "text": "你站在锈迹斑斑的铁门前，风里有潮气。",
      "choices": [
        {"label": "推门进去", "to": "hall", "gain": ["旧钥匙"]},
        {"label": "沿墙离开", "to": "leave"}
      ]
    },
    "hall": {
      "text": "大厅空无一人，壁炉里还有余温。",
      "choices": [
        {"label": "用钥匙开侧门", "to": "secret", "need": ["旧钥匙"]},
        {"label": "原路返回", "to": "leave"}
      ]
    },
    "secret": {
      "text": "侧门后是一封未寄出的信。你决定带走真相。",
      "ending": "揭开往事",
      "outcome": "good"
    },
    "leave": {
      "text": "你转身走进夜色，门在身后关上。",
      "ending": "悄然离去",
      "outcome": "neutral"
    }
  }
}
```

字段：

- `need` / `gain` / `lose`：字符串道具名
- `set`：`{"旗名": true/false}` 写入旗帜
- `need_flags`：选项可见条件
- 结局节点：必须有 `ending` + `outcome`（`good`/`bad`/`neutral`），且无 `choices`

## 难度建议

- 简单：4～6 节点，1～2 结局，少道具门
- 普通：6～12 节点，至少 2 结局，1～2 件关键道具
- 困难：更多死路与旗帜门，好结局需特定顺序

## 烂图（丢弃）

- 无结局、断链（`to` 不存在）、开局即无选项且非结局
- 选项剧透结局名、色情暴力不当内容
- 做成数值修仙或纯问答汤

## 演绎

- 代码块外只用 1～2 句氛围，不替玩家做选择
- 缺道具导致选项消失时，可含蓄提示，不点破未达节点
