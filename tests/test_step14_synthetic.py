"""Step14 offline fail-closed checks: all match records generated in code."""
import copy
import math
import unittest

from src.kb3_step14_synthetic import (
    Step14SafetyError, synthetic_rows, validate_dataset,
    validate_row, run_synthetic_catboost,
)


class Step14SyntheticContract(unittest.TestCase):
    def setUp(self):
        self.rows = synthetic_rows()

    def test_synthetic_partition_and_provenance(self):
        train, valid = validate_dataset(self.rows)
        self.assertEqual((len(train), len(valid)), (90, 30))

    def test_future_cutoff_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["feature_cutoff_utc"] = row["kickoff_utc"]
        with self.assertRaisesRegex(Step14SafetyError, "FUTURE"):
            validate_row(row)

    def test_source_future_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["source_observed_at_utc"] = row["kickoff_utc"]
        with self.assertRaisesRegex(Step14SafetyError, "FUTURE"):
            validate_row(row)

    def test_future_feature_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["feature_availability"]["elo_home_minus_away"] = row["kickoff_utc"]
        with self.assertRaisesRegex(Step14SafetyError, "FUTURE"):
            validate_row(row)

    def test_odds_and_result_columns_rejected(self):
        for name in ("odds_1x2", "goals_home_90", "postmatch_result"):
            row = copy.deepcopy(self.rows[0])
            row[name] = 1
            with self.subTest(name=name), self.assertRaisesRegex(Step14SafetyError, "POSSIBLE_LEAK"):
                validate_row(row)

    def test_no_real_rows_even_if_partition_train(self):
        row = copy.deepcopy(self.rows[0])
        row["evidence_class"] = "RETROSPECTIVE"
        with self.assertRaisesRegex(Step14SafetyError, "REAL_FIT_BLOCKED"):
            validate_row(row)
        row = copy.deepcopy(self.rows[0])
        row["partition"] = "TEST"
        with self.assertRaisesRegex(Step14SafetyError, "NOT_FOR_TRAINING"):
            validate_row(row)

    def test_xg_missing_not_zero_and_flags_exact(self):
        row = copy.deepcopy(self.rows[0])
        self.assertIsNone(row["features"]["home_all_5_xg_avg"])
        row["features"]["home_all_5_xg_avg"] = 0
        with self.assertRaisesRegex(Step14SafetyError, "MISSING_XG"):
            validate_row(row)

    def test_duplicate_fixture_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[1]["fixture_id"] = rows[0]["fixture_id"]
        with self.assertRaisesRegex(Step14SafetyError, "DUPLICATE"):
            validate_dataset(rows)

    def test_naive_timezone_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row["kickoff_utc"] = "2024-01-01T00:00:00"
        with self.assertRaisesRegex(Step14SafetyError, "TIMESTAMP_MUST_BE_UTC"):
            validate_row(row)

    def test_cpu_catboost_deterministic_data_and_probabilities(self):
        first = run_synthetic_catboost(use_xg=False)
        second = run_synthetic_catboost(use_xg=False)
        self.assertEqual(first["synthetic_data_sha256"], second["synthetic_data_sha256"])
        self.assertAlmostEqual(first["synthetic_log_loss"], second["synthetic_log_loss"], places=12)
        self.assertTrue(math.isfinite(first["synthetic_brier_sum3"]))
        self.assertFalse(first["real_data_training_eligible"])
        self.assertFalse(first["gate14_pass"])
        xg = run_synthetic_catboost(use_xg=True)
        self.assertEqual(xg["synthetic_train_count"], 90)
        self.assertEqual(xg["synthetic_validation_count"], 30)
        self.assertFalse(xg["production_approved"])


if __name__ == "__main__":
    unittest.main()
