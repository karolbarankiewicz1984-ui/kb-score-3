"""Step15 ML vs M0 numerical controls, fixed validation contract (no real API)."""
import math
import unittest

from scripts.step15_goal_ml_catboost_720_374 import (
    PARAMS, MARKETS_UNIQUE, _binary_losses, _bounded_rate, _ci_by_week,
    compare_predictions, GoalMLError,
)
from src.kb3_step15_goal_markets import markets_from_lambdas


class GoalMLIndependentTests(unittest.TestCase):
    def test_training_params_fixed_and_poisson(self):
        self.assertEqual(PARAMS["loss_function"],"Poisson")
        self.assertEqual(PARAMS["iterations"],350)
        self.assertEqual(len(MARKETS_UNIQUE),18)
        self.assertEqual(len(set(MARKETS_UNIQUE)),18)
        self.assertNotIn("eval_set",PARAMS)
        self.assertNotIn("use_best_model",PARAMS)

    def test_exact_binary_brier_and_logloss(self):
        b,l=_binary_losses(.75,1)
        self.assertAlmostEqual(b,.0625,places=13)
        self.assertAlmostEqual(l,-math.log(.75),places=13)
        b2,l2=_binary_losses(.25,0)
        self.assertAlmostEqual(b,b2)
        self.assertAlmostEqual(l,l2)

    def test_invalid_probabilities_fail(self):
        for value,target in ((float("nan"),1),(-.1,0),(1.1,1),(.6,True)):
            with self.subTest(value=value,target=target),self.assertRaises(GoalMLError):
                _binary_losses(value,target)

    def test_positive_goal_rate_and_clamp(self):
        self.assertEqual(_bounded_rate(1.4),1.4)
        self.assertEqual(_bounded_rate(9.0),8.0)
        self.assertEqual(_bounded_rate(0.0),1e-6)
        for bad in (float("nan"),float("inf"),True,"1.2"):
            with self.assertRaises(GoalMLError):
                _bounded_rate(bad)

    def test_matched_week_cluster_interval(self):
        d=[-.1]*374
        week=[f"2025-W{i%43:02d}" for i in range(374)]
        x=_ci_by_week(d,week)
        self.assertAlmostEqual(x["delta_mean"],-.1,places=12)
        self.assertAlmostEqual(x["ci95_lower"],-.1,places=12)
        self.assertAlmostEqual(x["ci95_upper"],-.1,places=12)
        self.assertEqual(x["bootstrap_clusters"],43)

    def test_identical_models_no_false_improvement(self):
        predictions=[
            {"ml":markets_from_lambdas(1.5,1.2),
             "m0":markets_from_lambdas(1.5,1.2)}
            for _ in range(374)
        ]
        labels=[]
        for i in range(374):
            gh,ga=((1,1) if i%2 else (2,0))
            label={}
            total=gh+ga
            for name in ("1.5","2.5","3.5"):
                over=int(total>float(name))
                label["over_"+name]=over
                label["under_"+name]=1-over
            label["btts_yes"]=int(gh>0 and ga>0)
            label["btts_no"]=1-label["btts_yes"]
            for side,g in (("home",gh),("away",ga)):
                for k in range(1,4):label[f"{side}_{k}plus"]=int(g>=k)
                for k in range(4):label[f"{side}_exact_{k}"]=int(g==k)
            labels.append(label)
        weeks=[f"2025-W{i%43:02d}" for i in range(374)]
        scores,agg,flags,winner=compare_predictions(predictions,labels,weeks)
        self.assertEqual(len(scores),22)
        self.assertAlmostEqual(agg["delta_ml_minus_m0"]["brier"]["delta_mean"],0)
        self.assertAlmostEqual(agg["delta_ml_minus_m0"]["log_loss"]["delta_mean"],0)
        self.assertEqual(winner,"NO_CONFIRMED_AGGREGATE_ML_IMPROVEMENT")
        self.assertTrue(all(not x["ci95_both_favor_ml"] for x in flags.values()))

    def test_mismatched_validation_denied(self):
        with self.assertRaises(GoalMLError):
            compare_predictions([],[],[])


if __name__=="__main__":
    unittest.main()
