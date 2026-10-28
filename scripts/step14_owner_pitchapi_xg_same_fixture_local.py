"""Owner-only deterministic 6-game PitchAPI vs historical FPL xG comparison.

Requires encrypted original historical match-id ZIP and owner's private RSA
key on Windows plus PITCHAPI_API_KEY environment variable. No private item
IDs, source values, raw API responses, shots, scores or RSA leave device.
Exactly 6 match IDs and 2 REST SDK endpoints each (12 PitchAPI calls).
Target data: 2023/24 training predecessor season only, not validation/TEST.
No original PitchAPI historical publication proof is claimed.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import argparse,json,os,math

from src.kb3_step13_archive_preflight import verify_original_zip,ENC,MAN
from src.kb3_pitch_uefa_evidence import restore
from src.kb3_step14_full_identity_pit_audit import _validate_safe,_validate_native
from scripts.step14_multiseason_owner_native_join_local import ROOT,SAFE,map_fpl_team_ids_by_finished_clock
from src.kb3_step14_owner_elo_2023_to_2024 import FULL_2023,check_pinned_public_evidence
from src.kb3_step14_fpl_form5_lineage import parse_fixture_rows
from src.kb3_step14_multiseason_pit import fetch,utc
from src.kb3_step14_xg_four_gates import extract_public_xg,FULL_MERGED_PATH,FULL_MERGED_SHA
from src.kb3_step14_pitchapi_xg_semantics import aggregate,side_comparison
from scripts.pitchapi_step06_audit import to_plain

PUBLIC_AUDIT=ROOT/"data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json"
SELECTED_CHRONOLOGICAL_INDICES=(20,84,148,212,276,340)
MAX_PITCHAPI_REQUESTS=12

class LocalXGError(ValueError):pass

def load_old_public_data():
    proof=json.loads(PUBLIC_AUDIT.read_text(encoding="utf8"))
    check_pinned_public_evidence(proof)
    base=f"https://raw.githubusercontent.com/{FULL_2023['repo']}/{FULL_2023['commit']}/"
    fixtures=fetch(base+FULL_2023["path"],limit=3_000_001)
    players=fetch(base+FULL_MERGED_PATH,limit=40_000_001)
    if sha256(fixtures).hexdigest()!=FULL_2023["sha"] or sha256(players).hexdigest()!=FULL_MERGED_SHA:
        raise LocalXGError("PINNED_2023_FPL_SOURCE_HASH_MISMATCH")
    public=extract_public_xg(fixtures,players,
       pinned_fixture_sha=FULL_2023["sha"],pinned_player_sha=FULL_MERGED_SHA,
       published_at=FULL_2023["push"])
    if public["finished_fixtures"]!=380 or public["side_count_with_xg"]!=760:
        raise LocalXGError("FULL_PUBLIC_2023_XG_GRID_NOT_COMPLETE")
    return fixtures,public

def private_match_sample(native,public_fixtures,public):
    rows=parse_fixture_rows(public_fixtures)
    mapping=map_fpl_team_ids_by_finished_clock(rows,native,season="2023-24",
        published_at=FULL_2023["push"],expected_finished=380)
    idx={}
    for mid,n in native.items():
        if n["season"]!="2023-24":continue
        key=(n["home_id"],n["away_id"],n["kickoff_utc"])
        if key in idx:raise LocalXGError("DUPLICATE_NATIVE_FIXTURE_IDENTITY")
        idx[key]=(mid,n)
    if len(idx)!=380:raise LocalXGError("ORIGINAL_2023_NATIVE_COUNT_CHANGED")
    prior=[r for r in rows if r["finished"]=="True"]
    prior.sort(key=lambda r:(utc(r["kickoff_time"]),int(r["id"])))
    if len(prior)!=380:raise LocalXGError("FULL_PUBLIC_FIXTURES_NOT_380")
    selected=[]
    for index in SELECTED_CHRONOLOGICAL_INDICES:
        r=prior[index]
        key=(mapping[r["team_h"]],mapping[r["team_a"]],r["kickoff_time"])
        hit=idx.get(key)
        if hit is None:raise LocalXGError("PITCHAPI_FPL_SAME_FIXTURE_TEAM_ID_CROSSWALK_FAILED")
        mid,n=hit
        if n["role"]!="TRAIN":
            raise LocalXGError("ONLY_FROZEN_TRAIN_PREDECESSOR_MATCHES_ALLOWED")
        h,a=int(r["team_h"]),int(r["team_a"])
        pubid=int(r["id"])
        if not all((pubid,t) in public["source_side_xg_values_IN_MEMORY_ONLY"] for t in (h,a)):
            raise LocalXGError("NO_PRE_2024_PUBLIC_BOTH_SIDES_XG")
        selected.append((mid,n["home_id"],n["away_id"],pubid,h,a))
    if len(selected)!=len(SELECTED_CHRONOLOGICAL_INDICES):
        raise LocalXGError("UNEXPECTED_SAMPLE_SIZE")
    return selected

def api_replay(*,selected,public,key):
    from pitchapi import PitchAPI
    client=PitchAPI(api_key=key)
    gathered=[];requests=0
    for mid,home,away,pubid,fpl_h,fpl_a in selected:
        if requests+2>MAX_PITCHAPI_REQUESTS:raise LocalXGError("API_REQUEST_BUDGET_EXCEEDED")
        # SDK uses key internally; NO response is written to disk.
        try:
            shots=to_plain(client.matches.shots(mid));requests+=1
            stats=to_plain(client.matches.stats(mid));requests+=1
        except Exception as exc:
            # Don't print full exception: library exceptions may echo URLs/tokens.
            raise LocalXGError("PITCHAPI_SOURCE_REQUEST_OR_AUTHENTICATION_FAILED") from None
        gathered+=side_comparison(match_id=mid,home_id=home,away_id=away,
               source_shots=shots,source_stats=stats,
               fpl_side_values=public["source_side_xg_values_IN_MEMORY_ONLY"],
               public_fixture_id=pubid,fpl_home_id=fpl_h,fpl_away_id=fpl_a)
    summary=aggregate(gathered)
    summary["sample_selection"]="fixed six historical 2023-24 chronological indices 20,84,148,212,276,340"
    summary["source_public_FPL_xg_asof"]="2024-05-27T18:05:12Z"
    summary["source_PitchAPI_observed_at_utc"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    summary["source_PitchAPI_original_first_publication_utc"]=None
    summary["api_calls"]=requests
    summary["sampled_original_native_2023_24_match_ids_disclosed"]=False
    summary["owner_RSA_plaintext_disclosed"]=False
    summary["FPL_provider_equivalence_still_a_statistical_comparison_only"]=True
    return summary

def run(*,archive_zip,private_key,output):
    dest=Path(output).expanduser().resolve()
    if dest.exists() or dest.is_relative_to(ROOT.resolve()) or dest.is_dir():
        raise LocalXGError("NEW_OUTPUT_OUTSIDE_GITHUB_REQUIRED")
    key=os.getenv("PITCHAPI_API_KEY","").strip()
    if not key:raise LocalXGError("PITCHAPI_API_KEY_NOT_SET_IN_WINDOWS_SESSION")
    fixtures,public=load_old_public_data()
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    idx=_validate_safe(safe)
    zipinfo=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="KB3_xg_comparison_owner_private_") as tmp:
        with ZipFile(archive_zip) as pack:
            crypt=Path(tmp)/ENC;manifest=Path(tmp)/MAN
            crypt.write_bytes(pack.read(ENC));manifest.write_bytes(pack.read(MAN))
        restored=restore(crypt,manifest,private_key,include_receipts=True)
        if restored.get("validated") is not True or restored.get("training_allowed") is not False:
            raise LocalXGError("ORIGINAL_RSA_VERIFICATION_BLOCKED")
        native,_,_=_validate_native(restored["receipts"],idx,
             zip_sha=zipinfo["zip_sha256"],
             chain_sha=restored["proof"]["final_chain_sha256"])
        selected=private_match_sample(native,fixtures,public)
        del restored,native,fixtures
        result=api_replay(selected=selected,public=public,key=key)
        del selected,public,key
    dest.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(dest,flags,0o600)
    with os.fdopen(fd,"w",encoding="utf8") as out:
        json.dump(result,out,sort_keys=True,ensure_ascii=False,indent=2)
        out.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-zip",required=True)
    p.add_argument("--private-key",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    try:
        r=run(archive_zip=a.archive_zip,private_key=a.private_key,output=a.output)
        print("KB3_STEP14_PITCHAPI_XG_SAME_FIXTURE_SEMANTICS",r["exact_matched_fixtures"],
              "FIXTURES",r["exact_matched_team_sides"],"TEAM_SIDES")
        print("PITCH_SHOTS_VS_PITCH_STATS",r["PITCH_SHOTS_XG_vs_PITCH_FULL_MATCH_STATS_XG"])
        print("FPL_PLAYER_SUM_VS_PITCH_STATS",r["FPL_OPTA_PLAYER_SUM_XG_vs_PITCH_FULL_MATCH_STATS_XG"])
        print("PITCHAPI_HISTORICAL_FIRST_PUBLISHED_UTC UNKNOWN",
              "GATE14 PENDING TRAIN_ELIGIBLE 0 VALIDATION_ELIGIBLE 0")
        print("PRIVATE_AGGREGATES_ONLY_OUTSIDE_GITHUB_WRITTEN")
    except Exception as exc:
        print("KB3_STEP14_XG_SEMANTIC_AUDIT_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
