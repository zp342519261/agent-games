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
import juben_engine as juben


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            juben.run_cmd(argv)
    except SystemExit as e:
        code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


ROLES = [
    {
        "id": "host",
        "name": "房东",
        "public": "别墅主人，声称当晚在书房写作到很晚。",
        "private": "你确实在书房，但中途下楼倒水，看见亲戚鬼鬼祟祟。" * 2,
        "is_murderer": False,
    },
    {
        "id": "guest",
        "name": "远房亲戚",
        "public": "刚回来争遗产，情绪不稳。",
        "private": "你才是下手的人，用枕头捂死了睡在躺椅上的主人后伪装现场。" * 2,
        "is_murderer": True,
    },
    {
        "id": "maid",
        "name": "女佣",
        "public": "负责二楼打扫，说自己很早就睡了。",
        "private": "你听到争执但不敢出声，捡到一把陌生钥匙藏在围裙里。" * 2,
        "is_murderer": False,
    },
]

CLUES = [
    {"id": "p1", "text": "花瓶碎在走廊，缺口朝向楼梯。", "holder": None},
    {"id": "p2", "text": "书房台历停在案发日。", "holder": None},
    {"id": "p3", "text": "侧门插销被撬过。", "holder": None},
    {"id": "p4", "text": "茶几上有两只杯子。", "holder": None},
    {"id": "u1", "text": "你袖口有未洗掉的墨渍。", "holder": "guest"},
    {"id": "m1", "text": "你捡到一把不属于自己的钥匙。", "holder": "maid"},
]

PUBLIC = "雨夜别墅命案：主人死在书房躺椅上，门锁完好，三位在场者各执一词。"


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
        self.assertIn(juben.UI_BEGIN, out)
        self.assertIn("剧本杀", out)

    def test_help_slash(self):
        code, out, _ = run(["help"])
        self.assertEqual(code, 0)
        self.assertIn("/剧本杀", out)


class TestPlay(CwdTest):
    def _start(self, user_role="host"):
        run(["init"])
        return run([
            "start",
            "--title",
            "雨夜别墅",
            "--public",
            PUBLIC,
            "--roles-json",
            json.dumps(ROLES, ensure_ascii=False),
            "--clues-json",
            json.dumps(CLUES, ensure_ascii=False),
            "--user-role",
            user_role,
            "--seed",
            "1",
        ])

    def test_start_hides_private(self):
        code, out, _ = self._start()
        self.assertEqual(code, 0)
        self.assertIn("雨夜别墅", out)
        self.assertNotIn("你才是下手的人", out)
        self.assertNotIn("未洗掉的墨渍", out)
        st = juben.load_state()
        self.assertEqual(st["phase"], "intro")
        self.assertEqual(st["status"], "playing")

    def test_myrole_and_secret(self):
        self._start("guest")
        code, out, _ = run(["myrole"])
        self.assertEqual(code, 0)
        self.assertNotIn(juben.UI_BEGIN, out)
        self.assertIn("远房亲戚", out)
        self.assertIn("下手", out)
        self.assertIn("墨渍", out)
        code, out, _ = run(["secret"])
        self.assertEqual(code, 0)
        self.assertIn("murderer", out)
        self.assertNotIn(juben.UI_BEGIN, out)

    def test_phase_draw_vote_win(self):
        self._start("host")
        code, out, _ = run(["phase", "--to", "search"])
        self.assertEqual(code, 0)
        self.assertIn("搜证", out)
        code, out, _ = run(["draw"])
        self.assertEqual(code, 0)
        self.assertIn("公开线索", out)
        self.assertEqual(len(juben.load_state()["drawn"]), 1)
        run(["phase", "--to", "discuss"])
        run(["phase", "--to", "vote"])
        run(["vote", "--voter", "房东", "--target", "远房亲戚"])
        run(["vote", "--voter", "女佣", "--target", "远房亲戚"])
        code, out, _ = run(["vote", "--voter", "远房亲戚", "--target", "女佣"])
        self.assertEqual(code, 0)
        st = juben.load_state()
        self.assertEqual(st["status"], "ended")
        self.assertEqual(st["outcome"], "civilians_win")
        self.assertIn("真凶", out)

    def test_invalid_phase_skip(self):
        self._start()
        code, _, err = run(["phase", "--to", "vote"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_must_one_murderer(self):
        run(["init"])
        bad = [dict(r, is_murderer=False) for r in ROLES]
        code, _, err = run([
            "start",
            "--title",
            "雨夜别墅",
            "--public",
            PUBLIC,
            "--roles-json",
            json.dumps(bad, ensure_ascii=False),
            "--clues-json",
            json.dumps(CLUES, ensure_ascii=False),
            "--user-role",
            "host",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)


class TestSkillDocs(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_skill_frontmatter(self):
        text = (self.root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: juben", text)
        self.assertIn("/剧本杀", text)
        self.assertIn("JUBEN_UI_BEGIN", text)
        self.assertIn("disable-model-invocation: true", text)

    def test_version_file(self):
        self.assertEqual(
            (self.root / "VERSION").read_text(encoding="utf-8").strip(),
            "1.0.0",
        )


if __name__ == "__main__":
    unittest.main()
