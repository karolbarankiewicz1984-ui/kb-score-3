"""KB3 Step12 acceptance tests against unchanged 1520-real-fixture protocol."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.kb3_split import SplitSafetyError, freeze_manifest, sha
from src.kb3_step12_acceptance import accept_methodology

ROOT = Path(__file__).resolve().parents[1]


def loads(path):
    return json.loads((ROOT / path).read_text(encoding="utf8"))


class FinalMethodologyAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.safe = loads("data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json")
        cls.dual = loads("data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json")
        cls.acceptance = accept_methodology(cls.safe, cls.dual)

    def test_real_protocol_gate_can_pass_without_training(self):
        a = self.acceptance
        self.assertTrue(a["step12_gate_pass"])
        self.assertFalse(a["training_allowed"])
        self.assertFalse(a["real_historical_pit_verified"])
        self.assertEqual((a["completed_steps"], a["total_steps"]), (12, 29))
        self.assertEqual(a["validation_fixture_coverage"], 380)
        self.assertEqual(a["heldout_test_fixtures"], 380)

    def test_both_methods_same_validation_without_test(self):
        a = self.acceptance
        self.assertEqual(
            [f["shared_validation_fixtures"] for f in a["folds"]],
            [60, 126, 123, 71])
        self.assertEqual(
            [f["expanding_schedule_candidates"] for f in a["folds"]],
            [760, 820, 946, 1069])
        self.assertEqual(
            [f["rolling_two_year_schedule_candidates"] for f in a["folds"]],
            [760, 753, 750, 776])
        self.assertEqual([f["test_overlap"] for f in a["folds"]], [0]*4)

    def test_no_model_metrics_or_actual_training(self):
        a = self.acceptance
        self.assertFalse(a["test_labels_accessed"])
        self.assertFalse(a["validation_predictions_created"])
        self.assertFalse(a["training_allowed"])
        self.assertIn("VERIFIED_PREMATCH_FEATURE_PROVENANCE",
                      a["next_step13_training_blocked_until"])

    def test_reproducible_record_and_freeze(self):
        first = accept_methodology(loads("data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"), loads("data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json"))
        self.assertEqual(first, self.acceptance)
        first["record_sha256"] = sha(first)
        with TemporaryDirectory() as folder:
            target = Path(folder) / "gate.json"
            self.assertEqual(freeze_manifest(first, target), "FROZEN_NEW_VERSION")
            self.assertEqual(freeze_manifest(first, target), "VERIFIED_UNCHANGED")
            with self.assertRaisesRegex(SplitSafetyError, "IMMUTABLE"):
                freeze_manifest({**first, "training_allowed": True}, target)

    def test_corrupt_schedule_rejected(self):
        bad = copy.deepcopy(self.safe)
        bad["fixtures"][0]["kickoff_utc"] = "2027-05-12T20:00:00Z"
        with self.assertRaisesRegex(SplitSafetyError, "SOURCE"):
            accept_methodology(bad, self.dual)

    def test_changes_even_with_valid_recomputed_dual_hash_rejected(self):
        bad = copy.deepcopy(self.dual)
        bad["folds"][0]["strategies"]["ROLLING_24_CALENDAR_MONTHS"]["schedule_candidate_fixture_ids"].pop()
        bad["comparison_sha256"] = sha({
            k: v for k, v in bad.items() if k != "comparison_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "DUAL_VERSION"):
            accept_methodology(self.safe, bad)

    def test_test_in_history_rejected(self):
        bad = copy.deepcopy(self.dual)
        bad["folds"][1]["strategies"]["EXPANDING"]["schedule_candidate_fixture_ids"].append(
            self.safe["test_fixture_ids"][0])
        with self.assertRaisesRegex(SplitSafetyError, "DUAL_CONTENT"):
            accept_methodology(self.safe, bad)

    def test_false_training_approval_rejected(self):
        bad = copy.deepcopy(self.dual)
        bad["training_allowed"] = True
        with self.assertRaisesRegex(SplitSafetyError, "DUAL_CONTENT"):
            accept_methodology(self.safe, bad)

    def test_no_provider_data_or_scores_in_method_record(self):
        encoded = json.dumps(self.acceptance, sort_keys=True)
        for value in ("label_90m", "score_home", "score_away", "xg_home",
                      "source_record_sha256", "trained_model", "predictions"):
            self.assertNotIn('"' + value + '"', encoded)


if __name__ == "__main__":
    unittest.main()
