# 修仙叙事节奏改版（xiuxian 1.1）

日期：2026-09-02  
状态：已确认（2026-09-02）

本文件是对 [2026-09-01-xiuxian-design.md](./2026-09-01-xiuxian-design.md) 的**玩法改版**。未写明的条目（境界、战斗、天劫公式、轮回配额、42 技能、36×41 死物、大纲字数、state 字段除本文件新增者外）仍以旧 spec 与现有 `skills/xiuxian/` 为准。

冲突时：**玩家牌面与 `inscribe` 模式以本文件为准。**

## 目标

玩家侧改成「先看这阵子游历了什么，关键情况再定夺」，而不是每一层都点三选一。

引擎仍按层结算、仍锁骰子与合法性。玩家看不见「层」。

`VERSION` 升到 **1.1.0**。不改 `skills/nlhe/`、`skills/soup/`。

## 非目标

- 不改战斗公式、轮回裁剪、经验阈值、天劫成功率计算
- 不做真实历法/寿元（「这几年」只是文案）
- 不做引擎强制「每 N 层必须分叉」（除天劫外由 Agent 决定；SKILL 约束节奏）
- 不把数值奖励画回定夺牌面

## 决策摘要

| 项 | 选择 |
|----|------|
| 节奏 | 默认游历；Agent 判断关键才定夺；天劫必须定夺 |
| 游历收获 | 可选；一层至多一种；连续两层游历不能都给 |
| 定夺牌面 | 只给三个短句，不露效果/角色/成功率 |
| 层号 | 一切玩家 UI 禁止出现「层」 |
| 给物给人 | 游历可给；定夺选项也可给 |

## 状态机

```
hub ──start──► composing ──inscribe travel──► composing …（不经 choosing）
                      │
                      └──inscribe fork──► choosing ──choose/use──► composing / ended
```

天劫层 `inscribe --mode travel` → `ERROR`，state 不变。

`use` 仍仅 `choosing` 且非天劫。游历年不能用药结束本段。

`giveup` / `log` / `recall` / `next` 规则同旧 spec。

## 一层时序

1. 引擎定 `node_type`、掷三槽（天劫不掷），`composing`。  
2. `draft`（无 UI 标记）。  
3. `inscribe --mode travel|fork`（必填 `--outline`）。  
4. **travel**：校验 `--gain`（若有）→ 套用 → 写 chronicle（`act=travel` 或 `travel+gain`）→ `pending_log=true` → 活则 `floor+=1` 回 1；死则 `ended`。不进 `choosing`。  
5. **fork**：进 `choosing`，出定夺牌面；其后 `choose`/`use` 同旧 spec（战斗、意外、天劫骰不变）。  
6. `log --after` 仍建议立刻写；不写则下一步 `draft`/`inscribe`/`next` 机械补。机械句只用「这一段游历结束」或「路已选定」，**不得**含「层」字、气血数字、胜负字样。

`event_battle` 不再等于「本层必打」。开战只发生在定夺选项/`use` 带了会打的效果。游历层即使 `node_type=event_battle` 也不自动开战。`draft` 仍提示「本层偏患事」，供 Agent 决定要不要 fork。

## `inscribe`

```
--mode travel|fork     必填（天劫层只允许 fork）
--outline              必填，20～80 字
--body                 必填，20～400 字
```

**travel**

- 禁止 `--c1/c2/c3`、`--e1/e2/e3`（带了 → `ERROR`）  
- 可选 `--gain S`：整段必须是**恰好一种**原子：`grant:…` 或 `ally:…` 或 `skill:…`（与旧解析器相同语法）  
- `--gain` 合法性：  
  - 禁止 `battle`、`accident`、`hp-`、`atk±`、`qi±`、`maxhp` 等非 grant/ally/skill 原子  
  - `grant` 的 `fx` 仅 SAFE 白名单：`hp,qi,maxhp,ward,iron,luck_floor,exp,fullhp,barrier,meridians_now,dawn_fight,sight,rest,insight_now`  
  - `skill` 的 `kind` 仅 SAFE：`breath,qi_flow,guard,meditation,meridians,sage,dawn,spark_ward`  
  - `ally`：`partner` n=1；`dao` n=1～3；`beast` n=1～3  
- 一层最多一种收获；无 `--gain` 合法  
- `--gain` 走现有 `parse_effect`；多原子、未知 type/fx、解析失败 → `ERROR`，state 不变  
- `run.travel_looted`：上一层是否为「带收获的游历」。为 true 时本层 travel 再带 `--gain` → `ERROR`  
- 本层游历有 `--gain` → 结算后 `true`；空游历 → `false`；定夺 `choose`/`use` 结算后 → `false`（中间夹了定夺就不算连续游历，下一层游历可以再给）。定夺自己给的物不占用这条空窗。  
- `start` 时 `travel_looted=false`

**fork**

- 非天劫：必填 `--c1/c2/c3`、`--e1/e2/e3`，校验同旧 spec（三槽 SAFE/GREEDY/WEIRD）  
- 天劫：不要 `--e*`、不要 `--gain`；三选项对应硬渡/护体/心魔，文案自定义  

缺 `--mode` → `ERROR`。

## 玩家 UI（有 `XIUXIAN_UI_*` 标记）

禁止出现：「层」「第N层」「进入下一层」以及效果原文、角色名 SAFE/GREEDY/WEIRD、成功率百分数、`气血+N` / `攻+N` 这类奖励数字。

| 场面 | 内容 |
|------|------|
| start | 例如「【轮回系统】新一世启程」+ 境界；不写层 |
| travel 成功 | 仅 `--body` |
| fork / 定夺中 `info` | `--body` + `1. 2. 3.` 短句；天劫同样不写成功率 |
| choose/use 结算 | 一句「你选了：{短句}」或「已使用：{名字}」；不报面板数字、不报层 |
| recall | 只列出 `setup` / `after` 句子；不写 `floor` |
| hub / ended `info` | 仍是系统面板（气血、格、前世、死因、待轮回预览）——主动查账才给数字 |

`draft` / `help` 仍无 UI 标记。`draft` 必须含：`node_type`、是否天劫、`travel_looted`、本层 travel 是否允许 `--gain`、三槽、面板、成功率（天劫）。

## SKILL（相对 1.0 新增）

- 默认 `--mode travel`；`--mode fork` 只用于破境、生死、立事、决裂/认人。  
- 不要一世除天劫外零定夺；关键情况必须停。  
- 约十段游历里一两段带 `--gain`，空窗正常。  
- 玩家可见回复禁止：效果串、成功率、气血加减、「第几层」。  
- 游历收获须写进 `--body`（拣到什么、遇见谁），不要只靠引擎暗加。  
- 误把定夺效果或层号给玩家：立刻再跑当前允许的 `info`/`recall` 覆盖。

## 测试（本改版最低集）

- `inscribe` 无 `--mode` → ERROR  
- 天劫 `travel` → ERROR，status 仍 composing  
- travel 无 `--gain`：status=composing，floor+1，chronicle `act` 含 travel，stdout 有 body、无「层」、无 `气血+`  
- travel `--gain` 合法 grant：行囊 +1；紧接着再 travel `--gain` → ERROR；空 travel 或一次定夺结算之后，下一段 travel 才允许再给  
- travel `--gain` 带 `battle` 或 GREEDY skill → ERROR  
- fork 玩家 UI：有三个短句，无 `SAFE`/`GREEDY`、无 `fmt_effect` 中文奖励、无 `%`  
- 天劫 fork UI 无「成功率」  
- start / choose 结算 / recall 均不含「层」  
- `event_battle` 层 travel 后未开战（`did_battle` false）  
- 旧：意外、天劫骰、轮回配额、非法 inscribe 不改 state —— 回归仍过  

## 验收

- 玩一局可以连续几段只看游历，偶尔才三选一  
- 选的时候看不到奖励数字  
- 游历里能遇到人或拣到东西，定夺里也能  
- 全程看不到「第几层」  
- `info` 在系统空间仍能查面板  

## 风险

- Agent 一直 travel → SKILL 约束；引擎只锁天劫  
- 游历给物过密 → 连续空窗硬限制 + 稳槽白名单  
- 玩家不知物品 uid → 定夺时 `info` 仍不给数字；`use` 靠 Agent 在代码块外用一句「要用行囊里的某某（引擎 uid）」——**不在本改版把 uid 画回定夺牌面**；查完整行囊用 hub/`ended` 的 `info`，局中 `use` 仍认 uid（Agent 从 `draft` 读）
