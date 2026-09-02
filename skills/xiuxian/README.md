# 修仙

Agent 当主持、你当散修。没有固定剧本；每世现编奇遇，引擎锁定数值与骰子。适用于 Cursor 等 Agent。

当前版本：**1.1.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s xiuxian -y
```

## 使用

在 Cursor 聊天中：

```
/修仙
/修仙 init
```

先进入【系统空间】，确认「开始」后才 `start` 入世。多数片段直接游历推进；遇到破境、生死、立事等关键情况，再选 1/2/3 定夺。用药 `use`；自绝 `giveup`；身死后 `next` 回系统空间。

从本仓库开发时，在**用户项目**（或仓库根）拷运行态：

```bash
mkdir -p .xiuxian
cp skills/xiuxian/templates/xiuxian_engine.py .xiuxian/
python .xiuxian/xiuxian_engine.py init
```

经 skills.sh 安装后，skill 在 `~/.cursor/skills/xiuxian/`，Agent 按 `SKILL.md` 从 `xiuxian/templates/` 同步到 `.xiuxian/`。

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/xiuxian/` 下执行，或：`python3 -m unittest` 以该目录为 cwd。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
