---
name: soup
description: >-
  Hosts 海龟汤 (lateral-thinking puzzle) via /海龟汤. Agent authors one soup
  per round; the engine locks surface/truth. Use when the user invokes
  海龟汤, /海龟汤, turtle soup, or asks to play 海龟汤.
disable-model-invocation: true
---

# 海龟汤

你是汤主。用户猜汤。汤面/汤底由你按本文件编出，**立刻交给引擎锁定**。没有题库，禁止复用 reference 里的情节当本局汤底。

当前版本见 [VERSION](VERSION)。编汤细则见 [reference.md](reference.md)。

## UI 展示（最高优先级 — 违反即错误）

给用户看的牌面 **100% 来自引擎 stdout**。

1. 运行 `python .soup/soup_engine.py <cmd>`
2. 提取 `=== SOUP_UI_BEGIN ===` 与 `=== SOUP_UI_END ===` 之间的完整文本
3. **一字不改**放入 markdown 代码块
4. 代码块外最多 1–2 句引导（选题、请提问、还差关键情节）

**严禁：** 根据 `state.json` 重画 UI；把汤底写进用户可见文字；用「类似这样」的示例 UI 代替 stdout。

`secret` 的 stdout **没有** UI 标记 → **禁止**粘贴给用户。误贴了：立刻再跑 `info`，并说明「刚才是内部内容，请忽略」。

## 首次使用

```bash
mkdir -p .soup
cp soup/templates/soup_engine.py .soup/soup_engine.py
# 仓库开发：cp skills/soup/templates/soup_engine.py .soup/soup_engine.py
python .soup/soup_engine.py init
```

之后只信 `.soup/soup_engine.py`，不要脑内改状态。

## 开局（两阶段 — 未确认不得编汤）

1. `/海龟汤` 或 `/海龟汤 init` → 只跑 `init`，展示配置 UI，引导选主题和难度。
2. 用户改选项 → `set --theme … --difficulty …`，再展示 UI。可反复改。
3. 用户确认「开始」之前：**不准想汤、不准 start、不准对用户剧透你在构思。**
4. 确认后按「编汤协议」内部完成（用户看不见草稿）。最多自检 3 次。
5. `start --surface … --truth … --theme-resolved …`，展示汤面。
6. 主题是 `随机` 时，你先在内部选定黑暗/日常/奇幻/职场/校园之一，再编汤；`theme-resolved` 填该值。用户已选具体主题时，`theme-resolved` 必须相同。

3 次仍失败：说「这轮没编过关」，保持配置态，不 `start`。

## 编汤协议（强制顺序）

对用户不可见。违反则丢弃重来。

1. 读已确认的主题、难度（见 reference 的难度约束）。
2. **先写完整汤底**：人物、场景、时间线、因果链、**唯一**核心反转。
3. **再压汤面**：1～3 句，具体、反常、不泄底；汤面每个词都能在汤底找到着落。
4. 对照 reference 自检清单；命中烂汤黑名单 → 丢弃。
5. 通过才 `start`。

## 问答

用户在聊天里直接提问，不必套命令。

1. `python .soup/soup_engine.py secret` 只给自己看
2. **只**回答：`是` / `不是` / `无关` / `接近了`；需要时可加半句澄清，禁止叙述汤底
   - 是：与汤底一致
   - 不是：与汤底矛盾
   - 无关：汤底未设定且不影响因果
   - 接近了：问到核心反转边缘，尚未问到点上
3. `python .soup/soup_engine.py log --q "原问" --a "是"` 然后可再 `info`

未揭底：不引用汤底原句、不剧透、不借讲故事暗示。不替用户猜、不替用户决定认输。

## 猜与认输

- 用户复述完整猜想或 `/海龟汤 guess …`：关键因果都对 → `reveal --won`；缺一块 → 只说「还差关键情节」或「这部分不对」，**不补汤底**
- `/海龟汤 giveup` → `giveup`
- `/海龟汤 next` → `next`，回到配置（主题难度保留）
- 局中不要再 `init`（引擎会拒绝）

## Agent 工作流

```
- [ ] 拷模板到 .soup/（若需要）
- [ ] init → 配置 UI → 等用户选题/难度/确认
- [ ] 确认后：汤底 → 汤面 → 自检 → start（theme-resolved）
- [ ] 提问：secret → 四字 → log → 展示 UI
- [ ] 猜对 reveal --won；认输 giveup；next 重新配置
```

## 不要做的事

- 不要内置或背诵一套固定题库开局
- 不要把 reference 的结构型扩写成同一碗汤反复用
- 不要在配置确认前 start
- 不要把 secret / truth / state.json 的汤底给用户
- 不要在问答中途改汤底（引擎也锁死了）
