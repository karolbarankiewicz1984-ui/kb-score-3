"""Real signed source evidence gap counts, no extra API use."""
import copy
import json
from pathlib import Path
import unittest

from src.kb3_split import SplitSafetyError, sha
from src.kb3_step12_evidence_gap import gap_report

SOURCE = (Path(__file__).resolve().parents[1] /
          "data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json")


class GapReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(SOURCE.read_text(encoding="utf8"))

    def test_real_quarantine_counts_are_truthful(self):
        r = gap_report(self.raw)
        self.assertEqual(r["retrospective_finished_not_historic_pit"], 1220)
        self.assertEqual(r["prospective_schedule_only_no_model_features"], 300)
        self.assertEqual(r["eligible_training_examples"], 0)
        self.assertEqual(r["untouched_test_fixture_count"], 380)
        self.assertFalse(r["training_allowed"])
        self.assertEqual(r["partition_reasons"], {
            "TEST:RETROSPECTIVE": 80,
            "TEST:STEP11_FEATURE_TRAINING_NOT_APPROVED": 300,
            "TRAIN:RETROSPECTIVE": 760,
            "VALIDATION:RETROSPECTIVE": 380,
        })
        self.assertEqual(r["report_sha256"], sha({
            k:v for k,v in r.items() if k != "report_sha256"}))

    def test_no_target_or_result_hashes_in_public_aggregate(self):
        data = json.dumps(gap_report(self.raw))
        for forbidden in ('"label_90m"', '"score_home"',
                          '"source_record_sha256"', '"fixture_id"'):
            self.assertNotIn(forbidden, data)

    def test_changed_kickoff_rejected(self):
        altered = copy.deepcopy(self.raw)
        altered["rows"][0]["kickoff_utc"] = "2032-01-01T10:00:00Z"
        with self.assertRaisesRegex(SplitSafetyError, "NOT_PINNED"):
            gap_report(altered)

    def test_rehashed_but_changed_source_rejected(self):
        altered = copy.deepcopy(self.raw)
        altered["rows"][0]["reason"] = "PIT_CERTIFIED"
        altered["manifest_sha256"] = sha({
            k:v for k,v in altered.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "NOT_PINNED"):
            gap_report(altered)


if __name__ == "__main__":
    unittest.main()
