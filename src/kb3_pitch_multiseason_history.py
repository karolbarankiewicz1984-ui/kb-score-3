"""Strict PitchAPI-native Premier League historical source receipts.

Historical seasons fetched NOW are retrospective provider records, not
original in-2023..2026 prematch observations. They may enrich a future
2026/27 observed-at feature ONLY after their actual fetch time.
No API-Football identifiers, league switches, alias names or training.
"""
from __future__ import annotations
from datetime import datetime, timezone
from src.kb3_pit_ledger import as_utc
from src.kb3_pitch_native import check_season
from src.kb3_pitch_uefa_evidence import verify_receipts
from src.kb3_features import FeatureSafetyError,RESULT_LAG,utc_dt

HISTORICAL_SEASONS=("2023/2024","2024/2025","2025/2026")
SEASON_RESOURCE="pitchapi:history:premier-league:{season}:matches:played"

def historical_season_history(receipts,*,cutoff_utc,current_match_ids=()):
    """Validate all 3 REAL independently captured historical source lists.

    Include only results whose SOURCE was fetched by cutoff and at least
    3h after kickoff. No retroactive prediction availability is claimed.
    """
    if not isinstance(receipts,list):
        raise FeatureSafetyError("PITCH_HISTORICAL_RECEIPTS_REQUIRED")
    try:
        proof=verify_receipts(receipts)
    except (ValueError,KeyError,TypeError) as exc:
        raise FeatureSafetyError("INVALID_HISTORICAL_SOURCE_CHAIN") from exc
    cutoff=utc_dt(cutoff_utc)
    if not receipts or len(receipts)!=4:
        raise FeatureSafetyError("PITCH_HISTORICAL_RECEIPT_COUNT_INVALID")
    catalogue=[r for r in receipts if r.get("resource")=="pitchapi:catalog"]
    if len(catalogue)!=1:
        raise FeatureSafetyError("PITCH_HISTORICAL_CATALOGUE_NOT_UNIQUE")
    all_sources={}
    identities=set(current_match_ids)
    history=[]
    latest_observed=None
    for year in HISTORICAL_SEASONS:
        res=SEASON_RESOURCE.format(season=year)
        matching=[r for r in receipts if r.get("resource")==res]
        if len(matching)!=1:
            raise FeatureSafetyError("PITCH_HISTORICAL_SEASON_MISSING_OR_DUPLICATED")
        r=matching[0]
        observed=utc_dt(r["completed_at_utc"])
        if observed>cutoff:
            raise FeatureSafetyError("PITCH_HISTORICAL_OBSERVED_AFTER_CUTOFF")
        latest_observed=max(latest_observed,observed) if latest_observed else observed
        response=r["payload"]
        if not isinstance(response,dict) or not isinstance(response.get("matches"),list):
            raise FeatureSafetyError("PITCH_HISTORICAL_PAYLOAD_MISSING")
        match_list=response["matches"]
        try:
            evidence=check_season(match_list,year,expected_count=380,
                                  require_upcoming=False)
        except (ValueError,TypeError) as exc:
            raise FeatureSafetyError("PITCH_HISTORICAL_SEASON_INVALID") from exc
        if evidence["status_counts"]!={"finished":380}:
            raise FeatureSafetyError("PITCH_HISTORICAL_SEASON_NOT_ALL_FINISHED")
        all_sources[year]={
            "fixture_count":380,
            "status":"RETROSPECTIVE_OBSERVED_NOW_NOT_HISTORIC_PIT",
            "provider_original_published_at_utc":None,
            "source_observed_at_utc":r["completed_at_utc"],
            "source_payload_sha256":r["payload_sha256"],
        }
        for m in match_list:
            mid=m["id"]
            if mid in identities:
                raise FeatureSafetyError("PITCH_HISTORICAL_DUPLICATE_NATIVE_MATCH_ID")
            identities.add(mid)
            ko=utc_dt(m["time_utc"])
            if ko>=cutoff or ko+RESULT_LAG>observed:
                raise FeatureSafetyError("PITCH_HISTORICAL_MATCH_NOT_OBSERVED_ASOF")
            history.append({
              "fixture_id":mid,"season_start_year":int(year[:4]),
              "home_team_id":m["home_team"]["id"],
              "away_team_id":m["away_team"]["id"],
              "kickoff_utc":m["time_utc"],"date":ko,"status":"FINISHED",
              "goals_home_90":m["score_home"],"goals_away_90":m["score_away"],
              "snapshot_id":r["chain_sha256"][:32],
              "result_provider_name":"PitchAPI",
              "result_record_updated_at_utc":None,
              "captured_at_utc":r["completed_at_utc"],"published_at_utc":None,
              "xgh":None,"xga":None,
              "xgh_source":None,"xga_source":None})
    if set(x["resource"] for x in receipts)!={
        "pitchapi:catalog",*(SEASON_RESOURCE.format(season=x) for x in HISTORICAL_SEASONS)
    }:
        raise FeatureSafetyError("PITCH_HISTORICAL_UNEXPECTED_SOURCE_RESOURCE")
    if utc_dt(catalogue[0]["completed_at_utc"])>cutoff:
        raise FeatureSafetyError("PITCH_HISTORICAL_CATALOGUE_AFTER_CUTOFF")
    latest_observed=max(latest_observed,utc_dt(catalogue[0]["completed_at_utc"]))
    return history,{"provider":"PitchAPI","seasons":all_sources,
        "source_receipt_chain_sha256":proof["final_chain_sha256"],
        "actual_observed_at_utc":latest_observed.isoformat().replace("+00:00","Z"),
        "historical_provider_pit_certified":False,
        "training_allowed":False}
