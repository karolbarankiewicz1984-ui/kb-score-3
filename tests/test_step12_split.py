"""Step 12: synthetic safety fixtures, not real match evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.kb3_split import (
    SplitSafetyError, build_manifest, freeze_manifest, sha, timestamp,
)

EXPORT = "2026-10-26T14:30:00Z"


def item(mid="train-1", kickoff="2024-01-15T20:00:00Z",
         cutoff="2024-01-15T10:00:00Z",
         observed="2024-01-15T09:00:00Z",
         label_at="2024-01-16T00:00:00Z",
         evidence="PROSPECTIVE_OBSERVED_AT", approved=True):
    return {
        "fixture_id": mid, "kickoff_utc": kickoff,
        "feature_cutoff_utc": cutoff,
        "feature_availability": {"elo": {
            "latest_required_observed_at_utc": observed,
            "training_allowed": approved,
            "evidence_class": "OBSERVED_AT_NOT_PROVIDER_PUBLISHED"}},
        "evidence_class": evidence, "label_90m": "H",
        "label_observed_at_utc": label_at,
    }


def build(records):
    return build_manifest(records, dataset_version="synthetic-v1",
                          exported_at_utc=EXPORT)


class Step12SplitTests(unittest.TestCase):
    def test_chronological_boundaries_and_no_target_labels_in_manifest(self):
        rows = [
            item(), item("valid-1", "2025-08-15T20:00:00Z",
                         "2025-08-15T10:00:00Z", "2025-08-15T09:00:00Z",
                         "2025-08-16T00:00:00Z"),
            item("test-1", "2026-08-15T20:00:00Z",
                 "2026-08-15T10:00:00Z", "2026-08-15T09:00:00Z",
                 "2026-08-16T00:00:00Z"),
        ]
        manifest = build(list(reversed(rows)))
        self.assertEqual(manifest["eligible_counts"], {
            "TRAIN": 1, "VALIDATION": 1, "TEST": 1})
        self.assertFalse(manifest["training_allowed"])
        self.assertFalse(manifest["gate12_pass"])
        self.assertTrue(manifest["test_held_out"])
        self.assertNotIn('"label_90m"', json.dumps(manifest))
        self.assertNotIn('"label_observed_at_utc"', json.dumps(manifest))
        self.assertEqual(manifest["manifest_sha256"],
                         sha({k: v for k, v in manifest.items()
                              if k != "manifest_sha256"}))

    def test_stable_hash_independent_of_input_order(self):
        a = item()
        b = item("valid-1", "2025-08-15T20:00:00Z",
                 "2025-08-15T10:00:00Z", "2025-08-15T09:00:00Z",
                 "2025-08-16T00:00:00Z")
        self.assertEqual(build([a, b]), build([b, a]))

    def test_retro_history_cannot_be_backtested_as_pit(self):
        retro = item(evidence="RETROSPECTIVE")
        manifest = build([retro])
        self.assertEqual(manifest["eligible_counts"]["TRAIN"], 0)
        self.assertEqual(manifest["quarantined_count"], 1)
        self.assertEqual(manifest["rows"][0]["reason"], "RETROSPECTIVE")

    def test_unapproved_step11_features_cannot_pass(self):
        manifest = build([item(approved=False)])
        self.assertEqual(manifest["rows"][0]["reason"],
                         "STEP11_FEATURE_TRAINING_NOT_APPROVED")

    def test_missing_xg_does_not_imply_zero_or_eligibility(self):
        r = item()
        r["feature_availability"] = {}
        with self.assertRaisesRegex(SplitSafetyError, "MISSING_PER_FEATURE"):
            build([r])

    def test_future_feature_receipt_rejected(self):
        with self.assertRaisesRegex(SplitSafetyError, "FEATURE_OBSERVED_AFTER_CUTOFF"):
            build([item(observed="2024-01-15T11:00:00Z")])

    def test_feature_cutoff_at_kickoff_rejected(self):
        with self.assertRaisesRegex(SplitSafetyError, "FEATURE_CUTOFF_AFTER_KICKOFF"):
            build([item(cutoff="2024-01-15T20:00:00Z")])

    def test_label_observed_before_kickoff_rejected(self):
        with self.assertRaisesRegex(SplitSafetyError, "LABEL_OBSERVED_BEFORE_KICKOFF"):
            build([item(label_at="2024-01-15T19:00:00Z")])

    def test_historic_train_result_arriving_after_validation_start(self):
        r = item(label_at="2026-01-01T00:00:00Z")
        self.assertEqual(build([r])["rows"][0]["reason"],
                         "LABEL_TOO_LATE_FOR_NEXT_PARTITION")

    def test_label_future_to_export_rejected(self):
        with self.assertRaisesRegex(SplitSafetyError, "LABEL_OBSERVED_AFTER_EXPORT"):
            build([item(label_at="2026-11-01T00:00:00Z")])

    def test_duplicate_fixture_id_rejected(self):
        with self.assertRaisesRegex(SplitSafetyError, "DUPLICATE_FIXTURE_ID"):
            build([item(), item()])

    def test_naive_date_rejected(self):
        r = item()
        r["kickoff_utc"] = "2024-01-15T20:00:00"
        with self.assertRaisesRegex(SplitSafetyError, "NAIVE_TIMESTAMP"):
            build([r])

    def test_pending_future_match_not_eligible(self):
        r = item(mid="future", kickoff="2026-11-20T20:00:00Z",
                 cutoff="2026-11-20T08:00:00Z",
                 observed="2026-11-20T07:00:00Z")
        r["label_90m"] = None
        r["label_observed_at_utc"] = None
        self.assertEqual(build([r])["rows"][0]["reason"], "PENDING_LABEL")

    def test_walk_forward_expanding_train_never_includes_test(self):
        rows = [
            item(), item("valid-1", "2025-08-15T20:00:00Z",
                         "2025-08-15T10:00:00Z", "2025-08-15T09:00:00Z",
                         "2025-08-16T00:00:00Z"),
            item("valid-2", "2025-11-15T20:00:00Z",
                 "2025-11-15T10:00:00Z", "2025-11-15T09:00:00Z",
                 "2025-11-16T00:00:00Z"),
            item("test-1", "2026-08-15T20:00:00Z",
                 "2026-08-15T10:00:00Z", "2026-08-15T09:00:00Z",
                 "2026-08-16T00:00:00Z"),
        ]
        folds = build(rows)["walk_forward"]
        self.assertIn("valid-1", folds[1]["training_fixture_ids"])
        self.assertIn("valid-2", folds[1]["validation_fixture_ids"])
        self.assertTrue(all(
            "test-1" not in fold["training_fixture_ids"] +
            fold["validation_fixture_ids"] for fold in folds))

    def test_immutable_write_and_verify(self):
        m = build([item()])
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "step12_v1.json"
            self.assertEqual(freeze_manifest(m, path), "FROZEN_NEW_VERSION")
            self.assertEqual(freeze_manifest(m, path), "VERIFIED_UNCHANGED")
            with self.assertRaisesRegex(
                    SplitSafetyError, "IMMUTABLE_SPLIT_VERSION_CONFLICT"):
                freeze_manifest({**m, "dataset_version": "changed"}, path)


if __name__ == "__main__":
    unittest.main()
