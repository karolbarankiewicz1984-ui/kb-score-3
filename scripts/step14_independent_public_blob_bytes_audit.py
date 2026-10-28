"""Independently redownload eight pre-kickoff public FPL fixture blobs by commit.

Verify current public GitHub immutable-commit bytes against SHA256 previously
pinned by separate GHArchive PushEvent witnesses. This verifies *source bytes*,
not the original GHArchive event itself, PitchAPI original publication, xG,
the full 121+38 PIT, or original CatBoost readiness. No keys/TEST/target scores.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.step14_independent_frozen_lineage_recheck import (
    AUDIT, WITNESS_2023, WITNESS_2024, require, utc, witnesses
)

SCHEMA = "kb3-step14-independent-eight-old-public-source-byte-recheck-v1"
MAX_BYTES = 3_000_001

def download_old_blob(item, fetcher=None):
    url = ("https://raw.githubusercontent.com/" + item["repo"] + "/" +
           item["commit"] + "/" + item["path"])
    if fetcher is not None:
        raw = fetcher(url)
    else:
        req = Request(url, headers={"User-Agent": "KB3-Step14-Independent-Old-Blob-Recheck"})
        with urlopen(req, timeout=35) as response:
            raw = response.read(MAX_BYTES + 1)
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES,
            "OLD_PUBLIC_SOURCE_SIZE_INVALID")
    return raw

def verify_blob(item, raw):
    require(sha256(raw).hexdigest() == item["sha"], "OLD_PUBLIC_BLOB_SHA256_MISMATCH")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        require(reader.fieldnames is not None and
                {"id", "team_h", "team_a", "kickoff_time", "finished"}.issubset(reader.fieldnames),
                "SOURCE_CSV_SCHEMA_INVALID")
        rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("OLD_PUBLIC_CSV_DECODE_FAILURE") from exc
    require(len(rows) == 380, "SOURCE_NOT_380_FIXTURES")
    require(len({r["id"] for r in rows}) == 380 and all(r["id"] for r in rows),
            "DUPLICATE_OR_EMPTY_PUBLIC_FIXTURE_ID")
    require(all(r["finished"] in ("True", "False") and
                r["team_h"] and r["team_a"] and r["team_h"] != r["team_a"]
                for r in rows), "INVALID_OLD_PUBLIC_TEAM_OR_FINISHED_STATE")
    finished = sum(r["finished"] == "True" for r in rows)
    require(finished == item["ft"], "OLD_SOURCE_FINISHED_COUNT_DISAGREES")
    require(any(r["finished"] == "False" and r["kickoff_time"] and
                utc(r["kickoff_time"]) > utc(item["push"]) for r in rows),
            "NO_FUTURE_UNPLAYED_FIXTURE_AT_PUBLICATION")
    # Intentionally never parse any team_h_score/team_a_score columns.
    return {
        "commit": item["commit"],
        "season": item["season"],
        "source_sha256": item["sha"],
        "raw_byte_length": len(raw),
        "public_finished_fixture_flags": finished,
        "public_unfinished_fixture_flags": len(rows) - finished,
        "fixture_identity_count": len(rows),
        "gharchive_push_time_from_prior_witness_not_refetched": item["push"],
        "sha256_and_structure_rechecked": True,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    old23 = json.loads(WITNESS_2023.read_text(encoding="utf-8"))
    old24 = json.loads(WITNESS_2024.read_text(encoding="utf-8"))
    source_map = witnesses(old23, old24)
    result_rows = []
    for commit, item in sorted(source_map.items()):
        raw = download_old_blob(item)
        result_rows.append(verify_blob(item, raw))
    require(len(result_rows) == 8 and
            sum(r["public_finished_fixture_flags"] for r in result_rows) > 0,
            "EIGHT_OLD_PUBLIC_SOURCE_BLOBS_NOT_VERIFIED")
    report = {
        "schema": SCHEMA,
        "scope": "EIGHT_IMMUTABLE_PUBLIC_GITHUB_FPL_CSV_BYTES_REDOWNLOADED_AND_SHA256_CHECKED",
        "sources_checked": 8,
        "all_source_byte_checks": "PASS",
        "total_source_fixture_rows": sum(r["fixture_identity_count"] for r in result_rows),
        "source_details": result_rows,
        "external_push_events_independently_refetched_in_this_run": False,
        "historical_clock_claim": "PRIOR_GHARCHIVE_WITNESSES_ONLY_NOT_NEW_SERVER_TIME_ATTESTATION",
        "original_pitchapi_team_xg_first_published_at_proven": False,
        "full_121_plus_38_original_pit_proven": False,
        "original_train_certified": 0,
        "original_validation_certified": 0,
        "original_M1_training_allowed": False,
        "gate14": "PENDING",
        "test_examined": False,
        "target_result_scores_examined": False,
        "notes": "Independent public blob byte hashes and fixture/finished flags only; does not read goal values or certify original PitchAPI data."
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            require(args.output.read_text(encoding="utf-8") == encoded,
                    "APPEND_ONLY_PUBLIC_BLOB_AUDIT_REPLACEMENT_REFUSED")
        else:
            args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": "EIGHT_PUBLIC_BLOB_SHA256_AND_FIXTURE_FLAGS_PASS",
                      "sources": 8, "original_pitchapi_pit": False,
                      "gate14": "PENDING"}, sort_keys=True))

if __name__ == "__main__":
    main()
