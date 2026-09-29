# 谁是卧底

多人社交推理。Agent 主持，引擎锁定词对与身份。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s spy -y
```

## 使用

在 Cursor 聊天中：

```
/卧底
/卧底 init
```

先确认人数与卧底数，再开始。看自己的词：`/卧底 myword`。认输揭晓：`/卧底 giveup`。下一局：`/卧底 next`。

从本仓库开发时：

```bash
mkdir -p .spy
cp skills/spy/templates/spy_engine.py .spy/
python .spy/spy_engine.py init
```

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/spy/` 下执行。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
