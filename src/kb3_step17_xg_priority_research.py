"""Experimental NO-API, no-lookahead ranking of native xG predecessor matches.

Research only: does not modify existing Step17 collector or schedule.
Uses the same already observed fixture groups and at most eight pair requests,
prioritizing actual missing last-five matches (never last-five available xG).
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone,timedelta

COUNTRIES=("ESP","ITA","GER","FRA","NED","BEL","TUR","POL")

def _utc(s):
    d=s if isinstance(s,datetime) else datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None:
        raise ValueError("NAIVE_UTC_TIME")
    return d.astimezone(timezone.utc)

def score_missing_last5(groups,known,at):
    at=_utc(at)
    scores=defaultdict(float)
    uses=defaultdict(int)
    candidates={}
    for country in COUNTRIES:
        part=groups.get(country,{})
        history=[m for m in part.get("history",())
                 if m.get("status")=="finished"
                 and _utc(m["time_utc"])+timedelta(hours=3)<=at]
        ids={m["id"] for m in history}
        if len(ids)!=len(history):
            raise ValueError("DUPLICATE_HISTORY_MATCH_ID")
        futures=[m for m in part.get("future",())
                 if m.get("status") in ("scheduled","not_started","upcoming")
                 and m.get("score_home") is None and m.get("score_away") is None
                 and _utc(m["time_utc"])>at+timedelta(minutes=90)]
        for target in futures:
            kickoff=_utc(target["time_utc"])
            hours=max(0.0,(kickoff-at).total_seconds()/3600.)
            urgency=1./(1.+hours/48.)
            for side in ("home_team","away_team"):
                team=target[side]["id"]
                prior=sorted((m for m in history
                   if team in (m["home_team"]["id"],m["away_team"]["id"])
                   and _utc(m["time_utc"])<kickoff),
                   key=lambda m:(m["time_utc"],m["id"]),reverse=True)[:5]
                missing=[m for m in prior if (country,m["id"]) not in known]
                if not missing:continue
                # Reward progress toward complete exact last-five team form.
                benefit=urgency/(len(missing)**2)
                for m in missing:
                    key=country,m["id"]
                    scores[key]+=benefit
                    uses[key]+=1
                    candidates[key]=m
    return scores,uses,candidates

def ranked_eight(groups,known,at,*,budget=8,per_league=1):
    """Research alternative to latest-finished-per-league, no live activation."""
    if type(budget) is not int or not 0<=budget<=8:
        raise ValueError("XG_PAIRS_BUDGET_EXCEEDED")
    if type(per_league) is not int or not 1<=per_league<=8:
        raise ValueError("XG_PER_LEAGUE_BUDGET_INVALID")
    scores,uses,rows=score_missing_last5(groups,known,at)
    counts=defaultdict(int)
    selected=[]
    for key in sorted(rows,key=lambda k:(-scores[k],-uses[k],
                      -_utc(rows[k]["time_utc"]).timestamp(),k)):
        country,mid=key
        if counts[country]>=per_league:continue
        selected.append((country,rows[key]))
        counts[country]+=1
        if len(selected)==budget:break
    return selected,{"candidates":len(rows),"selected_pairs":len(selected),
       "max_provider_calls":17+2*budget,
       "score_missing_last5":sum(scores[(c,m["id"])] for c,m in selected),
       "no_network":True,"training_allowed":False,"activated_in_live":False}

def projected_last5_coverage(groups,known,at):
    """Strict counterfactual coverage if listed prior xG pairs were already observed.

    No call, no provider-success claim, no backdating, no skipping missing games.
    """
    at=_utc(at)
    scanned=complete=0
    for country in COUNTRIES:
        part=groups.get(country,{})
        history=[m for m in part.get("history",())
                 if m.get("status")=="finished"
                 and _utc(m["time_utc"])+timedelta(hours=3)<=at]
        for target in part.get("future",()):
            kickoff=_utc(target["time_utc"])
            if kickoff<=at+timedelta(minutes=90):
                continue
            scanned+=1
            sides=[]
            for side in ("home_team","away_team"):
                tid=target[side]["id"]
                prior=sorted((m for m in history
                   if _utc(m["time_utc"])<kickoff
                   and tid in (m["home_team"]["id"],m["away_team"]["id"])),
                   key=lambda m:(m["time_utc"],m["id"]),reverse=True)[:5]
                sides.append(len(prior)==5 and
                             all((country,m["id"]) in known for m in prior))
            complete+=int(all(sides))
    return {"targets":scanned,"strict_complete_last5":complete}

def compare_counterfactual_selection(groups,known,at,baseline,experimental):
    """Ceiling-only comparison: assumes EVERY selected shots/stats pair validates."""
    original=projected_last5_coverage(groups,known,at)
    old=projected_last5_coverage(groups,
        known|{(country,m["id"]) for country,m in baseline},at)
    new=projected_last5_coverage(groups,
        known|{(country,m["id"]) for country,m in experimental},at)
    if original["targets"]!=old["targets"] or old["targets"]!=new["targets"]:
        raise ValueError("PROJECTED_TARGET_SCOPE_CHANGED")
    return {"current_verified_last5":original["strict_complete_last5"],
            "baseline_if_all_selected_xg_pairs_validate":old["strict_complete_last5"],
            "experimental_if_all_selected_xg_pairs_validate":new["strict_complete_last5"],
            "counterfactual_gain_if_all_valid":new["strict_complete_last5"]-old["strict_complete_last5"],
            "targets":original["targets"],
            "only_a_theoretical_ceiling_not_observed_gain":True,
            "additional_provider_calls":0,
            "model_fit_or_promotion":False}
