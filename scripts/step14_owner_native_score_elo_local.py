"""Trusted-owner-only: compare old public scores vs RSA PitchAPI predecessors.

Runs on Windows in original kb-score-3 directory using the same encrypted
historic ZIP/owner PEM as the prior 1140 identity audit. Never upload PEM,
raw decrypted payload, private IDs, future target labels or any TEST data.
A small aggregate JSON outside repository is the only durable output.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import argparse,json,os

from src.kb3_step14_multiseason_pit import SOURCES,fetch
from scripts.step14_multiseason_owner_native_join_local import ADDITIONAL_2023,ROOT,SAFE
from src.kb3_step14_private_results_equivalence import (
    pinned_raw,collect_prior_native_ids,native_scores,audit
)

def run_local(*,archive_zip,private_key,output):
    # The private key is accessed only here. CI tests never load crypto.
    from src.kb3_step13_archive_preflight import verify_original_zip,ENC,MAN
    from src.kb3_pitch_uefa_evidence import restore
    from src.kb3_step14_full_identity_pit_audit import _validate_safe,_validate_native
    dest=Path(output).expanduser().resolve()
    if dest.is_relative_to(ROOT.resolve()) or dest.is_dir() or dest.exists():
        raise ValueError("NEW_PRIVATE_AGGREGATE_MUST_BE_OUTSIDE_GIT_REPO")
    sources=(SOURCES[0],ADDITIONAL_2023,SOURCES[1])
    raws={}
    # Fetch only old PUBLIC source blobs, BEFORE decrypting any private file.
    for s in sources:
        url=f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/{s['path']}"
        raw=fetch(url)
        pinned_raw(s,raw)
        raws[s["commit"]]=raw
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    idx=_validate_safe(safe)
    zip_meta=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="kb3_owner_prior_score_match_") as tmp:
        with ZipFile(archive_zip) as zip:
            crypt=Path(tmp)/ENC;manifest=Path(tmp)/MAN
            crypt.write_bytes(zip.read(ENC))
            manifest.write_bytes(zip.read(MAN))
        restored=restore(crypt,manifest,private_key,include_receipts=True)
        if restored.get("validated") is not True or restored.get("training_allowed") is not False:
            raise ValueError("UNVERIFIED_ORIGINAL_ARCHIVE")
        native,_,_=_validate_native(
            restored["receipts"],idx,
            zip_sha=zip_meta["zip_sha256"],
            chain_sha=restored["proof"]["final_chain_sha256"])
        allowlist=collect_prior_native_ids(native,raws)
        scores=native_scores(restored["receipts"],native,allowlist)
        report=audit(native,scores,raws)
        report["original_training_or_validation_target_labels_read"]=False
        report["only_allowlisted_predecessor_scores_read"]=True
        report["no_paid_sport_api_requests"]=True
        del scores,allowlist,native,restored
    dest.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    file_handle=os.open(dest,flags,0o600)
    with os.fdopen(file_handle,"w",encoding="utf8") as file:
        json.dump(report,file,ensure_ascii=False,sort_keys=True,indent=2)
        file.write("\n")
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive-zip",required=True)
    parser.add_argument("--private-key",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        report=run_local(archive_zip=args.archive_zip,
                         private_key=args.private_key,output=args.output)
        print("KB3_STEP14_OLD_PUBLIC_FT_VS_ORIGINAL_PITCHAPI")
        for item in report["historical_pinned_public_sources_vs_RSA_PitchAPI"]:
            print(item["season"],"PREVIOUS_FT",item["old_completed_FT"],
                  "EXACT_NATIVE_FT",item["exact_original_native_score_matches"],
                  "DISAGREEMENTS",item["score_disagreements"],
                  "PUBLIC_ELO_FORM5_TARGETS",item.get("source_form5_target_native_elo_evidence",0),
                  "STATUS",item["status"])
        print("ORIGINAL_TRAIN_PIT",0,"GATE14","PENDING",
              "PRIVATE_AGGREGATES_ONLY_REPORT_CREATED_OUTSIDE_GITHUB")
    except Exception as exc:
        # Never log a path, PEM, source payload, match ID or score.
        print("KB3_STEP14_OLD_FT_RECHECK_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
