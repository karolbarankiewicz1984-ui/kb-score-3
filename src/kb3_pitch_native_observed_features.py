"""Build observed-at PitchAPI-native features; never fit or predict."""
from __future__ import annotations
from collections import defaultdict
from src.kb3_pitch_native_ledger import verify,latest_asof,shots_asof
from src.kb3_features import FeatureSafetyError,EloParameters,RESULT_LAG,utc_dt,_compose_features

def build_native_observed(db,target_match_id,*,cutoff_utc,elo_params=None):
    params=EloParameters() if elo_params is None else elo_params
    if not isinstance(params,EloParameters):
        raise FeatureSafetyError("INVALID_ELO_PARAMETERS")
    cutoff=utc_dt(cutoff_utc)
    proof=verify(db)
    if not proof["fixture_captures"]:
        raise FeatureSafetyError("NO_NATIVE_PROVIDER_CAPTURE")
    games=latest_asof(db,cutoff_utc)
    if games is None:
        raise FeatureSafetyError("NO_NATIVE_SOURCE_BEFORE_CUTOFF")
    if target_match_id not in games:
        raise FeatureSafetyError("NATIVE_TARGET_NOT_IN_CAPTURE")
    sessions=db.execute("""SELECT capture_id,chain_sha256,completed_at_utc
      FROM pitch_captures WHERE kind='matches' AND origin='NETWORK_OBSERVED'
      ORDER BY completed_at_utc DESC,ordinal DESC""").fetchall()
    selected=next((r for r in sessions if utc_dt(r[2])<=cutoff),None)
    if selected is None:
        raise FeatureSafetyError("NATIVE_CAPTURE_NOT_FOUND")
    cid,chain,observed_at=selected
    target_game=games[target_match_id]
    kickoff=utc_dt(target_game["time_utc"])
    if cutoff>=kickoff or target_game["status"]=="finished":
        raise FeatureSafetyError("NATIVE_TARGET_ALREADY_STARTED")
    target={"fixture_id":target_match_id,
       "home_team_id":target_game["home_team"]["id"],
       "away_team_id":target_game["away_team"]["id"],
       "season_start_year":2026}
    history=[];excluded=defaultdict(int)
    for mid,game in games.items():
        if mid==target_match_id:continue
        start=utc_dt(game["time_utc"])
        if start>=kickoff or start>=cutoff:
            excluded["not_before_cutoff"]+=1;continue
        if game["status"]!="finished":
            excluded["not_finished"]+=1;continue
        if start+RESULT_LAG>utc_dt(observed_at):
            excluded["result_not_known"]+=1;continue
        observation=shots_asof(db,mid,cutoff_utc)
        if observation:
            home_xg,away_xg=observation["xg_home"],observation["xg_away"]
            source={"provider":"PitchAPI","native_match_id":mid,
                    "shot_observed_at_utc":observation["captured_at_utc"],
                    "source_published_at_utc":None}
        else:
            home_xg=away_xg=None;source=None
        history.append({"fixture_id":mid,"season_start_year":2026,
           "home_team_id":game["home_team"]["id"],
           "away_team_id":game["away_team"]["id"],
           "kickoff_utc":game["time_utc"],"date":start,"status":"FINISHED",
           "goals_home_90":game["score_home"],"goals_away_90":game["score_away"],
           "snapshot_id":cid,"result_provider_name":"PitchAPI",
           "result_record_updated_at_utc":None,
           "captured_at_utc":observed_at,"published_at_utc":None,
           "xgh":home_xg,"xga":away_xg,
           "xgh_source":source,"xga_source":source})
    evidence={"provider":"PitchAPI","native_ids_only":True,
      "source_capture_id":cid,"source_chain_sha256":chain,
      "source_observed_at_utc":observed_at,
      "hash_chain_verified":True,"source_first_publication_time_known":False,
      "historical_pit_certified":False,"training_allowed":False}
    return _compose_features(target,history,cutoff=cutoff,kickoff=kickoff,
        target_id=target_match_id,mode="observed",params=params,
        excluded=excluded,source_evidence=evidence)
