"""Read-only V3-R forward eligibility audit on genuine previously frozen M0.

No prediction or provider API. Historical research SQLite is not a trusted
full as-of fixture list; candidate coverage is never forward PIT-certified.
Checks original observed_at for source stats BEFORE the M0 freeze timestamp.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3

from scripts.kb3_p1_historical_eligibility_split import (
    SOURCE_DB, RECHECK_DB, read_only_conn, hash_json, utc,
)
from scripts.kb3_p1_retro_catboost_1007_376 import (
    BASE, WITH_XG, build_features_without_target_label,
)
from src.kb3_p1_shared_asof_features_v2 import LEAGUES
from src.kb3_historical_feature_quality import raw_stat, rolling_window
M0_DB = Path(__file__).resolve().parents[1] / 'data/forward_m0_720_eight/kb3_forward_eight.sqlite'

SCHEMA = "kb3-v3r-forward-readiness-existing-m0-v1"
MIN_LEAD = timedelta(minutes=90)
RESULT_LAG = timedelta(hours=3)
SOURCE_SCOPES = frozenset(LEAGUES)


class V3RReadinessError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise V3RReadinessError(message)


def asof_observations(observed_rows, cutoff):
    """Only immutable provider samples independently observed by cutoff.

    No later event-recheck overlays, no post-match hindsight and no backdated
    provider publication timestamps.
    """
    result = {}
    for item in observed_rows:
        k = (item["scope"], item["match_id"])
        need(k not in result, "DUPLICATE_OBSERVATION")
        if item["scope"] not in SOURCE_SCOPES:
            continue  # UCL research rows are not part of the eight-league V3-R
        if utc(item["observed_at_utc"]) <= utc(cutoff):
            result[k] = {
                "home_team_id": item["home_team_id"],
                "away_team_id": item["away_team_id"],
                "kickoff_utc": item["kickoff_utc"],
                "items": item["items"],
                "xg_status": item["xg_status"],
                "xg_home": item["xg_home"],
                "xg_away": item["xg_away"],
            }
    return result


def audit_target(target, fixture_rows, obs_rows):
    cutoff = utc(target["captured_at_utc"])
    kickoff = utc(target["kickoff_utc"])
    need(target["league"] in SOURCE_SCOPES, "PROTECTED_LEAGUE")
    need(cutoff < kickoff - MIN_LEAD, "M0_FREEZE_TOO_LATE")
    need(target["home_team_id"] != target["away_team_id"],
         "MATCH_SAME_TEAM")
    rows = [r for r in fixture_rows
            if r["scope"] == target["league"] and
            utc(r["kickoff_utc"]) + RESULT_LAG <= cutoff and
            utc(r["listed_at_utc"]) <= cutoff]
    rows.sort(key=lambda x: (x["kickoff_utc"], x["match_id"]))
    history = [{
        "scope": r["scope"], "match_id": r["match_id"],
        "home_team_id": r["home_team_id"],
        "away_team_id": r["away_team_id"],
        "kickoff_utc": r["kickoff_utc"],
        "goals_home_90": r["goals_home_90"],
        "goals_away_90": r["goals_away_90"],
    } for r in rows]
    target_obj = {
        "match_id": target["native_match_id"],
        "kickoff_utc": target["kickoff_utc"],
        "home_team_id": target["home_team_id"],
        "away_team_id": target["away_team_id"],
    }
    seen = asof_observations(obs_rows, target["captured_at_utc"])
    # Explicitly reject an older/later feed record whose native identity
    # no longer agrees with the immutable completed-fixture index.
    for row in history:
        ob = seen.get((row["scope"], row["match_id"]))
        if ob is not None:
            need(all(ob[k] == row[k] for k in (
                "home_team_id","away_team_id","kickoff_utc")),
                "PROVIDER_SOURCE_FIXTURE_IDENTITY_CHANGED")
    # Exactly the same 14/18 feature names and last-five windows as TRAIN.
    # Optional missing values remain NULL/NaN rather than rejecting target.
    features, flags = build_features_without_target_label(
        target_obj, history, seen,
        [utc(r["kickoff_utc"]) for r in history], allow_incomplete=True)
    need(set(features)==set(WITH_XG), "TRAIN_FORWARD_FEATURE_LIST_DRIFT")
    missing = sorted(k for k in WITH_XG if features[k] is None)
    # No synthetic mean is permitted: a partial 3/5 is NULL, not 3/5 used
    # instead of 5/5. Missing stat values are retried in later capture.
    core_ok = all(features[k] is not None for k in BASE)
    xg_ok = all(features[k] is not None for k in WITH_XG)
    need(core_ok == bool(flags["core5"]) and
         xg_ok == (core_ok and bool(flags["xg5"])),
         "READINESS_BUILDER_PARITY_DRIFT")
    if not flags["history5"]:
        # A completely absent last-five result chain is not a fatal pipeline
        # error: fallback to M0, which is already independently frozen.
        status = "M0_FALLBACK_HISTORY_SHORT"
        action = "CONTINUE_M0_AND_RETRY_MISSING_HISTORY"
    elif xg_ok:
        status,action = "CANDIDATE_ALL_18","V3R_RESEARCH_CANDIDATE"
    elif core_ok:
        status,action = "CANDIDATE_14_ONLY","V3R_RESEARCH_WITH_XG_NAN"
    else:
        status,action = "PARTIAL_NAN_OK_RESEARCH","V3R_RESEARCH_WITH_OPTIONAL_NAN"
    return {
        "history5":bool(flags["history5"]),
        "core5":core_ok,"xg5":xg_ok,
        "status":status,"pipeline_action":action,
        "missing_fields":missing,
        "missing_values_are_null_not_zero":True,
        "missing_fields_remain_on_retrieval_queue":bool(missing),
        "source_first_publication_proven":False,
        "not_automatic_prediction_without_complete_catalog":True}


def _load_db_rows(m0_db, source_db):
    with read_only_conn(m0_db) as db:
        need(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
             "M0_DB_INTEGRITY")
        forecasts = [dict(zip(("id","league","native_match_id","kickoff_utc",
                               "captured_at_utc","home_team_id","away_team_id"),r))
                     for r in db.execute("""SELECT id,league,native_match_id,
                     kickoff_utc,captured_at_utc,home_team_id,away_team_id
                     FROM forecasts ORDER BY captured_at_utc,id""")]
    with read_only_conn(source_db) as db:
        need(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
             "HISTORICAL_DB_INTEGRITY")
        fixture = [dict(zip((
            "scope","match_id","kickoff_utc","home_team_id","away_team_id",
            "goals_home_90","goals_away_90","listed_at_utc"),r))
            for r in db.execute("""SELECT scope,match_id,kickoff_utc,
              home_team_id,away_team_id,goals_home_90,goals_away_90,
              listing_observed_at_utc FROM finished_fixture_index""")]
        observations = [dict(zip((
            "scope","match_id","kickoff_utc","home_team_id","away_team_id",
            "observed_at_utc","items","xg_status","xg_home","xg_away"),r))
            for r in db.execute("""SELECT scope,match_id,kickoff_utc,
              home_team_id,away_team_id,source_observed_at_utc,
              stat_items_json,xg_status,xg_home,xg_away FROM observations""")]
        for item in observations:
            item["items"] = json.loads(item["items"])
    return forecasts,fixture,observations


def run(*, m0_db=M0_DB, source_db=SOURCE_DB, now=None, since=None, out=None):
    now = now or datetime.now(timezone.utc)
    need(now.utcoffset()==timedelta(0), "UTC_CLOCK_REQUIRED")
    floor = utc(since) if since else now - timedelta(days=7)
    forecasts,fixtures,observations = _load_db_rows(m0_db,source_db)
    candidates=[x for x in forecasts if utc(x["captured_at_utc"])>=floor
                and utc(x["kickoff_utc"])>now]
    counts = Counter();league = defaultdict(Counter)
    actions = Counter(); missing_fields = Counter()
    for target in candidates:
        state=audit_target(target,fixtures,observations)
        counts[state["status"]]+=1
        actions[state["pipeline_action"]]+=1
        missing_fields.update(state["missing_fields"])
        league[target["league"]][state["status"]]+=1
    result={
        "schema":SCHEMA,
        "mode":"READ_ONLY_EXISTING_GENUINE_M0_FORWARD_RECEIPTS",
        "checked_at_utc":now.isoformat().replace("+00:00","Z"),
        "since_utc":floor.isoformat().replace("+00:00","Z"),
        "total_saved_m0_forecasts":len(forecasts),
        "future_m0_targets_in_window":len(candidates),
        "source_observation_rows_examined":len(observations),
        "source_fixture_rows_examined":len(fixtures),
        "by_status":dict(sorted(counts.items())),
        "nonblocking_pipeline_decisions":dict(sorted(actions.items())),
        "missing_fields_retry_queue":dict(sorted(missing_fields.items())),
        "missing_optional_stats_will_be_retried":True,
        "missing_optional_stats_do_not_stop_research":True,
        "by_league":{k:dict(sorted(v.items())) for k,v in sorted(league.items())},
        "original_asof_provider_publication_proven":False,
        "source_index_is_not_complete_live_fixture_catalog":True,
        "not_eligible_for_auto_forward_scoring_without_fresh_listing_crosscheck":True,
        "no_new_forward_predictions_generated":True,
        "no_provider_api_used":True,
        "existing_M0_unchanged":True,
        "original_gate14_strict":"PENDING",
        "no_automatic_champion_promotion":True,
        "production_approved":False,
        "research_only":True,
    }
    result["report_sha256"]=hash_json(result)
    if out is not None:
        p=Path(out);need(not p.exists(),"NO_OVERWRITE")
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("x",encoding="utf8") as fh:
            json.dump(result,fh,indent=2,sort_keys=True,ensure_ascii=False)
            fh.write("\n")
    print("V3R_FORWARD_READINESS",json.dumps({
        "future_m0_targets_in_window":len(candidates),
        "by_status":result["by_status"],
        "no_forward_predictions_generated":True,
        "report_sha256":result["report_sha256"]},sort_keys=True))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--since",default=None)
    args=p.parse_args()
    run(since=args.since,out=args.out)


if __name__=="__main__":
    main()
