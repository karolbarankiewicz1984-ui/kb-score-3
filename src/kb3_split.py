"""KB Score 3.0 — Step 12: immutable chronological, PIT-safe split manifest.

No API requests, no model fitting and no historical-prematch claims.
Only certified prospective source receipts may enter modeling partitions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


SCHEMA_VERSION = "kb3-step12-split-v0.1"
WINDOWS = (
    ("TRAIN", "2023-07-01T00:00:00Z", "2025-07-01T00:00:00Z"),
    ("VALIDATION", "2025-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    ("TEST", "2026-07-01T00:00:00Z", "2027-07-01T00:00:00Z"),
)
WALK_FORWARD = (
    ("2025-07-01T00:00:00Z", "2025-10-01T00:00:00Z"),
    ("2025-10-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    ("2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z"),
    ("2026-04-01T00:00:00Z", "2026-07-01T00:00:00Z"),
)


class SplitSafetyError(ValueError):
    """Fail closed; never turn invalid time evidence into a training row."""


def timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise SplitSafetyError("MISSING_UTC_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SplitSafetyError("INVALID_TIMESTAMP") from exc
    if parsed.tzinfo is None:
        raise SplitSafetyError("NAIVE_TIMESTAMP")
    return parsed.astimezone(timezone.utc)


def utc(value):
    return timestamp(value).isoformat().replace("+00:00", "Z")


def sha(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def window_for(kickoff):
    for name, start, end in WINDOWS:
        if timestamp(start) <= kickoff < timestamp(end):
            return name
    return "OUT_OF_SCOPE"


def audit_row(raw, exported_at, next_boundaries):
    if not isinstance(raw, dict):
        raise SplitSafetyError("INVALID_ROW")
    mid = raw.get("fixture_id")
    if not isinstance(mid, str) or not mid.strip():
        raise SplitSafetyError("MISSING_FIXTURE_ID")
    kickoff = timestamp(raw.get("kickoff_utc"))
    role = window_for(kickoff)
    evidence = raw.get("evidence_class", "UNKNOWN")
    if evidence not in ("PROSPECTIVE_OBSERVED_AT", "RETROSPECTIVE", "UNKNOWN"):
        raise SplitSafetyError("INVALID_EVIDENCE_CLASS")

    label = raw.get("label_90m")
    if label is not None and label not in ("H", "D", "A"):
        raise SplitSafetyError("INVALID_90M_LABEL")
    label_at = raw.get("label_observed_at_utc")
    if label is not None:
        if not label_at:
            raise SplitSafetyError("LABEL_WITHOUT_OBSERVATION_TIME")
        observed = timestamp(label_at)
        if observed < kickoff:
            raise SplitSafetyError("LABEL_OBSERVED_BEFORE_KICKOFF")
    elif label_at is not None:
        raise SplitSafetyError("LABEL_TIME_WITHOUT_LABEL")

    disposition = "QUARANTINE"
    reason = "OUT_OF_SCOPE" if role == "OUT_OF_SCOPE" else evidence
    normalized_cutoff = None
    if role != "OUT_OF_SCOPE" and evidence == "PROSPECTIVE_OBSERVED_AT":
        cutoff = timestamp(raw.get("feature_cutoff_utc"))
        normalized_cutoff = utc(raw["feature_cutoff_utc"])
        if not cutoff < kickoff:
            raise SplitSafetyError("FEATURE_CUTOFF_AFTER_KICKOFF")
        if cutoff > exported_at:
            raise SplitSafetyError("FEATURE_CUTOFF_AFTER_EXPORT")
        availability = raw.get("feature_availability")
        if not isinstance(availability, dict) or not availability:
            raise SplitSafetyError("MISSING_PER_FEATURE_PROVENANCE")
        for field, meta in availability.items():
            if not isinstance(field, str) or not isinstance(meta, dict):
                raise SplitSafetyError("INVALID_FEATURE_PROVENANCE")
            if "latest_required_observed_at_utc" not in meta:
                raise SplitSafetyError("FEATURE_WITHOUT_RECEIPT")
            receipt = timestamp(meta["latest_required_observed_at_utc"])
            if receipt > cutoff:
                raise SplitSafetyError("FEATURE_OBSERVED_AFTER_CUTOFF")
            if receipt > exported_at:
                raise SplitSafetyError("FEATURE_OBSERVED_AFTER_EXPORT")
            if meta.get("training_allowed") is not True:
                reason = "STEP11_FEATURE_TRAINING_NOT_APPROVED"
                break
        else:
            if label is None:
                reason = "PENDING_LABEL"
            elif observed > exported_at:
                raise SplitSafetyError("LABEL_OBSERVED_AFTER_EXPORT")
            elif role in next_boundaries and observed >= next_boundaries[role]:
                reason = "LABEL_TOO_LATE_FOR_NEXT_PARTITION"
            else:
                disposition = "ELIGIBLE"
                reason = "PIT_CERTIFIED"

    # Fingerprint includes evidence/target but manifest does not publish target labels.
    return {
        "fixture_id": mid, "kickoff_utc": utc(raw["kickoff_utc"]),
        "partition": role, "disposition": disposition, "reason": reason,
        "evidence_class": evidence, "feature_cutoff_utc": normalized_cutoff,
        "source_record_sha256": sha(raw),
        "_label_observed": timestamp(label_at) if label_at else None,
    }


def build_manifest(records, *, exported_at_utc, dataset_version):
    if not isinstance(records, list):
        raise SplitSafetyError("RECORDS_MUST_BE_LIST")
    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise SplitSafetyError("MISSING_DATASET_VERSION")
    exported_at = timestamp(exported_at_utc)
    boundaries = {"TRAIN": timestamp(WINDOWS[1][1]),
                  "VALIDATION": timestamp(WINDOWS[2][1])}
    audited = [audit_row(row, exported_at, boundaries) for row in records]
    names = [item["fixture_id"] for item in audited]
    if len(names) != len(set(names)):
        raise SplitSafetyError("DUPLICATE_FIXTURE_ID")
    audited.sort(key=lambda x: (x["kickoff_utc"], x["fixture_id"]))
    folds = []
    for index, (start, end) in enumerate(WALK_FORWARD, 1):
        lower, upper = timestamp(start), timestamp(end)
        train_ids = [
            r["fixture_id"] for r in audited
            if r["disposition"] == "ELIGIBLE"
            and timestamp(r["kickoff_utc"]) < lower
            and r["_label_observed"] < lower
        ]
        validation_ids = [
            r["fixture_id"] for r in audited
            if r["disposition"] == "ELIGIBLE"
            and lower <= timestamp(r["kickoff_utc"]) < upper
        ]
        if set(train_ids) & set(validation_ids):
            raise SplitSafetyError("WALK_FORWARD_OVERLAP")
        folds.append({
            "fold": index, "train_asof_exclusive_utc": start,
            "validation_from_utc": start, "validation_to_exclusive_utc": end,
            "training_fixture_ids": sorted(train_ids),
            "validation_fixture_ids": sorted(validation_ids),
        })

    counts = Counter((r["partition"], r["disposition"]) for r in audited)
    public_rows = [{key: val for key, val in r.items()
                    if key != "_label_observed"} for r in audited]
    eligible = {role: counts.get((role, "ELIGIBLE"), 0)
                for role in ("TRAIN", "VALIDATION", "TEST")}
    # Training remains blocked until an independent approval and sufficient
    # genuine PIT material in every partition; this script grants no approval.
    manifest = {
        "schema_version": SCHEMA_VERSION, "dataset_version": dataset_version,
        "exported_at_utc": utc(exported_at_utc),
        "partition_windows_closed_open": [
            {"name": name, "from_utc": start, "to_exclusive_utc": end}
            for name, start, end in WINDOWS
        ],
        "source_records_sha256": sha(sorted(records, key=lambda r: str(r.get("fixture_id")))),
        "rows": public_rows, "eligible_counts": eligible,
        "quarantined_count": sum(r["disposition"] != "ELIGIBLE" for r in audited),
        "walk_forward": folds,
        "training_allowed": False, "test_held_out": True,
        "gate12_pass": False,
        "gate12_reason": "PENDING_REAL_PIT_DATA_AND_INDEPENDENT_ACCEPTANCE",
    }
    manifest["manifest_sha256"] = sha(manifest)
    return manifest


def freeze_manifest(manifest, output_path):
    path = Path(output_path)
    output = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != output:
            raise SplitSafetyError("IMMUTABLE_SPLIT_VERSION_CONFLICT")
        return "VERIFIED_UNCHANGED"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(output)
    return "FROZEN_NEW_VERSION"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON: dataset_version, exported_at_utc, records[]")
    parser.add_argument("--output", required=True, help="Immutable manifest destination")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    manifest = build_manifest(
        payload["records"], exported_at_utc=payload["exported_at_utc"],
        dataset_version=payload["dataset_version"])
    print(freeze_manifest(manifest, args.output), manifest["manifest_sha256"])
    print("ELIGIBLE", manifest["eligible_counts"],
          "QUARANTINE", manifest["quarantined_count"],
          "GATE12", "PENDING")


if __name__ == "__main__":
    main()
