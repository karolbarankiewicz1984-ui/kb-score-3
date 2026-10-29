"""Negative controls for original historical M1 training gate."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.step14_final_gate14_recheck import (
    audit, write, Gate14EvidenceError, LINEAGE, ROOT, _source_check)
from src.kb3_step14_real_pit_gate import check_real_fit_admission, RealPITGateError


class FinalStep14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.rows = audit()

    def test_all_1140_native_records_and_159_fields_have_explicit_state(self):
        self.assertEqual(len(self.rows), 1140)
        self.assertEqual(self.report["matrix_evidence_slots"], 181260)
        self.assertEqual(self.report["original_field_evidence_slots_proven"], 0)
        self.assertEqual(sum(len(x["field_receipts"]["numeric"]) for x in self.rows), 1140*121)
        self.assertEqual(sum(len(x["field_receipts"]["missing_flags"]) for x in self.rows), 1140*38)
        self.assertTrue(all(x["original_feature_cutoff_utc"] is None for x in self.rows))
        self.assertEqual(self.report["gate14"], "PENDING")

    def test_fit_and_actual_m1_metrics_unavailable_without_historic_pit(self):
        self.assertFalse(self.report["allow_M1_fit"])
        self.assertFalse(self.report["real_CatBoost_M1_model_exported"])
        self.assertIsNone(self.report["real_CatBoost_M1_log_loss"])
        self.assertIsNone(self.report["real_CatBoost_M1_TEST_metrics"])
        self.assertFalse(self.report["original_heldout_TEST_labels_read"])
        with self.assertRaisesRegex(RealPITGateError, "REAL_M1_FIT_DENIED"):
            from src.kb3_step14_real_pit_gate import SAFE_PATH, REAL_PATH
            check_real_fit_admission(json.loads((ROOT/REAL_PATH).read_text()),
                                     json.loads((ROOT/SAFE_PATH).read_text()))

    def test_source_recheck_no_evidence_cannot_activate_training(self):
        source = {
          "schema":"kb3-step14-last-2024-and-validation-2025-fpl-old-sources-v1",
          "source_candidates":5,"sources":[{"season":"2025-26","verified_publication":False}]*5,
          "independently_verified_sources":[],"training_allowed":False,"gate14_pass":False
        }
        report, _ = audit(source_report=source)
        self.assertEqual(report["source_2025_26_recheck"]["state"], "REAL_ARCHIVE_RECHECK")
        self.assertEqual(report["original_full_PIT_train_rows"], 0)
        self.assertFalse(report["allow_M1_fit"])
        source["training_allowed"] = True
        with self.assertRaisesRegex(Gate14EvidenceError, "UNTRUSTED"):
            audit(source_report=source)

    def test_duplicate_or_faked_eligibility_is_refused(self):
        original=(ROOT/LINEAGE).read_text()
        first,rest=original.splitlines()[0],original.splitlines()[1:]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.jsonl"
            path.write_text(first+"\n"+first+"\n"+"\n".join(rest)+"\n")
            with self.assertRaisesRegex(Gate14EvidenceError,"DUPLICATE"):
                audit(lineage_override=path)
            injected=json.loads(first)
            injected["original_121_plus_38_PIT_training_eligible"]=True
            path.write_text(json.dumps(injected)+"\n"+"\n".join(rest)+"\n")
            with self.assertRaisesRegex(Gate14EvidenceError,"UNAUTHORIZED"):
                audit(lineage_override=path)

    def test_matrix_is_restorable_and_not_encrypted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"audit.json"
            matrix=Path(tmp)/"rows.jsonl.gz"
            write(dict(self.report),self.rows,out,matrix)
            saved=json.loads(out.read_text())
            import gzip, hashlib
            with gzip.open(matrix,"rt") as f:
                rows=[json.loads(line) for line in f]
            self.assertEqual(len(rows),1140)
            self.assertEqual(saved["matrix_gzip_sha256"],
                             hashlib.sha256(matrix.read_bytes()).hexdigest())
            with self.assertRaisesRegex(Gate14EvidenceError,"NO_OVERWRITE"):
                write(dict(self.report),self.rows,out,matrix)


if __name__=="__main__":
    unittest.main()
