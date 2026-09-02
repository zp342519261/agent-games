# 修仙叙事节奏改版（xiuxian 1.1）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `xiuxian` 改成默认游历、关键才定夺；玩家牌面不露奖励数字与层号；游历可低频率给物。

**Architecture:** 仍是单一引擎 `skills/xiuxian/templates/xiuxian_engine.py`。`inscribe --mode travel|fork` 分叉：travel 当场结算并跳过 `choosing`；fork 进 `choosing` 但牌面只出三个短句。新增 `run.travel_looted` 锁连续游历给物。战斗/天劫/轮回公式不动。

**Tech Stack:** Python 3 stdlib、`unittest`、现有 `skills/xiuxian/` 布局。

**Spec:** `docs/superpowers/specs/2026-09-02-xiuxian-narrative-design.md`（覆盖玩家牌面与 `inscribe` 模式）；未写明处仍以 `docs/superpowers/specs/2026-09-01-xiuxian-design.md` 与现有引擎为准。

## Global Constraints

- 不改 `skills/nlhe/`、`skills/soup/` 任何文件
- 不改战斗公式、轮回裁剪、经验阈值、天劫成功率计算
- 引擎 stdlib only；骰子仍用已播种 `random.Random`
- UI 标记：`=== XIUXIAN_UI_BEGIN ===` / `=== XIUXIAN_UI_END ===`；`draft` / `help` 无标记
- 玩家 UI（有标记的 stdout）禁止：「层」「第N层」「进入下一层」、`SAFE`/`GREEDY`/`WEIRD`、成功率百分数、`气血+N` / `攻+N`、效果串原文
- `VERSION` 升到 **1.1.0**（在 Task 4 改，前三 Task 不要提前改 VERSION 测试）
- `git commit` / `git push` 仅在用户本轮明确同意后执行；未同意则做完文件改动后停下，跳过各 Task 的 Commit step
- 验证只跑本 plan 写明的命令；不要另写总结文档

## File map

| 文件 | 职责 |
|------|------|
| `skills/xiuxian/templates/xiuxian_engine.py` | `--mode`/`--gain`、travel 结算、去层号/去奖励牌面、`travel_looted` |
| `skills/xiuxian/tests/test_engine.py` | 新测 + 夹具 `--mode fork` + 改掉依赖旧牌面的断言 |
| `skills/xiuxian/SKILL.md` | 默认游历、定夺时机、禁止把数字/层号给玩家 |
| `skills/xiuxian/reference.md` | `inscribe` 模式与 travel `--gain` 白名单 |
| `skills/xiuxian/VERSION` | `1.1.0` |
| `skills/xiuxian/CHANGELOG.md` | 1.1.0 条目 |
| `skills/xiuxian/README.md` | 版本号与「游历 / 定夺」一句 |

---

### Task 1: `inscribe --mode` 必填 + 定夺牌面去数字

**Files:**
- Modify: `skills/xiuxian/tests/test_engine.py`（夹具与定夺/天劫 UI 断言）
- Modify: `skills/xiuxian/templates/xiuxian_engine.py`（`build_parser`、`validate_body`、`cmd_inscribe`、`_render_choosing`）

**Interfaces:**
- Consumes: 现有 `parse_effect` / `validate_effect` / `validate_outline` / `trib_chances`
- Produces: `--mode` 必填；`--gain` 参数存在但本 Task 定夺带 `--gain` 即 ERROR；fork 玩家行只有 `i. 短句`；`validate_body(body: str) -> str`（20～400）

- [ ] **Step 1: 夹具加上 `--mode fork`，并写失败测试**

在 `inscribe_ok` 的 argv 里，`"inscribe"` 后立刻插入 `"--mode", "fork"`。

所有手写 `inscribe` argv（`test_inscribe_requires_outline`、`test_outline_too_short`、`test_tribulation_rejects_effects_and_shows_chances`、`test_tribulation_info_repeats_each_strategy_chance`、`TestTribulation._inscribe_tribulation`）同样加上 `"--mode", "fork"`。

把过短天劫正文换成（≥20 字）：

```python
TRIB_BODY = "天劫云压顶，三道雷纹在识海里转。系统冷冰冰列出三条渡法。"
```

在 `TestInscribe` 增加：

```python
    def test_inscribe_requires_mode(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        roles = [s["role"] for s in st["run"]["slots"]]
        code, _, err = run(
            [
                "inscribe",
                "--outline", OUTLINE,
                "--body", "矿洞深处三盏灯摇晃，像在等人选路。风里有铁锈和药味。",
                "--c1", "走近左灯",
                "--c2", "走近中灯",
                "--c3", "走近右灯",
                "--e1", _e_for(roles[0]),
                "--e2", _e_for(roles[1]),
                "--e3", _e_for(roles[2]),
            ]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(xx.load_state()["status"], "composing")

    def test_fork_ui_hides_roles_and_rewards(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, out, err = inscribe_ok()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("1. 走近左灯", out)
        self.assertIn("2. 走近中灯", out)
        self.assertIn("3. 走近右灯", out)
        self.assertNotIn("SAFE", out)
        self.assertNotIn("GREEDY", out)
        self.assertNotIn("WEIRD", out)
        self.assertNotIn("气血+", out)
        self.assertNotIn("%", out)
        self.assertEqual(xx.load_state()["status"], "choosing")
```

把 `test_tribulation_rejects_effects_and_shows_chances` 成功路径断言从 `assertIn("成功率", out)` 改成：

```python
        self.assertIn("1. 硬渡", out)
        self.assertNotIn("成功率", out)
        self.assertNotIn("%", out)
```

把 `test_tribulation_info_repeats_each_strategy_chance` 三行成功率断言改成：

```python
        self.assertIn("1. 硬渡", out)
        self.assertIn("2. 护体", out)
        self.assertIn("3. 心魔问道", out)
        self.assertNotIn("成功率", out)
        self.assertNotIn("%", out)
```

- [ ] **Step 2: 跑测试，确认新测失败、旧夹具因缺 `--mode` 参数也失败**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestInscribe.test_inscribe_requires_mode TestInscribe.test_fork_ui_hides_roles_and_rewards -v
```

Expected: FAIL 或 argparse `ERROR`（尚未登记 `--mode`）。

- [ ] **Step 3: 实现 parser、正文长度、fork 牌面**

`build_parser` 的 `inscribe` 增加：

```python
    ins.add_argument("--mode", default=None, choices=("travel", "fork"))
    ins.add_argument("--gain", default=None)
```

在 `validate_outline` 旁增加：

```python
def validate_body(body: str) -> str:
    body = body.strip()
    if not 20 <= len(body) <= 400:
        raise ValueError("body 长度须为 20～400")
    return body
```

改 `cmd_inscribe`：开头在 `try` 里先：

```python
        if args.mode not in ("travel", "fork"):
            raise ValueError("必须指定 --mode travel 或 fork")
        outline = validate_outline(args.outline)
        body = validate_body(args.body)
        if args.mode == "travel":
            raise ValueError("游历模式尚未接线")  # Task 2 立刻删掉这行并接真实 travel
        if args.gain:
            raise ValueError("定夺不能带 --gain")
```

Fork 分支：非天劫仍校验三个 `--e*`；天劫仍拒绝 `--e*`。**玩家行不要角色、不要 `fmt_effect`、不要成功率：**

```python
            effect_lines = [
                f"{i}. {choice['text']}"
                for i, choice in enumerate(choices, 1)
            ]
```

`_render_choosing` 两边都改成同样格式（天劫也不拼成功率）。

本 Task **不要**实现 travel 结算；`--mode travel` 暂时走上面的 `ValueError`，Task 2 替换。

- [ ] **Step 4: 跑 Task 1 相关测试**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestInscribe TestStartDraft TestTribulation -v
```

Expected: 全部 PASS。`test_inscribe_ok_goes_choosing` 仍为 `choosing`。

- [ ] **Step 5: Commit**（仅当用户本轮明确要求提交时）

```bash
git add skills/xiuxian/tests/test_engine.py skills/xiuxian/templates/xiuxian_engine.py
git commit -m "$(cat <<'EOF'
feat(xiuxian): require inscribe --mode and hide fork rewards

EOF
)"
```

---

### Task 2: 空窗游历（无 `--gain`）

**Files:**
- Modify: `skills/xiuxian/tests/test_engine.py`（新增 `TestTravel`）
- Modify: `skills/xiuxian/templates/xiuxian_engine.py`（`new_run`、`cmd_inscribe` travel 分支、抽出结算）

**Interfaces:**
- Consumes: Task 1 的 `--mode` / `validate_body`
- Produces: `new_run` 含 `travel_looted: False`；`inscribe --mode travel` 无 `--c*`/`--e*`/`--gain` 时当场结算，`status=composing`，`floor+=1`，`chronicle[-1]["act"]=="travel"`，stdout 仅 `--body`；天劫 travel → ERROR 且 status 仍 `composing`

- [ ] **Step 1: 写失败测试**

在 `test_engine.py` 增加常量与 helper（与 `inscribe_ok` 同级）：

```python
BODY = "矿洞深处三盏灯摇晃，像在等人选路。风里有铁锈和药味。"


def travel_ok(gain: str | None = None) -> tuple[int, str, str]:
    args = [
        "inscribe",
        "--mode", "travel",
        "--outline", OUTLINE,
        "--body", BODY,
    ]
    if gain:
        args.extend(["--gain", gain])
    return run(args)
```

（若运行环境是 3.9，把 `str | None` 写成 `Optional[str]`，文件顶部已有 `from __future__ import annotations` 则 `str | None` 可用。）

新增 class：

```python
class TestTravel(CwdTest):
    def test_travel_without_gain_skips_choosing(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, out, err = travel_ok()
        self.assertEqual((code, err), (0, ""))
        self.assertIn(BODY, out)
        self.assertNotIn("1. ", out)
        self.assertNotIn("层", out)
        self.assertNotIn("气血+", out)
        st = xx.load_state()
        self.assertEqual(st["status"], "composing")
        self.assertEqual(st["run"]["floor"], 2)
        self.assertEqual(st["run"]["chronicle"][0]["act"], "travel")
        self.assertTrue(st["run"]["pending_log"])
        self.assertFalse(st["run"]["travel_looted"])

    def test_travel_rejects_options(self):
        run(["init"])
        run(["start", "--seed", "1"])
        before = xx.load_state()
        code, _, err = run(
            [
                "inscribe",
                "--mode", "travel",
                "--outline", OUTLINE,
                "--body", BODY,
                "--c1", "走近左灯",
            ]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(xx.load_state(), before)

    def test_tribulation_rejects_travel(self):
        run(["init"])
        st = xx.load_state()
        st["meta"]["exp"] = 50
        xx.save_state(st)
        run(["start", "--seed", "1"])
        self.assertEqual(xx.load_state()["run"]["node_type"], "tribulation")
        before = xx.load_state()
        code, _, err = travel_ok()
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        after = xx.load_state()
        self.assertEqual(after["status"], "composing")
        self.assertEqual(after["run"]["floor"], before["run"]["floor"])
        self.assertEqual(after["run"]["node_type"], "tribulation")

    def test_event_battle_travel_does_not_fight(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        st["run"]["floor"] = 2
        xx.enter_floor(st)
        xx.save_state(st)
        self.assertEqual(xx.load_state()["run"]["node_type"], "event_battle")
        code, _, err = travel_ok()
        self.assertEqual((code, err), (0, ""))
        st = xx.load_state()
        self.assertEqual(st["run"]["chronicle"][0]["node"], "event_battle")
        self.assertEqual(st["run"]["chronicle"][0]["act"], "travel")
        self.assertNotIn("开战", st["run"]["chronicle"][0]["facts"])
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestTravel -v
```

Expected: FAIL（仍是「游历模式尚未接线」）。

- [ ] **Step 3: 实现空窗 travel**

`new_run` 增加 `"travel_looted": False`。

删除 Task 1 的 `raise ValueError("游历模式尚未接线")`。

在 `cmd_inscribe` 里，`mode == "travel"` 分支（天劫已在更前拒绝）：

```python
        if run["node_type"] == "tribulation" and args.mode == "travel":
            raise ValueError("天劫必须定夺，不能游历")

        if args.mode == "travel":
            if any(x.strip() for x in (args.c1, args.c2, args.c3)):
                raise ValueError("游历不能带 --c*")
            if any(effect is not None for effect in (args.e1, args.e2, args.e3)):
                raise ValueError("游历不能带 --e*")
            if args.gain:
                raise ValueError("游历收获尚未接线")  # Task 3 替换
            # 空窗结算见下
```

抽出（或内联）结算，**不要**调用 `fight` / `should_fight` / `resolve_accident`：

```python
def settle_travel(st: dict[str, Any], parsed: dict[str, Any] | None) -> None:
    run = st["run"]
    gained = None
    if parsed is not None:
        before = {
            "inventory": len(run["inventory"]),
            "allies": len(run["allies"]),
            "skills": len(run["skills"]),
        }
        apply_parsed(st, parsed, "travel+gain")
        for target in ("inventory", "allies", "skills"):
            if len(run[target]) > before[target]:
                gained = run[target][-1]
                break
        act = "travel+gain"
        effect_label = parsed.get("_raw", "gain")
    else:
        act = "travel"
        effect_label = "travel"
    _apply_floor_end_passives(run)
    facts = _facts_text(run, effect_label, gained, None)
    append_chronicle(st, act, facts)
    _award_floor_exp(st)
    run["travel_looted"] = parsed is not None
    advance_or_end(st)
```

空窗路径：`ensure_after(st)` → `run["outline"]=outline` → `run["body"]=body` → `settle_travel(st, None)` → `save_state` → `emit_ui(body)`。不要进 `choosing`。

本 Task `parsed` 恒为 `None`，因此 `travel_looted` 结算后为 `False`。

- [ ] **Step 4: 跑测试**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestTravel TestInscribe TestTribulation TestStartDraft -v
```

Expected: 全部 PASS。

- [ ] **Step 5: Commit**（仅当用户本轮明确要求提交时）

```bash
git add skills/xiuxian/tests/test_engine.py skills/xiuxian/templates/xiuxian_engine.py
git commit -m "$(cat <<'EOF'
feat(xiuxian): settle travel years without a three-choice fork

EOF
)"
```

---

### Task 3: 游历 `--gain` 与连续空窗

**Files:**
- Modify: `skills/xiuxian/tests/test_engine.py`（`TestTravel` 增测）
- Modify: `skills/xiuxian/templates/xiuxian_engine.py`（`validate_travel_gain`、travel `--gain`、`cmd_choose`/`cmd_use` 清 `travel_looted`）

**Interfaces:**
- Consumes: `parse_effect`、`SAFE_GRANT_FX`、`SAFE_SKILLS`、`settle_travel`
- Produces: `validate_travel_gain(parsed: dict[str, Any]) -> None`；合法 `--gain` 写入行囊/同行/功法且 `act=="travel+gain"`；连续两段 travel 都带 `--gain` → ERROR；空 travel 或一次 `choose`/`use` 结算后允许再给；`--gain` 含 `battle` 或 GREEDY skill → ERROR 且 state 不变

- [ ] **Step 1: 写失败测试**

```python
GAIN_SAFE = "grant:type=dan:fx=hp:n=8:name=蛇丹"


    def test_travel_gain_grant_then_blocks_consecutive(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, out, err = travel_ok(GAIN_SAFE)
        self.assertEqual((code, err), (0, ""))
        self.assertIn(BODY, out)
        st = xx.load_state()
        self.assertEqual(len(st["run"]["inventory"]), 1)
        self.assertEqual(st["run"]["inventory"][0]["name"], "蛇丹")
        self.assertTrue(st["run"]["travel_looted"])
        self.assertEqual(st["run"]["chronicle"][0]["act"], "travel+gain")
        before = xx.load_state()
        code, _, err = travel_ok(GAIN_SAFE)
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(xx.load_state(), before)

    def test_empty_travel_then_gain_allowed(self):
        run(["init"])
        run(["start", "--seed", "1"])
        travel_ok(GAIN_SAFE)
        travel_ok()
        code, _, err = travel_ok("ally:bond=partner:n=1:name=阿青")
        self.assertEqual((code, err), (0, ""))
        st = xx.load_state()
        self.assertEqual(st["run"]["allies"][-1]["name"], "阿青")

    def test_fork_breaks_travel_loot_streak(self):
        run(["init"])
        run(["start", "--seed", "1"])
        travel_ok(GAIN_SAFE)
        inscribe_ok()
        force_effects("hp+4", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])
        code, _, err = travel_ok(GAIN_SAFE)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(xx.load_state()["run"]["inventory"]), 2)

    def test_travel_gain_rejects_battle_and_greedy_skill(self):
        run(["init"])
        run(["start", "--seed", "1"])
        before = xx.load_state()
        code, _, err = travel_ok("battle")
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(xx.load_state(), before)
        code, _, err = travel_ok("skill:kind=sword:n=1:name=剑诀")
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(xx.load_state(), before)
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestTravel.test_travel_gain_grant_then_blocks_consecutive TestTravel.test_travel_gain_rejects_battle_and_greedy_skill -v
```

Expected: FAIL（仍是「游历收获尚未接线」或未解析 `--gain`）。

- [ ] **Step 3: 实现校验与接线**

```python
def validate_travel_gain(parsed: dict[str, Any]) -> None:
    if (
        parsed["battle"]
        or parsed["accident"]
        or parsed["hp"]
        or parsed["atk"]
        or parsed["qi"]
        or parsed["maxhp"]
    ):
        raise ValueError("游历收获只能是 grant/ally/skill")
    grant, ally, skill = parsed["grant"], parsed["ally"], parsed["skill"]
    kinds = [item for item in (grant, ally, skill) if item is not None]
    if len(kinds) != 1:
        raise ValueError("游历收获必须恰好一种")
    if grant and grant["fx"] not in SAFE_GRANT_FX:
        raise ValueError("游历道具效果不合法")
    if skill and skill["kind"] not in SAFE_SKILLS:
        raise ValueError("游历功法不合法")
    if ally:
        if ally["bond"] not in {"partner", "dao", "beast"}:
            raise ValueError("游历同行不合法")
        if ally["bond"] == "partner" and ally["n"] != 1:
            raise ValueError("游历伙伴 n 须为 1")
```

Travel 分支替换「尚未接线」：

```python
            parsed = None
            if args.gain:
                if run.get("travel_looted"):
                    raise ValueError("连续游历不能都给东西")
                parsed = parse_effect(args.gain.strip())
                validate_travel_gain(parsed)
            ensure_after(st)
            run["outline"] = outline
            run["body"] = body
            settle_travel(st, parsed)
            save_state(st)
            emit_ui(body)
            return
```

`cmd_choose` 两条路径（天劫与普通）在 `advance_or_end` 之前：`run["travel_looted"] = False`。

`cmd_use` 同样在 `advance_or_end` 之前清掉。

非法 `--gain` 必须在 `ensure_after` / 写 outline **之前** `die`，保证 `test_travel_gain_rejects_battle_and_greedy_skill` 的 state 全等。

- [ ] **Step 4: 跑测试**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestTravel TestInscribe TestChronicle.test_log_after_and_recall -v
```

Expected: 全部 PASS。

- [ ] **Step 5: Commit**（仅当用户本轮明确要求提交时）

```bash
git add skills/xiuxian/tests/test_engine.py skills/xiuxian/templates/xiuxian_engine.py
git commit -m "$(cat <<'EOF'
feat(xiuxian): allow sparse travel loot with a one-year gap

EOF
)"
```

---

### Task 4: 玩家 UI 去层号 + draft 字段 + SKILL 1.1.0

**Files:**
- Modify: `skills/xiuxian/tests/test_engine.py`（机械句、recall、start、choose、VERSION、SKILL 关键词）
- Modify: `skills/xiuxian/templates/xiuxian_engine.py`（start / choose / use / recall / ended / digest / mechanical_after / draft / help）
- Modify: `skills/xiuxian/SKILL.md`
- Modify: `skills/xiuxian/reference.md`
- Modify: `skills/xiuxian/VERSION`
- Modify: `skills/xiuxian/CHANGELOG.md`
- Modify: `skills/xiuxian/README.md`

**Interfaces:**
- Consumes: Task 2–3 的 travel / `travel_looted`
- Produces: 有 UI 标记的 stdout 不含「层」；机械句仅为「这一段游历结束」或「路已选定」；`draft` 含 `is_tribulation=`、`travel_looted=`、`travel_gain_ok=`；`ENGINE_VERSION`/`VERSION`=`1.1.0`

- [ ] **Step 1: 改旧断言并写新测**

`test_init_hub_ui_is_system_space` 的 `engine_version` 改 `"1.1.0"`。

`TestSkillDocs.test_version_file` 期望 `"1.1.0"`。

`test_skill_frontmatter_and_rules` 增加：

```python
        self.assertIn("--mode", text)
        self.assertIn("travel", text)
        self.assertIn("定夺", text)
```

`test_draft_fills_mechanical_after` 与 `test_giveup_fills_previous_pending_after_before_appending` 的机械句改成 `"路已选定"`。

在 `TestStartDraft` 增加：

```python
    def test_start_ui_has_no_floor_word(self):
        run(["init"])
        code, out, err = run(["start", "--seed", "1"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("新一世启程", out)
        self.assertNotIn("层", out)
```

在 `TestTravel` 或 `TestChronicle` 增加：

```python
    def test_choose_result_and_recall_hide_floor_and_rewards(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        force_effects("hp+4", "qi+3", "maxhp+2")
        code, out, err = run(["choose", "--n", "1"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("你选了：走近左灯", out)
        self.assertNotIn("层", out)
        self.assertNotIn("气血", out)
        self.assertNotIn("SAFE", out)
        code, out, _ = run(["recall"])
        self.assertIn("起：", out)
        self.assertIn("后：", out)
        self.assertNotIn("层", out)
        self.assertNotIn("行：", out)

    def test_draft_lists_travel_gain_flags(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, out, err = run(["draft"])
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn(xx.UI_BEGIN, out)
        self.assertIn("is_tribulation=0", out)
        self.assertIn("travel_looted=0", out)
        self.assertIn("travel_gain_ok=1", out)
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py TestStartDraft.test_start_ui_has_no_floor_word TestChronicle.test_draft_fills_mechanical_after TestSkillDocs.test_version_file -v
```

Expected: FAIL（仍是「第1层 · 待落墨」、旧机械句、VERSION 1.0.0）。

- [ ] **Step 3: 改引擎文案与 draft**

`ENGINE_VERSION = "1.1.0"`。

`cmd_start` 的 `emit_ui`：

```python
    emit_ui(
        "\n".join(
            [
                "【轮回系统】新一世启程",
                f"境界：{st['run']['realm']}",
            ]
        )
    )
```

`mechanical_after` 整函数换成：

```python
def mechanical_after(entry: dict[str, Any], run_snapshot: dict[str, Any]) -> str:
    act = entry.get("act") or ""
    if str(act).startswith("travel"):
        return "这一段游历结束"
    return "路已选定"
```

`_render_choice_result` 换成：

```python
def _render_choice_result(choice: dict[str, Any], death_cause: str | None) -> str:
    lines = [f"你选了：{choice['text']}"]
    if death_cause:
        lines.append(f"此世终结：{DEATH_LABEL[death_cause]}")
    return "\n".join(lines)
```

调用处改为 `_render_choice_result(choice, run["death_cause"])`，不要拼结算数字、不要「进入第N层」。

`cmd_use` 的 result_ui：

```python
    result_ui = f"已使用：{item['name']}"
    if run["death_cause"]:
        result_ui += f"\n此世终结：{DEATH_LABEL[run['death_cause']]}"
```

`_render_ended` 去掉 `层数：{run['floor']}`，保留境界与死因。

`_render_chronicle` 每条只输出：

```python
                f"起：{entry['setup'] or '无'}",
                f"后：{entry['after'] or '待补写'}",
```

`cmd_next` 的 digest 去掉 `历{run['floor']}层 · `，改为：

```python
    digest = f"第{meta['cycles'] + 1}世 · {run['realm']} · 死于{cause}"
```

`cmd_draft` 在现有行之后追加（天劫仍输出 `hard=`/`guard=`/`heart=`）：

```python
        f"is_tribulation={1 if run['node_type']=='tribulation' else 0}",
        f"travel_looted={1 if run.get('travel_looted') else 0}",
        f"travel_gain_ok={0 if run['node_type']=='tribulation' or run.get('travel_looted') else 1}",
```

`cmd_help` 补一句：`inscribe --mode travel|fork`；`draft / help` 仍无 UI 标记。

- [ ] **Step 4: 改 SKILL / reference / VERSION / CHANGELOG / README**

`VERSION` 文件内容改为 `1.1.0`。

`CHANGELOG.md` 顶部加：

```markdown
## 1.1.0

- 默认游历；关键情况与天劫才定夺
- 定夺牌面只出短句，不露奖励数字与成功率
- 玩家可见文案去掉层号；游历可低频率给物
```

`README.md` 版本改为 1.1.0；「使用」段改成先看游历、关键再选 1/2/3。

`SKILL.md` 必须写明：

- 默认 `inscribe --mode travel`（`--outline` + `--body`，可选 `--gain`）
- `--mode fork` 只用于破境、生死、立事、决裂/认人；天劫只能 fork，且不要 `--e*`
- 不要一世除天劫外零定夺
- 约十段游历里一两段带 `--gain`；收获写进 `--body`
- 玩家可见回复禁止：效果串、成功率、气血加减、「第几层」
- 定夺中 `info` 与牌面相同（无行囊数字）；`use --id` 的 uid 从 `draft` 读，代码块外用一句「要用行囊里的某某」
- 工作流改为：`start → draft → inscribe --mode travel|fork`；travel 后若 composing 则继续 draft；fork 才 `choose`/`use`
- 误把效果或层号给玩家：立刻再跑当前允许的 `info`/`recall` 覆盖

`reference.md`：

- 补 `inscribe --mode travel|fork` 与 travel `--gain` 白名单（与 spec 相同的 SAFE grant fx / SAFE skill / ally 规则）
- 删掉或改写「UI 已有规范化效果行」——定夺牌面不再有规范化效果行
- 黑名单加：把层号、成功率、效果串读给玩家

- [ ] **Step 5: 跑全量引擎测试**

Run:

```bash
python3 skills/xiuxian/tests/test_engine.py -v
```

Expected: 全部 PASS（含原有意外/天劫/轮回回归）。

- [ ] **Step 6: Commit**（仅当用户本轮明确要求提交时）

```bash
git add skills/xiuxian/templates/xiuxian_engine.py skills/xiuxian/tests/test_engine.py skills/xiuxian/SKILL.md skills/xiuxian/reference.md skills/xiuxian/VERSION skills/xiuxian/CHANGELOG.md skills/xiuxian/README.md
git commit -m "$(cat <<'EOF'
feat(xiuxian): hide floor numbers and document travel-first hosting

EOF
)"
```

---

## Spec coverage（自检）

| Spec 条目 | Task |
|-----------|------|
| `--mode` 必填；天劫不能 travel | 1–2 |
| travel 跳过 choosing；fork 进 choosing | 1–2 |
| travel 禁 `--c*`/`--e*` | 2 |
| `--gain` 恰好一种、SAFE 白名单、禁 battle | 3 |
| 连续两层 travel 不能都给；fork 打断 | 3 |
| `event_battle` travel 不自动开战 | 2 |
| 定夺/天劫牌面无效果、无成功率 | 1 |
| 玩家 UI 无「层」；recall 只 setup/after | 4 |
| 机械句无层号/气血/胜负 | 4 |
| `draft` 天劫标记与 travel 给物许可 | 4 |
| SKILL 默认游历、禁止数字 | 4 |
| VERSION 1.1.0 | 4 |
| 不改战斗/轮回/阈值 | 全局；回归在 Task 4 全量测试 |
