"""Offline, fail-closed preflight of REAL GitHub-hosted three-league captures.

Never calls PitchAPI/GitHub, decrypts, makes predictions or alters M0.
This preflight distinguishes a host-attested 90-minute prematch snapshot
from a formally admissible CatBoost v3 source archived <= EXACT feature cutoff.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
import zipfile

SCHEMA = "kb3-v3-three-league-hosted-archive-preflight-v1"
COUNTRIES = frozenset(("ESP", "ITA", "GER"))
SHA256 = re.compile(r"^[a-f0-9]{64}$")
SQLITE_MEMBER = "forward_m0/kb3_forward_m0.sqlite"


class EvidenceFailure(ValueError):
    """An artifact, contract, or an archived record fails basic integrity."""


def require(ok, reason):
    if not ok:
        raise EvidenceFailure(reason)


def utc(value):
    require(type(value) is str and value.endswith("Z"), "CANONICAL_UTC_Z_REQUIRED")
    try:
        when = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceFailure("INVALID_UTC_TIMESTAMP") from exc
    require(when.utcoffset() == timedelta(0), "INVALID_UTC_OFFSET")
    return when


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_digest(obj):
    return digest(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8"))


def read_member(archive, name, *, max_size=25_000_000):
    require(name in archive.namelist(), "MISSING_ARCHIVE_MEMBER:" + name)
    info = archive.getinfo(name)
    require(0 < info.file_size <= max_size, "BAD_MEMBER_SIZE:" + name)
    return archive.read(info)


def inspect_view(view, contract):
    """Validate 87 original-CONTRACT field names, values and per-field clocks.

    A Step11 M0 view is NOT a shared-asof-v2/verified_view instance even if
    every one of the 87 contract values exists in it.
    """
    require(view.get("schema") == "kb3-step11-v0.5", "WRONG_VIEW_SCHEMA")
    require(view.get("mode") == "observed", "NOT_NETWORK_OBSERVED_MODE")
    require(view.get("training_allowed") is False, "VIEW_TRAINING_ALLOWED_DRIFT")
    h = view.get("sha256")
    require(type(h) is str and SHA256.fullmatch(h), "VIEW_SHA256_MISSING")
    require(json_digest({k: v for k, v in view.items() if k != "sha256"}) == h,
            "VIEW_CONTENT_HASH_MISMATCH")
    cutoff = utc(view["feature_cutoff_utc"])
    kickoff = utc(view["kickoff_utc"])
    require(cutoff <= kickoff - timedelta(minutes=90), "VIEW_TOO_CLOSE_TO_KICKOFF")
    require(isinstance(view.get("feature_availability"), dict),
            "FEATURE_CLOCKS_MISSING")
    require(isinstance(view.get("features"), dict) and
            isinstance(view.get("missing_flags"), dict), "MISSING_FEATURES")
    expected = contract["features"]
    require(contract["feature_count"] == len(expected) == 87,
            "CONTRACT_NOT_87_FEATURES")
    require(len({x["name"] for x in expected}) == 87, "CONTRACT_DUPLICATE_NAMES")
    for spec in expected:
        kind, name = spec["name"].split(":", 1)
        require(kind in ("num", "miss"), "CONTRACT_KIND_INVALID")
        source = view["features"] if kind == "num" else view["missing_flags"]
        require(name in source, "CONTRACT_FEATURE_MISSING:" + spec["name"])
        val = source[name]
        if kind == "miss":
            require(type(val) is bool, "MISSING_FLAG_NOT_BOOL:" + spec["name"])
        elif val is None:
            require(spec["nullable"] is True, "NONNULLABLE_FIELD_IS_NULL:" + name)
        else:
            require(type(val) in (int, float) and math.isfinite(val),
                    "BAD_NUMERIC_VALUE:" + name)
        clock_name = name if kind == "num" else "missing:" + name
        clock = view["feature_availability"].get(clock_name)
        require(isinstance(clock, dict), "NO_FIELD_PROVENANCE:" + clock_name)
        require(utc(clock.get("latest_required_observed_at_utc")) <= cutoff,
                "FIELD_OBSERVED_AFTER_CUTOFF:" + clock_name)
    require(view.get("target_prematch_snapshot_certified") is False,
            "PREMATCH_CERTIFICATION_DRIFT")
    return cutoff, kickoff


def inspect_archive(raw_zip, *, artifact_id, artifact_created_at_utc,
                    artifact_sha256, day, contract):
    """The three metadata fields MUST come from GitHub API, never from the ZIP.

    sha256 covers the actual hosted ZIP bytes. GitHub artifact created_at is
    independently server-recorded; it is NEVER reinterpreted as provider first
    publication time. No official v3 training admission is possible here.
    """
    require(type(artifact_id) is int and artifact_id > 0, "BAD_ARTIFACT_ID")
    host_created = utc(artifact_created_at_utc)
    require(type(artifact_sha256) is str and
            artifact_sha256.startswith("sha256:") and
            artifact_sha256[7:] == digest(raw_zip), "HOSTED_ZIP_DIGEST_MISMATCH")
    require(type(day) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day),
            "INVALID_UTC_DAY")
    base = "pit_sidecar/pitchapi_three_league_daily/" + day + "/"
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
        names = z.namelist()
        require(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
        receipt = json.loads(read_member(z, base + "THREE_LEAGUE_DAILY_RECEIPT.json"))
        manifest = json.loads(read_member(z, base + "THREE_LEAGUE_DAILY_SOURCE.manifest.json"))
        encrypted = read_member(z, base + "THREE_LEAGUE_DAILY_SOURCE.enc")
        db_bytes = read_member(z, SQLITE_MEMBER, max_size=256_000_000)
        capture_member = base + "M0_CAPTURE_LEDGER.sqlite"
        # The original receipt SHA refers to the exact pre-shadow capture DB.
        # Subsequent append-only M0 settlements change the file-level SHA.
        # Never claim that an updated DB equals the original captured bytes.
        captured_db_bytes = (read_member(z, capture_member, max_size=256_000_000)
                             if capture_member in names else db_bytes)
    require(receipt.get("utc_day") == day, "RECEIPT_DAY_MISMATCH")
    require(digest(encrypted) == manifest.get("ciphertext_sha256") ==
            receipt.get("source_ciphertext_sha256"), "ENCRYPTED_PAYLOAD_SHA_MISMATCH")
    require(manifest.get("proof", {}).get("final_chain_sha256") ==
            receipt.get("source_chain_sha256"), "SOURCE_CHAIN_MISMATCH")
    require(digest(captured_db_bytes) == receipt.get("feature_sqlite_ledger_sha256"),
            "SQLITE_LEDGER_SHA_MISMATCH")
    require(utc(receipt["observation_end_utc"]) <= host_created,
            "HOST_ARCHIVE_CREATED_BEFORE_CAPTURE_FINISHED")
    require(receipt.get("original_Premier_League_2026_27_TEST_not_accessed") is True,
            "PROTECTED_TEST_ACCESS_DRIFT")
    require(manifest.get("training_allowed") is False and
            manifest.get("offsite_restore_verified") is False,
            "MANIFEST_ELIGIBILITY_DRIFT")

    def read_frozen_day_rows(binary_sqlite):
        conn = sqlite3.connect(":memory:")
        try:
            conn.deserialize(binary_sqlite)
            conn.execute("PRAGMA query_only=ON")
            require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                    "CORRUPT_SQLITE")
            cols = ("league_country, kickoff_original_utc, captured_before_kickoff_utc, "
                    "signed_source_chain_sha256, source_ciphertext_sha256, "
                    "feature_payload_json, numeric_fields, missing_flag_fields, "
                    "eligible_for_original_M1")
            return conn.execute("SELECT " + cols +
                                " FROM m0_forward_feature_records "
                                "WHERE snapshot_day_utc=? ORDER BY league_country,"
                                "provider_match_id", (day,)).fetchall()
        finally:
            conn.close()

    rows = read_frozen_day_rows(captured_db_bytes)
    # Validate that later SQLite writes did not change any captured feature
    # rows. Append-only unrelated tables are allowed, altered day-rows are not.
    require(read_frozen_day_rows(db_bytes) == rows,
            "POSTCAPTURE_SQLITE_FROZEN_ROWS_CHANGED")

    pre_90 = 0
    before_exact_cutoff = 0
    counts = Counter()
    shortest_lead_minutes = None
    for country, ko, capture, chain, cipher_sha, payload, n_num, n_miss, m1 in rows:
        require(country in COUNTRIES, "UNKNOWN_OR_PROTECTED_LEAGUE")
        view = json.loads(payload)
        cutoff, kickoff = inspect_view(view, contract)
        require(utc(ko) == kickoff and utc(capture) == cutoff,
                "RECORD_AND_VIEW_TIMES_DIFFER")
        require(chain == receipt["source_chain_sha256"] and
                cipher_sha == receipt["source_ciphertext_sha256"],
                "RECORD_AND_SOURCE_HASHES_DIFFER")
        require(n_num == 121 and n_miss == 38 and m1 == 0,
                "ORIGINAL_M0_METADATA_DRIFT")
        counts[country] += 1
        archived_in_time = host_created <= kickoff - timedelta(minutes=90)
        pre_90 += int(archived_in_time)
        before_exact_cutoff += int(host_created <= cutoff)
        lead = round((kickoff - host_created).total_seconds()/60, 3)
        if shortest_lead_minutes is None or lead < shortest_lead_minutes:
            shortest_lead_minutes = lead
    require(len(rows) == receipt.get("frozen_M0_feature_snapshots"),
            "RECEIPT_FROZEN_ROWS_COUNT_DRIFT")
    require(dict(counts) == dict(receipt.get("M0_targets_by_country", {})),
            "RECEIPT_COUNTRY_COUNTS_DRIFT")

    blockers = []
    if before_exact_cutoff < len(rows):
        blockers.append("HOST_ARTIFACT_CREATED_AFTER_EXISTING_FEATURE_CUTOFF")
    blockers.extend((
        "ENCRYPTED_NATIVE_SOURCE_NOT_AVAILABLE_TO_V3_VERIFIED_VIEW",
        "M0_STEP11_VIEW_IS_NOT_ORIGINAL_SHARED_ASOF_V2_INPUT",
        "NO_PER_SOURCE_PRE_CUTOFF_NATIVE_MEMBER_PROOFS",
    ))
    return {
        "schema": SCHEMA, "artifact_id": artifact_id, "artifact_day": day,
        "artifact_created_at_utc": artifact_created_at_utc,
        "github_zip_sha256_verified": True, "encrypted_source_sha256_verified": True,
        "sqlite_ledger_sha256_verified": True,
        "sample_payload_sha256_verified": len(rows),
        "contract_87_fields_and_clocks_verified": len(rows),
        "country_counts": dict(sorted(counts.items())),
        "prematch_hosted_90min_count": pre_90,
        "hosted_before_existing_exact_feature_cutoff_count": before_exact_cutoff,
        "shortest_host_to_kickoff_minutes": shortest_lead_minutes,
        "original_provider_first_publication_proven": False,
        "v3_native_input_verified": False,
        "official_v3_admitted_samples": 0,
        "production_approved": False,
        "blockers": blockers,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--artifact-id", required=True, type=int)
    p.add_argument("--github-created-at", required=True)
    p.add_argument("--github-sha256", required=True)
    p.add_argument("--day", required=True)
    p.add_argument("--contract", default="contracts/kb3_catboost_asof_v3.json",
                   type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    report = inspect_archive(a.zip.read_bytes(), artifact_id=a.artifact_id,
                             artifact_created_at_utc=a.github_created_at,
                             artifact_sha256=a.github_sha256, day=a.day,
                             contract=json.loads(a.contract.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if a.out.exists():
        p.error("OUTPUT_EXISTS_FAIL_CLOSED")
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write("\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
