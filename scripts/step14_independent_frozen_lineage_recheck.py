"""Independent, read-only consistency recheck of frozen Step14 public PIT lineage.

This does NOT reconstruct original PitchAPI features or certify the 121+38
contract. It verifies the already-persisted 1140 rows against independent
witness JSONs and the frozen summary, without SDK, secrets, target results,
TEST, odds, CatBoost, or historical values. No fixture IDs are emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data/audits"
SUMMARY = AUDIT / "STEP14_1140_EXACT_NATIVE_PUBLIC_SOURCE_PIT_SUMMARY_2026-10-28.json"
ROWS = AUDIT / "STEP14_1140_EXACT_NATIVE_PUBLIC_SOURCE_PIT_PER_MATCH_2026-10-28.jsonl"
WITNESS_2023 = AUDIT / "STEP14_NEW_FOUR_INDEPENDENT_GHARCHIVE_SNAPSHOTS_2023_24_2026-10-28.json"
WITNESS_2024 = AUDIT / "STEP14_NEW_FOUR_FPL_2024_25_GHARCHIVE_PUBLISHED_2026-10-28.json"
SCHEMA = "kb3-step14-independent-frozen-public-lineage-consistency-recheck-v1"
EXPECTED_ROW_KEYS = {
    "fixture_id", "partition", "season", "kickoff_utc",
    "independent_older_source_candidates_checked", "public_result_source_lineage_state",
    "best_old_public_source", "original_PitchAPI_73_nonxg_fields_asof_proven",
    "original_PitchAPI_team_xg_first_published_proven",
    "actual_provider_historic_feature_cutoff_utc",
    "original_121_plus_38_PIT_training_eligible",
}

class AuditFailure(ValueError):
    pass

def require(condition, code):
    if not condition:
        raise AuditFailure(code)

def utc(value):
    require(isinstance(value, str) and value.endswith("Z"), "UTC_TIMESTAMP_REQUIRED")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AuditFailure("INVALID_UTC_TIMESTAMP") from exc
    require(dt.utcoffset().total_seconds() == 0, "UTC_OFFSET_INVALID")
    return dt.astimezone(timezone.utc)

def witnesses(old23, old24):
    require(old23.get("schema") == "kb3-step14-verified-new-4-FPL-2023-historic-clock-evidence-v1",
            "OLD_2023_WITNESS_SCHEMA_CHANGED")
    require(old24.get("schema") == "kb3-step14-2024-25-verified-four-old-FPL-sources-v1",
            "OLD_2024_WITNESS_SCHEMA_CHANGED")
    items = old23.get("verified_sources", []) + old24.get("sources", [])
    require(len(items) == 8, "EXPECTED_EIGHT_OLD_WITNESSES")
    by_commit = {}
    for item in items:
        commit = item.get("commit")
        require(isinstance(commit, str) and len(commit) == 40 and
                all(c in "0123456789abcdef" for c in commit),
                "INVALID_WITNESS_COMMIT")
        require(commit not in by_commit, "DUPLICATE_WITNESS_COMMIT")
        require(item.get("external_publication_evidence_verified") is True,
                "UNVERIFIED_WITNESS")
        require(item.get("provider") == "FPL" and
                item.get("repo") == "vaastav/Fantasy-Premier-League" and
                item.get("path") == f"data/{item.get('season')}/fixtures.csv",
                "WITNESS_SOURCE_IDENTITY_MISMATCH")
        require(isinstance(item.get("sha"), str) and len(item["sha"]) == 64 and
                all(c in "0123456789abcdef" for c in item["sha"]),
                "INVALID_SOURCE_SHA256")
        require(str(item.get("event", "")).isdigit() and int(item["event"]) > 0,
                "INVALID_GHARCHIVE_EVENT")
        utc(item.get("push"))
        by_commit[commit] = item
    return by_commit

def check_row(row, *, source_ids, witness_map):
    require(set(row) == EXPECTED_ROW_KEYS, "ROW_SCHEMA_OR_UNEXPECTED_PRIVATE_FIELD")
    require(isinstance(row["fixture_id"], str) and bool(row["fixture_id"]),
            "MISSING_NATIVE_FIXTURE_ID")
    season = row["season"]
    require(season in ("2023-24", "2024-25", "2025-26"), "UNEXPECTED_SEASON")
    require(row["partition"] == ("VALIDATION" if season == "2025-26" else "TRAIN"),
            "FROZEN_SPLIT_VIOLATION")
    cutoff = utc(row["kickoff_utc"])
    require(row["original_PitchAPI_73_nonxg_fields_asof_proven"] is False and
            row["original_PitchAPI_team_xg_first_published_proven"] is False and
            row["actual_provider_historic_feature_cutoff_utc"] is None and
            row["original_121_plus_38_PIT_training_eligible"] is False,
            "UNSUPPORTED_ORIGINAL_PIT_CLAIM")
    n = row["independent_older_source_candidates_checked"]
    require(type(n) is int and 0 <= n <= 13, "INVALID_CANDIDATE_COUNT")
    source = row["best_old_public_source"]
    if source is None:
        require(row["public_result_source_lineage_state"] ==
                "NO_COMPLETE_SOURCE_BACKED_PRIOR_RESULT_CHAIN",
                "MISSING_SOURCE_BUT_POSITIVE_STATUS")
        return False, False
    require(row["public_result_source_lineage_state"] ==
            "PUBLIC_OLD_RESULTS_ALL_PREDECESSORS_SOURCE_ONLY",
            "POSITIVE_SOURCE_BUT_WRONG_STATUS")
    require(season != "2025-26", "UNSUPPORTED_VALIDATION_PIT")
    require(n > 0 and isinstance(source, dict) and
            set(source) == {"source_commit", "source_published_at_utc",
                            "verified_exact_native_prior_fixture_count",
                            "both_have_five_prior_games",
                            "all_same_season_predecessor_FT_in_old_source"},
            "INVALID_OLD_SOURCE_LINEAGE")
    commit = source["source_commit"]
    require(commit in source_ids, "SOURCE_NOT_IN_FROZEN_13")
    require(utc(source["source_published_at_utc"]) < cutoff,
            "PUBLICATION_NOT_BEFORE_TARGET_KICKOFF")
    require(type(source["verified_exact_native_prior_fixture_count"]) is int and
            source["verified_exact_native_prior_fixture_count"] >= 5,
            "NO_PROVEN_PREVIOUS_FIXTURES")
    require(source["both_have_five_prior_games"] is True and
            source["all_same_season_predecessor_FT_in_old_source"] is True,
            "NOT_COMPLETE_PUBLIC_FORM5_SOURCE")
    witness = witness_map.get(commit)
    if witness is not None:
        require(witness["season"] == season and
                witness["push"] == source["source_published_at_utc"],
                "SOURCE_PUBLICATION_DISAGREES_WITH_EXTERNAL_WITNESS")
    return True, witness is not None

def audit(summary, rows, witness_map):
    require(summary.get("schema") ==
            "kb3-step14-three-season-1140-exact-native-public-PIT-match-lineage-v1",
            "SUMMARY_SCHEMA_CHANGED")
    require(summary.get("frozen_native_safe_SHA") ==
            "3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7",
            "FROZEN_SAFE_HASH_CHANGED")
    require(summary.get("original_exact_native_ID_and_kickoff_joins") == 1140 and
            summary.get("train") == 760 and summary.get("validation") == 380 and
            summary.get("historical_sources_checked") == 13 and
            summary.get("per_target_frozen_source_provenance_records") == 1140,
            "ORIGINAL_SPLIT_OR_SOURCE_COUNTS_CHANGED")
    source_joins = summary.get("old_to_native_source_exact_join_counts")
    require(isinstance(source_joins, dict) and len(source_joins) == 13,
            "MISSING_13_SOURCE_JOINS")
    require(set(witness_map).issubset(source_joins), "EXTERNAL_WITNESS_NOT_IN_SOURCE_JOIN")
    require(len(rows) == 1140, "ROW_COUNT_NOT_1140")
    require(summary.get("original_train_certified_PIT") == 0 and
            summary.get("original_validation_certified_PIT") == 0 and
            summary.get("original_CatBoost_M1_fit_allowed") is False and
            summary.get("gate14_pass") is False and
            summary.get("test_examined") is False and
            summary.get("target_result_scores_accessed") is False and
            summary.get("model_or_split_modified") is False,
            "ORIGINAL_MODEL_OR_TEST_GUARD_VIOLATION")
    require(summary.get("old_FPL_player_xG_not_PitchAPI_team_xG") is True and
            summary.get("public_old_FT_does_not_prove_native_PitchAPI_PIT_or_121_plus_38") is True,
            "PROVIDER_SEMANTICS_GUARD_VIOLATION")

    seen = set()
    seasons, parts, candidate_counts, status_counts = Counter(), Counter(), Counter(), Counter()
    positives_by_season, used_witnesses = Counter(), Counter()
    last_order = None
    for row in rows:
        positive, externally_clocked = check_row(
            row, source_ids=set(source_joins), witness_map=witness_map)
        fid = row["fixture_id"]
        require(fid not in seen, "DUPLICATE_NATIVE_FIXTURE")
        seen.add(fid)
        key = (utc(row["kickoff_utc"]), fid)
        require(last_order is None or last_order < key, "CHRONOLOGICAL_ORDER_VIOLATION")
        last_order = key
        seasons[row["season"]] += 1
        parts[row["partition"]] += 1
        candidate_counts[str(row["independent_older_source_candidates_checked"])] += 1
        status_counts[row["public_result_source_lineage_state"]] += 1
        if positive:
            positives_by_season[row["season"]] += 1
        if externally_clocked:
            used_witnesses[row["best_old_public_source"]["source_commit"]] += 1
    require(dict(seasons) == {"2023-24": 380, "2024-25": 380, "2025-26": 380},
            "SEASON_COUNTS_NOT_380")
    require(dict(parts) == {"TRAIN": 760, "VALIDATION": 380}, "SPLIT_COUNTS_WRONG")
    require(dict(candidate_counts) == summary.get("candidate_source_count_by_target"),
            "CANDIDATE_HISTOGRAM_DISAGREES")
    require(status_counts["PUBLIC_OLD_RESULTS_ALL_PREDECESSORS_SOURCE_ONLY"] == 106 and
            status_counts["NO_COMPLETE_SOURCE_BACKED_PRIOR_RESULT_CHAIN"] == 1034,
            "OLD_PUBLIC_FORM5_COUNTS_WRONG")
    require(dict(positives_by_season) == {"2023-24": 58, "2024-25": 48},
            "SEASON_PUBLIC_FORM5_COUNTS_WRONG")
    require(summary.get("both_teams_form5_source_available") == 106 and
            summary.get("all_prior_FT_in_real_old_public_source_both_teams") == 106 and
            summary.get("best_source_state_counts", {}).get("BOTH_TEAM_5_PRIOR_RESULTS_PUBLIC") == 106,
            "SUMMARY_PUBLIC_FORM5_DISAGREES")
    return {
        "schema": SCHEMA,
        "scope": "READ_ONLY_INDEPENDENT_RECHECK_OF_PERSISTED_PUBLIC_LINEAGE_AND_EIGHT_PRIOR_WITNESS_RECORDS",
        "full_original_pitchapi_pit_proven": False,
        "full_121_features_plus_38_flags_proven": False,
        "original_pitchapi_team_xg_first_publication_proven": False,
        "original_M1_training_allowed": False,
        "gate14": "PENDING",
        "original_train_certified": 0,
        "original_validation_certified": 0,
        "rows_independently_rechecked": len(rows),
        "unique_native_fixture_ids": len(seen),
        "season_counts": dict(sorted(seasons.items())),
        "partition_counts": dict(sorted(parts.items())),
        "public_form5_source_only": 106,
        "public_form5_source_only_by_season": dict(sorted(positives_by_season.items())),
        "old_source_clock_witnesses_crosschecked": len(witness_map),
        "public_form5_rows_using_crosschecked_witnesses": sum(used_witnesses.values()),
        "used_crosschecked_witness_count": len(used_witnesses),
        "consistency_tests": "PASS",
        "limitations": [
            "Witness JSONs are previously collected GHArchive evidence; this pass does not independently redownload GHArchive or old CSV bytes.",
            "Persisted per-target lineage does not contain prior fixture ID chains, so their individual original result/identity proofs cannot be rederived here.",
            "Old FPL/Opta results and player xG do not prove original PitchAPI 73 non-xG or 48 xG features or provider first publication.",
            "No 2025-26 VALIDATION fixture has a complete old public result-source chain in this frozen set.",
        ],
        "test_examined": False,
        "target_result_values_examined": False,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    raw_summary = SUMMARY.read_bytes()
    raw_rows = ROWS.read_bytes()
    old23 = WITNESS_2023.read_bytes()
    old24 = WITNESS_2024.read_bytes()
    summary = json.loads(raw_summary)
    rows = [json.loads(line) for line in raw_rows.splitlines() if line.strip()]
    result = audit(summary, rows, witnesses(json.loads(old23), json.loads(old24)))
    result["input_sha256"] = {
        "frozen_summary": sha256(raw_summary).hexdigest(),
        "frozen_1140_jsonl": sha256(raw_rows).hexdigest(),
        "witness_2023": sha256(old23).hexdigest(),
        "witness_2024": sha256(old24).hexdigest(),
    }
    output = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            require(args.output.read_text(encoding="utf-8") == output,
                    "APPEND_ONLY_INDEPENDENT_REPORT_ALREADY_EXISTS_DIFFERENT")
        else:
            args.output.write_text(output, encoding="utf-8")
    print(json.dumps({
        "state": "FROZEN_1140_PUBLIC_LINEAGE_INDEPENDENT_CONSISTENCY_PASS",
        "rows": result["rows_independently_rechecked"],
        "public_form5_only": result["public_form5_source_only"],
        "original_pitchapi_PIT": False, "gate14": "PENDING"
    }, sort_keys=True))

if __name__ == "__main__":
    main()
