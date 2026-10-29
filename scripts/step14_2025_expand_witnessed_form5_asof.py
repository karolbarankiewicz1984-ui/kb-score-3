"""Expand strictly witnessed 2025/26 public FORM5 and source xG beyond 18.

Every source is an OLD pinned commit, independently server-witnessed by public
GitHub Actions main run. No target score used, no original native xG substituted.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
from scripts.step14_fpl_core_2025_independent_asof import (
    SOURCES as FOUR, REPO, _read_matches, _read_teams, _fetch_raw,
    _get_json, _utc, _reference, _qualify_target, actions_witness,
    CandidateError)
from scripts.step14_fplcore_native_2025_crosswalk_semantics import load_public

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-2025-fplcore-extended-old-GitHub-witnessed-public-FORM5-xG-v1"
# SHA, GitHub Actions run ID, gameweek availability max, server-created run UTC.
EXTRA=(
    ("126b9ffec2076a9a42458e7e4fd5d555968f305d",19279791484,12,"2025-11-11T22:06:28Z"),
    ("49c4a6573492e7c5fb020ee4d650e60baf0f138b",20071891722,15,"2025-12-09T17:04:53Z"),
    ("1a3e9917b4a9e5bd3629557354dc7b7f4c17924f",20376914645,17,"2025-12-19T17:03:42Z"),
    ("dd71bba4a8eb5bc71f3749b7458554bd50749672",20859461952,21,"2026-01-09T17:06:07Z"),
    ("2c00c3886c421d488ff017d83e96631474b80847",21817774292,24,"2026-02-09T08:31:00Z"),
    ("fde4aaa35eabb9d0a247039f99b34ab46a7f7de6",22362135047,27,"2026-02-24T17:22:54Z"),
    ("0584db7dd55de2d3c35d3799ea479c80ad5d233a",23637824776,31,"2026-03-27T08:31:03Z"),
    ("cf95db2c2fc3635e8f5ff53a53af31efed9e7130",24436336657,33,"2026-04-15T04:25:45Z"),
    ("137ff45d53197e3a6839339a92b5d6ea0f0f0da8",25224669814,35,"2026-05-01T17:21:56Z"),
    ("254862a0b966d43c428840dfbf550b84c8d47094",25661785696,37,"2026-05-11T09:25:47Z"),
)
ALL=tuple(sorted((*FOUR,*EXTRA),key=lambda z:_utc(z[3])))
assert len(ALL)==14 and len({s[0] for s in ALL})==14

class ExtendedEvidenceError(ValueError): pass

def source_at_version(item,reference,*,fetcher=_fetch_raw,gh_json=_get_json,include_predecessors=False):
    commit,run,top,clock=item
    witness=actions_witness(commit,run,clock,gh_json)
    raw,hash_teams=fetcher(commit,"data/2025-2026/By Gameweek/GW10/teams.csv")
    teams=_read_teams(raw)
    old={}
    quarantine={}
    blobs={}
    def load(gw):
        buf,digest=fetcher(commit,f"data/2025-2026/By Gameweek/GW{gw}/matches.csv")
        try: return gw,digest,_read_matches(buf,witness=clock,teams=teams),None
        except CandidateError as exc:
            if str(exc) in ("FUTURE_OR_RECENT_FT_IN_OLD_SNAPSHOT", "INVALID_MATCH_SCORE",
                               "MISSING_TIME", "INVALID_TIME", "NON_UTC_TIME"):
                return gw,digest,{},str(exc)+"_QUARANTINED"
            raise
    with ThreadPoolExecutor(max_workers=7) as pool:
        jobs=[pool.submit(load,gw) for gw in range(1,top+1)]
        for f in as_completed(jobs):
            gw,digest,data,err=f.result()
            blobs[str(gw)]=digest
            if err:quarantine[str(gw)]=err
            for key,value in data.items():
                if key in old:raise ExtendedEvidenceError("DUPLICATED_PRIOR_FINISHED_MATCH")
                old[key]=value
    index={r["key"] for r in reference}
    prior={k:v for k,v in old.items() if k in index}
    valid=[]
    for match in reference:
        a=_qualify_target(match,_utc(clock),prior,reference)
        if a is None:continue
        a["evidence_source_commit"]=commit
        a["evidence_github_run_id"]=run
        valid.append(a)
    report={"sha":commit,"witness":witness,
            "team_file_sha256":hash_teams,
            "gameweek_file_sha256":dict(sorted(blobs.items(),key=lambda x:int(x[0]))),
            "quarantined_gameweeks":dict(sorted(quarantine.items(),key=lambda x:int(x[0]))),
            "valid_prior_premier_league_rows":len(old),
            "exact_public_reference_prior_rows":len(prior),
            "public_FORM5_future_targets":len(valid),
            "alternative_xG5_complete_future_targets":sum(
                all(not t["prematch_public_FORM5"][k]["alternative_xg_missing"]
                    for k in ("home","away")) for t in valid)}
    return (report,valid,prior) if include_predecessors else (report,valid)

def audit(root=ROOT,*,fetcher=_fetch_raw,gh_json=_get_json):
    original,_=load_public(root)
    ref=_reference(Path(root)/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json")
    seen={}
    source_reports=[]
    # Quarantining a defective file does not contaminate other old versions.
    for row in ALL:
        proof,found=source_at_version(row,ref,fetcher=fetcher,gh_json=gh_json)
        source_reports.append(proof)
        for x in found:
            key=(x["target_public_home"],x["target_public_away"],x["target_kickoff_utc"])
            if key not in seen or _utc(x["source_publication_witness_utc"])>_utc(seen[key]["source_publication_witness_utc"]):
                seen[key]=x
    # Previously published immutable 18 candidates cannot disappear.
    missing=[]
    for old in original["candidates"]:
        key=(old["target_public_home"],old["target_public_away"],old["target_kickoff_utc"])
        if key not in seen:
            missing.append(key)
    if missing:raise ExtendedEvidenceError("ORIGINAL_18_SOURCE_TARGETS_LOST")
    rows=sorted(seen.values(),key=lambda x:(x["target_kickoff_utc"],x["target_public_home"],x["target_public_away"]))
    extra=len(rows)-18
    return {"schema":SCHEMA,"source_repo":REPO,
            "original_confirmed_18_preserved":True,
            "historical_versions_count":len(source_reports),
            "new_source_versions_count":len(EXTRA),
            "sources":source_reports,
            "total_distinct_prematch_public_FORM5_targets":len(rows),
            "new_unique_targets_beyond_original_18":extra,
            "distinct_alternative_source_xg5_targets":sum(
                all(not x["prematch_public_FORM5"][k]["alternative_xg_missing"]
                    for k in ("home","away")) for x in rows),
            "public_no_score_reference_size":len(ref),
            "original_native_fixture_IDs_revalidated_for_new_targets":False,
            "old_historic_GitHub_server_source_clocks_verified":True,
            "source_feature_semantics_not_original_native_PitchAPI":True,
            "full_native_121_38_M1_PIT_rows_certified":0,
            "M1_trained":False,
            "TEST_2026_27_examined":False,
            "GATE14":"PENDING",
            "targets":rows}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    output=Path(a.out)
    if output.exists():raise ExtendedEvidenceError("APPEND_ONLY_REPORT_EXISTS")
    output.parent.mkdir(parents=True,exist_ok=True)
    report=audit()
    output.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({"witnessed_versions":report["historical_versions_count"],
                       "form5_targets":report["total_distinct_prematch_public_FORM5_targets"],
                       "new_beyond_18":report["new_unique_targets_beyond_original_18"],
                       "xg5_targets":report["distinct_alternative_source_xg5_targets"],
                       "original_M1_PIT":0,"gate14":"PENDING"},sort_keys=True))

if __name__=="__main__":
    main()
