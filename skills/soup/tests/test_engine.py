from __future__ import annotations

import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import soup_engine as soup


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            soup.run_cmd(argv)
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


class TestInitSetHelp(CwdTest):
    def test_init_ui_has_markers_no_surface_no_truth(self):
        code, out, err = run(["init"])
        self.assertEqual(code, 0)
        self.assertIn(soup.UI_BEGIN, out)
        self.assertIn(soup.UI_END, out)
        self.assertIn("主题：随机", out)
        self.assertIn("难度：普通", out)
        self.assertNotIn("汤面", out)
        self.assertNotIn("汤底", out)
        st = soup.load_state()
        self.assertEqual(st["status"], "configuring")
        self.assertIsNone(st["surface"])
        self.assertIsNone(st["truth"])

    def test_set_theme_and_difficulty(self):
        run(["init"])
        code, out, _ = run(["set", "--theme", "黑暗", "--difficulty", "简单"])
        self.assertEqual(code, 0)
        self.assertIn("主题：黑暗", out)
        self.assertIn("难度：简单", out)
        st = soup.load_state()
        self.assertEqual(st["theme"], "黑暗")
        self.assertEqual(st["difficulty"], "简单")

    def test_set_invalid_theme(self):
        run(["init"])
        code, _, err = run(["set", "--theme", "科幻"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_help_lists_slash(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/海龟汤", out)
        self.assertNotIn(soup.UI_BEGIN, out)


if __name__ == "__main__":
    unittest.main()
