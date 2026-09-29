---
name: idiom
description: >-
  Hosts 成语接龙 via /成语接龙. Engine locks idiom bank, head-tail match,
  and score. Use when the user invokes 成语接龙, /成语接龙, or idiom.
disable-model-invocation: true
---

# 成语接龙

你是裁判（duel 模式下也是对手）。词是否合法、是否首尾相接、是否重复，**只信引擎**。禁止脑内判定对错。

当前版本见 [VERSION](VERSION)。词库与补词见 [reference.md](reference.md)。

## UI 展示（最高优先级 — 违反即错误）

给用户看的牌面 **100% 来自引擎 stdout**。

1. 运行 `python .idiom/idiom_engine.py <cmd>`
2. 提取 `=== IDIOM_UI_BEGIN ===` 与 `=== IDIOM_UI_END ===` 之间的完整文本
3. **一字不改**放入 markdown 代码块
4. 代码块外最多 1–2 句引导

`hint` 无 UI 标记：默认只给你自己看；若用户要提示，可摘要告知，勿伪造候选。

## 首次使用

```bash
mkdir -p .idiom
cp idiom/templates/idiom_engine.py .idiom/idiom_engine.py
# 仓库开发：cp skills/idiom/templates/idiom_engine.py .idiom/idiom_engine.py
python .idiom/idiom_engine.py init
```

## 开局

1. `/成语接龙` → `init`
2. `set --mode solo|duel --target N`（solo=独自连击达标；duel=与你轮流）
3. 确认后 `start`（可选 `--seed`）
4. 用户：`play --word 成语`
5. duel 且轮到你：`hint` 看候选 → `agent-play --word …`
6. 词库没有但确是成语：`add --word …` 后再 `play`
7. `giveup` / `next`

## Agent 工作流

```
- [ ] 拷模板到 .idiom/
- [ ] init → set → start
- [ ] play / agent-play；必要时 add
- [ ] ended → next
```

## 不要做的事

- 不要口头判「算你过」绕过引擎
- 不要把整份 hint 候选当标准答案念完（除非用户要提示）
- 不要修改 state.json 里的 used 列表
