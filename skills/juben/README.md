# 剧本杀

多角色本杀。Agent 主持并演 NPC，引擎锁定角色本与投票。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s juben -y
```

## 使用

在 Cursor 聊天中：

```
/剧本杀
/剧本杀 init
```

确认后开始。看自己的本：`/剧本杀 myrole`。认输揭晓：`/剧本杀 giveup`。下一局：`/剧本杀 next`。

从本仓库开发时：

```bash
mkdir -p .juben
cp skills/juben/templates/juben_engine.py .juben/
python .juben/juben_engine.py init
```

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/juben/` 下执行。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
