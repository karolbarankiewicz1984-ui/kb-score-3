"""Step12: explain real PIT availability gaps from PINNED original audit only.

It emits aggregates (no match results, target-dependent hashes, player/team
names or private source payloads), independent of a model or training.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from src.kb3_split import SplitSafetyError, freeze_manifest, sha, timestamp
from src.kb3_step12_methodology import PINNED_REAL_MANIFEST_SHA256

SCHEMA = "kb3-step12-real-receipt-gap-audit-v1"


def gap_report(source):
    if not isinstance(source, dict):
        raise SplitSafetyError("STEP12_GAP_SOURCE_MISSING")
    stamp = source.get("manifest_sha256")
    if (stamp != PINNED_REAL_MANIFEST_SHA256
            or stamp != sha({k: v for k, v in source.items()
                             if k != "manifest_sha256"})):
        raise SplitSafetyError("STEP12_GAP_SOURCE_NOT_PINNED")
    if source.get("training_allowed") is not False:
        raise SplitSafetyError("STEP12_GAP_TRAINING_GATE_CHANGED")
    rows = source.get("rows")
    if not isinstance(rows, list) or len(rows) != 1520:
        raise SplitSafetyError("STEP12_GAP_REAL_SOURCE_INCOMPLETE")
    categories, partition_reasons = Counter(), Counter()
    exported = timestamp(source["exported_at_utc"])
    for row in rows:
        group, reason = row["partition"], row["reason"]
        evidence = row["evidence_class"]
        ko = timestamp(row["kickoff_utc"])
        if row["disposition"] != "QUARANTINE":
            raise SplitSafetyError("STEP12_GAP_UNEXPECTED_ELIGIBLE_ROW")
        if evidence == "RETROSPECTIVE":
            if ko >= exported or reason != "RETROSPECTIVE":
                raise SplitSafetyError("STEP12_GAP_FALSE_RETROSPECTIVE")
        elif evidence == "PROSPECTIVE_OBSERVED_AT":
            if (ko <= exported or
                    reason != "STEP11_FEATURE_TRAINING_NOT_APPROVED" or
                    timestamp(row["feature_cutoff_utc"]) >= ko):
                raise SplitSafetyError("STEP12_GAP_FUTURE_NOT_CORRECTLY_BLOCKED")
        else:
            raise SplitSafetyError("STEP12_GAP_UNKNOWN_CLASS")
        categories[reason] += 1
        partition_reasons[group + ":" + reason] += 1
    expected = {
        "RETROSPECTIVE": 1220,
        "STEP11_FEATURE_TRAINING_NOT_APPROVED": 300,
    }
    if dict(categories) != expected:
        raise SplitSafetyError("STEP12_GAP_UNEXPECTED_REAL_REASONS")
    summary = {
        "schema": SCHEMA,
        "source_manifest_sha256": stamp,
        "observation_time_utc": source["exported_at_utc"],
        "real_fixture_count": 1520,
        "retrospective_finished_not_historic_pit": categories["RETROSPECTIVE"],
        "prospective_schedule_only_no_model_features": categories[
            "STEP11_FEATURE_TRAINING_NOT_APPROVED"],
        "reasons": dict(sorted(categories.items())),
        "partition_reasons": dict(sorted(partition_reasons.items())),
        "eligible_training_examples": 0,
        "untouched_test_fixture_count": 380,
        "original_data_changed": False,
        "model_fitted": False,
        "training_allowed": False,
        "next_action": "Certify source receipts and feature observed-at independently before training; do not infer historical pre-match availability from retrospective rows.",
    }
    summary["report_sha256"] = sha(summary)
    return summary


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    data = json.loads(Path(args.source).read_text(encoding="utf8"))
    result = gap_report(data)
    print(freeze_manifest(result, args.out))
    print("STEP12_REAL_ASOF_GAP", json.dumps({
        k: result[k] for k in (
            "retrospective_finished_not_historic_pit",
            "prospective_schedule_only_no_model_features",
            "eligible_training_examples",
            "training_allowed")}, sort_keys=True))


if __name__ == "__main__":
    main()
