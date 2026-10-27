"""Real manifest *metadata-only* PIT gate; never open per-match TEST labels."""
import copy
import json
from pathlib import Path
import unittest
from src.kb3_step14_real_pit_gate import (
    RealPITGateError, REAL_PATH, SAFE_PATH,
    inspect_real_pit_manifest, inspect_repo, check_real_fit_admission,
)

ROOT=Path(__file__).resolve().parents[1]


def sources():
    return (
        json.loads((ROOT / REAL_PATH).read_text(encoding="utf8")),
        json.loads((ROOT / SAFE_PATH).read_text(encoding="utf8")),
    )


class RealStep14TrainingAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real,cls.safe=sources()

    def test_real_signed_index_760_380_has_no_eligible_training(self):
        r=inspect_real_pit_manifest(self.real,self.safe)
        self.assertEqual((r["train_row_count"],r["validation_row_count"]),(760,380))
        self.assertEqual((r["train_missing_feature_cutoff_count"],
                          r["validation_missing_feature_cutoff_count"]),(760,380))
        self.assertEqual((r["train_proven_pre_match_eligible"],
                          r["validation_proven_pre_match_eligible"]),(0,0))
        self.assertEqual(r["test_rows_examined"],0)
        self.assertEqual(r["test_targets_read"],0)
        self.assertFalse(r["real_catboost_train_allowed"])
        self.assertFalse(r["gate14_pass"])

    def test_real_model_fit_is_refused_before_catboost(self):
        with self.assertRaisesRegex(RealPITGateError,"REAL_M1_FIT_DENIED"):
            check_real_fit_admission(self.real,self.safe)

    def test_repo_entrypoint_same_evidence(self):
        self.assertEqual(inspect_repo(ROOT),inspect_real_pit_manifest(self.real,self.safe))

    def test_tamper_fake_prematch_cutoff_rejected(self):
        real=copy.deepcopy(self.real)
        row=next(r for r in real["rows"] if r["partition"]=="TRAIN")
        row["feature_cutoff_utc"]="2023-08-10T12:00:00Z"
        with self.assertRaisesRegex(RealPITGateError,"SOURCE_TAMPERED"):
            inspect_real_pit_manifest(real,self.safe)

    def test_tamper_training_release_rejected(self):
        real=copy.deepcopy(self.real)
        real["training_allowed"]=True
        with self.assertRaisesRegex(RealPITGateError,"SOURCE_TAMPERED"):
            inspect_real_pit_manifest(real,self.safe)

    def test_re_signing_modified_manifest_is_not_authorization(self):
        from src.kb3_split import sha
        real=copy.deepcopy(self.real)
        row=next(r for r in real["rows"] if r["partition"]=="TRAIN")
        row["feature_cutoff_utc"]="2023-08-10T12:00:00Z"
        real["manifest_sha256"]=sha({k:v for k,v in real.items() if k!="manifest_sha256"})
        with self.assertRaisesRegex(RealPITGateError,"SOURCE_PIN_MISMATCH"):
            inspect_real_pit_manifest(real,self.safe)

    def test_corrupt_safe_projection_rejected(self):
        safe=copy.deepcopy(self.safe)
        row=next(r for r in safe["fixtures"] if r["partition"]=="TRAIN")
        row["kickoff_utc"]="2023-01-01T10:00:00Z"
        with self.assertRaisesRegex(RealPITGateError,"SOURCE_TAMPERED"):
            inspect_real_pit_manifest(self.real,safe)

    def test_injected_target_and_odds_never_accepted(self):
        safe=copy.deepcopy(self.safe)
        row=next(r for r in safe["fixtures"] if r["partition"]=="TRAIN")
        row["odds_1x2"]=1.5
        with self.assertRaisesRegex(RealPITGateError,"SOURCE_TAMPERED"):
            inspect_real_pit_manifest(self.real,safe)

    def test_preserve_test_holdout_and_four_fold_counts(self):
        r=inspect_real_pit_manifest(self.real,self.safe)
        self.assertEqual(r["no_lookahead_source_index_check"],"PASS_SCHEDULE_IDENTITY_ONLY")
        self.assertEqual(r["no_lookahead_actual_model_assessment"],"NOT_PERFORMED")
        self.assertFalse(r["real_validation_metrics_available"])


if __name__=="__main__":
    unittest.main()
