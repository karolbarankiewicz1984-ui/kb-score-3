"""Read-only feasibility audit: can PitchAPI replace two-provider fixture/xG pairing?

No API-Football requests. No data migration. This is an intentionally tiny
shadow-mode snapshot; only safe aggregate counts and hashes leave CI.
Historical API payload fetched now remains RETROSPECTIVE, NOT PIT proof.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone,timedelta
import argparse
import json
import os
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain,norm
from src.kb3_pitch_native import check_season,verify_native_shots

SEASONS=("2023/2024","2024/2025","2026/2027")
MAX_CALLS=9
SHOTS_SAMPLE=5

def unwrap(obj,outer_key):
    v=to_plain(obj)
    if isinstance(v,dict):
        if isinstance(v.get(outer_key),list):return v[outer_key]
        if isinstance(v.get("data"),dict) and isinstance(v["data"].get(outer_key),list):
            return v["data"][outer_key]
    raise ValueError("PITCH_SDK_UNEXPECTED_RESPONSE_SHAPE")

def audit():
    from pitchapi import PitchAPI
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:raise ValueError("MISSING_PITCHAPI_KEY")
    api=PitchAPI(api_key=key)
    calls=0
    catalog=unwrap(api.leagues.list(),"leagues");calls+=1
    pl=[l for l in catalog if norm(l.get("name")).replace(" ","")=="premierleague"
        and str(l.get("country_code") or "").upper()=="ENG"]
    if len(pl)!=1:raise ValueError("PITCH_PL_LEAGUE_NOT_UNIQUE")
    league=pl[0]
    available=league.get("seasons") or []
    if not all(year in available for year in SEASONS):
        raise ValueError("PITCH_MISSING_REQUIRED_SEASON")
    found_names=[(str(l.get("name") or "")) for l in catalog]
    # Other leagues: informational only, never assume xG completeness.
    indicative={
        "top_five_candidate_names":sum(any(token in norm(n) for n in
          ("premier league","la liga","serie a","bundesliga","ligue 1"))
          for name in found_names for n in [name]),
        "uefa_europa_name_hits":sum("europa" in norm(name) for name in found_names),
        "uefa_conference_name_hits":sum("conference" in norm(name) for name in found_names),
    }
    evidence={}
    current=[]
    for season in SEASONS:
        # status=all is essential. Default PitchAPI lists PLAYED only.
        # SDK method supports the full season status filter per public docs.
        raw=api.leagues.matches(league["id"],season=season,
                                status="all" if season=="2026/2027" else "played")
        calls+=1
        items=unwrap(raw,"matches")
        info=check_season(items,season,expected_count=380,
                          require_upcoming=season=="2026/2027")
        evidence[season]=info
        if season=="2026/2027":current=items
    played=sorted([x for x in current if x.get("status")=="finished"],
                  key=lambda x:(x["time_utc"],x["id"]))
    if len(played)<SHOTS_SAMPLE:raise ValueError("PITCH_NOT_ENOUGH_FINISHED")
    indexes=[(2*i+1)*len(played)//(2*SHOTS_SAMPLE) for i in range(SHOTS_SAMPLE)]
    chosen=[played[i] for i in indexes]
    shots_states=Counter()
    xg_ready=0
    captured=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    for match in chosen:
        obj=to_plain(api.matches.shots(match["id"]));calls+=1
        wrapped={"data":obj["data"] if isinstance(obj,dict) and
                                  isinstance(obj.get("data"),dict) else obj}
        item=verify_native_shots(match,wrapped,observed_at_utc=captured)
        shots_states[item["shot_state"]]+=1
        xg_ready+=int(item["shot_state"]=="COMPLETE_SHOT_XG")
    if calls>MAX_CALLS:raise ValueError("PITCH_NATIVE_CALL_BUDGET_EXCEEDED")
    return {
       "schema":"kb3-step11-pitchapi-single-provider-feasibility-v1",
       "observed_at_utc":datetime.now(timezone.utc).isoformat(),
       "provider":"PitchAPI",
       "scope":"Premier League 2023/24, 2024/25, 2026/27",
       "season_evidence":evidence,
       "catalog_total_leagues":len(catalog),
       "competition_indicators":indicative,
       "shot_feed_sample":SHOTS_SAMPLE,
       "shot_feed_complete":xg_ready,
       "shot_feed_status_counts":dict(sorted(shots_states.items())),
       "api_football_requests":0,
       "pitchapi_requests":calls,
       "request_ceiling":MAX_CALLS,
       "provider_match_id_directly_links_fixture_result_and_xg":True,
       "foreign_team_name_aliases_needed":False,
       "odds_endpoint_confirmed":False,
       "future_schedule_verified_with_status_all":True,
       "historical_prematch_proof":False,
       "raw_payloads_persisted":False,
       "shadow_only_no_migration":True,
       "training_allowed":False,
       "production_switch_approved":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    a=p.parse_args()
    try:
        result=audit()
        target=Path(a.out)
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("x",encoding="utf8") as stream:
            json.dump(result,stream,indent=2,sort_keys=True)
            stream.write("\n")
        print("KB3_SINGLE_PROVIDER_SHADOW_PASS",json.dumps(result,sort_keys=True))
    except Exception as exc:
        # Raw HTTP/SDK error descriptions may accidentally contain private data.
        print("KB3_SINGLE_PROVIDER_SHADOW_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
