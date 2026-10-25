"""Offline contract checks for KB Score 3.0 API-Football audit.

No API key needed, no network requests.
"""
import unittest

from scripts.step05_api_football_audit import (
    FINAL_STATUSES, LEAGUES, SEASONS, MAX_CALLS,
    choose_samples, stats_flags, lineup_flag,
)


class CoverageAuditContract(unittest.TestCase):
    def test_fixed_matrix_and_budget(self):
        self.assertEqual(len(LEAGUES), 5)
        self.assertEqual(len(SEASONS), 5)
        self.assertEqual(len(LEAGUES) * len(SEASONS), 25)
        # status + leagues, fixtures, 2 stats, 1 lineup each + odds for 5 leagues
        self.assertGreaterEqual(MAX_CALLS, 1 + 25 * 5 + 5)
        self.assertLessEqual(MAX_CALLS, 150)

    def test_finished_matches_only_and_stable_order(self):
        def fixture(fid, date, status):
            return {"fixture": {"id": fid, "date": date,
                                 "status": {"short": status}}}
        items = [
            fixture(13, "2024-01-04T12:00:00Z", "FT"),
            fixture(11, "2024-01-01T12:00:00Z", "FT"),
            fixture(16, "2024-01-05T12:00:00Z", "NS"),
            fixture(14, "2024-01-03T12:00:00Z", "AET"),
            fixture(12, "2024-01-02T12:00:00Z", "FT"),
        ]
        self.assertEqual(choose_samples(items), choose_samples(list(reversed(items))))
        self.assertTrue(all(id != 16 for id in choose_samples(items)))
        self.assertEqual(FINAL_STATUSES, {"FT", "AET", "PEN"})

    def test_null_is_missing_not_zero(self):
        source = [
            {"statistics": [{"type": "Fouls", "value": None},
                            {"type": "Corner Kicks", "value": 0}]},
            {"statistics": [{"type": "Fouls", "value": 12},
                            {"type": "Corner Kicks", "value": 0}]},
        ]
        output = stats_flags(source)
        self.assertFalse(output["both_by_type"]["Fouls"])
        self.assertTrue(output["both_by_type"]["Corner Kicks"])
        self.assertTrue(output["both_any"])

    def test_partial_statistics_not_two_team_coverage(self):
        self.assertFalse(stats_flags([{"statistics": [{"type": "Fouls", "value": 10}]}])["both_any"])
        self.assertFalse(stats_flags([])["both_any"])

    def test_lineups_require_two_starting_elevens(self):
        self.assertTrue(lineup_flag([
            {"startXI": [{"player": {"id": i}} for i in range(11)]},
            {"startXI": [{"player": {"id": i}} for i in range(11)]},
        ]))
        self.assertFalse(lineup_flag([
            {"startXI": [{"player": {"id": i}} for i in range(10)]},
            {"startXI": [{"player": {"id": i}} for i in range(11)]},
        ]))


if __name__ == "__main__":
    unittest.main()
