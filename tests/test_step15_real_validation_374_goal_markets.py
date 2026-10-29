"""Independent market-scoring guards: no network access."""
import math
import unittest
from scripts.step15_real_validation_374_goal_markets import (
    _score_binary, _outcomes, _prediction_markets, Step15EvalError,
)
from src.kb3_step15_goal_markets import markets_from_lambdas


class Step15ValidationMathTests(unittest.TestCase):
    def test_binary_scores(self):
        x=_score_binary([(0.75,1),(0.25,0)])
        self.assertEqual(x["n"],2)
        self.assertAlmostEqual(x["brier"],.0625,places=12)
        self.assertAlmostEqual(x["log_loss"],-math.log(.75),places=12)

    def test_bad_binary_rows_fail_closed(self):
        for row in ([(-.1,1)],[(1.1,0)],[(float("nan"),0)],[(.5,2)],[(.5,True)],[]):
            with self.subTest(row=row),self.assertRaises(Step15EvalError):
                _score_binary(row)

    def test_2_1_market_targets(self):
        m=_outcomes(2,1)
        self.assertEqual(m["over_1.5"],1)
        self.assertEqual(m["over_2.5"],1)
        self.assertEqual(m["under_3.5"],1)
        self.assertEqual(m["btts_yes"],1)
        self.assertEqual(m["home_2plus"],1)
        self.assertEqual(m["away_2plus"],0)
        self.assertEqual(m["home_exact_2"],1)
        self.assertEqual(m["away_exact_1"],1)

    def test_invalid_goals_fail_closed(self):
        for gh,ga in ((-1,1),(2.0,2),(True,0),(31,0)):
            with self.assertRaises(Step15EvalError):
                _outcomes(gh,ga)

    def test_predicted_market_names_match_90min_targets(self):
        p=_prediction_markets(markets_from_lambdas(1.45,1.15))
        m=_outcomes(2,1)
        self.assertEqual(set(p),set(m))
        self.assertEqual(len(p),22)
        self.assertTrue(all(0<=v<=1 for v in p.values()))


if __name__=="__main__":
    unittest.main()
