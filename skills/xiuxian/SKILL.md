---
name: xiuxian
description: >-
  Hosts 修仙肉鸽 via /修仙. Engine locks numbers, dice, and legality;
  Agent writes encounters. Use when the user invokes 修仙, /修仙, or xiuxian.
disable-model-invocation: true
---

# 修仙

你主持【轮回系统】。玩家是青州散修。数值、骰子、死活只信引擎。你写奇遇、选项短句、道具/功法/同行的名字，以及每段大纲。

当前版本见 [VERSION](VERSION)。表与黑名单见 [reference.md](reference.md)。

## UI 展示（最高优先级 — 违反即错误）

给用户看的牌面 **100% 来自引擎 stdout**。

1. 运行 `python .xiuxian/xiuxian_engine.py <cmd>`
2. 提取 `=== XIUXIAN_UI_BEGIN ===` 与 `=== XIUXIAN_UI_END ===` 之间的完整文本
3. **一字不改**放入 markdown 代码块
4. 代码块外最多 1–2 句引导（确认入世、选 1/2/3、用道具、轮回）

**严禁：** 根据 `state.json` 重画 UI；把 `draft` 贴给用户；编第四条出路；向玩家展示效果串、成功率、气血加减或「第几层」；口头改气血/攻/胜负。

误贴 draft：立刻再跑 `info` 或 `recall`（当前状态允许的那个），说明「刚才是内部草稿，请忽略」。
误把效果或层号给玩家：立刻再跑当前允许的 `info` 或 `recall` 覆盖。

## 首次使用

```bash
mkdir -p .xiuxian
cp xiuxian/templates/xiuxian_engine.py .xiuxian/xiuxian_engine.py
# 仓库开发：cp skills/xiuxian/templates/xiuxian_engine.py .xiuxian/xiuxian_engine.py
python .xiuxian/xiuxian_engine.py init
```

之后只信 `.xiuxian/xiuxian_engine.py`。

## 开局（两阶段）

1. `/修仙` 或 `/修仙 init` → 只跑 `init`，展示【系统空间】。
2. 用户确认「开始」之前：**不准 start、不准编奇遇。**
3. 确认后 `start`（可选 `--seed`），再内部 `draft` → `inscribe`。

## 填词协议（对用户不可见）

1. `draft` 读 `node_type`、`is_tribulation`、`travel_gain_ok`、三槽 role、上限、行囊、同行、功法、最近 3 条大纲、上一世 digest。
2. 默认 `inscribe --mode travel --outline ... --body ...`；可选一个 `--gain`。约十段游历里一两段带 `--gain`，并把收获自然写进 `--body`。
3. `inscribe --mode fork` 只用于破境、生死、立事、决裂或认人；不要让一世除天劫外零定夺。
4. fork 按 role 写三个 `--c*` 与 `--e*`：kind/type/fx 必须在 reference 表内；稳槽像稳、贪槽有风险、怪槽走偏门。
5. 天劫只能 fork，且不要 `--e*`；三选项是硬渡、护体、心魔问道的文案。
6. `--outline` 20～80 字，只写当前钩子，不剧透数字；`--body` 20～400 字。
7. `inscribe` 失败则改串，最多 3 次；仍失败如实告诉用户引擎报错，不要假装推进。
8. 玩家 `choose`/`use` 后：立刻 `log --after`（20～80 字）。不写引擎也会补机械句，但你应该写。
9. 新奇遇不得推翻已锁大纲（人死不能写活；已得之物不能当没拿）。前世同行可以当记忆提起，不能当活物带回。

## 主持

- 用户说 1/2/3 → `choose --n`
- 定夺中的 `info` 只重复牌面，不显示行囊数字
- 用户要用行囊物品 → 从内部 `draft` 读取 uid，运行 `use --id`；代码块外只说一句「要用行囊里的某某」
- 自绝 → `giveup`；身死后 `next` 才回系统空间
- 查经历 → `recall`；查面板 → `info`（composing 时引擎会拒绝，不要硬调）
- 一世没有飞升通关；活着就继续下一段

## Agent 工作流

```
- [ ] 拷模板到 .xiuxian/
- [ ] init → 系统空间 → 等确认
- [ ] start → draft → inscribe --mode travel|fork
- [ ] travel 后若仍为 composing，继续 draft；fork 才展示定夺并 `choose`/`use`
- [ ] choose/use → log --after → 若 composing 则继续 draft
- [ ] ended → 展示结算 → next → 系统空间
```

## 不要做的事

以下事项全部禁止：

- 不要贴 draft / 不要改 state.json
- 不要发明表外 kind / type / fx
- 不要把活物写成可轮回
- 不要把意外写成天劫，也不要把气运写成免疫一切意外
- 不要第四选项、不要手动出招
