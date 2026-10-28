"""B: real GitHub Actions PitchAPI secret, exact full 380-fixture FPL/Opta xG.

No RSA, no Windows, no target labels/TEST/odds. Original FPL fixture+team
identity is reconstructed from the FULL 380 MATCH kickoff/home/away graph,
using current PitchAPI native IDs only transiently; no fuzzy alias joins,
score matches, private source file, response dump or API token in output.
Can compare retrospective values now, cannot prove their 2023 first publication.
"""
from __future__ import annotations
import argparse,json,os
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from src.kb3_step14_owner_elo_2023_to_2024 import FULL_2023,check_pinned_public_evidence
from src.kb3_step14_xg_four_gates import extract_public_xg,FULL_MERGED_PATH,FULL_MERGED_SHA
from src.kb3_step14_multiseason_pit import fetch,utc
from src.kb3_step14_fpl_form5_lineage import parse_fixture_rows
from scripts.step14_multiseason_owner_native_join_local import map_fpl_team_ids_by_finished_clock
from scripts.pitchapi_step06_audit import norm,to_plain
from src.kb3_pitch_native import check_season
from src.kb3_step14_pitchapi_xg_semantics import aggregate,side_comparison,SemanticAuditError

ROOT=Path(__file__).resolve().parents[1]
SAMPLE_INDICES=(20,84,148,212,276,340)
MAX_CALLS=14 # catalog + exact full 380 2023 native fixtures + 2*6 shots/stats
class BSourceError(ValueError):pass

def old_fpl(fetcher=fetch):
    proof=json.loads((ROOT/"data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json").read_text())
    check_pinned_public_evidence(proof)
    base=f"https://raw.githubusercontent.com/{FULL_2023['repo']}/{FULL_2023['commit']}/"
    f=fetcher(base+FULL_2023["path"],limit=3_000_001)
    x=fetcher(base+FULL_MERGED_PATH,limit=40_000_001)
    if sha256(f).hexdigest()!=FULL_2023["sha"] or sha256(x).hexdigest()!=FULL_MERGED_SHA:
        raise BSourceError("PUBLIC_HISTORIC_FPL_BLOB_HASH_CHANGED")
    s=extract_public_xg(f,x,published_at=FULL_2023["push"],
         pinned_fixture_sha=FULL_2023["sha"],pinned_player_sha=FULL_MERGED_SHA)
    if s["finished_fixtures"]!=380 or s["side_count_with_xg"]!=760:
        raise BSourceError("PUBLIC_SOURCE_NOT_FULL_380_760")
    return parse_fixture_rows(f),s

def exact_current_native_graph_join(rows,pitch_matches,source):
    check_season(pitch_matches,"2023/2024",expected_count=380)
    if len({m["id"] for m in pitch_matches})!=380:
        raise BSourceError("DUPLICATE_NATIVE_MATCH")
    if any(m.get("status")!="finished" for m in pitch_matches):
        raise BSourceError("ORIGINAL_2023_NOT_ALL_FINISHED")
    native={m["id"]:{"season":"2023-24","kickoff_utc":m["time_utc"],
                       "home_id":m["home_team"]["id"],"away_id":m["away_team"]["id"]}
            for m in pitch_matches}
    # Must be a global 20-team 38 home/away event-fingerprint bijection.
    # Every original fixture, not merely chosen 6, must match exactly.
    mp=map_fpl_team_ids_by_finished_clock(rows,native,season="2023-24",
         published_at=FULL_2023["push"],expected_finished=380)
    reverse={}
    for m in pitch_matches:
        key=(m["home_team"]["id"],m["away_team"]["id"],m["time_utc"])
        if key in reverse:raise BSourceError("DUPLICATE_NATIVE_SCHEDULE_PAIR")
        reverse[key]=m
    checked=set()
    for r in rows:
        key=(mp[r["team_h"]],mp[r["team_a"]],r["kickoff_time"])
        m=reverse.get(key)
        if m is None or m["id"] in checked:
            raise BSourceError("FPL_VS_NATIVE_380_FIXTURE_IDENTITY_FAIL")
        checked.add(m["id"])
    if len(checked)!=380:raise BSourceError("FULL_380_NOT_BIJECTIVE")
    ordered=sorted(rows,key=lambda r:(utc(r["kickoff_time"]),int(r["id"])))
    selected=[]
    for n in SAMPLE_INDICES:
        r=ordered[n]
        m=reverse[(mp[r["team_h"]],mp[r["team_a"]],r["kickoff_time"])]
        idh,ida=int(r["team_h"]),int(r["team_a"])
        fid=int(r["id"])
        if (fid,idh) not in source["source_side_xg_values_IN_MEMORY_ONLY"] or (
            fid,ida) not in source["source_side_xg_values_IN_MEMORY_ONLY"]:
            raise BSourceError("SAMPLED_FPL_TEAM_XG_NOT_PRESENT")
        selected.append((m["id"],m["home_team"]["id"],m["away_team"]["id"],fid,idh,ida))
    if len(selected)!=6 or len({s[0] for s in selected})!=6:
        raise BSourceError("DETERMINISTIC_SIX_MATCHES_NOT_UNIQUE")
    return selected

def compare_live(key,*,provider_factory=None,fetcher=fetch):
    if not isinstance(key,str) or not key.strip():raise BSourceError("PITCHAPI_SECRET_UNAVAILABLE")
    if provider_factory is None:
        from pitchapi import PitchAPI
        provider_factory=PitchAPI
    rows,source=old_fpl(fetcher)
    client=provider_factory(api_key=key)
    requests=0
    def call(method,*args,**kwargs):
        nonlocal requests
        if requests>=MAX_CALLS:raise BSourceError("API_CALL_BUDGET_EXCEEDED")
        requests+=1
        try:return to_plain(method(*args,**kwargs))
        except Exception:
            raise BSourceError("SDK_SOURCE_REQUEST_FAILED") from None
    catalog=call(client.leagues.list)
    if not isinstance(catalog,dict) or not isinstance(catalog.get("leagues"),list):
        raise BSourceError("PITCH_CATALOG_SCHEMA_UNSUPPORTED")
    candidates=[x for x in catalog["leagues"]
        if norm(x.get("name")).replace(" ","")=="premierleague"
        and str(x.get("country_code","")).upper()=="ENG"
        and "2023/2024" in (x.get("seasons") or [])]
    if len(candidates)!=1:raise BSourceError("NO_UNIQUE_2023_ENGLAND_LEAGUE")
    listing=call(client.leagues.matches,candidates[0]["id"],season="2023/2024")
    if not isinstance(listing,dict) or not isinstance(listing.get("matches"),list):
        raise BSourceError("PITCH_2023_MATCHES_SCHEMA_UNSUPPORTED")
    selected=exact_current_native_graph_join(rows,listing["matches"],source)
    observed=[]
    for mid,home,away,fid,fh,fa in selected:
        shots=call(client.matches.shots,mid)
        stats=call(client.matches.stats,mid)
        try:
            observed.extend(side_comparison(match_id=mid,home_id=home,away_id=away,
                source_shots=shots,source_stats=stats,
                fpl_side_values=source["source_side_xg_values_IN_MEMORY_ONLY"],
                public_fixture_id=fid,fpl_home_id=fh,fpl_away_id=fa))
        except SemanticAuditError as e:
            if str(e)=="TEAM_STATS_XG_FIELD_NOT_UNIQUE":
                # Only schema labels, never match IDs, values or payloads.
                data=stats.get("data",stats)
                periods=data.get("periods",[]) if isinstance(data,dict) else []
                labels=[]
                for pp in periods if isinstance(periods,list) else []:
                    if not isinstance(pp,dict):continue
                    if pp.get("period")!="All":continue
                    for gg in pp.get("groups",[]):
                        if isinstance(gg,dict):
                            for item in gg.get("items",[]):
                                if isinstance(item,dict) and isinstance(item.get("key"),str):
                                    k=item["key"]
                                    if k.isascii() and k.replace("_","").isalnum() and len(k)<=45:
                                        labels.append(k)
                raise BSourceError("STATS_ALL_PUBLIC_SCHEMA_KEYS:"+",".join(sorted(set(labels))[:32])) from None
            raise
    result=aggregate(observed)
    result["schema"]="kb3-step14-B-real-2023-pitchapi-vs-old-fpl-exact-380-identity-6-samples-v1"
    result["provider_request_count"]=requests
    result["whole_season_exact_fixture_home_away_identity_matches"]=380
    result["six_match_selection"]="chronological indices 20,84,148,212,276,340"
    result["source_FPL_independently_published_at_utc"]=FULL_2023["push"]
    result["PitchAPI_retrieved_at_utc_NOT_original_first_publication"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    result["PitchAPI_provider_original_first_published_at_utc"]=None
    result["original_2023_to_2025_provider_PIT_certified"]=False
    result["training_allowed"]=False
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise BSourceError("OUTPUT_APPEND_ONLY")
    try:
        report=compare_live(os.environ.get("PITCHAPI_API_KEY",""))
        report["live_comparison_state"]="REAL_SIX_MATCH_SEMANTIC_COMPARISON_COMPLETE"
    except Exception as exc:
        # No exception message: upstream SDK can include request/token details.
        report={"schema":"kb3-step14-B-real-2023-pitchapi-vs-fpl-v1",
                "live_comparison_state":"REAL_API_OR_MATCH_SEMANTICS_BLOCKED",
                "safe_error_class":type(exc).__name__,
                "safe_error_reason_code":str(exc) if isinstance(exc,(BSourceError,SemanticAuditError)) else "OPAQUE_NON_SOURCE_ERROR",
                "real_six_match_numeric_comparison_complete":False,
                "historic_original_provider_published_at_proven":False,
                "training_allowed":False,"gate14_pass":False,
                "raw_values_or_secret_exported":False}
    out.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"state":report["live_comparison_state"],
        "matched_games":report.get("exact_matched_fixtures",0),
        "native_graph_matches":report.get("whole_season_exact_fixture_home_away_identity_matches",0),
        "error_type":report.get("safe_error_class"),
        "reason_code":report.get("safe_error_reason_code"),
        "first_historical_PitchAPI_publish_proven":False,
        "gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
