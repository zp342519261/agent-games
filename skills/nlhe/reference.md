# NLHE 参考

Agent 仅在需要规则细节、状态字段或 UI 解读时读本文件。

## 玩法约定

- **NLHE**：无限注德州，德州标准五张公共牌 + 两人底牌。
- 街道：`preflop` → `flop`（3）→ `turn`（1）→ `river`（1）→ `showdown`。
- 位置：按钮 `button`；盲注座位按人数常规：2 人时 BTN=SB，另一人 BB。
- 下注：`raise <n>` 的 `n` 为**加注后本街累计投入**（该座位本轮 `bet` 目标值），不是「再追加多少」；引擎会校验最小加注。

## 牌力从高到低

1. 皇家同花顺  
2. 同花顺  
3. 四条  
4. 葫芦  
5. 同花  
6. 顺子（A-2-3-4-5 为最小顺，A 作 1）  
7. 三条  
8. 两对  
9. 一对  
10. 高牌  

摊牌时每人用 7 张（2 手牌 + 5 公共）取最佳 5 张比较。

## 状态文件 `.nlhe/state.json`（摘要）

| 字段 | 含义 |
|------|------|
| `hand_id` | 手牌序号 |
| `street` | preflop/flop/turn/river/showdown/hand_over |
| `pot` | 主池（简化：单池；多人 all-in 由引擎按投入切边池） |
| `board` | 公共牌列表，如 `["Ah","Kd","7c"]` |
| `button` | 按钮座位 |
| `sb` / `bb` | 盲注 |
| `to_act` | 当前应行动座位；`null` 表示不等待 |
| `status` | `awaiting_human` / `awaiting_bot` / `hand_over` / `idle` |
| `engine_version` | 写入状态时的引擎 semver |
| `coach_log[]` | Hero 各决策点快照（供 `review`；含 spot、freqs、hero_action） |
| `session` | 桌级配置：`players/sb/bb/human`（供 `next` 延续） |
| `players[]` | `id, name, stack, bet, hole, folded, all_in, is_human, style, style_label` |

## AI 桌型（bot style）

开桌时为每个非 human 座位加权随机一种风格（`next` 保留）：

| id | 中文 | 倾向 |
|----|------|------|
| `tag` | 紧凶 | 牌紧、常加注 |
| `lag` | 松凶 | 牌松、常加压 |
| `nit` | 超紧 | 极少进池 |
| `rock` | 紧弱 | 紧但少主动 |
| `station` | 跟注站 | 爱跟、很少加注 |
| `maniac` | 疯子 | 极松极凶、爱诈唬 |
| `fish` | 弱鱼 | 进池多、决策差、爱跟 |

决策综合：`style` 参数 + 起手牌粗评 + 翻后 `best_hand` 档位。

## 观战与回放

- 人类 `fold` 后：`watching=true`，引擎继续推进至 `hand_over`。
- `replay[]` 记录街道发牌与每步行动；结束时打印「观战回放」。
- 观战结束：`show_holes=true`，亮出未弃牌对手手牌。

## 牌桌 UI（方案 A）

**唯一来源**：引擎 stdout 的 `=== NLHE_UI_BEGIN ===` … `=== NLHE_UI_END ===` 区间。Agent 必须原样代码块展示，**禁止**根据 state 或下文自行重绘。

- 椭圆毡面：Hero 固定南位，其余顺时针环绕。
- 中央毡面显示公共牌与 POT。
- 牌桌下方并排 **上一轮 / 这一轮** 操作面板。
- **牌型预览**：进行中显示 You 当前最高牌型；摊牌/观战结束显示全员牌型。
- **GTO 教练条**（仅 `status=awaiting_human`）：附在 UI 标记内、牌型预览之后；见下文「教练条字段」。
- 标记：`D`=按钮，`<`=待行动，`X`=已弃，`AI`=全下。

## 版本与升级

### 两层更新

| 层 | 位置 | 检查 | 更新 |
|----|------|------|------|
| **Skill 包** | `~/.cursor/skills/nlhe/` | `npx skills check nlhe -g` 或 `/NLHE skills-check` | `npx skills update nlhe -g -y` |
| **运行态** | 项目 `.nlhe/` | `python .nlhe/nlhe_engine.py version` | `python .nlhe/nlhe_engine.py upgrade` |

通过 [skills.sh](https://www.skills.sh/) 安装时，lock 文件在 `~/.agents/.skill-lock.json`。`skills-check` 发现 GitHub 上有新 commit 时 exit **2**，Agent 应提醒用户执行 `npx skills update`，再 `upgrade`。

- 权威版本：`~/.cursor/skills/nlhe/VERSION`（与模板 `ENGINE_VERSION` 一致）。
- 工作区运行态：`.nlhe/nlhe_engine.py`、`.nlhe/nlhe_coach.py`、`.nlhe/charts/`、`state.json`。
- `python .nlhe/nlhe_engine.py version`：对比本地引擎与 skill；落后时 exit code **2** 且 `status: OUTDATED`。
- `upgrade`：从 skill 同步 `nlhe_engine.py`、`nlhe_coach.py` 与 `charts/`（整目录覆盖），更新 `.nlhe/VERSION` 与 `state.engine_version`，**不重置**筹码与牌局。
- 旧引擎没有 `version` 子命令时：Agent 直接 `cp` 模板与 charts 后再校验。

## 连续多手

- `/NLHE next`：要求 `status=hand_over`；保留筹码与 `session`，按钮前移到下一位仍有筹码者。
- 破产座位 `stack=0`：不再发牌；盲注跳过无筹码座位。
- 有效人数 < 2：引擎报错，需 `/NLHE init --start --fresh` 重开。

## 开桌（init 两阶段）

1. **`/NLHE init`**（无 `--start`）：只输出配置建议，**不发牌**。包含：
   - GTO 教学推荐（6 人 / 1000 筹码 / 5-10 盲 / 100bb，匹配 `preflop-6max-100bb`）
   - 当前 CLI 参数与有效深度
   - 已有 `state.json` 摘要（若存在）
   - 带 `--start` 的确认开桌命令示例
2. **`/NLHE init --start`**：按参数真正开局并发第一手牌。常用：`--start --fresh --players 6 --stack 1000 --sb 5 --bb 10 --human 0`

Agent 流程：先跑 `init` 展示建议 → 等用户确认或调整参数 → 再跑 `init --start …` 进入牌桌 UI。


牌面编码：`[rank][suit]`，rank=`2-9,T,J,Q,K,A`，suit=`c,d,h,s`（♣♦♥♠）。

## 合法行动（概念）

- `fold`：弃牌  
- `check`：无人加注且本街已齐时可过牌  
- `call`：跟注到当前最高 `bet`（不够则 all-in）  
- `raise <n>`：加注到累计 `n`（须 ≥ 最低加注）  
- `allin`：全下  

具体合法性以 `act` 的引擎校验为准。

## GTO 教学（P0）

### SpotKey（引擎生成，Agent 不填）

`build_spot_key(state)` 从当前局面推导查谱键；不符或 P0 未覆盖则带 `miss_reason` → UI 显示 `NO_CHART`。

| 字段 | 说明 |
|------|------|
| `game` | 固定 `NLHE` |
| `eff_bb` | 有效筹码档（P0 仅 **100bb**，±15bb 内对齐） |
| `street` | P0 仅 `preflop` 查谱 |
| `hero_pos` | 6-max：BTN / SB / BB / UTG / HJ / CO（相对 button 顺时针） |
| `vs_pos` | `line=vs_open` 时为开池者位置；RFI 时为 `null` |
| `line` | P0：`rfi`（无人自愿加注）或 `vs_open`（面对单次 open） |
| `board_class` | 翻后板面分类；preflop 为 `null`（P2+） |
| `hero_hand` | 规范化 combo：`AA` / `AKs` / `T9o` 等 |
| `spot_id` | 文件名键，如 `6max_100bb_btn_rfi`、`6max_100bb_bb_vs_btn_open` |

### NO_CHART 原因

| reason | 含义 |
|--------|------|
| `players_not_6` | 非 6-max |
| `depth_not_in_tier` | 有效深度不在 P0 档位（100bb±15） |
| `street_not_preflop_p0` | 翻后（P0 无翻后包） |
| `line_unsupported` | 3bet+ 等多 raise 线（P1） |
| `incomplete_key` | spot_id 或 hero_hand 缺失 |
| `spot_file_missing` | manifest 无对应 spot JSON |
| `combo_not_in_chart` | spot 存在但该 combo 未收录 |
| `invalid_freqs` | spot JSON 频率和 ≠ 1.0（±0.01） |

未命中时 UI **不得**出现 `GTO: raise/call/fold x%`；Agent 只解释 `NO_CHART` 与原因，不补频率。

### Chart pack 格式（brief）

`charts/manifest.json` 列出 pack；每包含 `meta.json` + `spots/*.json`。

Spot 文件示例：

```json
{
  "id": "6max_100bb_btn_rfi",
  "meta_ref": "preflop-6max-100bb",
  "actions": ["fold", "raise"],
  "combos": {
    "AKs": { "raise": 1.0 },
    "J9o": { "fold": 0.55, "raise": 0.45 }
  }
}
```

- 同一 combo 下各行动频率之和应为 **1.0**（加载时校验）。
- `meta.json` 必填 `source`（如 `teaching-pack`）、`assumptions`（6-max、100bb、open 尺寸等）、`version`。

P0 内置包 `preflop-6max-100bb`：完整教学 combo 以 **BTN RFI**、**BB vs BTN open** 为主；其他位置 RFI / vs_open 可能 `spot_file_missing` 或 `combo_not_in_chart`。

### 教练条字段

仅在 `awaiting_human` 时出现在 `NLHE_UI_BEGIN…END` 内：

| 行 | 含义 |
|----|------|
| `Pot odds:` | 跟注所需胜率（`to_call / (pot + to_call)`）；无需跟注时为「无需跟注」 |
| `Equity≈…%（MC，非 GTO）` | 蒙特卡洛粗估对未弃牌对手；**不是**求解器 GTO equity |
| `Chart: …` | 命中：`pack / spot_id · combo [source]`；未命中：`NO_CHART（原因: …）` |
| `GTO:` | 仅 HIT 时：谱内各行动频率 |
| `建议:` | HIT：最高频行动（谱命中）；MISS：「无谱，不提供 GTO 行动」 |

### `review` / `charts`

- **`python .nlhe/nlhe_engine.py review`**：读本手 `coach_log`，逐条对比 Hero 实际行动与谱频率；行动非最高频 GTO 时标 **【谱外】**。无记录时提示「暂无 Hero 决策记录」。输出包在 `NLHE_UI_BEGIN…END`。
- **`review --god`**：额外一行 Hero 底牌（不揭示对手盖牌）。
- **`python .nlhe/nlhe_engine.py charts`**：列出 manifest 中已装 pack、`source`、`assumptions`、`notes`。
