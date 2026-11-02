import unittest
from src.kb3_step19_market_math import evaluate_exact_1x2, MarketContractError

KICK="2026-11-07T20:00:00Z"
CAP="2026-11-07T17:00:00Z"
CUT="2026-11-07T18:00:00Z"

def quotes():
    return [{
        "quote_id":"q"+side,"fixture_id":"match_A","kickoff_utc":KICK,
        "captured_at_utc":CAP,"provider":"demo","bookmaker":"demo-book",
        "market":"FT_90MIN_1X2","selection":side,"line":None,
        "decimal_odds":odd
    } for side,odd in (("1",2.0),("X",3.4),("2",4.2))]

def check(qu=None,**kwargs):
    return evaluate_exact_1x2(
        quotes=quotes() if qu is None else qu,
        probabilities=kwargs.pop("probabilities",{"1":0.50,"X":0.28,"2":0.22}),
        fixture_id="match_A",kickoff_utc=KICK,cutoff_utc=CUT,**kwargs)

class MarketMathTests(unittest.TestCase):
    def test_correct_three_way_no_vig_math(self):
        r=check()
        self.assertEqual(r["market"],"FT_90MIN_1X2")
        self.assertAlmostEqual(sum(x["normalized_no_vig_probability"]
                                   for x in r["selection_math"].values()),1.0)
        self.assertAlmostEqual(r["selection_math"]["1"]["arithmetic_ev_per_unit"],0.0)
        self.assertFalse(r["value_pick_recommended"])
        self.assertFalse(r["formal_gate19_pass"])
        self.assertFalse(r["real_source_time_proof_independently_verified"])

    def test_reject_wrong_market_or_line(self):
        q=quotes();q[0]["market"]="OVER_UNDER";q[0]["line"]=2.5
        with self.assertRaisesRegex(MarketContractError,"MARKET_OR_LINE"): check(q)

    def test_reject_different_bookmaker_and_capture_snapshot(self):
        q=quotes();q[1]["bookmaker"]="not-same"
        with self.assertRaisesRegex(MarketContractError,"MIXED_PROVIDER"): check(q)
        q=quotes();q[1]["captured_at_utc"]="2026-11-07T17:02:00Z"
        with self.assertRaisesRegex(MarketContractError,"MIXED_PROVIDER"): check(q)

    def test_reject_late_or_false_kickoff(self):
        q=quotes();q[0]["captured_at_utc"]="2026-11-07T19:05:00Z"
        with self.assertRaisesRegex(MarketContractError,"QUOTE_NOT_OBSERVED"): check(q)
        q=quotes();q[0]["kickoff_utc"]="2026-11-08T20:00:00Z"
        with self.assertRaisesRegex(MarketContractError,"FIXTURE_OR_KICKOFF"): check(q)

    def test_reject_duplicate_selection_and_invalid_odds(self):
        q=quotes();q[0]["selection"]="X"
        with self.assertRaisesRegex(MarketContractError,"DUPLICATE"): check(q)
        q=quotes();q[0]["decimal_odds"]=float("nan")
        with self.assertRaisesRegex(MarketContractError,"INVALID_DECIMAL"): check(q)
        q=quotes();q[0]["decimal_odds"]=1
        with self.assertRaisesRegex(MarketContractError,"INVALID_DECIMAL"): check(q)

if __name__=="__main__":unittest.main()
