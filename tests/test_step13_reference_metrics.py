"""Step13 metrics: mathematical definitions, never pretend historical data."""
import math
import unittest
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_reference_metrics import score_synthetic_reference


class SyntheticReferenceMetrics(unittest.TestCase):
    def test_uniform_3class_log_loss_and_sum3_brier(self):
        rows=[{"probabilities":{"1":1/3,"X":1/3,"2":1/3},"label":label}
              for label in ("H","D","A")]
        r=score_synthetic_reference(rows,mode="SYNTHETIC_REFERENCE_ONLY")
        self.assertAlmostEqual(r["multiclass_log_loss"],math.log(3),places=12)
        self.assertAlmostEqual(r["multiclass_brier_sum3"],2/3,places=12)
        self.assertEqual(r["sample_size"],3)
        self.assertFalse(r["empirical_historical_performance"])

    def test_synthetic_fully_correct_is_zero_loss(self):
        for label,probs in (("H",{"1":1.0,"X":0.0,"2":0.0}),
                            ("D",{"1":0.0,"X":1.0,"2":0.0}),
                            ("A",{"1":0.0,"X":0.0,"2":1.0})):
            result=score_synthetic_reference(
                [{"probabilities":probs,"label":label}],
                mode="SYNTHETIC_REFERENCE_ONLY")
            self.assertAlmostEqual(result["multiclass_brier_sum3"],0.0,places=14)
            self.assertAlmostEqual(result["multiclass_log_loss"],0.0,places=14)

    def test_confidently_wrong_is_penalized(self):
        row={"probabilities":{"1":0.99,"X":0.005,"2":0.005},"label":"A"}
        r=score_synthetic_reference([row],mode="SYNTHETIC_REFERENCE_ONLY")
        self.assertGreater(r["multiclass_log_loss"],5.0)
        self.assertGreater(r["multiclass_brier_sum3"],1.9)

    def test_each_error_is_rejected(self):
        good=[{"probabilities":{"1":0.4,"X":0.3,"2":0.3},"label":"H"}]
        for mode in ("HISTORICAL", "REAL_BACKTEST", "VALIDATION", ""):
            with self.assertRaisesRegex(BaselineSafetyError,"NOT_CERTIFIED"):
                score_synthetic_reference(good,mode=mode)
        with self.assertRaisesRegex(BaselineSafetyError,"ROWS_REQUIRED"):
            score_synthetic_reference([],mode="SYNTHETIC_REFERENCE_ONLY")
        for broken in (
                [{"probabilities":{"1":0.5,"X":0.3,"2":0.3},"label":"H"}],
                [{"probabilities":{"1":float("nan"),"X":0.3,"2":0.7},"label":"H"}],
                [{"probabilities":{"1":0.5,"X":0.2},"label":"H"}],
                [{"probabilities":{"1":0.5,"X":0.2,"2":0.3},"label":"NO_LABEL"}],
                [{"probabilities":{"1":0.5,"X":0.2,"2":0.3},"label":"H",
                  "bookmaker_odds":1.8}],
            ):
            with self.assertRaises(BaselineSafetyError):
                score_synthetic_reference(broken,mode="SYNTHETIC_REFERENCE_ONLY")

    def test_calibration_bins_count_exactly_n(self):
        examples=[{"probabilities":{"1":0.8,"X":0.1,"2":0.1},"label":"H"},
                  {"probabilities":{"1":0.5,"X":0.4,"2":0.1},"label":"D"},
                  {"probabilities":{"1":0.36,"X":0.33,"2":0.31},"label":"A"}]
        a=score_synthetic_reference(examples,mode="SYNTHETIC_REFERENCE_ONLY")
        self.assertEqual(sum(b["sample_size"] for b in a["calibration_bins"]),3)
        self.assertGreaterEqual(a["top_class_ece_5bins"],0)
        self.assertLessEqual(a["top_class_ece_5bins"],1)
        self.assertFalse(a["training_allowed"])


if __name__=="__main__":
    unittest.main()
