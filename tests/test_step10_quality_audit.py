"""GATE10 negative-test suite; tests do not require an API key or live data."""
import datetime as dt
import unittest

from scripts.step10_quality_audit import (
    assess_fixture, parse_time, prematch_source_decision,
)

KICKOFF="2025-01-01T19:00:00Z"
CUTOFF="2025-01-01T15:00:00Z"
OLD="2024-12-31T14:00:00Z"

def row(**changes):
    r={"kickoff_utc":KICKOFF,"home_team_id":1,"away_team_id":2,
       "status":"FINISHED","goals_home_90":2,"goals_away_90":1}
    r.update(changes)
    return r

def source(**changes):
    r={"fixture_kickoff":KICKOFF,"feature_cutoff":CUTOFF,
       "observed_at":OLD,"published_at":OLD,
       "availability":"VERIFIED_PREMATCH",
       "source_match_id":"prior-match","target_match_id":"target-match",
       "contains_match_outcome":True}
    r.update(changes)
    return prematch_source_decision(**r)

class Gate10Tests(unittest.TestCase):
    def test_positive_fixture(self):
        self.assertEqual(assess_fixture(row()),[])

    def test_reject_invalid_kickoff(self):
        self.assertIn("INVALID_KICKOFF",assess_fixture(row(kickoff_utc="NO_DATE")))

    def test_reject_noncanonical_timezone(self):
        self.assertIn("NONCANONICAL_UTC",assess_fixture(
            row(kickoff_utc="2025-01-01T20:00:00+01:00")))

    def test_reject_outside_season(self):
        self.assertIn("KICKOFF_OUTSIDE_SEASON",assess_fixture(
            row(kickoff_utc="2026-01-01T19:00:00Z")))

    def test_reject_own_opponent(self):
        self.assertIn("SAME_HOME_AWAY",assess_fixture(row(away_team_id=1)))

    def test_reject_no_regulation_result(self):
        self.assertIn("MISSING_OR_INVALID_REGULATION_GOALS_goals_home_90",
                      assess_fixture(row(goals_home_90=None)))

    def test_reject_unfinished_in_complete_season(self):
        self.assertIn("INCOMPLETE_SEASON_STATUS",assess_fixture(row(status="SCHEDULED")))

    def test_reject_outlier_not_impute(self):
        self.assertIn("OUTLIER_GOALS_REVIEW_goals_home_90",
                      assess_fixture(row(goals_home_90=35)))

    def test_accept_proven_historical_prior_match(self):
        self.assertTrue(source()["eligible"])

    def test_reject_target_result_as_feature(self):
        decision=source(source_match_id="target-match")
        self.assertFalse(decision["eligible"])
        self.assertIn("TARGET_OUTCOME_LEAKAGE",decision["reasons"])

    def test_reject_late_publication(self):
        s=source(published_at="2025-01-01T17:00:00Z")
        self.assertIn("PUBLISHED_AFTER_CUTOFF",s["reasons"])

    def test_reject_late_observation(self):
        s=source(observed_at="2025-01-01T18:00:00Z")
        self.assertIn("OBSERVED_AFTER_CUTOFF",s["reasons"])

    def test_reject_unknown_publication_time(self):
        s=source(published_at=None)
        self.assertIn("MISSING_SOURCE_AVAILABILITY_PROOF",s["reasons"])

    def test_reject_retrospective_own_fixture(self):
        s=source(availability="RETROSPECTIVE",source_match_id="target-match")
        self.assertIn("NOT_VERIFIED_PREMATCH",s["reasons"])
        self.assertIn("TARGET_OUTCOME_LEAKAGE",s["reasons"])

    def test_reject_cutoff_at_or_after_kickoff(self):
        s=source(feature_cutoff="2025-01-01T20:00:00Z")
        self.assertIn("CUTOFF_AT_OR_AFTER_KICKOFF",s["reasons"])

    def test_reject_naive_time(self):
        with self.assertRaises(ValueError):
            parse_time("2025-01-01T19:00:00")

if __name__=="__main__":
    unittest.main()
