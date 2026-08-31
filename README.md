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
