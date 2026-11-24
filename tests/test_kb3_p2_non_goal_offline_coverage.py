import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.kb3_p2_non_goal_offline_coverage import (
    FIELDS, audit_connection, audit_sqlite, count_stat, inspect_items,
)


class CoverageTests(unittest.TestCase):
    def sample(self):
        return [{"key": key, "home": 5, "away": 2} for key in FIELDS.values()]

    def test_exact_provider_keys_and_sides(self):
        result = inspect_items(self.sample())
        self.assertEqual(set(result), set(FIELDS))
        self.assertTrue(all(v["both_sides_present"] for v in result.values()))
        self.assertEqual(result["FOULS"]["away"], 2)

    def test_missing_is_not_zero_and_aliases_not_guessed(self):
        result = inspect_items([{"key": "Fouls", "home": 1, "away": 2}])
        self.assertIsNone(result["FOULS"]["home"])
        self.assertEqual(result["FOULS"]["home_status"], "FIELD_MISSING")

    def test_conflicting_duplicate_blocks_only_affected_side(self):
        items = self.sample() + [{"key": "corners", "home": 9, "away": 2}]
        result = inspect_items(items)
        self.assertEqual(result["CORNERS"]["home_status"], "CONFLICTING_DUPLICATE")
        self.assertIsNone(result["CORNERS"]["home"])
        self.assertEqual(result["CORNERS"]["away"], 2)
        self.assertTrue(result["FOULS"]["both_sides_present"])

    def test_identical_duplicate_is_not_double_counted(self):
        item = {"key": "fouls", "home": "13", "away": 9}
        self.assertEqual(count_stat([item, item], "fouls", "home"), (13, "VALUE_PRESENT_RESEARCH_ONLY"))

    def test_reject_negative_float_fraction_nan_bool_and_empty(self):
        for invalid in (-1, 1.2, float("nan"), float("inf"), True, None, "", "-", "2.5", "bad"):
            with self.subTest(invalid=invalid):
                value, status = count_stat([{"key": "fouls", "home": invalid}], "fouls", "home")
                self.assertIsNone(value)
                self.assertNotEqual(status, "VALUE_PRESENT_RESEARCH_ONLY")
        self.assertEqual(count_stat([{"key": "fouls", "home": 0}], "fouls", "home")[0], 0)

    def test_reject_malformed_items_and_shot_contradiction(self):
        self.assertEqual(count_stat(None, "fouls", "home")[1], "MALFORMED_ITEMS")
        items = self.sample()
        next(x for x in items if x["key"] == "ShotsOnTarget")["home"] = 8
        result = inspect_items(items)
        self.assertEqual(result["SHOTS_TOTAL"]["home_status"], "SHOTS_SUBCATEGORY_CONTRADICTION")
        self.assertEqual(result["SHOTS_ON_TARGET"]["home_status"], "SHOTS_SUBCATEGORY_CONTRADICTION")
        self.assertTrue(result["CORNERS"]["both_sides_present"])

    def test_db_is_readonly_and_aggregate_has_no_native_ids(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "research.sqlite"
            with sqlite3.connect(path) as db:
                db.executescript("""CREATE TABLE observations (
                    scope TEXT, season TEXT, match_id TEXT, home_team_id TEXT,
                    away_team_id TEXT, stat_items_json TEXT);""")
                db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?)",
                           ("FRA", "2025/2026", "m_secret", "t_home", "t_away", json.dumps(self.sample())))
            result = audit_sqlite(path)
            self.assertEqual(result["observations"], 1)
            self.assertEqual(result["per_scope"]["FRA"]["complete_pair_by_family"]["FOULS"], 1)
            self.assertFalse(result["settlement_eligible"])
            self.assertFalse(result["period_90_minutes_independently_proven"])
            self.assertNotIn("m_secret", json.dumps(result))
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 1)

    def test_schema_and_team_id_mismatch_fail_closed(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE observations(scope TEXT, season TEXT, match_id TEXT, home_team_id TEXT, away_team_id TEXT, stat_items_json TEXT)")
            db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?)", ("FRA", "2025/2026", "m1", "t1", "t1", "[]"))
            with self.assertRaisesRegex(ValueError, "OBSERVATION_FIXTURE_IDENTITY_INVALID"):
                audit_connection(db)

    def test_unknown_rows_and_bad_json_are_not_credited(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE observations(scope TEXT, season TEXT, match_id TEXT, home_team_id TEXT, away_team_id TEXT, stat_items_json TEXT)")
            db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?)", ("POL", "2025/2026", "m1", "t1", "t2", "not json"))
            report = audit_connection(db)
            self.assertEqual(report["per_scope"]["POL"]["complete_pair_by_family"]["FOULS"], 0)
            self.assertEqual(report["per_scope"]["POL"]["side_reason_by_family"]["FOULS"]["MALFORMED_ITEMS"], 2)


if __name__ == "__main__":
    unittest.main()
