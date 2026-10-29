"""Step 14 real 1140 x 159 historical availability matrix and final GATE14 recheck.

READ-ONLY for original data. Never fit M1 on unproven historical records.
A dated independent public source may support FORM5, but cannot certify the
original native PitchAPI feature record or its original as-of timestamp.
No TEST fixture ID, outcome, odds, or validation targets are read.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from src.kb3_step14_bridge import EXPECTED_FEATURES, EXPECTED_MISSING
from src.kb3_step14_real_pit_gate import inspect_real_pit_manifest, RealPITGateError
from src.kb3_split import sha

ROOT = Path(__file__).resolve().parents[1]
SAFE = "data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
REAL = "data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json"
LINEAGE = "data/audits/STEP14_1140_EXACT_NATIVE_PUBLIC_SOURCE_PIT_PER_MATCH_2026-10-28.jsonl"
SUMMARY = "data/audits/STEP14_1140_EXACT_NATIVE_PUBLIC_SOURCE_PIT_SUMMARY_2026-10-28.json"
XG = "data/audits/STEP14_PITCHAPI_ORIGINAL_XG_FIRST_PUBLICATION_AND_SEMANTICS_STATUS_2026-10-28.json"
SCHEMA = "kb3-step14-five-stage-final-real-evidence-159-matrix-and-training-gate-v1"
NO_RECEIPT = "NO_ORIGINAL_NATIVE_PREMATCH_PUBLICATION_AND_CAPTURE_RECEIPT"

class Gate14EvidenceError(ValueError):
    pass

def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _utc(value):
    if not isinstance(value, str):
        raise Gate14EvidenceError("NO_ORIGINAL_TIMESTAMP")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise Gate14EvidenceError("INVALID_TIMESTAMP") from e
    if t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise Gate14EvidenceError("NON_UTC_TIMESTAMP")
    return t

def _xg_feature(k):
    return "xg" in k or "xga" in k

def _source_check(data):
    if data is None:
        return {"state": "NOT_RERUN", "candidate_sources": 0,
                "public_verified_by_season": {}, "native_PitchAPI_first_published_proof": False}
    if (data.get("schema") != "kb3-step14-last-2024-and-validation-2025-fpl-old-sources-v1"
        or data.get("source_candidates") != 5
        or data.get("training_allowed") is not False
        or data.get("gate14_pass") is not False
        or len(data.get("sources", [])) != 5):
        raise Gate14EvidenceError("UNTRUSTED_2025_SOURCE_RECHECK")
    verified = data.get("independently_verified_sources", [])
    if any(not x.get("verified_publication") or not x.get("independent_publication_UTC")
           or not x.get("source_sha256") for x in verified):
        raise Gate14EvidenceError("UNPROVEN_SOURCE_MISCLASSIFIED")
    expected = [x for x in data["sources"] if x.get("verified_publication")]
    if verified != expected:
        raise Gate14EvidenceError("INCONSISTENT_SOURCE_VERIFICATION")
    by_season = Counter(x["season"] for x in verified)
    return {"state": "REAL_ARCHIVE_RECHECK", "candidate_sources": 5,
            "public_verified_by_season": dict(sorted(by_season.items())),
            "native_PitchAPI_first_published_proof": False,
            "public_FPL_does_not_equal_original_PitchAPI_features": True}

def audit(root=ROOT, source_report=None, *, lineage_override=None):
    """Keep every field's evidence state explicit; 0 is not a missing value."""
    base = Path(root)
    safe = _json(base / SAFE)
    original = _json(base / REAL)
    prior = inspect_real_pit_manifest(original, safe)
    ref = _json(base / SUMMARY)
    xg = _json(base / XG)
    if (ref.get("original_exact_native_ID_and_kickoff_joins") != 1140
        or ref.get("frozen_native_safe_SHA") != safe.get("projection_sha256")
        or ref.get("original_train_certified_PIT") != 0
        or ref.get("original_validation_certified_PIT") != 0
        or ref.get("original_CatBoost_M1_fit_allowed") is not False
        or ref.get("both_teams_form5_source_available") != 106):
        raise Gate14EvidenceError("UNVERIFIED_OLD_1140_PROVENANCE")
    if (xg.get("provider") != "PitchAPI"
        or xg.get("provider_first_available_at_UTC_for_specific_original_team_match_xg") is not None
        or xg.get("historical_team_xg_original_provider_version_history_recovered") is not False
        or xg.get("official_M1_training_allowed") is not False):
        raise Gate14EvidenceError("PITCHAPI_XG_STATUS_CHANGED_REQUIRES_FRESH_AUDIT")
    tv = {}
    for s in safe["fixtures"]:
        if s.get("partition") == "TEST":
            continue  # Never inspect holdout fixture identifiers or labels.
        if s.get("partition") not in ("TRAIN", "VALIDATION") or s["fixture_id"] in tv:
            raise Gate14EvidenceError("DUPLICATE_OR_UNKNOWN_TRAIN_FIXTURE")
        tv[s["fixture_id"]] = (s["kickoff_utc"], s["partition"])
    if len(tv) != 1140:
        raise Gate14EvidenceError("MISSING_FROZEN_SAFE_FIXTURES")
    numeric = tuple(sorted(EXPECTED_FEATURES))
    missing = tuple(sorted(EXPECTED_MISSING))
    if (len(numeric) != 121 or len(missing) != 38
        or sum(not _xg_feature(x) for x in numeric) != 73
        or sum(not _xg_feature(x) for x in missing) != 14):
        raise Gate14EvidenceError("ORIGINAL_121_PLUS_38_CONTRACT_CHANGED")
    path = lineage_override if lineage_override is not None else base / LINEAGE
    seen = set()
    rows = []
    partial = Counter()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        fid = item["fixture_id"]
        if fid not in tv or fid in seen:
            raise Gate14EvidenceError("LINEAGE_TARGET_UNKNOWN_OR_DUPLICATE")
        seen.add(fid)
        ko, role = tv[fid]
        if (item.get("partition") != role or item.get("kickoff_utc") != ko
            or item.get("actual_provider_historic_feature_cutoff_utc") is not None
            or item.get("original_121_plus_38_PIT_training_eligible") is not False
            or item.get("original_PitchAPI_73_nonxg_fields_asof_proven") is not False
            or item.get("original_PitchAPI_team_xg_first_published_proven") is not False):
            raise Gate14EvidenceError("UNAUTHORIZED_PREMATCH_EVIDENCE_RELEASE")
        if item.get("public_result_source_lineage_state") == "BOTH_TEAM_5_PRIOR_RESULTS_PUBLIC":
            partial[role] += 1
        # Per-cell record; do not substitute zero for unavailable numeric features.
        rows.append({"fixture_id": fid, "partition": role, "kickoff_utc": ko,
                     "original_feature_cutoff_utc": None,
                     "public_source_lineage_context": item.get("public_result_source_lineage_state"),
                     "field_receipts": {
                       "numeric": {k: NO_RECEIPT for k in numeric},
                       "missing_flags": {k: NO_RECEIPT for k in missing}},
                     "original_no_xg_M1_eligible": False,
                     "original_full_xg_M1_eligible": False})
    if seen != set(tv) or len(rows) != 1140:
        raise Gate14EvidenceError("INCOMPLETE_1140_NATIVE_LINEAGE")
    # The source's 106 FORM5 refer to partial public predecessor evidence,
    # not to the original native 73 non-xG values or their 14 missing flags.
    src = _source_check(source_report)
    if (prior["train_proven_pre_match_eligible"] != 0
        or prior["validation_proven_pre_match_eligible"] != 0
        or prior["real_catboost_train_allowed"] is not False):
        raise Gate14EvidenceError("TRAIN_GATE_CHANGED_REQUIRES_REVIEW")
    rows.sort(key=lambda r: (r["kickoff_utc"], r["fixture_id"]))
    report = {
       "schema": SCHEMA, "original_safe_split_sha256": safe["projection_sha256"],
       "original_real_manifest_sha256": original["manifest_sha256"],
       "source_lineage_1140_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
       "source_partitions": {"TRAIN": 760, "VALIDATION": 380, "TEST_not_inspected": 380},
       "exact_native_match_join_count": 1140,
       "original_step11_numeric_fields": 121, "original_step11_missing_flags": 38,
       "non_xg_fields": 73, "non_xg_flags": 14, "xg_fields": 48, "xg_flags": 24,
       "matrix_rows": len(rows), "matrix_evidence_slots": 1140 * 159,
       "original_field_evidence_slots_proven": 0,
       "public_FORM5_both_teams_partial_prior_evidence": ref["both_teams_form5_source_available"],
       "public_FORM5_is_original_full_native_73_field_proof": False,
       "prior_matched_seasons_2023_24_2024_25_2025_26": [58, 48, 0],
       "source_2025_26_recheck": src,
       "original_PitchAPI_historical_xg_first_available_at": None,
       "original_PitchAPI_team_xg_semantics_equal_FPL_Opta_proven": False,
       "original_full_PIT_train_rows": prior["train_proven_pre_match_eligible"],
       "original_full_PIT_validation_rows": prior["validation_proven_pre_match_eligible"],
       "original_no_xg_train_rows_admitted": 0,
       "variant_NO_XG": {"model_trained": False, "reason": "MISSING_73_NATIVE_PREMATCH_FIELD_RECEIPTS"},
       "variant_WITH_XG": {"model_trained": False, "reason": "MISSING_73_NONXG_AND_48_XG_NATIVE_PREMATCH_FIELD_RECEIPTS"},
       "strict_final_gate_test": "PASS_BLOCKS_UNPROVEN_TRAINING",
       "real_CatBoost_M1_model_exported": False,
       "real_CatBoost_M1_log_loss": None,
       "real_CatBoost_M1_brier_sum3": None,
       "real_CatBoost_M1_TEST_metrics": None,
       "old_research_synthetic_model_not_substituted": True,
       "allow_M1_fit": False, "production_approved": False,
       "original_heldout_TEST_labels_read": False,
       "gate14": "PENDING", "completed_formal_steps": 13,
       "next_mandatory_dependency": "FIRST_PUBLICATION_AND_PER_FEATURE_MATCHED_NATIVE_PIT_RECEIPTS_FOR_TRAIN_AND_VALIDATION",
    }
    return report, rows

def write(report, rows, out, matrix):
    target, grid = Path(out), Path(matrix)
    target.parent.mkdir(parents=True, exist_ok=True)
    grid.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or grid.exists():
        raise Gate14EvidenceError("NO_OVERWRITE_OF_PRIOR_EVIDENCE")
    with gzip.open(grid, "wt", encoding="utf-8", compresslevel=9) as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False)+"\\n")
    # Note: gzip transport compresses the matrix, it does not encrypt it.
    report["matrix_gzip_sha256"] = hashlib.sha256(grid.read_bytes()).hexdigest()
    target.write_text(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2)+"\\n",
                      encoding="utf-8")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default=None)
    p.add_argument("--report", required=True)
    p.add_argument("--matrix", required=True)
    args = p.parse_args()
    source = _json(args.source) if args.source else None
    report, rows = audit(source_report=source)
    write(report, rows, args.report, args.matrix)
    print(json.dumps({
        "state": report["gate14"], "matrix_rows": report["matrix_rows"],
        "matrix_evidence_slots": report["matrix_evidence_slots"],
        "train_certified": report["original_full_PIT_train_rows"],
        "validation_certified": report["original_full_PIT_validation_rows"],
        "source_2025_rechecked": report["source_2025_26_recheck"]["state"],
        "actual_CatBoost_fit": False, "reason": report["next_mandatory_dependency"],
    }, sort_keys=True))

if __name__ == "__main__":
    main()
