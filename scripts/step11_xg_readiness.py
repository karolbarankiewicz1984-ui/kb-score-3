"""Step11: small read-only xG readiness probe, no fixture/xG rows exported.

Two finished seasons, at most 16 PitchAPI requests + 2 API-Football
requests. This assesses quality and strict ID matching only; neither a
point-in-time snapshot nor an xG import, and NEVER training eligibility.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from scripts.pitchapi_step06_audit import (
    Client,PITCH,FOOTBALL,norm,parse_shots,find_af_match
)

YEARS=(2023,2024)
SELECTED_PER_YEAR=6
PITCH_BUDGET=16     # catalog + two season listings + up to twelve shot feeds
FOOTBALL_BUDGET=2  # league-season lists only

def select_completed(matches, n=SELECTED_PER_YEAR):
    if n < 1 or not isinstance(matches,list):
        return []
    qualified=sorted(
        (m for m in matches if isinstance(m,dict)
         and m.get("status")=="finished" and isinstance(m.get("id"),str)
         and m["id"].startswith("m_") and isinstance(m.get("time_utc"),str)
         and isinstance(m.get("home_team"),dict) and isinstance(m.get("away_team"),dict)),
        key=lambda m:(m["time_utc"],m["id"]))
    if not qualified:
        return []
    if len(qualified)<=n:
        return qualified
    indexes=sorted({(len(qualified)-1)*i//(n-1) for i in range(n)}) if n>1 else [len(qualified)//2]
    return [qualified[i] for i in indexes]

def probe():
    pitch=Client(PITCH,"PITCHAPI_API_KEY","X-API-KEY",PITCH_BUDGET)
    football=Client(FOOTBALL,"API_FOOTBALL_KEY","x-apisports-key",FOOTBALL_BUDGET)
    catalog=pitch.get("/v1/leagues")
    leagues=(catalog or {}).get("data",{}).get("leagues")
    if not isinstance(leagues,list):
        raise ValueError("PITCH_CATALOG_UNAVAILABLE")
    pl=[l for l in leagues if norm(l.get("name")).replace(" ","")=="premierleague"
        and (l.get("country_code") or "").upper()=="ENG"]
    if len(pl)!=1:
        raise ValueError("PITCH_PREMIER_LEAGUE_AMBIGUOUS")
    league=pl[0]
    out={"schema":"kb3-step11-xg-readiness-v1",
         "run_utc":datetime.now(timezone.utc).isoformat(),
         "seasons":[],"provider":"PitchAPI shot-xG + API-Football fixture ID check",
         "point_in_time_verified":False,"historical_xg_availability_verified":False,
         "historical_xg_imported":False,"training_allowed":False,
         "trained_model":False,"scope":"12 selected matches, two seasons, not full coverage",
         "warnings":["Historical xG collected now cannot prove historic availability",
                     "Aliases are not approved as exact matches",
                     "Raw shot records and results are never published by this audit"]}
    for year in YEARS:
        season=f"{year}/{year+1}"
        if season not in (league.get("seasons") or []):
            raise ValueError("PITCH_SEASON_MISSING")
        listing=pitch.get(f"/v1/leagues/{league['id']}/matches",season=season)
        matches=(listing or {}).get("data",{}).get("matches")
        if not isinstance(matches,list):
            raise ValueError("PITCH_MATCH_LIST_MISSING")
        fixtures=football.get("/fixtures",league=39,season=year)
        af=(fixtures or {}).get("response")
        if not isinstance(af,list):
            raise ValueError("FOOTBALL_MATCH_LIST_MISSING")
        chosen=select_completed(matches)
        if len(chosen)!=SELECTED_PER_YEAR:
            raise ValueError("INSUFFICIENT_PLAYED_MATCHES")
        counts={"selected":len(chosen),"xg_complete":0,"xg_incomplete":0,
                "id_exact":0,"id_unverified":0,"xg_with_exact_id":0,
                "xg_without_certified_earlier_publication":0}
        source_hash=hashlib.sha256()
        for item in chosen:
            hid=(item["home_team"] or {}).get("id")
            aid=(item["away_team"] or {}).get("id")
            if not hid or not aid or hid==aid:
                raise ValueError("INVALID_PITCH_TEAM_IDS")
            shots=pitch.get(f"/v1/matches/{item['id']}/shots")
            result=parse_shots(shots,hid,aid)
            matching=find_af_match(item,af)
            is_complete=result.get("state")=="COMPLETE_SHOT_XG"
            is_exact=matching.get("state")=="EXACT_NAMES_DATE_SCORE"
            counts["xg_complete"]+=int(is_complete)
            counts["xg_incomplete"]+=int(not is_complete)
            counts["id_exact"]+=int(is_exact)
            counts["id_unverified"]+=int(not is_exact)
            counts["xg_with_exact_id"]+=int(is_complete and is_exact)
            counts["xg_without_certified_earlier_publication"]+=int(is_complete)
            source_hash.update(json.dumps(
                {"fixture_id":matching.get("api_football_fixture_id") if is_exact else None,
                 "pitch_match_id":item["id"],"xg":result},
                sort_keys=True,default=str).encode())
        out["seasons"].append({"start_year":year,"pitch_finished_listed":
                               sum(m.get("status")=="finished" for m in matches if isinstance(m,dict)),
                               "counts":counts,"sample_digest":source_hash.hexdigest()})
    out["requests"]={"pitchapi":pitch.calls,"pitch_ceiling":PITCH_BUDGET,
                     "api_football":football.calls,"football_ceiling":FOOTBALL_BUDGET}
    out["source_failures"]={"pitchapi_count":len(pitch.errors),
                            "api_football_count":len(football.errors)}
    out["xg_ready_for_historical_verified_mode"]=False
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    try:
        out=probe()
        target=Path(args.out)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf8")
        print("STEP11_XG_READINESS",json.dumps(
          {"seasons":out["seasons"],"requests":out["requests"],
           "point_in_time_verified":False,"training_allowed":False},
          sort_keys=True))
    except Exception as exc:
        # Never print full provider exception, tokens or response payloads.
        print("STEP11_XG_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":
    main()
