import unittest
from datetime import datetime, timedelta, timezone
from scripts.kb3_v3_offline_readiness_triage import assess_readiness


class TestV3OfflineReadiness(unittest.TestCase):
    def setUp(self):
        self.kickoff = datetime(2026, 11, 20, 20, tzinfo=timezone.utc)
        self.cutoff = self.kickoff - timedelta(minutes=90)

    def test_empty_window_is_not_selector_failure(self):
        self.assertEqual(assess_readiness(0, 0), "NO_FIXTURES_IN_WINDOW")

    def test_missing_selection_requires_replay(self):
        self.assertEqual(assess_readiness(2, 0), "SELECTOR_MISMATCH_REQUIRES_OFFLINE_REPLAY")

    def test_inconsistent_counts_fail_closed(self):
        self.assertEqual(assess_readiness(1, 2), "SELECTOR_COUNT_INCONSISTENT")

    def test_no_host_timestamp(self):
        self.assertEqual(assess_readiness(1, 1), "MISSING_INDEPENDENT_HOST_TIME")

    def test_exact_cutoff_rejected(self):
        self.assertEqual(assess_readiness(1, 1, self.kickoff, self.cutoff, True),
                         "SOURCE_NOT_BEFORE_EXACT_CUTOFF")

    def test_after_cutoff_rejected(self):
        self.assertEqual(assess_readiness(1, 1, self.kickoff, self.cutoff + timedelta(seconds=1), True),
                         "SOURCE_NOT_BEFORE_EXACT_CUTOFF")

    def test_before_cutoff_without_builder_rejected(self):
        self.assertEqual(assess_readiness(1, 1, self.kickoff, self.cutoff - timedelta(seconds=1), False),
                         "ORIGINAL_BUILDER_87_NOT_VERIFIED")

    def test_before_cutoff_with_builder_is_research_only(self):
        self.assertEqual(assess_readiness(1, 1, self.kickoff, self.cutoff - timedelta(seconds=1), True),
                         "RESEARCH_FORWARD_87_VERIFIED_NOT_PIT_TRAIN")


if __name__ == "__main__":
    unittest.main()
