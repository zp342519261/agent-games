---
name: nlhe
description: >-
  Simulates No-Limit Texas Hold'em via /NLHE commands with script-backed RNG
  and JSON state. Use when the user invokes nlhe, /NLHE, 德州扑克, Hold'em,
  or asks to play/simulate a poker hand at the table.
disable-model-invocation: true
---

# NLHE — GTO 教学桌

在脚本驱动的 NLHE 模拟之上，内置 **GTO 牌谱（charts）** 与 **教练条**：轮到 Hero 时展示底池赔率、Equity 粗估与谱内频率；一手结束后可用 `review` 对照你的行动。Agent 负责跑 CLI，**原样展示**引擎 stdout，并在轮到用户时等待输入。

当前 skill 版本见 [VERSION](VERSION)；变更见 [CHANGELOG.md](CHANGELOG.md)。

## UI 展示（最高优先级 — 违反即错误）

牌桌 UI **100% 由引擎硬编码**（`render()`），Agent **不得**自行绘制、改写或摘要。

### 必须这样做

1. 运行 `python .nlhe/nlhe_engine.py init|info|act|next …`
2. 从 stdout 提取 **`=== NLHE_UI_BEGIN ===` 与 `=== NLHE_UI_END ===` 之间**的完整文本
3. **一字不改**放入 markdown 代码块展示给用户（保留 `+` `│` `┌` 等所有字符与换行）
4. 代码块外最多加 **1–2 句**说明（如「轮到你，请输入 fold/call…」），**禁止**在代码块内增删改任何 UI 行

### 严禁这样做

- 读 `state.json` 后「重画」牌桌、座位、手牌、底池
- 把 ASCII 桌面改成 markdown 表格 / 列表 / 自造布局
- 省略「上一轮 / 这一轮」操作面板、Styles、观战回放、Actions 提示
- 用「类似这样」的示例 UI 或 reference 里的旧版样例代替真实 stdout
- 只写 prose 摘要（「你在 BTN，手牌 AK，底池 120…」）而不贴引擎输出

**若未跑脚本就展示 UI = 严重违规。** 若 stdout 无 UI 标记，先 `upgrade` 再重跑。

## 硬性规则

1. **禁止**脑内抽牌/洗牌/改筹码；只信引擎脚本。
2. 首次使用：复制模板到 `.nlhe/`，版本校验后 `upgrade`（含 `nlhe_coach.py` 与 `charts/`）。
3. `state.json` 仅供调试；**展示给用户的 UI 不来自 state 解析**。
4. 轮到 human 时：**等待用户输入**，不要替用户行动。
5. `hand_over` 后默认 `/NLHE next` 续桌。
6. 弃牌后引擎自动观战至结束；展示 stdout 中的完整 UI + 回放（仍须原样代码块）。
7. **GTO 频率只来自引擎 UI**：教练条 `GTO:` 行或 `review` 中的谱数字。命中时原样解释；`NO_CHART` 时说明原因，**禁止**编造 raise/call/fold 频率或「大概应该」的 GTO 建议。

## 版本机制

每次会话首次 NLHE 指令，**先检查 skills.sh 安装包，再同步运行态引擎**：

```bash
# 1. Skill 包（~/.cursor/skills/nlhe/）— 来自 npx skills 安装时
npx skills check nlhe -g
# 或: python .nlhe/nlhe_engine.py skills-check   # exit 2 = 有更新，需提醒用户

# 若有更新，征得用户同意后：
npx skills update nlhe -g -y

# 2. 运行态（.nlhe/）— 从 skill 模板同步引擎/coach/charts
mkdir -p .nlhe
cp nlhe/templates/nlhe_engine.py .nlhe/nlhe_engine.py
cp nlhe/templates/nlhe_coach.py .nlhe/nlhe_coach.py
cp -R nlhe/charts .nlhe/charts
python .nlhe/nlhe_engine.py version || true
python .nlhe/nlhe_engine.py upgrade
```

**两层更新不可混用**：只跑 `upgrade` 不会拉 GitHub 上的 skill 包；只跑 `npx skills update` 不会更新项目 `.nlhe/` 里的引擎。

`skills-check` / `npx skills check nlhe -g` 发现更新时，Agent **必须向用户说明**并给出 `npx skills update nlhe -g -y`，用户同意后再执行，然后跑 `upgrade`。

## 用户指令

| 指令 | 作用 |
|------|------|
| `/NLHE init` | 开桌配置建议（**不发牌**）；确认后加 `--start` 才真正开局 |
| `/NLHE next` | 下一手（保留筹码） |
| `/NLHE info` | 查看牌局（`awaiting_human` 时 UI 含 **GTO 教练条**） |
| `/NLHE review` | 本手 Hero 决策 vs 谱对照（`--god` 额外显示 Hero 底牌） |
| `/NLHE charts` | 列出已装 chart pack、来源与假设 |
| `/NLHE skills-check` | 检查 `npx skills` 安装包是否有更新（有更新时 exit 2） |
| `/NLHE version` / `/NLHE upgrade` | 运行态引擎版本；upgrade 同步 coach + charts |
| `/NLHE help` | 帮助 |
| `fold` / `check` / `call` / `raise <n>` / `allin` | 行动 |

```bash
python .nlhe/nlhe_engine.py init
python .nlhe/nlhe_engine.py init --start --fresh --players 6 --stack 1000 --sb 5 --bb 10 --human 0
python .nlhe/nlhe_engine.py act call
python .nlhe/nlhe_engine.py info
python .nlhe/nlhe_engine.py review
python .nlhe/nlhe_engine.py charts
python .nlhe/nlhe_engine.py next
```

## Agent 工作流

```
- [ ] skills-check 或 npx skills check nlhe -g；若 UPDATE_AVAILABLE → 提醒用户并待确认后 npx skills update nlhe -g -y
- [ ] version / upgrade（含 coach + charts）
- [ ] init（无 --start）：展示配置建议，等用户确认参数
- [ ] init --start：确认后开局，提取 NLHE_UI_BEGIN…END → 原样代码块
- [ ] awaiting_human：代码块外一句提示等待输入；可简要说明 HIT/NO_CHART，不改频率数字
- [ ] hand_over：可选 /NLHE review；默认提示 /NLHE next
```

细则见 [reference.md](reference.md)（**reference 无 UI 样例，不可用来画桌**）。

## 不要做的事

- 不要手写 `state.json` 修正牌局（除非用户明确要求调试）
- 不要跳过引擎宣布发牌/结果
- 不要替用户行动
- 不要用旧版 ╔══ 列表式 UI（已废弃，以引擎 stdout 为准）
- 不要在 `NO_CHART` 或无 `GTO:` 行时补充 GTO 频率或「标准打法」
