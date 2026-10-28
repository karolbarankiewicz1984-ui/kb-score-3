import json,copy,unittest
from pathlib import Path
from src.kb3_step14_a_nonxg_1140_pit_matrix import construct,MatrixError,ROW_STATUS
R=Path(__file__).resolve().parents[1]
class A73NoXG(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
    cls.safe=json.loads((R/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
 def test_full_real_metadata_1140_without_holdout(self):
    a,rows=construct(self.safe)
    self.assertEqual((len(rows),a["non_xg_numeric_fields_per_row"],a["non_xg_missing_flags_per_row"]),(1140,73,14))
    self.assertEqual(a["partition_counts"],{"TRAIN":760,"VALIDATION":380})
    self.assertFalse(a["training_allowed"])
 def test_every_field_original_pit_denied(self):
    a,rows=construct(self.safe)
    self.assertEqual(a["non_xg_field_evidence_slots"],1140*87)
    self.assertEqual(a["non_xg_qualified_field_slots"],0)
    for x in rows:
        self.assertIsNone(x["original_cutoff"])
        self.assertFalse(x["eligible_no_xg_original_M1"])
        self.assertEqual(set(x["original_feature_availability"].values()),{ROW_STATUS})
        self.assertEqual(set(x["original_missing_flag_availability"].values()),{ROW_STATUS})
 def test_no_xg_names_and_no_scores(self):
    _,rows=construct(self.safe)
    for r in rows[:20]:
        self.assertFalse(any("xg" in k for k in r["original_feature_availability"]))
        self.assertFalse(any("xg" in k for k in r["original_missing_flag_availability"]))
        self.assertNotIn("score_home",str(r))
        self.assertNotIn("goals_home_90",str(r))
 def test_source_snapshot_only_candidate_not_proof(self):
    _,rows=construct(self.safe)
    self.assertTrue(any(x["public_older_snapshot_count_NOT_NATIVE_RECEIPTS"]>0 for x in rows))
    self.assertFalse(any(x["original_team_identity_proof"] for x in rows))
 def test_fake_split_manifest_rejected(self):
    safe=copy.deepcopy(self.safe);safe["partition_counts"]["TRAIN"]=759
    with self.assertRaises(Exception):construct(safe)
 def test_fake_prediction_time_rejected(self):
    safe=copy.deepcopy(self.safe)
    for r in safe["fixtures"]:
        if r.get("partition")=="TRAIN":
            r["kickoff_utc"]="2026-10-28T20:00:00Z";break
    with self.assertRaises(Exception):construct(safe)
if __name__=="__main__":unittest.main()
