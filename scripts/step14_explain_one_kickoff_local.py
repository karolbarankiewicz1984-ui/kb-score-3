"""Owner-only offline classification of one PitchAPI/OpenFootball kickoff difference.

Reads encrypted source into an isolated temporary directory and prints only
public team names + UTC times. No JSON full raw export, no IDs, labels, odds,
TEST, GitHub network, API requests or private key disclosure.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from src.kb3_step13_archive_preflight import verify_original_zip,ENC,MAN
from src.kb3_pitch_uefa_evidence import restore
from src.kb3_step14_full_identity_pit_audit import (
    _validate_safe,_validate_native
)
from src.kb3_step14_one_kickoff_diagnosis import diagnose_one
from scripts.step14_full_native_identity_pit_local import SAFE,PUBLIC


def run(*,archive_zip,private_key):
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    public=json.loads(PUBLIC.read_text(encoding="utf8"))
    idx=_validate_safe(safe)
    zip_meta=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="kb3_step14_one_time_difference_") as directory:
        with ZipFile(archive_zip) as encrypted_zip:
            encrypted=Path(directory)/ENC
            manifest=Path(directory)/MAN
            encrypted.write_bytes(encrypted_zip.read(ENC))
            manifest.write_bytes(encrypted_zip.read(MAN))
        restored=restore(encrypted,manifest,private_key,include_receipts=True)
        if (restored.get("validated") is not True or
            restored.get("training_allowed") is not False):
            raise ValueError("SEALED_SOURCE_NOT_VALIDATED")
        native,_,_=_validate_native(
            restored["receipts"],idx,zip_sha=zip_meta["zip_sha256"],
            chain_sha=restored["proof"]["final_chain_sha256"])
        # Source memory is restricted to the process and never serialized.
        result=diagnose_one(native,public)
        del native,restored
    return result


def main():
    p=argparse.ArgumentParser(description="Only local public names and both UTC clocks; no native IDs")
    p.add_argument("--archive-zip",required=True)
    p.add_argument("--private-key",required=True)
    args=p.parse_args()
    try:
        result=run(archive_zip=args.archive_zip,private_key=args.private_key)
        print("KB3_ONE_PUBLIC_KICKOFF_DISCREPANCY_OWNER_LOCAL_ONLY")
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        print("PIT_TRAIN_CERTIFIED 0 GATE14 PENDING NO_SOURCE_FILES_MODIFIED")
    except Exception as exc:
        # Even if the path contains private account identifiers or secrets,
        # print only the exception class.
        print("KB3_ONE_KICKOFF_DIAGNOSIS_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
