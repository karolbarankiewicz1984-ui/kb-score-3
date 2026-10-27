"""Step13 / task 3: freeze SECOND future Premier League 1X2 shadow cohort.

Pre-registered fixture window: 2026-11-06 through 2026-11-08 UTC. Select
exactly ten safe metadata fixture IDs. All results strictly TRAIN 2023/24 and
2024/25; test provider listing MUST be status=upcoming with NULL scores.
No validation or TEST labels, no odds, no updates from 2025/26-2026/27.
"""
from __future__ import annotations
import argparse,json,os
from datetime import datetime, timezone
from pathlib import Path
from scripts.pitchapi_step06_audit import to_plain
from scripts.step13_prematch_forward_once import LEAGUE,TRAIN_SEASONS,TARGET_SEASON,SAFE,train_only
from src.kb3_step13_baseline import forecast,BaselineSafetyError
from src.kb3_pitch_native import check_season
from src.kb3_split import sha,freeze_manifest,timestamp
from src.kb3_step13_forward_score import SOURCE_HASH,SOURCE_FILE

SCHEMA="kb3-step13-prospective-second-ten-shadow-v1"
FIRST_TRAIN_SHA="5b1f46592457a648a3761d30ae3f519065470af06d6bf5f8505808b7c09dfac7"
START="2026-11-06T00:00:00Z"
END="2026-11-09T00:00:00Z"
OUTPUT="data/forecasts/STEP13_SECOND_PROSPECTIVE_PREMATCH_2026-10-27.json"

def next_10(*,train_seasons, upcoming_payload, safe, first_snapshot, observed_at, frozen_at):
    now,lock=timestamp(observed_at),timestamp(frozen_at)
    if not now<=lock<timestamp(START):
        raise BaselineSafetyError("STEP13_NEXT_FREEZE_NOT_BEFORE_COHORT")
    if (first_snapshot.get("report_sha256")!=SOURCE_HASH or
        sha({k:v for k,v in first_snapshot.items() if k!="report_sha256"})!=SOURCE_HASH):
        raise BaselineSafetyError("STEP13_NEXT_ORIGINAL_FORECAST_CHANGED")
    if (safe.get("schema")!="kb3-step12-methodology-v1" or
        safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380} or
        safe.get("training_allowed") is not False):
        raise BaselineSafetyError("STEP13_NEXT_SAFE_SPLIT_CHANGED")
    params,ratings,train_hashes,input_hash=train_only(train_seasons,safe)
    if input_hash!=FIRST_TRAIN_SHA or not all(abs(params.__dict__[key]-first_snapshot["fit_parameters"][key])<1e-12
       for key in first_snapshot["fit_parameters"]):
        raise BaselineSafetyError("STEP13_NEXT_TRAIN_OR_PARAMETER_DRIFT")
    if not isinstance(upcoming_payload,dict) or not isinstance(upcoming_payload.get("matches"),list):
        raise BaselineSafetyError("STEP13_NEXT_UPCOMING_PAYLOAD_INVALID")
    games=upcoming_payload["matches"]
    check_season(games,TARGET_SEASON,expected_count=None,require_upcoming=True)
    # Every source game, including one outside this cohort, must have no score.
    if any(g["status"]!="not_started" or g["score_home"] is not None or g["score_away"] is not None
           for g in games):
        raise BaselineSafetyError("STEP13_NEXT_UPCOMING_CONTAINS_TEST_LABEL")
    metadata={f["fixture_id"]:f for f in safe["fixtures"] if f["partition"]=="TEST" and
               timestamp(START)<=timestamp(f["kickoff_utc"])<timestamp(END)}
    if len(metadata)!=10:
        raise BaselineSafetyError("STEP13_NEXT_PREDECLARED_TEN_NOT_FOUND")
    original_ids={f["fixture_id"] for f in first_snapshot["forecasts"]}
    if set(metadata)&original_ids:
        raise BaselineSafetyError("STEP13_NEXT_REUSES_PRIOR_COHORT")
    candidates={g["id"]:g for g in games if g["id"] in metadata}
    if set(candidates)!=set(metadata):
        raise BaselineSafetyError("STEP13_NEXT_PROVIDER_MISSING_FIXED_TARGET")
    output=[]
    for fid in sorted(metadata,key=lambda k:(metadata[k]["kickoff_utc"],k)):
        game=candidates[fid]
        ko=timestamp(game["time_utc"])
        if ko!=timestamp(metadata[fid]["kickoff_utc"]) or not now<lock<ko:
            raise BaselineSafetyError("STEP13_NEXT_PROVIDER_KICKOFF_CHANGED")
        h,a=game["home_team"],game["away_team"]
        p=forecast(ratings.get(h["id"],params.initial_elo),
                   ratings.get(a["id"],params.initial_elo),params)
        if abs(sum(p["p_1x2"].values())-1)>1e-12:
            raise BaselineSafetyError("STEP13_NEXT_INVALID_PROB")
        output.append({
            "fixture_id":fid,"kickoff_utc":game["time_utc"],
            "home_team_id":h["id"],"away_team_id":a["id"],
            "home_team_name":h["name"],"away_team_name":a["name"],
            "probabilities_1x2":p["p_1x2"],
            "expected_goals_poisson":p["expected_goals"],
            "scores_at_source":{"home":None,"away":None},
            "source_observed_at_utc":observed_at,
            "forecast_frozen_at_utc":frozen_at,
            "eligible_for_betting":False,
        })
    result={
        "schema":SCHEMA,"source":"PitchAPI","season":TARGET_SEASON,
        "cohort_window_utc":[START,END],
        "source_observed_at_utc":observed_at,
        "forecast_frozen_at_utc":frozen_at,
        "previous_cohort_snapshot_sha256":SOURCE_HASH,
        "TRAIN_original_rows":760,
        "train_input_sha256":input_hash,
        "fitted_parameters_unchanged":True,
        "train_season_digests_sha256":train_hashes,
        "VALIDATION_results_read":0,"TEST_results_read":0,
        "test_metadata_only_targets":10,
        "previous_cohort_overlap_count":0,
        "cohort_target_count":10,
        "forecasts":output,
        "source_query_policy":"2_FINISHED_TRAIN_AND_1_UPCOMING_ONLY_TEST",
        "provider_requests":3,"original_source_pubtime_verified":False,
        "ratings_not_updated_since_2025_07_01":True,
        "historical_pit_proven":False,
        "shadow_research_only":True,
        "no_model_retraining_or_tuning":True,
        "training_allowed":False,"gate13_pass":False,"step14_started":False,
    }
    result["report_sha256"]=sha(result)
    return result

def capture():
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:raise BaselineSafetyError("STEP13_NEXT_MISSING_PROVIDER_CREDENTIAL")
    safe=json.loads(Path(SAFE).read_text(encoding="utf8"))
    original=json.loads(Path(SOURCE_FILE).read_text(encoding="utf8"))
    from pitchapi import PitchAPI
    client=PitchAPI(api_key=key)
    hist={}
    for year in TRAIN_SEASONS:
        hist[year]=to_plain(client.leagues.matches(LEAGUE,season=year,status="played"))
    upcoming=to_plain(client.leagues.matches(LEAGUE,season=TARGET_SEASON,status="upcoming"))
    received=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    provisional=next_10(train_seasons=hist,upcoming_payload=upcoming,safe=safe,
                       first_snapshot=original,observed_at=received,frozen_at=received)
    # Explicitly fix actual lock time AFTER forecast computation.
    finished=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    if not timestamp(finished)<timestamp(START):
        raise BaselineSafetyError("STEP13_NEXT_TOO_LATE_TO_FREEZE")
    provisional["forecast_frozen_at_utc"]=finished
    for row in provisional["forecasts"]:row["forecast_frozen_at_utc"]=finished
    provisional["report_sha256"]=sha({k:v for k,v in provisional.items() if k!="report_sha256"})
    return provisional

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default=OUTPUT)
    opts=p.parse_args()
    try:
        result=capture()
        freeze_manifest(result,opts.output)
        print("STEP13_SECOND_GENUINE_PREMATCH_COHORT_FROZEN",
           "n",result["cohort_target_count"],"SHA",result["report_sha256"],
           "TEST_RESULTS",result["TEST_results_read"])
    except Exception as e:
        print("STEP13_SECOND_PREMATCH_BLOCKED",type(e).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
