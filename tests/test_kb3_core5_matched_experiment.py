"""Safety and chronology checks for retrospective matched CatBoost experiment."""
import math
import unittest
from datetime import timedelta

from scripts.kb3_core5_matched_experiment import (
    chronological_split, columns, compare, scores, LABELS, utc,
)

def item(k,when):
    return {"league":"BEL","fixture":str(k),"kickoff":when}

class KB3Core5MatchedResearchTests(unittest.TestCase):
    def test_columns_are_identical_except_ablated_features(self):
        three=columns()
        core=columns(cards=True)
        plus=columns(cards=True,xg=True)
        self.assertEqual(len(three),12)
        self.assertEqual(len(core),14)
        self.assertEqual(len(plus),18)
        self.assertEqual(set(core)-set(three),
                         {"home_yellow_cards","away_yellow_cards"})
        self.assertEqual(set(plus)-set(core),
                         {"home_xg_for","away_xg_for",
                          "home_xg_against","away_xg_against"})
        self.assertNotIn("label",plus)

    def test_global_kickoff_split_has_seven_day_embargo_and_no_overlap(self):
        # Dense, tied kickoff times must remain on one side of the split.
        from datetime import datetime,timezone
        base=datetime(2024,1,1,tzinfo=timezone.utc)
        rows=[item(i,(base+timedelta(days=i//2)).isoformat()
                       .replace("+00:00","Z")) for i in range(80)]
        train,val,meta=chronological_split(rows)
        self.assertEqual(len(train)+len(val)+meta["embargo_discarded"],80)
        self.assertGreaterEqual(
            utc(val[0]["kickoff"])-utc(train[-1]["kickoff"]),
            timedelta(days=7))
        self.assertFalse({x["fixture"] for x in train}&
                         {x["fixture"] for x in val})
        self.assertTrue(all(utc(x["kickoff"])<utc(val[0]["kickoff"])
                            for x in train))

    def test_metrics_are_probability_based(self):
        rows=[dict(label="1",kickoff="2024-01-01T12:00:00Z"),
              dict(label="X",kickoff="2024-01-10T12:00:00Z")]
        good=[{"1":.8,"X":.1,"2":.1},
              {"1":.1,"X":.8,"2":.1}]
        bad=[{"1":.1,"X":.8,"2":.1},
             {"1":.8,"X":.1,"2":.1}]
        self.assertLess(scores(rows,good)["log_loss"],
                        scores(rows,bad)["log_loss"])
        self.assertLess(scores(rows,good)["brier_sum3"],
                        scores(rows,bad)["brier_sum3"])
        paired=compare(rows,bad,good)
        self.assertLess(paired["delta_candidate_minus_baseline"]["log_loss"],0)
        self.assertLess(paired["delta_candidate_minus_baseline"]["brier_sum3"],0)

    def test_no_target_score_appears_in_features(self):
        self.assertTrue(set(LABELS)=={"1","X","2"})
        self.assertTrue(all(not n.startswith("target_") and "label" not in n
                            for n in columns(cards=True,xg=True)))

if __name__=="__main__":
    unittest.main()
