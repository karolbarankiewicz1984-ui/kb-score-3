"""Paired variants comparison must keep identical validation labels and PIT blocked."""
import unittest
from src.kb3_step14_m1_xg_comparison import run_demo

class M1PairedVariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=run_demo()

    def test_paired_identical_30_rows_train_90(self):
        r=self.report
        self.assertEqual((r["train_count"],r["validation_count"]),(90,30))
        self.assertEqual(r["validation_calibration_count"],15)
        self.assertEqual(r["validation_later_evaluation_count"],15)
        self.assertEqual(r["same_later_15_paired_variant_comparison"]["n_paired"],15)

    def test_three_versus_seven_features_masks_present(self):
        r=self.report
        self.assertEqual(r["variants"]["NO_XG"]["feature_count"],3)
        self.assertEqual(r["variants"]["WITH_XG_MASKS"]["feature_count"],7)
        self.assertEqual(r["class_order"],["1","X","2"])
        self.assertTrue(r["with_xg_preserves_nullable_xg_and_missing_mask"])

    def test_probabilities_scores_and_reliability_are_bounded(self):
        for v in self.report["variants"].values():
            for block in (v["all_30_synthetic_valid"],
                          v["later_15_untouched_calibration_evaluation"]["raw"],
                          v["later_15_untouched_calibration_evaluation"]["calibrated"]):
                self.assertGreaterEqual(block["log_loss"],0)
                self.assertTrue(0<=block["brier_sum3"]<=2)
                self.assertTrue(0<=block["top1_ece_10bins"]<=1)
                self.assertEqual(sum(x["count"] for x in block["reliability_top1"]),block["n"])

    def test_calibration_never_uses_later_evaluation_and_has_no_auto_activation(self):
        r=self.report
        self.assertFalse(r["evaluation_previously_seen_in_calibration"])
        for v in r["variants"].values():
            self.assertEqual(v["calibration_fit_earlier_15"]["calibration_rows"],15)
            self.assertEqual(v["later_15_untouched_calibration_evaluation"]["raw"]["n"],15)
            self.assertFalse(v["later_15_untouched_calibration_evaluation"][
                "recommend_automatic_production_activation"])

    def test_temporary_synthetic_model_not_real_production_m1(self):
        r=self.report
        self.assertFalse(r["original_real_train_PIT_certified"])
        self.assertFalse(r["production_approved"])
        self.assertFalse(r["gate14_pass"])
        self.assertEqual(r["test_rows_read"],0)
        self.assertFalse(r["odds_used"])

if __name__=="__main__":unittest.main()
