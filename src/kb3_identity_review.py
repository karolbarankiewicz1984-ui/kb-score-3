"""Step11: exact PitchAPI↔API-Football evidence and quarantined review queue.

No fuzzy match is EVER auto-approved. A candidate is an investigative hint,
not source identity. Time-zone offsets are normalized before comparing kickoff.
"""
from __future__ import annotations

from datetime import timedelta
import difflib
from scripts.pitchapi_step06_audit import norm
from src.kb3_pit_ledger import as_utc

EXACT_TIME_TOLERANCE=timedelta(minutes=5)
REVIEW_TIME_TOLERANCE=timedelta(hours=3)

def _score_pair(match):
    a,b=match.get("score_home"),match.get("score_away")
    return (a,b) if all(type(x) is int and x>=0 for x in (a,b)) else None

def inspect_match(pitch,football_fixtures):
    """Return a strict approval or a structured reason for human review.

    No name alias, fuzzy similarity, score/date alone or one-candidate fallback
    may be turned into an approved fixture ID.
    """
    try:
        start=as_utc(pitch["time_utc"])
        pscore=_score_pair(pitch)
        pn=(norm((pitch.get("home_team") or {}).get("name")),
            norm((pitch.get("away_team") or {}).get("name")))
    except (KeyError,ValueError,TypeError):
        return {"state":"INVALID_PITCH_IDENTITY","fixture_id":None,
                "review_candidates":[]}
    if not all(pn) or pscore is None or pitch.get("status")!="finished":
        return {"state":"INCOMPLETE_PITCH_IDENTITY","fixture_id":None,
                "review_candidates":[]}

    nearby=[]
    for game in football_fixtures:
        if not isinstance(game,dict):
            continue
        fixture=game.get("fixture") or {}
        teams=game.get("teams") or {}
        fscore=(game.get("goals") or {})
        try:
            kickoff=as_utc(fixture["date"])
        except (KeyError,TypeError,ValueError):
            continue
        if abs(kickoff-start)>REVIEW_TIME_TOLERANCE:
            continue
        if fixture.get("status",{}).get("short")!="FT":
            continue
        fid=fixture.get("id")
        if type(fid) is not int:
            continue
        names=(norm((teams.get("home") or {}).get("name")),
               norm((teams.get("away") or {}).get("name")))
        same_score=(fscore.get("home"),fscore.get("away"))==pscore
        names_exact=names==pn
        dt=abs(kickoff-start)
        sim=(difflib.SequenceMatcher(None,pn[0],names[0]).ratio(),
             difflib.SequenceMatcher(None,pn[1],names[1]).ratio())
        nearby.append({"fixture_id":fid,"exact_time":dt<=EXACT_TIME_TOLERANCE,
                       "exact_names":names_exact,"same_score":same_score,
                       "similar_names":min(sim)>=0.70,
                       "minute_gap":int(dt.total_seconds()//60)})

    approved=[g for g in nearby if g["exact_time"] and g["exact_names"] and g["same_score"]]
    if len(approved)==1:
        return {"state":"EXACT_TIME_NAMES_SCORE_FT",
                "fixture_id":approved[0]["fixture_id"],
                "review_candidates":[]}
    if len(approved)>1:
        return {"state":"MULTIPLE_EXACT_FIXTURES_QUARANTINED",
                "fixture_id":None,
                "review_candidates":[g["fixture_id"] for g in approved]}

    same_score=[x for x in nearby if x["same_score"] and x["exact_time"]]
    plausible=[x for x in same_score if x["similar_names"]]
    if len(plausible)==1:
        state="ALIAS_REVIEW_REQUIRED"
    elif len(plausible)>1:
        state="MULTIPLE_REVIEW_CANDIDATES"
    elif same_score:
        state="NAME_DISAGREEMENT_OR_AMBIGUITY"
    elif any(x["exact_time"] for x in nearby):
        state="SCORE_DISAGREEMENT"
    elif nearby:
        state="KICKOFF_DISAGREEMENT"
    else:
        state="NO_FOOTBALL_FIXTURE_IN_WINDOW"
    review=plausible if plausible else same_score
    return {"state":state,"fixture_id":None,
            "review_candidates":[x["fixture_id"] for x in review],
            "review_only":True}

def aggregate_review(resolutions):
    counts={}
    for obj in resolutions:
        state=obj["state"]
        counts[state]=counts.get(state,0)+1
    return {"n":len(resolutions),"states":dict(sorted(counts.items())),
            "strict_approved":counts.get("EXACT_TIME_NAMES_SCORE_FT",0),
            "auto_approved_aliases":0,"training_allowed":False}
