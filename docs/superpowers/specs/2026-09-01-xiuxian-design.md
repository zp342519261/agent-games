# 短局修仙肉鸽 skill（xiuxian）设计

日期：2026-09-02  
状态：已确认（2026-09-02）

## 目标

在 `agent-games` 合集中新增独立 skill：**修仙**。玩家是凡人散修，身上绑着只有自己能见的【轮回系统】。一世之内只在奇遇分叉口三选一（或用死物道具），战斗由引擎自动结算；**只要还活着，这一世就不结束**，没有「打完九层飞升通关」。

身死（恶斗、意外、走火、渡劫失败、自绝）后系统发动轮回：带走**死物、经验、技能、属性**；**活物留下一世**（伙伴、道侣、灵兽不跟来）。新肉身再入局。

引擎锁角色、上限、骰子与合法性。Agent 写奇遇、属性串、道具/技能/同行的名字。

对外 skill 名：`xiuxian`  
用户指令：`/修仙`  
安装：`npx skills add zp342519261/agent-games -g -a cursor -s xiuxian -y`

调性：凡人流 + 系统流——短、狠、偶尔沙雕。系统口吻像冷面板，不要写成全能保姆。

## 世界观（写死，SKILL / reference 共用）

人界无仙庭编制可玩；第一版不进仙界。地图口称为**青州**，散修开局，强者为尊。

境界只走小说最常见的下境界链（每境不再拆九层，用经验阈值代表深浅）：

`炼气 → 筑基 → 金丹 → 元婴 → 化神`

- 炼气：引气入体，寿元近凡人，秘境里最容易横死  
- 筑基：气海夯实，宗门当外门/散修里稍能站住  
- 金丹：凝丹，一方小能人  
- 元婴：丹破婴生，开始真正怕天劫  
- 化神：触法则边，第一版封顶，不做炼虚/飞升结局

资源：灵石、丹药、符、法器都是**死物**（可进系统空间）。人、妖兽、道侣、灵宠是**活物**（有神魂，系统轮回带不走）。

死法不只有天劫。小说里更常见的是：秘境崩塌、丹爆、追杀、走火入魔、恶斗被斩。天劫只在**大境突破**时出现，失败则身死道消；成功则升境，**故事继续**。

主角例外：命里钉了一块【轮回系统】。别人身死即终；他死一次，系统收割可数字化的东西，另开一具肉身。这是能一遍遍开局的唯一理由，不是气运逆天。

## 非目标

- 不做飞升通关、仙界地图、寿元自然耗尽（可用意外/恶斗代替）
- 不做门派玩法、开放大地图、商店合成、好感度/吃醋
- 不做跨轮回带走活物
- 不做玩家手动出招、放置挂机、多难度排行
- 不做 NLHE 的 version/upgrade/skills-check/charts
- **不新增第四条战斗属性**（战斗只认气血、攻、灵气）
- 不改 `skills/nlhe/`、`skills/soup/`

## 决策摘要

| 项 | 选择 |
|----|------|
| 一世 | 不死就不结束；层数不封顶 |
| 结束一世 | 身死或自绝 → 系统轮回，不是通关 |
| 天劫 | 仅突破大境时出现；成功则继续，失败才死 |
| 其它死法 | 恶斗、意外骰、走火扣血、自绝 |
| 轮回带走 | 死物、经验、技能、属性，但有**空间格 / 技能槽 / 折损**，不是全额搬走 |
| 轮回留下 | 同行（活物）、超格死物与超槽技能、本世 `trib_run` |
| 操作 | 三选一或 `use` 死物；战斗自动 |
| 内容 | 引擎锁上限；Agent 填词与效果串 |
| 开局 | 系统空间（hub）确认后 `start` 新一世 |
| 经历 | 每层锁定大纲；本世可查；轮回写入系统前世录 |

## 架构

```
skills/xiuxian/
  SKILL.md
  reference.md              # 世界观、36 物品类型、40 物品效果、42 技能 kind
  README.md
  VERSION                   # 1.0.0
  CHANGELOG.md
  templates/xiuxian_engine.py
  tests/test_engine.py
```

运行态：`.xiuxian/`（模板拷引擎 + `state.json`）。根 README 加一行；`.gitignore` 加 `.xiuxian/`。

用户可见 stdout 必须包在 `=== XIUXIAN_UI_BEGIN ===` … `END`。`draft` / `help` 无标记。

## 状态机

```
无 state ──init──► hub ──start──► composing ──inscribe──► choosing ──choose/use──► composing …
                      ▲                                         │
                      │                                         ├─身死/自绝──► ended
                      │                                         │
                      └──── next（系统轮回结算）◄────────────────┘
```

hub 对外是【系统空间】。没有「飞升结束」。

| 状态 | 允许 | 拒绝 |
|------|------|------|
| 无 state | `init`、`help` | 其余 |
| `hub` | `init` 重绘、`start`、`info`、`recall`、`help` | `draft`/`choose`/`use`/`giveup`/`next`/`log` |
| `composing` | `draft`、`inscribe`、`giveup`、`help`、`recall`；`pending_log` 时还可 `log` | `info`/`choose`/`use`/`start`/`next` |
| `choosing` | `info`、`choose`、`giveup`、`help`、`recall`；非天劫层可 `use` | `draft`/`inscribe`/`start`/`next`/`log`；天劫层 `use` |
| `ended` | `info`、`next`、`help`、`recall`；`pending_log` 时还可 `log` | `start`（须先 `next`） |

`init` 在 run / ended 中不覆盖，stderr `ERROR`。

`next`（仅 `ended`）：按「轮回结算」写入 `meta`，`run=null`，回 hub。UI 列出带走/留下。

## 一世怎么走

`floor` 从 1 起，**无上限**。只要没进 `ended`，就继续下一层。

进入一层时引擎决定 `node_type`：

1. 若 `meta.exp` 已达**下一境**阈值，且 `run.realm` 还没升上去 → 本层强制 `tribulation`（突破天劫）  
2. 否则：奇数层 `event`，偶数层 `event_battle`

境界由经验决定（第一世从 0 炼气）：

| 境界 | 经验阈值（达到则可突破） |
|------|--------------------------|
| 炼气 | 0 |
| 筑基 | 50 |
| 金丹 | 120 |
| 元婴 | 220 |
| 化神 | 350 |

化神之后不再刷天劫节点；层数仍继续，敌人按层数涨。第一版没有飞升节点。

每层活着结束：`meta.exp += 5 + insight之和`；无战斗再 `+ sage之和`；用过 ward/skip/mirror 再 `+ scavenger之和`；打赢再 `+ 5 + hunt之和`。

开局（第一世）：气血 20/20，攻 3，灵气 0，行囊空，同行空，技能空，`trib_run=0`。  
之后每世 `start`：用 `meta` 里的上限/攻/灵气/死物/技能/经验；同行清空；当前气血=上限；`floor=1` 新种子可指定。

钳制：气血 `[0, max_hp]`；灵气 `[0, 99 + meridians之和]`；攻最低 1。`max_hp` 不另设硬顶。本层若有 `dawn`，攻在本层结算与战斗中再临时 +n，进下一层清掉。

## 一层时序

1. 定 `node_type`，掷三槽角色与上限（天劫层不掷），`composing`。  
2. `draft` → `inscribe`（必须带 `--outline` 本层大纲）。  
3. `choosing`：出 UI。  
4. `choose` 或 `use`（天劫只能 `choose`）。  
5. 套用效果 → 意外骰（若有）→ 需要则战斗 → 致死规则。引擎写入本层 `facts`，`pending_log=true`。  
6. `pending_log=true`。Agent 用 `log --after` 写结局大纲；若直接去下一层 `draft`/`inscribe` 或 `next`，引擎先填机械句，大纲不会缺。  
7. 活：天劫成功则升境；`floor += 1` 回步骤 1。  
8. 死：`ended`；记下 `death_cause`。`log` 仍可补，否则 `next` 时机械填。

禁止 Agent 编第四条剧情出路。效果以锁进引擎的为准。之后写奇遇不得与已存大纲矛盾。

## 经历大纲

系统把每一层经历锁进 `run.chronicle`，不靠 Agent 记忆。大纲是短句，不是全文副本。

**开场大纲** `inscribe --outline O`  
去空白后 20～80 字。缺省或超长 → `inscribe` 失败。天劫层同样要。只写本层钩子（何地、何人、何险），不要剧透未选选项的数字。

**结局大纲** `log --after A`  
在 `pending_log` 时调用（结算后、下一层 `inscribe` 前，或 `ended` 尚未 `next`）。20～80 字。不写则引擎在下一步动作前用机械句填上，例如 `选2；气血16/24；战胜；下层`。同一层只能写一次。

**引擎 facts**（自动，不可改）  
`floor`、`node`、`realm`、`act`（`choose:n` 或 `use:uid`）、气血/攻/灵气快照、是否开战、是否胜利、`death_cause` 或空。

一条记录：

```
{floor, node, realm, setup, act, facts, after}
```

`choose`/`use`/`giveup` 结算时立刻追加一条：`setup` 来自本层 `--outline`，`facts`/`act` 由引擎写，`after` 先空。然后 `pending_log=true`。

`run.chronicle` 本世按层追加；超过 **40** 条丢掉最旧。

**何时必须落 `after`**

- Agent 调用 `log --after` → 写入并清 `pending_log`  
- 仍 `pending_log` 时若调用下一层 `draft`/`inscribe`，或 `ended` 时 `next`：引擎先填机械句再继续  

**轮回** `next`：把本世打成一条前世，写入 `meta.lives`：

- `cycle`、`death_cause`、`realm`、`floors`（死时 floor）  
- `digest`：引擎生成 「第N世 · 境界 · 历X层 · 死于Y」（再拼最后一条 `after` 前 20 字）  
- `entries`：本世 **最后 15 条** chronicle  

`meta.lives` 最多 **8** 世，更旧的整世丢掉。这是系统日志（死数据），不是活物，允许带走、允许翻看。

**查阅**

- `draft`（无 UI 标记）附带：本世最近 3 条 `setup/after`，以及上一世 `digest`（若有），供 Agent 接戏  
- `recall`：有 UI 标记；hub 列出前世 digest；run/ended 列出本世 chronicle（被截断会注明）  

SKILL：写新奇遇不得推翻已锁大纲（人死不能写活、已得之物不能当没拿）。大纲里可以提到前世同行，那是记忆，不是把活物带回来。

## 死因

`run.death_cause`（`ended` 时必有）：

| 值 | 何时 |
|----|------|
| `combat` | 打架扣到 0（续命没救下） |
| `accident` | 意外骰中了（即使当时气血 > 0） |
| `backlash` | 走火类扣血到 0（如 `spark` / 金蝉） |
| `tribulation` | 突破天劫失败 |
| `given_up` | `giveup` |

续命不救天劫、不救意外、不救自绝。只救「气血要变成 0」的那一下。

## 效果语法

原子（去空白；`grant`/`ally`/`skill` 三条里最多出现一种，且彼此不同时出现）：

| 原子 | 含义 |
|------|------|
| `hp±N` `atk±N` `qi±N` `maxhp+N` | 属性 |
| `battle` | event 层选了会打 |
| `accident:p=N` | N 为 5～40；本层结算后掷 `1～100`，`<=N` 则意外身死 |
| `grant:type=T:fx=E:n=N:name=NAME` | 死物进包（类型与效果分开） |
| `ally:bond=B:n=N:name=NAME` | 活物同行（本世） |
| `skill:kind=K:n=N:name=NAME` | 技能进列表（可轮回） |

`NAME` 长度 2～8。每种数值原子每条最多一次。

**SAFE**：禁止 `battle`、`hp-`、`accident`、`atk+>1`；`grant` 的 `type` 须在类型表、`fx` 仅 `{hp,qi,maxhp,ward,iron,luck_floor,exp,fullhp,barrier,meridians_now,dawn_fight,sight,rest,insight_now}`；`ally` 仅 partner n=1；`skill` 仅 `{breath,qi_flow,guard,meditation,meridians,sage,dawn,spark_ward}`。至少一项有效收益。

**GREEDY**：必须 `atk+`（≤上限）且有风险（`battle` 或 `hp-≥3` 或 `accident`）；`grant` 的 `fx` 仅 `{atk,spark,bomb,second,weaken,poison,haste,frenzy_fight,drain_fight,thunder_fight,pack_fight,ward,mirror,bait,blood_price_fight,execute_fight,vigor_fight}`；`ally` 仅 beast 1～3；`skill` 仅 `{sword,thunder,drain,hunt,frenzy,vigor,execute,poison,haste,blood_price,weaken,leech_qi}`。

**WEIRD**：禁止 `atk+>2`；须有 qi 变化或 grant/ally/skill/maxhp 或（hp- 且 qi+）；`accident` 可选；`ally` 三种都行；`skill` 任意；`grant` 的 `type`/`fx` 均可为全表。

天劫层：不要 `--e*`，只交文案。

`accident` 骰：`random.Random(seed + 80000 + floor).randint(1, 100)`。中了则 `ended`，`death_cause=accident`，本层 grant/ally/skill 仍先结算再判定（已进包的死物能轮回带走）。

## 技能（可轮回）

功法/神通，**全程被动**，不能 `use`。Agent 起名；`kind` 必须在下表。同类 n 相加。未知 kind → `inscribe` 失败。

**回复 / 资源**

| kind | UI | n | 效果 |
|------|----|---|------|
| `breath` | 吐纳 | 1～3 | 进新层气血 +n |
| `qi_flow` | 聚灵 | 1～2 | 进新层灵气 +n |
| `meditation` | 入定 | 1～3 | 本层**没打架**则结束时再气血 +n |
| `meridians` | 经脉 | 2～10 | 灵气上限改为 `99+n` |
| `regen` | 战愈 | 1～2 | 战斗每轮开始（灵兽前）你 +n 血 |
| `leech_qi` | 抽灵 | 1 | 你每刀灵气 +n |
| `dawn` | 晨曦 | 1～2 | 本层攻临时 +n，出层清掉 |
| `spark_ward` | 避火 | 1～4 | `spark`/`mirror` 扣血减少 n（最低 0） |

**输出**

| kind | UI | n | 效果 |
|------|----|---|------|
| `sword` | 攻伐 | 1～2 | 每刀 +n |
| `thunder` | 雷引 | 1～3 | 本场你第一刀再 +n |
| `drain` | 噬血 | 1 | 每刀回 n 血 |
| `reflect` | 反噬 | 1～2 | 敌实际打掉你血后，敌掉 n |
| `frenzy` | 狂化 | 1～3 | 当前血 ≤ 上限一半时每刀 +n |
| `vigor` | 气盛 | 1～2 | 当前血 ≥ 上限一半时每刀 +n |
| `execute` | 斩杀 | 1～3 | 敌当前血 ≤ `4*n` 时每刀再 +n |
| `poison` | 淬毒 | 1～2 | 第二轮起，每轮灵兽前敌掉 n |
| `haste` | 连斩 | 1 | 每轮你固定多一刀（与道具 `second` 不叠第二下，有一即可） |
| `blood_price` | 燃血 | 1～3 | 你每刀先扣 1 血，伤害 +n；扣死走致死 |
| `weaken` | 破甲 | 2～6 | 开战敌血 -n（最低 1） |
| `pack` | 御兽 | 1～2 | 每只灵兽那一下 +n |

**生存**

| kind | UI | n | 效果 |
|------|----|---|------|
| `guard` | 护体 | 1 | 敌每下 -1 |
| `step` | 身法 | 1 | 无视敌第一下 |
| `slow` | 滞空 | 1～2 | 敌攻 -n（最低 1） |
| `freeze` | 冰封 | 1 | 敌第 2、4、6… 下伤害为 0 |
| `barrier` | 护盾 | 2～8 | 本场先吸收 n 点伤害再扣血 |
| `dusk` | 夜行 | 1 | **偶数层**敌每下再 -n |
| `last_stand` | 残息 | 1 | 每场战斗第一次本要扣到 0 时留 1 血（只救战斗；续命丹优先于它） |
| `brother` | 结义 | 1 | 每名伙伴的助攻 n 再 + 本技能 n |

**气运 / 修为 / 轮回**

| kind | UI | n | 效果 |
|------|----|---|------|
| `insight` | 悟性 | 1～2 | 每层活着 +n 经验 |
| `hunt` | 猎魔 | 2～5 | 打赢 +n 经验 |
| `sage` | 苦修 | 1～3 | 本层没打架 +n 经验 |
| `scavenger` | 拾荒 | 1～3 | 本层用过 ward/skip/mirror +n 经验 |
| `will` | 道心 | 5～15 | 天劫三项 raw +n |
| `brute` | 霸体 | 5～15 | 只加**硬渡** raw |
| `shell_heart` | 金钟 | 5～15 | 只加天劫**护体** raw |
| `tranquil` | 镇心 | 5～15 | 只加**心魔问道** raw |
| `luck` | 气运 | 5～15 | 意外有效 p 减去 n |
| `danger` | 危机 | 1 | 本世第一次本要命中的意外改为未中（一次性） |
| `oath` | 双修 | 2～6 | 每名道侣再给天劫 raw +n |
| `pouch` | 扩容 | 1 | 轮回死物格 +n |
| `memory` | 残忆 | 1 | 轮回经验留八成而非七成 |
| `vessel` | 道器 | 1 | 轮回属性留九成而非八成 |

共 42 个 kind。`haste`/`last_stand`/`danger`/`pouch`/`memory`/`vessel`/`step`/`freeze`/`dusk`/`guard`/`drain`/`leech_qi` 的 n 只能取表中那一档（多为 1）。

- `uid`：`s` + 递增；一世不限条数；轮回仍 3 槽  
- 稳槽不得给 GREEDY 那张输出表，也不得 `will`/`hunt`/`pouch`/`memory`/`vessel`

意外有效 p：`max(0, 选项p - luck之和)`。若掷中且尚未用过 `danger`：视为未中，标记已用。骰仍 `seed+80000+floor`。

## 道具（死物，可轮回）

一条死物 = **类型**（它是什么）+ **效果**（它做什么）+ 名字 + n。  
`grant:type=T:fx=E:n=N:name=NAME`  
未知 T 或 E → `inscribe` 失败。  
第一版**不校验**「丹必须配药、符必须配术」——那是 `reference.md` 文案要求，避免 36×40 矩阵。UI 必须两维都写出来：`蛇丹(p1)[丹药/回气] 气血+8`。

行囊存 `{uid,type,fx,n,name}`。一世不限件；轮回按 n 裁格。

### 类型表（36，只影响分类文案）

| type | UI |
|------|-----|
| `dan` | 丹药 |
| `fu` | 符箓 |
| `qi` | 法器 |
| `cai` | 灵材 |
| `jian` | 兵刃 |
| `jia` | 甲胄 |
| `zhu` | 宝珠 |
| `yin` | 印玺 |
| `jing` | 宝镜 |
| `zhong` | 钟鼎 |
| `fan` | 灵幡 |
| `ling` | 令牌 |
| `yu` | 玉简 |
| `tu` | 舆图 |
| `jiu` | 灵酒 |
| `xiang` | 香烛 |
| `huan` | 戒环 |
| `pei` | 玉佩 |
| `gu` | 枯骨 |
| `ping` | 瓶罐 |
| `zhen` | 阵盘 |
| `shi` | 灵石 |
| `lu` | 丹炉 |
| `nang` | 香囊 |
| `du` | 毒剂 |
| `cha` | 灵茶 |
| `zhou` | 咒片 |
| `xue` | 凝血 |
| `ta` | 宝塔 |
| `deng` | 长明灯 |
| `shu` | 残页 |
| `suo` | 锁链 |
| `wei` | 帷幔 |
| `guan` | 冠冕 |
| `dai` | 束带 |
| `pao` | 道袍 |

### 效果表（40）

**被动（不能 `use`）**

| fx | UI | n | 何时 |
|----|----|---|------|
| `revive` | 续命 | 1 | 本世第一次气血归零留 1 血；不救天劫/意外/自绝 |

**主动：改属性（`event` 不打，`event_battle` 仍打）**

| fx | UI | n | 使用 |
|----|----|---|------|
| `hp` | 回气 | 4～12 | 气血 +n |
| `qi` | 补灵 | 1～5 | 灵气 +n |
| `atk` | 增攻 | 1～3 | 攻 +n |
| `maxhp` | 炼体 | 2～6 | 上限与当前 +n |
| `spark` | 走火 | 2～6 | 灵气 +n，血 -3（先减 `spark_ward`） |
| `fullhp` | 回满 | 1 | 气血 = 上限 |
| `exp` | 顿悟 | 3～10 | 立刻 `meta.exp +n` |
| `luck_floor` | 避凶 | 5～15 | 本层意外有效 p 再 -n（出层清） |
| `meridians_now` | 通脉 | 2～10 | 本世灵气上限 +n |
| `trib` | 祭天 | 5～15 | 本世 `trib_run +n`（上限累计 20） |
| `dawn_fight` | 壮行 | 1～2 | 本层攻临时 +n |

**主动：跳过本层冲突**

| fx | UI | n | 使用 |
|----|----|---|------|
| `ward` | 避战 | 1 | 跳过三选项；不打 |
| `skip` | 遁走 | 1 | 跳过三选项；不打；进下一层 |
| `mirror` | 金蝉 | 1 | 跳过；不打；扣 4 血（先减 `spark_ward`） |

**主动：本场战斗修正（`event` 不打，`event_battle` 带修正打）**

| fx | UI | n | 使用 |
|----|----|---|------|
| `bomb` | 破军 | 1 | 敌开场血半 |
| `iron` | 铁衣 | 1 | 敌每下 -1 |
| `second` | 连击 | 1 | 你每轮多一刀（与技能 haste 不叠成三刀） |
| `barrier` | 护盾 | 2～8 | 本场吸收 n |
| `weaken` | 破甲 | 2～6 | 开战敌血 -n |
| `poison` | 淬毒 | 1～2 | 本场第 2 轮起敌每轮 -n |
| `haste` | 连斩 | 1 | 同 second |
| `freeze` | 冰封 | 1 | 本场敌偶数下 0 伤 |
| `slow` | 滞空 | 1～2 | 本场敌攻 -n |
| `drain_fight` | 噬血 | 1 | 本场你每刀回 n |
| `reflect_fight` | 反噬 | 1～2 | 本场反伤 n |
| `thunder_fight` | 雷引 | 1～3 | 本场你第一刀 +n |
| `step_fight` | 身法 | 1 | 本场无视敌第一下 |
| `pack_fight` | 御兽 | 1～2 | 本场灵兽 +n |
| `frenzy_fight` | 狂化 | 1～3 | 本场血半以下每刀 +n |
| `guard_fight` | 护体 | 1 | 本场敌每下再 -n |
| `double_exp` | 双倍 | 1 | 本层结束时把「层经验」×2 |
| `sight` | 天眼 | 1 | 本层意外有效 p = 0 |
| `rest` | 调息 | 4～8 | 不打；气血 +n |
| `bait` | 挑衅 | 1 | 本层**强制打架**（event 也打） |
| `qi_fight` | 抽灵 | 1 | 本场你每刀灵气 +n |
| `vigor_fight` | 气盛 | 1～2 | 本场血半以上每刀 +n |
| `execute_fight` | 斩杀 | 1～3 | 本场敌血 ≤4n 时每刀 +n |
| `insight_now` | 开悟 | 1～3 | 本层结束额外 +n 经验 |
| `last_stand_fight` | 残息 | 1 | 本场一次战斗续 1 血（同技能残息，每场仍只一次） |
| `blood_price_fight` | 燃血 | 1～3 | 本场你每刀先扣 1 血，伤害 +n |

`use --id`：非天劫、非 `revive`；消耗；结束本层三选项。本场修正写入 `run.fight_mods`（可多条），打完或跳过战后清空。  
技能被动与道具本场修正**同类相加**（例如技能 `guard` + 道具 `guard_fight`）。

拾荒 `scavenger` 统计本层是否 `use` 过 fx∈{ward,skip,mirror}。

## 同行（活物，不可轮回）

伙伴助攻、道侣回血+天劫、灵兽每轮咬。`next` 丢弃 allies。UI 写明活物未随轮回。

## 自动战斗

开战前：技能与本场 `fight_mods` 一并套用（`weaken`/`bomb`/`barrier` 等）。`bait` 使本层必打。`rest`/`ward`/`skip`/`mirror` 不打。`sight` 与 `luck_floor` 并入本层意外有效 p。

每轮：

1. `regen` 你回血；`poison` 从第 2 轮起扣敌血  
2. 灵兽各打：兽 n + `pack`  
3. 你一刀：基础 `atk + dawn + bonus + 伙伴(含结义) + sword`，再加 thunder（仅本场第一刀）、frenzy/vigor/execute、`blood_price` 的 +n；出刀前 `blood_price` 扣 1 血  
4. `drain` / `leech_qi`  
5. 若有技能 `haste` 或本场 `second`/`haste` 道具（只多 **一** 刀）：再一刀，无雷引  
6. 敌一刀：`slow`（技能+本场）后攻最低 1；`step`/`step_fight` 第一下 / `freeze` 偶数下 → 伤害 0；否则减铁衣、`guard`+`guard_fight`、偶数层 `dusk`；先打 `barrier` 再打血  
7. 实际扣你血 > 0 则 `reflect`  
8. 若此下要把你打到 0：先续命丹，再本场 `last_stand`

战报把触发过的 kind 写出来。敌人气血 `8 + 2*min(floor,40) + 4*realm_index`，攻 `2 + min(floor,40)//2 + realm_index`（炼气 0 … 化神 4），再叠 `weaken` / `bomb`。

## 天劫（只用于突破）

三项：硬渡 / 护体 / 心魔问道。

raw 加 `trib_run` + `will` + `oath×道侣数`，三项再分别加 `brute` / `shell_heart` / `tranquil`，然后钳制。

骰：`random.Random(seed + 90001 + floor).randint(1, 100)`。成功升境并继续；失败 `ended`/`tribulation`。不能 `use`。

## 轮回配额（系统如何把控带走量）

一世里可以乱捡；**卡在 `next` 那一下**。系统空间不是无底洞。玩家不用自己勾选（第一版不做「弃物」命令），引擎按规则裁，UI 必须列出带走 / 遗弃。

### 死物：空间格

`slot_cap = min(10, 4 + cycles + 死时技能中 pouch 的 n 之和)`  
`cycles` 用**结算前**的轮回次数（第一世刚死为 0，无扩容则最多 4 件）。有 `pouch` 先算进格数，再裁死物，再裁技能（扩容功法也可能被挤掉）。

保留规则：按 `n` 从大到小；`n` 相同则 `uid` 序号大的留下（后获得优先）。超出的遗弃，不进 `meta.inventory`。

保留件按 `uid` 序号升序写回，方便 UI 稳定。

### 技能：神识槽

固定 **3 槽**，不随轮回涨。同一套排序（`n` 大优先，同 n 留后学的）。超出遗弃。

### 经验：七成

`exp = (死时 exp * keep) // 10`。有 `memory` 则 `keep=8`，否则 `7`。

若折损后 `exp` 低于当前 `realm` 的阈值，把 `realm` 降到「阈值 ≤ 新 exp」的最高一境。系统词：肉身新生，修为打滑。仍可能留在原境（只是离下一破境更远）。

### 属性：八成，保底开局

死时快照后（有 `vessel` 则分子为 9，否则 8）：

- `max_hp = max(20, (max_hp * keep) // 10)`
- `atk = max(3, (atk * keep) // 10)`
- `qi = (qi * keep) // 10`（可为 0）

新一世当前气血 = 新的 `max_hp`。

### 不带走（全弃）

同行；`trib_run`；`fight_mods`；本世 `floor` 与种子。

本世 `run.chronicle` **数字化**：按「经历大纲」打进 `meta.lives`，不是遗弃。活物本身仍不跟来。

---

hub UI：格数 `已用/slot_cap`、技能 `已用/3`、经验、折损后属性、轮回次数。

`ended` 的 `info`：死因 + 「待轮回」预览（按上面规则算一遍，尚未写入 meta）。`next` 才落盘并 `cycles += 1`。

`start`：灌入已裁过的 meta；`allies=[]`；`floor=1`。

若新一世经验仍 ≥ 下一境阈值（折损后极少见），第一层仍可以是天劫。

## 引擎命令

`python .xiuxian/xiuxian_engine.py <cmd>`

| 命令 | 作用 |
|------|------|
| `init` | 见状态机 |
| `start` | 仅 hub；可选 `--seed N` |
| `draft` | composing；天劫层给三策略成功率 |
| `inscribe` | 必填 `--outline`；非天劫要 `--e1/e2/e3`；天劫不要 `--e*`。若仍 `pending_log`，先机械填 `after` 再写本层 |
| `choose --n 1\|2\|3` | choosing；结算后追加 chronicle，`pending_log=true` |
| `use --id UID` | choosing 且非天劫；同上追加 chronicle |
| `log --after A` | `pending_log` 时写本层结局大纲，清标记 |
| `recall` | hub / composing / choosing / ended：查本世或前世大纲（有 UI 标记） |
| `info` | hub / choosing / ended |
| `giveup` | 自绝；同样追加 chronicle |
| `next` | 仅 ended：若仍 `pending_log` 先机械填 `after`，再轮回写入 `meta.lives` |
| `help` | 无 UI 标记 |

无 `unlock`。

随机：层角色 `seed+f`；战斗 bonus `seed+1000*f+k`；意外 `seed+80000+f`；天劫 `seed+90001+f`。禁止未播种 `random`。

## 填词协议

`draft` 读角色、上限、行囊、同行、技能、境界、本层是否天劫/是否可能意外，以及本世最近 3 条大纲、上一世 digest。若仍 `pending_log`，先机械填 `after` 再给草稿（与 `inscribe` 同序，避免 Agent 接戏时缺结局）。  
功法名对得上 42 个技能 `kind`。死物必须 `type`+`fx` 都在表内；文案上丹对药、符对术，引擎不查搭配。不要把气运写成免疫一切意外。  
活物相遇点到为止。禁止贴 `draft`。

## 错误处理

非法状态、非法 `--e*`、缺 `--outline` 或超长、天劫 `use`、对 `revive`/`技能`/`同行` 执行 `use`、非 `pending_log` 时 `log`、`ended` 未 `next` 就 `start`：stderr 含 `ERROR`，state 不变。

## state.json

- `engine_version`：`1.0.0`  
- `status`  
- `meta`：`exp`、`realm`、`max_hp`、`atk`、`qi`、`inventory`、`skills`、`cycles`、`lives`（前世录，最多 8）  
- `run`：一世字段；`hub` 时 `null`；含 `death_cause`（仅 ended）、`fight_mods`、`inventory` 为 `{uid,type,fx,n,name}`、`outline`（本层已 inscribe、尚未进 chronicle）、`chronicle`、`pending_log`  
- 无 `shards` / `unlocks`

## 测试

- hub 为系统空间：有经验/轮回次数，无碎片店  
- `start --seed` 同 seed 第 1 层角色稳定；一世可 `floor>9` 仍 `composing`（夹具连过数层）  
- `accident:p=100` 夹具+固定 seed → `ended`，`death_cause=accident`，即使 hp>0  
- 恶斗致死 `combat`；`spark` 扣死 `backlash`；`giveup` → `given_up`  
- 未知 `skill:kind=foo` 拒绝；SAFE 带 `frenzy` 拒绝  
- 夹具 `pouch` n=1、cycles=0：`slot_cap=5`  
- 夹具 `danger`：第一次本应中的意外改为未中  
- 夹具 `luck` n=15 且 `accident:p=10`：有效 p=0，不因意外死  
- 夹具 `step`：战报敌人第一下伤害为 0  
- `grant:type=dan:fx=hp` 四件进本世行囊；未知 type 或 fx 拒绝；SAFE 的 `fx=bomb` 拒绝  
- 第一次轮回 `slot_cap=4`，夹具 6 件则 `next` 后 meta 只留 n 最高的 4 件，UI 有遗弃  
- 夹具 5 条技能，`next` 后 meta 只留 3 条  
- 死时 exp=100、max_hp=40、atk=10、qi=10：`next` 后 exp=70、max_hp=32、atk=8、qi=8；同行空；死物/技能按格带走  
- `ally` 不进 meta；`start` 新一世同行空，被保留的 `skill` 仍加伤害  
- 天劫层 `use` 失败；续命不救意外与天劫  
- 无 `unlock` 命令（或调用即 ERROR）
- `inscribe` 无 `--outline` 或不足 20 字 → ERROR；有 outline 则 choosing 后 `run.chronicle` 含该 `setup`
- `choose` 后 `pending_log=true`；`log --after` 写入 `after` 并清标记；未 `log` 就 `draft`/`inscribe`/`next` 则引擎填机械 `after`
- `next` 后 `meta.lives` 多一条，含 `digest` 与最多 15 条 `entries`；第 9 世轮回丢掉最旧一世
- `recall` 在 hub 能列出前世 digest；本世超 40 层时 chronicle 只留最近 40

## 验收

- README 能装 `xiuxian`  
- 先系统空间，再入一世  
- **不死就还能下一层**；没有飞升通关  
- 能意外死、能恶斗死、能渡劫失败死  
- 轮回后：死物不超过当时空间格、技能不超过 3；默认经验七成、属性八成保底（有残忆/道器则按技能改）；活物不在  
- `ended` 预览与 `next` 落盘一致  
- `draft` 不进用户可见回复
- 每层有开场大纲；结算后有结局大纲（Agent 或机械句）；轮回后能在系统空间翻前世录

## 风险

- 一世过长 → 敌人随层数与境界涨；玩家可 `giveup` 轮回  
- 属性无限膨胀 → 轮回打八成 + 敌人吃境界与层数；空间格限制死物堆叠  
- 活物被写成可轮回 → `next` 丢 allies，UI 写明  
- 玩家嫌系统乱丢 → 第一版按 n 自动裁，不做手工勾选
