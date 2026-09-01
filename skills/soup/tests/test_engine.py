from __future__ import annotations

import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
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


SURFACE = "一个男人走进餐厅点了一碗汤喝了一口后离开了。"
TRUTH = "他曾在荒岛靠同伴的牺牲活下来，这碗汤让他想起那件事。"


class TestStartInfoSecret(CwdTest):
    def _start_ok(self, theme_resolved="日常"):
        run(["init"])
        return run([
            "start",
            "--surface", SURFACE,
            "--truth", TRUTH,
            "--theme-resolved", theme_resolved,
        ])

    def test_start_missing_args_fails(self):
        run(["init"])
        code, _, err = run(["start", "--surface", SURFACE, "--truth", TRUTH])
        self.assertNotEqual(code, 0)
        self.assertEqual(soup.load_state()["status"], "configuring")

    def test_start_short_surface_fails(self):
        run(["init"])
        code, _, err = run([
            "start", "--surface", "太短了", "--truth", TRUTH,
            "--theme-resolved", "日常",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(soup.load_state()["status"], "configuring")

    def test_start_then_info_has_surface_not_truth(self):
        code, out, _ = self._start_ok()
        self.assertEqual(code, 0)
        self.assertIn(SURFACE, out)
        self.assertNotIn(TRUTH, out)
        self.assertIn("汤面", out)
        self.assertNotIn("汤底", out)
        self.assertIn("主题：随机 → 日常", out)
        st = soup.load_state()
        self.assertEqual(st["status"], "playing")
        self.assertEqual(st["truth"], TRUTH)

    def test_info_does_not_print_truth(self):
        self._start_ok()
        code, out, _ = run(["info"])
        self.assertEqual(code, 0)
        self.assertIn(SURFACE, out)
        self.assertNotIn(TRUTH, out)

    def test_secret_prints_truth_without_ui(self):
        self._start_ok()
        code, out, _ = run(["secret"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), TRUTH)
        self.assertNotIn(soup.UI_BEGIN, out)

    def test_secret_before_start_fails(self):
        run(["init"])
        code, _, err = run(["secret"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)

    def test_theme_resolved_must_match_chosen_theme(self):
        run(["init"])
        run(["set", "--theme", "职场"])
        code, _, err = run([
            "start", "--surface", SURFACE, "--truth", TRUTH,
            "--theme-resolved", "黑暗",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)


class TestLogRevealNext(CwdTest):
    def _play(self):
        run(["init"])
        run(["set", "--theme", "校园", "--difficulty", "困难"])
        run([
            "start", "--surface", SURFACE, "--truth", TRUTH,
            "--theme-resolved", "校园",
        ])

    def test_log_appears_in_info(self):
        self._play()
        code, out, _ = run(["log", "--q", "他是自杀的吗？", "--a", "不是"])
        self.assertEqual(code, 0)
        self.assertIn("他是自杀的吗？", out)
        self.assertIn("不是", out)
        self.assertNotIn(TRUTH, out)

    def test_log_rejects_bad_answer(self):
        self._play()
        code, _, err = run(["log", "--q", "？", "--a", "也许"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(soup.load_state()["qa"], [])

    def test_reveal_won_shows_truth(self):
        self._play()
        code, out, _ = run(["reveal", "--won"])
        self.assertEqual(code, 0)
        self.assertIn(TRUTH, out)
        self.assertIn("汤底", out)
        self.assertEqual(soup.load_state()["status"], "revealed")
        self.assertEqual(soup.load_state()["outcome"], "won")

    def test_giveup_shows_truth(self):
        self._play()
        code, out, _ = run(["giveup"])
        self.assertEqual(code, 0)
        self.assertIn(TRUTH, out)
        self.assertEqual(soup.load_state()["outcome"], "given_up")

    def test_init_during_play_does_not_clobber(self):
        self._play()
        code, _, err = run(["init"])
        self.assertNotEqual(code, 0)
        self.assertIn("ERROR", err)
        self.assertEqual(soup.load_state()["status"], "playing")
        self.assertEqual(soup.load_state()["truth"], TRUTH)

    def test_next_back_to_config_keeps_theme(self):
        self._play()
        run(["giveup"])
        code, out, _ = run(["next"])
        self.assertEqual(code, 0)
        st = soup.load_state()
        self.assertEqual(st["status"], "configuring")
        self.assertEqual(st["theme"], "校园")
        self.assertEqual(st["difficulty"], "困难")
        self.assertIsNone(st["surface"])
        self.assertIsNone(st["truth"])
        self.assertEqual(st["qa"], [])
        self.assertIsNone(st["theme_resolved"])
        self.assertNotIn(SURFACE, out)
        self.assertNotIn(TRUTH, out)


if __name__ == "__main__":
    unittest.main()
