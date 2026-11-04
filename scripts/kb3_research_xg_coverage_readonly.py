"""Independent read-only aggregate audit of actual historical xG/forma reports.

Does not repair conflicting xG, declare old publication dates, access API,
or modify derived caches. It makes complete-window losses explicit by league.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / ("data/pit_sidecar/historical_multistat/2026-11-04/"
                  "run-41882339782-1-summary/ROLLING_AFTER_RECHECK.json")
CAPTURE = ROOT / ("data/pit_sidecar/historical_multistat/2026-11-04/"
                  "run-41882339782-1-summary/ACCELERATED_CAPTURE_REPORT.json")
ALLOWED = frozenset(("ESP","ITA","GER","FRA","NED","BEL","TUR","POL","UCL"))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def analyze(summary, capture):
    totals = summary["totals"]
    by_scope = summary["by_scope"]
    require(set(by_scope) <= ALLOWED and "ENG" not in by_scope,
            "PROTECTED_OR_UNKNOWN_SOURCE")
    require(summary["quality"] == "REAL_SOURCE_COUNTS_RETROSPECTIVE_RESEARCH_ONLY",
            "HISTORICAL_SOURCE_LABEL_CHANGED")
    require(summary["retrospective_provider_original_publication_proven"] is False,
            "MUST_NOT_CERTIFY_OLD_PROVIDER_PUBLICATION")
    require(summary["full_feature_training_approved"] is False and
            summary["protected_test_touched"] is False, "PROTECTED_TRAIN_OR_TEST")
    require(capture["original_m0_unchanged"] is True and
            capture["provider_original_pit_certified"] is False and
            capture["protected_english_test_untouched"] is True,
            "CAPTURE_SOURCE_SAFETY_CHANGED")
    require(capture["cumulative_match_stats"] == totals["total_observed_stats_matches"] ==
            totals["targets_checked"], "CAPTURE_ROLLING_TARGET_COUNT_MISMATCH")
    require(capture["effective_xg_verified"] == totals["xg_verified_matches"],
            "VERIFIED_XG_MISMATCH")
    require(totals["xg_verified_matches"] + totals["xg_unverified_matches"] ==
            totals["total_observed_stats_matches"], "XG_STATUS_TOTAL_DRIFT")
    require(totals["indexed_finished_fixtures"] -
            totals["total_observed_stats_matches"] ==
            totals["missing_stat_match_count"], "FIXTURE_COVERAGE_DRIFT")
    require(sum(x.get("targets_checked",0) for x in by_scope.values()) ==
            totals["targets_checked"], "SCOPE_COUNTS_DO_NOT_ADD_UP")
    for n in (5,10,15):
        for kind in ("history","core","stats","xg"):
            prefix = f"pair_{kind}_{n}_"
            complete, incomplete = (totals.get(prefix+s,0)
                                    for s in ("complete","incomplete"))
            require(complete+incomplete==totals["targets_checked"],
                    "GLOBAL_ROLLING_PARTITION_DRIFT")
            require(sum(x.get(prefix+"complete",0) for x in by_scope.values()) ==
                    complete, "LEAGUE_ROLLING_COMPLETE_DRIFT")
    require(capture["effective_xg5_pair_complete"] ==
            totals["pair_xg_5_complete"], "CAPTURE_XG5_MISMATCH")
    require(capture["effective_xg10_pair_complete"] ==
            totals["pair_xg_10_complete"], "CAPTURE_XG10_MISMATCH")
    require(capture["effective_xg15_pair_complete"] ==
            totals["pair_xg_15_complete"], "CAPTURE_XG15_MISMATCH")
    xg_reason = summary.get("xg_unverified_reason_counts", {})
    require(sum(xg_reason.values()) == totals["xg_unverified_matches"],
            "XG_DISAGREEMENT_REASON_DRIFT")
    leagues = {}
    for scope, group in sorted(by_scope.items()):
        n = group.get("targets_checked",0)
        window = {str(k): {
            "history_complete": group.get(f"pair_history_{k}_complete",0),
            "core_complete": group.get(f"pair_core_{k}_complete",0),
            "xg_complete": group.get(f"pair_xg_{k}_complete",0),
            "xg_missing": group.get(f"pair_xg_{k}_incomplete",0),
        } for k in (5,10,15)}
        leagues[scope] = {
            "targets": n,
            "verified_xg_matches": group.get("xg_verified_matches",0),
            "xg_conflict_matches": group.get("xg_unverified_matches",0),
            "xg5_pair_coverage": (
                round(window["5"]["xg_complete"]/n,6) if n else 0.0),
            "complete_history_without_complete_xg5":
                window["5"]["history_complete"]-window["5"]["xg_complete"],
            "windows": window,
            "inter_competition_team_mapping_certified": False if scope=="UCL" else None,
        }
        require(leagues[scope]["complete_history_without_complete_xg5"] >= 0,
                "XG5_OUTNUMBERS_TRUE_HISTORY")
    report = {
        "schema": "kb3-research-xg-coverage-readonly-v1",
        "source_class": "HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
        "targets": totals["targets_checked"],
        "observed_stats": totals["total_observed_stats_matches"],
        "native_xg_verified": totals["xg_verified_matches"],
        "native_xg_unverified": totals["xg_unverified_matches"],
        "indexed_finished_fixtures": totals["indexed_finished_fixtures"],
        "xg_conflict_reasons": xg_reason,
        "complete_both_teams_windows": {
            "core5": totals["pair_core_5_complete"],
            "xg5": totals["pair_xg_5_complete"],
            "xg10": totals["pair_xg_10_complete"],
            "xg15": totals["pair_xg_15_complete"],
        },
        "by_scope": leagues,
        "new_history_stats_in_capture": capture["new_match_stats"],
        "new_native_xg_verified_in_capture": capture["new_verified_xg"],
        "research_only": True, "historic_original_pit_certified": False,
        "formal_training_allowed": False, "M0_changed": False,
        "gate16": "PENDING", "gate17": "PENDING",
    }
    report["report_sha256"] = hashlib.sha256(
        json.dumps(report,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--rolling", type=Path, default=SUMMARY)
    p.add_argument("--capture", type=Path, default=CAPTURE)
    args=p.parse_args()
    report=analyze(json.loads(args.rolling.read_text()),
                   json.loads(args.capture.read_text()))
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
