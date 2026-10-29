import math,unittest
from scripts.step14_m1r_train_real_catboost_720_evaluate_374 import (
   _as_label,_score,prepare_features,M1RFitSafetyError)
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING

class M1RTrainOnlyTests(unittest.TestCase):
    def test_multiclass_brier_log_loss_and_ece(self):
        probs=[{"1":.7,"X":.2,"2":.1},{"1":.1,"X":.4,"2":.5}]
        vals=_score(probs,["1","2"])
        self.assertEqual(vals["n"],2)
        self.assertAlmostEqual(vals["brier_multiclass_sum3"],(.14+.42)/2)
        self.assertAlmostEqual(vals["brier_multiclass_mean3"],(.14+.42)/6)
        self.assertAlmostEqual(vals["log_loss"],(-math.log(.7)-math.log(.5))/2)
        self.assertEqual(vals["top1_accuracy"],1)
        self.assertEqual(sum(z["count"] for z in vals["top1_reliability_5_bins"]),2)
        self.assertEqual(sum(z["count"] for z in vals["per_class_reliability_5_bins"]["X"]),2)
    def test_refuse_invalid_probs_and_bad_90min_goals(self):
        with self.assertRaises(M1RFitSafetyError):
            _score([{"1":.1,"X":.1,"2":.1}],["2"])
        with self.assertRaises(M1RFitSafetyError):
            _as_label(2.5,1)
    def test_training_only_feature_selection_ignores_validation_variables(self):
        names=sorted(k for k in EXPECTED_FEATURES if not k.endswith(
            ("_xg_n","_xg_avg","_xga_n","_xga_avg")))[:22]
        def make(i,part):
            vals={k:None for k in EXPECTED_FEATURES}
            for j,name in enumerate(names):
                vals[name]=float((i+j)%7)
            masks={k:True for k in EXPECTED_MISSING}
            return {"fixture_id":f"m_{part}_{i}","partition":part,
                "kickoff_utc":"2025-01-01T00:00:00Z" if part=="TRAIN" else "2025-08-01T00:00:00Z",
                "m1r_base_eligible":True,"original_M1_159_PIT_certified":False,
                "source_class":"B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT",
                "m1r_BASE_121_numeric_features":vals,"m1r_BASE_38_missing_flags":masks}
        tr=[make(i,"TRAIN") for i in range(720)]
        val=[make(i,"VALIDATION") for i in range(374)]
        _,_,sel,Xtr,Xv=prepare_features(tr+val)
        self.assertEqual(len(Xtr),720);self.assertEqual(len(Xv),374)
        self.assertTrue(len(sel)>=15)
        self.assertTrue(all("_xg" not in name and "_xga" not in name for name in sel))
        # Even a new VAL-only variable must not alter the selected feature names.
        self.assertNotIn("home_venue_games_available",names)
        for row in val:
            row["m1r_BASE_121_numeric_features"]["home_venue_games_available"]=float(len(row["fixture_id"]))
        _,_,sel2,_,_=prepare_features(tr+val)
        self.assertEqual(sel,sel2)
if __name__=="__main__":unittest.main()
