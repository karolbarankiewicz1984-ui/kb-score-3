"""Step13 reference M0 math: independent Poisson, Elo and no-market gates."""
import math
import unittest
from dataclasses import replace
from src.kb3_step13_baseline import (
    BaselineParameters, BaselineSafetyError, elo_expected_home_points,
    update_elo, forecast,
)


class Step13EloPoissonReference(unittest.TestCase):
    def test_equal_elo_home_advantage_has_more_home_goals(self):
        f = forecast(1500, 1500)
        self.assertGreater(f["expected_goals"]["home"], f["expected_goals"]["away"])
        self.assertAlmostEqual(f["expected_goals"]["home"], 1.45, places=12)
        self.assertAlmostEqual(f["expected_goals"]["away"], 1.15, places=12)
        self.assertGreater(f["p_1x2"]["1"], f["p_1x2"]["2"])
        self.assertGreater(f["elo_expected_home_points"], 0.5)
        self.assertFalse(f["training_allowed"])

    def test_1x2_all_positive_sum_to_one(self):
        for h,a in ((1500,1500),(1650,1400),(1300,1650),(1800,1100)):
            f=forecast(h,a)
            ps=f["p_1x2"]
            self.assertAlmostEqual(sum(ps.values()),1.0,places=12)
            self.assertEqual(set(ps),{"1","X","2"})
            self.assertTrue(all(0<=v<=1 for v in ps.values()))
            self.assertAlmostEqual(f["poisson_joint_retained_mass"],1.0,places=11)

    def test_increased_elo_increases_home_win_and_home_lambda(self):
        a,b=forecast(1500,1500),forecast(1700,1500)
        self.assertGreater(b["p_1x2"]["1"],a["p_1x2"]["1"])
        self.assertLess(b["p_1x2"]["2"],a["p_1x2"]["2"])
        self.assertGreater(b["expected_goals"]["home"],a["expected_goals"]["home"])
        self.assertLess(b["expected_goals"]["away"],a["expected_goals"]["away"])

    def test_over_goal_lines_are_ordered(self):
        for f in (forecast(1500,1500),forecast(1650,1470)):
            o=f["p_over"]
            self.assertGreater(o["1.5"],o["2.5"])
            self.assertGreater(o["2.5"],o["3.5"])
            self.assertTrue(all(0<=v<=1 for v in o.values()))
            self.assertTrue(0<=f["p_btts_yes"]<=1)

    def test_btts_uses_same_independent_joint_distribution(self):
        f=forecast(1600,1450)
        h,a=f["expected_goals"]["home"],f["expected_goals"]["away"]
        analytic=(1-math.exp(-h))*(1-math.exp(-a))
        self.assertAlmostEqual(f["p_btts_yes"],analytic,places=10)

    def test_top_scorelines_are_five_distinct_descending(self):
        scores=forecast(1500,1500)["top_5_scorelines"]
        self.assertEqual(len(scores),5)
        self.assertEqual(len({(r["home"],r["away"]) for r in scores}),5)
        self.assertEqual([r["probability"] for r in scores],
                         sorted([r["probability"] for r in scores],reverse=True))

    def test_no_second_poisson_home_advantage(self):
        p=replace(BaselineParameters(),base_home_goals=1.25,base_away_goals=1.25)
        f=forecast(1500,1500,p)
        self.assertAlmostEqual(f["p_1x2"]["1"],f["p_1x2"]["2"],places=12)
        self.assertGreater(f["elo_expected_home_points"],0.5)

    def test_elo_update_zero_sum_conservation(self):
        p=BaselineParameters()
        old=1500+1500
        for res in ("H","D","A"):
            h,a=update_elo(1500,1500,res,p)
            self.assertAlmostEqual(h+a,old,places=11)
        win=update_elo(1500,1500,"H",p)
        lose=update_elo(1500,1500,"A",p)
        self.assertGreater(win[0],1500)
        self.assertLess(lose[0],1500)
        self.assertLess(update_elo(1500,1500,"D",p)[0],1500)

    def test_elo_matches_standard_logistic_reference(self):
        p=BaselineParameters(elo_home_advantage=0)
        self.assertAlmostEqual(elo_expected_home_points(1500,1500,p),0.5,places=12)
        self.assertAlmostEqual(elo_expected_home_points(1700,1300,p),10/11,places=12)

    def test_invalid_probabilities_cannot_become_nan(self):
        with self.assertRaises(BaselineSafetyError):
            forecast(float("nan"),1500)
        with self.assertRaises(BaselineSafetyError):
            forecast(True,1500)
        with self.assertRaises(BaselineSafetyError):
            forecast(1500,float("inf"))
        with self.assertRaises(BaselineSafetyError):
            forecast(4000,100)

    def test_incorrect_parameters_are_rejected(self):
        with self.assertRaises(BaselineSafetyError):
            BaselineParameters(elo_k=0)
        with self.assertRaises(BaselineSafetyError):
            BaselineParameters(base_away_goals=-1)
        with self.assertRaises(BaselineSafetyError):
            BaselineParameters(poisson_max_goals=12)
        with self.assertRaises(BaselineSafetyError):
            BaselineParameters(elo_goal_elasticity=float("nan"))
        with self.assertRaises(BaselineSafetyError):
            forecast(1500,1500,params={"odds":1.3})

    def test_unknown_outcome_rejected_and_no_market_inputs(self):
        with self.assertRaisesRegex(BaselineSafetyError,"INVALID_RESULT"):
            update_elo(1500,1500,"ODDS",BaselineParameters())
        with self.assertRaises(TypeError):
            forecast(1500,1500,bookmaker_odds=2.0)
        self.assertNotIn("bookmaker_odds",forecast(1500,1500))

    def test_deterministic_repeat(self):
        self.assertEqual(forecast(1640,1520),forecast(1640,1520))
        self.assertEqual(update_elo(1540,1480,"D"),
                         update_elo(1540,1480,"D"))


if __name__ == "__main__":
    unittest.main()
