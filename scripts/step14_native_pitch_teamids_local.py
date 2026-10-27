"""Step14 native PitchAPI team-ID crosswalk — owner-trusted-local execution only.

Requires the OWNER'S offline private key (do NOT send key to GitHub/ChatGPT).
No network, no API, no TEST reads, no xG/results export, no model training.
Only four explicit PitchAPI fixture IDs and source-attested OpenFootball teams.
Private report written with exclusive file creation and 0600 permissions.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from src.kb3_step13_archive_preflight import verify_original_zip,ENC,MAN
from src.kb3_pitch_uefa_evidence import restore
from src.kb3_step14_native_team_crosswalk import (
    audit_crosswalk, ARCHIVE_CHAIN_SHA, SOURCE_OBSERVED_UTC,
)

ROOT=Path(__file__).resolve().parents[1]
SAFE=ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
BLOB=ROOT/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json"
CLOCK=ROOT/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json"


def run_local(*,archive_zip,private_key,output):
    output=Path(output).expanduser().resolve()
    root=ROOT.resolve()
    if output.is_relative_to(root) or output.is_dir() or output.exists():
        raise ValueError("PRIVATE_REPORT_MUST_BE_NEW_AND_OUTSIDE_REPOSITORY")
    # Validate original public source and signed FIXTURE-only split before
    # reading private-key bytes. No catch-and-retry using other archives.
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    blob=json.loads(BLOB.read_text(encoding="utf8"))
    clock=json.loads(CLOCK.read_text(encoding="utf8"))
    from src.kb3_step14_native_team_crosswalk import _verify_public_evidence
    _verify_public_evidence(safe,blob,clock)

    preflight=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="kb3_step14_local_secret_sources_") as tmp:
        with ZipFile(archive_zip) as zipped:
            encrypted=Path(tmp)/ENC
            manifest=Path(tmp)/MAN
            encrypted.write_bytes(zipped.read(ENC))
            manifest.write_bytes(zipped.read(MAN))
        restored=restore(encrypted,manifest,private_key,include_receipts=True)
        if (restored.get("validated") is not True or
            restored.get("proof",{}).get("final_chain_sha256")!=ARCHIVE_CHAIN_SHA or
            restored.get("training_allowed") is not False):
            raise ValueError("ORIGINAL_NATIVE_SOURCE_CHAIN_INVALID")
        report=audit_crosswalk(
            safe=safe,blob=blob,clock=clock,
            receipts=restored["receipts"],
            archive_zip_sha=preflight["zip_sha256"],
            source_chain_sha=restored["proof"]["final_chain_sha256"])
        del restored
    # Atomic no-overwrite, least-privilege private file. Never write into Git.
    output.parent.mkdir(parents=True,exist_ok=True)
    opts=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): opts|=os.O_NOFOLLOW
    fd=os.open(output,opts,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf8") as out:
            json.dump(report,out,sort_keys=True,ensure_ascii=False,indent=2)
            out.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return report


def main():
    p=argparse.ArgumentParser(description="Private local PitchAPI team ID crosswalk audit; no API access")
    p.add_argument("--archive-zip",required=True,help="Exact original Drive archive")
    p.add_argument("--private-key",required=True,help="Owner offline private PEM. NEVER upload.")
    p.add_argument("--output",required=True,help="New private report OUTSIDE git repository")
    args=p.parse_args()
    try:
        report=run_local(archive_zip=args.archive_zip,private_key=args.private_key,output=args.output)
        print("PITCHAPI_NATIVE_TEAM_PAIR_LOCAL_CHECK",
              "TOTAL",report["total_checked"],
              "MATCHED",report["identity_crosswalk_verified_count"],
              "TRAIN",report["train_verified_identity_count"],
              "VALIDATION",report["validation_verified_identity_count"],
              "REPORT_SHA",report["report_sha256"],
              "GATE14","PENDING")
        print("PRIVATE_REPORT_SAVED_OUTSIDE_REPOSITORY_NO_SECRET_PATHS_PRINTED")
    except Exception as e:
        # Exceptions can include filesystem path and private-data payloads,
        # so print ONLY a fixed harmless class label.
        print("LOCAL_NATIVE_PAIR_AUDIT_BLOCKED",type(e).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
