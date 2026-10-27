"""Artificial-score tests; safe view provides ONLY IDs and kickoff."""
import copy
import json
from pathlib import Path
import unittest
from src.kb3_step13_train_elo_sensitivity import diagnose,profile
from scripts.step13_pitchapi_train_elo_once import extract,SEASONS

SAFE=Path(__file__).resolve().parents[1]/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
def fixture():
    safe=json.loads(SAFE.read_text())
    payload={}
    for season in SEASONS:
        y=int(season[:4])
        train=[f for f in safe["fixtures"] if f["partition"]=="TRAIN"
               and f["kickoff_utc"]>=f"{y}-07-01T00:00:00Z"
               and f["kickoff_utc"]<f"{y+1}-07-01T00:00:00Z"]
        assert len(train)==380
        matches=[]
        for i,f in enumerate(train):
            h=(i%20)+1;a=((i+7)%20)+1
            matches.append({"id":f["fixture_id"],"time_utc":f["kickoff_utc"],
                    "home_team":{"id":f"t_{h:06d}","name":f"SYN_{h}"},
                    "away_team":{"id":f"t_{a:06d}","name":f"SYN_{a}"},
                    "status":"finished","score_home":i%4,
                    "score_away":(i+1)%3})
        payload[season]={"matches":matches}
    return safe,payload


class Step13TrainElasticityOnly(unittest.TestCase):
    def test_complete_two_train_seasons_no_validation_or_test(self):
        safe,payload=fixture()
        rows,digests=extract(payload,safe)
        self.assertEqual(len(rows),760)
        self.assertEqual(len(digests),2)
        r=diagnose(rows,safe,"2026-10-27T01:00:00Z")
        self.assertEqual((r["train_rows"],r["validation_rows_read"],r["test_rows_read"]),(760,0,0))
        self.assertEqual(len(r["profiles"]["TRAIN_760"]),13)
        self.assertEqual(len(r["profiles"]["TRAIN_2023_24"]),13)
        self.assertEqual(len(r["profiles"]["TRAIN_2024_25"]),13)
        self.assertIn(r["original_grid_best_train_elasticity"],[i/10 for i in range(7)])
        self.assertIn(r["diagnostic_grid_best_train_elasticity"],[i/10 for i in range(13)])
        self.assertGreaterEqual(r["train_nll_difference_original_minus_diagnostic"],-1e-8)
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["gate13_pass"])
        self.assertTrue(r["existing_model_parameters_unchanged"])

    def test_wrong_year_validation_poison_refused(self):
        safe,payload=fixture()
        payload["2025/2026"]={"matches":[]}
        with self.assertRaisesRegex(ValueError,"WRONG_SEASON"):
            extract(payload,safe)

    def test_wrong_id_and_kickoff_refused(self):
        safe,payload=fixture()
        payload["2024/2025"]["matches"][0]["time_utc"]="2024-08-05T12:00:00Z"
        with self.assertRaisesRegex(ValueError,"MISMATCHED"):
            extract(payload,safe)

    def test_bad_train_score_refused(self):
        safe,payload=fixture()
        payload["2023/2024"]["matches"][0]["score_home"]=None
        with self.assertRaisesRegex(ValueError,"FINAL_SCORE"):
            extract(payload,safe)

    def test_train_only_full_set_required(self):
        safe,payload=fixture()
        rows,_=extract(payload,safe)
        with self.assertRaisesRegex(ValueError,"TRAIN_ONLY_REQUIRED"):
            diagnose(rows[:759],safe,"2026-10-27T01:00:00Z")

    def test_tampered_train_safe_view_refused(self):
        safe,payload=fixture()
        rows,_=extract(payload,safe)
        bad=copy.deepcopy(safe);bad["training_allowed"]=True
        with self.assertRaisesRegex(ValueError,"FROZEN_SPLIT_CHANGED"):
            diagnose(rows,bad,"2026-10-27T01:00:00Z")

    def test_profile_pure_and_bounded(self):
        pts=[(float(i-15)/6,(i%4)+1,i%2) for i in range(30)]
        r=profile(pts)
        self.assertEqual(r,profile(pts))
        self.assertEqual([x["elasticity"] for x in r],[i/10 for i in range(13)])
        self.assertTrue(all(x["train_goal_nll"]>0 for x in r))

    def test_profile_rejects_inadmissible_data(self):
        with self.assertRaisesRegex(ValueError,"BAD_TRAIN"):
            profile([(0.0,1,True)]*10)
        with self.assertRaisesRegex(ValueError,"GRID_LOCKED"):
            profile([(0.0,1,0)]*10,grid=(0.0,3.0))


if __name__=="__main__":
    unittest.main()
