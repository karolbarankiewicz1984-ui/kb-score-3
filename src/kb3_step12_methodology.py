"""Step12 methodology, independently audited against a pinned real manifest.

SAFE_MODEL_VIEW carries fixture identity + kickoff + role only. It deliberately
has no labels, result times, snapshot hashes, status, or target-dependent SHA.
Original evidence manifest MUST remain audit-only, never a model data source.

This is a split-protocol check, NOT a training eligibility certificate.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from src.kb3_split import (
    WINDOWS, WALK_FORWARD, SplitSafetyError, freeze_manifest,
    sha, timestamp, utc, window_for,
)

PINNED_REAL_MANIFEST_SHA256 = (
    "da387303645a9bb9476351044944e5465d178ddff689c96b579093c4fb4fce3a"
)
REAL_DATASET_VERSION = "kb3-pitch-native-pl-2023-2027-v1"
SPLIT_PROTOCOL = "kb3-step12-methodology-v1"
SAFE_KEYS = frozenset(("fixture_id", "kickoff_utc", "partition"))
SPLIT_ROLES = ("TRAIN", "VALIDATION", "TEST")


def method_review(real, *, expected_source_sha256=PINNED_REAL_MANIFEST_SHA256):
    """Fail closed if actual existing source is altered or boundaries shift.

    The source itself is audit-only (contains label-dependent hashes).
    The public projection is schedule-only and does not carry these hashes.
    """
    if not isinstance(real, dict):
        raise SplitSafetyError("STEP12_EXPECTED_MANIFEST_DICTIONARY")
    manifest_sha = real.get("manifest_sha256")
    if manifest_sha != sha({k: v for k, v in real.items()
                           if k != "manifest_sha256"}):
        raise SplitSafetyError("STEP12_REAL_MANIFEST_TAMPER")
    if (expected_source_sha256 is not None and
            manifest_sha != expected_source_sha256):
        raise SplitSafetyError("STEP12_REAL_MANIFEST_VERSION_MISMATCH")
    if real.get("dataset_version") != REAL_DATASET_VERSION:
        raise SplitSafetyError("STEP12_DATASET_VERSION_CHANGED")
    if real.get("training_allowed") is not False or real.get("gate12_pass") is not False:
        raise SplitSafetyError("STEP12_REAL_GATE_POLICY_INVALID")
    windows = [
        {"name": name, "from_utc": lo, "to_exclusive_utc": hi}
        for name, lo, hi in WINDOWS
    ]
    if real.get("partition_windows_closed_open") != windows:
        raise SplitSafetyError("STEP12_UNAPPROVED_BOUNDARIES")
    rows = real.get("rows")
    if not isinstance(rows, list) or len(rows) != 1520:
        raise SplitSafetyError("STEP12_INCOMPLETE_REAL_INDEX")

    ids, safe_rows, counts, quarantines = set(), [], Counter(), 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("fixture_id"), str):
            raise SplitSafetyError("STEP12_INVALID_SOURCE_ROW")
        mid = row["fixture_id"]
        if not mid or mid in ids:
            raise SplitSafetyError("STEP12_DUPLICATE_OR_EMPTY_FIXTURE")
        ids.add(mid)
        kickoff = timestamp(row.get("kickoff_utc"))
        role = window_for(kickoff)
        if role == "OUT_OF_SCOPE" or row.get("partition") != role:
            raise SplitSafetyError("STEP12_CROSS_PARTITION_BOUNDARY")
        if row.get("disposition") != "QUARANTINE":
            raise SplitSafetyError("STEP12_UNEXPECTED_SOURCE_TRAINING_ELIGIBILITY")
        if row.get("evidence_class") not in ("RETROSPECTIVE",
                                             "PROSPECTIVE_OBSERVED_AT"):
            raise SplitSafetyError("STEP12_UNKNOWN_SOURCE_EVIDENCE")
        if row.get("evidence_class") == "PROSPECTIVE_OBSERVED_AT":
            cutoff = timestamp(row.get("feature_cutoff_utc"))
            if cutoff >= kickoff or cutoff > timestamp(real["exported_at_utc"]):
                raise SplitSafetyError("STEP12_FUTURE_SCHEDULE_RECEIPT")
        counts[role] += 1
        quarantines += 1
        safe_rows.append({
            "fixture_id": mid,
            "kickoff_utc": utc(row["kickoff_utc"]),
            "partition": role,
        })
    if dict(counts) != {"TRAIN": 760, "VALIDATION": 380, "TEST": 380}:
        raise SplitSafetyError("STEP12_REAL_PARTITION_TOTALS_WRONG")
    if real.get("quarantined_count") != quarantines or real.get("eligible_counts") != {
            "TRAIN": 0, "VALIDATION": 0, "TEST": 0}:
        raise SplitSafetyError("STEP12_SOURCE_ELIGIBILITY_COUNTS_CHANGED")
    safe_rows.sort(key=lambda x: (x["kickoff_utc"], x["fixture_id"]))
    for left, right in zip(safe_rows, safe_rows[1:]):
        if timestamp(left["kickoff_utc"]) > timestamp(right["kickoff_utc"]):
            raise SplitSafetyError("STEP12_NONCHRONOLOGICAL_ROWS")
    role_by_id = {r["fixture_id"]: r["partition"] for r in safe_rows}
    folds = []
    for number, (start, stop) in enumerate(WALK_FORWARD, 1):
        lo, hi = timestamp(start), timestamp(stop)
        train = [r["fixture_id"] for r in safe_rows
                 if r["partition"] != "TEST" and timestamp(r["kickoff_utc"]) < lo]
        valid = [r["fixture_id"] for r in safe_rows
                 if r["partition"] == "VALIDATION"
                 and lo <= timestamp(r["kickoff_utc"]) < hi]
        if set(train) & set(valid):
            raise SplitSafetyError("STEP12_WALK_FORWARD_OVERLAP")
        if any(role_by_id[ident] == "TEST" for ident in train + valid):
            raise SplitSafetyError("STEP12_TEST_IN_WALK_FORWARD")
        folds.append({
            "fold": number,
            "train_asof_exclusive_utc": start,
            "validation_from_utc": start,
            "validation_to_exclusive_utc": stop,
            "schedule_train_candidate_count": len(train),
            "schedule_validation_count": len(valid),
            "eligible_training_count": 0,
            "eligible_validation_count": 0,
            "train_fixture_ids": train,
            "validation_fixture_ids": valid,
        })
    if sum(x["schedule_validation_count"] for x in folds) != 380:
        raise SplitSafetyError("STEP12_WALK_FORWARD_VALIDATION_COVERAGE")
    projection = {
        "schema": SPLIT_PROTOCOL,
        "dataset_version": real["dataset_version"],
        "purpose": "SCHEDULE_ONLY_NO_TARGETS_NO_TRAINING",
        "information_policy": "OBSERVED_AT_IS_NOT_HISTORICAL_PUBLISH_PROOF",
        "partition_windows_closed_open": windows,
        "partition_counts": dict(sorted(counts.items())),
        "fixtures": safe_rows,
        "walk_forward": folds,
        "test_fixture_ids": [r["fixture_id"] for r in safe_rows
                             if r["partition"] == "TEST"],
        "training_allowed": False,
        "methodology_gate": "READY_FOR_OWNER_REVIEW",
        "train_data_gate": "BLOCKED_MISSING_PREMATCH_FEATURE_EVIDENCE",
    }
    projection["projection_sha256"] = sha(projection)
    audit = {
        "schema": "kb3-step12-independent-real-split-audit-v1",
        "privileged_source_manifest_sha256": manifest_sha,
        "source_has_label_dependent_row_hashes": True,
        "never_supply_privileged_source_to_model": True,
        "candidate_count": len(safe_rows),
        "partition_counts": dict(sorted(counts.items())),
        "walk_forward_fold_candidate_counts": [{
            "fold": x["fold"],
            "schedule_train_candidates": x["schedule_train_candidate_count"],
            "schedule_validation_candidates": x["schedule_validation_count"],
        } for x in folds],
        "validation_fold_total": sum(x["schedule_validation_count"] for x in folds),
        "test_in_train_or_validation_folds": False,
        "all_records_quarantined": True,
        "projection_is_target_free": True,
        "projection_sha256": projection["projection_sha256"],
        "methodology_review": "READY_FOR_OWNER_APPROVAL",
        "gate12_pass": False,
        "training_allowed": False,
        "reason": "Original step12 only requires split/walk-forward boundaries, "
                  "no leakage, immutable version, owner approval before fitting. "
                  "PIT readiness is a separate downstream constraint.",
    }
    return projection, audit


def safe_model_fixtures(projection, *, purpose, role):
    """Consumer fail-closed access: no TEST in tuning; no labels for any role."""
    if projection.get("schema") != SPLIT_PROTOCOL or projection.get("dataset_version") != REAL_DATASET_VERSION:
        raise SplitSafetyError("STEP12_REQUIRES_EXACT_SAFE_SCHEMA")
    if projection.get("projection_sha256") != sha({
            k: v for k, v in projection.items() if k != "projection_sha256"}):
        raise SplitSafetyError("STEP12_SAFE_PROJECTION_TAMPER")
    if any(set(row) != SAFE_KEYS for row in projection.get("fixtures", [])):
        raise SplitSafetyError("STEP12_NO_EXTRA_FIXTURE_FIELDS")
    if projection.get("training_allowed") is not False:
        raise SplitSafetyError("STEP12_TRAINING_GATE_MUST_BE_FALSE")
    if role not in SPLIT_ROLES or purpose not in ("schedule", "tuning", "scoring"):
        raise SplitSafetyError("STEP12_ACCESS_ROLE_INVALID")
    if role == "TEST" and purpose == "tuning":
        raise SplitSafetyError("STEP12_TEST_HOLDOUT_ACCESS_DENIED")
    if purpose == "tuning":
        # Schedule-only projection can NEVER authorize tuning, even when the
        # caller recomputes a modified JSON hash or toggles a policy flag.
        raise SplitSafetyError("STEP12_TUNING_NOT_YET_APPROVED")
    return tuple({k: row[k] for k in SAFE_KEYS} for row in projection["fixtures"]
                 if row["partition"] == role)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--projection", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()
    real = json.loads(Path(args.source).read_text(encoding="utf-8"))
    projection, audit = method_review(real)
    print(freeze_manifest(projection, args.projection))
    print(freeze_manifest(audit, args.audit))
    print("STEP12_SCHEDULE_SAFE", audit["partition_counts"],
          "FOLDS", audit["walk_forward_fold_candidate_counts"])
    print("STEP12_METHODOLOGY_READY_FOR_REVIEW_NOT_TRAINING")


if __name__ == "__main__":
    main()
