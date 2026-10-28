"""Offline owner-only source clock fingerprint -> original PitchAPI native join.

No upload of private RSA, IDs, scores, odds, TEST. The source audit is
safely reproducible from exact SHA-pinned old public FPL 2023 snapshots and
original encrypted, authenticated PitchAPI TRAIN/VALIDATION ZIP. Publishes
only aggregates, never creates model-ready feature tables.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import argparse,json,os

from src.kb3_step13_archive_preflight import verify_original_zip,ENC,MAN
from src.kb3_pitch_uefa_evidence import restore
from src.kb3_step14_full_identity_pit_audit import _validate_native,_validate_safe
from src.kb3_step14_native_team_crosswalk import canonical_team_name
from src.kb3_step14_multiseason_pit import SOURCES,audit as public_audit,fetch,utc
from src.kb3_step14_fpl_form5_lineage import _candidate,parse_fixture_rows
from src.kb3_step14_fpl_historic_clock_pilot import verify_raw_csv
from scripts.step14_full_native_identity_pit_local import SAFE

ROOT=Path(__file__).resolve().parents[1]
ADDITIONAL_2023={
    "season":"2023-24",
    "repo":"vaastav/Fantasy-Premier-League",
    "commit":"c4f66ee30ef026bb7e8b7184b2427f9708c77d74",
    "path":"data/2023-24/fixtures.csv",
    "sha":"c9f99615ca61bba4a8306f88131119b5539bb0862fee3178e54501111498f8f1",
    "push":"2023-12-04T13:04:15Z",
    "event":"33866831577",
    "ft":140,
}
class PrivateJoinError(ValueError):pass

def _key_public(row,side):
    return (utc(row["kickoff_time"]),side)

def map_fpl_team_ids_by_finished_clock(public_rows,native,*,season,published_at,expected_finished):
    """Match old public team IDs to owner-only native team IDs without scores.
    Require *every* prior fixture and the complete 20-team clock fingerprint.
    """
    pubdone=[r for r in public_rows if r["finished"]=="True"]
    if len(pubdone)!=expected_finished:
        raise PrivateJoinError("PUBLIC_FINISHED_SET_CHANGED")
    nativeprior=[r for r in native.values() if r["season"]==season and
                 utc(r["kickoff_utc"])<utc(published_at)]
    if len(nativeprior)!=expected_finished:
        raise PrivateJoinError("PUBLIC_VS_NATIVE_PRIOR_SCHEDULE_COUNT_MISMATCH")
    pub=defaultdict(list); private=defaultdict(list)
    for r in pubdone:
        if utc(r["kickoff_time"]).date()>=utc(published_at).date():
            raise PrivateJoinError("PUBLIC_FINISHED_AFTER_PUSH")
        pub[str(r["team_h"])].append(_key_public(r,"H"))
        pub[str(r["team_a"])].append(_key_public(r,"A"))
    for r in nativeprior:
        private[r["home_id"]].append((utc(r["kickoff_utc"]),"H"))
        private[r["away_id"]].append((utc(r["kickoff_utc"]),"A"))
    if len(pub)!=20 or len(private)!=20:
        raise PrivateJoinError("TWENTY_UNIQUE_TEAMS_REQUIRED")
    private_fingerprints={}
    for team,events in private.items():
        key=tuple(sorted(events))
        if key in private_fingerprints:raise PrivateJoinError("AMBIGUOUS_PRIVATE_FINGERPRINT")
        private_fingerprints[key]=team
    mapping={}
    for team,events in pub.items():
        private_id=private_fingerprints.get(tuple(sorted(events)))
        if private_id is None or private_id in mapping.values():
            raise PrivateJoinError("INCOMPLETE_OR_AMBIGUOUS_FINGERPRINT")
        mapping[team]=private_id
    if len(mapping)!=20 or len(set(mapping.values()))!=20:
        raise PrivateJoinError("NOT_BIJECTIVE")
    # Mapping contains private IDs and is NEVER placed in a report or printed.
    return mapping

def one_fpl_source(s,native):
    raw=fetch(f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/{s['path']}")
    if sha256(raw).hexdigest()!=s["sha"]:
        raise PrivateJoinError("PUBLIC_RAW_HASH_CHANGED")
    verify_raw_csv(raw,expected_finished=s["ft"],push_time_utc=s["push"])
    records=parse_fixture_rows(raw)
    try:
        mapping=map_fpl_team_ids_by_finished_clock(
            records,native,season=s["season"],
            published_at=s["push"],expected_finished=s["ft"])
    except PrivateJoinError as exc:
        return {"season":s["season"],"public_source_commit":s["commit"],
                "public_finished_results":s["ft"],
                "join_state":"PRIVATE_CLOCK_FINGERPRINT_NOT_YET_UNIQUE",
                "blocking_reason":str(exc),
                "public_form5_candidates":None,"joined_private_candidates":0,
                "native_ids_or_goals_exported":False}
    candidates=0;matches=0;not_joined=0
    private_index=defaultdict(list)
    for r in native.values():
        if r["season"]==s["season"]:
            key=(r["home_id"],r["away_id"],r["kickoff_utc"])
            private_index[key].append(r)
    for target in records:
        if target["finished"]!="False" or not target["kickoff_time"] or
            utc(target["kickoff_time"])<=utc(s["push"])):
            continue
        if _candidate(records,target,utc(s["push"]))["state"]!="PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE":
            continue
        candidates+=1
        key=(mapping[target["team_h"]],mapping[target["team_a"]],target["kickoff_time"])
        found=private_index.get(key,[])
        if len(found)>1:raise PrivateJoinError("DUPLICATE_PRIVATE_FIXTURE_EXACT")
        if len(found)==1:matches+=1
        else:not_joined+=1
    del mapping,private_index
    return {"season":s["season"],"public_source_commit":s["commit"],
            "independent_push_utc":s["push"],"independent_event_id":s["event"],
            "public_finished_results":s["ft"],
            "join_state":"ORIGINAL_RSA_NATIVE_CLOCK_FINGERPRINT_BIJECTION_CHECKED",
            "public_form5_candidates":candidates,
            "joined_private_candidates":matches,
            "public_candidates_not_matching_real_native_pair_and_kickoff":not_joined,
            "native_ids_or_goals_exported":False}

def native_openfootball_join(public,native):
    out={}
    for season in ("2024-25","2025-26"):
        target=public["verified_three_season_public_sources"][season]
        count=0;not_matched=0
        entries=[r for r in native.values() if r["season"]==season]
        for x in target["public_form5_candidates"]:
            matches=[r for r in entries
                if (canonical_team_name(r["home_name"])==x["home"]
                    and canonical_team_name(r["away_name"])==x["away"]
                    and r["kickoff_utc"]==x["kickoff_utc"])]
            if len(matches)>1:raise PrivateJoinError("DUPLICATE_EXACT_NATIVE_PAIR")
            if matches:count+=1
            else:not_matched+=1
        out[season]={
            "public_form5_candidates":len(target["public_form5_candidates"]),
            "exact_original_private_pitchapi_pair_utc_joins":count,
            "identity_disagreement_or_public_reschedule":not_matched,
            "source_sha":target["verified_prematch_raw_sha256"],
            "independent_public_push":target["push_utc"],
            "historical_original_provider_feature_values_PIT_proven":False}
    return out

def trusted_join(*,native,public):
    results=[]
    for s in (SOURCES[0],ADDITIONAL_2023):
        try:results.append(one_fpl_source(s,native))
        except (PrivateJoinError,ValueError) as e:
            results.append({"season":"2023-24","public_source_commit":s["commit"],
                            "join_state":"FPL_NATIVE_FINGERPRINT_BLOCKED",
                            "blocking_reason":type(e).__name__,
                            "public_form5_candidates":None,"joined_private_candidates":0,
                            "native_ids_or_goals_exported":False})
    openfootball=native_openfootball_join(public,native)
    return {"schema":"kb3-step14-original-private-1140-public-source-joins-v1",
            "source":"owner-local authenticated original encrypted PitchAPI archive",
            "native_original_train_validation_matches_verified":len(native),
            "fpl_2023_sources":results,
            "openfootball_sources":openfootball,
            "test_examined":False,"original_source_scores_or_ids_exported":False,
            "full_pitchapi_historical_121_plus_38_pit_proven":False,
            "official_original_train_pit_eligible":0,
            "official_original_validation_pit_eligible":0,
            "training_allowed":False,"gate14_pass":False}

def run_local(*,archive_zip,private_key,output):
    dest=Path(output).expanduser().resolve()
    if dest.exists() or dest.is_relative_to(ROOT.resolve()) or dest.is_dir():
        raise PrivateJoinError("NEW_PRIVATE_REPORT_OUTSIDE_REPOSITORY_REQUIRED")
    public=public_audit()
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    index=_validate_safe(safe)
    zipinfo=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="kb3_step14_private_identity_") as folder:
        with ZipFile(archive_zip) as z:
            crypt=Path(folder)/ENC; manifest=Path(folder)/MAN
            crypt.write_bytes(z.read(ENC))
            manifest.write_bytes(z.read(MAN))
        restored=restore(crypt,manifest,private_key,include_receipts=True)
        if restored.get("validated") is not True or restored.get("training_allowed") is not False:
            raise PrivateJoinError("ORIGINAL_SOURCE_NOT_VERIFIED")
        native,_,_=_validate_native(restored["receipts"],index,
             zip_sha=zipinfo["zip_sha256"],
             chain_sha=restored["proof"]["final_chain_sha256"])
        report=trusted_join(native=native,public=public)
        del restored,native
    # Store aggregate-only report locally with restrictive permissions.
    dest.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    f=os.open(dest,flags,0o600)
    with os.fdopen(f,"w",encoding="utf8") as stream:
        json.dump(report,stream,sort_keys=True,ensure_ascii=False,indent=2)
        stream.write("\n")
    return report

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--archive-zip",required=True)
    a.add_argument("--private-key",required=True)
    a.add_argument("--output",required=True)
    opts=a.parse_args()
    try:
        result=run_local(archive_zip=opts.archive_zip,private_key=opts.private_key,output=opts.output)
        print("KB3_STEP14_ORIGINAL_NATIVE_FORM5_CROSSWALK",
              "2023_2024",[(x["join_state"],x["joined_private_candidates"])
                           for x in result["fpl_2023_sources"]],
              "2024_2025",result["openfootball_sources"]["2024-25"]["exact_original_private_pitchapi_pair_utc_joins"],
              "2025_2026",result["openfootball_sources"]["2025-26"]["exact_original_private_pitchapi_pair_utc_joins"],
              "M1_GATE14_PENDING")
        print("PRIVATE_AGGREGATES_ONLY_REPORT_CREATED_OUTSIDE_GITHUB")
    except Exception as exc:
        print("KB3_PRIVATE_JOIN_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
