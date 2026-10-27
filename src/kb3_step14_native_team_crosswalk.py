"""KB3 Step14: trusted-local read of original PitchAPI team IDs for four pinned fixtures.

Offline and fail-closed: no API calls, TEST, wagers, model fit or approval.
GH Archive confirms historical OpenFootball *schedule* push; the PitchAPI
history was actually acquired October 26, 2026, never historical-prematch PIT.
This module only compares authenticated retrospective native PitchAPI team
IDs/names to public names already observed in independently pushed blobs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from src.kb3_pitch_native import MATCH_ID,TEAM_ID
from src.kb3_split import sha

SAFE_SHA="3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7"
ARCHIVE_ZIP_SHA="301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e"
ARCHIVE_CHAIN_SHA="33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367"
SOURCE_OBSERVED_UTC="2026-10-26T13:17:47.692940Z"
REQUIRED={
    "m_3AMymS":{
        "season":"2024-25","partition":"TRAIN",
        "kickoff_utc":"2024-10-05T16:30:00Z",
        "home":"Everton FC","away":"Newcastle United FC",
        "commit":"5f777dc6e2cd02cdafd1520e81b7e338284fb7a7",
        "push_event_id":"42475053178",
        "push_created_at_utc":"2024-10-02T13:52:44Z",
    },
    "m_4AseJ9":{
        "season":"2025-26","partition":"VALIDATION",
        "kickoff_utc":"2025-08-18T19:00:00Z",
        "home":"Leeds United","away":"Everton FC",
        "commit":"fdca227e6fc8284865254f009e987ce7a70935a0",
        "push_event_id":"52743265113",
        "push_created_at_utc":"2025-07-30T16:20:53Z",
    },
    "m_0lzfjT":{
        "season":"2025-26","partition":"VALIDATION",
        "kickoff_utc":"2025-08-31T15:30:00Z",
        "home":"Liverpool FC","away":"Arsenal FC",
        "commit":"fdca227e6fc8284865254f009e987ce7a70935a0",
        "push_event_id":"52743265113",
        "push_created_at_utc":"2025-07-30T16:20:53Z",
    },
    "m_0JJdwI":{
        "season":"2025-26","partition":"VALIDATION",
        "kickoff_utc":"2025-09-21T13:00:00Z",
        "home":"Sunderland AFC","away":"Aston Villa",
        "commit":"fdca227e6fc8284865254f009e987ce7a70935a0",
        "push_event_id":"52743265113",
        "push_created_at_utc":"2025-07-30T16:20:53Z",
    },
}

class NativeCrosswalkError(ValueError):
    pass

def _utc(value):
    if not isinstance(value,str):
        raise NativeCrosswalkError("INVALID_TIMESTAMP")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise NativeCrosswalkError("INVALID_TIMESTAMP") from exc
    if dt.utcoffset()!=timezone.utc.utcoffset(dt):
        raise NativeCrosswalkError("UTC_EXPECTED")
    return dt

def canonical_team_name(value):
    """Conservative fixed grammar; no fuzzy string or outcome-based match."""
    if not isinstance(value,str) or not value.strip():
        raise NativeCrosswalkError("MISSING_TEAM_NAME")
    text=re.sub(r"[^a-z0-9]+"," ",value.casefold().replace("&"," and ")).strip()
    # Only remove conventional FC/AFC suffixes (never whole team names).
    while text.endswith(" fc") or text.endswith(" afc"):
        text=text.rsplit(" ",1)[0]
    return text

def _verify_public_evidence(safe,blob,clock):
    if safe.get("schema")!="kb3-step12-methodology-v1" or safe.get("training_allowed") is not False:
        raise NativeCrosswalkError("UNTRUSTED_SPLIT")
    if (safe.get("projection_sha256")!=SAFE_SHA or
       sha({k:v for k,v in safe.items() if k!="projection_sha256"})!=SAFE_SHA):
        raise NativeCrosswalkError("SPLIT_SHA_NOT_PINNED")
    if blob.get("schema")!="kb3-step14-historical-blob-clock-crosswalk-audit-v1" or blob.get("gate14_pass") is not False:
        raise NativeCrosswalkError("UNTRUSTED_BLOB_REPORT")
    if clock.get("schema")!="kb3-step14-thirdparty-public-push-clock-v1" or clock.get("gate14_pass") is not False:
        raise NativeCrosswalkError("UNTRUSTED_PUBLIC_CLOCK")
    allowed={r["fixture_id"]:r for r in safe["fixtures"] if r["partition"] in ("TRAIN","VALIDATION")}
    evidence={r["pitch_fixture_id"]:r for r in blob.get("records",[]) if r.get("pitch_fixture_id") in REQUIRED}
    clocks={r["candidate_source_commit_sha"]:r for r in clock.get("records",[])
            if r.get("independent_public_push_time_corroborated")}
    if set(evidence)!=set(REQUIRED):
        raise NativeCrosswalkError("PILOT_EVIDENCE_INCOMPLETE")
    for ident,request in REQUIRED.items():
        x=evidence[ident]
        split=allowed.get(ident)
        if (split is None or split["partition"]!=request["partition"] or
            split["kickoff_utc"]!=request["kickoff_utc"]):
            raise NativeCrosswalkError("NATIVE_ID_NOT_IN_FROZEN_SPLIT")
        matches=x.get("match_by_exact_uk_local_to_utc_kickoff",[])
        if (x.get("partition")!=request["partition"] or
            x.get("season")!=request["season"] or
            x.get("kickoff_utc")!=request["kickoff_utc"] or
            x.get("status")!="ONE_PUBLIC_SCHEDULE_MATCH_BY_KICKOFF_ONLY" or
            x.get("candidate_commit_sha")!=request["commit"] or
            x.get("official_train_eligible") is not False or
            len(matches)!=1 or matches[0] != {
                "home_name_openfootball":request["home"],
                "away_name_openfootball":request["away"],
                "score_present_in_prematch_candidate_blob":False}):
            raise NativeCrosswalkError("PUBLIC_BLOB_CANDIDATE_CHANGED")
        ev=clocks.get(request["commit"])
        if (ev is None or ev.get("server_created_at_utc")!=request["push_created_at_utc"] or
            str(ev.get("server_github_event_id"))!=request["push_event_id"] or
            ev.get("public_branch_ref")!="refs/heads/master" or
            ev.get("public_branch_head_sha")!=request["commit"] or
            _utc(request["push_created_at_utc"])>=_utc(request["kickoff_utc"])):
            raise NativeCrosswalkError("INDEPENDENT_PUBLIC_PUSH_NOT_PINNED")
    return evidence

def _extract_native_matches(receipts):
    """Only choose exact requested native IDs; zero labels exported."""
    expected_sources={"pitchapi:catalog","pitchapi:history:premier-league:2023/2024:matches:played",
                      "pitchapi:history:premier-league:2024/2025:matches:played",
                      "pitchapi:history:premier-league:2025/2026:matches:played"}
    if not isinstance(receipts,list) or len(receipts)!=4 or {r.get("resource") for r in receipts}!=expected_sources:
        raise NativeCrosswalkError("ORIGINAL_NATIVE_RECEIPTS_WRONG")
    found={}
    id_by_team={}
    name_by_team={}
    for source in receipts:
        resource=source["resource"]
        if not resource.startswith("pitchapi:history:"):
            continue
        full_season=resource.split(":")[3]
        begin,end=map(int,full_season.split("/"))
        if end!=begin+1:
            raise NativeCrosswalkError("NATIVE_SOURCE_SEASON_INVALID")
        season=f"{begin}-{end%100:02d}"
        matches=source.get("payload",{}).get("matches")
        if not isinstance(matches,list) or len(matches)!=380:
            raise NativeCrosswalkError("ORIGINAL_NATIVE_SEASON_COUNT_WRONG")
        for row in matches:
            if not isinstance(row,dict):
                raise NativeCrosswalkError("NONDICT_NATIVE_ROW")
            home,away=row.get("home_team"),row.get("away_team")
            if not isinstance(home,dict) or not isinstance(away,dict):
                raise NativeCrosswalkError("TEAM_PAIR_MISSING")
            for t in (home,away):
                if not TEAM_ID.fullmatch(str(t.get("id",""))):
                    raise NativeCrosswalkError("NATIVE_TEAM_ID_INVALID")
                tid=t["id"]
                if tid in name_by_team and canonical_team_name(t["name"])!=name_by_team[tid]:
                    raise NativeCrosswalkError("NATIVE_TEAM_ID_COLLISION")
                name_by_team[tid]=canonical_team_name(t["name"])
            ident=row.get("id")
            if ident not in REQUIRED:
                continue
            if ident in found or not MATCH_ID.fullmatch(str(ident)):
                raise NativeCrosswalkError("DUPLICATE_NATIVE_FIXTURE")
            found[ident]={
                "fixture_id":ident, "season":season,
                "kickoff_utc":row.get("time_utc"),
                "pitch_home_team_id":home["id"],
                "pitch_away_team_id":away["id"],
                "pitch_home_name":home["name"],
                "pitch_away_name":away["name"],
            }
    if set(found)!=set(REQUIRED):
        raise NativeCrosswalkError("NATIVE_FIXTURE_MISSING_IN_ARCHIVE")
    return found

def audit_crosswalk(*,safe,blob,clock,receipts,archive_zip_sha=ARCHIVE_ZIP_SHA,
                    source_chain_sha=ARCHIVE_CHAIN_SHA):
    _verify_public_evidence(safe,blob,clock)
    if archive_zip_sha!=ARCHIVE_ZIP_SHA or source_chain_sha!=ARCHIVE_CHAIN_SHA:
        raise NativeCrosswalkError("ORIGINAL_ARCHIVE_HASH_CHANGED")
    found=_extract_native_matches(receipts)
    results=[]
    for ident,expect in REQUIRED.items():
        r=found[ident]
        pair_ids=(r["pitch_home_team_id"],r["pitch_away_team_id"])
        if len(set(pair_ids))!=2:
            raise NativeCrosswalkError("IDENTICAL_TEAM_IDS")
        kickoff_match=r["kickoff_utc"]==expect["kickoff_utc"]
        name_match=(canonical_team_name(r["pitch_home_name"])==canonical_team_name(expect["home"]) and
                    canonical_team_name(r["pitch_away_name"])==canonical_team_name(expect["away"]))
        role_match=r["season"]==expect["season"]
        valid=kickoff_match and name_match and role_match
        results.append({
            "pitch_fixture_id":ident,
            "official_partition":expect["partition"],
            "pitch_home_team_id":r["pitch_home_team_id"],
            "pitch_away_team_id":r["pitch_away_team_id"],
            "pitch_home_name":r["pitch_home_name"],
            "pitch_away_name":r["pitch_away_name"],
            "public_candidate_home_name":expect["home"],
            "public_candidate_away_name":expect["away"],
            "kickoff_utc":expect["kickoff_utc"],
            "native_kickoff_exact":kickoff_match,
            "both_native_team_names_match_public_candidate":name_match,
            "season_matches":role_match,
            "original_pinned_PitchAPI_native_ids_confirmed":True,
            "external_fixture_identity_crosswalk_confirmed":valid,
            "historical_scheduled_blob_sha":expect["commit"],
            "independent_push_event_id":expect["push_event_id"],
            "historical_PitchAPI_prematch_receipt_exists":False,
            "official_train_allowed":False,
        })
    result={
        "schema":"kb3-step14-local-native-pitchapi-team-pairs-v1",
        "evidence_class":"OWNER_LOCAL_DECRYPT_AUTHENTIC_RETROSPECTIVE_PITCHAPI_RECEIPTS",
        "source_archive_zip_sha256":ARCHIVE_ZIP_SHA,
        "source_chain_sha256":ARCHIVE_CHAIN_SHA,
        "source_observed_utc":SOURCE_OBSERVED_UTC,
        "original_safe_split_sha256":SAFE_SHA,
        "total_checked":len(results),
        "identity_crosswalk_verified_count":sum(x["external_fixture_identity_crosswalk_confirmed"] for x in results),
        "train_verified_identity_count":sum(x["external_fixture_identity_crosswalk_confirmed"] and x["official_partition"]=="TRAIN" for x in results),
        "validation_verified_identity_count":sum(x["external_fixture_identity_crosswalk_confirmed"] and x["official_partition"]=="VALIDATION" for x in results),
        "test_records_accessed":0,"sports_provider_requests":0,
        "result_scores_exported":False,"odds_exported":False,"private_key_exported":False,
        "historical_prematch_PIT_certified":False,
        "production_catboost_training_allowed":False,
        "gate14_pass":False,
        "rows":results,
    }
    result["report_sha256"]=sha(result)
    return result
