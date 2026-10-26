"""Step11: re-evaluate three frozen provider-ID reviews without mutating source.

A reviewed crosswalk is evidence for *these exact matches only*. It is not a
general fuzzy alias mapping, historic provider-publication certification, or
permission for ML. Original quarantined xG observations remain immutable.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import timedelta
from src.kb3_pit_ledger import as_utc,verify_chain,select_result_asof,hexdigest,canonical
from src.kb3_xg_pit import verify_xg,MIN_POSTMATCH_LAG
from scripts.pitchapi_step06_audit import parse_shots


def review(db, archive_manifest, crosswalk):
    if crosswalk.get("schema")!="kb3-step11-reviewed-fixture-crosswalk-v1":
        raise ValueError("WRONG_REVIEW_SCHEMA")
    if crosswalk.get("generic_name_alias_matching_allowed") is not False:
        raise ValueError("GENERIC_ALIASES_NOT_ALLOWED")
    if crosswalk.get("model_training_allowed") is not False:
        raise ValueError("REVIEW_CANNOT_ENABLE_TRAINING")
    if crosswalk["source_encrypted_sha256"]!=archive_manifest.get("encrypted_sha256"):
        raise ValueError("REVIEW_ARCHIVE_MISMATCH")
    ledger=verify_chain(db)
    if ledger["final_chain_sha256"]!=crosswalk["source_fixture_chain_sha256"]:
        raise ValueError("REVIEW_SOURCE_CHAIN_MISMATCH")
    before=verify_xg(db)
    reviews=crosswalk.get("reviewed")
    if not isinstance(reviews,list) or len(reviews)<1:
        raise ValueError("EMPTY_CROSSWALK")
    accepted={}
    seen_pitch=set()
    for r in reviews:
        pid=r["pitch_match_id"]
        fid=r["api_fixture_id"]
        if pid in seen_pitch or fid in accepted:
            raise ValueError("DUPLICATE_REVIEWED_MAPPING")
        seen_pitch.add(pid)
        rows=db.execute("""SELECT observation_id,raw_sha256,raw_json,
                                  completed_at_utc,identity_state,
                                  api_football_fixture_id,xg_home,xg_away
                           FROM pit_xg_observations WHERE pitch_match_id=?""",(pid,)).fetchall()
        if len(rows)!=1:
            raise ValueError("EXACTLY_ONE_SOURCE_OBSERVATION_REQUIRED")
        oid,rawhash,raw,observed,original_identity,original_fid,xgh,xga=rows[0]
        if (oid!=r["pitch_observation_id"] or rawhash!=r["raw_sha256"] or
                original_fid is not None or xgh is not None or xga is not None):
            raise ValueError("IMMUTABLE_QUARANTINE_EVIDENCE_MISMATCH")
        envelope=json.loads(raw)
        if envelope.get("schema")!="kb3-xg-source-envelope-v2":
            raise ValueError("NO_ORIGINAL_MATCH_METADATA_FOR_REVIEW")
        match=envelope["pitch_match"]
        if (match["id"]!=pid or as_utc(match["time_utc"])!=as_utc(r["pitch_kickoff_utc"]) or
                match.get("status")!="finished" or
                match.get("score_home")!=r["score_home"] or
                match.get("score_away")!=r["score_away"] or
                match["home_team"].get("id")!=r["pitch_home_team_id"] or
                match["away_team"].get("id")!=r["pitch_away_team_id"] or
                match["home_team"].get("name")!=r["pitch_home_name"] or
                match["away_team"].get("name")!=r["pitch_away_name"]):
            raise ValueError("PITCH_TEAM_ID_OR_MATCH_CHANGED")
        fixture=[f for f in envelope["api_football_candidates"]
                 if (f.get("fixture") or {}).get("id")==fid]
        if len(fixture)!=1:
            raise ValueError("NO_UNIQUE_REVIEWED_FOOTBALL_FIXTURE")
        f=fixture[0]
        if ((f["fixture"].get("status") or {}).get("short")!="FT" or
                as_utc(f["fixture"]["date"])!=as_utc(match["time_utc"]) or
                f["teams"]["home"].get("id")!=r["api_home_team_id"] or
                f["teams"]["away"].get("id")!=r["api_away_team_id"] or
                f["teams"]["home"].get("name")!=r["api_home_name"] or
                f["teams"]["away"].get("name")!=r["api_away_name"] or
                f["goals"].get("home")!=r["score_home"] or
                f["goals"].get("away")!=r["score_away"]):
            raise ValueError("FOOTBALL_TEAM_ID_OR_RESULT_CHANGED")
        if as_utc(observed)<as_utc(match["time_utc"])+MIN_POSTMATCH_LAG:
            raise ValueError("XG_CAPTURE_BEFORE_ELIGIBILITY")
        result=select_result_asof(db,fid,observed)
        if (not result or result["result_home_90"]!=r["score_home"] or
                result["result_away_90"]!=r["score_away"]):
            raise ValueError("FOOTBALL_RESULT_NOT_OBSERVED_BEFORE_XG")
        source_teams=(r["pitch_home_team_id"],r["pitch_away_team_id"])
        xg=parse_shots(envelope["shots_response"],*source_teams)
        if xg.get("state")!="COMPLETE_SHOT_XG":
            raise ValueError("XG_SHOTS_NOT_COMPLETE")
        accepted[fid]={"pitch_match_id":pid,
                       "xg_home":xg["home_xg_sum"],"xg_away":xg["away_xg_sum"],
                       "observed_completed_at_utc":observed,
                       "source_observation_id":oid,
                       "review_status":"CURATED_MATCH_BOUND_SOURCE_EVIDENCE",
                       "provider_initial_published_at_utc":None,
                       "historical_pit_certified":False,
                       "training_allowed":False}
    if len(accepted)>before["quarantined"]:
        raise ValueError("REVIEW_EXCEEDS_QUARANTINE")
    return accepted


def select_asof(db,archive_manifest,crosswalk,*,history_fixture_id,target_fixture_id,cutoff_utc):
    """Derived xG may only describe an EARLIER match than the prediction target.

    Never use an event's own post-match shots in its prematch prediction.
    """
    accepted=review(db,archive_manifest,crosswalk)
    x=accepted.get(history_fixture_id)
    if x is None or target_fixture_id==history_fixture_id:
        return None
    cutoff=as_utc(cutoff_utc)
    if as_utc(x["observed_completed_at_utc"])>cutoff:
        return None
    target=db.execute("SELECT response_json FROM captures LIMIT 1").fetchone()
    if not target: return None
    fixtures=json.loads(target[0])["response"]
    matches=[z for z in fixtures if z["fixture"]["id"]==target_fixture_id]
    if len(matches)!=1:
        return None
    if as_utc(matches[0]["fixture"]["date"])<=cutoff:
        return None
    return dict(x)
