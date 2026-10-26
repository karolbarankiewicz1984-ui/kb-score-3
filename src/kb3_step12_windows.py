"""KB Score 3.0 Step12: compare expanding vs trailing 2-year folds.

A schedule-only comparison, grounded in the pinned target-free 1520 fixture
projection. NEVER trains, scores, joins outcomes, or reads API/keys. Using
historical result hashes as inputs to a model is explicitly forbidden.
"""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path

from src.kb3_split import (
    WINDOWS, WALK_FORWARD, SplitSafetyError, freeze_manifest, sha, timestamp,
    utc, window_for,
)
from src.kb3_step12_methodology import (
    REAL_DATASET_VERSION, SAFE_KEYS, SPLIT_PROTOCOL,
)

SCHEMA = "kb3-step12-dual-window-v1"
SOURCE_VIEW_SHA256 = (
    "3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7"
)
MINIMUM_RESULT_LAG = timedelta(hours=3)
STRATEGIES = ("EXPANDING", "ROLLING_24_CALENDAR_MONTHS")


def comparison(safe_view, *, expected_sha256=SOURCE_VIEW_SHA256):
    """Compute both methods using EXACTLY the same validation fixtures.

    A candidate is only a scheduled match. An actual training fixture must
    independently pass verified target receipt, available-asof feature data,
    quality gates, and owner-approved training policies in later steps.
    """
    if not isinstance(safe_view, dict):
        raise SplitSafetyError("STEP12_DUAL_REQUIRES_SAFE_VIEW")
    signature = safe_view.get("projection_sha256")
    if signature != sha({k: v for k, v in safe_view.items()
                         if k != "projection_sha256"}):
        raise SplitSafetyError("STEP12_DUAL_SAFE_SOURCE_TAMPERED")
    if expected_sha256 is not None and signature != expected_sha256:
        raise SplitSafetyError("STEP12_DUAL_SOURCE_VERSION_CHANGED")
    if (safe_view.get("schema") != SPLIT_PROTOCOL
            or safe_view.get("dataset_version") != REAL_DATASET_VERSION
            or safe_view.get("purpose") != "SCHEDULE_ONLY_NO_TARGETS_NO_TRAINING"
            or safe_view.get("training_allowed") is not False
            or safe_view.get("train_data_gate") != "BLOCKED_MISSING_PREMATCH_FEATURE_EVIDENCE"):
        raise SplitSafetyError("STEP12_DUAL_UNSAFE_SOURCE_POLICY")

    rows = safe_view.get("fixtures")
    if not isinstance(rows, list) or len(rows) != 1520:
        raise SplitSafetyError("STEP12_DUAL_REAL_FIXTURES_REQUIRED")
    expected_windows = [
        {"name": key, "from_utc": start, "to_exclusive_utc": stop}
        for key, start, stop in WINDOWS
    ]
    if safe_view.get("partition_windows_closed_open") != expected_windows:
        raise SplitSafetyError("STEP12_DUAL_PARTITIONS_NOT_FROZEN")
    ids = set()
    fixtures = []
    expected_counts = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0}
    for row in rows:
        if not isinstance(row, dict) or set(row) != SAFE_KEYS:
            raise SplitSafetyError("STEP12_DUAL_TARGET_TAINT_IN_SOURCE")
        mid = row["fixture_id"]
        if not isinstance(mid, str) or not mid or mid in ids:
            raise SplitSafetyError("STEP12_DUAL_DUPLICATE_MATCH")
        ids.add(mid)
        kickoff = timestamp(row["kickoff_utc"])
        if window_for(kickoff) != row["partition"]:
            raise SplitSafetyError("STEP12_DUAL_CROSS_BOUNDARY")
        expected_counts[row["partition"]] += 1
        fixtures.append((kickoff, mid, row["partition"]))
    if expected_counts != {"TRAIN": 760, "VALIDATION": 380, "TEST": 380}:
        raise SplitSafetyError("STEP12_DUAL_COUNTS_MISMATCH")
    if safe_view.get("partition_counts") != expected_counts:
        raise SplitSafetyError("STEP12_DUAL_SOURCE_COUNT_CHANGED")
    fixtures.sort()
    holdout_ids = {mid for _, mid, part in fixtures if part == "TEST"}
    if (set(safe_view.get("test_fixture_ids", [])) != holdout_ids
            or len(safe_view["test_fixture_ids"]) != 380):
        raise SplitSafetyError("STEP12_DUAL_TEST_HOLDOUT_NOT_FROZEN")

    folds = []
    for index, (start, stop) in enumerate(WALK_FORWARD, start=1):
        start_at, end_at = timestamp(start), timestamp(stop)
        # Calendar months, not 730 days: each quarter boundary falls on day 1.
        rolling_from = start_at.replace(year=start_at.year - 2)
        train_expanding_from = timestamp(WINDOWS[0][1])
        validation = [mid for ko, mid, part in fixtures
                      if part == "VALIDATION" and start_at <= ko < end_at]
        expansion = [mid for ko, mid, part in fixtures if
                     part != "TEST" and train_expanding_from <= ko
                     and ko + MINIMUM_RESULT_LAG < start_at]
        rolling = [mid for ko, mid, part in fixtures if
                   part != "TEST" and rolling_from <= ko
                   and ko + MINIMUM_RESULT_LAG < start_at]
        if not set(rolling).issubset(set(expansion)):
            raise SplitSafetyError("STEP12_DUAL_ROLLING_NOT_SUBSET")
        if (holdout_ids.intersection(expansion + rolling + validation)
                or set(expansion).intersection(validation)
                or set(rolling).intersection(validation)):
            raise SplitSafetyError("STEP12_DUAL_TEST_OR_FOLD_LEAKAGE")
        folds.append({
            "fold": index,
            "validation_from_inclusive_utc": start,
            "validation_to_exclusive_utc": stop,
            "validation_fixture_ids": validation,
            "validation_fixture_count": len(validation),
            "strategies": {
                "EXPANDING": {
                    "history_from_inclusive_utc": WINDOWS[0][1],
                    "training_asof_exclusive_utc": start,
                    "schedule_candidate_fixture_ids": expansion,
                    "schedule_candidate_count": len(expansion),
                    "eligible_training_count": 0,
                },
                "ROLLING_24_CALENDAR_MONTHS": {
                    "history_from_inclusive_utc": utc(
                        rolling_from.isoformat()),
                    "training_asof_exclusive_utc": start,
                    "schedule_candidate_fixture_ids": rolling,
                    "schedule_candidate_count": len(rolling),
                    "eligible_training_count": 0,
                },
            },
            "eligible_validation_count": 0,
        })
    all_valid = [id for fold in folds for id in fold["validation_fixture_ids"]]
    if (len(all_valid) != 380 or len(set(all_valid)) != 380
            or set(all_valid) != {mid for _, mid, part in fixtures
                                  if part == "VALIDATION"}):
        raise SplitSafetyError("STEP12_DUAL_VALIDATION_COVERAGE_INVALID")

    plan = {
        "schema": SCHEMA,
        "dataset_version": REAL_DATASET_VERSION,
        "safe_source_view_sha256": signature,
        "historical_training_eligibility": "NOT_CERTIFIED",
        "mode": "SCHEDULE_CANDIDATES_ONLY",
        "strategies": list(STRATEGIES),
        "fixed_partitions": expected_windows,
        "fixed_counts": expected_counts,
        "validation_comparison_rule": "PAIRED_IDENTICAL_FIXTURE_IDS_PER_FOLD",
        "training_candidate_policy": {
            "earliest_source_utc": WINDOWS[0][1],
            "require_kickoff_plus_3h_strictly_before_fold_start": True,
            "require_final_result_observed_before_fold_start_for_training": True,
            "require_feature_observed_at_no_later_than_prematch_cutoff": True,
            "require_actual_feature_and_result_receipts": True,
            "history_length_selection_uses_validation_only": True,
            "untouched_test_predictions_only_after_model_freeze": True,
            "source_provider_published_at_historically_proven": False,
        },
        "planned_metrics_after_data_approval": {
            "primary": "MULTICLASS_LOG_LOSS",
            "secondary": ["MULTICLASS_BRIER_SCORE", "CALIBRATION_ERROR"],
            "comparison": "Same validation fixture IDs; do not score if incomplete or non-PIT."
        },
        "folds": folds,
        "all_validation_candidate_count": len(all_valid),
        "test_reserved_fixture_count": 380,
        "holdout_never_in_fold_training_or_validation": True,
        "training_allowed": False,
        "gate12_pass": False,
        "gate12_status": "AWAITING_FINAL_OWNER_METHODOLOGY_ACCEPTANCE",
    }
    plan["comparison_sha256"] = sha(plan)
    audit = {
        "schema": "kb3-step12-dual-window-independent-real-audit-v1",
        "safe_view_sha256": signature,
        "comparison_sha256": plan["comparison_sha256"],
        "folds": [
            {"fold": f["fold"],
             "validation_count": f["validation_fixture_count"],
             "expanding_history_candidates": f["strategies"]["EXPANDING"]["schedule_candidate_count"],
             "rolling_2y_history_candidates": f["strategies"]["ROLLING_24_CALENDAR_MONTHS"]["schedule_candidate_count"],
             "rolling_is_subset_of_expanding": True,
             "validation_ids_same_for_both": True}
            for f in folds
        ],
        "all_validation_count": 380,
        "train_test_overlap_count": 0,
        "validation_test_overlap_count": 0,
        "eligible_training_count": 0,
        "validity": "SCHEDULE_ONLY_NOT_MODEL_EVALUATION",
        "trained_model": False,
        "model_scores_generated": False,
        "test_outcomes_accessed": False,
        "gate12_pass": False,
        "training_allowed": False,
    }
    return plan, audit


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--safe-view", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.safe_view).read_text(encoding="utf-8"))
    plan, report = comparison(source)
    print(freeze_manifest(plan, args.output))
    print(freeze_manifest(report, args.audit))
    print("STEP12_DUAL_WINDOWS_SCHEDULE_ONLY", json.dumps(
        report["folds"], ensure_ascii=False, sort_keys=True))
    print("GATE12_PENDING_NO_TRAINING")


if __name__ == "__main__":
    main()
