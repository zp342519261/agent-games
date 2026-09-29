# 文字冒险

分支叙事。Agent 主持演绎，引擎锁定剧情图与道具。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s adv -y
```

## 使用

在 Cursor 聊天中：

```
/冒险
/冒险 init
```

先选类型与难度，确认后开始。局中按数字选分支；放弃 `/冒险 giveup`；下一局 `/冒险 next`。

从本仓库开发时：

```bash
mkdir -p .adv
cp skills/adv/templates/adv_engine.py .adv/
python .adv/adv_engine.py init
```

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/adv/` 下执行。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
