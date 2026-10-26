"""Verify + compare two *offsite ciphertext ZIPs* with owner's key locally.

No API calls, no network, no secret printing. Decrypted SQLite copies live only
in a temporary directory and are independently authenticated before comparison.
Only sanitized counts and digests are published.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import tempfile
import zipfile
from src.kb3_pitch_native_archive import restore
from src.kb3_pitch_native_drift import compare_independent_ledgers

EXPECTED=frozenset({
  "KB3_PITCH_NATIVE_2026-27_PIT.enc",
  "KB3_PITCH_NATIVE_2026-27_PIT.manifest.json",
  "STEP11_PITCH_NATIVE_SAFE_RECEIPT.json",
})
MAX_ARCHIVE=5_000_000
MAX_CIPHER=4_000_000

def extract_safe(zip_path,directory):
    src=Path(zip_path)
    if src.stat().st_size>MAX_ARCHIVE:
        raise ValueError("NATIVE_ARCHIVE_EXCEEDS_SAFE_SIZE")
    with zipfile.ZipFile(src) as z:
        rows=z.infolist()
        if len(rows)!=len(EXPECTED) or set(r.filename for r in rows)!=EXPECTED:
            raise ValueError("UNEXPECTED_NATIVE_ARCHIVE_MEMBERS")
        if any(r.is_dir() or r.file_size>MAX_CIPHER for r in rows):
            raise ValueError("INVALID_NATIVE_ARCHIVE_MEMBER")
        if z.testzip() is not None:
            raise ValueError("NATIVE_ARCHIVE_ZIP_CRC_INVALID")
        for r in rows:
            (Path(directory)/r.filename).write_bytes(z.read(r))
    return (Path(directory)/"KB3_PITCH_NATIVE_2026-27_PIT.enc",
            Path(directory)/"KB3_PITCH_NATIVE_2026-27_PIT.manifest.json")

def compare_encrypted_pairs(first_zip,second_zip,private_key_path):
    if Path(first_zip).resolve()==Path(second_zip).resolve():
        raise ValueError("SECOND_SNAPSHOT_MUST_BE_DIFFERENT_SOURCE_FILE")
    with tempfile.TemporaryDirectory(prefix="kb3_pair_",ignore_cleanup_errors=False) as root:
        base=Path(root)
        left=base/"older";right=base/"newer"
        left.mkdir();right.mkdir()
        enc_a,mf_a=extract_safe(first_zip,left)
        enc_b,mf_b=extract_safe(second_zip,right)
        db_a,db_b=left/"verified.sqlite3",right/"verified.sqlite3"
        restore(enc_a,mf_a,private_key_path,db_a)
        restore(enc_b,mf_b,private_key_path,db_b)
        result=compare_independent_ledgers(db_a,db_b)
        result["source_archives_independently_decrypted_and_verified"]=True
        result["offsite_ciphertext_source_urls_verified_externally"]=False
        result["no_keys_or_raw_rows_in_report"]=True
        result["historical_prematch_pit_certified"]=False
        result["training_allowed"]=False
        return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--earlier-offsite-zip",required=True)
    p.add_argument("--later-offsite-zip",required=True)
    p.add_argument("--owner-private-key",required=True)
    p.add_argument("--report",required=True)
    a=p.parse_args()
    result=compare_encrypted_pairs(
        a.earlier_offsite_zip,a.later_offsite_zip,a.owner_private_key)
    target=Path(a.report)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf8") as handle:
        json.dump(result,handle,sort_keys=True,indent=2)
        handle.write("\n")
    print("KB3_NATIVE_TWO_REAL_SOURCE_ARCHIVES_PASS",
          json.dumps({k:result[k] for k in
             ("prior_observed_at_utc","current_observed_at_utc","match_count",
              "changed_kickoffs","changed_statuses","changed_scores",
              "changed_raw_match_payloads","observations_on_distinct_utc_dates",
              "training_allowed")},sort_keys=True))
if __name__=="__main__":
    main()
