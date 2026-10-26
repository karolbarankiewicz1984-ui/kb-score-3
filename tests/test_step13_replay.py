"""Step13 synthetic chronological replay, anti-lookahead, no-odds tests."""
import copy
from datetime import datetime, timezone
import unittest

from src.kb3_split import SplitSafetyError
from src.kb3_step13_replay import run_synthetic_fold, compare_synthetic_fold


def match(mid, kickoff, observed, label, home="SYN-TEAM-A", away="SYN-TEAM-B", role="TRAIN"):
    return {
        "fixture_id": "SYN-MATCH-" + mid, "kickoff_utc": kickoff,
        "result_observed_at_utc": observed, "label_90m": label,
        "home_team_id": home, "away_team_id": away, "partition": role,
    }


def fixture_source():
    # A train match older than the rolling 24-calendar-month window at fold2.
    return {"dataset_kind": "SYNTHETIC_REFERENCE_ONLY", "fixtures": [
        match("OLD", "2023-08-01T12:00:00Z", "2023-08-01T16:00:00Z", "H"),
        match("RECENT", "2024-08-01T12:00:00Z", "2024-08-01T16:00:00Z", "A"),
        match("VAL1", "2025-10-05T12:00:00Z", "2025-10-05T16:00:00Z", "H", role="VALIDATION"),
        match("VAL2", "2025-10-06T12:00:00Z", "2025-10-06T16:00:00Z", "D", role="VALIDATION"),
    ]}


def replay(data=None, *, method="EXPANDING"):
    return run_synthetic_fold(
        fixture_source() if data is None else data,
        fold=2, method=method,
        evaluation_asof_utc="2026-01-03T00:00:00Z")


class Step13TemporalReplayTests(unittest.TestCase):
    def test_paired_same_synthetic_matches_in_two_history_methods(self):
        both = compare_synthetic_fold(
            fixture_source(), fold=2, evaluation_asof_utc="2026-01-03T00:00:00Z")
        self.assertTrue(both["validation_paired"])
        self.assertFalse(both["real_historical_test"])
        self.assertEqual(both["expanding"]["training_synthetic_candidate_count"],2)
        self.assertEqual(both["rolling"]["training_synthetic_candidate_count"],1)
        self.assertEqual([r["fixture_id"] for r in both["expanding"]["prediction_rows"]],
                         [r["fixture_id"] for r in both["rolling"]["prediction_rows"]])
        self.assertNotEqual(
            both["expanding"]["prediction_rows"][0]["elo_home_before_kickoff"],
            both["rolling"]["prediction_rows"][0]["elo_home_before_kickoff"])

    def test_delay_prevents_future_result_leakage(self):
        data=fixture_source()
        data["fixtures"][2]["result_observed_at_utc"] = "2025-10-07T17:00:00Z"
        z=replay(data)["prediction_rows"]
        # Validation2 kickoff on Oct 6, earlier than Oct 7 observation.
        self.assertEqual(z[0]["applied_prior_observations"],2)
        self.assertEqual(z[1]["applied_prior_observations"],2)
        self.assertEqual(z[0]["elo_home_before_kickoff"],z[1]["elo_home_before_kickoff"])

    def test_result_observed_between_two_validation_matches_is_applied(self):
        z=replay()["prediction_rows"]
        self.assertEqual(z[0]["applied_prior_observations"],2)
        self.assertEqual(z[1]["applied_prior_observations"],3)
        self.assertNotEqual(z[0]["elo_home_before_kickoff"],z[1]["elo_home_before_kickoff"])
        self.assertAlmostEqual(sum(z[0]["p_1x2"].values()),1.0,places=12)

    def test_future_validation_label_does_not_change_earlier_predictions(self):
        data=fixture_source()
        baseline=replay(data)["prediction_rows"]
        data["fixtures"][3]["label_90m"]="A"
        changed=replay(data)["prediction_rows"]
        self.assertEqual(
            [row["p_1x2"] for row in baseline],
            [row["p_1x2"] for row in changed])
        # Metrics may change because outcome was altered after forecasts.
        self.assertNotEqual(replay()["synthetic_score_reference"]["multiclass_log_loss"],
                            replay(data)["synthetic_score_reference"]["multiclass_log_loss"])

    def test_future_heldout_test_rows_are_not_permitted(self):
        data=fixture_source()
        data["fixtures"].append(match(
            "TEST", "2026-10-10T12:00:00Z", "2026-10-10T16:00:00Z",
            "H", role="TEST"))
        with self.assertRaisesRegex(SplitSafetyError,"TEST_DENIED"):
            replay(data)

    def test_missing_real_provider_receipts_are_never_forged(self):
        data=fixture_source()
        data["dataset_kind"]="HISTORICAL_REAL"
        with self.assertRaisesRegex(SplitSafetyError,"REAL_DATA_DENIED"):
            replay(data)
        data=fixture_source()
        data["fixtures"][0]["fixture_id"]="m_real_pitch_id"
        with self.assertRaisesRegex(SplitSafetyError,"NON_SYNTHETIC"):
            replay(data)

    def test_odds_and_unknown_fields_disallowed(self):
        data=fixture_source()
        data["fixtures"][0]["market_odds"]=1.5
        with self.assertRaisesRegex(SplitSafetyError,"TAINT"):
            replay(data)

    def test_label_must_be_observed_after_kickoff_plus_three_hours(self):
        data=fixture_source()
        data["fixtures"][2]["result_observed_at_utc"]="2025-10-05T13:00:00Z"
        with self.assertRaisesRegex(SplitSafetyError,"EARLIER_THAN_POSSIBLE"):
            replay(data)

    def test_label_must_be_known_by_evaluation_asof(self):
        data=fixture_source()
        data["fixtures"][3]["result_observed_at_utc"]="2026-01-07T18:00:00Z"
        with self.assertRaisesRegex(SplitSafetyError,"NOT_OBSERVED"):
            replay(data)

    def test_calendar_rolling_is_not_730_fixed_days(self):
        r=replay(method="ROLLING_24_CALENDAR_MONTHS")
        self.assertEqual(r["history_window_from_utc"],"2023-10-01T00:00:00Z")
        self.assertTrue(r["real_historical_training_allowed"] is False)

    def test_future_label_of_unselected_train_does_not_count(self):
        data=fixture_source()
        data["fixtures"][0]["result_observed_at_utc"]="2025-10-07T17:00:00Z"
        r=replay(data)
        self.assertEqual(r["training_synthetic_candidate_count"],1)
        self.assertEqual(r["prediction_rows"][0]["applied_prior_observations"],1)

    def test_same_kickoff_matches_not_influence_each_other(self):
        data=fixture_source()
        data["fixtures"].append(match(
            "VAL3", "2025-10-06T12:00:00Z", "2025-10-06T16:00:00Z",
            "A", role="VALIDATION"))
        r=replay(data)
        simultaneous=[x for x in r["prediction_rows"] if x["kickoff_utc"]=="2025-10-06T12:00:00Z"]
        self.assertEqual(len(simultaneous),2)
        self.assertEqual(simultaneous[0]["elo_home_before_kickoff"],
                         simultaneous[1]["elo_home_before_kickoff"])
        self.assertEqual(simultaneous[0]["applied_prior_observations"],
                         simultaneous[1]["applied_prior_observations"])

    def test_replay_deterministic_and_synthetic_metrics_only(self):
        self.assertEqual(replay(),replay())
        r=replay()
        self.assertFalse(r["gate13_pass"])
        self.assertFalse(r["empirical_historical_performance"])
        self.assertFalse(r["real_pit_verified"])
        self.assertEqual(r["synthetic_score_reference"]["sample_size"],2)

    def test_invalid_partition_or_naive_time_rejected(self):
        data=fixture_source()
        data["fixtures"][1]["partition"]="VALIDATION"
        with self.assertRaisesRegex(SplitSafetyError,"PARTITION_OR_TEST_DENIED"):
            replay(data)
        data=fixture_source()
        data["fixtures"][0]["kickoff_utc"]="2023-08-01T12:00:00"
        with self.assertRaisesRegex(SplitSafetyError,"NAIVE_TIMESTAMP"):
            replay(data)


if __name__=="__main__":
    unittest.main()
