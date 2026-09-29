# agent-games

给 Agent 玩的 skill 游戏合集。每一款游戏是一个独立 skill，用 `npx skills add` 按名字安装。

当前游戏：

| Skill | 说明 | 斜杠命令 |
|-------|------|----------|
| [nlhe](skills/nlhe/) | 6-max 德州扑克 GTO 教学桌 | `/NLHE` |
| [soup](skills/soup/) | 海龟汤（Agent 当汤主，现编现猜） | `/海龟汤` |
| [xiuxian](skills/xiuxian/) | 修仙肉鸽（轮回系统） | `/修仙` |
| [spy](skills/spy/) | 谁是卧底（词对社交推理） | `/卧底` |
| [bj](skills/bj/) | 二十一点（引擎发牌结算） | `/二十一点` |
| [idiom](skills/idiom/) | 成语接龙（词库校验） | `/成语接龙` |

## 安装（Cursor）

只装 NLHE：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y
```

只装海龟汤：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s soup -y
```

只装修仙：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s xiuxian -y
```

只装谁是卧底：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s spy -y
```

只装二十一点：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s bj -y
```

只装成语接龙：

```bash
npx skills add zp342519261/agent-games -g -a cursor -s idiom -y
```

- `-g`：装到 `~/.cursor/skills/<skill名>`（全局）
- `-a cursor`：只给 Cursor
- `-s <skill名>`：从这个合集只装这一款

[![skills.sh](https://skills.sh/b/zp342519261/agent-games)](https://skills.sh/b/zp342519261/agent-games)

已经用旧仓库 `zp342519261/nlhe` 装过的：请改用上面这条命令重新安装（不提供自动迁移）。GitHub 会把旧 URL 重定向到本仓库。

## 仓库结构

```
agent-games/
├── README.md
├── LICENSE
└── skills/
    ├── nlhe/          # 德州扑克 GTO 教学桌
    ├── soup/          # 海龟汤（Agent 当汤主，现编现猜）
    ├── xiuxian/       # 修仙肉鸽（轮回系统）
    ├── spy/           # 谁是卧底
    ├── bj/            # 二十一点
    └── idiom/         # 成语接龙
```

以后加游戏：在 `skills/` 下新建目录，内含自己的 `SKILL.md`。

## License

MIT — 见 [LICENSE](LICENSE)
