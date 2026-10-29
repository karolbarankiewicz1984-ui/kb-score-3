"""One-shot read-only PitchAPI league expansion feasibility audit for KB3 Step16.

No model deployment, forecast freeze, historical PIT claim, TEST access, new
subscription or source data disclosure. Candidate league seasons only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.pitchapi_step06_audit import to_plain
from scripts.step14_three_league_pitchapi_actual_audit import CURRENT, PREVIOUS
from src.kb3_pit_ledger import as_utc
from src.kb3_step14_pitchapi_xg_semantics import parse_native_shots, parse_native_team_stats

SCHEMA = "kb3-step16-pitchapi-additional-leagues-readonly-feasibility-v1"
MAX_CALLS = 29  # 1 catalogue + 2*7 seasons + 2*7 sample shots/stats
# Premier League is not in this allowlist: protected 2026/27 TEST.
CANDIDATES = (
    ("FRA", "Ligue 1", ("ligue1", "ligue1mcdonalds")),
    ("NED", "Eredivisie", ("eredivisie",)),
    ("POR", "Primeira Liga", ("primeiraliga", "ligaportugalbetclic")),
    ("BEL", "Belgian Pro League", ("jupilerproleague", "proleague", "firstdivisiona", "belgianproleague")),
    ("TUR", "Super Lig", ("superlig", "trendyolsuperlig")),
    ("POL", "Ekstraklasa", ("ekstraklasa", "pkobpekstraklasa")),
    ("ENG", "Championship", ("championship", "eflchampionship")),
)

class LeagueAuditError(ValueError):
    pass

def norm(s):
    return "".join(c for c in str(s).casefold() if c.isalnum())

def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()

def match_catalog(catalog):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("leagues"), list):
        raise LeagueAuditError("INVALID_REAL_LEAGUE_CATALOG")
    result = []
    used = set()
    for country, title, aliases in CANDIDATES:
        matches = [item for item in catalog["leagues"]
                   if isinstance(item, dict)
                   and str(item.get("country_code", "")).upper() == country
                   and norm(item.get("name", "")) in aliases]
        eligible = [item for item in matches
                    if CURRENT in (item.get("seasons") or [])
                    and PREVIOUS in (item.get("seasons") or [])]
        if len(eligible) > 1:
            raise LeagueAuditError("DUPLICATE_CANDIDATE_" + country)
        if not eligible:
            result.append({"country":country, "league":title,
                           "catalog_both_seasons":False, "reason":"NOT_IN_CATALOG_BOTH_SEASONS"})
            continue
        obj = eligible[0]
        lid = obj.get("id")
        if not isinstance(lid, str) or not lid.startswith("l_") or lid in used:
            raise LeagueAuditError("BAD_PROVIDER_LEAGUE_ID")
        used.add(lid)
        result.append({"country":country, "league":title,
                       "catalog_both_seasons":True,
                       "provider_league_id":lid,
                       "advertised_free": obj.get("is_free") if type(obj.get("is_free")) is bool else None})
    return result

def compact_season(games, season, current):
    if not isinstance(games, list) or not games:
        return {"valid":False,"reason":"NO_GAMES","finished":0,"future":0}
    seen=set();teams=set();finished=0;future=0
    for m in games:
        if not isinstance(m,dict) or not isinstance(m.get("id"),str):
            return {"valid":False,"reason":"BAD_MATCH_SCHEMA","finished":0,"future":0}
        if m["id"] in seen:
            return {"valid":False,"reason":"DUPLICATE_MATCH_IDS","finished":0,"future":0}
        seen.add(m["id"])
        try:
            ko=as_utc(m["time_utc"])
            ht=m["home_team"]["id"];at=m["away_team"]["id"]
            if ht==at:raise ValueError("same team")
            teams.update((ht,at))
        except (KeyError,ValueError,TypeError):
            return {"valid":False,"reason":"INVALID_FIXTURE_IDS","finished":0,"future":0}
        if m.get("status")=="finished":
            if any(type(m.get(k)) is not int or not 0<=m[k]<=30 for k in ("score_home","score_away")):
                return {"valid":False,"reason":"BAD_FINISHED_90MIN_SCORE","finished":0,"future":0}
            finished+=1
        elif current and m.get("status") in ("upcoming","not_started","scheduled"):
            if m.get("score_home") is not None or m.get("score_away") is not None:
                return {"valid":False,"reason":"UNPLAYED_HAS_TARGET_RESULT","finished":0,"future":0}
            if ko>datetime.now(timezone.utc)+timedelta(minutes=90):
                future+=1
        elif not current:
            return {"valid":False,"reason":"PREVIOUS_NOT_FINISHED","finished":0,"future":0}
    if len(teams)<12 or finished<20 or (current and future<1):
        return {"valid":False,"reason":"COVERAGE_INCOMPLETE","finished":finished,"future":future,
                "teams":len(teams)}
    return {"valid":True,"reason":"SEASON_FIXTURES_PRESENT","finished":finished,
            "future":future,"teams":len(teams),"fixtures":len(games),
            "fixture_ids_sha256":digest(sorted(seen))}

def audit(client, *, observation_time):
    if observation_time.utcoffset()!=timedelta(0):
        raise LeagueAuditError("UTC_REQUIRED")
    n=0; errors=[]
    def read(method,*args,**kwargs):
        nonlocal n
        if n>=MAX_CALLS:
            raise LeagueAuditError("MAX_PROVIDER_CALLS_EXCEEDED")
        n+=1
        try:
            value=to_plain(method(*args,**kwargs))
            if not isinstance(value,dict):
                raise LeagueAuditError("NON_OBJECT_PROVIDER_RESPONSE")
            return value
        except Exception as exc:
            errors.append(type(exc).__name__)
            return None
    catalog=read(client.leagues.list)
    if catalog is None:
        raise LeagueAuditError("LEAGUE_CATALOG_NETWORK_OR_ENTITLEMENT_ERROR")
    matches=match_catalog(catalog)
    candidates=[]
    for item in matches:
        info=dict(item)
        if not info["catalog_both_seasons"]:
            candidates.append(info)
            continue
        lid=info.pop("provider_league_id")
        current=read(client.leagues.matches,lid,season=CURRENT,status="all")
        previous=read(client.leagues.matches,lid,season=PREVIOUS)
        if current is None or previous is None:
            info.update({"provider_fixture_access":False,"ready":False,
                         "reason":"SEASON_ENDPOINT_REJECTED"})
            candidates.append(info)
            continue
        c=compact_season(current.get("matches"),CURRENT,True)
        p=compact_season(previous.get("matches"),PREVIOUS,False)
        info.update({"provider_fixture_access":True,"current":c,"previous":p,
                     "ready":False,"native_xg_sample_verified":False})
        if not c["valid"] or not p["valid"]:
            info["reason"]="SEASON_COVERAGE_NOT_VERIFIED"
            candidates.append(info)
            continue
        finished=[m for m in current["matches"] if m["status"]=="finished"
                  and as_utc(m["time_utc"])+timedelta(hours=3)<observation_time]
        # Only previous already-finished data, never sample an upcoming target.
        if not finished:
            info["reason"]="NO_FINISHED_CURRENT_SAMPLE"
            candidates.append(info)
            continue
        sample=max(finished,key=lambda x:(x["time_utc"],x["id"]))
        mid=sample["id"]
        shots=read(client.matches.shots,mid)
        stats=read(client.matches.stats,mid)
        if shots is not None and stats is not None:
            try:
                h=sample["home_team"]["id"];a=sample["away_team"]["id"]
                parse_native_shots(shots,mid,h,a)
                parse_native_team_stats(stats,mid,h,a)
                info["native_xg_sample_verified"]=True
                info["ready"]=True
                info["reason"]="REAL_FIXTURES_AND_ONE_REAL_XG_PAIR_VERIFIED"
            except Exception:
                info["reason"]="NATIVE_XG_SCHEMA_REJECTED"
        else:
            info["reason"]="NO_REAL_XG_SAMPLE_PAIR"
        candidates.append(info)
    report={"schema":SCHEMA,
            "utc_observed":observation_time.isoformat().replace("+00:00","Z"),
            "network_observed":True,
            "provider_calls":n,"hard_ceiling":MAX_CALLS,
            "candidate_count":len(CANDIDATES),
            "candidates":candidates,
            "verified_full_1xg_pair_count":sum(c.get("ready") is True for c in candidates),
            "errors_type_only":sorted(set(errors)),
            "premier_league_2026_27_test_results_requested":False,
            "original_m0_or_m1_changed":False,
            "target_result_used_for_model_fitting":False,
            "production_auto_enabled":False,
            "historic_provider_first_publication_proven":False,
            "new_leagues_live_pipeline_enabled":False,
            "step16_gate":"PENDING"}
    report["report_sha256"]=digest(report)
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="data/audits/STEP16_ADDITIONAL_LEAGUES_LIVE_20261029.json")
    args=parser.parse_args()
    key=os.environ.get("PITCHAPI_API_KEY","")
    if not key:
        raise SystemExit("PROVIDER_SECRET_NOT_AVAILABLE")
    from pitchapi import PitchAPI
    result=audit(PitchAPI(api_key=key),observation_time=datetime.now(timezone.utc))
    path=Path(args.output)
    if path.exists():
        raise SystemExit("APPEND_ONLY_AUDIT_ALREADY_EXISTS")
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf8") as f:
        json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2)
        f.write("\n")
    print(json.dumps({"new_candidates_ready":result["verified_full_1xg_pair_count"],
                      "provider_calls":result["provider_calls"],
                      "failed_request_types":result["errors_type_only"],
                      "report_sha256":result["report_sha256"]},sort_keys=True))

if __name__=="__main__":
    main()
