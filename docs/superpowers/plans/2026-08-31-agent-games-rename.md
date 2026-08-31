# agent-games 合集改名 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把单一 NLHE skill 仓库改成 `agent-games` 合集，NLHE 作为 `skills/nlhe/` 中的一款 skill，GitHub 与本地目录一并改名。

**Architecture:** 根目录只做合集壳（README / LICENSE / .gitignore / docs），没有根 `SKILL.md`。每个游戏一个 skill，放在 `skills/<name>/`，以符合 `npx skills` 对 `skills/` 的扫描约定。NLHE 玩法、`/NLHE`、`.nlhe/` 运行态、引擎与 charts 不改；只搬家和改安装文案。改名顺序：先提交仓库内容 → `gh repo rename` → 改 origin 与本地目录。

**Tech Stack:** Git、GitHub CLI (`gh`)、Python 3 stdlib 测试（已有 `test_coach.py`）、npx skills CLI。

**Spec:** `docs/superpowers/specs/2026-08-31-agent-games-rename-design.md`

## Global Constraints

- 仓库名 / GitHub：`zp342519261/agent-games`（由 `zp342519261/nlhe` 改名）
- 本地目录：`/Users/ollk/workspace/nlhe` → `/Users/ollk/workspace/agent-games`
- 一游戏一 skill，路径：`skills/nlhe/`
- 安装命令写死：`npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y`
- 检查 / 更新已装 skill：`npx skills check nlhe -g` 与 `npx skills update nlhe -g -y`
- `VERSION` 保持 `1.5.2`；CHANGELOG 只在 1.5.2 下加一条搬家说明
- 不改 NLHE 玩法、`/NLHE`、引擎逻辑、charts、`.nlhe/` 运行态、skill `name: nlhe`
- 不新增第二款游戏；不做旧用户自动迁移脚本
- 不改 GitHub 用户名、LICENSE 的 MIT 许可证类型
- `git commit` / `git push` / `gh repo rename` 仅在用户本轮明确同意后执行；未同意则做完文件改动后停下
- 用户规则：不要额外写总结文档；验证只跑本 plan 写明的命令

---

### Task 1: 把 NLHE 迁入 `skills/nlhe/`

**Files:**
- Move: `SKILL.md` → `skills/nlhe/SKILL.md`
- Move: `VERSION` → `skills/nlhe/VERSION`
- Move: `CHANGELOG.md` → `skills/nlhe/CHANGELOG.md`
- Move: `reference.md` → `skills/nlhe/reference.md`
- Move: `templates/` → `skills/nlhe/templates/`
- Move: `charts/` → `skills/nlhe/charts/`
- Move: `tests/` → `skills/nlhe/tests/`
- Keep at root: `README.md`, `LICENSE`, `.gitignore`, `docs/`

**Interfaces:**
- Consumes: 当前仓库根即 NLHE skill（`SKILL.md` 与 `templates/` 为兄弟目录）
- Produces: skill 根变为 `skills/nlhe/`。`resolve_skill_root()` 在引擎位于 `templates/` 时用 `parent.parent`，搬家后仍指向 `skills/nlhe/`。`tests/test_coach.py` 用 `parents[1] / "templates"`，搬家后仍指向 `skills/nlhe/templates`。不要改 `Path.cwd() / "nlhe"`（那是用户项目里名为 `nlhe` 的 skill 副本）。

- [ ] **Step 1: 确认当前是 git 仓库且根上仍有 SKILL.md**

Run:

```bash
cd /Users/ollk/workspace/nlhe
test -f SKILL.md && test -d templates && test ! -d skills
git status
```

Expected: `SKILL.md` 存在、`skills/` 不存在；status 可含已有的 spec/plan 未提交文件。

- [ ] **Step 2: git mv 整包迁入 skills/nlhe**

Run:

```bash
cd /Users/ollk/workspace/nlhe
mkdir -p skills/nlhe
git mv SKILL.md VERSION CHANGELOG.md reference.md skills/nlhe/
git mv templates charts tests skills/nlhe/
```

Expected: 无报错。根目录不再有 `SKILL.md`、`templates/`、`charts/`、`tests/`、`VERSION`、`CHANGELOG.md`、`reference.md`。

- [ ] **Step 3: 验证布局 + 跑已有教练测试**

Run:

```bash
cd /Users/ollk/workspace/nlhe
test ! -f SKILL.md
test -f skills/nlhe/SKILL.md
test -f skills/nlhe/VERSION
test -f skills/nlhe/templates/nlhe_engine.py
test -d skills/nlhe/charts
python3 skills/nlhe/tests/test_coach.py -v
```

Expected: 所有 `test` 成功；`test_coach.py` 全部 PASS。若 FAIL，先停：多半是 `sys.path` 相对路径坏了，不要改玩法，只修 `tests/test_coach.py` 的 path insert，使其指向 `skills/nlhe/templates`。

- [ ] **Step 4: Commit（仅当用户已授权 commit）**

```bash
git add skills/nlhe
git status
git commit -m "$(cat <<'EOF'
chore: 将 NLHE skill 迁入 skills/nlhe

为合集仓库腾出根目录，NLHE 成为第一款可独立安装的 skill。
EOF
)"
```

若用户未授权 commit：跳过本步，继续 Task 2。

---

### Task 2: 合集 README、NLHE 文档与安装文案

**Files:**
- Modify: `README.md`（整文件改写成合集目录页）
- Create: `skills/nlhe/README.md`（原根 README 的 NLHE 说明，路径按仓库克隆更新）
- Modify: `skills/nlhe/CHANGELOG.md`（1.5.2 下加一条）
- Modify: `skills/nlhe/templates/nlhe_engine.py`：两处 `OWNER/nlhe` 改为 `zp342519261/agent-games`
- Modify: `skills/nlhe/reference.md`：两层更新表上方加首次安装命令
- Keep: `skills/nlhe/SKILL.md` 里 `cp nlhe/templates/...`（安装后 skill 目录仍叫 `nlhe`）；`npx skills check/update nlhe` 不变

**Interfaces:**
- Consumes: Task 1 的 `skills/nlhe/` 布局
- Produces: 对外安装命令统一为 `npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y`

- [ ] **Step 1: 把根 README 改成合集页**

将 `/Users/ollk/workspace/nlhe/README.md` **整文件**替换为下面内容（外层四反引号；写入文件时用普通三反引号围栏）：

````markdown
# agent-games

给 Agent 玩的 skill 游戏合集。每一款游戏是一个独立 skill，用 `npx skills add` 按名字安装。

当前游戏：

| Skill | 说明 | 斜杠命令 |
|-------|------|----------|
| [nlhe](skills/nlhe/) | 6-max 德州扑克 GTO 教学桌 | `/NLHE` |

## 安装（Cursor）

只装 NLHE：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y
```

- `-g`：装到 `~/.cursor/skills/nlhe`（全局）
- `-a cursor`：只给 Cursor
- `-s nlhe`：从这个合集只装这一款

[![skills.sh](https://skills.sh/b/zp342519261/agent-games)](https://skills.sh/b/zp342519261/agent-games)

已经用旧仓库 `zp342519261/nlhe` 装过的：请改用上面这条命令重新安装（不提供自动迁移）。GitHub 会把旧 URL 重定向到本仓库。

## 仓库结构

```
agent-games/
├── README.md
├── LICENSE
└── skills/
    └── nlhe/          # 德州扑克 GTO 教学桌
```

以后加游戏：在 `skills/` 下新建目录，内含自己的 `SKILL.md`。

## License

MIT — 见 [LICENSE](LICENSE)
````

- [ ] **Step 2: 写入 skills/nlhe/README.md**

创建 `/Users/ollk/workspace/nlhe/skills/nlhe/README.md`，内容为：

````markdown
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
````

- [ ] **Step 3: CHANGELOG 加搬家说明（不改 VERSION）**

在 `skills/nlhe/CHANGELOG.md` 的 `## 1.5.2` 列表**最上方**插入一条：

```markdown
- **仓库**：迁入合集 `zp342519261/agent-games`（路径 `skills/nlhe/`）；安装改为 `npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y`
```

确认 `skills/nlhe/VERSION` 仍是 `1.5.2`（可带或不带换行，与现文件一致）。

- [ ] **Step 4: 引擎里两处安装源文案**

在 `skills/nlhe/templates/nlhe_engine.py` 把下面两处字符串**原样替换**（只改仓库名，其它参数不变）：

旧：

```python
"  若通过 skills.sh 安装: npx skills add OWNER/nlhe -g -a cursor -s nlhe -y",
```

新：

```python
"  若通过 skills.sh 安装: npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y",
```

旧：

```python
"action:       npx skills add OWNER/nlhe -g -a cursor -s nlhe -y",
```

新：

```python
"action:       npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y",
```

不要改 `SKILL_NAME = "nlhe"`，不要改 `npx skills check nlhe` / `update nlhe` 那些行。

- [ ] **Step 5: reference.md 补首次安装**

在 `skills/nlhe/reference.md` 的 `### 两层更新` 标题**之后**、表格**之前**插入：

````markdown
首次安装 / 换源重装：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y
```
````

表格里的 check/update 命令保持不变。

- [ ] **Step 6: 确认 SKILL.md 安装后拷贝路径未改错**

Run:

```bash
cd /Users/ollk/workspace/nlhe
rg -n "zp342519261/nlhe|OWNER/nlhe" skills/nlhe README.md || true
rg -n "cp nlhe/templates" skills/nlhe/SKILL.md
python3 skills/nlhe/tests/test_coach.py -v
```

Expected:

- 仓库内容里不再出现 `zp342519261/nlhe` 或 `OWNER/nlhe`（`docs/superpowers/` 里提到旧名作为历史说明可以保留）
- `SKILL.md` 仍有 `cp nlhe/templates/...`（安装后路径）
- 测试 PASS

- [ ] **Step 7: Commit（仅当用户已授权 commit）**

```bash
git add README.md skills/nlhe/README.md skills/nlhe/CHANGELOG.md skills/nlhe/templates/nlhe_engine.py skills/nlhe/reference.md
git commit -m "$(cat <<'EOF'
docs: 将仓库说明改为 agent-games 合集并更新 NLHE 安装源

根 README 只做游戏目录；NLHE 文档与引擎提示改为从 agent-games 安装。
EOF
)"
```

---

### Task 3: GitHub 改名、本地目录、安装发现验收

**Files:**
- Remote: GitHub 仓库 `zp342519261/nlhe` → `zp342519261/agent-games`
- Local folder: `/Users/ollk/workspace/nlhe` → `/Users/ollk/workspace/agent-games`
- Git: `origin` URL 更新
- No source-tree file moves in this task

**Interfaces:**
- Consumes: Task 1–2 的提交（至少工作区已改完；push 需用户同意）
- Produces: 对外地址 `https://github.com/zp342519261/agent-games`；`npx skills add zp342519261/agent-games --list` 能列出 `nlhe`

- [ ] **Step 1: 征得用户同意后再 push / rename**

若用户还没说可以 push、可以改 GitHub 名字：**停在这里问**，不要执行 Step 2–5。

需要用户明确同意这三件事（可一条消息里一起回）：

1. `git push` 当前分支
2. `gh repo rename agent-games`
3. 把本地文件夹改名为 `agent-games`

- [ ] **Step 2: 推送已有提交（当前 origin 仍是 nlhe）**

```bash
cd /Users/ollk/workspace/nlhe
git status
git push -u origin HEAD
```

Expected: push 成功。若无远程跟踪分支，按当前默认分支 push。

- [ ] **Step 3: 重命名 GitHub 仓库**

```bash
cd /Users/ollk/workspace/nlhe
gh repo rename agent-games --yes
git remote set-url origin https://github.com/zp342519261/agent-games.git
git remote -v
gh repo view --json name,url -q '{name,url}'
```

Expected: `name` 为 `agent-games`；fetch/push URL 含 `agent-games.git`。

- [ ] **Step 4: 本地目录改名，并把 Cursor workspace 指过去**

```bash
cd /Users/ollk/workspace
mv nlhe agent-games
ls agent-games/README.md agent-games/skills/nlhe/SKILL.md
```

然后调用 Cursor `cursor-app-control` 的 `move_agent_to_root`，`path` 设为 `/Users/ollk/workspace/agent-games`。

Expected: 新路径下能看到合集 README 与 `skills/nlhe/SKILL.md`。告诉用户：若当前聊天仍绑定旧路径，请用 Cursor 打开 `/Users/ollk/workspace/agent-games`。

- [ ] **Step 5: skills CLI 能发现 nlhe**

在网络可用时：

```bash
cd /Users/ollk/workspace/agent-games
npx skills add zp342519261/agent-games --list
```

Expected: 输出里出现 skill 名 `nlhe`。若「No skills found」：先确认 GitHub 上 `skills/nlhe/SKILL.md` 已在默认分支；不要改目录改成根级 `nlhe/`，先查 CLI 是否要更深扫描，再问用户。

不要在本 task 里对用户机器执行 `npx skills add ... -y`（那会改全局 skill）；`--list` 只读即可。

---

## 执行交接

Plan 写在 `docs/superpowers/plans/2026-08-31-agent-games-rename.md`。两种执行方式：

**1. Subagent-Driven（推荐）** — 每个 Task 派一个新 subagent，Task 之间人工过一眼

**2. Inline Execution** — 本会话按 executing-plans 逐步做，做完一个 Task 停下来给你看

选哪个？另外：Task 1–2 的 **commit**、以及 Task 3 的 **push / GitHub 改名 / 本地改文件夹**，要不要现在一并授权？
