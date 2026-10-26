"""Step11: optional *independent* sealed strict-xG evidence for observed features.

Never splice two independently hash-chained PIT SQLite files together. Validate
each against its own source manifest, require the exact same fixture response,
and use strict shot-xG no earlier than its genuinely recorded capture time.
"""
from __future__ import annotations
import sqlite3
from src.kb3_pit_ledger import verify_chain,as_utc
from src.kb3_xg_pit import verify_xg,_inspect


def collect_strict_xg(db,manifest,*,cutoff_utc,fixture_response_sha256):
    if not isinstance(manifest,dict) or manifest.get("schema")!="kb3-pit-sealed-observation-v1":
        raise ValueError("INVALID_INDEPENDENT_XG_MANIFEST")
    if manifest.get("training_allowed") is not False or manifest.get("provider_publication_certified") is not False:
        raise ValueError("UNSAFE_SECONDARY_XG_SOURCE_CLAIM")
    if not isinstance(manifest.get("encrypted_sha256"),str) or len(manifest["encrypted_sha256"])!=64:
        raise ValueError("SECONDARY_XG_CIPHERTEXT_ID_MISSING")
    actual_ledger=verify_chain(db)
    actual_xg=verify_xg(db)
    if actual_ledger!=manifest.get("ledger_evidence") or actual_xg!=manifest.get("xg_evidence"):
        raise ValueError("SECONDARY_SOURCE_MANIFEST_MISMATCH")
    sessions=db.execute("""SELECT resource,origin,completed_at_utc,response_sha256
                            FROM captures""").fetchall()
    if len(sessions)!=1 or sessions[0][:2]!=("fixtures?league=39&season=2026","NETWORK_OBSERVED"):
        raise ValueError("SECONDARY_CAPTURE_SCOPE_NOT_APPROVED")
    scope,origin,source_observed_at,source_sha=sessions[0]
    if source_sha!=fixture_response_sha256:
        raise ValueError("SECONDARY_SNAPSHOT_SOURCE_MISMATCH")
    cutoff=as_utc(cutoff_utc)
    # This source observation is not available at a pre-observation cutoff.
    if as_utc(source_observed_at)>cutoff:
        return {},None
    xg_map={}
    for row in db.execute("SELECT * FROM pit_xg_observations"):
        info=_inspect(row)
        if info["identity_state"]!="EXACT_TIME_NAMES_SCORE_FT" or info["result_state"]!="COMPLETE_SHOT_XG":
            continue
        if as_utc(info["completed_at_utc"])>cutoff:
            continue
        fid=info["api_football_fixture_id"]
        if fid in xg_map:
            raise ValueError("DUPLICATE_STRICT_XG_MATCH")
        xg_map[fid]={
            "xg_home":info["xg_home"],"xg_away":info["xg_away"],
            "observed_completed_at_utc":info["completed_at_utc"],
            "source_observation_id":row[0],
            "pitch_match_id":row[1],
            "review_status":"SOURCE_STRICT_EXACT_TIME_NAMES_SCORE",
            "provider_initial_published_at_utc":None,
            "historical_pit_certified":False,
            "training_allowed":False}
    return xg_map,{
       "sealed_ciphertext_sha256":manifest["encrypted_sha256"],
       "source_observed_at_utc":source_observed_at,
       "source_response_sha256":source_sha,
       "strict_xg_available_at_cutoff":len(xg_map),
       "provider_initial_published_at_known":False,
       "training_allowed":False,
    }
