"""Methodology tests: real pinned 1520 native fixtures, no API or labels."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.kb3_split import SplitSafetyError, sha, freeze_manifest
from src.kb3_step12_methodology import (
    method_review, safe_model_fixtures, SAFE_KEYS,
    PINNED_REAL_MANIFEST_SHA256,
)

SOURCE = Path(__file__).resolve().parent.parent / (
    "data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json")


def actual():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


class Step12MethodologyRealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = actual()
        cls.projection, cls.audit = method_review(cls.source)

    def test_verified_real_source_hash_and_counts(self):
        self.assertEqual(self.source["manifest_sha256"],
                         PINNED_REAL_MANIFEST_SHA256)
        self.assertEqual(self.audit["partition_counts"],
                         {"TRAIN": 760, "VALIDATION": 380, "TEST": 380})
        self.assertEqual(len(self.projection["fixtures"]), 1520)

    def test_four_folds_cover_all_validation_without_test(self):
        folds = self.projection["walk_forward"]
        self.assertEqual(len(folds), 4)
        self.assertEqual(sum(x["schedule_validation_count"] for x in folds), 380)
        self.assertEqual(len(set(fid for f in folds
                                 for fid in f["validation_fixture_ids"])), 380)
        holdout = set(self.projection["test_fixture_ids"])
        self.assertEqual(len(holdout), 380)
        for f in folds:
            self.assertFalse(holdout.intersection(f["train_fixture_ids"]))
            self.assertFalse(holdout.intersection(f["validation_fixture_ids"]))
            self.assertFalse(set(f["train_fixture_ids"]).intersection(
                f["validation_fixture_ids"]))
            self.assertEqual(f["eligible_training_count"], 0)
            self.assertEqual(f["eligible_validation_count"], 0)

    def test_safe_projection_has_no_scores_or_label_dependent_hashes(self):
        projection = self.projection
        dangerous = (
            "label_90m", "label_observed_at_utc", "score_home", "score_away",
            "source_record_sha256", "source_records_sha256",
            "native_match_sha256", "source_payload_sha256",
            "source_manifest_sha256", "result", "status", "disposition",
            "evidence_class", "source_chain_sha256",
        )
        raw = json.dumps(projection, ensure_ascii=False)
        for field in dangerous:
            self.assertNotIn('"' + field + '"', raw)
        for row in projection["fixtures"]:
            self.assertEqual(set(row), SAFE_KEYS)
        self.assertNotIn(PINNED_REAL_MANIFEST_SHA256, raw)

    def test_tuning_and_scoring_guards(self):
        with self.assertRaisesRegex(SplitSafetyError, "TEST_HOLDOUT"):
            safe_model_fixtures(self.projection, purpose="tuning", role="TEST")
        with self.assertRaisesRegex(SplitSafetyError, "TUNING_NOT_YET_APPROVED"):
            safe_model_fixtures(self.projection, purpose="tuning", role="TRAIN")
        r = safe_model_fixtures(self.projection, purpose="schedule", role="TEST")
        self.assertEqual(len(r), 380)
        self.assertEqual(set(r[0]), SAFE_KEYS)

    def test_extra_target_field_rejected_even_if_projection_rehashed(self):
        changed = copy.deepcopy(self.projection)
        changed["fixtures"][0]["label_90m"] = "H"
        changed["projection_sha256"] = sha({
            k: v for k, v in changed.items() if k != "projection_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "NO_EXTRA_FIXTURE_FIELDS"):
            safe_model_fixtures(changed, purpose="schedule", role="TRAIN")

    def test_wrong_safe_schema_cannot_be_pretended_to_be_model_view(self):
        changed = copy.deepcopy(self.projection)
        changed["schema"] = "some-privileged-evidence"
        changed["projection_sha256"] = sha({
            k: v for k, v in changed.items() if k != "projection_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "REQUIRES_EXACT_SAFE_SCHEMA"):
            safe_model_fixtures(changed, purpose="schedule", role="TRAIN")

    def test_original_audit_contains_sensitive_label_hashes_is_not_model_view(self):
        self.assertIn("source_record_sha256", self.source["rows"][0])
        self.assertTrue(self.audit["never_supply_privileged_source_to_model"])
        self.assertFalse(self.audit["training_allowed"])
        self.assertFalse(self.audit["gate12_pass"])

    def test_immutable_projection_freeze_and_reconstruction(self):
        rebuilt, report = method_review(actual())
        self.assertEqual(self.projection, rebuilt)
        self.assertEqual(self.audit, report)
        with TemporaryDirectory() as d:
            path = Path(d) / "protocol.json"
            self.assertEqual(freeze_manifest(rebuilt, path), "FROZEN_NEW_VERSION")
            self.assertEqual(freeze_manifest(rebuilt, path), "VERIFIED_UNCHANGED")
            changed = {**rebuilt, "purpose": "tampered"}
            with self.assertRaisesRegex(SplitSafetyError, "IMMUTABLE"):
                freeze_manifest(changed, path)

    def test_corrupted_real_source_rejected(self):
        bad = copy.deepcopy(self.source)
        bad["rows"][0]["kickoff_utc"] = "2030-01-01T00:00:00Z"
        with self.assertRaisesRegex(SplitSafetyError, "REAL_MANIFEST_TAMPER"):
            method_review(bad)

    def test_unauthorized_recomputed_source_blocked_by_pin(self):
        bad = copy.deepcopy(self.source)
        bad["rows"][0]["partition"] = "TEST"
        bad["manifest_sha256"] = sha({
            k: v for k, v in bad.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "REAL_MANIFEST_VERSION_MISMATCH"):
            method_review(bad)

    def test_safe_projection_hash_rejects_injected_taint(self):
        bad = copy.deepcopy(self.projection)
        bad["fixtures"][0]["label_90m"] = "H"
        with self.assertRaisesRegex(SplitSafetyError, "SAFE_PROJECTION_TAMPER"):
            safe_model_fixtures(bad, purpose="schedule", role="TRAIN")

    def test_source_duplicate_even_with_rehash_rejected(self):
        bad = copy.deepcopy(self.source)
        bad["rows"][1]["fixture_id"] = bad["rows"][0]["fixture_id"]
        bad["manifest_sha256"] = sha({
            k: v for k, v in bad.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "DUPLICATE_OR_EMPTY_FIXTURE"):
            method_review(bad, expected_source_sha256=None)

    def test_source_boundary_tamper_even_with_rehash_rejected(self):
        bad = copy.deepcopy(self.source)
        bad["rows"][0]["partition"] = "TEST"
        bad["manifest_sha256"] = sha({
            k: v for k, v in bad.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "CROSS_PARTITION_BOUNDARY"):
            method_review(bad, expected_source_sha256=None)

    def test_source_training_claim_even_with_rehash_rejected(self):
        bad = copy.deepcopy(self.source)
        bad["training_allowed"] = True
        bad["manifest_sha256"] = sha({
            k: v for k, v in bad.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "REAL_GATE_POLICY_INVALID"):
            method_review(bad, expected_source_sha256=None)


if __name__ == "__main__":
    unittest.main()
