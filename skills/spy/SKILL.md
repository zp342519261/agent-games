---
name: spy
description: >-
  Hosts 谁是卧底 via /卧底. Engine locks word pair, roles, votes, and win
  check. Use when the user invokes 卧底, /卧底, 谁是卧底, or spy.
disable-model-invocation: true
---

# 谁是卧底

你是主持人。引擎锁定词对、卧底座位、发言记录与投票计票。禁止脑内抽签或改票。

当前版本见 [VERSION](VERSION)。词对与主持细则见 [reference.md](reference.md)。

## UI 展示（最高优先级 — 违反即错误）

给用户看的牌面 **100% 来自引擎 stdout**。

1. 运行 `python .spy/spy_engine.py <cmd>`
2. 提取 `=== SPY_UI_BEGIN ===` 与 `=== SPY_UI_END ===` 之间的完整文本
3. **一字不改**放入 markdown 代码块
4. 代码块外最多 1–2 句引导（确认开局、请描述、请投票）

**严禁：** 根据 `state.json` 重画 UI；把 `secret` / 全部身份贴给用户；替用户改票。

`secret` / `npcword` 的 stdout **没有** UI 标记 → **禁止**整段粘贴给用户。误贴了：立刻再跑 `info`，并说明「刚才是内部内容，请忽略」。

## 首次使用

```bash
mkdir -p .spy
cp spy/templates/spy_engine.py .spy/spy_engine.py
# 仓库开发：cp skills/spy/templates/spy_engine.py .spy/spy_engine.py
python .spy/spy_engine.py init
```

之后只信 `.spy/spy_engine.py`。

## 开局（两阶段）

1. `/卧底` 或 `/卧底 init` → 只跑 `init`，展示配置 UI。
2. 用户可改人数 / 卧底数 / 自己的座位：`set --players N --spies K --user-seat U`。
3. 用户确认「开始」之前：**不准 start、不准想词对剧透。**
4. 确认后按 reference 选相近词对，`start --civilian … --spy …`（可选 `--seed`）。
5. 展示开局 UI；让用户跑或代跑 `myword`（只显示词，不标身份）。
6. 你用 `secret` / `npcword --seat` 在内部扮演其他座位（用户看不见）。

## 流程

- **描述阶段**：存活座位各描述一次（暗示自己的词，不直说）。用户描述后：`describe --seat <用户座> --text …`；NPC 由你写短句再同样提交。
- 全员描述完 → 引擎自动进入 **投票**。
- **投票**：`vote --voter N --target M`。全员投完自动计票；平票无人出局；否则一人出局并公布其平民/卧底身份。
- 胜负由引擎判定：无卧底→平民胜；卧底数 ≥ 平民数→卧底胜。
- `/卧底 giveup` → 提前揭晓；`/卧底 next` → 回配置。

## Agent 工作流

```
- [ ] 拷模板到 .spy/
- [ ] init → 配置 → 等确认
- [ ] start 词对 → myword 给用户 → secret 自己看
- [ ] 轮流 describe → 投票 vote → 直至 ended
- [ ] next 再来一局
```

## 不要做的事

- 不要脑内指定谁是卧底
- 不要把 secret / 全部身份给用户
- 不要在描述里直接念出词面（你自己扮演 NPC 时也尽量暗示）
- 不要跳过引擎改存活名单或胜负
