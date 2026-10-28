"""Trusted Windows RSA proof of 2023/24 full FT and 2024/25 Elo rollover.

Zero PitchAPI API calls; all original decrypted data/keys remain only here.
Only 380 previous 2023/24 FT and 60 previous 2024/25 FT are allowed;
no original 2024 target outcomes, no 2025/26 validation or TEST.
Aggregate result created only outside GitHub working tree.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import argparse,json,os

from src.kb3_step14_multiseason_pit import SOURCES,fetch
from src.kb3_step14_owner_elo_2023_to_2024 import (
    FULL_2023,check_pinned_public_evidence,audit
)
from scripts.step14_multiseason_owner_native_join_local import ROOT,SAFE

PROOF=ROOT/"data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json"

def run_local(*,archive_zip,private_key,output):
    from src.kb3_step13_archive_preflight import verify_original_zip,ENC,MAN
    from src.kb3_pitch_uefa_evidence import restore
    from src.kb3_step14_full_identity_pit_audit import _validate_safe,_validate_native
    dest=Path(output).expanduser().resolve()
    if dest.exists() or dest.is_dir() or dest.is_relative_to(ROOT.resolve()):
        raise ValueError("NEW_AGGREGATE_OUTPUT_OUTSIDE_REPOSITORY_REQUIRED")
    evidence=json.loads(PROOF.read_text(encoding="utf8"))
    check_pinned_public_evidence(evidence)
    original={}
    for s in (FULL_2023,SOURCES[1]):
        url=f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/{s['path']}"
        raw=fetch(url)
        from hashlib import sha256
        if sha256(raw).hexdigest()!=s["sha"]:
            raise ValueError("ORIGINAL_PUBLIC_SOURCE_SHA_CHANGED")
        original[s["commit"]]=raw
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    idx=_validate_safe(safe)
    zipinfo=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="KB3_private_380_elo_rollover_") as tmp:
        with ZipFile(archive_zip) as pack:
            crypt=Path(tmp)/ENC;manifest=Path(tmp)/MAN
            crypt.write_bytes(pack.read(ENC))
            manifest.write_bytes(pack.read(MAN))
        restored=restore(crypt,manifest,private_key,include_receipts=True)
        if restored.get("validated") is not True or restored.get("training_allowed") is not False:
            raise ValueError("ORIGINAL_RSA_PAYLOAD_NOT_VERIFIED")
        native,_,_=_validate_native(
            restored["receipts"],idx,
            zip_sha=zipinfo["zip_sha256"],
            chain_sha=restored["proof"]["final_chain_sha256"])
        report=audit(native,restored["receipts"],
                     original[FULL_2023["commit"]],
                     original[SOURCES[1]["commit"]],evidence)
        del native,restored,original
    dest.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_CREAT|os.O_WRONLY|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    handle=os.open(dest,flags,0o600)
    with os.fdopen(handle,"w",encoding="utf8") as f:
        json.dump(report,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-zip",required=True)
    p.add_argument("--private-key",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    try:
        x=run_local(archive_zip=a.archive_zip,private_key=a.private_key,output=a.output)
        print("KB3_STEP14_REAL_NATIVE_CROSSSEASON_ELO")
        print("2023_24_FULL_ORIGINAL_FT_EXACT",x["2023_full_380_prior_FT_RSA_PitchAPI_exact"],
              "2024_25_OLDER_FT_EXACT",x["2024_publicly_prior_60_FT_RSA_PitchAPI_exact"])
        print("NATIVE_TEAM_IDS_STABLE",x["2024_start_stable_native_team_ids"],
              "PROMOTED_STARTED_1500",x["2024_promoted_native_team_ids_started_at_1500"],
              "SEASON_RETENTION",x["2024_elo_rollover_decay"])
        print("2024_25_ORIGINAL_TEAM_PAIRS_WITH_FULL_ELO",x["2024_exact_native_target_pairs_with_crossseason_elo_proof"],
              "OF",x["2024_pinned_public_form5_target_pairs"])
        print("GATE14 PENDING","TRAIN_ELIGIBLE",0,"VALIDATION_ELIGIBLE",0,
              "PRIVATE_AGGREGATE_OUTSIDE_GITHUB_CREATED")
    except Exception as exc:
        print("KB3_STEP14_NATIVE_380_ELO_ROLLOVER_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
