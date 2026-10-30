"""Independent step15 market audit arithmetic and corruption guards."""
import math
import unittest

from scripts.step15_independent_market_audit import (
    _check_market, _labels, _market_dict, _binary, IndependentAuditError,
)
from src.kb3_step15_goal_markets import markets_from_lambdas


class IndependentStep15AuditMath(unittest.TestCase):
    def test_reference_model_is_coherent(self):
        p=markets_from_lambdas(1.45,1.15)
        self.assertTrue(_check_market(p))
        self.assertEqual(len(_market_dict(p)),22)

    def test_90min_2_1_label_exact(self):
        y=_labels(2,1)
        self.assertEqual(len(y),22)
        self.assertEqual(y["over_2.5"],1)
        self.assertEqual(y["under_3.5"],1)
        self.assertEqual(y["btts_yes"],1)
        self.assertEqual(y["home_exact_2"],1)
        self.assertEqual(y["away_exact_1"],1)

    def test_binary_independent_score(self):
        a=_binary([{"over_2.5":0.8},{"over_2.5":0.2}],
                  [{"over_2.5":1},{"over_2.5":0}],"over_2.5")
        self.assertAlmostEqual(a["brier"],.04)
        self.assertAlmostEqual(a["log_loss"],-math.log(.8))

    def test_reject_incoherent_over_market(self):
        p=markets_from_lambdas(1.45,1.15)
        p["p_over"]["3.5"]=p["p_over"]["2.5"]+.01
        p["p_under"]["3.5"]=1-p["p_over"]["3.5"]
        with self.assertRaises(IndependentAuditError):
            _check_market(p)

    def test_reject_bad_duration_and_team_totals(self):
        p=markets_from_lambdas(1.45,1.15)
        p["match_duration"]="INCLUDES_EXTRA_TIME"
        with self.assertRaises(IndependentAuditError):
            _check_market(p)
        q=markets_from_lambdas(1.45,1.15)
        q["team_goals"]["home"]["at_least"]["2+"] = .99
        with self.assertRaises(IndependentAuditError):
            _check_market(q)

    def test_no_corrupt_labels(self):
        with self.assertRaises(IndependentAuditError):
            _labels(2.0,1)


    def test_reject_renormalized_but_wrong_over_25(self):
        # Previously complement and monotonicity would not detect this.
        p=markets_from_lambdas(1.45,1.15)
        p["p_over"]["2.5"]+=0.01
        p["p_under"]["2.5"]-=0.01
        with self.assertRaisesRegex(IndependentAuditError,"JOINT_POISSON_MISMATCH"):
            _check_market(p)

    def test_reject_btts_pair_even_when_complemented(self):
        p=markets_from_lambdas(1.45,1.15)
        p["p_btts"]["yes"]+=0.001
        p["p_btts"]["no"]-=0.001
        with self.assertRaisesRegex(IndependentAuditError,"JOINT_POISSON_MISMATCH"):
            _check_market(p)

    def test_reject_1x2_pair_even_when_normalized(self):
        p=markets_from_lambdas(1.45,1.15)
        p["p_1x2"]["1"]+=0.001
        p["p_1x2"]["2"]-=0.001
        with self.assertRaisesRegex(IndependentAuditError,"JOINT_POISSON_MISMATCH"):
            _check_market(p)

    def test_reject_wrong_top5_probability_with_correct_ranking(self):
        p=markets_from_lambdas(1.45,1.15)
        p["top_5_scorelines"][0]["probability"]+=0.00001
        with self.assertRaisesRegex(IndependentAuditError,"JOINT_POISSON_MISMATCH"):
            _check_market(p)

    def test_stress_independent_joint_at_limits(self):
        for h,a in ((1e-6,1e-6),(8.,8.),(8.,1e-6),(1.45,1.15)):
            with self.subTest(h=h,a=a):
                self.assertTrue(_check_market(markets_from_lambdas(h,a)))

if __name__=="__main__":
    unittest.main()
