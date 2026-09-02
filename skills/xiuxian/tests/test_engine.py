from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import xiuxian_engine as xx


OUTLINE = "青州郊外废弃矿洞深处传来低语，洞口摆着三盏来历不明的灯。"


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            xx.run_cmd(argv)
    except SystemExit as e:
        code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


def _e_for(role: str) -> str:
    if role == "SAFE":
        return "hp+4"
    if role == "GREEDY":
        return "atk+2;hp-3"
    return "qi+3"


def inscribe_ok(st=None):
    st = st or xx.load_state()
    roles = [s["role"] for s in st["run"]["slots"]]
    args = [
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
    return run(args)


def force_effects(e1: str, e2: str, e3: str) -> None:
    st = xx.load_state()
    for choice, effect in zip(st["run"]["choices"], (e1, e2, e3)):
        choice["parsed"] = xx.parse_effect(effect)
    xx.save_state(st)


class CwdTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cwd = Path.cwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self.tmp.cleanup()


class TestInitHelp(CwdTest):
    def test_init_hub_ui_is_system_space(self):
        code, out, err = run(["init"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn(xx.UI_BEGIN, out)
        self.assertIn(xx.UI_END, out)
        self.assertIn("系统空间", out)
        self.assertIn("轮回次数：0", out)
        self.assertIn("经验：0", out)
        self.assertIn("炼气", out)
        self.assertNotIn("碎片", out)
        st = xx.load_state()
        self.assertEqual(st["status"], "hub")
        self.assertIsNone(st["run"])
        self.assertEqual(st["engine_version"], "1.0.0")
        self.assertEqual(st["meta"]["cycles"], 0)
        self.assertEqual(st["meta"]["lives"], [])

    def test_init_in_hub_redraws(self):
        run(["init"])
        code, out, _ = run(["init"])
        self.assertEqual(code, 0)
        self.assertIn("系统空间", out)

    def test_help_lists_slash_no_ui(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/修仙", out)
        self.assertNotIn(xx.UI_BEGIN, out)

    def test_unlock_is_error(self):
        run(["init"])
        code, _, err = run(["unlock"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_draft_without_state_errors(self):
        code, _, err = run(["draft"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)


class TestStartDraft(CwdTest):
    def test_start_seed_stable_roles(self):
        run(["init"])
        code, out, _ = run(["start", "--seed", "7"])
        self.assertEqual(code, 0)
        self.assertIn(xx.UI_BEGIN, out)
        st = xx.load_state()
        self.assertEqual(st["status"], "composing")
        self.assertEqual(st["run"]["seed"], 7)
        self.assertEqual(st["run"]["floor"], 1)
        self.assertEqual(st["run"]["node_type"], "event")
        roles_a = [s["role"] for s in st["run"]["slots"]]
        self.assertEqual(sorted(roles_a), ["GREEDY", "SAFE", "WEIRD"])
        st["status"] = "hub"
        st["run"] = None
        xx.save_state(st)
        run(["start", "--seed", "7"])
        st2 = xx.load_state()
        roles_b = [s["role"] for s in st2["run"]["slots"]]
        self.assertEqual(roles_a, roles_b)

    def test_init_during_run_errors(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, _, err = run(["init"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(xx.load_state()["status"], "composing")

    def test_draft_has_no_ui_marker(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, out, _ = run(["draft"])
        self.assertEqual(code, 0)
        self.assertNotIn(xx.UI_BEGIN, out)
        self.assertIn("node_type", out)
        self.assertIn("SAFE", out)
        self.assertIn("GREEDY", out)
        self.assertIn("WEIRD", out)

    def test_odd_even_node_types(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        self.assertEqual(st["run"]["node_type"], "event")
        st["run"]["floor"] = 2
        xx.enter_floor(st)
        self.assertEqual(st["run"]["node_type"], "event_battle")

    def test_start_not_from_ended(self):
        run(["init"])
        st = xx.load_state()
        st["status"] = "ended"
        st["run"] = xx.new_run(st["meta"], 1)
        st["run"]["death_cause"] = "combat"
        xx.save_state(st)
        code, _, err = run(["start"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)


class TestInscribe(CwdTest):
    def test_tables_match_required_sizes(self):
        self.assertEqual(len(xx.ITEM_TYPES), 36)
        # 规范标题写 40，但逐行共有 41 个 key；不能为凑数漏掉表中条目。
        self.assertEqual(len(xx.FX), 41)
        self.assertEqual(len(xx.SKILLS), 42)

    def test_inscribe_requires_outline(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        roles = [s["role"] for s in st["run"]["slots"]]
        code, _, err = run(
            [
                "inscribe",
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

    def test_outline_too_short(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        roles = [s["role"] for s in st["run"]["slots"]]
        code, _, err = run(
            [
                "inscribe",
                "--outline", "太短了",
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

    def test_inscribe_ok_goes_choosing(self):
        run(["init"])
        run(["start", "--seed", "1"])
        code, out, err = inscribe_ok()
        self.assertEqual(err, "")
        self.assertEqual(code, 0)
        self.assertIn(xx.UI_BEGIN, out)
        st = xx.load_state()
        self.assertEqual(st["status"], "choosing")
        self.assertEqual(st["run"]["outline"], OUTLINE)
        self.assertTrue(all("parsed" in choice for choice in st["run"]["choices"]))

    def test_unknown_skill_rejected(self):
        self.assertRaises(ValueError, xx.parse_effect, "skill:kind=foo:n=1:name=乱功")

    def test_unknown_lover_bond_rejected(self):
        self.assertRaises(
            ValueError,
            xx.parse_effect,
            "ally:bond=lover:n=1:name=月华",
        )

    def test_safe_frenzy_rejected(self):
        parsed = xx.parse_effect("skill:kind=frenzy:n=1:name=狂刀诀")
        self.assertRaises(ValueError, xx.validate_effect, "SAFE", parsed, "event")

    def test_unknown_grant_type_or_fx(self):
        self.assertRaises(ValueError, xx.parse_effect, "grant:type=zzz:fx=hp:n=8:name=蛇丹")
        self.assertRaises(ValueError, xx.parse_effect, "grant:type=dan:fx=zzz:n=8:name=蛇丹")

    def test_safe_bomb_grant_rejected(self):
        parsed = xx.parse_effect("grant:type=dan:fx=bomb:n=1:name=破军丹")
        self.assertRaises(ValueError, xx.validate_effect, "SAFE", parsed, "event")

    def test_tribulation_rejects_effects_and_shows_chances(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        st["run"]["node_type"] = "tribulation"
        st["run"]["slots"] = []
        xx.save_state(st)
        args = [
            "inscribe", "--outline", OUTLINE, "--body", "劫云压城，三条生路同时显现。",
            "--c1", "硬渡", "--c2", "护体", "--c3", "问心", "--e1", "hp+4",
        ]
        code, _, err = run(args)
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        code, out, err = run(args[:-2])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("成功率", out)
        choices = xx.load_state()["run"]["choices"]
        self.assertEqual(
            [choice["effect"] for choice in choices],
            ["trib:hard", "trib:guard", "trib:heart"],
        )

    def test_trib_chances_counts_dao_entries_not_ally_n(self):
        run_state = xx.new_run(xx.default_meta(), 1)
        run_state["skills"] = [{"kind": "oath", "n": 2, "name": "同心诀"}]
        run_state["allies"] = [{"bond": "dao", "n": 3, "name": "月华"}]
        self.assertEqual(xx.trib_chances(run_state), (14, 42, 5))


class TestTribulation(CwdTest):
    def _start_tribulation(self, *, atk=3, qi=0, seed=1):
        run(["init"])
        st = xx.load_state()
        st["meta"]["exp"] = 50
        st["meta"]["atk"] = atk
        st["meta"]["qi"] = qi
        xx.save_state(st)
        run(["start", "--seed", str(seed)])

    def _inscribe_tribulation(self):
        return run(
            [
                "inscribe",
                "--outline", OUTLINE,
                "--body", "天劫云压顶，三道雷纹在识海里转。系统冷冰冰列出三条渡法。",
                "--c1", "硬渡",
                "--c2", "护体",
                "--c3", "心魔问道",
            ]
        )

    def test_exp_forces_trib_floor_and_draft_shows_chances(self):
        self._start_tribulation()

        st = xx.load_state()
        self.assertEqual(st["run"]["node_type"], "tribulation")
        code, out, err = run(["draft"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("hard=", out)
        self.assertIn("guard=", out)
        self.assertIn("heart=", out)

    def test_trib_use_rejected(self):
        self._start_tribulation()
        self._inscribe_tribulation()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "dan", "fx": "hp", "n": 8, "name": "蛇丹"}
        ]
        xx.save_state(st)

        code, _, err = run(["use", "--id", "p1"])

        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_trib_success_raises_both_realms_and_continues(self):
        self._start_tribulation(atk=30, qi=30, seed=1)
        st = xx.load_state()
        self.assertEqual(xx.trib_chances(st["run"])[0], 95)
        self.assertLessEqual(
            xx.trib_roll(st["run"]["seed"], st["run"]["floor"]),
            95,
        )
        self._inscribe_tribulation()

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertEqual(st["status"], "composing")
        self.assertEqual(st["run"]["realm"], "筑基")
        self.assertEqual(st["meta"]["realm"], "筑基")
        self.assertEqual(st["run"]["floor"], 2)

    def test_trib_failure_ends_without_consuming_revive(self):
        self._start_tribulation(seed=1)
        self.assertGreater(xx.trib_roll(1, 1), 5)
        self._inscribe_tribulation()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "dan", "fx": "revive", "n": 1, "name": "续命丹"}
        ]
        xx.save_state(st)

        run(["choose", "--n", "3"])

        st = xx.load_state()
        self.assertEqual(st["status"], "ended")
        self.assertEqual(st["run"]["death_cause"], "tribulation")
        self.assertFalse(st["run"]["revive_used"])
        self.assertEqual(len(st["run"]["inventory"]), 1)

    def test_huashen_never_needs_tribulation(self):
        meta = xx.default_meta()
        meta["exp"] = 999
        meta["realm"] = "化神"

        self.assertFalse(xx.need_tribulation(meta, "化神"))


class TestChooseGrant(CwdTest):
    def _choosing(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()

    def test_choose_grant_four_pills(self):
        self._choosing()
        force_effects(
            "grant:type=dan:fx=hp:n=8:name=蛇丹甲",
            "hp+4",
            "qi+3",
        )
        run(["choose", "--n", "1"])
        for name in ("蛇丹乙", "蛇丹丙", "蛇丹丁"):
            st = xx.load_state()
            self.assertEqual(st["status"], "composing")
            inscribe_ok()
            force_effects(
                f"grant:type=dan:fx=hp:n=8:name={name}",
                "hp+4",
                "qi+3",
            )
            run(["choose", "--n", "1"])

        inv = xx.load_state()["run"]["inventory"]
        self.assertEqual(len(inv), 4)
        self.assertEqual([item["uid"] for item in inv], ["p1", "p2", "p3", "p4"])
        self.assertEqual(inv[0]["type"], "dan")
        self.assertEqual(inv[0]["fx"], "hp")

    def test_choose_applies_stats_allies_skills_and_exp(self):
        self._choosing()
        force_effects("maxhp+2;hp+4", "qi+3", "atk+1")
        run(["choose", "--n", "1"])
        st = xx.load_state()
        self.assertEqual((st["run"]["max_hp"], st["run"]["hp"]), (22, 22))
        self.assertEqual(st["meta"]["exp"], 5)

        inscribe_ok()
        force_effects(
            "ally:bond=partner:n=1:name=青羽",
            "hp+4",
            "qi+3",
        )
        run(["choose", "--n", "1"])
        inscribe_ok()
        force_effects(
            "skill:kind=insight:n=2:name=观星诀",
            "hp+4",
            "qi+3",
        )
        run(["choose", "--n", "1"])
        st = xx.load_state()
        self.assertEqual(st["run"]["allies"][0]["uid"], "a1")
        self.assertEqual(st["run"]["skills"][0]["uid"], "s1")
        self.assertEqual(st["meta"]["exp"], 22)

    def test_choose_clamps_attack_and_qi_to_run_limits(self):
        self._choosing()
        st = xx.load_state()
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "meridians", "n": 10, "name": "通脉诀"}
        ]
        st["run"]["qi_bonus"] = 4
        xx.save_state(st)
        force_effects("atk-99;qi+999", "hp+4", "maxhp+2")

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertEqual(st["run"]["atk"], 1)
        self.assertEqual(st["run"]["qi"], 113)

    def test_choose_sets_pending_log_and_setup(self):
        self._choosing()
        force_effects("hp+4", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])
        st = xx.load_state()
        self.assertTrue(st["run"]["pending_log"])
        self.assertEqual(st["run"]["chronicle"][0]["setup"], OUTLINE)
        self.assertEqual(st["run"]["chronicle"][0]["act"], "choose:1")
        self.assertIsNone(st["run"]["chronicle"][0]["after"])

    def test_choose_backlash_ends_run(self):
        self._choosing()
        force_effects("hp-20", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])
        st = xx.load_state()
        self.assertEqual(st["status"], "ended")
        self.assertEqual(st["run"]["hp"], 0)
        self.assertEqual(st["run"]["death_cause"], "backlash")
        self.assertEqual(st["meta"]["exp"], 0)

    def test_info_supports_hub_choosing_ended_but_not_composing(self):
        run(["init"])
        code, out, err = run(["info"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("系统空间", out)

        run(["start", "--seed", "1"])
        code, _, err = run(["info"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

        inscribe_ok()
        code, out, err = run(["info"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("矿洞深处", out)

        force_effects("hp-20", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])
        code, out, err = run(["info"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("走火", out)


class TestFightUse(CwdTest):
    def _fight_state(self):
        return {
            "meta": xx.default_meta(),
            "run": xx.new_run(xx.default_meta(), 1),
        }

    def test_bomb_halves_opening_hp(self):
        st = self._fight_state()
        st["run"]["fight_mods"] = [{"fx": "bomb", "n": 1}]

        report = xx.fight(st)

        self.assertEqual(report["log"][0], "开战：敌 气血5 攻2")

    def test_execute_triggers_at_four_times_n(self):
        st = self._fight_state()
        st["run"]["atk"] = 1
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "weaken", "n": 2, "name": "破甲诀"},
            {"uid": "s2", "kind": "execute", "n": 2, "name": "斩妖诀"},
        ]

        report = xx.fight(st)

        self.assertEqual(report["log"][1], "第1轮 你造成3伤害")

    def test_blood_price_adds_n_to_strike_damage(self):
        st = self._fight_state()
        st["run"]["atk"] = 1
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "blood_price", "n": 2, "name": "燃血诀"}
        ]

        report = xx.fight(st)

        self.assertEqual(report["log"][1], "第1轮 你造成3伤害")

    def test_vigor_triggers_at_exactly_half_hp(self):
        st = self._fight_state()
        st["run"]["hp"] = 10
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "vigor", "n": 2, "name": "气盛诀"}
        ]

        report = xx.fight(st)

        self.assertEqual(report["log"][1], "第1轮 你造成5伤害")

    def test_brother_bonus_applies_per_partner(self):
        st = self._fight_state()
        st["run"]["atk"] = 1
        st["run"]["allies"] = [
            {"uid": "a1", "bond": "partner", "n": 1, "name": "青羽"},
            {"uid": "a2", "bond": "partner", "n": 2, "name": "玄石"},
        ]
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "brother", "n": 1, "name": "结义诀"}
        ]

        report = xx.fight(st)

        self.assertEqual(report["log"][1], "第1轮 你造成6伤害")

    def test_step_zeros_first_enemy_hit(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "step", "n": 1, "name": "踏影"}
        ]
        st["run"]["atk"] = 50
        xx.save_state(st)
        force_effects("battle;atk+1;hp-3", "hp+4", "qi+3")

        run(["choose", "--n", "1"])

        facts = xx.load_state()["run"]["chronicle"][0]["facts"]
        self.assertIn("身法", facts)

    def test_use_unknown_rejected(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()

        code, _, err = run(["use", "--id", "p9"])

        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_use_hp_pill(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "dan", "fx": "hp", "n": 8, "name": "蛇丹"}
        ]
        st["run"]["hp"] = 10
        st["run"]["node_type"] = "event"
        xx.save_state(st)

        code, _, _ = run(["use", "--id", "p1"])

        self.assertEqual(code, 0)
        st = xx.load_state()
        self.assertEqual(st["run"]["inventory"], [])
        self.assertGreaterEqual(st["run"]["hp"], 18)

    def test_spark_adds_qi_and_loses_three_hp_after_ward(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "dan", "fx": "spark", "n": 6, "name": "焚心丹"}
        ]
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "spark_ward", "n": 1, "name": "避火诀"}
        ]
        st["run"]["hp"] = 10
        st["run"]["node_type"] = "event"
        xx.save_state(st)

        code, _, _ = run(["use", "--id", "p1"])

        self.assertEqual(code, 0)
        st = xx.load_state()
        self.assertEqual(st["run"]["qi"], 6)
        self.assertEqual(st["run"]["hp"], 8)

    def test_winning_awards_hunt_exp(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "hunt", "n": 2, "name": "猎魔诀"}
        ]
        st["run"]["atk"] = 50
        xx.save_state(st)
        force_effects("battle;atk+1;hp-3", "hp+4", "qi+3")

        run(["choose", "--n", "1"])

        self.assertEqual(xx.load_state()["meta"]["exp"], 12)

    def test_ward_use_awards_scavenger_exp(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "fu", "fx": "ward", "n": 1, "name": "避战符"}
        ]
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "scavenger", "n": 3, "name": "拾荒诀"}
        ]
        st["run"]["node_type"] = "event"
        xx.save_state(st)

        run(["use", "--id", "p1"])

        self.assertEqual(xx.load_state()["meta"]["exp"], 8)


class TestDeaths(CwdTest):
    def test_accident_p100_kills_with_hp(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        force_effects("qi+1;accident:p=40", "hp+4", "qi+3")
        st = xx.load_state()
        st["run"]["choices"][0]["parsed"]["accident"] = 100
        xx.save_state(st)

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertEqual(st["status"], "ended")
        self.assertEqual(st["run"]["death_cause"], "accident")
        self.assertGreater(st["run"]["hp"], 0)

    def test_luck_cancels_low_p(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "luck", "n": 15, "name": "气运"}
        ]
        xx.save_state(st)
        force_effects("qi+1;accident:p=10", "hp+4", "qi+3")

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertNotEqual(st["run"].get("death_cause"), "accident")
        self.assertNotEqual(st["status"], "ended")

    def test_danger_saves_first_accident(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["skills"] = [
            {"uid": "s1", "kind": "danger", "n": 1, "name": "危机感知"}
        ]
        xx.save_state(st)
        force_effects("qi+1;accident:p=40", "hp+4", "qi+3")
        st = xx.load_state()
        st["run"]["choices"][0]["parsed"]["accident"] = 100
        xx.save_state(st)

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertNotEqual(st["status"], "ended")
        self.assertTrue(st["run"]["danger_used"])

    def test_spark_kills_backlash(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "dan", "fx": "spark", "n": 2, "name": "躁丹"}
        ]
        st["run"]["hp"] = 2
        xx.save_state(st)

        run(["use", "--id", "p1"])

        st = xx.load_state()
        self.assertEqual(st["status"], "ended")
        self.assertEqual(st["run"]["death_cause"], "backlash")

    def test_giveup(self):
        run(["init"])
        run(["start", "--seed", "1"])

        code, out, _ = run(["giveup"])

        self.assertEqual(code, 0)
        st = xx.load_state()
        self.assertEqual(st["status"], "ended")
        self.assertEqual(st["run"]["death_cause"], "given_up")
        self.assertIn("自绝", out)
        self.assertEqual(st["run"]["chronicle"][-1]["act"], "giveup")

    def test_revive_does_not_save_accident(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        st = xx.load_state()
        st["run"]["inventory"] = [
            {"uid": "p1", "type": "dan", "fx": "revive", "n": 1, "name": "续命丹"}
        ]
        xx.save_state(st)
        force_effects("qi+1;accident:p=40", "hp+4", "qi+3")
        st = xx.load_state()
        st["run"]["choices"][0]["parsed"]["accident"] = 100
        xx.save_state(st)

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertEqual(st["run"]["death_cause"], "accident")
        self.assertFalse(st["run"]["revive_used"])
        self.assertEqual(len(st["run"]["inventory"]), 1)

    def test_lethal_attribute_loss_prevents_accident_roll(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        force_effects("hp-20;accident:p=40", "hp+4", "qi+3")
        st = xx.load_state()
        st["run"]["choices"][0]["parsed"]["accident"] = 100
        xx.save_state(st)

        run(["choose", "--n", "1"])

        st = xx.load_state()
        self.assertEqual(st["run"]["death_cause"], "backlash")


class TestChronicle(CwdTest):
    def test_log_after_and_recall(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        force_effects("hp+4", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])
        after = "左灯熄灭，你把一缕余温收进气海，继续往矿脉深处走。"

        code, out, err = run(["log", "--after", after])

        self.assertEqual(code, 0, err)
        st = xx.load_state()
        self.assertFalse(st["run"]["pending_log"])
        self.assertEqual(st["run"]["chronicle"][0]["after"], after)
        code, out, _ = run(["recall"])
        self.assertIn(xx.UI_BEGIN, out)
        self.assertIn("矿洞", out)

    def test_draft_fills_mechanical_after(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        force_effects("hp+4", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])

        run(["draft"])

        st = xx.load_state()
        self.assertFalse(st["run"]["pending_log"])
        self.assertEqual(
            st["run"]["chronicle"][0]["after"],
            "选1；气血20/20；未战；下层",
        )

    def test_log_without_pending_errors(self):
        run(["init"])

        code, _, err = run(["log", "--after", OUTLINE])

        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_log_rejects_after_outside_length_limit(self):
        run(["init"])
        run(["start", "--seed", "1"])
        inscribe_ok()
        force_effects("hp+4", "qi+3", "maxhp+2")
        run(["choose", "--n", "1"])

        code, _, err = run(["log", "--after", "太短"])

        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertTrue(xx.load_state()["run"]["pending_log"])

    def test_next_writes_lives(self):
        run(["init"])
        run(["start", "--seed", "1"])
        run(["giveup"])

        run(["next"])

        lives = xx.load_state()["meta"]["lives"]
        self.assertEqual(len(lives), 1)
        self.assertIn("死于", lives[0]["digest"])
        self.assertLessEqual(len(lives[0]["entries"]), 15)
        code, out, _ = run(["recall"])
        self.assertIn(lives[0]["digest"], out)

    def test_lives_cap_8(self):
        run(["init"])
        for i in range(9):
            st = xx.load_state()
            st["status"] = "ended"
            st["run"] = xx.new_run(st["meta"], i + 1)
            st["run"]["death_cause"] = "given_up"
            st["run"]["chronicle"] = []
            st["run"]["pending_log"] = False
            xx.save_state(st)
            run(["next"])

        self.assertEqual(len(xx.load_state()["meta"]["lives"]), 8)

    def test_floor_past_nine(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        st["run"]["atk"] = 100
        st["meta"]["exp"] = -100
        xx.save_state(st)
        for _ in range(9):
            inscribe_ok()
            force_effects("hp+4", "qi+3", "maxhp+2")
            run(["choose", "--n", "1"])
        st = xx.load_state()
        self.assertGreaterEqual(st["run"]["floor"], 10)
        self.assertEqual(st["status"], "composing")

    def test_chronicle_cap_40(self):
        run(["init"])
        run(["start", "--seed", "1"])
        st = xx.load_state()
        st["run"]["chronicle"] = [
            {
                "floor": i,
                "node": "event",
                "realm": "炼气",
                "setup": OUTLINE,
                "act": "choose:1",
                "facts": "气血20/20",
                "after": "机械",
            }
            for i in range(1, 41)
        ]
        xx.save_state(st)
        inscribe_ok()
        force_effects("hp+4", "qi+3", "maxhp+2")

        run(["choose", "--n", "1"])

        chronicle = xx.load_state()["run"]["chronicle"]
        self.assertEqual(len(chronicle), 40)
        self.assertEqual(chronicle[0]["floor"], 2)


class TestRebirth(CwdTest):
    def _dead(self, **run_over):
        run(["init"])
        run(["start", "--seed", "1"])
        run(["giveup"])
        st = xx.load_state()
        st["run"].update(run_over)
        xx.save_state(st)
        return st

    def test_preview_uses_pouch_and_preincrement_cycles_for_slot_cap(self):
        st = self._dead(
            skills=[{"uid": "s1", "kind": "pouch", "n": 1, "name": "扩容"}],
        )
        st["meta"]["cycles"] = 5

        preview = xx.preview_rebirth(st)

        self.assertEqual(preview["slot_cap"], 10)

    def test_next_keeps_best_items_and_writes_uid_order(self):
        items = [
            {"uid": uid, "type": "dan", "fx": "hp", "n": n, "name": uid}
            for uid, n in (
                ("p10", 4), ("p2", 4), ("p7", 6),
                ("p1", 1), ("p5", 5), ("p3", 3),
            )
        ]
        self._dead(inventory=items, skills=[])

        code, out, err = run(["next"])

        self.assertEqual((code, err), (0, ""))
        self.assertIn("带走", out)
        self.assertIn("遗弃", out)
        meta = xx.load_state()["meta"]
        self.assertEqual(
            [(item["uid"], item["n"]) for item in meta["inventory"]],
            [("p2", 4), ("p5", 5), ("p7", 6), ("p10", 4)],
        )
        self.assertEqual(meta["cycles"], 1)

    def test_next_keeps_three_best_skills_and_writes_uid_order(self):
        skills = [
            {"uid": uid, "kind": "sword", "n": n, "name": uid}
            for uid, n in (
                ("s9", 2), ("s2", 4), ("s10", 2), ("s1", 1), ("s7", 3),
            )
        ]
        self._dead(skills=skills, inventory=[])

        run(["next"])

        kept = xx.load_state()["meta"]["skills"]
        self.assertEqual(
            [(skill["uid"], skill["n"]) for skill in kept],
            [("s2", 4), ("s7", 3), ("s10", 2)],
        )

    def test_preview_applies_memory_vessel_and_recomputes_realm(self):
        st = self._dead(
            skills=[
                {"uid": "s1", "kind": "memory", "n": 1, "name": "残忆"},
                {"uid": "s2", "kind": "vessel", "n": 1, "name": "道器"},
            ],
        )
        st["meta"].update({"exp": 149, "realm": "金丹"})
        st["run"].update({"max_hp": 21, "atk": 3, "qi": 11})

        preview = xx.preview_rebirth(st)

        self.assertEqual(preview["exp"], 119)
        self.assertEqual(preview["realm"], "筑基")
        self.assertEqual(preview["max_hp"], 20)
        self.assertEqual(preview["atk"], 3)
        self.assertEqual(preview["qi"], 9)

    def test_ended_info_matches_next_and_drops_allies(self):
        self._dead(
            inventory=[
                {"uid": "p1", "type": "dan", "fx": "hp", "n": 4, "name": "青丹"}
            ],
            skills=[{"uid": "s1", "kind": "sword", "n": 1, "name": "剑诀"}],
            allies=[{"uid": "a1", "bond": "partner", "n": 1, "name": "阿青"}],
        )

        _, info_out, _ = run(["info"])
        code, next_out, err = run(["next"])

        self.assertEqual((code, err), (0, ""))
        for text in ("青丹", "剑诀", "活物未随轮回"):
            self.assertIn(text, info_out)
            self.assertIn(text, next_out)
        st = xx.load_state()
        self.assertEqual(st["status"], "hub")
        self.assertIsNone(st["run"])
        self.assertNotIn("allies", st["meta"])
        run(["start", "--seed", "2"])
        self.assertEqual(xx.load_state()["run"]["allies"], [])

    def test_start_continues_uids_after_kept_items_and_skills(self):
        self._dead(
            inventory=[
                {"uid": "p5", "type": "dan", "fx": "hp", "n": 4, "name": "青丹"}
            ],
            skills=[{"uid": "s8", "kind": "sword", "n": 1, "name": "剑诀"}],
        )
        run(["next"])

        run(["start", "--seed", "2"])

        new_run = xx.load_state()["run"]
        self.assertEqual(new_run["next_p"], 6)
        self.assertEqual(new_run["next_s"], 9)
        self.assertEqual(new_run["next_a"], 1)

    def test_next_rejects_non_ended_state(self):
        run(["init"])

        code, _, err = run(["next"])

        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)


if __name__ == "__main__":
    unittest.main()
