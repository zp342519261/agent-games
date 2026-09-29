from __future__ import annotations

import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import spy_engine as spy


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            spy.run_cmd(argv)
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


class TestConfig(CwdTest):
    def test_init_ui(self):
        code, out, _ = run(["init"])
        self.assertEqual(code, 0)
        self.assertIn(spy.UI_BEGIN, out)
        self.assertIn("人数：4", out)
        self.assertEqual(spy.load_state()["status"], "configuring")

    def test_set_and_invalid(self):
        run(["init"])
        code, out, _ = run(["set", "--players", "5", "--spies", "1", "--user-seat", "2"])
        self.assertEqual(code, 0)
        self.assertIn("人数：5", out)
        self.assertIn("你的座位：2", out)
        code, _, err = run(["set", "--spies", "3"])  # 3*2>=5
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_help_slash(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/卧底", out)


class TestPlay(CwdTest):
    def _start(self, seed=1):
        run(["init"])
        run(["set", "--players", "4", "--spies", "1", "--user-seat", "1"])
        return run([
            "start", "--civilian", "牛奶", "--spy", "豆浆", "--seed", str(seed),
        ])

    def test_start_assigns_roles_secret_hidden_from_ui(self):
        code, out, _ = self._start()
        self.assertEqual(code, 0)
        self.assertIn("第 1 轮", out)
        self.assertNotIn("豆浆", out)
        self.assertNotIn("牛奶", out)
        st = spy.load_state()
        self.assertEqual(st["status"], "playing")
        spies = [s for s, r in st["roles"].items() if r == "spy"]
        self.assertEqual(len(spies), 1)

        code, out, _ = run(["secret"])
        self.assertEqual(code, 0)
        self.assertIn("平民词：牛奶", out)
        self.assertIn("卧底词：豆浆", out)
        self.assertNotIn(spy.UI_BEGIN, out)

        code, out, _ = run(["myword"])
        self.assertEqual(code, 0)
        self.assertTrue(out.strip().startswith("你的词："))
        self.assertNotIn("平民", out)
        self.assertNotIn("卧底", out)

    def test_describe_then_vote_flow(self):
        self._start(seed=42)
        for seat in (1, 2, 3, 4):
            code, out, _ = run(["describe", "--seat", str(seat), "--text", f"白色饮料{seat}"])
            self.assertEqual(code, 0)
        st = spy.load_state()
        self.assertEqual(st["phase"], "vote")
        self.assertIn("投票", out)

        # everyone votes seat 2
        for voter in (1, 2, 3, 4):
            code, out, _ = run(["vote", "--voter", str(voter), "--target", "2"])
            self.assertEqual(code, 0)
        st = spy.load_state()
        self.assertNotIn(2, st["alive"])
        self.assertTrue(st["status"] in ("playing", "ended"))

    def test_same_words_rejected(self):
        run(["init"])
        code, _, err = run(["start", "--civilian", "牛奶", "--spy", "牛奶"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_next_keeps_config(self):
        self._start()
        run(["giveup"])
        code, out, _ = run(["next"])
        self.assertEqual(code, 0)
        st = spy.load_state()
        self.assertEqual(st["status"], "configuring")
        self.assertEqual(st["players"], 4)
        self.assertIsNone(st["civilian_word"])
        self.assertNotIn("牛奶", out)


class TestDocs(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_skill(self):
        text = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: spy", text)
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("/卧底", text)
        self.assertIn("SPY_UI_BEGIN", text)

    def test_version(self):
        self.assertEqual((self.root / "VERSION").read_text(encoding="utf-8").strip(), "1.0.0")


if __name__ == "__main__":
    unittest.main()
