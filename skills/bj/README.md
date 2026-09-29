# 二十一点

经典 Blackjack。引擎锁定洗牌与点数。适用于 Cursor 等 Agent。

当前版本：**1.0.0**（见 [VERSION](VERSION) · [CHANGELOG](CHANGELOG.md)）

## 安装

```bash
npx skills add zp342519261/agent-games -g -a cursor -s bj -y
```

## 使用

```
/二十一点
/二十一点 init
```

确认配置后开始；`hit` / `stand` / `double`；下一手 `deal`；回配置 `next`。

```bash
mkdir -p .bj
cp skills/bj/templates/bj_engine.py .bj/
python .bj/bj_engine.py init
```

## 开发

```bash
python3 tests/test_engine.py -v
```

在 `skills/bj/` 下执行。

## License

MIT — 见仓库根目录 [LICENSE](../../LICENSE)
