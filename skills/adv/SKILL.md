---
name: adv
description: >-
  Hosts 文字冒险 via /冒险. Engine locks story graph, inventory, flags,
  and endings. Use when the user invokes 冒险, /冒险, text adventure, or
  asks to play 文字冒险.
disable-model-invocation: true
---

# 文字冒险

你是叙事主持。分支、道具、旗帜与结局由引擎锁定。你编剧情图并演绎场景，禁止脑内改节点或结局。

当前版本见 [VERSION](VERSION)。编图细则见 [reference.md](reference.md)。

## UI 展示（最高优先级 — 违反即错误）

给用户看的牌面 **100% 来自引擎 stdout**。

1. 运行 `python .adv/adv_engine.py <cmd>`
2. 提取 `=== ADV_UI_BEGIN ===` 与 `=== ADV_UI_END ===` 之间的完整文本
3. **一字不改**放入 markdown 代码块
4. 代码块外最多 1–2 句引导（确认开局、请选 1/2/3）

**严禁：** 根据 `state.json` 重画 UI；把 `secret` 剧情图贴给用户；口头改行囊或跳转节点。

`secret` 的 stdout **没有** UI 标记 → **禁止**整段粘贴给用户。误贴了：立刻再跑 `info`，并说明「刚才是内部内容，请忽略」。

## 首次使用

```bash
mkdir -p .adv
cp adv/templates/adv_engine.py .adv/adv_engine.py
# 仓库开发：cp skills/adv/templates/adv_engine.py .adv/adv_engine.py
python .adv/adv_engine.py init
```

之后只信 `.adv/adv_engine.py`。

## 开局（两阶段）

1. `/冒险` 或 `/冒险 init` → 只跑 `init`，展示配置 UI。
2. 用户可改类型/难度：`set --genre … --difficulty …`。
3. 用户确认「开始」之前：**不准 start、不准剧透你在构思的结局。**
4. 确认后按 reference 编完整剧情图（含至少 1 个结局节点），再：
   `start --title … --scenario-json '…' --genre-resolved …`
5. 展示场景 UI；用户选数字 → `choose --n`。

主题是 `随机` 时，你先在内部选定奇幻/科幻/悬疑/日常之一；`genre-resolved` 填该值。

## 主持

- 用户说 1/2/3 或「选二」→ `choose --n`
- 选项因缺道具不可见时，引擎会隐藏；可暗示「似乎还缺什么」但不要剧透未达节点
- `/冒险 giveup` → 放弃；`/冒险 next` → 回配置
- 需要自检图结构时用 `secret`（仅自己看）

## Agent 工作流

```
- [ ] 拷模板到 .adv/
- [ ] init → 配置 → 等确认
- [ ] 编图 → start（genre-resolved）
- [ ] choose 推进 → 抵达 ending 由引擎结算
- [ ] next 再来一局
```

## 不要做的事

- 不要脑内跳转节点或加减道具
- 不要把 secret / 未抵达节点正文给用户
- 不要在局中改 scenario（引擎已锁死）
- 不要做成修仙数值肉鸽或海龟汤问答换皮
