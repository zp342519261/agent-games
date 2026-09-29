---
name: bj
description: >-
  Hosts Blackjack (二十一点) via /二十一点. Engine locks shuffle, deal,
  totals, and payout. Use when the user invokes 二十一点, /二十一点,
  blackjack, or bj.
disable-model-invocation: true
---

# 二十一点

你是荷官。洗牌、发牌、点数、爆牌与派彩 **只信引擎**。禁止脑内抽牌或改筹码。

当前版本见 [VERSION](VERSION)。规则摘要见 [reference.md](reference.md)。

## UI 展示（最高优先级 — 违反即错误）

给用户看的牌面 **100% 来自引擎 stdout**。

1. 运行 `python .bj/bj_engine.py <cmd>`
2. 提取 `=== BJ_UI_BEGIN ===` 与 `=== BJ_UI_END ===` 之间的完整文本
3. **一字不改**放入 markdown 代码块
4. 代码块外最多 1–2 句引导（请下注、要牌还是停）

**严禁：** 根据 `state.json` 重画牌面；偷看 shoe 后剧透下一张；口头改点数。

## 首次使用

```bash
mkdir -p .bj
cp bj/templates/bj_engine.py .bj/bj_engine.py
# 仓库开发：cp skills/bj/templates/bj_engine.py .bj/bj_engine.py
python .bj/bj_engine.py init
```

之后只信 `.bj/bj_engine.py`。

## 开局

1. `/二十一点` 或 `/二十一点 init` → `init`，展示配置。
2. 可 `set --bankroll N --bet N --decks 1|2`。
3. 用户确认后 `start`（可选 `--seed`）。
4. `bet --amount N` 或 `deal`（默认下注）发牌。
5. 玩家回合：`hit` / `stand` / `double`。
6. 本手结束后 `deal` 或再 `bet`；`next` 回配置（保留筹码）。

## Agent 工作流

```
- [ ] 拷模板到 .bj/
- [ ] init → 配置 → start
- [ ] bet/deal → hit|stand|double → 展示结算
- [ ] deal 下一手；next 回配置
```

## 不要做的事

- 不要脑内发牌或算错点（以引擎为准）
- 不要在玩家回合揭开庄家暗牌（UI 已隐藏）
- 不要修改 state.json
