"""KB3 Step13: original PitchAPI encrypted ZIP integrity preflight without RSA key.

Checks signed-by-hash archive metadata, not plaintext or historic PIT.
No provider requests, archive contents, secret keys or match scores in output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ZIP_SHA="301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e"
CIPHER_SHA="e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343"
CHAIN_SHA="33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367"
OBSERVED="2026-10-26T13:17:47.692940Z"
ENC="KB3_PITCH_PL_HIST_2023_2026_NATIVE.enc"
MAN="KB3_PITCH_PL_HIST_2023_2026_NATIVE.manifest.json"
SUMMARY="PITCH_PL_HIST_NATIVE_SUMMARY.json"
EXPECTED={ENC,MAN,SUMMARY}


class ArchivePreflightError(ValueError):
    """Reject changed source; do not silently substitute a different archive."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_original_zip(path, *, expected_zip=ZIP_SHA, expected_cipher=CIPHER_SHA,
                        expected_chain=CHAIN_SHA, expected_observed=OBSERVED):
    """Pure offline inspection. Overrides are ONLY for artificial unit tests.

    Production CLI and trusted-local runner call without overrides.
    """
    source=Path(path).read_bytes()
    if len(source)>20_000_000 or digest(source)!=expected_zip:
        raise ArchivePreflightError("STEP13_ARCHIVE_ZIP_HASH_NOT_PINNED")
    try:
        with ZipFile(path) as z:
            infos=z.infolist()
            if (len(infos)!=3 or {x.filename for x in infos}!=EXPECTED
                    or any(x.is_dir() or x.flag_bits & 1 for x in infos)
                    or sum(x.file_size for x in infos)>2_000_000):
                raise ArchivePreflightError("STEP13_ARCHIVE_ZIP_LAYOUT_INVALID")
            cipher=z.read(ENC)  # Validates CRC along with outer/inner SHA.
            manifest_bytes=z.read(MAN)
            summary_bytes=z.read(SUMMARY)
    except (BadZipFile,RuntimeError,KeyError,OSError) as exc:
        raise ArchivePreflightError("STEP13_ARCHIVE_ZIP_CRC_OR_FORMAT_INVALID") from exc
    if digest(cipher)!=expected_cipher:
        raise ArchivePreflightError("STEP13_ARCHIVE_CIPHER_HASH_CHANGED")
    try:
        m=json.loads(manifest_bytes)
        s=json.loads(summary_bytes)
    except (ValueError,UnicodeDecodeError) as exc:
        raise ArchivePreflightError("STEP13_ARCHIVE_JSON_INVALID") from exc
    proof=m.get("proof",{})
    if (m.get("schema")!="kb3-step11-pitch-uefa-evidence-v1"
            or m.get("ciphertext_bytes")!=len(cipher)
            or m.get("ciphertext_sha256")!=expected_cipher
            or m.get("training_allowed") is not False
            or m.get("historical_prematch_pit_certified") is not False
            or m.get("provider_publication_proven") is not False
            or proof.get("final_chain_sha256")!=expected_chain
            or proof.get("sessions")!=4
            or proof.get("source_first_published_at_known") is not False):
        raise ArchivePreflightError("STEP13_ARCHIVE_MANIFEST_CONFLICT")
    seasons=s.get("seasons")
    if (s.get("schema")!="kb3-pitch-native-3season-history-v1"
            or s.get("cipher_sha256")!=expected_cipher
            or s.get("final_chain_sha256")!=expected_chain
            or s.get("last_real_observed_at_utc")!=expected_observed
            or s.get("historical_fixtures_total")!=1140
            or s.get("training_allowed") is not False
            or s.get("historical_prematch_pit_certified") is not False
            or not isinstance(seasons,dict)
            or set(seasons)!={"2023/2024","2024/2025","2025/2026"}
            or any(x.get("fixtures")!=380 or x.get("retrospective_source") is not True
                   for x in seasons.values())):
        raise ArchivePreflightError("STEP13_ARCHIVE_SUMMARY_CONFLICT")
    out={
        "schema":"kb3-step13-sealed-real-archive-preflight-v1",
        "source":"PITCHAPI_PREVIOUSLY_SEALED_ARCHIVE",
        "zip_sha256":digest(source),
        "zip_size_bytes":len(source),
        "cipher_sha256":digest(cipher),
        "cipher_size_bytes":len(cipher),
        "manifest_sha256":digest(manifest_bytes),
        "source_provenance_chain_sha256":expected_chain,
        "source_observed_at_utc":expected_observed,
        "historical_seasons":3,
        "historical_fixture_count_declared":1140,
        "archive_zip_integrity_verified":True,
        "manifest_and_summary_consistency_verified":True,
        "ciphertext_sha256_pinned":True,
        "archive_decrypted":False,
        "archive_plaintext_integrity_verified_in_this_run":False,
        "historical_prematch_pit_proven":False,
        "real_fit_performed":False,
        "real_backtest_performed":False,
        "real_backtest_metrics_available":False,
        "test_partition_accessed":False,
        "training_allowed":False,
        "gate13_pass":False,
        "next":"OWNER_LOCAL_RSA_KEY_REQUIRED_TO_DECRYPT_FOR_RESEARCH_ONLY",
    }
    out["report_sha256"]=digest(json.dumps(
        out,sort_keys=True,ensure_ascii=False,allow_nan=False,
        separators=(",",":")).encode("utf-8"))
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-zip",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    try:
        result=verify_original_zip(args.archive_zip)
        text=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        path=Path(args.output)
        if path.exists() and path.read_text(encoding="utf8")!=text:
            raise ArchivePreflightError("STEP13_ARCHIVE_REPORT_VERSION_CONFLICT")
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with path.open("x",encoding="utf8") as handle:
                handle.write(text)
        print("STEP13_SEALED_ARCHIVE_VERIFIED_NOT_DECRYPTED",
              result["report_sha256"])
    except (ArchivePreflightError,OSError) as exc:
        print("STEP13_SEALED_PREFLIGHT_BLOCKED",type(exc).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
