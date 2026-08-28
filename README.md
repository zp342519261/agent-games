# NLHE — GTO 教学桌

6-max 德州扑克（NLHE）模拟 + 内置 GTO 牌谱（charts）与教练条。适用于 Cursor 等 Agent：脚本驱动 RNG、JSON 状态持久化、轮到 Hero 时展示底池赔率 / Equity 粗估 / 谱内频率。

当前版本：**1.5.2**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 功能

- 脚本洗牌发牌，禁止 Agent 脑内抽牌
- GTO 教练条（`awaiting_human`）：Pot odds、Equity≈（MC）、谱命中频率；`NO_CHART` 不伪造 GTO
- P0 谱包：`preflop-6max-100bb`（BTN RFI、BB vs BTN open 等）
- `review` / `charts` 复盘与列谱
- `init` 两阶段：先看配置建议，`--start` 再开局

## 安装（skills.sh / Cursor）

```bash
npx skills add zp342519261/nlhe -g -a cursor -s nlhe -y
```

[![skills.sh](https://skills.sh/b/zp342519261/nlhe)](https://skills.sh/b/zp342519261/nlhe)

## 使用

在 Cursor 聊天中：

```
/NLHE init
/NLHE init --start --fresh --players 6 --stack 1000 --sb 5 --bb 10 --human 0
```

或在工作区项目内：

```bash
mkdir -p .nlhe
cp nlhe/templates/nlhe_engine.py .nlhe/
cp nlhe/templates/nlhe_coach.py .nlhe/
cp -R nlhe/charts .nlhe/
python .nlhe/nlhe_engine.py init
python .nlhe/nlhe_engine.py init --start --fresh --players 6 --stack 1000 --sb 5 --bb 10 --human 0
```

## 更新

Skill 包与运行态引擎分两层更新：

```bash
# 1. 检查 / 更新 skill 包（GitHub）
npx skills check nlhe -g
npx skills update nlhe -g -y

# 2. 同步到项目 .nlhe/（不重置筹码）
python .nlhe/nlhe_engine.py upgrade
```

## 仓库结构

```
nlhe/
├── SKILL.md          # Agent 指令（必需）
├── reference.md      # 规则与 GTO 说明
├── VERSION / CHANGELOG.md
├── templates/
│   ├── nlhe_engine.py
│   └── nlhe_coach.py
├── charts/           # GTO teaching packs
└── tests/
```

## 开发

```bash
cd nlhe
python3 tests/test_coach.py -v
```

## License

MIT — 见 [LICENSE](LICENSE)
