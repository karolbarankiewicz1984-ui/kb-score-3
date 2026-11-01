import unittest
from datetime import datetime,timedelta,timezone
from scripts.step16_train_only_walkforward_catboost import folds,columns,M1RFitSafetyError
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
class TrainOnlyIsolation(unittest.TestCase):
    def rows(self):
        d=datetime(2023,8,1,tzinfo=timezone.utc)
        return [{"fixture_id":str(i),
            "kickoff_utc":(d+timedelta(hours=2*i)).isoformat().replace("+00:00","Z"),
            "m1r_BASE_121_numeric_features":{x:float(i%7+1) for x in EXPECTED_FEATURES},
            "m1r_BASE_38_missing_flags":{x:bool(i%2) for x in EXPECTED_MISSING}}
            for i in range(720)]
    def test_fixed_expanding_train_only_windows(self):
        fs=folds(self.rows())
        self.assertEqual([(len(a),len(b)) for a,b in fs],[(360,100),(480,100),(600,100)])
        for tr,te in fs:self.assertLess(tr[-1]["kickoff_utc"],te[0]["kickoff_utc"])
    def test_tied_kickoff_moves_boundary_forward(self):
        rs=self.rows();rs[360]["kickoff_utc"]=rs[359]["kickoff_utc"]
        a,b=folds(rs)[0];self.assertEqual(len(a),361)
        self.assertLess(a[-1]["kickoff_utc"],b[0]["kickoff_utc"])
    def test_only_actual_train_fold_selects_features_and_no_xg(self):
        for name in ("BASE_FIXED","SHALLOW_FIXED","ELO_FORM5_FIXED"):
            selected=columns(self.rows()[:360],name)
            self.assertGreaterEqual(len(selected),5)
            self.assertTrue(all("xg" not in n.lower() for n in selected))
    def test_no_374_or_test_count_allowed(self):
        with self.assertRaises(M1RFitSafetyError):folds(self.rows()[:700])
if __name__=="__main__":unittest.main()
