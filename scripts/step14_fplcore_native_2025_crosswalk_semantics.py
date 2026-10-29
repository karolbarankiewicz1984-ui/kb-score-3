"""Real original PitchAPI fixture crosswalk for 18 witnessed 2025/26 FPL-Core targets.

Only 2025/26 VALIDATION native fixture identifiers, names and kickoff; never
read any target score, a target's post-match stats, 2026/27 TEST or odds.
Optional retrospective xG semantics uses SIX DIFFERENT *previously completed*
source fixture sides, not labels of 18 target matches.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import json, os
from pathlib import Path
from statistics import mean
from src.kb3_step14_native_team_crosswalk import SAFE_SHA
from src.kb3_step14_pitchapi_xg_semantics import parse_native_team_stats
from src.kb3_pitch_native import check_season
from scripts.pitchapi_step06_audit import norm,to_plain
from scripts.step14_fpl_core_2025_independent_asof import (
    _name,_utc,_read_teams,_read_matches,_fetch_raw,SOURCES,REPO)
from src.kb3_split import sha

ROOT=Path(__file__).resolve().parents[1]
AUDIT="data/audits/STEP14_2025_FPLCORE_INDEPENDENT_ASOF_RECOVERY_2026-10-29.json"
SAFE="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
SCHEMA="kb3-step14-native-PitchAPI-exact-18-witnessed-public-2025-fixture-and-2025-xg-semantics-v1"
class NativeJoinError(ValueError): pass

def load_public(root=ROOT):
    item=json.loads((Path(root)/AUDIT).read_text())
    if (item.get("new_distinct_published_public_FORM5_candidates")!=18
        or item.get("new_distinct_published_public_alternative_xg_FORM5_candidates")!=18
        or item.get("gate14")!="PENDING"
        or item.get("original_121_plus_38_eligible_validation")!=0
        or len(item.get("candidates",[]))!=18
        or item.get("source")!=REPO):
        raise NativeJoinError("ORIGINAL_18_RESEARCH_RECEIPT_CHANGED")
    safe=json.loads((Path(root)/SAFE).read_text())
    if (safe.get("projection_sha256")!=SAFE_SHA
        or sha({k:v for k,v in safe.items() if k!="projection_sha256"})!=SAFE_SHA
        or safe.get("training_allowed") is not False):
        raise NativeJoinError("FROZEN_SAFE_SOURCE_CHANGED")
    validation={x["fixture_id"]:x["kickoff_utc"] for x in safe["fixtures"]
                if x["partition"]=="VALIDATION"}  # TEST never examined.
    if len(validation)!=380: raise NativeJoinError("VALIDATION_COUNT_CHANGED")
    return item,validation

def select_native_catalog(catalog):
    if not isinstance(catalog,dict) or not isinstance(catalog.get("leagues"),list):
        raise NativeJoinError("PITCH_CATALOG_WRONG")
    matches=[x for x in catalog["leagues"]
       if norm(x.get("name")).replace(" ","")=="premierleague"
       and str(x.get("country_code","")).upper()=="ENG"
       and "2025/2026" in (x.get("seasons") or [])]
    if len(matches)!=1: raise NativeJoinError("NO_UNIQUE_2025_PREMIER_LEAGUE")
    return matches[0]["id"]

def exact_native_join(public,validation,raw_matches):
    checked=check_season(raw_matches,"2025/2026",expected_count=380)
    if len(raw_matches)!=380 or any(m["status"]!="finished" for m in raw_matches):
        raise NativeJoinError("REAL_2025_NOT_ALL_FINISHED")
    if {m["id"] for m in raw_matches}!=set(validation):
        raise NativeJoinError("ORIGINAL_380_NATIVE_SCHEDULE_SET_CHANGED")
    index={}
    for m in raw_matches:
        if m["time_utc"]!=validation[m["id"]]:
            raise NativeJoinError("ORIGINAL_2025_KICKOFF_SPLIT_CHANGED")
        key=(_name(m["home_team"]["name"]),_name(m["away_team"]["name"]),
             _utc(m["time_utc"]).isoformat())
        if key in index: raise NativeJoinError("AMBIGUOUS_NATIVE_PAIR")
        index[key]=m
    mapped=[]
    unresolved=[]
    used=set()
    for target in public["candidates"]:
        key=(_name(target["target_public_home"]),_name(target["target_public_away"]),
             _utc(target["target_kickoff_utc"]).isoformat())
        match=index.get(key)
        if match is None:
            # No kickoff-only guess, never use the target's current match score.
            unresolved.append({"public_pair":[key[0],key[1]],"kickoff_utc":
                               target["target_kickoff_utc"],"reason":"NO_EXACT_NATIVE_SIDE_AND_KICKOFF"})
            continue
        if match["id"] in used:raise NativeJoinError("DUPLICATE_ORIGINAL_NATIVE_TARGET")
        used.add(match["id"])
        mapped.append({"native_pitchapi_fixture_id":match["id"],
            "native_home_team_id":match["home_team"]["id"],
            "native_away_team_id":match["away_team"]["id"],
            "public_pair":[key[0],key[1]],
            "kickoff_utc":match["time_utc"],
            "fplcore_old_source_commit":target["evidence_source_commit"],
            "fplcore_old_source_witness_utc":target["source_publication_witness_utc"],
            "same_native_match_home_away_and_kickoff":True,
            "native_PitchAPI_original_xg_asof_certified":False,
            "original_m1_121_plus_38_pit_eligible":False})
    if len(mapped)+len(unresolved)!=18:raise NativeJoinError("MISSING_TARGET")
    return sorted(mapped,key=lambda r:r["kickoff_utc"]),unresolved,index

def compare_previous_xg(index, *, stats_call, fetcher=_fetch_raw, max_stats=6):
    # On-source immutable 2025-11-07 data. Retrospective 2026 PitchAPI values
    # only for six earlier finished fixtures. This cannot certify PIT in 2025.
    commit,_,_,clock=SOURCES[1]
    raw,_=fetcher(commit,"data/2025-2026/By Gameweek/GW10/teams.csv")
    teams=_read_teams(raw)
    prior=[]
    for gw in range(1,11):
        raw,_=fetcher(commit,f"data/2025-2026/By Gameweek/GW{gw}/matches.csv")
        prior.extend(_read_matches(raw,witness=clock,teams=teams).items())
    eligible=[]
    for key,public in prior:
        native=index.get(key)
        if native is None:continue
        if public["home_xg"] is None or public["away_xg"] is None:continue
        eligible.append((native,public))
    eligible.sort(key=lambda s:(s[0]["time_utc"],s[0]["id"]))
    sampled=[]
    errors=[]
    # Deterministic spread; never request any of 18 held-out target matches.
    target_dates = {_utc("2025-11-08T00:00:00Z")}
    for native,public in eligible[:max_stats]:
        if _utc(native["time_utc"])>=_utc(clock):
            raise NativeJoinError("XG_SOURCE_NOT_HISTORIC_BEFORE_AUDIT")
        stats=stats_call(native["id"])
        h,a=parse_native_team_stats(stats,native["id"],native["home_team"]["id"],
                                   native["away_team"]["id"])
        errors.extend((abs(h-public["home_xg"]),abs(a-public["away_xg"])))
        sampled.append(native["id"])
    return {"original_native_same_match_xg_side_comparisons":len(errors),
        "different_old_2025_source_vs_current_2026_pitch_xg":True,
        "mean_absolute_xg_difference":round(mean(errors),6) if errors else None,
        "maximum_absolute_xg_difference":round(max(errors),6) if errors else None,
        "number_of_differences_above_0_02":sum(v>0.0200001 for v in errors),
        "actual_original_PitchAPI_provider_first_published_at_utc":None,
        "FPL_Core_xg_not_proven_equivalent_to_PitchAPI_xg":True,
        "sample_only_preexisting_completed_games":len(sampled),
        "no_target_result_or_target_xg_sampled":True}

def run(*,api_key,client_factory=None,stats_calls_limit=6):
    if not api_key or not isinstance(api_key,str):raise NativeJoinError("PITCHAPI_API_KEY_MISSING")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    public,validation=load_public()
    client=client_factory(api_key=api_key)
    n=0
    def call(fn,*args,**kw):
        nonlocal n
        if n>=2+stats_calls_limit:raise NativeJoinError("PITCH_API_HARD_BUDGET")
        n+=1
        try:return to_plain(fn(*args,**kw))
        except Exception:raise NativeJoinError("PITCH_SDK_REQUEST_FAILED") from None
    catalog=call(client.leagues.list)
    lid=select_native_catalog(catalog)
    season=call(client.leagues.matches,lid,season="2025/2026")
    matched,unresolved,index=exact_native_join(public,validation,season.get("matches"))
    semantics=compare_previous_xg(index,stats_call=lambda mid:call(client.matches.stats,mid),
                                   max_stats=stats_calls_limit)
    return {"schema":SCHEMA,"validation_season":"2025/2026",
        "original_SAFE_2025_validation_rows":380,
        "public_research_target_candidates":18,
        "actual_PitchAPI_native_fixture_ID_exact_side_and_kickoff_joins":len(matched),
        "public_targets_without_exact_native_match":unresolved,
        "native_fixture_crosswalk":matched,
        "xg_semantic_retrospective_2025_same_finished_fixture_test":semantics,
        "provider_API_requests":n,"provider_original_historical_per_value_published_at":None,
        "official_121_plus_38_PIT_validation_eligible":0,
        "original_M1_training_allowed":False,"original_GATE14":"PENDING",
        "no_TEST_labels_or_target_scores_or_odds_read":True}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    args=p.parse_args()
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise NativeJoinError("OUTPUT_APPEND_ONLY")
    res=run(api_key=os.environ.get("PITCHAPI_API_KEY",""))
    out.write_text(json.dumps(res,sort_keys=True,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"exact_native_joins":res["actual_PitchAPI_native_fixture_ID_exact_side_and_kickoff_joins"],
        "unresolved":len(res["public_targets_without_exact_native_match"]),
        "retrospective_xg_sides_compared":res["xg_semantic_retrospective_2025_same_finished_fixture_test"]["original_native_same_match_xg_side_comparisons"],
        "API_calls":res["provider_API_requests"],"original_M1_fit":False},sort_keys=True))
if __name__=="__main__":
    main()
