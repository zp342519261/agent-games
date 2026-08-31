# NLHE Changelog

## 1.5.2
- **仓库**：迁入合集 `zp342519261/agent-games`（路径 `skills/nlhe/`）；安装改为 `npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y`
- **skills.sh 更新提醒**：新增 `skills-check` 命令；`init` 配置页展示 `npx skills check/update` 指引；SKILL 工作流会话首检 skill 包

## 1.5.1
- **init 两阶段**：默认只展示开桌配置建议（含 GTO 教学预设、已有 state 摘要）；加 `--start` 才发牌开局

## 1.5.0
- **GTO 教学桌**：`awaiting_human` 时在 UI 内展示教练条（底池赔率 + Equity≈ + 谱频率/建议）
- **nlhe_coach**：手牌规范化、SpotKey、chart 查谱、MC equity、coach/review/charts 文本
- **内置 charts**：`preflop-6max-100bb`（BTN RFI、BB vs BTN open 等 P0 spot）
- **upgrade**：同步 `nlhe_coach.py` 与 `charts/` 到工作区 `.nlhe/`
- **CLI**：`review`（`--god`）、`charts`；`coach_log` 记录 Hero 决策供复盘
- **纪律**：NO_CHART 时不输出伪造 GTO 频率

## 1.4.5
- 牌型预览：进行中显示 Hero 当前最高牌型（起手/翻后）
- 摊牌后展示所有未弃牌者最高牌型（含 ★赢家）

## 1.4.4
- stdout `NLHE_UI_BEGIN/END`；禁止 Agent 重绘 UI

## 1.4.3
- 「上一轮 / 这一轮」双操作面板

## 1.4.2
- 修复 AI 翻后全员 check

## 1.4.1
- 方案 A 椭圆牌桌 UI

## 1.4.0
- 弃牌观战回放

## 1.3.0
- AI 随机桌型

## 1.2.0
- version / upgrade

## 1.1.0
- `/NLHE next`

## 1.0.0
- 初版
