"""One-off supplemental PitchAPI UEFA and discipline data coverage audit.

Informational probe only; no blanket claims about all competitions or betting
odds. No API-Football requests, no xG cross-provider mappings or training.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from scripts.pitchapi_step06_audit import to_plain,norm

MAX_CALLS=5


def choose(league_list,token,season="2026/2027"):
    matching=[l for l in league_list if token in norm(l.get("name"))]
    active=[l for l in matching if season in (l.get("seasons") or [])]
    if len(active)!=1:
        raise ValueError("UEFA_CATALOG_SCOPE_NOT_UNIQUE")
    return active[0]


def audit():
    from pitchapi import PitchAPI
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:raise ValueError("PITCH_KEY_MISSING")
    sdk=PitchAPI(api_key=key)
    calls=0
    catalog=to_plain(sdk.leagues.list());calls+=1
    leagues=catalog.get("leagues") if isinstance(catalog,dict) else None
    if not isinstance(leagues,list):
        raise ValueError("CATALOG_SHAPE_INVALID")
    coverage={}
    for flag,term in (("europa_league","europa league"),
                      ("conference_league","conference league")):
        target=choose(leagues,term)
        rows=to_plain(sdk.leagues.matches(target["id"],
                    season="2026/2027",status="all"))
        calls+=1
        matches=rows.get("matches") if isinstance(rows,dict) else None
        if not isinstance(matches,list) or not matches:
            raise ValueError("UEFA_CURRENT_SEASON_FIXTURES_MISSING")
        keys=[m.get("id") for m in matches]
        if len(set(keys))!=len(keys):
            raise ValueError("DUPLICATE_UEFA_PROVIDER_MATCH_IDS")
        coverage[flag]={"league_source":"PitchAPI",
               "fixture_count":len(matches),
               "unique_native_ids":len(set(keys)),
               "scheduled_or_unplayed_count":sum(
                   m.get("status") in ("not_started","scheduled","upcoming")
                   for m in matches),
               "finished_count":sum(m.get("status")=="finished"
                                    for m in matches),
               "league_name_confirmed":True,
               "historical_xg_coverage_certified":False}
    pl=[l for l in leagues if norm(l.get("name"))=="premier league"
        and str(l.get("country_code") or "").upper()=="ENG"
        and "2026/2027" in (l.get("seasons") or [])]
    if len(pl)!=1:
        raise ValueError("PL_CATALOG_ID_NOT_UNIQUE")
    pl=pl[0]
    obj=to_plain(sdk.leagues.matches(pl["id"],season="2026/2027",status="played"))
    calls+=1
    matches=obj.get("matches") if isinstance(obj,dict) else None
    if not isinstance(matches,list) or not matches:
        raise ValueError("PL_FINISHED_MATCHES_MISSING")
    sorted_matches=sorted([m for m in matches if m.get("status")=="finished"],
                          key=lambda m:(m["time_utc"],m["id"]))
    if not sorted_matches:
        raise ValueError("PL_NO_COMPLETED_GAMES")
    one=sorted_matches[len(sorted_matches)//2]
    stats=to_plain(sdk.matches.stats(one["id"]));calls+=1
    if not isinstance(stats,dict):
        raise ValueError("PITCH_STATS_RESPONSE_SHAPE_INVALID")
    periods=stats.get("periods") or []
    keys=set()
    if not isinstance(periods,list):
        raise ValueError("PITCH_STATS_PERIODS_MISSING")
    for period in periods:
        if not isinstance(period,dict):continue
        for group in period.get("groups",[]) or []:
            if not isinstance(group,dict):continue
            for item in group.get("items",[]) or []:
                if isinstance(item,dict) and isinstance(item.get("key"),str):
                    keys.add(item["key"])
    if calls>MAX_CALLS:
        raise ValueError("OVER_REQUEST_BUDGET")
    return {"schema":"kb3-step11-native-uefa-discipline-v1",
        "provider":"PitchAPI",
        "competition_2026_27":coverage,
        "pl_match_stats_key_count":len(keys),
        "observed_fouls_stats_keys":sorted(k for k in keys if "foul" in k.lower()),
        "observed_cards_stats_keys":sorted(k for k in keys if "card" in k.lower()),
        "odds_endpoint_documented":False,
        "pitchapi_requests":calls,"max_requests":MAX_CALLS,
        "api_football_requests":0,
        "league_level_xg_completeness_not_proven":True,
        "initial_provider_publication_known":False,
        "shadow_mode":True,"training_allowed":False}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    try:
        result=audit()
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("x",encoding="utf8") as fd:
            json.dump(result,fd,indent=2,sort_keys=True);fd.write("\n")
        print("KB3_PITCH_NATIVE_UEFA_PASS",json.dumps(result,sort_keys=True))
    except Exception as err:
        safe_codes={"UEFA_CATALOG_SCOPE_NOT_UNIQUE","PL_CATALOG_ID_NOT_UNIQUE",
          "UEFA_CURRENT_SEASON_FIXTURES_MISSING","DUPLICATE_UEFA_PROVIDER_MATCH_IDS",
          "CATALOG_SHAPE_INVALID","PL_FINISHED_MATCHES_MISSING","PL_NO_COMPLETED_GAMES",
          "PITCH_STATS_RESPONSE_SHAPE_INVALID","PITCH_STATS_PERIODS_MISSING",
          "OVER_REQUEST_BUDGET"}
        reason=str(err) if isinstance(err,ValueError) and str(err) in safe_codes else type(err).__name__
        print("KB3_PITCH_NATIVE_UEFA_BLOCKED",reason)
        raise SystemExit(3)
if __name__=="__main__":
    main()
