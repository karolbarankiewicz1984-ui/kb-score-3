"""Actual safeguards for new relaxed M1-R feature replay."""
import unittest
from datetime import datetime,timezone
from scripts.step14_m1r_recompute_1140_relaxed_48h import recompute,M1RRecomputeError
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING

def ev(i,date,gh,ga,home="A",away="B",role="TRAIN",year=2023):
    return {"fixture_id":f"m_{i}","kickoff":datetime.fromisoformat(date.replace("Z","+00:00")),
      "home_id":home,"away_id":away,"season":f"{year}-{(year+1)%100:02d}",
      "partition":role,"year":year,"gh":gh,"ga":ga}

class Relaxed1140Tests(unittest.TestCase):
    def test_three_old_matches_admit_fourth_without_xg(self):
        events=[
            ev(1,"2023-08-01T12:00:00Z",1,0),
            ev(2,"2023-08-04T12:00:00Z",0,0),
            ev(3,"2023-08-07T12:00:00Z",0,1),
            ev(4,"2023-08-10T12:00:00Z",2,1),
        ]
        result=recompute(events,expected=4)
        self.assertEqual([r["m1r_base_eligible"] for r in result],
                         [False,False,False,True])
        last=result[-1]
        self.assertEqual((last["m1r_BASE_121_numeric_features"]["home_all_5_n"],
                          last["m1r_BASE_121_numeric_features"]["away_all_5_n"]),(3,3))
        self.assertIsNone(last["m1r_BASE_121_numeric_features"]["home_all_5_xg_avg"])
        self.assertEqual(last["m1r_BASE_121_numeric_features"]["home_all_5_xg_n"],0)
        self.assertTrue(last["m1r_BASE_38_missing_flags"]["home_all_5_xg"])
        self.assertTrue(last["m1r_BASE_38_missing_flags"]["home_all_5_history"])
        self.assertEqual((len(last["m1r_BASE_121_numeric_features"]),
                          len(last["m1r_BASE_38_missing_flags"])),(121,38))
    def test_36h_old_result_does_not_enter_features(self):
        events=[ev(1,"2023-09-01T00:00:00Z",2,0),
            ev(2,"2023-09-02T12:00:00Z",0,1),
            ev(3,"2023-09-03T01:00:00Z",1,1)]
        records=recompute(events)
        self.assertEqual(records[1]["m1r_BASE_121_numeric_features"]["home_all_5_n"],0)
        self.assertEqual(records[2]["m1r_BASE_121_numeric_features"]["home_all_5_n"],1)
    def test_target_label_changed_does_not_change_its_features(self):
        events=[ev(1,"2023-09-01T00:00:00Z",2,0),
            ev(2,"2023-09-07T00:00:00Z",0,1)]
        altered=[dict(x) for x in events];altered[1]["gh"]=17;altered[1]["ga"]=1
        a=recompute(events)[1];b=recompute(altered)[1]
        self.assertEqual(a["m1r_BASE_121_numeric_features"],b["m1r_BASE_121_numeric_features"])
        self.assertNotIn("gh",a)
        self.assertNotIn("ga",a)
    def test_no_2025_valid_label_can_leak_into_2024_train(self):
        events=[ev(1,"2024-05-01T00:00:00Z",1,0,role="TRAIN",year=2023),
                ev(2,"2025-08-01T00:00:00Z",0,2,role="VALIDATION",year=2025)]
        a=recompute(events)
        self.assertEqual(a[0]["m1r_BASE_121_numeric_features"]["home_all_5_n"],0)
        self.assertEqual(a[1]["m1r_BASE_121_numeric_features"]["home_all_5_n"],1)
    def test_same_kickoff_does_not_leak_scores(self):
        events=[ev(1,"2023-08-01T00:00:00Z",9,0),
                ev(2,"2023-08-01T00:00:00Z",0,7,home="C",away="D")]
        rows=recompute(events)
        self.assertTrue(all(r["m1r_BASE_121_numeric_features"]["home_all_5_n"]==0 for r in rows))
    def test_duplicate_fixture_ids_fail(self):
        a=ev(1,"2023-08-01T00:00:00Z",1,1)
        with self.assertRaisesRegex(M1RRecomputeError,"DUPLICATE"):
            recompute([a,a])
if __name__=="__main__":unittest.main()
