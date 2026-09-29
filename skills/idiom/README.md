# 成语接龙

轻量文字竞技。引擎校验词库与首尾相接。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s idiom -y
```

## 使用

```
/成语接龙
/成语接龙 init
```

`solo` 冲连击或 `duel` 对战主持。出词：`play --word …`。认输：`giveup`。下一局：`next`。

```bash
mkdir -p .idiom
cp skills/idiom/templates/idiom_engine.py .idiom/
python .idiom/idiom_engine.py init
```

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/idiom/` 下执行。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
