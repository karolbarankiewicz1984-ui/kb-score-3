"""Step15 Poisson joint goal-market properties, analytic fixtures and negative tests."""
import math
import unittest
from dataclasses import replace

from src.kb3_step13_baseline import BaselineParameters, BaselineSafetyError, forecast
from src.kb3_step15_goal_markets import (
    markets_from_lambdas, forecast_goal_markets, validate_goal_markets,
)


class Step15GoalMarketTests(unittest.TestCase):
    def test_analytic_over_and_btts(self):
        h, a = 1.45, 1.15
        m = markets_from_lambdas(h, a)
        total = h + a
        for line, n in (("1.5",1),("2.5",2),("3.5",3)):
            cdf = math.exp(-total)*sum(total**k/math.factorial(k) for k in range(n+1))
            self.assertAlmostEqual(m["p_over"][line], 1-cdf, places=11)
            self.assertAlmostEqual(m["p_under"][line], cdf, places=11)
        self.assertAlmostEqual(m["p_btts"]["yes"], (1-math.exp(-h))*(1-math.exp(-a)), places=11)
        self.assertAlmostEqual(m["team_goals"]["home"]["exact"]["0"], math.exp(-h), places=11)
        self.assertAlmostEqual(m["team_goals"]["away"]["exact"]["2"], math.exp(-a)*a*a/2, places=11)

    def test_exact_90_min_goals_and_monotonicity(self):
        for h, a in ((0.1,0.1),(0.8,3.1),(1.45,1.15),(5.9,0.2),(8.0,8.0),(0.000001,0.000001)):
            with self.subTest(h=h,a=a):
                m=markets_from_lambdas(h,a)
                self.assertTrue(validate_goal_markets(m))
                self.assertAlmostEqual(sum(m["p_1x2"].values()),1,places=10)
                o=m["p_over"]
                self.assertGreaterEqual(o["1.5"],o["2.5"])
                self.assertGreaterEqual(o["2.5"],o["3.5"])
                self.assertLessEqual(m["p_btts"]["yes"],o["1.5"]+1e-12)
                for side in ("home","away"):
                    x=m["team_goals"][side]["at_least"]
                    self.assertGreaterEqual(x["1+"]+1e-12,x["2+"])
                    self.assertGreaterEqual(x["2+"]+1e-12,x["3+"])
                self.assertEqual(m["match_duration"],"REGULAR_90_MINUTES")
                self.assertFalse(m["trained_or_calibrated_here"])

    def test_unchanged_step13_reference_overlap(self):
        for home,away in ((1500,1500),(1650,1400),(1300,1650),(1800,1100)):
            old=forecast(home,away)
            new=forecast_goal_markets(home,away)
            for key in old["p_1x2"]:
                self.assertAlmostEqual(old["p_1x2"][key],new["p_1x2"][key],places=11)
            for line in old["p_over"]:
                self.assertAlmostEqual(old["p_over"][line],new["p_over"][line],places=11)
            self.assertAlmostEqual(old["p_btts_yes"],new["p_btts"]["yes"],places=11)
            self.assertFalse(new["test_season_2026_27_read"])

    def test_train_only_fitted_params_not_fit_here(self):
        p=replace(BaselineParameters(),base_home_goals=1.52,
                  base_away_goals=1.24,elo_goal_elasticity=0.2)
        self.assertTrue(validate_goal_markets(forecast_goal_markets(1620,1440,p)))

    def test_zero_zero_analytic(self):
        m=markets_from_lambdas(.1,.1)
        best=m["top_5_scorelines"][0]
        self.assertEqual((best["home"],best["away"]),(0,0))
        self.assertGreater(m["p_under"]["1.5"],0.9)
        self.assertLess(m["p_btts"]["yes"],.02)
        self.assertGreaterEqual(m["p_1x2"]["X"],math.exp(-.2)-1e-12)

    def test_repeat_is_deterministic(self):
        self.assertEqual(forecast_goal_markets(1577,1489),forecast_goal_markets(1577,1489))

    def test_bad_numeric_and_odds_fail_closed(self):
        for bad in (float("nan"),float("inf"),0,-1,8.1,True,"1.5"):
            with self.subTest(bad=bad),self.assertRaises(BaselineSafetyError):
                markets_from_lambdas(bad,1.0)
        with self.assertRaises(BaselineSafetyError):
            forecast_goal_markets(1500,1500,params={"odds":2})
        with self.assertRaises(TypeError):
            markets_from_lambdas(1.0,1.0,bookmaker_odds=1.5)

    def test_tampered_over_under_fails(self):
        m=markets_from_lambdas(1.5,1.1)
        m["p_under"]["2.5"]=.99
        with self.assertRaisesRegex(BaselineSafetyError,"COMPLEMENT"):
            validate_goal_markets(m)

    def test_tampered_over_order_fails(self):
        m=markets_from_lambdas(1.5,1.1)
        m["p_over"]["3.5"]=m["p_over"]["2.5"]+.01
        m["p_under"]["3.5"]=1-m["p_over"]["3.5"]
        with self.assertRaisesRegex(BaselineSafetyError,"MONOTONICITY"):
            validate_goal_markets(m)

    def test_tampered_team_goal_fails(self):
        m=markets_from_lambdas(1.5,1.1)
        m["team_goals"]["home"]["at_least"]["3+"] = .9
        with self.assertRaises(BaselineSafetyError):
            validate_goal_markets(m)

    def test_tampered_btts_fails(self):
        m=markets_from_lambdas(1.5,1.1)
        m["p_btts"]["yes"] = .99
        m["p_btts"]["no"] = .01
        with self.assertRaisesRegex(BaselineSafetyError,"IMPOSSIBLE"):
            validate_goal_markets(m)

    def test_overtime_rejected(self):
        m=markets_from_lambdas(1.5,1.1)
        m["match_duration"]="INCLUDES_EXTRA_TIME"
        with self.assertRaisesRegex(BaselineSafetyError,"90_MINUTES"):
            validate_goal_markets(m)


if __name__ == "__main__":
    unittest.main()
