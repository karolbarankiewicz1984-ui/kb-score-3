"""Offline-only step15 repair: no provider, no training, no protected TEST."""
import unittest
from scripts.step15_offline_reaudit import (
    MODELS, REL_FROZEN, REL_REPORT, REL_SECOND, OfflineStep15Error,
    require, audit,
)


class Step15OfflineReauditTests(unittest.TestCase):
    def test_paths_are_stable_archived_20261029(self):
        self.assertEqual(len(MODELS), 2)
        self.assertTrue(REL_FROZEN.endswith("20261029.jsonl.gz"))
        self.assertTrue(REL_REPORT.endswith("20261029.json"))
        self.assertTrue(REL_SECOND.endswith("20261029.json"))

    def test_fail_closed_helper(self):
        with self.assertRaises(OfflineStep15Error):
            require(False, "EXPECTED_FAIL")
        require(True, "OK")

    def test_original_repository_archive_integrity(self):
        result = audit()
        self.assertEqual(result["status"],
                         "PASS_OFFLINE_ARCHIVE_INTEGRITY_AND_POISSON_JOINT")
        self.assertEqual(result["provider_api_calls"], 0)
        self.assertEqual(result["model_by_fixture_joint_checks"], 748)
        self.assertEqual(result["m0_wins_brier_markets"], 22)
        self.assertEqual(result["m0_wins_log_loss_markets"], 22)
        self.assertFalse(result["test_season_accessed"])
        self.assertFalse(result["production_promotion"])


if __name__ == "__main__":
    unittest.main()
