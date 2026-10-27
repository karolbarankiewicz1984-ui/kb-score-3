"""Artificial future final scores ONLY. Never query PitchAPI or open TEST labels."""
import copy
import json
from pathlib import Path
import unittest
from datetime import timedelta
from src.kb3_split import timestamp, sha
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_forward_score import score_locked_first_ten, SOURCE_HASH

ORIGINAL=Path(__file__).resolve().parents[1]/"data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json"
FUTURE_CAPTURE="2026-11-03T10:00:00Z"
FUTURE_EVALUATION="2026-11-03T12:00:00Z"

def fake_fixture_receipts():
    forecast=json.loads(ORIGINAL.read_text(encoding="utf8"))
    receipts=[]
    for i,f in enumerate(forecast["forecasts"]):
        receipts.append({
            "fixture_id":f["fixture_id"],
            "home_team_id":f["home_team_id"],
            "away_team_id":f["away_team_id"],
            "kickoff_utc":f["kickoff_utc"],
            "status":"finished",
            "goals_home_90":i%4,
            "goals_away_90":(i+1)%3,
            "observed_at_utc":FUTURE_CAPTURE,
            "source":"PitchAPI",
            "capture_sha256":sha({"synthetic_only":True,"fixture_position":i}),
        })
    return forecast,receipts


class Step13ForwardScoringContractTests(unittest.TestCase):
    def test_ten_scores_only_in_synthetic_future_evaluation(self):
        frozen,receipts=fake_fixture_receipts()
        report=score_locked_first_ten(frozen,receipts,
                            scoring_observed_at_utc=FUTURE_EVALUATION)
        self.assertEqual(report["frozen_forecast_sha256"],SOURCE_HASH)
        self.assertEqual(report["prospective_evaluation_target_count"],10)
        self.assertEqual(report["result_labels_for_this_prespecified_shadow_sample_read"],10)
        self.assertEqual(report["other_370_test_labels_read_by_this_protocol"],0)
        self.assertLess(report["multiclass_1x2_logloss"],5)
        self.assertGreater(report["multiclass_1x2_brier_sum3"],0)
        self.assertTrue(0<=report["top_class_1x2_ece_5bins_exploratory"]<=1)
        self.assertEqual(report["report_sha256"],sha({k:v for k,v in report.items() if k!="report_sha256"}))
        self.assertFalse(report["actual_provider_receipt_chain_separately_verified"])
        self.assertFalse(report["gate13_pass"])
        self.assertFalse(report["training_allowed"])
        self.assertFalse(report["step14_started"])
        self.assertTrue(report["not_for_parameter_selection_or_retraining"])
        output=str(report).lower()
        self.assertNotIn("goals_home_90",output)
        self.assertNotIn("goals_away_90",output)
        for rec in receipts:
            self.assertNotIn(rec["fixture_id"],output)

    def test_exactly_ten_and_no_extra_test_result(self):
        frozen,receipts=fake_fixture_receipts()
        with self.assertRaisesRegex(BaselineSafetyError,"EXACTLY_TEN"):
            score_locked_first_ten(frozen,receipts[:-1],scoring_observed_at_utc=FUTURE_EVALUATION)
        with self.assertRaisesRegex(BaselineSafetyError,"EXACTLY_TEN"):
            score_locked_first_ten(frozen,receipts+[copy.deepcopy(receipts[0])],
                    scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_frozen_prediction_tamper_rejected(self):
        frozen,receipts=fake_fixture_receipts()
        frozen["forecasts"][0]["probabilities_1x2"]["1"]=0.90
        with self.assertRaisesRegex(BaselineSafetyError,"TAMPERED"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_unfrozen_and_forged_report_rejected(self):
        frozen,receipts=fake_fixture_receipts()
        frozen["report_sha256"]="f"*64
        with self.assertRaisesRegex(BaselineSafetyError,"SHA_MISMATCH"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_evaluation_before_end_of_last_match_refused(self):
        frozen,receipts=fake_fixture_receipts()
        with self.assertRaisesRegex(BaselineSafetyError,"BEFORE_ALL_MATCHES"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc="2026-10-31T20:00:00Z")

    def test_receipt_captured_before_final_refused(self):
        frozen,receipts=fake_fixture_receipts()
        receipts[0]["observed_at_utc"]="2026-10-31T13:00:00Z"
        with self.assertRaisesRegex(BaselineSafetyError,"NOT_GENUINELY_AFTER_MATCH"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_cross_fixture_or_wrong_team_refused(self):
        frozen,receipts=fake_fixture_receipts()
        receipts[3]["away_team_id"]="t_FAKE12"
        with self.assertRaisesRegex(BaselineSafetyError,"IDENTITY_OR_STATUS"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_duplicate_receipt_refused(self):
        frozen,receipts=fake_fixture_receipts()
        receipts[-1]=copy.deepcopy(receipts[0])
        with self.assertRaisesRegex(BaselineSafetyError,"DUPLICATED"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_status_and_extra_odds_field_refused(self):
        frozen,receipts=fake_fixture_receipts()
        receipts[0]["bookmaker_odds"]=2.10
        with self.assertRaisesRegex(BaselineSafetyError,"FIELDS_UNEXPECTED"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)
        receipts[0].pop("bookmaker_odds")
        receipts[0]["status"]="postponed"
        with self.assertRaisesRegex(BaselineSafetyError,"IDENTITY_OR_STATUS"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_boolean_or_negative_score_rejected(self):
        frozen,receipts=fake_fixture_receipts()
        receipts[0]["goals_home_90"]=True
        with self.assertRaisesRegex(BaselineSafetyError,"NINETY_MINUTE_SCORE"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)
        receipts[0]["goals_home_90"]=-2
        with self.assertRaisesRegex(BaselineSafetyError,"NINETY_MINUTE_SCORE"):
            score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)

    def test_original_snapshot_and_fake_receipts_are_deterministic(self):
        frozen,receipts=fake_fixture_receipts()
        a=score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)
        b=score_locked_first_ten(frozen,receipts,scoring_observed_at_utc=FUTURE_EVALUATION)
        self.assertEqual(a,b)

if __name__=="__main__":
    unittest.main()
