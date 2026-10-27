"""Step13 aggregate-only calibration stability: no provider, no TEST or scores."""
import copy
import json
from pathlib import Path
import unittest

from src.kb3_split import sha
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_stability_audit import audit_stability, SOURCE

def original():
    return json.loads((Path(__file__).resolve().parents[1]/SOURCE).read_text())

def repin(record):
    record["report_sha256"]=sha({k:v for k,v in record.items() if k!="report_sha256"})
    return record


class Step13StabilityAuditTests(unittest.TestCase):
    def test_genuine_aggregate_real_research_without_pit_promotion(self):
        r=audit_stability(original())
        self.assertEqual(r["validation_total"],380)
        self.assertEqual(r["test_rows_read"],0)
        self.assertEqual(r["methods"]["EXPANDING"]["top1_correct_count"],185)
        self.assertEqual(r["methods"]["ROLLING_24_CALENDAR_MONTHS"]["top1_correct_count"],184)
        self.assertEqual(r["folds_with_lower_expanding_logloss"],2)
        self.assertEqual(r["folds_with_lower_rolling_logloss"],1)
        self.assertEqual(r["folds_with_equal_logloss"],1)
        self.assertTrue(r["all_eight_elasticity_fits_at_original_grid_upper_edge"])
        self.assertTrue(r["fold3_overconfidence_detected_both_methods"])
        self.assertFalse(r["real_historical_pit_proven"])
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["gate13_pass"])
        self.assertFalse(r["model_winner_promoted"])
        self.assertFalse(r["retraining_or_parameter_grid_change_performed"])
        self.assertIsNone(r["comparison_statistically_significant"])
        self.assertFalse(r["per_match_paired_confidence_intervals_available"])
        self.assertEqual(r["report_sha256"],sha({k:v for k,v in r.items() if k!="report_sha256"}))

    def test_quarter_three_accuracy_is_lower_than_confidence(self):
        r=audit_stability(original())
        for method in ("EXPANDING","ROLLING_24_CALENDAR_MONTHS"):
            q=r["methods"][method]["quarterly"][2]
            self.assertEqual(q["validation_n"],123)
            self.assertEqual(q["top1_correct_count"],48)
            self.assertLess(q["top1_accuracy"],0.40)
            self.assertGreater(q["mean_top1_confidence"],0.48)
            self.assertLess(q["accuracy_minus_confidence"],-0.09)

    def test_pooled_ece_can_mask_quarterly_regime_changes(self):
        r=audit_stability(original())
        for method in ("EXPANDING","ROLLING_24_CALENDAR_MONTHS"):
            q=r["methods"][method]["quarterly"]
            self.assertGreater(q[1]["accuracy_minus_confidence"],0.08)
            self.assertLess(q[2]["accuracy_minus_confidence"],-0.09)
            self.assertLess(r["methods"][method]["top1_ece_pooled_5bin_descriptive_only"],
                            r["methods"][method]["top1_ece_fold_weighted_5bin"])
            self.assertEqual(sum(b["n"] for b in r["methods"][method]["merged_bins"]),380)

    def test_stability_report_is_deterministic(self):
        a=audit_stability(original())
        self.assertEqual(a,audit_stability(original()))

    def test_data_tamper_with_old_hash_rejected(self):
        rec=original()
        rec["folds"][2]["methods"]["EXPANDING"]["metrics"]["top_class_ece_5bin"]=0.0
        with self.assertRaisesRegex(BaselineSafetyError,"TAMPERED"):
            audit_stability(rec)

    def test_even_rehashed_new_report_rejected(self):
        rec=original()
        rec["test_rows_processed"]=1
        repin(rec)
        with self.assertRaisesRegex(BaselineSafetyError,"WRONG_PINNED"):
            audit_stability(rec)

    def test_wrong_sha_rejected(self):
        rec=original()
        rec["report_sha256"]="00"*32
        with self.assertRaisesRegex(BaselineSafetyError,"WRONG_PINNED"):
            audit_stability(rec)


if __name__=="__main__":
    unittest.main()
