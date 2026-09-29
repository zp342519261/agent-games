from __future__ import annotations

import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import idiom_engine as idiom


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            idiom.run_cmd(argv)
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


class TestIdiom(CwdTest):
    def test_init_and_start(self):
        code, out, _ = run(["init"])
        self.assertEqual(code, 0)
        self.assertIn(idiom.UI_BEGIN, out)
        code, out, _ = run(["start", "--seed", "1"])
        self.assertEqual(code, 0)
        st = idiom.load_state()
        self.assertEqual(st["status"], "playing")
        self.assertEqual(len(st["current"]), 4)
        self.assertIn(st["current"], out)

    def test_play_match_and_reject(self):
        run(["init"])
        run(["set", "--mode", "solo", "--target", "5"])
        run(["start", "--seed", "7"])
        st = idiom.load_state()
        need = st["current"][-1]
        cands = idiom.candidates(st, need)
        self.assertTrue(cands, "seed should leave at least one candidate")
        word = cands[0]
        code, out, _ = run(["play", "--word", word])
        self.assertEqual(code, 0)
        self.assertIn(word, out)
        self.assertEqual(idiom.load_state()["streak"], 1)

        code, _, err = run(["play", "--word", "不对不对"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

        code, _, err = run(["play", "--word", word])
        self.assertNotEqual(code, 0)

    def test_add_then_play(self):
        run(["init"])
        run(["start", "--seed", "2"])
        st = idiom.load_state()
        need = st["current"][-1]
        fake = need + "甲乙丙"
        # make valid 4-char: need + 3 chars
        fake = need + "开天地"
        self.assertEqual(len(fake), 4)
        code, out, _ = run(["add", "--word", fake])
        self.assertEqual(code, 0)
        code, out, _ = run(["play", "--word", fake])
        self.assertEqual(code, 0)
        self.assertIn(fake, out)

    def test_giveup_next(self):
        run(["init"])
        run(["start", "--seed", "3"])
        run(["giveup"])
        st = idiom.load_state()
        self.assertEqual(st["status"], "ended")
        run(["next"])
        self.assertEqual(idiom.load_state()["status"], "configuring")

    def test_help(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/成语接龙", out)


class TestDocs(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_skill(self):
        text = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: idiom", text)
        self.assertIn("/成语接龙", text)
        self.assertIn("IDIOM_UI_BEGIN", text)

    def test_bank_all_four(self):
        for w in idiom.IDIOM_BANK:
            self.assertEqual(len(w), 4, w)
            self.assertTrue(idiom.is_four_han(w), w)

    def test_version(self):
        self.assertEqual((self.root / "VERSION").read_text(encoding="utf-8").strip(), "1.0.0")


if __name__ == "__main__":
    unittest.main()
