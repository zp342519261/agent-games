# agent-games：仓库改名为 skill 游戏合集

日期：2026-08-31  
状态：已批准（2026-08-31）

## 目标

把当前单一 NLHE skill 仓库，改成 **Agent skill 游戏合集**。NLHE 是其中一款游戏，本轮不加第二款。

对外名称：`agent-games`  
GitHub：`zp342519261/nlhe` → `zp342519261/agent-games`  
本地目录：`workspace/nlhe` → `workspace/agent-games`

## 非目标

- 不新增第二款游戏
- 不改 NLHE 玩法、`/NLHE` 指令、引擎、charts、教练条
- 不改项目运行态目录（仍是 `.nlhe/`）
- 不给旧安装用户做自动迁移脚本
- 不合集单独起版本号（版本仍跟各游戏走）

## 决策摘要

| 项 | 选择 |
|----|------|
| 仓库名 | `agent-games` |
| Skill 模型 | 一游戏一 skill |
| 目录 | `skills/<name>/`（skills.sh 合集约定） |
| GitHub | 远程一并改名；旧 `nlhe` URL 由 GitHub 重定向 |
| 安装 | `-g -a cursor`：全局 `~/.cursor/skills/`，只装 Cursor |
| 版本 | `VERSION` / `CHANGELOG` 留在 `skills/nlhe/` |

## 目标结构

```
agent-games/
  README.md              # 合集：介绍 + 游戏列表 + 安装
  LICENSE
  .gitignore
  docs/superpowers/      # 本设计与后续 plan（实现时保留）
  skills/
    nlhe/
      SKILL.md
      VERSION
      CHANGELOG.md
      reference.md
      templates/
      charts/
      tests/
```

根目录 **没有** `SKILL.md`。根目录不再扮演「一个 skill」。

## 安装与更新

推荐安装（README 写死）：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y
```

含义：

- `-g`：全局，装到 `~/.cursor/skills/nlhe`
- `-a cursor`：只给 Cursor，不装到其它 Agent
- `-s nlhe`：从这个合集只装 NLHE

不写 `-a` 时 CLI 会询问 Agent，**不会**默认装进 `.agents`。Cursor **项目级**（无 `-g`）才是 `.agents/skills/`。

文档里的命令分工：

- **首次安装 / 换源重装**：`npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y`
- **检查 / 更新已装 skill**：`npx skills check nlhe -g` 与 `npx skills update nlhe -g -y`（按已装名称 `nlhe`，源地址写在 lock 里）

旧文档里的 `npx skills add zp342519261/nlhe …` 全部换成上面的 add 命令。已用旧仓库装过的人，lock 仍可能指向 `zp342519261/nlhe`（GitHub 重定向）；要彻底换源就再跑一次新的 `add`。

## NLHE 搬家规则

**保持不变：**

- skill `name: nlhe`
- `/NLHE`、引擎脚本、charts、教练条
- 用户项目里的 `.nlhe/` 运行态
- `VERSION` 仍为当前 `1.5.2`，`CHANGELOG` 只加一条「迁入合集仓库」类说明，不升功能版本也可（实现时一条 changelog 即可）

**必须改：**

- 现有根级 NLHE 文件整包移入 `skills/nlhe/`
- 根 `README.md` 改写为合集目录页（不再只讲 NLHE 玩法细节；NLHE 细节仍在 `skills/nlhe/`）
- 克隆仓库后手动拷模板的路径：`nlhe/templates/` → `skills/nlhe/templates/`（及 coach、charts 同理）
- 经 skills.sh 安装后，skill 仍落在 `~/.cursor/skills/nlhe/`。Agent 从 **已安装 skill 目录** 拷模板的指令继续用 `nlhe/templates/`（安装后布局与现在一致）

## 改名顺序

1. 先改仓库内容（搬家 + 文案）
2. 再 `gh repo rename agent-games`
3. 更新本地 `origin`；工作区目录改为 `agent-games`
4. 不改 GitHub 用户名、LICENSE 许可证类型

旧用户：README 用一句话说明请改用新地址安装；不强制卸载、不做迁移脚本。GitHub 对旧 `nlhe` URL 的重定向可依赖平台默认行为。

## 验收

- 根目录无 `SKILL.md`；NLHE 全在 `skills/nlhe/`
- 根 README 表明这是游戏合集，安装命令为上面那条
- GitHub 仓库名为 `agent-games`，本地目录名为 `agent-games`
- 内容 push 之后：`npx skills add zp342519261/agent-games --list` 能列出 `nlhe`
- 不测 NLHE 玩法；只确认文件仍在、文档路径已改

## 风险

- skills.sh 若未识别 `skills/nlhe/SKILL.md`，安装会失败 → 用 `--list` 验收；若失败再查 CLI 扫描深度，不提前加额外包装
- 已装旧 `nlhe` 的全局 skill 不会自动改源 → 文档说明即可
- Cursor 工作区路径变更后，当前对话的 workspace 可能需要重新打开新目录
