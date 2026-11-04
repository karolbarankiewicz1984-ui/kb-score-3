"""P1-01 research dataset inventory + chronological split, NEVER formal TRAIN.

Read-only real historic PitchAPI SQLite input, no provider API / model fit.
Actual original provider first-publication and target prematch host receipts
are absent from this history collection. It is NOT PIT-certified training.
Output manifests carry only research selection, not scores or fitted vectors.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3
from pathlib import Path

from src.kb3_historical_feature_quality import _load_records, rolling_window
from src.kb3_p1_shared_asof_features_v2 import (
    SCHEMA as CONTRACT, LEAGUES, MIN_LEAD, RESULT_MIN_LAG,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "data/research/historical_multistat/observations.sqlite"
RECHECK_DB = ROOT / "data/research/historical_multistat/issue_rechecks.sqlite"
REPORT_SCHEMA = "kb3-p1-historical-eligibility-research-v1"
ALLOWED_SCOPES = frozenset(LEAGUES | {"UCL"})
SELECTED_HISTORICAL_SEASONS = frozenset(
    ("2023/2024", "2024/2025", "2025/2026"))
CUT_BEFORE_KICKOFF = timedelta(hours=2)  # HYPOTHETICAL: not actual historic receipt!
EMBARGO = timedelta(days=7)
TRAIN_FRACTION = 0.7


class EligibilityError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise EligibilityError(reason)


def utc(value):
    need(isinstance(value, str) and value.endswith("Z"), "STRICT_UTC_Z_REQUIRED")
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EligibilityError("INVALID_UTC") from exc
    need(out.utcoffset() == timedelta(0), "NON_UTC_CLOCK")
    return out


def stamp(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def hash_json(data):
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_only_conn(db_path):
    db_path = Path(db_path)
    need(db_path.is_file(), "SOURCE_SQLITE_NOT_FOUND")
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    db.execute("PRAGMA query_only = ON")
    return db


def chronological_split(cohort, *, fraction=TRAIN_FRACTION,
                        embargo=EMBARGO):
    """Global chronological split: entire fixture group on one side of boundary.

    No same-day tied kickoff across sets; 7-day time embargo after last TRAIN.
    Labels and original protected TEST season never used in the selection.
    """
    need(isinstance(cohort, list), "INVALID_COHORT_LIST")
    need(0 < fraction < 1 and embargo >= timedelta(days=1),
         "SPLIT_POLICY_INVALID")
    ordered = sorted(cohort, key=lambda x: (x["kickoff_utc"],
                                            x["league"], x["fixture_id"]))
    if len(ordered) < 3:
        return [], [], ordered, {
            "status": "INSUFFICIENT_RESEARCH_COHORT",
            "boundary_utc": None, "embargo_days": embargo.days}
    cutoff_index = max(1, min(len(ordered)-1, int(len(ordered)*fraction)))
    boundary = utc(ordered[cutoff_index]["kickoff_utc"])
    # All fixtures at a boundary instant go to the same (later) side.
    train = [x for x in ordered if utc(x["kickoff_utc"]) < boundary]
    left = utc(train[-1]["kickoff_utc"]) if train else None
    threshold = left + embargo if left is not None else boundary
    validate = [x for x in ordered if utc(x["kickoff_utc"]) >=
                max(boundary, threshold)]
    trids = {(x["league"], x["fixture_id"]) for x in train}
    vaids = {(x["league"], x["fixture_id"]) for x in validate}
    need(not trids.intersection(vaids), "TRAIN_VALIDATION_FIXTURE_LEAK")
    need(all(x["season"] in SELECTED_HISTORICAL_SEASONS
             for x in train+validate), "CURRENT_OR_PROTECTED_SEASON_LEAK")
    if train and validate:
        need(utc(train[-1]["kickoff_utc"]) + embargo <=
             utc(validate[0]["kickoff_utc"]), "SPLIT_EMBARGO_VIOLATION")
    removed = [x for x in ordered if (x["league"],x["fixture_id"]) not in
               trids | vaids]
    return train, validate, removed, {
        "status": "RESEARCH_SPLIT_ONLY_NOT_FIT",
        "boundary_utc": stamp(boundary),
        "first_validation_utc": validate[0]["kickoff_utc"] if validate else None,
        "last_train_utc": train[-1]["kickoff_utc"] if train else None,
        "embargo_days": embargo.days,
        "train_fraction_intent": fraction,
        "chronological_no_overlap": True}


def _manifest(rows, partition):
    """Research-only selectors; no target labels or alleged v2 PIT vectors."""
    return [
        {"row_schema": "kb3-research-asof-cohort-selector-v1",
         "partition": partition,
         "league": x["league"],
         "fixture_id": x["fixture_id"],
         "season": x["season"],
         "kickoff_utc": x["kickoff_utc"],
         "assumed_not_original_cutoff_utc": x["proxy_cutoff_utc"],
         "complete_last5_history": x["history5"],
         "complete_core5": x["core5"],
         "complete_xg5": x["xg5"],
         "historical_original_pit_certified": False,
         "source_class": "HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
         "train_approved": False,
         "official_fit_eligible": False,
         "candidate_contract": CONTRACT}
        for x in rows]


def assess(db_path, recheck_path=None):
    """Return evidence gate and disjoint research-only TRAIN/VALIDATION manifests.

    Historic match postmatch source receipt cannot be turned into earlier
    prematch features. Real v2 training requires a separate source snapshot
    captured before each target; this DB has none.
    """
    db_path = Path(db_path)
    original_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
    with read_only_conn(db_path) as db:
        need(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
             "ORIGINAL_SQLITE_INTEGRITY_FAILURE")
        tables = {x[0] for x in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        need({"finished_fixture_index", "observations",
              "rolling_feature_cache"} <= tables,
             "HISTORICAL_TABLE_MISSING")

        fixt, obs, recheck, bins = _load_records(
            db, recheck_db_path=recheck_path)
        need(set(fixt) <= ALLOWED_SCOPES and "ENG" not in fixt,
             "PROTECTED_PREMIER_LEAGUE_TEST_INCLUDED")
        index = {(f["scope"], f["match_id"]): f
                 for group in fixt.values() for f in group}
        need(len(index) == sum(len(x) for x in fixt.values()),
             "INDEX_UNIQUE_DRIFT")
        need(set(obs) <= set(index), "OBSERVED_WITHOUT_FINISHED_TARGET")

        listing = {(row[0],row[1]): (row[2],row[3])
                   for row in db.execute(
            "SELECT scope,match_id,listing_observed_at_utc,"
            "original_provider_first_published_utc FROM finished_fixture_index")}
        observed_clock = {(row[0],row[1]): (row[2],row[3],row[4],row[5])
                          for row in db.execute(
             "SELECT scope,match_id,source_observed_at_utc,"
             "provider_first_published_at_utc,research_only,xg_status "
             "FROM observations")}
        cached = {(row[0],row[1]): json.loads(row[2])
                  for row in db.execute(
             "SELECT scope,target_match_id,feature_json "
             "FROM rolling_feature_cache")}
        need(set(obs) == set(cached), "ROLLING_CACHE_TARGET_INVENTORY_DRIFT")
        need(all(not v["original_pit_certified"] and
                 not v["training_approved"] and
                 v["availability_class"] ==
                 "HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT"
                 for v in cached.values()),
             "RETROSPECTIVE_CACHE_FALSELY_CERTIFIED")
        need(all(x[2] == 1 for x in observed_clock.values()),
             "SOURCE_HISTORY_FLAG_CHANGED")
        need(all(x[1] is None for x in observed_clock.values()),
             "HISTORICAL_PROVIDER_FIRST_PUBLISHED_CHANGED")
        need(all(x[1] is None for x in listing.values()),
             "HISTORICAL_LISTING_FIRST_PUBLISHED_CHANGED")

        by_league = defaultdict(Counter)
        by_season = defaultdict(Counter)
        cohort = []
        all_observations = Counter()
        fixture_ko = {
            scope: [utc(f["kickoff_utc"]) for f in group]
            for scope, group in fixt.items()}
        for scope in fixture_ko:
            need(fixture_ko[scope] == sorted(fixture_ko[scope]),
                 "HISTORICAL_FIXTURE_INDEX_NOT_CHRONOLOGICAL")
        for key, observation in obs.items():
            scope, match_id = key
            target = index[key]
            season = target["season"]
            need(observation["kickoff_utc"] == target["kickoff_utc"] and
                 observation["home_team_id"] == target["home_team_id"] and
                 observation["away_team_id"] == target["away_team_id"],
                 "ORIGINAL_TARGET_IDENTITY_MISMATCH")
            ko = utc(target["kickoff_utc"])
            cutoff = ko - CUT_BEFORE_KICKOFF
            need(cutoff <= ko - MIN_LEAD, "CUTOFF_90MIN_POLICY_DRIFT")
            observed = utc(observed_clock[key][0])
            listing_observed = utc(listing[key][0])
            dst = by_league[scope]
            all_observations["observed_targets"] += 1
            dst["observed_targets"] += 1
            by_season[season]["observed_targets"] += 1
            if observed <= cutoff:
                dst["postmatch_stat_observed_before_target_cutoff"] += 1
                all_observations["postmatch_stat_observed_before_target_cutoff"] += 1
            if listing_observed <= cutoff:
                dst["fixture_listing_observed_before_target_cutoff"] += 1
                all_observations["fixture_listing_observed_before_target_cutoff"] += 1
            if scope == "UCL":
                dst["excluded_isolated_ucl"] += 1
                continue
            need(scope in LEAGUES, "UNEXPECTED_LEAGUE")
            if season not in SELECTED_HISTORICAL_SEASONS:
                dst["excluded_current_or_other_season"] += 1
                continue

            # Research-only chronological proxy: predecessor RESULT earliest
            # selectable at predecessor kickoff +3h <= target (kickoff -2h).
            mature = cutoff - RESULT_MIN_LAG
            prefix = fixt[scope][:bisect_right(fixture_ko[scope], mature)]
            need(all(utc(r["kickoff_utc"]) + RESULT_MIN_LAG <= cutoff
                     and r["match_id"] != match_id for r in prefix),
                 "TARGET_OR_POSTCUTOFF_LEAK")
            h = rolling_window(prefix, obs, target["home_team_id"], 5)
            a = rolling_window(prefix, obs, target["away_team_id"], 5)
            history5 = h["history_complete"] and a["history_complete"]
            core5 = h["core_stats_complete"] and a["core_stats_complete"]
            xg5 = h["xg_complete"] and a["xg_complete"]
            need(not core5 or history5, "CORE5_WITHOUT_HISTORY5")
            need(not xg5 or history5, "XG5_WITHOUT_HISTORY5")
            need(cached[key]["original_pit_certified"] is False,
                 "FALSE_RESEARCH_PIT")
            dst["historical_cohort_targets"] += 1
            if history5:
                dst["research_history5_complete"] += 1
            if core5:
                dst["research_core5_complete"] += 1
            if xg5:
                dst["research_xg5_complete"] += 1
            if history5:
                cohort.append({
                    "league": scope, "fixture_id": match_id,
                    "season": season,
                    "kickoff_utc": target["kickoff_utc"],
                    "proxy_cutoff_utc": stamp(cutoff),
                    "history5": history5, "core5": core5, "xg5": xg5,
                })

    need(hashlib.sha256(db_path.read_bytes()).hexdigest() == original_hash,
         "HISTORICAL_DB_CHANGED_DURING_READ")
    train, validation, embargoed, split = chronological_split(cohort)
    need(all(x["league"] in LEAGUES for x in train+validation),
         "PROTECTED_SCOPE_IN_RESEARCH_SPLIT")
    need(all(x["season"] in SELECTED_HISTORICAL_SEASONS
             for x in train+validation), "CURRENT_SEASON_IN_TRAIN_SPLIT")
    need(not any("score" in x or "outcome" in x or "label" in x
                 for x in train+validation), "TARGET_OUTCOME_LEAK")

    def breakdown(rows):
        return dict(sorted(Counter(x["league"] for x in rows).items()))

    research = {
        "research_only": True,
        "historical_source_sha256": original_hash,
        "observed_historical_match_stats": all_observations["observed_targets"],
        "national_league_observations":
            sum(v["observed_targets"] for k,v in by_league.items() if k in LEAGUES),
        "excluded_ucl": by_league["UCL"]["observed_targets"],
        "potential_historical_no_xg_history5": len(cohort),
        "optional_core5_subset": sum(x["core5"] for x in cohort),
        "optional_xg5_subset": sum(x["xg5"] for x in cohort),
        "chronological_train_rows": len(train),
        "chronological_validation_rows": len(validation),
        "embargo_discarded": len(embargoed),
        "split": split,
        "train_by_league": breakdown(train),
        "validation_by_league": breakdown(validation),
        "by_scope": {k:dict(v) for k,v in sorted(by_league.items())},
        "by_season": {k:dict(v) for k,v in sorted(by_season.items())},
        "recheck_overlay": dict(recheck),
        "historical_v2_feature_vector_exported": False,
        "historical_reconstruction_only": True,
    }
    report = {
        "schema": REPORT_SCHEMA,
        "contract_reference": CONTRACT,
        "source_type": "PITCHAPI_NATIVE_MATCH_FINISHED_HISTORICAL_MULTISTAT",
        "cutoff_policy": "HYPOTHETICAL_KICKOFF_MINUS_2H_RESEARCH_ONLY",
        "source_first_published_proven": False,
        "independent_historical_target_prematch_host_receipt_available":
            False,
        "official_v2_training_eligible": 0,
        "official_v2_validation_eligible": 0,
        "official_v2_training_gate": "BLOCKED_MISSING_ORIGINAL_PREMATCH_RECEIPTS",
        "official_fit_samples_added": 0,
        "formal_catboost_85_retraining_authorized": False,
        "existing_m0_fit_74_not_part_of_this_historical_dataset": True,
        "original_m0_unchanged": True,
        "model_weights_changed": False,
        "gate16": "PENDING", "gate17": "PENDING",
        "source_timing_checks": dict(all_observations),
        "research_reconstruction": research,
    }
    report["report_sha256"] = hash_json(report)
    return report, _manifest(train, "RESEARCH_TRAIN"), _manifest(
        validation, "RESEARCH_VALIDATION")


def write_report(report, train, validation, outdir):
    """Write separate RESEARCH manifests; never a formally trainable dataset."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    def save(filename, obj):
        file = outdir / filename
        with file.open("x", encoding="utf-8") as f:
            json.dump(obj,f,indent=2,ensure_ascii=False,sort_keys=True)
            f.write("\n")
    save("HISTORICAL_V2_ELIGIBILITY_READINESS.json",report)
    save("RECONSTRUCTED_RESEARCH_TRAIN_SELECTORS.json",train)
    save("RECONSTRUCTED_RESEARCH_VALIDATION_SELECTORS.json",validation)
    save("FORMAL_V2_TRAIN_VALIDATION_NO_ELIGIBLE_ROWS.json", {
        "schema": "kb3-formal-v2-empty-gate-v1",
        "contract": CONTRACT,
        "train": [],
        "validation": [],
        "reason": "NO_INDEPENDENT_CERTIFIED_PREMATCH_HISTORICAL_SOURCES",
        "fit_allowed": False, "model_training_performed": False,
    })
    return str(outdir)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=SOURCE_DB)
    p.add_argument("--recheck",type=Path,default=RECHECK_DB)
    p.add_argument("--outdir",type=Path)
    args = p.parse_args()
    report, train, val = assess(args.db, args.recheck)
    if args.outdir is not None:
        write_report(report,train,val,args.outdir)
    summary = {k: report[k] for k in (
        "schema","official_v2_training_eligible",
        "official_v2_validation_eligible",
        "official_v2_training_gate","report_sha256",
        "source_timing_checks")}
    summary["research_counts"] = {
        k:v for k,v in report["research_reconstruction"].items()
        if k in ("observed_historical_match_stats",
                 "national_league_observations",
                 "excluded_ucl","potential_historical_no_xg_history5",
                 "optional_core5_subset","optional_xg5_subset",
                 "chronological_train_rows","chronological_validation_rows",
                 "embargo_discarded","split","train_by_league",
                 "validation_by_league")}
    print(json.dumps(summary,sort_keys=True,ensure_ascii=False))


if __name__ == "__main__":
    main()
