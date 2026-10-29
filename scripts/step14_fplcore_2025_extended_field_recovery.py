"""Extend 18 proven public 2025 targets to all recoverable Step11-shaped history.

STRICTLY research-only. Missing historical evidence => None, never made-up Elo
or a full 121+38 original PitchAPI vector. Source values under the original
field NAMES are comparable candidates, not original provider-qualified values.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import timezone
from pathlib import Path
import json
import math
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from scripts.step14_fpl_core_2025_independent_asof import (
    _read_matches,_read_teams,_fetch_raw,_reference,_utc,SOURCES,CandidateError,REPO)
from scripts.step14_fplcore_native_2025_crosswalk_semantics import (
    load_public,SCHEMA as NATIVE_SCHEMA)

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-2025-alternative-source-all-121-38-recoverable-partial-field-coverage-v1"
class CoverageError(ValueError): pass

def public_source(commit,*,fetcher=_fetch_raw):
    matches=next((x for x in SOURCES if x[0]==commit),None)
    if matches is None:raise CoverageError("UNKNOWN_UNWITNESSED_SOURCE")
    _,run_id,last,clock=matches
    teams_raw,_=fetcher(commit,"data/2025-2026/By Gameweek/GW10/teams.csv")
    teams=_read_teams(teams_raw)
    prior={}
    quarantined={}
    blobs={}
    def get(gw):
        raw,checksum=fetcher(commit,f"data/2025-2026/By Gameweek/GW{gw}/matches.csv")
        try:return gw,checksum,_read_matches(raw,witness=clock,teams=teams),None
        except CandidateError as exc:
            if str(exc)=="FUTURE_OR_RECENT_FT_IN_OLD_SNAPSHOT":
                return gw,checksum,{},"FUTURE_FINISHED_MATCH_IN_ARCHIVED_GW"
            raise
    with ThreadPoolExecutor(max_workers=6) as t:
        jobs=[t.submit(get,n) for n in range(1,last+1)]
        for fut in as_completed(jobs):
            gw,checksum,data,bad=fut.result()
            blobs[str(gw)]=checksum
            if bad:quarantined[str(gw)]=bad
            for k,row in data.items():
                if k in prior:raise CoverageError("DUPLICATE_PUBLISHED_PRIOR_EVENT")
                prior[k]=row
    return {"witness":clock,"commit":commit,"run_id":run_id,
            "prematch_previous_completed_games":prior,
            "source_gw_sha256":blobs,"quarantined_gw":quarantined}

def _team_window(target,team,category,n,all_2025,past,witness):
    prior=sorted([p for p in all_2025
       if p["ko"]<target["ko"]
       and (p["home"]==team or p["away"]==team)
       and (category=="all" or
            (p["home"]==team)==(target["home"]==team))],
       key=lambda p:p["ko"],reverse=True)
    sample=prior[:n]
    if not sample:
        return {"n":0,"history_missing":True,"source_asof_complete":True,
                "points_avg":None,"gf_avg":None,"ga_avg":None,
                "opponent_elo_avg":None,"xg_n":0,"xg_avg":None,"xga_n":0,"xga_avg":None,
                "xg_missing":True,"xga_missing":True}
    # Entire last-n from *retrospective score-free fixture schedule* must appear
    # in archived, server-witnessed old source. Otherwise ALL aggregates null.
    covered=[past.get(x["key"]) for x in sample]
    complete=all(m is not None for m in covered)
    if not complete:
        return {"n":None,"history_missing":True,"source_asof_complete":False,
                "points_avg":None,"gf_avg":None,"ga_avg":None,
                "opponent_elo_avg":None,"xg_n":None,"xg_avg":None,
                "xga_n":None,"xga_avg":None,"xg_missing":None,"xga_missing":None}
    points=[];gfs=[];gas=[];xgs=[];xgas=[]
    for x,m in zip(sample,covered):
        h = x["home"]==team
        gf=m["home_goals"] if h else m["away_goals"]
        ga=m["away_goals"] if h else m["home_goals"]
        points.append(3 if gf>ga else 1 if gf==ga else 0)
        gfs.append(gf);gas.append(ga)
        own=m["home_xg"] if h else m["away_xg"]
        against=m["away_xg"] if h else m["home_xg"]
        if own is not None:xgs.append(own)
        if against is not None:xgas.append(against)
    return {"n":len(sample),"history_missing":len(sample)<n,
            "source_asof_complete":True,
            "points_avg":round(sum(points)/len(sample),6),
            "gf_avg":round(sum(gfs)/len(sample),6),
            "ga_avg":round(sum(gas)/len(sample),6),
            "opponent_elo_avg":None, # genuine Elo depends on full earlier seasons
            "xg_n":len(xgs),"xg_avg":round(sum(xgs)/len(xgs),6) if xgs else None,
            "xga_n":len(xgas),"xga_avg":round(sum(xgas)/len(xgas),6) if xgas else None,
            "xg_missing":len(xgs)<len(sample) or not sample,
            "xga_missing":len(xgas)<len(sample) or not sample}

def _candidate(target,all_2025,history,source):
    cutoff=_utc(source["witness"])
    if target["ko"]<=cutoff:raise CoverageError("TARGET_ALREADY_PLAYED_AT_SOURCE_WITNESS")
    values={x:None for x in EXPECTED_FEATURES}
    masks={x:None for x in EXPECTED_MISSING}
    for side in ("home","away"):
        team=target[side]
        # No prior-season rows in this datasource: these MUST remain unknown.
        relevant=sorted([p for p in all_2025 if p["ko"]<target["ko"]
                        and team in (p["home"],p["away"])],
                        key=lambda p:p["ko"],reverse=True)
        observed=[history.get(p["key"]) for p in relevant]
        all_complete=all(v is not None for v in observed)
        if all_complete:
            values[side+"_games_available"]=len(relevant)
            values[side+"_venue_games_available"]=sum(
               (p["home"]==team)==(side=="home") for p in relevant)
            if relevant:
                values[side+"_days_since_last_kickoff"]=round(
                  (cutoff-relevant[0]["ko"]).total_seconds()/86400,4)
                masks[side+"_days_since_last_kickoff"]=False
            else:
                masks[side+"_days_since_last_kickoff"]=True
        for category in ("all","venue"):
            for n in (5,10,15):
                d=_team_window(target,team,category,n,all_2025,
                    history,source["witness"])
                stem=f"{side}_{category}_{n}"
                for fld in ("n","points_avg","gf_avg","ga_avg","opponent_elo_avg",
                            "xg_n","xg_avg","xga_n","xga_avg"):
                    values[stem+"_"+fld]=d[fld]
                masks[stem+"_history"]=d["history_missing"] if d["source_asof_complete"] else None
                masks[stem+"_xg"]=d["xg_missing"]
                masks[stem+"_xga"]=d["xga_missing"]
    if set(values)!=EXPECTED_FEATURES or set(masks)!=EXPECTED_MISSING:
        raise CoverageError("ORIGINAL_FIELD_NAME_CONTRACT_CHANGED")
    if any(isinstance(x,(int,float)) and not isinstance(x,bool) and not math.isfinite(x)
           for x in values.values() if x is not None):
        raise CoverageError("INVALID_NONFINITE_FEATURE")
    return {"public_pair":[target["home"],target["away"]],
        "kickoff_utc":target["ko"].isoformat().replace("+00:00","Z"),
        "research_features_not_native_PitchAPI":values,
        "research_missing_flags_not_native_PitchAPI":masks,
        "non_null_numeric_source_field_count":sum(v is not None for v in values.values()),
        "non_null_missing_flag_source_count":sum(v is not None for v in masks.values()),
        "source_commit":source["commit"],"source_witness":source["witness"],
        "native_API_history_feature_equivalence_proven":False,
        "full_original_pit_eligible":False}

def run(root=ROOT):
    base=Path(root)
    public,_=load_public(base)
    originals=_reference(base/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json")
    target_index={x["key"]:x for x in originals}
    source_versions={}
    for commit in {x["evidence_source_commit"] for x in public["candidates"]}:
        source_versions[commit]=public_source(commit)
    rows=[]
    for item in public["candidates"]:
        key=(item["target_public_home"],item["target_public_away"],
             _utc(item["target_kickoff_utc"]).isoformat())
        target=target_index.get(key)
        if target is None:raise CoverageError("PUBLIC_TARGET_REFERENCE_IDENTITY_CHANGED")
        source=source_versions[item["evidence_source_commit"]]
        row=_candidate(target,originals,source["prematch_previous_completed_games"],source)
        # Cross-check old, already independently tested five prior FORM5 values.
        for side in ("home","away"):
            for metric in ("points_avg","gf_avg","ga_avg","xg_avg","xga_avg"):
                desired=item["prematch_public_FORM5"][side][
                    "alternative_"+metric if metric in ("xg_avg","xga_avg") else metric]
                observed=row["research_features_not_native_PitchAPI"][side+"_all_5_"+metric]
                if observed is None or abs(observed-desired)>0.00001:
                    raise CoverageError("NEW_SOURCE_FEATURES_DO_NOT_MATCH_PREVIOUS_VERIFIED_FORM5")
        rows.append(row)
    if len(rows)!=18:raise CoverageError("CANDIDATE_COUNT_CHANGED")
    return {"schema":SCHEMA,
      "source":"olbauday/FPL-Core-Insights archived GitHub main witnessed versions",
      "rows":rows,
      "historical_public_targets_with_research_values":len(rows),
      "original_Step11_field_name_count":121,
      "original_Step11_missing_mask_name_count":38,
      "non_null_research_numeric_slots":sum(r["non_null_numeric_source_field_count"] for r in rows),
      "non_null_research_missing_slots":sum(r["non_null_missing_flag_source_count"] for r in rows),
      "recoverable_research_numeric_fields_with_any_witnessed_value":
          sorted({k for r in rows for k,v in r["research_features_not_native_PitchAPI"].items()
                  if v is not None}),
      "not_recoverable_research_numeric_fields_without_old_source_or_complete_Elo":
          sorted({k for k in EXPECTED_FEATURES if all(r["research_features_not_native_PitchAPI"][k] is None
                                                      for r in rows)}),
      "distinct_archived_research_sources_used":len(source_versions),
      "quarantined_old_files":{k: v["quarantined_gw"] for k,v in source_versions.items()},
      "all_target_scores_or_TEST_labels_read":False,
      "original_PitchAPI_full_121_38_PIT_validated_rows":0,
      "original_M1_fit_allowed":False,"GATE14":"PENDING"}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise CoverageError("IMMUTABLE_RESEARCH_OUTPUT_EXISTS")
    doc=run()
    out.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "historically_witnessed_targets":doc["historical_public_targets_with_research_values"],
        "numeric_slots":doc["non_null_research_numeric_slots"],
        "missing_flag_slots":doc["non_null_research_missing_slots"],
        "numeric_field_names_recovered":len(doc["recoverable_research_numeric_fields_with_any_witnessed_value"]),
        "original_M1_fitted":False,"GATE14":"PENDING"},sort_keys=True))
if __name__=="__main__":
    main()
