"""Independent current public historic-season fixture projection (NO SCORE, NO TEST).

This October 2026 download can corroborate historical event identities, but
MUST NEVER be interpreted as a match-time PIT source for 2023-2026. Exact
Source SHA hashes are recorded; ONLY whitelisted name/date/time are exported.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
from urllib.request import Request,urlopen
from src.kb3_split import sha

SEASONS=("2023-24","2024-25","2025-26")
SOURCE="https://raw.githubusercontent.com/openfootball/football.json/master/{season}/en.1.json"
SCHEMA="kb3-step14-public-historical-1140-targetfree-identity-reference-v1"

class PublicReferenceError(ValueError):pass

def project(fetcher=None,observed_at_utc=None):
    if fetcher is None:
        def fetcher(url):
            req=Request(url,headers={"User-Agent":"KB3-step14-targetfree-identity-audit"})
            with urlopen(req,timeout=30) as f:
                return f.read(2000001)
    when=observed_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    if not isinstance(when,str) or not when.endswith("Z") or not when.startswith("2026-"):
        raise PublicReferenceError("HISTORIC_RESEARCH_CAPTURE_CLOCK_REQUIRED")
    seasons={}
    for season in SEASONS:
        raw=fetcher(SOURCE.format(season=season))
        if type(raw) is not bytes or not 2000<len(raw)<=2000000:
            raise PublicReferenceError("UNEXPECTED_SOURCE_BYTES")
        data=json.loads(raw)
        if type(data) is not dict or type(data.get("matches")) is not list or len(data["matches"])!=380:
            raise PublicReferenceError("PUBLIC_LEAGUE_COUNT_WRONG")
        rows=[]
        seen=set()
        for x in data["matches"]:
            if type(x) is not dict:
                raise PublicReferenceError("PUBLIC_GAME_FORMAT")
            day=x.get("date")
            t=x.get("time")
            h=x.get("team1")
            a=x.get("team2")
            if not all(type(y) is str and y.strip() and len(y)<=128 for y in (day,h,a)):
                raise PublicReferenceError("PUBLIC_GAME_REQUIRED_FIELD")
            if t is not None and (type(t) is not str or len(t)!=5 or t[2]!=":"):
                raise PublicReferenceError("PUBLIC_KICKOFF_LOCAL_TIME_WRONG")
            if h==a or (h,a) in seen:
                raise PublicReferenceError("PUBLIC_DUPLICATE_HOME_AWAY")
            seen.add((h,a))
            # No target score, status, odds, xG, raw match digest or bookmaker.
            rows.append({"date":day,"time_london":t,"home_name":h,"away_name":a})
        rows.sort(key=lambda y:(y["date"],y["home_name"],y["away_name"]))
        seasons[season]={"reference_matches":len(rows),
                         "original_source_sha256_AUDIT_ONLY":hashlib.sha256(raw).hexdigest(),
                         "fixtures_target_free":rows}
    result={
        "schema":SCHEMA,"public_provider":"openfootball/football.json",
        "actual_observed_at_utc":when,
        "observation_is_retrospective_not_2023_2026_pit":True,
        "full_coverage_historical_season_fixtures":1140,
        "test_2026_2027_not_downloaded":True,
        "result_labels_in_projection":False,"odds_in_projection":False,
        "xg_in_projection":False,
        "no_prematch_feature_release":True,
        "source_seasons":seasons,
        "training_allowed":False,"gate14_pass":False,
    }
    result["projection_sha256"]=sha(result)
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    args=p.parse_args();r=project()
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():raise PublicReferenceError("REFERENCE_ALREADY_EXISTS")
    dest.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"season_counts":{k:v["reference_matches"] for k,v in r["source_seasons"].items()},
         "projection_sha256":r["projection_sha256"],"actual_observed_at_utc":r["actual_observed_at_utc"],
         "training_allowed":r["training_allowed"]},sort_keys=True))
