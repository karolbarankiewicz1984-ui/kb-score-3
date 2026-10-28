"""Step14 full 1140 TRAIN+VALIDATION native fixture <> genuinely dated old public sources.

Separates three different claims: (1) exact identity of original PitchAPI
native fixture + teams (from current native catalog and frozen original safe
IDs), (2) independently published prior public fixture results (GitHub
GHArchive old SHA), and (3) original PitchAPI as-of provenance. (3) remains
unproved, so NEVER train original CatBoost or read TEST/target scores.
No native team ID, current/historic goals or exact xG values are serialized.
"""
from __future__ import annotations
import argparse,datetime,json,os
from collections import defaultdict,Counter
from hashlib import sha256
from pathlib import Path
from src.kb3_step14_a_nonxg_1140_pit_matrix import construct as verify_safe
from src.kb3_step14_multiseason_pit import SOURCES,raw_url,fetch,utc,parse_openfootball,verify_existing_clocks
from src.kb3_step14_fpl_form5_lineage import parse_fixture_rows
from src.kb3_step14_fpl_historic_clock_pilot import verify_raw_csv
from src.kb3_step14_native_team_crosswalk import canonical_team_name
from scripts.step14_multiseason_owner_native_join_local import ADDITIONAL_2023,map_fpl_team_ids_by_finished_clock
from src.kb3_step14_owner_elo_2023_to_2024 import FULL_2023,check_pinned_public_evidence
from src.kb3_pitch_native import check_season
from scripts.pitchapi_step06_audit import norm,to_plain

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-three-season-1140-exact-native-public-PIT-match-lineage-v1"
BASE_SOURCES=(SOURCES[0],dict(ADDITIONAL_2023,provider='FPL'),
              dict(FULL_2023,season='2023-24',provider='FPL'),SOURCES[1],SOURCES[2])
NEW_2023_PROOF=ROOT/"data/audits/STEP14_NEW_FOUR_INDEPENDENT_GHARCHIVE_SNAPSHOTS_2023_24_2026-10-28.json"
ADDED_2023_PINNED={
 "8b05861fb33ee89bae34c2b6d06564449a5885db":("2023-09-25T15:34:10Z","32084180987","1dcc0fd05aaa43b93cb3136e8907d4a6aec653ed1214abd90da370e283aa3dac",59),
 "546143eb5d0ae6d250e074374152e8be4b15719b":("2024-01-23T13:01:36Z","35049350413","fbfd0780fd97b29fee22e35a3e826270200ab7f051654ea0f52bcea831c7025b",208),
 "f061aafa88a921dd70fd2b0f72b8020889d8e589":("2024-02-22T10:23:48Z","35904934811","8b3849fcba1d4bc09dc259269c7ae35a74e9f3546e67833fe2635ffdc2c4be95",250),
 "436f1ff2d306783d3e3892dc3d3ce21712cbc08e":("2024-04-08T10:31:24Z","37259299021","0f0f380b8ac935c9a3c2f97235172759fcd4d4c60d5488ea85bd206aaf730da3",313)
}
def independently_pinned_sources():
    proof=json.loads(NEW_2023_PROOF.read_text(encoding="utf8"))
    sources=proof.get("verified_sources",[])
    if (proof.get("schema")!="kb3-step14-verified-new-4-FPL-2023-historic-clock-evidence-v1"
        or proof.get("source_artifact_id")!=12840930348
        or len(sources)!=4
        or {x.get("commit") for x in sources}!=set(ADDED_2023_PINNED)):
        raise ReconstructError("NEW_PUBLIC_HISTORICAL_GHARCHIVE_WITNESS_CHANGED")
    for x in sources:
        expect=ADDED_2023_PINNED[x["commit"]]
        if ((x.get("push"),x.get("event"),x.get("sha"),x.get("ft"))!=expect
            or x.get("season")!="2023-24" or x.get("provider")!="FPL"
            or x.get("repo")!="vaastav/Fantasy-Premier-League"
            or x.get("path")!="data/2023-24/fixtures.csv"
            or x.get("external_publication_evidence_verified") is not True):
            raise ReconstructError("NEW_HISTORIC_GHARCHIVE_PUBLISHED_SHA_NOT_PINNED")
    all_sources=tuple(sorted(BASE_SOURCES+tuple(sources),
                  key=lambda x:x["push"]))
    if len(all_sources)!=9 or len({x["commit"] for x in all_sources})!=9:
        raise ReconstructError("HISTORIC_PUBLIC_SOURCES_NOT_NINE_DISTINCT")
    return all_sources
class ReconstructError(ValueError):pass

def old_source_rows(src,*,fetcher=fetch):
    repo=src["repo"];base=f"https://raw.githubusercontent.com/{repo}/{src['commit']}/{src['path']}"
    raw=fetcher(base,limit=3_000_001)
    if sha256(raw).hexdigest()!=src["sha"]:
        raise ReconstructError("OLD_PUBLIC_SOURCE_BYTES_CHANGED")
    if src.get("provider","FPL")=="FPL":
        verify_raw_csv(raw,expected_finished=src["ft"],push_time_utc=src["push"])
        items=parse_fixture_rows(raw)
        return [{"source_fixture_id":r["id"],"home":r["team_h"],"away":r["team_a"],
                 "utc":r["kickoff_time"],"finished":r["finished"]=="True"}
                for r in items]
    else:
        out=parse_openfootball(raw,src)
        return [{"source_fixture_id":None,"home":r["home"],"away":r["away"],
                 "utc":r["kickoff"].isoformat().replace("+00:00","Z") if r["kickoff"] else None,
                 "finished":r["ft_published"]} for r in out]

def native_three_seasons(*,key,client_factory=None):
    if not key:raise ReconstructError("CURRENT_PITCHAPI_API_KEY_MISSING")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    cli=client_factory(api_key=key);count=0
    def call(fn,*args,**kw):
        nonlocal count
        if count>=4:raise ReconstructError("MAX_FOUR_REAL_SPORTS_API_CALLS")
        count+=1
        try:return to_plain(fn(*args,**kw))
        except Exception:raise ReconstructError("PITCHAPI_SDK_CALL_FAILED") from None
    catalog=call(cli.leagues.list)
    found=[x for x in catalog.get("leagues",[])
       if norm(x.get("name")).replace(" ","")=="premierleague"
       and str(x.get("country_code","")).upper()=="ENG"
       and all(s in (x.get("seasons") or []) for s in
               ("2023/2024","2024/2025","2025/2026"))]
    if len(found)!=1:raise ReconstructError("THREE_SEASONS_NOT_ONE_ORIGINAL_PROVIDER_LEAGUE")
    result={}
    for year in (2023,2024,2025):
        season=f"{year}/{year+1}"
        payload=call(cli.leagues.matches,found[0]["id"],season=season)
        matches=payload.get("matches")
        check_season(matches,season,expected_count=380)
        if any(m["status"]!="finished" for m in matches):
            raise ReconstructError("ORIGINAL_SEASON_NOT_FINISHED")
        result[f"{year}-{(year+1)%100:02d}"]=matches
    return result,count

def exact_source_map(src,srcrows,native,team_map_2023):
    """Per source exact original fixture identity; output only in-memory IDs."""
    season=src["season"]
    native_map={};kicks={}
    for m in native[season]:
        h,a=m["home_team"],m["away_team"]
        if season=="2023-24":
            key=(h["id"],a["id"],m["time_utc"])
        else:
            key=(canonical_team_name(h["name"]),
                 canonical_team_name(a["name"]),m["time_utc"])
        if key in native_map:raise ReconstructError("NATIVE_DUPLICATE_IDENTITY")
        native_map[key]=m["id"]
        kicks[m["id"]]=m["time_utc"]
    mapped={};miss=0
    for r in srcrows:
        if season=="2023-24":
            key=(team_map_2023[r["home"]],team_map_2023[r["away"]],r["utc"])
        else:
            key=(r["home"],r["away"],r["utc"])
        if r["utc"] is None:
            miss+=1;continue
        ident=native_map.get(key)
        if ident is None:
            miss+=1;continue
        if ident in mapped:raise ReconstructError("DUPLICATE_PUBLIC_SOURCE_TO_NATIVE_JOIN")
        mapped[ident]={"finished":r["finished"],"published_at":src["push"],
                       "source_fixture_id":r["source_fixture_id"]}
    return mapped,miss

def all_1140_pit(*,safe,native,sources,selected):
    source_rows=sources
    if set(native)!={"2023-24","2024-25","2025-26"} or any(len(v)!=380 for v in native.values()):
        raise ReconstructError("NATIVE_ORIGINAL_THREE_SEASONS_NOT_FULL")
    safe_meta,_=verify_safe(safe)
    ix={r["fixture_id"]:(r["partition"],r["kickoff_utc"]) for r in safe["fixtures"]
        if r.get("partition") in ("TRAIN","VALIDATION")}
    actual={m["id"]:(season,m) for season,items in native.items() for m in items}
    if len(ix)!=1140 or len(actual)!=1140 or set(actual)!=set(ix):
        raise ReconstructError("CURRENT_PITCHAPI_VS_ORIGINAL_FROZEN_1140_IDS_NOT_BIJECTIVE")
    for ident,(season,m) in actual.items():
        partition,ko=ix[ident]
        if (ko!=m["time_utc"] or
            partition!=("VALIDATION" if season=="2025-26" else "TRAIN")):
            raise ReconstructError("ORIGINAL_FROZEN_VS_CURRENT_PROVIDER_KICKOFF_ROLE_CHANGED")
    # Global exact FPL 2023 team mapping is learned from all finished fixtures
    # (never from results), then applied unchanged to older Oct/Dec snapshots.
    frozen_fpl=source_rows[FULL_2023["commit"]]
    native_2023={m["id"]:{"season":"2023-24","kickoff_utc":m["time_utc"],
        "home_id":m["home_team"]["id"],"away_id":m["away_team"]["id"]}
        for m in native["2023-24"]}
    fullraw=source_rows[FULL_2023["commit"]+"_RAW"]
    mp=map_fpl_team_ids_by_finished_clock(parse_fixture_rows(fullraw),
         native_2023,season="2023-24",published_at=FULL_2023["push"],
         expected_finished=380)
    bysource={};join_counts={}
    for src in selected:
        rows=source_rows[src["commit"]]
        mapping,unmatched=exact_source_map(src,rows,native,mp)
        bysource[src["commit"]]=mapping
        join_counts[src["commit"]]={"season":src["season"],
            "old_rows_exact_native_home_away_and_kickoff":len(mapping),
            "unmatched_due_to_changed_old_schedule_or_source_time":unmatched}
    byseason={k:sorted(v,key=lambda m:(m["time_utc"],m["id"])) for k,v in native.items()}
    output=[];candidate_counts=Counter();best=Counter();missing_counts=Counter()
    total_last5=0
    for ident in sorted(ix,key=lambda fid:(ix[fid][1],fid)):
        season,m=actual[ident];kickoff=utc(m["time_utc"])
        predecessors=[p for p in byseason[season] if
                      utc(p["time_utc"])<kickoff and p["id"]!=ident]
        sides=(m["home_team"]["id"],m["away_team"]["id"])
        team_prior={side:[p for p in predecessors
                    if side in (p["home_team"]["id"],p["away_team"]["id"])]
                    for side in sides}
        attempted=0;qualifying=[];notes=Counter()
        for src in selected:
            if src["season"]!=season or utc(src["push"])>=kickoff:
                continue
            attempted+=1
            mapped=bysource[src["commit"]]
            target=mapped.get(ident)
            if target is None:
                notes["TARGET_NOT_IN_EXACT_OLD_SOURCE_SCHEDULE"]+=1;continue
            if target["finished"]:
                notes["OLD_SNAPSHOT_TARGET_ALREADY_PLAYED"]+=1;continue
            # Source must be before target and all preceding games published
            # after their results; current retrospective scores are never read.
            needed=set()
            for history in team_prior.values():
                needed.update(p["id"] for p in history)
            valid=True;complete=0
            for oldid in needed:
                p=actual[oldid][1]
                if (oldid not in mapped or not mapped[oldid]["finished"] or
                    utc(p["time_utc"])+datetime.timedelta(hours=3)>utc(src["push"])):
                    valid=False;break
                complete+=1
            if not valid:
                notes["SOME_TRUE_PREDECESSOR_NOT_IN_OLD_SOURCE"]+=1;continue
            full5=all(len(team_prior[side])>=5 for side in sides)
            qualifying.append({"source_commit":src["commit"],
                  "source_published_at_utc":src["push"],
                  "verified_exact_native_prior_fixture_count":complete,
                  "both_have_five_prior_games":full5,
                  "all_same_season_predecessor_FT_in_old_source":True})
        candidate_counts[attempted]+=1
        if qualifying:
            selected=max(qualifying,key=lambda q:q["source_published_at_utc"])
            best["SOURCE_PRIOR_RESULTS_COMPLETE_ALL_SAME_SEASON"]+=1
            if selected["both_have_five_prior_games"]:
                best["BOTH_TEAM_5_PRIOR_RESULTS_PUBLIC"]+=1;total_last5+=1
            rank="PUBLIC_OLD_RESULTS_ALL_PREDECESSORS_SOURCE_ONLY"
            basis=selected
        else:
            rank="NO_COMPLETE_SOURCE_BACKED_PRIOR_RESULT_CHAIN"
            basis=None
        if not basis:
            for key,n in notes.items():missing_counts[key]+=n
        output.append({"fixture_id":ident,"partition":ix[ident][0],
          "season":season,"kickoff_utc":m["time_utc"],
          "independent_older_source_candidates_checked":attempted,
          "public_result_source_lineage_state":rank,
          "best_old_public_source":basis,
          "original_PitchAPI_73_nonxg_fields_asof_proven":False,
          "original_PitchAPI_team_xg_first_published_proven":False,
          "actual_provider_historic_feature_cutoff_utc":None,
          "original_121_plus_38_PIT_training_eligible":False})
    result={"schema":SCHEMA,
      "frozen_native_safe_SHA":safe["projection_sha256"],
      "original_exact_native_ID_and_kickoff_joins":1140,
      "train":760,"validation":380,
      "historical_sources_checked":len(selected),
      "old_to_native_source_exact_join_counts":join_counts,
      "candidate_source_count_by_target":dict(sorted(candidate_counts.items())),
      "best_source_state_counts":dict(sorted(best.items())),
      "reason_counts_for_unavailable_old_source":dict(sorted(missing_counts.items())),
      "per_target_frozen_source_provenance_records":len(output),
      "all_prior_FT_in_real_old_public_source_both_teams":best["SOURCE_PRIOR_RESULTS_COMPLETE_ALL_SAME_SEASON"],
      "both_teams_form5_source_available":total_last5,
      "public_old_FT_does_not_prove_native_PitchAPI_PIT_or_121_plus_38":True,
      "old_FPL_player_xG_not_PitchAPI_team_xG":True,
      "original_train_certified_PIT":0,"original_validation_certified_PIT":0,
      "original_CatBoost_M1_fit_allowed":False,
      "test_examined":False,"target_result_scores_accessed":False,
      "model_or_split_modified":False,"gate14_pass":False}
    return result,output

def live_run(key,*,client_factory=None,fetcher=fetch):
    root=ROOT; verify_existing_clocks(root)
    check_pinned_public_evidence(json.loads((root/
       "data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json").read_text()))
    sources={}
    selected=independently_pinned_sources()
    for s in selected:
        raw=fetcher(f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/{s['path']}",limit=3_000_001)
        if sha256(raw).hexdigest()!=s["sha"]:
            raise ReconstructError("EXTERNALLY_PINNED_PUBLIC_SOURCE_CHANGED")
        sources[s["commit"]]=old_source_rows(s,fetcher=lambda url,**kwargs:raw)
        if s["commit"]==FULL_2023["commit"]:
            sources[s["commit"]+"_RAW"]=raw
    native,ncalls=native_three_seasons(key=key,client_factory=client_factory)
    safe=json.loads((root/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
    report,records=all_1140_pit(safe=safe,native=native,sources=sources,selected=selected)
    report["current_read_UTC_NOT_HISTORIC_PUBLICATION"]=datetime.datetime.now(
       datetime.timezone.utc).isoformat().replace("+00:00","Z")
    report["actual_current_PitchAPI_API_calls"]=ncalls
    return report,records

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True);p.add_argument("--rows",required=True)
    a=p.parse_args()
    dest=Path(a.report);rows=Path(a.rows)
    if dest.exists() or rows.exists():raise ReconstructError("APPEND_ONLY_OUTPUT_ALREADY_EXISTS")
    dest.parent.mkdir(parents=True,exist_ok=True);rows.parent.mkdir(parents=True,exist_ok=True)
    try:
        result,records=live_run(os.environ.get("PITCHAPI_API_KEY",""))
        (dest).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
        with rows.open("x",encoding="utf8") as f:
            for row in records:
                f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n")
        print(json.dumps({"state":"REAL_1140_PUBLIC_PREMATCH_SOURCE_LINEAGE_FINISHED",
              "native_fixture_joins":result["original_exact_native_ID_and_kickoff_joins"],
              "public_form5_targets":result["both_teams_form5_source_available"],
              "all_previous_source_ft":result["all_prior_FT_in_real_old_public_source_both_teams"],
              "provider_original_full_pit":False,"gate14_pass":False},sort_keys=True))
    except Exception as e:
        # SDK errors may contain sensitive headers, never print them.
        import traceback
        frames=[(Path(x.filename).name,x.name,x.lineno)
                for x in traceback.extract_tb(e.__traceback__)][-4:]
        # Names, function names and line numbers only; NO SDK error text.
        print("FULL_NATIVE_PUBLIC_PIT_RECONSTRUCTION_BLOCKED",
              type(e).__name__,"source_location",repr(frames))
        raise SystemExit(3)
if __name__=="__main__":main()
