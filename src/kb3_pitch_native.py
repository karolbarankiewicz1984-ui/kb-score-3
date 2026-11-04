"""Step11 PitchAPI-native candidate source: *no cross-provider fixture matching*.

This adapter does not train or produce forecasts. Source match/team IDs remain
opaque across all fixture, shot and pre-match records. Reject missing/ambiguous
identity and never substitute 0 for unavailable xG. Provider timestamps are
capture timestamps, NOT original publication proof.
"""
from __future__ import annotations
from collections import Counter
from datetime import timedelta
import hashlib
import json
import math
import re

from src.kb3_pit_ledger import as_utc, canonical
from scripts.pitchapi_step06_audit import parse_shots,parse_shots_v1_archive

MATCH_ID=re.compile(r"^m_[A-Za-z0-9]{6}$")
TEAM_ID=re.compile(r"^t_[A-Za-z0-9]{6}$")
FINISHED="finished"
FUTURE={"not_started","upcoming","scheduled"}
LAG=timedelta(hours=3)


def check_season(match_list,season,*,expected_count=380,require_upcoming=False):
    if not isinstance(match_list,list):
        raise ValueError("PITCH_MATCHES_NOT_A_LIST")
    by_id={}; by_team={}; counts=Counter()
    for match in match_list:
        if not isinstance(match,dict):
            raise ValueError("PITCH_MATCH_NOT_OBJECT")
        mid=match.get("id")
        if not isinstance(mid,str) or not MATCH_ID.fullmatch(mid) or mid in by_id:
            raise ValueError("PITCH_DUPLICATE_OR_INVALID_MATCH_ID")
        team_ids=[]
        for field in ("home_team","away_team"):
            value=match.get(field)
            if not isinstance(value,dict) or not isinstance(value.get("id"),str) or not TEAM_ID.fullmatch(value["id"]):
                raise ValueError("PITCH_TEAM_ID_MISSING")
            if not isinstance(value.get("name"),str) or not value["name"].strip():
                raise ValueError("PITCH_TEAM_NAME_MISSING")
            previous=by_team.setdefault(value["id"],value["name"])
            if previous!=value["name"]:
                # Stable IDs, names may change, but never silently overwrite a team name.
                raise ValueError("PITCH_TEAM_IDENTITY_NAME_CHANGED")
            team_ids.append(value["id"])
        if len(set(team_ids))!=2:
            raise ValueError("PITCH_SAME_TEAM_BOTH_SIDES")
        kickoff=as_utc(match.get("time_utc"))
        year=int(season.split("/")[0])
        if not(year<=kickoff.year<=year+1):
            raise ValueError("PITCH_KICKOFF_OUTSIDE_SEASON")
        status=match.get("status")
        if status!=FINISHED and status not in FUTURE:
            raise ValueError("PITCH_UNKNOWN_FIXTURE_STATUS")
        gh,ga=match.get("score_home"),match.get("score_away")
        if status==FINISHED:
            if not all(type(v) is int and v>=0 for v in (gh,ga)):
                raise ValueError("PITCH_FINISHED_WITHOUT_FINAL_SCORE")
        elif gh is not None or ga is not None:
            raise ValueError("PITCH_FUTURE_CONTAINS_FINAL_SCORE")
        counts[status]+=1
        by_id[mid]=match
    if expected_count is not None and len(by_id)!=expected_count:
        raise ValueError("PITCH_SEASON_INCOMPLETE")
    if require_upcoming and not any(s in counts for s in FUTURE):
        raise ValueError("PITCH_NO_UPCOMING_FIXTURES")
    return {"season":season,"fixtures":len(by_id),"unique_provider_match_ids":len(by_id),
            "unique_team_ids":len(by_team),"status_counts":dict(sorted(counts.items())),
            "match_digest_sha256":hashlib.sha256(canonical(
                [by_id[mid] for mid in sorted(by_id)])).hexdigest(),
            "results_and_schedule_same_provider":True,
            "cross_provider_join_needed":False,
            "training_allowed":False}


def _verify_native_shots_v1(match,shot_feed,*,observed_at_utc):
    """Validate shot xG under EXACT SAME native match ID + two team IDs."""
    if not isinstance(match,dict) or match.get("status")!=FINISHED:
        raise ValueError("PITCH_XG_REQUIRES_FINISHED_MATCH")
    mid=match.get("id")
    if not isinstance(mid,str) or not MATCH_ID.fullmatch(mid):
        raise ValueError("PITCH_MATCH_ID_INVALID")
    observed=as_utc(observed_at_utc)
    if observed<as_utc(match.get("time_utc"))+LAG:
        raise ValueError("PITCH_SHOTS_NOT_AFTER_MATCH")
    if not isinstance(shot_feed,dict):
        raise ValueError("PITCH_SHOT_RESPONSE_INVALID")
    body=shot_feed.get("data") or {}
    if not isinstance(body,dict) or body.get("match_id")!=mid:
        raise ValueError("PITCH_SHOT_FIXTURE_ID_MISMATCH")
    home,away=match["home_team"]["id"],match["away_team"]["id"]
    parsed=parse_shots_v1_archive(shot_feed,home,away)
    if parsed.get("state")!="COMPLETE_SHOT_XG":
        return {"match_id":mid,"xg_home":None,"xg_away":None,
                "shot_state":parsed.get("state"),
                "captured_at_utc":observed_at_utc,
                "source_provider_published_at_utc":None,
                "training_allowed":False}
    gh,ga=parsed.get("home_xg_sum"),parsed.get("away_xg_sum")
    if not all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in (gh,ga)):
        raise ValueError("PITCH_NONFINITE_SHOT_XG")
    return {"match_id":mid,"xg_home":gh,"xg_away":ga,
            "shot_state":"COMPLETE_SHOT_XG",
            "captured_at_utc":observed_at_utc,
            "source_provider_published_at_utc":None,
            "training_allowed":False}

def verify_native_shots(match,shot_feed,*,observed_at_utc,stats_payload=None):
    """Validate new observations; an unpaired source cannot certify xG."""
    result=_verify_native_shots_v1(match,shot_feed,observed_at_utc=observed_at_utc)
    parsed=parse_shots(shot_feed,match["home_team"]["id"],match["away_team"]["id"],
                       stats_payload=stats_payload)
    result.update(shot_state=parsed["state"],xg_home=parsed["home_xg_sum"],
                  xg_away=parsed["away_xg_sum"])
    if "reason" in parsed:
        result["reason"]=parsed["reason"]
    return result
