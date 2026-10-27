"""Offline Step14 readiness: no fixture or match result data accessed."""
import copy
import json
from pathlib import Path
import unittest

from src.kb3_step14_readiness import (
    RECORDS, Step14ReadinessError, inspect_original_training_gate,
    inspect_repo_aggregate_only,
)
from src.kb3_split import sha


ROOT = Path(__file__).resolve().parents[1]


def aggregates():
    return [json.loads((ROOT / path).read_text(encoding="utf8"))
            for path, _, _ in RECORDS]


class Step14PITEvidenceGate(unittest.TestCase):
    def setUp(self):
        self.records = aggregates()

    def test_real_signed_aggregates_stay_closed_without_reading_test(self):
        out = inspect_original_training_gate(*self.records)
        self.assertEqual(out["source_paths"], [r[0] for r in RECORDS])
        self.assertEqual(out["fixture_ids_read"], 0)
        self.assertEqual(out["actual_raw_result_labels_read"], 0)
        self.assertEqual(out["eligibility_in_old_pit_gap_audit"], 0)
        self.assertFalse(out["historic_gap_is_current_certification"])
        self.assertFalse(out["real_catboost_fit_eligible"])
        self.assertFalse(out["gate14_pass"])

    def test_report_schema_matches_pinned_hashes(self):
        for doc, (_, field, expected) in zip(self.records, RECORDS):
            self.assertEqual(doc[field], expected)
            self.assertEqual(sha({k: v for k, v in doc.items() if k != field}), expected)

    def test_modified_evidence_without_resigning_rejected(self):
        x = copy.deepcopy(self.records)
        x[1]["eligible_training_examples"] = 760
        with self.assertRaisesRegex(Step14ReadinessError, "REPORT_SHA"):
            inspect_original_training_gate(*x)

    def test_forged_training_permission_and_resigned_report_rejected(self):
        x = copy.deepcopy(self.records)
        x[1]["eligible_training_examples"] = 760
        x[1]["training_allowed"] = True
        x[1]["report_sha256"] = sha({k: v for k, v in x[1].items() if k != "report_sha256"})
        with self.assertRaisesRegex(Step14ReadinessError, "PINNED_REPORT_CHANGED"):
            inspect_original_training_gate(*x)

    def test_accepted_step13_scope_cannot_grant_training(self):
        x = copy.deepcopy(self.records)
        x[2]["training_allowed"] = True
        with self.assertRaisesRegex(Step14ReadinessError, "REPORT_SHA"):
            inspect_original_training_gate(*x)

    def test_test_label_flag_mutation_rejected(self):
        x = copy.deepcopy(self.records)
        x[0]["test_labels_accessed"] = True
        with self.assertRaisesRegex(Step14ReadinessError, "REPORT_SHA"):
            inspect_original_training_gate(*x)

    def test_repository_read_path_restricted_to_three_aggregates(self):
        out = inspect_repo_aggregate_only(ROOT)
        self.assertEqual(len(out["source_paths"]), 3)
        self.assertTrue(all("/audits/" in p for p in out["source_paths"]))
        self.assertEqual(out["new_sports_api_calls"], 0)


if __name__ == "__main__":
    unittest.main()
