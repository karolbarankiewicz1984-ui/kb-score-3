"""KB3 Step14: offline eligibility preflight on THREE SIGNED AGGREGATE AUDITS ONLY.

This module never opens the raw schedules, historical fixtures, TEST labels,
PitchAPI secrets, forecast snapshots, or the CatBoost training entrypoint.
The legacy PIT gap audit is dated 2026-10-26; it is *not* today's live status.
No JSON field, even if set to True, can grant model-training permission here.
"""
from __future__ import annotations

import json
from pathlib import Path
from src.kb3_split import sha


class Step14ReadinessError(ValueError):
    pass


RECORDS = (
    ("data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json", "record_sha256",
     "0332edf73cd893f9848ffb23ea7821a09f5c183e6add77fc7cfdd7378959c5be"),
    ("data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json", "report_sha256",
     "2b9502d09bf40d4fc4b2bd8a09283e4ea56e055a36f5744e9b1ed2f1acb32998"),
    ("data/audits/STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json", "report_sha256",
     "a4d26dc96bf75bf2073007e66c4445f61adcaed22611f5fa21c31d74a36e4718"),
)


def _verify(record, idx):
    path, field, expected = RECORDS[idx]
    if type(record) is not dict or record.get(field) != expected:
        raise Step14ReadinessError("PINNED_REPORT_CHANGED")
    if sha({k: v for k, v in record.items() if k != field}) != expected:
        raise Step14ReadinessError("REPORT_SHA_INTEGRITY_FAILURE")
    return path


def inspect_original_training_gate(step12, pit_gap, step13):
    """Check old signed evidence, explicitly *not* certified prematch PIT."""
    source_files = [_verify(record, idx) for idx, record in enumerate(
        (step12, pit_gap, step13))]
    if (step12.get("schema") != "kb3-step12-methodology-acceptance-v1" or
        step12.get("step12_gate_pass") is not True or
        step12.get("methodology_gate") != "PASS_SPLIT_PROTOCOL_ONLY" or
        step12.get("partition_counts") != {"TRAIN": 760, "VALIDATION": 380, "TEST": 380} or
        step12.get("real_historical_pit_verified") is not False or
        step12.get("training_allowed") is not False or
        step12.get("test_labels_accessed") is not False):
        raise Step14ReadinessError("STEP12_DATA_RELEASE_NOT_AUTHORIZED")
    if (pit_gap.get("schema") != "kb3-step12-real-receipt-gap-audit-v1" or
        pit_gap.get("eligible_training_examples") != 0 or
        pit_gap.get("real_fixture_count") != 1520 or
        pit_gap.get("retrospective_finished_not_historic_pit") != 1220 or
        pit_gap.get("prospective_schedule_only_no_model_features") != 300 or
        pit_gap.get("untouched_test_fixture_count") != 380 or
        pit_gap.get("training_allowed") is not False or
        pit_gap.get("model_fitted") is not False):
        raise Step14ReadinessError("STEP12_PIT_GAP_NOT_RESOLVED")
    if (step13.get("schema") != "kb3-step13-original-baseline-scope-acceptance-v1" or
        step13.get("step13_original_scope_accepted") is not True or
        step13.get("train_rows") != 760 or
        step13.get("retrospective_validation_rows") != 380 or
        step13.get("forward_prematch_predictions_frozen") != 20 or
        step13.get("forward_test_results_read") != 0 or
        step13.get("historical_test_rows_read") != 0 or
        step13.get("historical_provider_prematch_pit_certified") is not False or
        step13.get("global_production_eligibility_granted") is not False or
        step13.get("original_unverified_source_promoted_to_training") is not False or
        step13.get("training_allowed") is not False):
        raise Step14ReadinessError("STEP13_SCOPE_IS_NOT_REAL_TRAINING_GATE")
    return {
        "schema": "kb3-step14-signed-aggregate-readiness-v1",
        "source_paths": source_files,
        "source_hashes": [r[2] for r in RECORDS],
        "historic_gap_observation_date": "2026-10-26",
        "historic_gap_is_current_certification": False,
        "step13_original_scope_pass": True,
        "step12_split_methodology_pass": True,
        "fixture_ids_read": 0,
        "actual_raw_result_labels_read": 0,
        "new_sports_api_calls": 0,
        "eligibility_in_old_pit_gap_audit": 0,
        "historic_provider_prematch_pit_proven": False,
        "real_catboost_fit_eligible": False,
        "catboost_production_approved": False,
        "gate14_pass": False,
        "status": "PENDING_DATA_PIT_EVIDENCE_AND_ACTUAL_MODEL_ACCEPTANCE",
    }


def inspect_repo_aggregate_only(repository_root):
    root = Path(repository_root)
    reports = []
    for path, _, _ in RECORDS:
        reports.append(json.loads((root / path).read_text(encoding="utf8")))
    return inspect_original_training_gate(*reports)


if __name__ == "__main__":
    report = inspect_repo_aggregate_only(Path(__file__).resolve().parents[1])
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
