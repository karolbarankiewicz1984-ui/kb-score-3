"""Step13 v0.3: synthetic TRAIN-only Poisson profile MLE acceptance tests."""
import copy
import math
import unittest
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_poisson_train import (
    FIXED_GRID, fit_synthetic_poisson_train, forecast_from_synthetic_fit,
)


def example():
    rows=[]
    for i in range(12):
        rows.append({
            "fixture_id":f"SYN-MATCH-{i:02d}",
            "home_team_id":f"SYN-TEAM-{i%4:02d}",
            "away_team_id":f"SYN-TEAM-{(i+1)%4:02d}",
            "kickoff_utc":f"2024-10-{i+1:02d}T15:00:00Z",
            "feature_cutoff_utc":f"2024-10-{i+1:02d}T12:00:00Z",
            "result_observed_at_utc":f"2024-10-{i+1:02d}T19:00:00Z",
            "home_elo_before_kickoff":1450.0+(i%4)*40,
            "away_elo_before_kickoff":1500.0+(i%3)*20,
            "goals_home_90":(i%3)+1,
            "goals_away_90":i%2,
            "partition":"TRAIN",
            "source_type":"SYNTHETIC_REFERENCE_ONLY",
        })
    return rows


def fit(rows=None, freeze="2025-10-01T00:00:00Z"):
    return fit_synthetic_poisson_train(example() if rows is None else rows,
                                      freeze_utc=freeze)


class Step13PoissonTrainTests(unittest.TestCase):
    def test_synthetic_profile_mle_and_correct_flags(self):
        r=fit()
        self.assertEqual(r["synthetic_train_n"],12)
        self.assertIn(r["fitted_parameters"]["elo_goal_elasticity"],FIXED_GRID)
        self.assertGreater(r["fitted_parameters"]["base_home_goals"],0)
        self.assertGreater(r["fitted_parameters"]["base_away_goals"],0)
        self.assertTrue(math.isfinite(r["selected_train_nll_total"]))
        self.assertFalse(r["validation_labels_read"])
        self.assertFalse(r["test_labels_read"])
        self.assertFalse(r["real_historical_model_fitted"])
        self.assertFalse(r["empirical_historical_performance"])
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["gate13_pass"])

    def test_profile_mle_has_correct_weighted_score_equations(self):
        rows=example()
        r=fit(rows)
        e=r["fitted_parameters"]["elo_goal_elasticity"]
        d=[(x["home_elo_before_kickoff"]-x["away_elo_before_kickoff"])/400
           for x in rows]
        weighted_home=math.fsum(math.exp(e*x) for x in d)
        weighted_away=math.fsum(math.exp(-e*x) for x in d)
        expected_h=sum(x["goals_home_90"] for x in rows)/weighted_home
        expected_a=sum(x["goals_away_90"] for x in rows)/weighted_away
        self.assertAlmostEqual(r["fitted_parameters"]["base_home_goals"],expected_h)
        self.assertAlmostEqual(r["fitted_parameters"]["base_away_goals"],expected_a)

    def test_candidate_can_generate_probabilities_but_not_betting_status(self):
        candidate=fit()
        p=forecast_from_synthetic_fit(candidate,1500,1500)
        self.assertAlmostEqual(sum(p["p_1x2"].values()),1,places=12)
        self.assertEqual(p["parameters_status"],
                         "SYNTHETIC_FITTED_REFERENCE_ONLY_NOT_FOR_BETTING")
        self.assertEqual(p["synthetic_fit_report_sha256"],candidate["report_sha256"])
        self.assertFalse(p["training_allowed"])

    def test_deterministic(self):
        self.assertEqual(fit(),fit())
        self.assertEqual(forecast_from_synthetic_fit(fit(),1400,1550),
                         forecast_from_synthetic_fit(fit(),1400,1550))

    def test_validation_and_test_rows_are_never_admitted(self):
        for role in ("VALIDATION","TEST"):
            a=example()
            a[5]["partition"]=role
            with self.assertRaisesRegex(BaselineSafetyError,"NON_TRAIN"):
                fit(a)

    def test_real_source_spoof_flag_and_non_synthetic_id_denied(self):
        rows=example()
        rows[0]["source_type"]="RETROSPECTIVE_PITCHAPI"
        with self.assertRaisesRegex(BaselineSafetyError,"NON_SYNTHETIC"):
            fit(rows)
        rows=example()
        rows[0]["fixture_id"]="pitchapi_real_match"
        with self.assertRaisesRegex(BaselineSafetyError,"INVALID_SYNTHETIC_ID"):
            fit(rows)

    def test_no_odds_and_no_out_of_band_features(self):
        a=example()
        a[0]["bookmaker_odds"]=1.8
        with self.assertRaisesRegex(BaselineSafetyError,"SCHEMA"):
            fit(a)
        a=example()
        a[0]["xg_current_unverified"]=2.0
        with self.assertRaisesRegex(BaselineSafetyError,"SCHEMA"):
            fit(a)

    def test_result_after_train_freeze_denied(self):
        a=example()
        a[0]["result_observed_at_utc"]="2025-10-04T09:00:00Z"
        with self.assertRaisesRegex(BaselineSafetyError,"RESULT_RECEIPT"):
            fit(a)

    def test_future_kickoff_and_postmatch_cutoff_denied(self):
        a=example()
        a[0]["kickoff_utc"]="2025-10-04T15:00:00Z"
        a[0]["feature_cutoff_utc"]="2025-10-04T12:00:00Z"
        a[0]["result_observed_at_utc"]="2025-10-04T19:00:00Z"
        with self.assertRaisesRegex(BaselineSafetyError,"POSTMATCH_FEATURES"):
            fit(a)
        a=example()
        a[0]["feature_cutoff_utc"]="2024-10-01T19:00:00Z"
        with self.assertRaisesRegex(BaselineSafetyError,"POSTMATCH_FEATURES"):
            fit(a)

    def test_no_future_result_before_three_hour_lag(self):
        a=example()
        a[0]["result_observed_at_utc"]="2024-10-01T17:59:59Z"
        with self.assertRaisesRegex(BaselineSafetyError,"RESULT_RECEIPT"):
            fit(a)

    def test_insufficient_or_degenerate_training_refused(self):
        with self.assertRaisesRegex(BaselineSafetyError,"INSUFFICIENT"):
            fit(example()[:7])
        a=example()
        for x in a:
            x["goals_home_90"]=0
        with self.assertRaisesRegex(BaselineSafetyError,"DEGENERATE"):
            fit(a)

    def test_negative_non_integer_or_nan_score_refused(self):
        for bad in (True,-1,2.5,"2"):
            a=example()
            a[0]["goals_home_90"]=bad
            with self.assertRaisesRegex(BaselineSafetyError,"INVALID_90MIN"):
                fit(a)
        a=example()
        a[0]["home_elo_before_kickoff"]=float("nan")
        with self.assertRaisesRegex(BaselineSafetyError,"INVALID_ELO"):
            fit(a)

    def test_duplicate_train_id_refused(self):
        a=example()
        a[1]["fixture_id"]=a[0]["fixture_id"]
        with self.assertRaisesRegex(BaselineSafetyError,"DUPLICATE"):
            fit(a)

    def test_tampered_synthetic_fit_digest_refused(self):
        candidate=fit()
        a=copy.deepcopy(candidate)
        a["fitted_parameters"]["base_home_goals"]=3.3
        with self.assertRaisesRegex(BaselineSafetyError,"UNVERIFIED"):
            forecast_from_synthetic_fit(a,1500,1500)
        a=copy.deepcopy(candidate)
        a["data_kind"]="RETROSPECTIVE"
        with self.assertRaisesRegex(BaselineSafetyError,"UNVERIFIED"):
            forecast_from_synthetic_fit(a,1500,1500)

    def test_non_utc_or_invalid_schema_denied(self):
        with self.assertRaisesRegex(ValueError,"NAIVE_TIMESTAMP"):
            fit(example(),freeze="2025-10-01T00:00:00")
        a=example()
        a[0]["feature_cutoff_utc"]=None
        with self.assertRaisesRegex(ValueError,"MISSING_UTC"):
            fit(a)


if __name__=="__main__":
    unittest.main()
