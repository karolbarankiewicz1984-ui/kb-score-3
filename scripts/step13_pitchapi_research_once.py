"""KB Score 3.0 / existing Step13: ONE bounded live PitchAPI reread for research.

Results are historical as retrieved TODAY, not PIT snapshots for past fixtures.
No bookmaker odds, xG, API-Football, private RSA key, real results in artifacts,
individual scores in logs, or TEST labels read. This script is invoked by one
purpose-scoped GitHub Actions workflow only. No scheduler or continuous API loop.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain
from src.kb3_pitch_native import check_season
from src.kb3_split import sha, freeze_manifest, timestamp
from src.kb3_step13_retrospective import POLICY, retrospective_research

LEAGUE = "l_4WFCIZ"
SEASONS=("2023/2024","2024/2025","2025/2026")
EXPECTED_COUNT=1140
SCHEMA="kb3-step13-live-reread-research-v0.5"
SAFE_PATH="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"


def extract_research_rows(seasons, *, safe_view):
    """Fails closed on changed native IDs, changed kickoff, or TEST source.

    This function receives data ONLY for the 3 completed seasons; never a
    provider query for 2026/27, even if today's results are available.
    """
    if set(seasons)!=set(SEASONS):
        raise ValueError("STEP13_RESEARCH_WRONG_SEASON_SET")
    fixtures=safe_view.get("fixtures")
    if not isinstance(fixtures,list) or len(fixtures)!=1520:
        raise ValueError("STEP13_RESEARCH_SAFE_SPLIT_NOT_1520")
    safe={f["fixture_id"]:f for f in fixtures}
    if len(safe)!=1520:
        raise ValueError("STEP13_RESEARCH_SAFE_IDS_DUPLICATED")
    allowed={k:v for k,v in safe.items() if v.get("partition") in ("TRAIN","VALIDATION")}
    if Counter(v["partition"] for v in allowed.values()) != {"TRAIN":760,"VALIDATION":380}:
        raise ValueError("STEP13_RESEARCH_SPLIT_COUNTS_NOT_FROZEN")
    if safe_view.get("training_allowed") is not False or len(allowed)!=EXPECTED_COUNT:
        raise ValueError("STEP13_RESEARCH_SPLIT_ALREADY_PROMOTED")
    team_ids_prev=None
    records=[]
    hashes={}
    seen=set()
    for year in SEASONS:
        payload=seasons[year]
        if not isinstance(payload,dict) or not isinstance(payload.get("matches"),list):
            raise ValueError("STEP13_RESEARCH_PROVIDER_BODY_INVALID")
        matches=payload["matches"]
        checked=check_season(matches,year,expected_count=380,require_upcoming=False)
        if checked["status_counts"]!={"finished":380}:
            raise ValueError("STEP13_RESEARCH_NOT_380_COMPLETED_MATCHES")
        team_ids={t["id"] for m in matches for t in (m["home_team"],m["away_team"])}
        if len(team_ids)!=20 or team_ids_prev is not None and len(team_ids_prev & team_ids)<14:
            raise ValueError("STEP13_RESEARCH_UNSTABLE_NATIVE_TEAM_IDS")
        team_ids_prev=team_ids
        hashes[year]=checked["match_digest_sha256"]
        for m in matches:
            mid=m["id"]
            if mid in seen:
                raise ValueError("STEP13_RESEARCH_REPEAT_MATCH_ID")
            seen.add(mid)
            historical=allowed.get(mid)
            # Keep original frozen kickoff and fixture identity exactly.
            if historical is None or timestamp(m["time_utc"])!=timestamp(historical["kickoff_utc"]):
                raise ValueError("STEP13_RESEARCH_NATIVE_MATCH_OR_KICKOFF_DRIFT")
            gh,ga=m.get("score_home"),m.get("score_away")
            if type(gh) is not int or type(ga) is not int or not (0<=gh<=30 and 0<=ga<=30):
                raise ValueError("STEP13_RESEARCH_GOALS_INVALID")
            records.append({
                "fixture_id":mid,"home_team_id":m["home_team"]["id"],
                "away_team_id":m["away_team"]["id"],
                "kickoff_utc":historical["kickoff_utc"],
                "goals_home_90":gh,"goals_away_90":ga,
            })
    if seen!=set(allowed):
        raise ValueError("STEP13_RESEARCH_MISSING_OR_SURPLUS_HISTORICAL_IDS")
    if len(records)!=EXPECTED_COUNT:
        raise ValueError("STEP13_RESEARCH_UNEXPECTED_TOTAL")
    return records,hashes


def assemble(seasons, *, safe_view, observed_at):
    if safe_view.get("schema")!="kb3-step12-methodology-v1":
        # This is a safety-critical contract: change only with review.
        raise ValueError("STEP13_RESEARCH_SAFE_VIEW_SCHEMA_CHANGED")
    records,season_hashes=extract_research_rows(seasons,safe_view=safe_view)
    study=retrospective_research(records,policy=POLICY)
    if (study["train_partition_rows"]!=760 or
        study["validation_partition_rows"]!=380 or
        study["test_rows_processed"]!=0 or
        [f["validation_count"] for f in study["folds"]] != [60,126,123,71]):
        raise ValueError("STEP13_RESEARCH_UNEXPECTED_FOLDS")
    report={**study,
       "schema":SCHEMA,
       "provider":"PitchAPI",
       "provider_native_league_id":LEAGUE,
       "seasons_historical":list(SEASONS),
       "provider_requests_exactly":3,
       "provider_read_at_utc":observed_at,
       "source_category":"REAL_PROVIDER_RETRIEVED_NOW_RETROSPECTIVE_EVENTTIME_ONLY",
       "season_native_match_digests":season_hashes,
       "frozen_safe_view_sha256":safe_view["projection_sha256"],
       "test_partition_data_requested":False,
       "source_scores_in_report":False,
       "historical_original_provider_pubtime_certified":False,
       "offline_synthetic_reference_only":False,
       "real_match_outcomes_used_for_research":True,
       "historical_pit_backtest_performed":False,
       "model_production_eligible":False,
       "training_allowed":False,
       "gate13_pass":False,
       "owner_private_rsa_key_used":False,
    }
    report["report_sha256"]=sha({k:v for k,v in report.items() if k!="report_sha256"})
    return report


def one_time_live(*,safe_path):
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:
        raise ValueError("STEP13_PITCHAPI_SECRET_MISSING")
    safe=json.loads(Path(safe_path).read_text(encoding="utf8"))
    if (safe.get("training_allowed") is not False or
        len(safe.get("fixtures",[]))!=1520 or
        Counter(f["partition"] for f in safe["fixtures"]) !=
        {"TRAIN":760,"VALIDATION":380,"TEST":380}):
        raise ValueError("STEP13_RESEARCH_SAFE_VIEW_GATE_CHANGED")
    from pitchapi import PitchAPI
    client=PitchAPI(api_key=key)
    payloads={}
    # EXACTLY THREE calls to free historical listings; no status=all.
    # If an error occurs, no partial report is produced.
    for year in SEASONS:
        payloads[year]=to_plain(client.leagues.matches(LEAGUE,season=year,status="played"))
    when=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    return assemble(payloads,safe_view=safe,observed_at=when)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    try:
        report=one_time_live(safe_path=SAFE_PATH)
        print(freeze_manifest(report,args.output))
        print("KB3_STEP13_REAL_RETROSPECTIVE_RESEARCH_DONE_NOT_PIT",
              "VALIDATION",report["validation_partition_rows"],
              "TEST",report["test_rows_processed"],
              "GATE13",report["gate13_pass"],
              "SHA",report["report_sha256"])
        for method,stats in report["overall"].items():
            print("KB3_STEP13_AGGREGATE_ONLY",method,
                "n",stats["validation_n"],
                "logloss",round(stats["multiclass_logloss_fold_weighted"],6),
                "brier",round(stats["multiclass_brier_sum3_fold_weighted"],6),
                "ece",round(stats["top_class_ece_5bin_fold_weighted"],6))
    except Exception as exc:
        # Log only the exception *type*; neither key nor provider payload.
        print("KB3_STEP13_REAL_RESEARCH_BLOCKED",type(exc).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
