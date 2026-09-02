# 修仙参考表

## 世界观

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

死物文案应让类型与效果相配，例如**丹对药、符对术**，避免出现语义别扭的组合；但这只是填词要求，**引擎不校验** type 与 fx 的搭配。

## 类型表（36，只影响分类文案）

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

## 效果表（规范标题为 40，逐行共 41 个 key）

### 被动（不能 `use`）

| fx | UI | n | 何时 |
|----|----|---|------|
| `revive` | 续命 | 1 | 本世第一次气血归零留 1 血；不救天劫/意外/自绝 |

### 主动：改属性（`event` 不打，`event_battle` 仍打）

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

### 主动：跳过本层冲突

| fx | UI | n | 使用 |
|----|----|---|------|
| `ward` | 避战 | 1 | 跳过三选项；不打 |
| `skip` | 遁走 | 1 | 跳过三选项；不打；进下一层 |
| `mirror` | 金蝉 | 1 | 跳过；不打；扣 4 血（先减 `spark_ward`） |

### 主动：本场战斗修正（`event` 不打，`event_battle` 带修正打）

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

## 技能（可轮回）

功法/神通，**全程被动**，不能 `use`。Agent 起名；`kind` 必须在下表。同类 n 相加。未知 kind → `inscribe` 失败。

### 回复 / 资源

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

### 输出

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

### 生存

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

### 气运 / 修为 / 轮回

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

## 大纲规则

- 开场大纲通过 `inscribe --outline` 提交，去空白后 20～80 字。
- 只写本层钩子（何地、何人、何险），不要剧透未选选项的数字。
- 结局大纲通过 `log --after` 提交，长度同为 20～80 字。
- 新奇遇须承接已锁定大纲，不得自相矛盾：人死不能写活，已得之物不能当作未取得。
- 前世同行只能作为记忆提起，不能作为活物带回。

## 黑名单

- 飞升通关、仙界编制、门派日常、商店合成
- 第四战斗属性（根骨/身法当战斗轴）
- 把伙伴/道侣/灵兽写进系统空间或 next 带走
- 把 draft 或效果串原文当用户剧情朗读（UI 已有规范化效果行）
- 用「天劫」描写普通层意外
- 复用同一套三选项文案超过一层
