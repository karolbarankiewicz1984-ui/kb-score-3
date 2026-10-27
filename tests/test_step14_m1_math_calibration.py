"""Independent CatBoost M1 proper-scoring math / future calibration safety."""
import copy
from datetime import datetime,timedelta,timezone
import math
import unittest

from src.kb3_step14_m1_math_calibration import (
    M1MathError,stable_softmax,order_probability,score_one,
    score_predictions,temperature_probabilities,fit_temperature,
    evaluate_calibrated_holdout,freeze_forecast,audit_frozen_settlements,
)

def example():
    return {"1":0.6,"X":0.25,"2":0.15}

class MulticlassMathCalibrationTests(unittest.TestCase):
    def test_softmax_numeric_stability_extreme_logits(self):
        v=stable_softmax([1000.0,999.0,-1000.0])
        self.assertAlmostEqual(sum(v),1,places=14)
        self.assertTrue(all(math.isfinite(x) and x>=0 for x in v))
        self.assertGreater(v[0],v[1])

    def test_1x2_order_must_be_explicit_not_alpha(self):
        self.assertEqual(order_probability({"X":0.25,"2":0.15,"1":0.6}),[0.6,0.25,0.15])
        self.assertEqual(score_one({"X":0.25,"2":0.15,"1":0.6},"X"),
                         score_one(example(),"X"))
        for other in ({"1":0.5,"X":0.5}, {"1":0.4,"X":0.4,"2":0.4},
                      {"1":1.0,"X":-0.1,"2":0.1},
                      {"1":float("nan"),"X":0.0,"2":1.0},
                      {"1":True,"X":0.0,"2":0.0}):
            with self.subTest(other=other),self.assertRaises(M1MathError):
                order_probability(other)

    def test_brier_sum3_formula_and_log_loss(self):
        ll,brier=score_one(example(),"1")
        self.assertAlmostEqual(ll,-math.log(.6))
        self.assertAlmostEqual(brier,(.6-1)**2+.25**2+.15**2)
        r=score_predictions([example()],["1"])
        self.assertAlmostEqual(r["log_loss"],ll)
        self.assertAlmostEqual(r["brier_sum3"],brier)
        self.assertEqual(r["n"],1)

    def test_perfect_probabilities_zero_and_wrong_prediction_penalty(self):
        perfect={"1":1.0,"X":0.0,"2":0.0}
        self.assertAlmostEqual(score_one(perfect,"1")[0],0.0)
        self.assertAlmostEqual(score_one(perfect,"1")[1],0.0)
        self.assertAlmostEqual(score_one(perfect,"2")[1],2.0)
        self.assertGreater(score_one(perfect,"2")[0],30)

    def test_temperature_one_identity_and_flattening(self):
        p=example()
        t1=temperature_probabilities(p,1.0)
        for k in p:self.assertAlmostEqual(p[k],t1[k],places=14)
        warm=temperature_probabilities(p,2.0)
        self.assertLess(warm["1"],p["1"])
        self.assertGreater(warm["2"],p["2"])
        self.assertAlmostEqual(sum(warm.values()),1)

    def test_grid_only_past_valid_and_neutral_candidate(self):
        preds=[example() for i in range(15)]
        labels=["1"]*10+["2"]*5
        fit=fit_temperature(preds,labels,min_rows=15)
        self.assertIn(fit["temperature"],[.7,.85,1.0,1.15,1.4,1.8,2.2])
        self.assertTrue(fit["frozen_before_evaluation"])
        hold=evaluate_calibrated_holdout(preds[:5],["2"]*5,fit)
        self.assertEqual(hold["raw"]["n"],5)
        self.assertFalse(hold["recommend_automatic_production_activation"])
        with self.assertRaisesRegex(M1MathError,"NOT_ENOUGH_PAST"):
            fit_temperature(preds[:9],labels[:9],min_rows=10)

    def test_reliability_top1_bins_and_n(self):
        preds=[example(),{"1":0.2,"X":0.5,"2":0.3}]
        x=score_predictions(preds,["1","2"])
        self.assertEqual(x["n"],2)
        self.assertAlmostEqual(x["top1_accuracy"],.5)
        self.assertEqual(sum(a["count"] for a in x["reliability_top1"]),2)
        self.assertTrue(0<=x["top1_ece_10bins"]<=1)

    def test_frozen_forecast_keeps_model_version_and_id(self):
        x=freeze_forecast(forecast_id="SYNTH_F1",
            frozen_at_utc="2026-10-27T10:00:00Z",
            kickoff_utc="2026-10-27T16:00:00Z",
            model_version="M1_OFFLINE_DEMO",variant="NO_XG",
            probabilities=example())
        self.assertEqual(len(x["sha256"]),64)
        pairs=audit_frozen_settlements([x],[{
            "forecast_id":"SYNTH_F1","settled_at_utc":"2026-10-27T18:00:00Z",
            "label_1x2":"X"}],cutoff_utc="2026-10-27T19:00:00Z")
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs[0][0]["model_version"],"M1_OFFLINE_DEMO")

    def test_cannot_freeze_after_kickoff(self):
        with self.assertRaisesRegex(M1MathError,"NOT_BEFORE_KICKOFF"):
            freeze_forecast(forecast_id="F",frozen_at_utc="2026-10-28T15:00:00Z",
                kickoff_utc="2026-10-28T14:00:00Z",
                model_version="M1",variant="NO_XG",probabilities=example())

    def test_can_only_calibrate_from_settled_results_before_cutoff(self):
        x=freeze_forecast(forecast_id="F",frozen_at_utc="2026-10-27T10:00:00Z",
                kickoff_utc="2026-10-27T14:00:00Z",
                model_version="M1",variant="NO_XG",probabilities=example())
        with self.assertRaisesRegex(M1MathError,"FUTURE_OUTCOME"):
            audit_frozen_settlements([x],[{
                "forecast_id":"F","settled_at_utc":"2026-10-27T18:00:00Z",
                "label_1x2":"1"}],cutoff_utc="2026-10-27T17:59:59Z")
        with self.assertRaisesRegex(M1MathError,"FUTURE_OUTCOME"):
            audit_frozen_settlements([x],[{
                "forecast_id":"F","settled_at_utc":"2026-10-27T13:59:00Z",
                "label_1x2":"1"}],cutoff_utc="2026-10-28T00:00:00Z")

    def test_single_forecast_may_not_be_settled_twice(self):
        x=freeze_forecast(forecast_id="F",frozen_at_utc="2026-10-27T10:00:00Z",
                kickoff_utc="2026-10-27T14:00:00Z",
                model_version="M1",variant="NO_XG",probabilities=example())
        y={"forecast_id":"F","settled_at_utc":"2026-10-27T18:00:00Z","label_1x2":"2"}
        with self.assertRaisesRegex(M1MathError,"UNKNOWN_DUPLICATE"):
            audit_frozen_settlements([x],[y,y],cutoff_utc="2026-10-28T00:00:00Z")

    def test_forged_hash_or_modified_probability_rejected(self):
        x=freeze_forecast(forecast_id="F",frozen_at_utc="2026-10-27T10:00:00Z",
                kickoff_utc="2026-10-27T14:00:00Z",
                model_version="M1",variant="NO_XG",probabilities=example())
        altered=copy.deepcopy(x);altered["probabilities"]["1"]=0.5
        with self.assertRaisesRegex(M1MathError,"FROZEN_RECORD_CHANGED"):
            audit_frozen_settlements([altered],[],cutoff_utc="2026-10-28T00:00:00Z")

    def test_real_TEST_score_is_never_a_freeze_field(self):
        x=freeze_forecast(forecast_id="F",frozen_at_utc="2026-10-27T10:00:00Z",
                kickoff_utc="2026-10-27T14:00:00Z",
                model_version="M1",variant="NO_XG",probabilities=example())
        x["target"]="1"
        with self.assertRaisesRegex(M1MathError,"INVALID_FROZEN_RECORD"):
            audit_frozen_settlements([x],[],cutoff_utc="2026-10-28T00:00:00Z")

if __name__=="__main__":unittest.main()
