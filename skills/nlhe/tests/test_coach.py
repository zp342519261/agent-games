import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import nlhe_coach as coach


class TestNormalizeHand(unittest.TestCase):
    def test_pair(self):
        self.assertEqual(coach.normalize_hand(["Ah", "Ad"]), "AA")

    def test_suited(self):
        self.assertEqual(coach.normalize_hand(["Ah", "Kh"]), "AKs")

    def test_offsuit_order(self):
        self.assertEqual(coach.normalize_hand(["Kd", "As"]), "AKo")


class TestPotOdds(unittest.TestCase):
    def test_facing_bet(self):
        self.assertAlmostEqual(coach.pot_odds_needed(80, 20), 0.20)

    def test_no_call(self):
        self.assertIsNone(coach.pot_odds_needed(100, 0))


class TestSpotKey(unittest.TestCase):
    def _base_state(self, n=6, street="preflop", button=0, hero=0):
        players = []
        for i in range(n):
            players.append({
                "id": i,
                "stack": 1000 if i != hero else 990,
                "bet": 10 if i != hero else 0,
                "folded": False,
                "all_in": False,
                "is_human": i == hero,
                "hole": ["Ah", "Kh"] if i == hero else ["2c", "3d"],
                "acted": False,
            })
        return {
            "street": street,
            "button": button,
            "bb": 10,
            "sb": 5,
            "pot": 15,
            "board": [],
            "players": players,
            "to_act": hero,
            "history": [],
        }

    def test_non_6max_miss_reason(self):
        st = self._base_state(n=4)
        key = coach.build_spot_key(st)
        self.assertEqual(key["miss_reason"], "players_not_6")

    def test_btn_rfi_preflop(self):
        st = self._base_state(n=6, button=0, hero=0)
        key = coach.build_spot_key(st)
        self.assertIsNone(key.get("miss_reason"))
        self.assertEqual(key["hero_pos"], "BTN")
        self.assertEqual(key["line"], "rfi")
        self.assertEqual(key["hero_hand"], "AKs")
        self.assertEqual(key["eff_bb"], 100)


class TestChartLookup(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / "charts"

    def test_hit_btn_rfi_aks(self):
        key = {
            "spot_id": "6max_100bb_btn_rfi",
            "hero_hand": "AKs",
            "miss_reason": None,
        }
        hit = coach.lookup_chart(self.root, key)
        self.assertTrue(hit["hit"])
        self.assertEqual(hit["freqs"]["raise"], 1.0)

    def test_miss_unknown_spot(self):
        key = {"spot_id": "nope", "hero_hand": "AA", "miss_reason": None}
        hit = coach.lookup_chart(self.root, key)
        self.assertFalse(hit["hit"])
        self.assertEqual(hit["reason"], "spot_file_missing")

    def test_miss_combo(self):
        key = {"spot_id": "6max_100bb_btn_rfi", "hero_hand": "33", "miss_reason": None}
        hit = coach.lookup_chart(self.root, key)
        self.assertFalse(hit["hit"])
        self.assertEqual(hit["reason"], "combo_not_in_chart")


class TestEquityAndCoachText(unittest.TestCase):
    def test_suggest_argmax(self):
        self.assertEqual(coach.suggest_action({"fold": 0.2, "raise": 0.8}), "raise")

    def test_coach_text_contains_no_fake_freq_on_miss(self):
        state = {
            "street": "preflop", "pot": 30, "bb": 10, "button": 0,
            "players": [
                {"id": 0, "is_human": True, "hole": ["Ah", "Kh"], "stack": 990, "bet": 0, "folded": False},
                {"id": 1, "is_human": False, "hole": ["2c", "2d"], "stack": 980, "bet": 20, "folded": False},
            ],
            "history": [{"seat": 1, "action": "raise"}],
            "board": [], "to_act": 0, "status": "awaiting_human",
        }
        text = coach.render_coach_block(state, charts_root=Path("/tmp/empty_charts"))
        self.assertIn("NO_CHART", text)
        self.assertNotRegex(text, r"GTO: raise 0\.\d+")


class TestReview(unittest.TestCase):
    def test_review_compares_action(self):
        freqs = {"fold": 0.0, "raise": 1.0}
        line = coach.format_review_line(
            street="preflop", hand="AKs", hero_action="call", freqs=freqs
        )
        self.assertIn("call", line)
        self.assertIn("raise 100%", line)
        self.assertIn("谱外", line)


if __name__ == "__main__":
    unittest.main()
