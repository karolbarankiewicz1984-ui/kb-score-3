"""KB Score 3.0 Step14: independent read-only eligibility audit on REAL frozen manifests.

This is a *blocking* dataset gate, not retrospective model training.
Read only fixture_id/kickoff/partition/cutoff/evidence for TRAIN+VALIDATION.
Do not inspect per-match target, score, bookmaker odds, or TEST row content.
The real source manifest has label-dependent row hashes: NEVER export it to M1.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from datetime import datetime, timezone
from src.kb3_split import sha, window_for


class RealPITGateError(ValueError):
    pass


REAL_PATH = "data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json"
SAFE_PATH = "data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
REAL_SHA = "da387303645a9bb9476351044944e5465d178ddff689c96b579093c4fb4fce3a"
SAFE_SHA = "3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7"


def _utc(value):
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError) as exc:
        raise RealPITGateError("INVALID_UTC") from exc
    if d.tzinfo is None:
        raise RealPITGateError("NO_UTC_OFFSET")
    return d.astimezone(timezone.utc)


def _signature(record, field, pinned):
    if type(record) is not dict or record.get(field) != pinned:
        raise RealPITGateError("SOURCE_PIN_MISMATCH")
    if sha({k: v for k, v in record.items() if k != field}) != pinned:
        raise RealPITGateError("SOURCE_TAMPERED")
    return pinned


def inspect_real_pit_manifest(real, safe):
    """Only audit the historical TRAIN and VALIDATION partitions.

    Neither accepted metadata nor old historical timestamps certify first
    publication by the provider. Fail closed if any declared eligibility or
    other evidence is changed without a new independently audited version.
    """
    _signature(real, "manifest_sha256", REAL_SHA)
    _signature(safe, "projection_sha256", SAFE_SHA)
    if (real.get("schema_version") != "kb3-step12-split-v0.1" or
        real.get("dataset_version") != "kb3-pitch-native-pl-2023-2027-v1" or
        real.get("training_allowed") is not False or
        real.get("eligible_counts") != {"TRAIN": 0, "VALIDATION": 0, "TEST": 0} or
        real.get("quarantined_count") != 1520 or
        len(real.get("rows", [])) != 1520):
        raise RealPITGateError("REAL_SOURCE_QUARANTINE_INCONSISTENT")
    if (safe.get("schema") != "kb3-step12-methodology-v1" or
        safe.get("purpose") != "SCHEDULE_ONLY_NO_TARGETS_NO_TRAINING" or
        safe.get("training_allowed") is not False or
        safe.get("train_data_gate") != "BLOCKED_MISSING_PREMATCH_FEATURE_EVIDENCE" or
        safe.get("partition_counts") != {"TRAIN": 760, "VALIDATION": 380, "TEST": 380} or
        len(safe.get("fixtures", [])) != 1520):
        raise RealPITGateError("SAFE_SOURCE_INCONSISTENT")

    # The SAFE source contains no label or label-dependent per-match checksum.
    allowed_safe_keys = {"fixture_id", "kickoff_utc", "partition"}
    safe_tv = {}
    for row in safe["fixtures"]:
        if not isinstance(row, dict) or set(row) != allowed_safe_keys:
            raise RealPITGateError("UNSAFE_MODEL_VIEW")
        if row["partition"] not in ("TRAIN", "VALIDATION"):
            # Deliberately do not inspect even the fixture ID of holdout TEST.
            continue
        fid = row["fixture_id"]
        if not isinstance(fid, str) or not fid or fid in safe_tv:
            raise RealPITGateError("DUPLICATE_SCHEDULE_ID")
        ko = _utc(row["kickoff_utc"])
        if window_for(ko) != row["partition"]:
            raise RealPITGateError("SPLIT_CHRONOLOGY_ERROR")
        safe_tv[fid] = (ko, row["partition"])
    if len(safe_tv) != 1140:
        raise RealPITGateError("SAFE_TRAIN_VALIDATION_INCOMPLETE")

    counts = Counter()
    missing_cutoff = Counter()
    candidates = Counter()
    seen = set()
    for row in real["rows"]:
        if not isinstance(row, dict):
            raise RealPITGateError("INVALID_SOURCE_ROW")
        role = row.get("partition")
        if role not in ("TRAIN", "VALIDATION"):
            # Reject unknown roles; TEST content is strictly ignored.
            if role != "TEST":
                raise RealPITGateError("UNKNOWN_PARTITION")
            continue
        # Never examine source_record_sha256: it may be result-dependent.
        if set(row) != {"disposition", "evidence_class", "feature_cutoff_utc",
                        "fixture_id", "kickoff_utc", "partition", "reason",
                        "source_record_sha256"}:
            raise RealPITGateError("SOURCE_ROW_SHAPE_CHANGED")
        fid = row["fixture_id"]
        if fid in seen or fid not in safe_tv:
            raise RealPITGateError("SOURCE_IDENTITY_MISMATCH")
        seen.add(fid)
        kickoff, expected = safe_tv[fid]
        if expected != role or _utc(row["kickoff_utc"]) != kickoff:
            raise RealPITGateError("SOURCE_KICKOFF_MISMATCH")
        counts[role] += 1
        if (row["disposition"] != "QUARANTINE" or
            row["evidence_class"] != "RETROSPECTIVE" or
            row["reason"] != "RETROSPECTIVE"):
            raise RealPITGateError("PREMATURE_QUARANTINE_RELEASE")
        if row["feature_cutoff_utc"] is None:
            missing_cutoff[role] += 1
        else:
            # Even a valid-looking timestamp would require per-feature,
            # source-backed, genuinely historical PIT receipts.
            cutoff = _utc(row["feature_cutoff_utc"])
            if cutoff >= kickoff:
                raise RealPITGateError("POST_KICKOFF_CUTOFF")
            candidates[role] += 1
    if counts != {"TRAIN": 760, "VALIDATION": 380} or len(seen) != 1140:
        raise RealPITGateError("INCOMPLETE_REAL_TRAIN_VALIDATION")
    if missing_cutoff != counts or candidates:
        raise RealPITGateError("HISTORICAL_CUTOFF_EVIDENCE_NOT_PROVEN")

    folds = safe.get("walk_forward", [])
    if len(folds) != 4 or [x.get("schedule_validation_count") for x in folds] != [60,126,123,71]:
        raise RealPITGateError("CHANGED_VALIDATION_FOLDS")
    if any(x.get("eligible_training_count") != 0 or
           x.get("eligible_validation_count") != 0 for x in folds):
        raise RealPITGateError("FOLD_TRAINING_RELEASE_UNAUTHORIZED")

    return {
        "schema": "kb3-step14-real-source-pit-eligibility-audit-v1",
        "source_snapshot_as_of_utc": real.get("exported_at_utc"),
        "source_real_manifest_sha256": REAL_SHA,
        "source_safe_projection_sha256": SAFE_SHA,
        "train_row_count": counts["TRAIN"],
        "validation_row_count": counts["VALIDATION"],
        "test_rows_examined": 0,
        "train_missing_feature_cutoff_count": missing_cutoff["TRAIN"],
        "validation_missing_feature_cutoff_count": missing_cutoff["VALIDATION"],
        "train_proven_pre_match_eligible": 0,
        "validation_proven_pre_match_eligible": 0,
        "historic_provider_publication_proof_available": False,
        "no_lookahead_source_index_check": "PASS_SCHEDULE_IDENTITY_ONLY",
        "no_lookahead_actual_model_assessment": "NOT_PERFORMED",
        "real_catboost_model_fitted": False,
        "real_catboost_train_allowed": False,
        "real_validation_metrics_available": False,
        "test_targets_read": 0,
        "production_approved": False,
        "gate14_pass": False,
        "reason": "HISTORICAL_SOURCES_RETROSPECTIVE_NO_PREMATCH_CUTOFF_RECEIPTS",
    }


def check_real_fit_admission(real, safe):
    result = inspect_real_pit_manifest(real, safe)
    if not result["real_catboost_train_allowed"]:
        raise RealPITGateError("REAL_M1_FIT_DENIED_NO_CERTIFIED_PREMATCH_TRAIN")
    raise RealPITGateError("UNIMPLEMENTED_FUTURE_SEPARATE_INDEPENDENT_APPROVAL_REQUIRED")


def inspect_repo(root=None):
    base = Path(root or Path(__file__).resolve().parents[1])
    real = json.loads((base / REAL_PATH).read_text(encoding="utf8"))
    safe = json.loads((base / SAFE_PATH).read_text(encoding="utf8"))
    return inspect_real_pit_manifest(real, safe)


if __name__ == "__main__":
    print(json.dumps(inspect_repo(), sort_keys=True, ensure_ascii=False, indent=2))
