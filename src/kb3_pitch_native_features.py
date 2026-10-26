"""Step11 single-PitchAPI shadow feature adapter. No API-Football joins.

Uses native match/team IDs for schedules, 90-minute final results and
shot-xG. A demo snapshot in memory is NOT a durable provenance receipt;
this mode is explicitly NOT CERTIFIED and never trains or predicts.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from src.kb3_features import (
    EloParameters,RESULT_LAG,FeatureSafetyError,utc_dt,digest,_compose_features
)
from src.kb3_pitch_native import check_season,verify_native_shots


def native_shadow_features(matches,target_match_id,*,season,source_observed_at_utc,
                           cutoff_utc,shot_observations=(),params=None):
    params=params or EloParameters()
    if not isinstance(params,EloParameters):
        raise FeatureSafetyError("INVALID_ELO")
    cutoff=utc_dt(cutoff_utc)
    source_at=utc_dt(source_observed_at_utc)
    if source_at>cutoff:
        raise FeatureSafetyError("SOURCE_OBSERVED_AFTER_CUTOFF")
    if not isinstance(season,str) or season!="2026/2027":
        raise FeatureSafetyError("NATIVE_SHADOW_CURRENT_SEASON_ONLY")
    evidence=check_season(matches,season,expected_count=380,require_upcoming=True)
    by_id={m["id"]:m for m in matches}
    if target_match_id not in by_id:
        raise FeatureSafetyError("MISSING_TARGET_NATIVE_ID")
    target=by_id[target_match_id]
    kickoff=utc_dt(target["time_utc"])
    if kickoff<=cutoff or target["status"]=="finished":
        raise FeatureSafetyError("TARGET_ALREADY_STARTED")
    accepted={}
    for o in shot_observations:
        if not isinstance(o,dict) or o.get("match_id") not in by_id:
            raise FeatureSafetyError("UNKNOWN_SHOT_NATIVE_ID")
        mid=o["match_id"]
        if mid in accepted:
            raise FeatureSafetyError("DUPLICATE_NATIVE_SHOTS")
        try:
            xg=verify_native_shots(by_id[mid],o["shots_response"],
                                   observed_at_utc=o["observed_at_utc"])
        except (KeyError,ValueError,TypeError) as exc:
            raise FeatureSafetyError("INVALID_NATIVE_SHOT_RECORD") from exc
        accepted[mid]=xg
    history=[]
    excluded=defaultdict(int)
    for m in matches:
        if m["id"]==target_match_id:continue
        date=utc_dt(m["time_utc"])
        if date>=cutoff or date>=kickoff:
            excluded["future_or_current"]+=1
            continue
        if m["status"]!="finished":
            excluded["not_finished"]+=1
            continue
        # Results observed after the game (and after a conservative lag).
        if date+RESULT_LAG>source_at:
            excluded["not_observed_after_result_lag"]+=1
            continue
        xg=accepted.get(m["id"])
        # The extra shot source has its own distinct observation clock.
        if xg and utc_dt(xg["captured_at_utc"])>cutoff:
            xg=None
            excluded["xg_observed_after_cutoff"]+=1
        if xg is not None and xg["shot_state"]=="COMPLETE_SHOT_XG":
            hxg,axg=xg["xg_home"],xg["xg_away"]
            origin={"pitch_match_id":m["id"],"source":"PitchAPI",
                    "captured_at_utc":xg["captured_at_utc"],
                    "provider_published_at_utc":None,
                    "source_natively_joined":True}
        else:
            hxg=axg=None
            origin=None
        history.append({
            "fixture_id":m["id"],
            "season_start_year":2026,
            "home_team_id":m["home_team"]["id"],
            "away_team_id":m["away_team"]["id"],
            "kickoff_utc":m["time_utc"],
            "date":date,"status":"FINISHED",
            "goals_home_90":m["score_home"],
            "goals_away_90":m["score_away"],
            "snapshot_id":"IN_MEMORY_SHADOW_NOT_PERSISTED",
            "result_provider_name":"PitchAPI",
            "result_record_updated_at_utc":None,
            "captured_at_utc":source_observed_at_utc,
            "published_at_utc":None,
            "xgh":hxg,"xga":axg,
            "xgh_source":origin,"xga_source":origin})
    target_core={
        "fixture_id":target_match_id,
        "home_team_id":target["home_team"]["id"],
        "away_team_id":target["away_team"]["id"],
        "season_start_year":2026}
    result=_compose_features(target_core,history,cutoff=cutoff,kickoff=kickoff,
            target_id=target_match_id,mode="shadow_native",
            params=params,excluded=excluded)
    result["source_evidence"]={
        "provider":"PitchAPI","single_provider_identity":True,
        "fixture_list_hash_sha256":evidence["match_digest_sha256"],
        "observed_at_utc":source_observed_at_utc,
        "raw_records_archived":False,
        "original_published_at_utc":None,
        "requires_future_verified_receipt_ledger":True,
        "training_allowed":False}
    result["sha256"]=digest({k:v for k,v in result.items() if k!="sha256"})
    assert result["training_allowed"] is False
    return result
