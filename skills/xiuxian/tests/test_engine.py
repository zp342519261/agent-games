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


if __name__ == "__main__":
    unittest.main()
