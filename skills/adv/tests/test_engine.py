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
import adv_engine as adv


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            adv.run_cmd(argv)
    except SystemExit as e:
        code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


SCENARIO = {
    "start": "intro",
    "nodes": {
        "intro": {
            "text": "你站在锈迹斑斑的铁门前，风里有潮气与松脂味。",
            "choices": [
                {"label": "推门进去", "to": "hall", "gain": ["旧钥匙"]},
                {"label": "沿墙离开", "to": "leave"},
            ],
        },
        "hall": {
            "text": "大厅空无一人，壁炉里还有余温，侧门挂着铜锁。",
            "choices": [
                {
                    "label": "用钥匙开侧门",
                    "to": "secret",
                    "need": ["旧钥匙"],
                },
                {"label": "原路返回门外", "to": "leave"},
            ],
        },
        "secret": {
            "text": "侧门后是一封未寄出的信。你决定带走真相。",
            "ending": "揭开往事",
            "outcome": "good",
        },
        "leave": {
            "text": "你转身走进夜色，门在身后轻轻关上。",
            "ending": "悄然离去",
            "outcome": "neutral",
        },
    },
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
        self.assertIn(adv.UI_BEGIN, out)
        self.assertIn("类型：随机", out)
        self.assertEqual(adv.load_state()["status"], "configuring")

    def test_set_and_invalid(self):
        run(["init"])
        code, out, _ = run(["set", "--genre", "悬疑", "--difficulty", "困难"])
        self.assertEqual(code, 0)
        self.assertIn("类型：悬疑", out)
        code, _, err = run(["set", "--genre", "武侠"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_help_slash(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/冒险", out)


class TestPlay(CwdTest):
    def _start(self, genre_resolved="悬疑"):
        run(["init"])
        run(["set", "--genre", "悬疑", "--difficulty", "普通"])
        return run([
            "start",
            "--title",
            "锈门夜访",
            "--scenario-json",
            json.dumps(SCENARIO, ensure_ascii=False),
            "--genre-resolved",
            genre_resolved,
        ])

    def test_start_hides_future_nodes(self):
        code, out, _ = self._start()
        self.assertEqual(code, 0)
        self.assertIn("铁门", out)
        self.assertNotIn("未寄出的信", out)
        self.assertIn("1. 推门进去", out)
        st = adv.load_state()
        self.assertEqual(st["status"], "playing")
        self.assertEqual(st["current"], "intro")

    def test_secret_no_ui(self):
        self._start()
        code, out, _ = run(["secret"])
        self.assertEqual(code, 0)
        self.assertNotIn(adv.UI_BEGIN, out)
        self.assertIn("揭开往事", out)

    def test_choose_gain_and_need(self):
        self._start()
        code, out, _ = run(["choose", "--n", "1"])
        self.assertEqual(code, 0)
        self.assertIn("旧钥匙", out)
        self.assertIn("用钥匙开侧门", out)
        code, out, _ = run(["choose", "--n", "1"])
        self.assertEqual(code, 0)
        self.assertIn("揭开往事", out)
        self.assertEqual(adv.load_state()["outcome"], "good")
        self.assertEqual(adv.load_state()["status"], "ended")

    def test_bad_scenario_rejected(self):
        run(["init"])
        bad = {"start": "x", "nodes": {"x": {"text": "太短", "choices": []}}}
        code, _, err = run([
            "start",
            "--title",
            "坏图",
            "--scenario-json",
            json.dumps(bad, ensure_ascii=False),
            "--genre-resolved",
            "日常",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(adv.load_state()["status"], "configuring")

    def test_genre_resolved_must_match(self):
        run(["init"])
        run(["set", "--genre", "科幻"])
        code, _, err = run([
            "start",
            "--title",
            "锈门夜访",
            "--scenario-json",
            json.dumps(SCENARIO, ensure_ascii=False),
            "--genre-resolved",
            "日常",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_giveup_and_next(self):
        self._start()
        code, out, _ = run(["giveup"])
        self.assertEqual(code, 0)
        self.assertEqual(adv.load_state()["outcome"], "bad")
        code, out, _ = run(["next"])
        self.assertEqual(code, 0)
        st = adv.load_state()
        self.assertEqual(st["status"], "configuring")
        self.assertEqual(st["genre"], "悬疑")
        self.assertIsNone(st["title"])


class TestSkillDocs(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_skill_frontmatter(self):
        text = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: adv", text)
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("/冒险", text)
        self.assertIn("ADV_UI_BEGIN", text)
        self.assertIn("secret", text)

    def test_version_file(self):
        v = (self.root / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(v, "1.0.0")


if __name__ == "__main__":
    unittest.main()
