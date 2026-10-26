"""KB3 Step12: independent acceptance of frozen split METHOD, not training.

Consumes only the target-free schedule and dual-window comparison; no access
to historical outcomes, provider credentials, trained models or market odds.
"""
from __future__ import annotations
import json
from datetime import timedelta
from pathlib import Path
from src.kb3_split import SplitSafetyError, sha, timestamp, freeze_manifest
from src.kb3_step12_windows import comparison, SOURCE_VIEW_SHA256

DUAL_PLAN_SHA256 = "25242ed4a626aba2669ea86605b31664cb17bf10a6a74e4e3548470954c81198"
SCHEMA = "kb3-step12-methodology-acceptance-v1"


def accept_methodology(safe_view, dual_plan):
    if not isinstance(safe_view, dict) or not isinstance(dual_plan, dict):
        raise SplitSafetyError("STEP12_ACCEPTANCE_INPUT_MISSING")
    if safe_view.get("projection_sha256") != SOURCE_VIEW_SHA256:
        raise SplitSafetyError("STEP12_ACCEPTANCE_VIEW_VERSION_CHANGED")
    if dual_plan.get("comparison_sha256") != DUAL_PLAN_SHA256:
        raise SplitSafetyError("STEP12_ACCEPTANCE_DUAL_VERSION_CHANGED")
    if dual_plan.get("comparison_sha256") != sha({
            key: value for key, value in dual_plan.items()
            if key != "comparison_sha256"}):
        raise SplitSafetyError("STEP12_ACCEPTANCE_DUAL_CONTENT_CHANGED")
    recalculated, _ = comparison(safe_view)
    if recalculated != dual_plan:
        raise SplitSafetyError("STEP12_ACCEPTANCE_UNREPRODUCIBLE_SPLIT")
    if dual_plan["fixed_counts"] != {
            "TRAIN": 760, "VALIDATION": 380, "TEST": 380}:
        raise SplitSafetyError("STEP12_ACCEPTANCE_WRONG_PARTITION_COUNTS")
    if dual_plan.get("training_allowed") is not False or dual_plan.get("gate12_pass") is not False:
        raise SplitSafetyError("STEP12_ACCEPTANCE_CHANGED_FROZEN_PREAPPROVAL")
    if len(dual_plan["folds"]) != 4:
        raise SplitSafetyError("STEP12_ACCEPTANCE_MISSING_WALK_FORWARD_FOLDS")
    test_ids = set(safe_view["test_fixture_ids"])
    by_id = {row["fixture_id"]: timestamp(row["kickoff_utc"])
             for row in safe_view["fixtures"]}
    fold_summary = []
    validated = set()
    for fold in dual_plan["folds"]:
        boundary = timestamp(fold["validation_from_inclusive_utc"])
        valid = set(fold["validation_fixture_ids"])
        if (not valid or valid & test_ids or validated & valid or
                len(valid) != fold["validation_fixture_count"]):
            raise SplitSafetyError("STEP12_ACCEPTANCE_VALIDATION_OVERLAP")
        validated |= valid
        history = {}
        for key in ("EXPANDING", "ROLLING_24_CALENDAR_MONTHS"):
            batch = fold["strategies"][key]
            ids = batch["schedule_candidate_fixture_ids"]
            if len(ids) != len(set(ids)) or len(ids) != batch["schedule_candidate_count"]:
                raise SplitSafetyError("STEP12_ACCEPTANCE_TRAIN_DUPLICATE")
            if valid.intersection(ids) or test_ids.intersection(ids):
                raise SplitSafetyError("STEP12_ACCEPTANCE_TEST_OR_VALIDATION_LEAK")
            earliest = timestamp(batch["history_from_inclusive_utc"])
            if any(by_id[i] < earliest or by_id[i] + timedelta(hours=3) >= boundary
                   for i in ids):
                raise SplitSafetyError("STEP12_ACCEPTANCE_NO_LOOKAHEAD_VIOLATION")
            if batch["eligible_training_count"] != 0:
                raise SplitSafetyError("STEP12_ACCEPTANCE_FAKE_ELIGIBILITY")
            history[key] = set(ids)
        if not history["ROLLING_24_CALENDAR_MONTHS"].issubset(history["EXPANDING"]):
            raise SplitSafetyError("STEP12_ACCEPTANCE_ROLLING_NOT_NESTED")
        if fold["eligible_validation_count"] != 0:
            raise SplitSafetyError("STEP12_ACCEPTANCE_FAKE_VALIDATION_ELIGIBILITY")
        fold_summary.append({
            "fold": fold["fold"],
            "expanding_schedule_candidates": len(history["EXPANDING"]),
            "rolling_two_year_schedule_candidates": len(history["ROLLING_24_CALENDAR_MONTHS"]),
            "shared_validation_fixtures": len(valid),
            "test_overlap": 0,
            "training_eligible": 0,
        })
    if len(validated) != 380:
        raise SplitSafetyError("STEP12_ACCEPTANCE_VALIDATION_COVERAGE")
    if (dual_plan["all_validation_candidate_count"] != 380
            or dual_plan["test_reserved_fixture_count"] != 380
            or not dual_plan["holdout_never_in_fold_training_or_validation"]):
        raise SplitSafetyError("STEP12_ACCEPTANCE_TEST_RESERVATION_FAILED")
    return {
        "schema": SCHEMA,
        "project": "KB Score 3.0",
        "acceptance_date": "2026-10-26",
        "original_split_method": "TRAIN 2023-2025, VALIDATION 2025-2026, TEST 2026-2027",
        "method_variant_selected": [
            "EXPANDING_FULL_AVAILABLE_HISTORY",
            "ROLLING_LAST_24_CALENDAR_MONTHS",
        ],
        "paired_validation": True,
        "primary_metric_when_scoring_permitted": "MULTICLASS_LOG_LOSS",
        "secondary_metrics_when_scoring_permitted": [
            "MULTICLASS_BRIER", "CALIBRATION",
        ],
        "safe_schedule_source_sha256": SOURCE_VIEW_SHA256,
        "frozen_dual_window_plan_sha256": DUAL_PLAN_SHA256,
        "folds": fold_summary,
        "partition_counts": {"TRAIN": 760, "VALIDATION": 380, "TEST": 380},
        "validation_fixture_coverage": 380,
        "heldout_test_fixtures": 380,
        "methodology_test_result": "PASS",
        "owner_direction": "User agreed to proceed with the two-method proposal in chat; no model training was requested",
        "methodology_gate": "PASS_SPLIT_PROTOCOL_ONLY",
        "step12_gate_pass": True,
        "completed_steps": 12,
        "total_steps": 29,
        "training_allowed": False,
        "real_historical_pit_verified": False,
        "validation_predictions_created": False,
        "test_labels_accessed": False,
        "next_step13_training_blocked_until": [
            "VERIFIED_PREMATCH_FEATURE_PROVENANCE",
            "VERIFIED_RESULT_AVAILABILITY_ASOF_FOLD",
            "INDEPENDENT_DATA_QUALITY_APPROVAL",
        ],
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--safe-view", required=True)
    p.add_argument("--dual-plan", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    safe = json.loads(Path(a.safe_view).read_text(encoding="utf8"))
    dual = json.loads(Path(a.dual_plan).read_text(encoding="utf8"))
    decision = accept_methodology(safe, dual)
    decision["record_sha256"] = sha(decision)
    print(freeze_manifest(decision, a.out))
    print("STEP12_METHOD_GATE_PASS_TRAINING_STILL_BLOCKED",
          json.dumps({k: decision[k] for k in
                      ("step12_gate_pass", "training_allowed", "completed_steps",
                       "validation_fixture_coverage", "heldout_test_fixtures")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
