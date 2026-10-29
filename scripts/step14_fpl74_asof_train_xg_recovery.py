"""KB3 Step14 use all 74 historic FPL revisions + source-authenticated player xG.

Only FPL old blobs proven public before target by independent GHArchive
descendant timestamps. Recompute source-visible 121/38 *research* data
on exact original frozen native fixture IDs. Never use target scores, TEST,
original native historical xG equivalence, or fit the CatBoost M1.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import timedelta
from hashlib import sha256
import argparse,csv,gzip,io,json,math,os
from pathlib import Path
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step14_multiseason_pit import fetch
from src.kb3_step14_xg_four_gates import extract_public_xg,XGFourGateError,METHOD
from scripts.step14_fpl74_independent_historic_ancestry import SCHEMA as INVENTORY_SCHEMA,REPO
from scripts.step14_train_760_decimal_FPL_FT_corrected_v2 import corrected_source
from scripts.step14_train_760_dense_validation_1140_matrix import (
   _original_schedule,_team,_candidate,ROOT)
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import _valid_safe
from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_fpl_core_2025_independent_asof import _utc

SCHEMA="kb3-step14-74-git-historic-FPL-public-player-xg-760-native-TRAIN-research-v1"
INVENTORY="data/audits/STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json"
V2_MATRIX="data/audits/STEP14_760_TRAIN_FPL_WHOLE_DECIMAL_CORRECTED_1140x159_2026-10-29.jsonl.gz"
V2_REPORT="data/audits/STEP14_760_TRAIN_FPL_WHOLE_DECIMAL_CORRECTED_SUMMARY_2026-10-29.json"
class Historic74Error(ValueError): pass

def _raw(commit,season,path,max_bytes=25_000_000,fetcher=fetch):
    url=f"https://raw.githubusercontent.com/{REPO}/{commit}/data/{season}/{path}"
    buf=fetcher(url,limit=max_bytes+1)
    if not isinstance(buf,bytes) or len(buf)>max_bytes:
        raise Historic74Error("HISTORIC_BLOB_OVERSIZED")
    return buf

def _source_from_revision(rev,fetcher=fetch):
    if rev.get("status")!="OLD_GITHUB_SHA_GIT_ANCESTRY_PUBLISHED_BY_VERIFIED_PUSH":
        raise Historic74Error("GIT_DAG_AND_TIMESTAMP_NOT_VERIFIED")
    commit,season,witness=rev["sha"],rev["season"],rev["witnessed_public_by_utc"]
    raw=_raw(commit,season,"fixtures.csv",fetcher=fetcher)
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(rows)!=380 or any(not {"id","team_h","team_a","finished","kickoff_time",
                                    "team_h_score","team_a_score"}.issubset(x) for x in rows):
        raise Historic74Error("BAD_OLD_FIXTURE_GRID")
    finished=sum(x["finished"]=="True" for x in rows)
    if any(x["finished"] not in ("True","False") for x in rows):
        raise Historic74Error("BAD_OLD_FT_STATUS")
    pin={"season":season,"provider":"FPL","repo":REPO,"path":f"data/{season}/fixtures.csv",
         "commit":commit,"push":witness,"ft":finished,"sha":sha256(raw).hexdigest()}
    base=corrected_source(pin,fetcher=fetcher)
    base["source"]["GHArchive_actual_old_descendant_sha"]=rev["old_public_descendant_anchor_sha"]
    base["source"]["GHArchive_old_event_id"]=rev["external_GHArchive_event_id"]
    base["source"]["historic_ancestry_publication_upper_bound_utc"]=witness
    base["source"]["publication_proof"]="OLD_GITHUB_ANCESTOR_SHA_IN_GHARCHIVE_TIMESTAMPED_DESCENDANT"
    base["old_gharchive_verified_before_target"]=True
    base["fixture_raw"]=raw
    return base

def _last_five(target,allrows,side):
    team=target[side]
    arr=sorted((x for x in allrows if x["ko"]<target["ko"] and
                team in (x["home"],x["away"])),
               key=lambda x:(x["ko"],x["native_fixture_id"]),reverse=True)
    return arr[:5] if len(arr)>=5 else []

def _candidate_precheck(target,allrows,src):
    if not _utc(src["witness"])<target["ko"]:return False
    if src["schedules"].get(target["key"]) is not False:return False
    for side in ("home","away"):
        prior=_last_five(target,allrows,side)
        if len(prior)!=5:return False
        if any(x["key"] not in src["past"] for x in prior):return False
    return True

def _fpl_side_xg(blob,src,fetcher=fetch):
    """Existing verified strict matching: FPL fixture ID, side, opponent, player."""
    pin=src["source"]
    raw=_raw(pin["commit"],pin["season"],"gws/merged_gw.csv",max_bytes=30_000_000,fetcher=fetcher)
    if not raw:raise Historic74Error("EMPTY_HISTORIC_PLAYER_XG")
    xg=extract_public_xg(src["fixture_raw"],raw,
        published_at=pin["push"],
        pinned_fixture_sha=pin["sha"],pinned_player_sha=sha256(raw).hexdigest())
    teamsraw=_raw(pin["commit"],pin["season"],"teams.csv",max_bytes=100_000,fetcher=fetcher)
    names={}
    for row in csv.DictReader(io.StringIO(teamsraw.decode("utf-8-sig"))):
        tid=int(row["id"]);name=_team(row["name"])
        if tid in names or name in names.values():raise Historic74Error("DUPLICATE_OLD_FPL_TEAM")
        names[tid]=name
    index={}
    for row in csv.DictReader(io.StringIO(src["fixture_raw"].decode("utf-8-sig"))):
        if not row["kickoff_time"]:continue
        key=(names[int(row["team_h"])],names[int(row["team_a"])],
             _utc(row["kickoff_time"]).isoformat())
        if key in index:raise Historic74Error("DUPLICATE_OLD_FPL_FIXTURE_FOR_XG")
        index[key]=(int(row["id"]),int(row["team_h"]),int(row["team_a"]))
    past={}
    for key,record in src["past"].items():
        copy=dict(record);copy["home_xg"]=None;copy["away_xg"]=None
        ids=index.get(key)
        if ids:
            fid,h,a=ids
            # A complete fixture requires BOTH sets of player rows.
            left=xg["source_side_row_counts"].get((fid,h),0)
            right=xg["source_side_row_counts"].get((fid,a),0)
            if left>=11 and right>=11:
                hx=xg["source_side_xg_values_IN_MEMORY_ONLY"].get((fid,h))
                ax=xg["source_side_xg_values_IN_MEMORY_ONLY"].get((fid,a))
                if hx is not None and ax is not None:
                    copy["home_xg"]=round(hx,8);copy["away_xg"]=round(ax,8)
        past[key]=copy
    return {"sha256":sha256(raw).hexdigest(),"player_rows":xg["player_rows"],
         "fixture_both_sides_xg":sum(r["home_xg"] is not None and r["away_xg"] is not None
                                     for r in past.values()),
         "past":past,"source_metric":METHOD}

def _enhanced_candidate(target,seasonrows,src,player):
    doc=_candidate(target,seasonrows,player["past"],{"witness":src["witness"],
         "commit":src["commit"]})
    vals=doc["research_features_not_native_PitchAPI"]
    flags=doc["research_missing_flags_not_native_PitchAPI"]
    # Numeric mean over 1-4 available old games must not be labeled complete xG5.
    sides=[]
    for side in ("home","away"):
        f=f"{side}_all_5"
        full=(vals[f+"_xg_n"]==5 and vals[f+"_xga_n"]==5
              and flags[f+"_xg"] is False and flags[f+"_xga"] is False)
        sides.append(full)
        if not full:
            for suffix in ("xg_avg","xga_avg"):
                vals[f+"_"+suffix]=None
    return doc,all(sides)

def run(root=ROOT,*,fetcher=fetch,api_key=None):
    root=Path(root)
    inv=json.loads((root/INVENTORY).read_text())
    if inv.get("schema")!=INVENTORY_SCHEMA or not inv.get("all_74_source_revisions_inventoried"):
        raise Historic74Error("UNTRUSTED_74_SOURCE_INVENTORY")
    safe=_valid_safe(root)
    native,calls=native_three_seasons(key=api_key or os.environ.get("PITCHAPI_API_KEY",""))
    by_key,seasonrows=_original_schedule(native,safe)
    v2=json.loads((root/V2_REPORT).read_text())
    if v2.get("distinct_original_TRAIN_with_historical_public_result_FORM5")!=54 or v2.get("GATE14")!="PENDING":
        raise Historic74Error("FROZEN_CORRECTED_V2_MUST_HAVE_54_TRAIN")
    raw=(root/V2_MATRIX).read_bytes()
    if v2["matrix_gzip_sha256"]!=sha256(raw).hexdigest():
        raise Historic74Error("OLD_CANONICAL_1140x159_BYTES_CHANGED")
    with gzip.open(root/V2_MATRIX,"rt",encoding="utf-8") as f:
        matrix=[json.loads(x) for x in f if x.strip()]
    if len(matrix)!=1140:raise Historic74Error("ORIGINAL_1140_MATRIX_WRONG")
    original={x["fixture_id"]:x for x in matrix}
    if len(original)!=1140:raise Historic74Error("ORIGINAL_NATIVE_ID_DUPLICATE")
    proven=[r for r in inv["fpl_revisions"] if r["certified_before_target"]]
    sources=[];failures=[];skipped=Counter()
    # Fetch all 74 fixture versions (for qualified candidates); errors are
    # explicitly inventoried and cannot secretly contribute features.
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs={executor.submit(_source_from_revision,r,fetcher):r for r in proven}
        for future in as_completed(jobs):
            rev=jobs[future]
            try:sources.append(future.result())
            except Exception as exc:
                reason=str(exc) if isinstance(exc,(Historic74Error,ValueError)) else type(exc).__name__
                failures.append({"commit":rev["sha"],"season":rev["season"],"reason":reason})
    versions=defaultdict(list)
    for source in sources:versions[source["source"]["season"]].append(source)
    lookups={}
    selected_candidates={}
    for season in ("2023-24","2024-25"):
        allrows=seasonrows[season]
        for target in allrows:
            valid=[x for x in versions[season] if _candidate_precheck(target,allrows,x)]
            if not valid:continue
            valid.sort(key=lambda s:(s["witness"],s["commit"]),reverse=True)
            selected_candidates[target["native_fixture_id"]]=(target,allrows,valid)
    # Avoid N target xG requests: cache immutable merged_gw for selected SHAs.
    xg_cache={};bad_xg=Counter()
    for ident,(target,allrows,candidates) in sorted(
          selected_candidates.items(),key=lambda p:p[1][0]["ko"]):
        chosen=None
        # Search at most two eligible revisions; favour genuine witnessed
        # complete 5+5 xG instead of a later incomplete old blob.
        for src in candidates[:2]:
            commit=src["commit"]
            if commit not in xg_cache:
                try:xg_cache[commit]=_fpl_side_xg(None,src,fetcher=fetcher)
                except Exception as exc:
                    xg_cache[commit]=None
                    bad_xg[str(exc) if isinstance(exc,(ValueError,Historic74Error)) else
                          type(exc).__name__]+=1
            xg=xg_cache[commit]
            if xg is None:continue
            newrow,complete=_enhanced_candidate(target,allrows,src,xg)
            if complete:
                chosen=(src,newrow,xg,True)
                break
            if chosen is None:chosen=(src,newrow,xg,False)
        if chosen is None:
            # Even without valid player xG, preserve real witness source FT.
            src=candidates[0]
            doc=_candidate(target,allrows,src["past"],
                     {"witness":src["witness"],"commit":src["commit"]})
            chosen=(src,doc,None,False)
        src,doc,xg,complete=chosen
        selected_candidates[ident]=(target,allrows,src,doc,xg,complete)
    promoted=0;matched=0;complete_xg5=0;source_methods=Counter()
    audit_rows=[]
    for ident,record in sorted(selected_candidates.items()):
        target,allrows,src,doc,xg,complete=record
        current=original[ident]
        if current["partition"]!="TRAIN" or current["kickoff_utc"]!=target["ko"].isoformat().replace("+00:00","Z"):
            raise Historic74Error("ORIGINAL_TRAIN_ID_KICKOFF_DRIFT")
        old_status=current["history_public_asof_source"]["status"]
        source_methods["old_"+old_status]+=1
        vals=doc["research_features_not_native_PitchAPI"]
        flags=doc["research_missing_flags_not_native_PitchAPI"]
        if set(vals)!=EXPECTED_FEATURES or set(flags)!=EXPECTED_MISSING:
            raise Historic74Error("ORIGINAL_121_38_FIELD_NAMES_CHANGED")
        if any(vals[k] is not None for k in
            current["separate_2026_retrospective_native_19_Elo_NOT_historic_PIT"]):
            raise Historic74Error("FALSE_PROMOTION_RETRO_ELO")
        if not (_utc(src["witness"])<target["ko"]):
            raise Historic74Error("PUBLIC_SOURCE_PUBLISHED_AFTER_TARGET")
        if complete:complete_xg5+=1
        new_status=("PINNED_GHARCHIVE_FPL_PLAYER_XG5_ALTERNATIVE_RESEARCH"
              if complete else "PINNED_GHARCHIVE_PUBLIC_FT_FORM5_RESEARCH")
        current["public_source_research_121_numeric_features"]=vals
        current["public_source_research_38_missing_flags"]=flags
        current["history_public_asof_source"]={
            "status":new_status,"sha":src["commit"],"witness_utc":src["witness"],
            "provider":"vaastav_FPL_OPTA_PLAYER_XG_NOT_PITCHAPI",
            "original_FPL_fixture_sha256":src["source"]["sha"],
            "older_historical_GHArchive_anchor":src["source"]["GHArchive_actual_old_descendant_sha"],
            "older_historical_GHArchive_event":src["source"]["GHArchive_old_event_id"],
            "FPL_player_xG_original_blob_sha256":xg["sha256"] if xg else None,
            "external_xG_definition_is_NOT_original_PitchAPI":True}
        current["original_native_121_plus_38_certified"]=False
        source_methods[new_status]+=1;matched+=1
        if old_status=="NO_QUALIFIED_OLD_PUBLIC_F5":promoted+=1
        audit_rows.append({"native_fixture_id":ident,"season":target["season"],
            "kickoff_utc":current["kickoff_utc"],
            "original_source_commit":src["commit"],
            "historic_publication_upper_bound_utc":src["witness"],
            "prior_both_team_FORM5_verified":True,
            "complete_ALTERNATIVE_fpl_player_xG5":complete,
            "merged_FPL_player_blob_sha256":xg["sha256"] if xg else None,
            "same_original_PitchAPI_native_match_identity_join":True,
            "original_PitchAPI_xG_equivalence_or_publication_proven":False})
    if len({r["native_fixture_id"] for r in audit_rows})!=len(audit_rows):
        raise Historic74Error("DUPLICATE_RESEARCH_TRAIN_TARGET")
    all_source_train=sum(x["partition"]=="TRAIN" and
       x["history_public_asof_source"]["status"]!="NO_QUALIFIED_OLD_PUBLIC_F5"
       for x in matrix)
    if (all_source_train<54 or all_source_train>760 or
        sum(x["partition"]=="VALIDATION" and x["history_public_asof_source"]["status"].startswith("PINNED")
         for x in matrix)!=109):
        raise Historic74Error("BASELINE_TRAIN_VALIDATION_COUNTS_DRIFT")
    if any(x["original_native_121_plus_38_certified"] is not False for x in matrix):
        raise Historic74Error("FALSE_ORIGINAL_M1_ADMISSION")
    # Preserve VAL exact old data, no TEST or original target scores.
    return {
      "schema":SCHEMA,"original_74_fpl_revisions_examined":74,
      "historically_attested_candidate_revisions":len(proven),
      "successfully_parsed_old_source_fixture_versions":len(sources),
      "old_source_versions_blocked":failures,
      "original_760_TRAIN_public_FORM5_total_after_74":all_source_train,
      "additional_TRAIN_public_FORM5_over_previous_54":all_source_train-54,
      "TRAIN_targets_verified_from_74":matched,
      "TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5":complete_xg5,
      "distinct_old_merged_FPL_player_xG_SHA_attempted":len(xg_cache),
      "historical_FPL_xG_blob_failures":dict(bad_xg),
      "train_public_source_statuses":dict(source_methods),
      "original_380_VALIDATION_FORM5_preserved":109,
      "original_380_VALIDATION_ALTERNATIVE_xG5_preserved":107,
      "original_1140_native_ID_121_plus_38_matrix_rows":1140,
      "Elo_19_retro_per_row_kept_separate":True,
      "historical_FPL_xG_is_player_sum_not_PitchAPI_team_xG":True,
      "original_native_159_PIT_TRAIN_eligible":0,
      "original_native_159_PIT_VALIDATION_eligible":0,
      "CatBoost_M1_original_fitted":False,
      "TEST_2026_27_read":False,"GATE14":"PENDING",
      "source_verified_train_records":audit_rows
    },matrix

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",required=True)
    p.add_argument("--matrix",required=True)
    a=p.parse_args()
    summary=Path(a.summary);target=Path(a.matrix)
    if summary.exists() or target.exists():raise Historic74Error("APPEND_ONLY_NO_OVERWRITE")
    out,rows=run()
    summary.parent.mkdir(parents=True,exist_ok=True);target.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(target,"wt",encoding="utf8",compresslevel=7) as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n")
    out["matrix_gzip_sha256"]=sha256(target.read_bytes()).hexdigest()
    summary.write_text(json.dumps(out,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"all_revisions":74,"train_form5":out["original_760_TRAIN_public_FORM5_total_after_74"],
      "train_new":out["additional_TRAIN_public_FORM5_over_previous_54"],
      "fpl_xG5_alternative":out["TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5"],
      "VALIDATION_FORM5":109,"M1_fit":False,"gate14":"PENDING"},sort_keys=True))

if __name__=="__main__":main()
