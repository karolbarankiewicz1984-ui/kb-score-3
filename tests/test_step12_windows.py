"""Step12 real 1520 fixture dual-window regression tests; no API, no fitting."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.kb3_split import SplitSafetyError, freeze_manifest, sha, timestamp
from src.kb3_step12_windows import comparison, SOURCE_VIEW_SHA256

SOURCE = Path(__file__).resolve().parent.parent / (
    "data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json")


def source():
    return json.loads(SOURCE.read_text(encoding="utf8"))


class Step12TwoHistoryMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.safe = source()
        cls.plan, cls.report = comparison(cls.safe)

    def test_old_safe_model_view_has_expected_pinned_sha(self):
        self.assertEqual(self.safe["projection_sha256"], SOURCE_VIEW_SHA256)
        self.assertEqual(self.plan["safe_source_view_sha256"], SOURCE_VIEW_SHA256)
        self.assertEqual(self.plan["comparison_sha256"], sha({
            k: v for k, v in self.plan.items() if k != "comparison_sha256"}))
        self.assertFalse(self.plan["training_allowed"])

    def test_identical_validation_for_two_history_strategies(self):
        self.assertEqual(len(self.plan["folds"]), 4)
        self.assertEqual(
            [f["validation_fixture_count"] for f in self.plan["folds"]],
            [60, 126, 123, 71])
        self.assertEqual(self.plan["all_validation_candidate_count"], 380)
        self.assertTrue(all(f["validation_fixture_ids"] for f in self.plan["folds"]))

    def test_rolling_calendar_lower_bound_and_expanding_start(self):
        fs = self.plan["folds"]
        self.assertEqual(
            [f["strategies"]["ROLLING_24_CALENDAR_MONTHS"][
                "history_from_inclusive_utc"] for f in fs],
            ["2023-07-01T00:00:00Z", "2023-10-01T00:00:00Z",
             "2024-01-01T00:00:00Z", "2024-04-01T00:00:00Z"])
        self.assertTrue(all(f["strategies"]["EXPANDING"][
            "history_from_inclusive_utc"] == "2023-07-01T00:00:00Z"
                            for f in fs))

    def test_same_initial_history_and_rolling_subset_every_quarter(self):
        folds = self.plan["folds"]
        for f in folds:
            e = set(f["strategies"]["EXPANDING"]["schedule_candidate_fixture_ids"])
            r = set(f["strategies"]["ROLLING_24_CALENDAR_MONTHS"][
                "schedule_candidate_fixture_ids"])
            self.assertLessEqual(len(r), len(e))
            self.assertTrue(r.issubset(e))
        self.assertEqual(
            folds[0]["strategies"]["EXPANDING"]["schedule_candidate_fixture_ids"],
            folds[0]["strategies"]["ROLLING_24_CALENDAR_MONTHS"][
                "schedule_candidate_fixture_ids"])
        self.assertTrue(any(
            f["strategies"]["EXPANDING"]["schedule_candidate_count"] >
            f["strategies"]["ROLLING_24_CALENDAR_MONTHS"]["schedule_candidate_count"]
            for f in folds[1:]))

    def test_train_candidates_are_older_than_fold_with_3hour_lag(self):
        by_id = {f["fixture_id"]: timestamp(f["kickoff_utc"])
                 for f in self.safe["fixtures"]}
        from datetime import timedelta
        for fold in self.plan["folds"]:
            boundary = timestamp(fold["validation_from_inclusive_utc"])
            for method in self.plan["strategies"]:
                group = fold["strategies"][method]
                left = timestamp(group["history_from_inclusive_utc"])
                for mid in group["schedule_candidate_fixture_ids"]:
                    ko = by_id[mid]
                    self.assertLessEqual(left, ko)
                    self.assertLess(ko + timedelta(hours=3), boundary)

    def test_holdout_never_in_any_fold(self):
        holdout = set(self.safe["test_fixture_ids"])
        validation_seen = []
        for f in self.plan["folds"]:
            valid = set(f["validation_fixture_ids"])
            validation_seen.extend(valid)
            self.assertFalse(valid & holdout)
            for method in self.plan["strategies"]:
                train = set(f["strategies"][method]["schedule_candidate_fixture_ids"])
                self.assertFalse(train & holdout)
                self.assertFalse(train & valid)
        self.assertEqual(len(validation_seen), len(set(validation_seen)))
        self.assertEqual(len(validation_seen), 380)

    def test_zero_eligible_no_train_or_scores(self):
        self.assertFalse(self.report["trained_model"])
        self.assertFalse(self.report["model_scores_generated"])
        self.assertFalse(self.report["test_outcomes_accessed"])
        self.assertEqual(self.report["eligible_training_count"], 0)
        for fold in self.plan["folds"]:
            self.assertEqual(fold["eligible_validation_count"], 0)
            for method in self.plan["strategies"]:
                self.assertEqual(fold["strategies"][method]["eligible_training_count"], 0)

    def test_stable_after_reorder_input(self):
        altered = copy.deepcopy(self.safe)
        altered["fixtures"].reverse()
        altered["projection_sha256"] = sha({
            k:v for k,v in altered.items() if k != "projection_sha256"})
        rebuilt, _ = comparison(altered, expected_sha256=None)
        self.assertEqual(rebuilt["folds"], self.plan["folds"])
        self.assertNotEqual(rebuilt["comparison_sha256"], self.plan["comparison_sha256"])

    def test_source_rehash_cannot_bypass_pinned_safe_view(self):
        changed = copy.deepcopy(self.safe)
        changed["fixtures"][0]["kickoff_utc"] = "2031-01-01T00:00:00Z"
        changed["projection_sha256"] = sha({
            k: v for k, v in changed.items() if k != "projection_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "SOURCE_VERSION_CHANGED"):
            comparison(changed)

    def test_leakage_field_blocked_even_with_pin_disabled(self):
        changed = copy.deepcopy(self.safe)
        changed["fixtures"][0]["label_90m"] = "H"
        changed["projection_sha256"] = sha({
            k: v for k, v in changed.items() if k != "projection_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "TARGET_TAINT"):
            comparison(changed, expected_sha256=None)

    def test_manipulated_role_blocked_even_with_pin_disabled(self):
        changed = copy.deepcopy(self.safe)
        changed["fixtures"][0]["partition"] = "TEST"
        changed["projection_sha256"] = sha({
            k: v for k, v in changed.items() if k != "projection_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "CROSS_BOUNDARY"):
            comparison(changed, expected_sha256=None)

    def test_no_duplicate_ids_even_with_pin_disabled(self):
        changed = copy.deepcopy(self.safe)
        changed["fixtures"][1]["fixture_id"] = changed["fixtures"][0]["fixture_id"]
        changed["projection_sha256"] = sha({
            k: v for k, v in changed.items() if k != "projection_sha256"})
        with self.assertRaisesRegex(SplitSafetyError, "DUPLICATE_MATCH"):
            comparison(changed, expected_sha256=None)

    def test_immutable_sha_and_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "dual-windows.json"
            self.assertEqual(freeze_manifest(self.plan, path), "FROZEN_NEW_VERSION")
            self.assertEqual(freeze_manifest(self.plan, path), "VERIFIED_UNCHANGED")
            wrong = {**self.plan, "mode": "trained"}
            with self.assertRaisesRegex(SplitSafetyError, "IMMUTABLE_SPLIT_VERSION_CONFLICT"):
                freeze_manifest(wrong, path)

    def test_no_labels_or_target_hashes_in_new_plan(self):
        serialized = json.dumps(self.plan, ensure_ascii=False)
        for field in ("label_90m", "source_record_sha256", "result",
                      "score_home", "score_away", "source_records_sha256",
                      "source_payload_sha256", "label_observed_at_utc"):
            self.assertNotIn('"' + field + '"', serialized)


if __name__ == "__main__":
    unittest.main()
