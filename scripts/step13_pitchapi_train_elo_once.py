"""One-off two-season TRAIN-only PitchAPI diagnostic. Never reads 2025/26 or TEST.

Provider scores never written to repo or log. Aggregate-only research report.
"""
import argparse
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
from src.kb3_split import timestamp,sha,freeze_manifest
from src.kb3_pitch_native import check_season
from src.kb3_step13_train_elo_sensitivity import diagnose
from scripts.pitchapi_step06_audit import to_plain

SEASONS=("2023/2024","2024/2025")
LEAGUE="l_4WFCIZ"
SAFE="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"


def extract(payload,safe):
    if set(payload)!=set(SEASONS):
        raise ValueError("STEP13_WRONG_SEASON_SET_OR_VALIDATION_READ")
    fixed={f["fixture_id"]:f for f in safe["fixtures"] if f["partition"]=="TRAIN"}
    if len(fixed)!=760 or safe.get("training_allowed") is not False:
        raise ValueError("STEP13_TRAIN_SOURCE_INVALID")
    rows=[];seen=set();digests={};teams_prev=None
    for season in SEASONS:
        data=payload[season]
        if not isinstance(data,dict) or not isinstance(data.get("matches"),list):
            raise ValueError("STEP13_TRAIN_PROVIDER_SHAPE_INVALID")
        matches=data["matches"]
        audit=check_season(matches,season,expected_count=380)
        if audit["status_counts"]!={"finished":380}:
            raise ValueError("STEP13_TRAIN_NOT_ALL_FINISHED")
        current_teams={t["id"] for m in matches for t in (m["home_team"],m["away_team"])}
        if len(current_teams)!=20 or (teams_prev is not None and len(current_teams & teams_prev)<14):
            raise ValueError("STEP13_TRAIN_TEAM_ID_CONTINUITY_INVALID")
        teams_prev=current_teams
        digests[season]=audit["match_digest_sha256"]
        for m in matches:
            mid=m["id"];reference=fixed.get(mid)
            if mid in seen or not reference or timestamp(m["time_utc"])!=timestamp(reference["kickoff_utc"]):
                raise ValueError("STEP13_TRAIN_MISMATCHED_ID_OR_KICKOFF")
            seen.add(mid)
            rows.append({
                "fixture_id":mid,"home_team_id":m["home_team"]["id"],
                "away_team_id":m["away_team"]["id"],
                "kickoff_utc":reference["kickoff_utc"],
                "goals_home_90":m["score_home"],
                "goals_away_90":m["score_away"],
            })
    if seen!=set(fixed) or len(rows)!=760:
        raise ValueError("STEP13_TRAIN_MISSING_OR_SURPLUS_ID")
    return rows,digests


def live_once():
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:
        raise ValueError("STEP13_PROVIDER_SECRET_MISSING")
    safe=json.loads(Path(SAFE).read_text(encoding="utf-8"))
    if (safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380}
            or safe.get("training_allowed") is not False):
        raise ValueError("STEP13_TRAIN_SPLIT_COUNTS_CHANGED")
    from pitchapi import PitchAPI
    api=PitchAPI(api_key=key)
    payload={}
    for season in SEASONS:
        payload[season]=to_plain(api.leagues.matches(LEAGUE,season=season,status="played"))
    observed=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    rows,digests=extract(payload,safe)
    out=diagnose(rows,safe,observed)
    out["provider"]="PitchAPI"
    out["provider_calls"]=2
    out["native_match_digests"]=digests
    out["match_scores_exported"]=False
    out["api_key_or_rsa_exported"]=False
    out["report_sha256"]=sha({k:v for k,v in out.items() if k!="report_sha256"})
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    try:
        result=live_once()
        print(freeze_manifest(result,args.output))
        print("STEP13_TRAIN_ONLY_ELO_SENSITIVITY_RESEARCH_PASS_NOT_PIT",
              "TRAIN",result["train_rows"],
              "VALIDATION",result["validation_rows_read"],
              "TEST",result["test_rows_read"],
              "ORIGINAL",result["original_grid_best_train_elasticity"],
              "DIAGNOSTIC",result["diagnostic_grid_best_train_elasticity"],
              "PRODUCTION_CHANGED",not result["existing_model_parameters_unchanged"],
              "SHA",result["report_sha256"])
    except Exception as e:
        print("STEP13_TRAIN_ONLY_SOURCE_OR_FIT_BLOCKED",type(e).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
