"""Owner-only trusted-local KB3 Step14 full native 760 TRAIN / 380 VALIDATION audit.

Verifies same original PINNED encrypted ZIP as successful 4/4 check. Requires
owner's private PEM only on this PC. Zero sport API calls; never touches TEST.
The report exports aggregates only: NO team IDs, no fixture IDs, no scores,
no labels, no odds, no RSA key or raw receipts. Cannot promote M1 fit.
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
from src.kb3_step14_full_identity_pit_audit import audit_1140

ROOT=Path(__file__).resolve().parents[1]
SAFE=ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
BLOB=ROOT/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json"
CLOCK=ROOT/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json"
PUBLIC=ROOT/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json"

def run_local(*,archive_zip,private_key,output):
    root=ROOT.resolve()
    dest=Path(output).expanduser().resolve()
    if dest.is_relative_to(root) or dest.is_dir() or dest.exists():
        raise ValueError("NEW_AGGREGATE_REPORT_MUST_BE_OUTSIDE_REPOSITORY")
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    blob=json.loads(BLOB.read_text(encoding="utf8"))
    clock=json.loads(CLOCK.read_text(encoding="utf8"))
    public_reference=json.loads(PUBLIC.read_text(encoding="utf8"))
    zipmeta=verify_original_zip(archive_zip)
    with TemporaryDirectory(prefix="kb3_step14_1140_source_") as directory:
        # Source key and encrypted bytes never leave owner device.
        with ZipFile(archive_zip) as package:
            encrypted=Path(directory)/ENC
            manifest=Path(directory)/MAN
            encrypted.write_bytes(package.read(ENC))
            manifest.write_bytes(package.read(MAN))
        restored=restore(encrypted,manifest,private_key,include_receipts=True)
        if (restored.get("validated") is not True or
            restored.get("training_allowed") is not False):
            raise ValueError("ORIGINAL_RESTORED_SOURCE_NOT_VALIDATED")
        report=audit_1140(safe=safe,receipts=restored["receipts"],
                          zip_sha=zipmeta["zip_sha256"],
                          chain_sha=restored["proof"]["final_chain_sha256"],
                          blob=blob,clock=clock,
                          public_reference=public_reference)
        del restored
    # Never overwrite an existing report; default private file permissions.
    dest.parent.mkdir(parents=True,exist_ok=True)
    opts=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):opts|=os.O_NOFOLLOW
    handle=os.open(dest,opts,0o600)
    try:
        with os.fdopen(handle,"w",encoding="utf8") as f:
            json.dump(report,f,sort_keys=True,ensure_ascii=False,indent=2)
            f.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-zip",required=True)
    p.add_argument("--private-key",required=True)
    p.add_argument("--output",required=True)
    options=p.parse_args()
    try:
        r=run_local(archive_zip=options.archive_zip,private_key=options.private_key,output=options.output)
        print("KB3_STEP14_FULL_NATIVE_IDENTITY_AUDIT",
              "CHECKED",r["native_identity_fixture_ids_checked"],
              "TRAIN",r["identity_checked_partition_counts"]["TRAIN"],
              "VALIDATION",r["identity_checked_partition_counts"]["VALIDATION"],
              "PUBLIC_SAMPLE",r["external_archive_crosswalk_sample"]["sample_count"],
              "PUBLIC_FULL",r["external_full_1140_targetfree_crosscheck"]["checked"],
              "PUBLIC_EXACT",r["external_full_1140_targetfree_crosscheck"]["counts"].get("EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF",0),
              "FIELD_PROOFS_REQUIRED",r["feature_contract_total_lineage_proofs_expected"],
              "PIT_TRAIN_CERTIFIED",r["real_training_prematch_proven_rows"],
              "GATE14","PENDING")
        print("PRIVATE_AGGREGATES_ONLY_REPORT_SAVED_OUTSIDE_REPOSITORY")
    except Exception as exc:
        # Never print path, source, key or exception message.
        print("KB3_FULL_IDENTITY_AUDIT_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
