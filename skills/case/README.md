# 探案

推理搜证。Agent 主持询问，引擎锁定线索与真凶。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s case -y
```

## 使用

在 Cursor 聊天中：

```
/探案
/探案 init
```

确认难度后开始。搜证、询问嫌疑人，最后指控真凶。认输 `/探案 giveup`；下一局 `/探案 next`。

从本仓库开发时：

```bash
mkdir -p .case
cp skills/case/templates/case_engine.py .case/
python .case/case_engine.py init
```

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/case/` 下执行。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
