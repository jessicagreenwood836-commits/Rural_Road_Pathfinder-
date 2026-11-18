"""Tests for roads.py + rules.pl. Run: python3 -m unittest test_roads -v
Each test works on a temp copy of the project, so roads.pl is never touched."""
import os
import shutil
import tempfile
import unittest

import roads


class RoadsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for name in ("roads.pl", "rules.pl"):
            shutil.copy(os.path.join(roads.HERE, name), self.tmp)
        self.saved = (roads.HERE, roads.ROADS_FILE, roads.RULES_FILE)
        roads.HERE = self.tmp
        roads.ROADS_FILE = os.path.join(self.tmp, "roads.pl")
        roads.RULES_FILE = os.path.join(self.tmp, "rules.pl")

    def tearDown(self):
        roads.HERE, roads.ROADS_FILE, roads.RULES_FILE = self.saved
        shutil.rmtree(self.tmp)

    def road(self, a, b):
        rs, _ = roads.load_roads()
        return roads.find_road(rs, a, b)

    def edges(self):
        return {(s, d) for s, d, _, _ in roads.query_prolog("dump_edges")}

    def test_plus_five_once_for_cisterns_and_potholes(self):
        self.assertEqual(self.road("Half Way Tree", "Papine")["effective_mins"], 18 + 5)
        # cisterns + deep potholes together still add 5 once
        self.assertEqual(self.road("Gordon Town", "Mavis Bank")["effective_mins"], 30 + 5)

    def test_pothole_over_3_inches_is_inferred(self):
        r = self.road("Harbour View", "Bull Bay")      # 2 in: no delay
        self.assertEqual(r["effective_mins"], r["mins"])
        rs, season = roads.load_roads()
        roads.find_road(rs, "Harbour View", "Bull Bay")["pothole_inches"] = 4.0
        roads.save_roads(rs, season)                    # 4 in, not stored as a condition
        r = self.road("Harbour View", "Bull Bay")
        self.assertEqual(r["effective_mins"], r["mins"] + 5)
        self.assertIn("inferred deep_potholes", r["reasons"])

    def test_closures(self):
        self.assertEqual(self.road("Stony Hill", "Lawrence Tavern")["effective_status"], "closed")
        self.assertEqual(self.road("Papine", "Irish Town")["effective_status"], "closed")
        self.assertEqual(self.road("Papine", "Gordon Town")["effective_status"], "open")

    def test_falling_rocks_warns_but_stays_open(self):
        r = self.road("Papine", "Gordon Town")
        self.assertEqual(r["effective_status"], "open")
        self.assertIn("falling rocks", r["reasons"])

    def test_rainy_season_closes_seasonal_roads(self):
        rs, _ = roads.load_roads()
        roads.save_roads(rs, "rainy")
        self.assertEqual(self.road("Papine", "Gordon Town")["effective_status"], "closed")
        self.assertNotIn(("Papine", "Gordon Town"), self.edges())

    def test_one_way_not_reversed_two_way_is_(self):
        edges = self.edges()
        self.assertIn(("Downtown Kingston", "Cross Roads"), edges)
        self.assertNotIn(("Cross Roads", "Downtown Kingston"), edges)
        self.assertIn(("Papine", "Cross Roads"), edges)
        self.assertNotIn(("Irish Town", "Papine"), edges)     # closed

    def test_save_load_round_trip_and_no_temp_file(self):
        rs, season = roads.load_roads()
        new = {"source": "Mary's Town", "dest": "Papine", "km": 2.5, "mins": 7,
               "type": "paved", "conditions": ["falling_rocks"], "pothole_inches": 3.5,
               "status": "open", "direction": "one_way", "seasonal": "none"}
        self.assertEqual(roads.validate_road(new), [])
        roads.save_roads(rs + [new], season)
        got = self.road("Mary's Town", "Papine")
        self.assertEqual((got["km"], got["mins"], got["conditions"], got["pothole_inches"]),
                         (2.5, 7, ["falling_rocks"], 3.5))
        self.assertEqual(got["effective_mins"], 12)           # 3.5 in => deep => +5
        self.assertFalse(os.path.exists(roads.ROADS_FILE + ".tmp"))

    def test_parallel_roads_do_not_mix_state(self):
        base = {"source": "Aa", "dest": "Bb", "type": "paved", "pothole_inches": 0.0,
                "direction": "two_way", "seasonal": "none"}
        open_road = {**base, "km": 5.0, "mins": 10, "conditions": [], "status": "open"}
        shut_road = {**base, "km": 9.0, "mins": 20, "conditions": ["broken_cisterns",
                     "broken_cisterns"], "status": "closed", "direction": "one_way"}
        roads.save_roads([open_road, shut_road], "dry")
        rs, _ = roads.load_roads()
        self.assertEqual([(r["effective_mins"], r["effective_status"]) for r in rs],
                         [(10, "open"), (25, "closed")])
        self.assertEqual(rs[1]["reasons"].count("broken_cisterns"), 1)   # listed once
        self.assertEqual(roads.query_prolog("dump_edges"),
                         [["Aa", "Bb", "5", "10"], ["Bb", "Aa", "5", "10"]])

    def test_non_ascii_digit_choice_is_rejected_not_a_crash(self):
        from unittest import mock
        import contextlib
        import io
        with mock.patch("builtins.input", side_effect=["\u00b2", "1"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(roads.ask_choice("Pick", ("x", "y")), "x")

    def test_swap_accepts_yes(self):
        import contextlib
        import io
        from unittest import mock
        rs, season = roads.load_roads()
        answers = ["Cross Roads", "Downtown Kingston"] + [""] * 8 + ["yes"]
        with mock.patch("builtins.input", side_effect=answers), \
                contextlib.redirect_stdout(io.StringIO()):
            roads.update_road(rs, season)
        self.assertIsNotNone(self.road("Cross Roads", "Downtown Kingston"))
        self.assertEqual(self.road("Cross Roads", "Downtown Kingston")["source"], "Cross Roads")

    def test_dry_season_reports_no_seasonal_closures(self):
        import contextlib
        import io
        from unittest import mock
        rs, season = roads.load_roads()
        roads.find_road(rs, "Papine", "Gordon Town")["status"] = "closed"   # admin block
        roads.save_roads(rs, "dry")
        rs, season = roads.load_roads()
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=["1"]), contextlib.redirect_stdout(out):
            roads.set_season(rs, season)
        self.assertIn("Seasonal roads closed: none", out.getvalue())

    def test_non_ascii_names_survive_any_locale(self):
        for loc in ("C", "xx_YY.UTF-8"):
            with self.subTest(locale=loc):
                os.environ["LC_ALL"] = loc
                try:
                    rs, season = roads.load_roads()
                    rs.append({"source": "Caf\u00e9 \u00d1u", "dest": "Papine", "km": 1.0,
                               "mins": 2, "type": "paved", "conditions": [],
                               "pothole_inches": 0.0, "status": "open",
                               "direction": "two_way", "seasonal": "none"})
                    roads.save_roads(rs, season)
                    self.assertIsNotNone(self.road("Caf\u00e9 \u00d1u", "Papine"))
                    self.assertIn(("Caf\u00e9 \u00d1u", "Papine"), self.edges())
                finally:
                    del os.environ["LC_ALL"]

    def test_failed_save_keeps_old_file_and_leaves_no_temp(self):
        from unittest import mock
        with open(roads.ROADS_FILE, encoding="utf-8") as fh:
            before = fh.read()
        rs, season = roads.load_roads()
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                roads.save_roads(rs, "rainy")
        with open(roads.ROADS_FILE, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before)
        self.assertFalse(os.path.exists(roads.ROADS_FILE + ".tmp"))

    def test_canon_place_reuses_existing_spelling(self):
        rs, _ = roads.load_roads()
        self.assertEqual(roads.canon_place(rs, "papine"), "Papine")
        self.assertEqual(roads.canon_place(rs, "half way tree"), "Half Way Tree")
        self.assertEqual(roads.canon_place(rs, "Yallahs"), "Yallahs")

    def test_validation_rejects_bad_roads(self):
        good = {"source": "A", "dest": "B", "km": 1.0, "mins": 1, "type": "paved",
                "conditions": [], "pothole_inches": 0.0, "status": "open",
                "direction": "two_way", "seasonal": "none"}
        self.assertEqual(roads.validate_road(good), [])
        for change in ({"dest": "a"}, {"km": 0.0}, {"km": float("nan")}, {"mins": 0},
                       {"pothole_inches": -1.0}, {"type": "gravel"},
                       {"conditions": ["lava"]}, {"source": "A\tB"}, {"dest": "x\\y"}):
            self.assertTrue(roads.validate_road({**good, **change}), change)

    def test_readme_demo_add_and_update(self):
        import contextlib
        import io
        from unittest import mock
        rs, season = roads.load_roads()
        out = io.StringIO()
        # Demo 1: lowercase 'bull bay' must join the existing Bull Bay node.
        add = ["bull bay", "Yallahs", "12", "20", "1", "0", "4", "1", "2", "1"]
        with mock.patch("builtins.input", side_effect=add), contextlib.redirect_stdout(out):
            roads.add_road(rs, season)
        self.assertIn("inferred deep_potholes", out.getvalue())
        self.assertIn("now:    25 min, open", out.getvalue())
        self.assertIn(("Bull Bay", "Yallahs"), self.edges())
        self.assertNotIn("bull bay", {p for r in roads.load_roads()[0]
                                      for p in (r["source"], r["dest"])})
        # Demo 2: cisterns + severely damaged => 17 min, closed.
        rs, season = roads.load_roads()
        out = io.StringIO()
        upd = ["Half Way Tree", "Constant Spring", "", "", "", "1,3", "", "", "", ""]
        with mock.patch("builtins.input", side_effect=upd), contextlib.redirect_stdout(out):
            roads.update_road(rs, season)
        self.assertIn("before: 12 min, open", out.getvalue())
        self.assertIn("now:    17 min, closed", out.getvalue())

    def test_show_roads_columns_stay_apart_for_long_names(self):
        rs, season = roads.load_roads()
        rs[0]["source"] = "A Very Long Village Name Indeed"
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            roads.show_roads(rs, season)
        line = [l for l in out.getvalue().splitlines() if "A Very Long" in l][0]
        self.assertIn("Indeed  Cross Roads", line)


if __name__ == "__main__":
    unittest.main()
