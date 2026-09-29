from __future__ import annotations

import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import bj_engine as bj


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            bj.run_cmd(argv)
    except SystemExit as e:
        code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


class CwdTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cwd = Path.cwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self.tmp.cleanup()


class TestBasics(CwdTest):
    def test_hand_total_soft_and_bust(self):
        self.assertEqual(bj.hand_total(["A♠", "9♥"])[0], 20)
        self.assertEqual(bj.hand_total(["A♠", "9♥", "A♦"])[0], 21)
        self.assertEqual(bj.hand_total(["K♠", "Q♥", "5♦"])[0], 25)
        self.assertTrue(bj.is_blackjack(["A♠", "K♥"]))
        self.assertFalse(bj.is_blackjack(["A♠", "5♥", "5♦"]))

    def test_init_start_bet_flow(self):
        code, out, _ = run(["init"])
        self.assertEqual(code, 0)
        self.assertIn(bj.UI_BEGIN, out)
        code, out, _ = run(["start", "--seed", "1"])
        self.assertEqual(code, 0)
        self.assertIn("下注", out)
        code, out, _ = run(["bet", "--amount", "50"])
        self.assertEqual(code, 0)
        st = bj.load_state()
        self.assertIn(st["phase"], ("player", "settled"))
        self.assertEqual(len(st["player"]), 2)
        self.assertEqual(len(st["dealer"]), 2)
        if st["phase"] == "player":
            self.assertIn("??", out)

    def test_hit_stand(self):
        run(["init"])
        run(["start", "--seed", "99"])
        run(["bet", "--amount", "50"])
        st = bj.load_state()
        if st["phase"] == "player":
            code, out, _ = run(["stand"])
            self.assertEqual(code, 0)
            st = bj.load_state()
            self.assertEqual(st["phase"], "settled")
            self.assertIn("结果", out)

    def test_insufficient_bet(self):
        run(["init"])
        run(["set", "--bankroll", "100", "--bet", "50"])
        run(["start", "--seed", "2"])
        code, _, err = run(["bet", "--amount", "500"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_next_keeps_bankroll(self):
        run(["init"])
        run(["start", "--seed", "3"])
        run(["bet", "--amount", "50"])
        before = bj.load_state()["bankroll"]
        code, out, _ = run(["next"])
        self.assertEqual(code, 0)
        st = bj.load_state()
        self.assertEqual(st["status"], "configuring")
        self.assertEqual(st["bankroll"], before)

    def test_help(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/二十一点", out)


class TestDocs(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_skill(self):
        text = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: bj", text)
        self.assertIn("/二十一点", text)
        self.assertIn("BJ_UI_BEGIN", text)

    def test_version(self):
        self.assertEqual((self.root / "VERSION").read_text(encoding="utf-8").strip(), "1.0.0")


if __name__ == "__main__":
    unittest.main()
