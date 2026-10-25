"""Offline unit tests for the Step 05 API-Football coverage audit."""
import unittest

from scripts.api_football_coverage_audit import (
    AuditAPI, MAX_CALLS, both_teams_stats, get_finished, sample_deterministic
)


class Step05CoverageTests(unittest.TestCase):
    def test_repeatable_two_samples(self):
        items = list(range(20))
        self.assertEqual(sample_deterministic(items), [5, 15])
        self.assertEqual(sample_deterministic(items), [5, 15])

    def test_tiny_and_empty_samples(self):
        self.assertEqual(sample_deterministic([]), [])
        self.assertEqual(sample_deterministic(["a"]), ["a"])

    def test_missing_stats_not_reported_as_zero(self):
        out = both_teams_stats({"response": []})
        self.assertEqual(out["state"], "NOT_AVAILABLE")
        self.assertEqual(out["complete_types"], [])

    def test_requires_both_teams_for_valid_stat(self):
        out = both_teams_stats({"response": [
            {"statistics": [{"type": "Fouls", "value": 0}, {"type": "Corner Kicks", "value": None}]},
            {"statistics": [{"type": "Fouls", "value": 13}, {"type": "Corner Kicks", "value": 4}]}
        ]})
        self.assertEqual(out["state"], "AVAILABLE")
        self.assertEqual(out["complete_types"], ["Fouls"])

    def test_finished_only(self):
        matches = [
            {"fixture": {"id": 3, "date": "2022-01-03", "status": {"short": "NS"}}},
            {"fixture": {"id": 1, "date": "2022-01-01", "status": {"short": "FT"}}},
            {"fixture": {"id": 2, "date": "2022-01-02", "status": {"short": "PST"}}},
        ]
        self.assertEqual([x["fixture"]["id"] for x in get_finished(matches)], [1])

    def test_audit_request_budget_hard_stop(self):
        api = AuditAPI("TEST_TOKEN_NOT_REAL")
        api.calls = MAX_CALLS
        with self.assertRaisesRegex(RuntimeError, "AUDIT_CALL_BUDGET_REACHED"):
            api.get("fixtures", league=39, season=2025)


if __name__ == "__main__":
    unittest.main()
