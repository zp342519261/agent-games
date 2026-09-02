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


if __name__ == "__main__":
    unittest.main()
