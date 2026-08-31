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
npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y
```

## 使用

在 Cursor 聊天中：

```
/NLHE init
/NLHE init --start --fresh --players 6 --stack 1000 --sb 5 --bb 10 --human 0
```

从本仓库克隆后，在**仓库根目录**拷到项目运行态：

```bash
mkdir -p .nlhe
cp skills/nlhe/templates/nlhe_engine.py .nlhe/
cp skills/nlhe/templates/nlhe_coach.py .nlhe/
cp -R skills/nlhe/charts .nlhe/
python .nlhe/nlhe_engine.py init
python .nlhe/nlhe_engine.py init --start --fresh --players 6 --stack 1000 --sb 5 --bb 10 --human 0
```

经 skills.sh 安装后，skill 在 `~/.cursor/skills/nlhe/`，Agent 按 `SKILL.md` 从 `nlhe/templates/` 同步到项目 `.nlhe/`。

## 更新

Skill 包与运行态引擎分两层更新：

```bash
# 1. 检查 / 更新 skill 包（GitHub）
npx skills check nlhe -g
npx skills update nlhe -g -y

# 2. 同步到项目 .nlhe/（不重置筹码）
python .nlhe/nlhe_engine.py upgrade
```

## 开发

```bash
python3 tests/test_coach.py -v
```

（在 `skills/nlhe/` 目录下执行，或从仓库根：`python3 skills/nlhe/tests/test_coach.py -v`）

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
