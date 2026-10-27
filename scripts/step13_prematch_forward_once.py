"""Step13: first genuine BEFORE-KICKOFF shadow forecast snapshot, 2026/27.

The training results are ONLY two seasons in original 760-match TRAIN.
The provider call for 2026/27 uses status=upcoming only; neither finished
2026/27 scores nor 2025/26 VALIDATION labels are requested or processed.
Forecasts are nonproduction research, with a durable real observation clock.
Never backdate provider publication times or imply historical PIT certification.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timedelta,timezone
import argparse
import json
import os
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain
from src.kb3_pitch_native import check_season
from src.kb3_split import sha,freeze_manifest,timestamp
from src.kb3_step13_baseline import forecast,BaselineSafetyError
from src.kb3_step13_retrospective import _validate,_historical_states,_train_poisson
from src.kb3_step13_poisson_train import FIXED_GRID

LEAGUE="l_4WFCIZ"
TRAIN_SEASONS=("2023/2024","2024/2025")
TARGET_SEASON="2026/2027"
SAFE="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
OUTPUT_SCHEMA="kb3-step13-prospective-first-frozen-shadow-v0.9"
REFERENCE_TRAIN_FIT={
    "base_home_goals":1.63733387301664,
    "base_away_goals":1.4370968890275349,
    "elo_goal_elasticity":0.6,
}
REFERENCE_REAL_REPORT_SHA="3d950fff30b57c94a6f71462c7521cfda2cb0b27c666d59d09d274261efca803"
CUTOFF_TRAIN="2025-07-01T00:00:00Z"
MIN_LEAD_HOURS=48
HORIZON_DAYS=10
MAX_MATCHES=10


def train_only(raw_by_season, safe):
    """Admit *only* the frozen 760 TRAIN IDs and no other score-bearing data."""
    if set(raw_by_season)!=set(TRAIN_SEASONS):
        raise BaselineSafetyError("STEP13_FORWARD_TRAIN_SEASONS_EXACT_ONLY")
    if (safe.get("schema")!="kb3-step12-methodology-v1" or
        safe.get("training_allowed") is not False or
        safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380}):
        raise BaselineSafetyError("STEP13_FORWARD_FROZEN_SPLIT_MISSING")
    fixtures=safe.get("fixtures")
    if not isinstance(fixtures,list) or len(fixtures)!=1520:
        raise BaselineSafetyError("STEP13_FORWARD_SPLIT_NOT_1520")
    training={f["fixture_id"]:f for f in fixtures if f.get("partition")=="TRAIN"}
    if len(training)!=760:
        raise BaselineSafetyError("STEP13_FORWARD_TRAIN_IDENTITIES_BAD")
    rows=[]
    previous=None
    seen=set()
    fingerprints={}
    for season in TRAIN_SEASONS:
        payload=raw_by_season[season]
        if not isinstance(payload,dict) or not isinstance(payload.get("matches"),list):
            raise BaselineSafetyError("STEP13_FORWARD_TRAIN_PAYLOAD_INVALID")
        games=payload["matches"]
        evidence=check_season(games,season,expected_count=380)
        if evidence["status_counts"]!={"finished":380}:
            raise BaselineSafetyError("STEP13_FORWARD_TRAIN_NOT_FINISHED")
        fingerprints[season]=evidence["match_digest_sha256"]
        teams={t["id"] for g in games for t in (g["home_team"],g["away_team"])}
        if len(teams)!=20 or previous is not None and len(teams&previous)<14:
            raise BaselineSafetyError("STEP13_FORWARD_TRAIN_TEAM_IDS_DRIFT")
        previous=teams
        for g in games:
            idx=training.get(g["id"])
            if g["id"] in seen or idx is None or timestamp(idx["kickoff_utc"])!=timestamp(g["time_utc"]):
                raise BaselineSafetyError("STEP13_FORWARD_TRAIN_ID_OR_DATE_CHANGED")
            seen.add(g["id"])
            rows.append({
                "fixture_id":g["id"],
                "home_team_id":g["home_team"]["id"],
                "away_team_id":g["away_team"]["id"],
                "kickoff_utc":idx["kickoff_utc"],
                "goals_home_90":g["score_home"],
                "goals_away_90":g["score_away"],
            })
    if seen!=set(training) or len(rows)!=760:
        raise BaselineSafetyError("STEP13_FORWARD_TRAIN_INCOMPLETE")
    checked=_validate(rows)
    ratings,train=_historical_states(checked,boundary=timestamp(CUTOFF_TRAIN),
                                      lower=timestamp("2023-07-01T00:00:00Z"))
    if len(train)!=760:
        raise BaselineSafetyError("STEP13_FORWARD_FIT_EMBARGO_CHANGED")
    parameters=_train_poisson(train)
    if any(abs(getattr(parameters,k)-v)>1e-10 for k,v in REFERENCE_TRAIN_FIT.items()):
        raise BaselineSafetyError("STEP13_FORWARD_ORIGINAL_TRAIN_FIT_DRIFT")
    if parameters.elo_goal_elasticity!=FIXED_GRID[-1]:
        raise BaselineSafetyError("STEP13_FORWARD_TRAIN_ELASTICITY_CHANGED")
    return parameters,ratings,fingerprints,sha(rows)


def build_first_snapshot(*,train_seasons,upcoming_payload,safe,observed_at,completed_at):
    """No result input from 2026/27. Fail closed on a drifted fixture kickoff."""
    source_time=timestamp(observed_at)
    frozen_time=timestamp(completed_at)
    if frozen_time<source_time:
        raise BaselineSafetyError("STEP13_FORWARD_FREEZE_BEFORE_SOURCE")
    if (safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380} or
        safe.get("training_allowed") is not False):
        raise BaselineSafetyError("STEP13_FORWARD_SPLIT_UNSAFE")
    params,ratings,train_fingerprints,train_hash=train_only(train_seasons,safe)
    if not isinstance(upcoming_payload,dict) or not isinstance(upcoming_payload.get("matches"),list):
        raise BaselineSafetyError("STEP13_FORWARD_UPCOMING_PAYLOAD_INVALID")
    games=upcoming_payload["matches"]
    if not games:
        raise BaselineSafetyError("STEP13_FORWARD_NO_UPCOMING_PROVIDER_MATCHES")
    check_season(games,TARGET_SEASON,expected_count=None,require_upcoming=True)
    safe_test={f["fixture_id"]:f for f in safe["fixtures"] if f["partition"]=="TEST"}
    if len(safe_test)!=380:
        raise BaselineSafetyError("STEP13_FORWARD_NO_PINNED_TEST_FIXTURES")
    upper=source_time+timedelta(days=HORIZON_DAYS)
    lower=source_time+timedelta(hours=MIN_LEAD_HOURS)
    targets=[]
    for m in games:
        if m.get("status")!="not_started" or m.get("score_home") is not None or m.get("score_away") is not None:
            raise BaselineSafetyError("STEP13_FORWARD_UPCOMING_HAS_RESULT_OR_STATUS")
        kickoff=timestamp(m["time_utc"])
        if lower<=kickoff<=upper:
            expected=safe_test.get(m["id"])
            if expected is None or kickoff!=timestamp(expected["kickoff_utc"]):
                raise BaselineSafetyError("STEP13_FORWARD_TARGET_ID_OR_KICKOFF_DRIFT")
            if frozen_time>=kickoff:
                raise BaselineSafetyError("STEP13_FORWARD_FROZEN_TOO_LATE")
            targets.append(m)
    if not 1<=len(targets)<=MAX_MATCHES:
        raise BaselineSafetyError("STEP13_FORWARD_TARGET_COUNT_UNSAFE")
    forecasts=[]
    for m in sorted(targets,key=lambda x:(x["time_utc"],x["id"])):
        h,a=m["home_team"],m["away_team"]
        p=forecast(ratings.get(h["id"],params.initial_elo),
                   ratings.get(a["id"],params.initial_elo),params)
        likelihood=p["p_1x2"]
        if abs(sum(likelihood.values())-1.0)>1e-12:
            raise BaselineSafetyError("STEP13_FORWARD_1X2_NOT_NORMALIZED")
        forecasts.append({
            "fixture_id":m["id"],
            "kickoff_utc":m["time_utc"],
            "home_team_id":h["id"],"away_team_id":a["id"],
            "home_team_name":h["name"],"away_team_name":a["name"],
            "scores_at_source":{"home":None,"away":None},
            "probabilities_1x2":likelihood,
            "expected_goals":p["expected_goals"],
            "highest_probability_scoreline":p["top_5_scorelines"][0],
            "elo_at_forecast":{"home":p["elo_home"],"away":p["elo_away"]},
            "source_observed_at_utc":observed_at,
            "forecast_frozen_at_utc":completed_at,
            "target_result_known_before_forecast":False,
            "eligible_for_betting":False,
        })
    result={
        "schema":OUTPUT_SCHEMA,
        "source":"PitchAPI",
        "historical_train_seasons":list(TRAIN_SEASONS),
        "target_season":TARGET_SEASON,
        "provider_requests":3,
        "provider_request_policy":"2_FINISHED_HISTORICAL_TRAIN_LISTS_PLUS_1_UPCOMING_ONLY_TEST_SCHEDULE",
        "observed_at_utc":observed_at,
        "forecast_frozen_at_utc":completed_at,
        "original_provider_publication_time_proven":False,
        "genuinely_pre_kickoff_observation_and_forecast":True,
        "historical_2023_2026_prematch_pit_certified":False,
        "original_retro_validation_report_sha256":REFERENCE_REAL_REPORT_SHA,
        "frozen_step12_safe_view_sha256":safe["projection_sha256"],
        "historical_train_native_season_hashes":train_fingerprints,
        "train_input_sha256":train_hash,
        "train_rows_admitted":760,
        "validation_rows_admitted":0,
        "test_results_accessed":0,
        "test_future_fixture_metadata_used":len(forecasts),
        "initial_elo_history_omits_2025_2026_validation_and_2026_2027_test_outcomes":True,
        "rating_limitation":"OUTDATED_ELO_AS_OF_2025_07_01_NO_CURRENT_SEASON_RESULTS",
        "fit_parameters":{k:getattr(params,k) for k in
                          ("initial_elo","elo_k","elo_scale","elo_home_advantage",
                           "base_home_goals","base_away_goals","elo_goal_elasticity")},
        "first_snapshot_match_count":len(forecasts),
        "forecasts":forecasts,
        "immutable_predictions_pending_future_results":True,
        "no_odds_or_market_inputs":True,
        "research_shadow_only":True,
        "no_model_champion_selected":True,
        "training_allowed":False,
        "gate13_pass":False,
        "step14_started":False,
    }
    result["report_sha256"]=sha(result)
    return result


def capture():
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:
        raise BaselineSafetyError("STEP13_FORWARD_NO_PROVIDER_SECRET")
    safe=json.loads(Path(SAFE).read_text(encoding="utf8"))
    from pitchapi import PitchAPI
    sdk=PitchAPI(api_key=key)
    sources={}
    for season in TRAIN_SEASONS:
        sources[season]=to_plain(sdk.leagues.matches(LEAGUE,season=season,status="played"))
    # No API call for played/all in TEST 2026/27. Absolutely upcoming only.
    upcoming=to_plain(sdk.leagues.matches(LEAGUE,season=TARGET_SEASON,status="upcoming"))
    observed=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    # Restrict provider payload to in-memory validation & never persist outcomes.
    completed=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    return build_first_snapshot(train_seasons=sources,upcoming_payload=upcoming,
                                safe=safe,observed_at=observed,completed_at=completed)


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--output",required=True)
    parsed=args.parse_args()
    try:
        report=capture()
        result=freeze_manifest(report,parsed.output)
        print("KB3_STEP13_REAL_PREMATCH_SHADOW_FROZEN",
              result,"MATCHES",report["first_snapshot_match_count"],
              "TRAIN",report["train_rows_admitted"],
              "VALIDATION",report["validation_rows_admitted"],
              "TEST_RESULTS",report["test_results_accessed"],
              "GATE13",report["gate13_pass"],"SHA",report["report_sha256"])
    except Exception as exc:
        print("KB3_STEP13_PREMATCH_SHADOW_BLOCKED",type(exc).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
