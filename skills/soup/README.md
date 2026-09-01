# 海龟汤

Agent 当汤主、你猜汤。没有题库；每局现编，引擎锁定汤底。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s soup -y
```

## 使用

在 Cursor 聊天中：

```
/海龟汤
/海龟汤 init
```

先选主题和难度，确认后才出汤面。直接提问；认输 `/海龟汤 giveup`；下一局 `/海龟汤 next`。

从本仓库开发时，在**用户项目**（或仓库根）拷运行态：

```bash
mkdir -p .soup
cp skills/soup/templates/soup_engine.py .soup/
python .soup/soup_engine.py init
```

经 skills.sh 安装后，skill 在 `~/.cursor/skills/soup/`，Agent 按 `SKILL.md` 从 `soup/templates/` 同步到 `.soup/`。

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/soup/` 下执行，或：`python3 -m unittest` 以该目录为 cwd。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
