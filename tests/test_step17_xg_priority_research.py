"""Synthetic offline budget, future cutoff and missing last5 tests."""
import unittest
from datetime import datetime,timedelta,timezone
from src.kb3_step17_xg_priority_research import ranked_eight,score_missing_last5,compare_counterfactual_selection

AT=datetime(2026,11,1,6,tzinfo=timezone.utc)
def match(i,t,h,a,status="finished"):
    return {"id":i,"time_utc":t.isoformat().replace("+00:00","Z"),
      "home_team":{"id":h},"away_team":{"id":a},
      "status":status,"score_home":None if status=="scheduled" else 1,
      "score_away":None if status=="scheduled" else 0}

class XGPriorityResearchTests(unittest.TestCase):
    def test_eight_leagues_remain_within_33_calls(self):
        g={}
        for c in ("ESP","ITA","GER","FRA","NED","BEL","TUR","POL"):
            hist=[match(c+str(i),AT-timedelta(days=15-i),c+"H",c+"A") for i in range(10)]
            fut=[match(c+"future",AT+timedelta(days=2),c+"H",c+"A","scheduled")]
            g[c]={"history":hist,"future":fut}
        picks,report=ranked_eight(g,set(),AT)
        self.assertEqual(len(picks),8)
        self.assertEqual(report["max_provider_calls"],33)
        self.assertEqual({c for c,m in picks},set(g))
        self.assertTrue(all(m["status"]=="finished" for c,m in picks))

    def test_near_complete_last5_is_prioritized(self):
        hist=[match("A"+str(i),AT-timedelta(days=7-i),"A","X") for i in range(5)]
        hist +=[match("B"+str(i),AT-timedelta(days=12-i),"B","Y") for i in range(5)]
        fut=[match("FA",AT+timedelta(days=2),"A","X","scheduled"),
             match("FB",AT+timedelta(days=2),"B","Y","scheduled")]
        known={("ESP","A"+str(i)) for i in range(4)}
        result,_=ranked_eight({"ESP":{"history":hist,"future":fut}},known,AT)
        self.assertEqual(result[0][1]["id"],"A4")

    def test_late_or_unfinished_not_selected(self):
        hist=[match("late",AT-timedelta(hours=1),"A","X"),
              match("good",AT-timedelta(days=3),"A","X")]
        soon=[match("soon",AT+timedelta(minutes=10),"A","X","scheduled")]
        self.assertEqual(ranked_eight({"ESP":{"history":hist,"future":soon}},set(),AT)[0],[])
        soon[0]["time_utc"]=(AT+timedelta(days=2)).isoformat().replace("+00:00","Z")
        result,_=ranked_eight({"ESP":{"history":hist,"future":soon}},set(),AT)
        self.assertEqual(result[0][1]["id"],"good")

    def test_pairwise_projection_shows_ceiling_not_actual_xg(self):
        # More recent B match wins the old rank; missing A4 completes two
        # teams' true previous five, so a research candidate is different.
        ah=[match("A"+str(i),AT-timedelta(days=22-i),"A","X") for i in range(5)]
        bh=[match("B"+str(i),AT-timedelta(days=7-i),"B","Y") for i in range(5)]
        fut=[match("FA",AT+timedelta(days=2),"A","X","scheduled"),
             match("FB",AT+timedelta(days=2),"B","Y","scheduled")]
        g={"ESP":{"history":ah+bh,"future":fut}}
        known={("ESP","A"+str(i)) for i in range(4)}
        baseline=[("ESP",bh[-1])]
        new,meta=ranked_eight(g,known,AT)
        self.assertEqual(new[0][1]["id"],"A4")
        report=compare_counterfactual_selection(g,known,AT,baseline,new)
        self.assertEqual(report["current_verified_last5"],0)
        self.assertEqual(report["baseline_if_all_selected_xg_pairs_validate"],0)
        self.assertEqual(report["experimental_if_all_selected_xg_pairs_validate"],1)
        self.assertEqual(report["counterfactual_gain_if_all_valid"],1)
        self.assertTrue(report["only_a_theoretical_ceiling_not_observed_gain"])
        self.assertEqual(report["additional_provider_calls"],0)

    def test_budget_reject_and_no_fake_xg(self):
        with self.assertRaises(ValueError):ranked_eight({},set(),AT,budget=9)
        with self.assertRaises(ValueError):ranked_eight({},set(),AT,per_league=0)
        self.assertEqual(len(score_missing_last5({},set(),AT)[0]),0)
if __name__=="__main__":unittest.main()
