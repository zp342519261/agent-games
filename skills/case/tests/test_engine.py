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
import case_engine as case


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            case.run_cmd(argv)
    except SystemExit as e:
        code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


SURFACE = "林宅主人昨夜死在书房，门锁完好，桌上只剩半杯凉透的茶。"
TRUTH = (
    "管家老周因高利贷走投无路，从侧门入内用枕头捂死主人，"
    "再摆出喝茶假象，泥脚印与手套出卖了他。"
)
SUSPECTS = ["管家老周", "太太", "司机"]
LOCATIONS = {
    "书房": [
        {"id": "c1", "hint": "抽屉里有催款单", "secret": "催款单显示老周欠高利贷"},
    ],
    "花园": [
        {"id": "c2", "hint": "侧门有新鲜泥脚印", "secret": "脚印尺码与老周皮鞋吻合"},
        {"id": "c3", "hint": "花盆下有半截手套", "secret": "手套内侧绣着周"},
    ],
}


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
        self.assertIn(case.UI_BEGIN, out)
        self.assertIn("难度：普通", out)

    def test_help_slash(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/探案", out)


class TestPlay(CwdTest):
    def _start(self):
        run(["init"])
        run(["set", "--difficulty", "简单"])
        return run([
            "start",
            "--surface",
            SURFACE,
            "--truth",
            TRUTH,
            "--culprit",
            "管家老周",
            "--suspects-json",
            json.dumps(SUSPECTS, ensure_ascii=False),
            "--locations-json",
            json.dumps(LOCATIONS, ensure_ascii=False),
        ])

    def test_start_hides_truth(self):
        code, out, _ = self._start()
        self.assertEqual(code, 0)
        self.assertIn(SURFACE, out)
        self.assertNotIn(TRUTH, out)
        self.assertNotIn("高利贷", out)
        self.assertEqual(case.load_state()["status"], "playing")

    def test_secret_no_ui(self):
        self._start()
        code, out, _ = run(["secret"])
        self.assertEqual(code, 0)
        self.assertNotIn(case.UI_BEGIN, out)
        self.assertIn("管家老周", out)
        self.assertIn("高利贷", out)

    def test_search_progress_locked(self):
        self._start()
        code, out, _ = run(["search", "--loc", "花园"])
        self.assertEqual(code, 0)
        self.assertIn("泥脚印", out)
        self.assertNotIn("绣着周", out)
        self.assertEqual(case.load_state()["found"], ["c2"])
        code, out, _ = run(["search", "--loc", "花园"])
        self.assertEqual(code, 0)
        self.assertIn("半截手套", out)
        code, out, _ = run(["search", "--loc", "花园"])
        self.assertEqual(code, 0)
        self.assertIn("已无新线索", out)

    def test_ask_and_accuse(self):
        self._start()
        code, out, _ = run([
            "ask", "--suspect", "太太", "--q", "你昨晚在哪？", "--a", "是",
        ])
        self.assertEqual(code, 0)
        self.assertIn("太太", out)
        code, out, _ = run(["accuse", "--name", "司机"])
        self.assertEqual(code, 0)
        self.assertEqual(case.load_state()["outcome"], "wrong")
        self.assertIn(TRUTH, out)

        # 新局再测猜对
        run(["next"])
        self._start()
        code, out, _ = run(["accuse", "--name", "管家老周"])
        self.assertEqual(code, 0)
        self.assertEqual(case.load_state()["outcome"], "won")

    def test_culprit_must_be_suspect(self):
        run(["init"])
        code, _, err = run([
            "start",
            "--surface",
            SURFACE,
            "--truth",
            TRUTH,
            "--culprit",
            "陌生人",
            "--suspects-json",
            json.dumps(SUSPECTS, ensure_ascii=False),
            "--locations-json",
            json.dumps(LOCATIONS, ensure_ascii=False),
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)


class TestSkillDocs(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_skill_frontmatter(self):
        text = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: case", text)
        self.assertIn("/探案", text)
        self.assertIn("CASE_UI_BEGIN", text)
        self.assertIn("disable-model-invocation: true", text)

    def test_version_file(self):
        self.assertEqual(
            (self.root / "VERSION").read_text(encoding="utf-8").strip(),
            "1.0.0",
        )


if __name__ == "__main__":
    unittest.main()
