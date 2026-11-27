"""Read-only P2-02 audit of existing PitchAPI archives and card recheck evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sqlite3

from src.kb3_p2_source_contract import (
    CARD_TARGETS, SCOPES, SHA256, STAT_FIELDS, TARGETS, Fixture, Source,
    native_periods, period_items, source_identity, validate,
)
from src.kb3_pit_ledger import canonical

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = {
    "historical_multistat": ("HISTORICAL_SOURCE", "HISTORICAL_BACKFILL_REPORT", "source_ciphertext_sha256"),
    "historical_issue_rechecks": ("ISSUE_SOURCE", "ISSUE_RECHECK_REPORT", "source_cipher_sha256"),
}
ARCHIVE_SCHEMA = "kb3-step11-pitch-uefa-evidence-v1"
CANDIDATE_KEYS = (*STAT_FIELDS.values(), "yellow_cards", "red_cards")
RECHECK_STATUSES = {
    "EVENTS_UNAVAILABLE", "EVENTS_WRONG_MATCH_ID", "EVENTS_EMPTY_OR_MISSING",
    "EVENTS_MALFORMED", "EVENTS_MALFORMED_OR_UNKNOWN",
    "EVENTS_TEAM_STATS_CONFLICT", "EVENT_YELLOW_CONFIRMED",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha(path):
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def verify_archive(cipher, manifest, report, cipher_field):
    proof = manifest.get("proof") or {}
    metadata_ok = (
        manifest.get("schema") == ARCHIVE_SCHEMA
        and manifest.get("algorithms") == "AES-256-GCM+RSA-OAEP-SHA256+gzip"
        and all(isinstance(value, str) and SHA256.fullmatch(value) for value in (
            proof.get("final_chain_sha256"), manifest.get("raw_sha256"),
            manifest.get("recipient_fingerprint_sha256"), manifest.get("ciphertext_sha256"),
        ))
        and type(proof.get("sessions")) is int and proof["sessions"] > 0
        and manifest.get("provider_publication_proven") is False
        and proof.get("source_first_published_at_known") is False
    )
    if not metadata_ok:
        raise ValueError("ARCHIVE_METADATA_INVALID")
    with cipher.open("rb") as source:
        if source.read(7) != b"KB3UE1\n":
            raise ValueError("ARCHIVE_HEADER_MISMATCH")
    digest = file_sha(cipher)
    if digest != manifest["ciphertext_sha256"] or cipher.stat().st_size != manifest.get("ciphertext_bytes"):
        raise ValueError("ARCHIVE_CIPHERTEXT_CHECKSUM_MISMATCH")
    if (digest != report.get(cipher_field)
            or proof["final_chain_sha256"] != report.get("source_chain_sha256")):
        raise ValueError("ARCHIVE_REPORT_LINEAGE_MISMATCH")
    if cipher_field == "source_cipher_sha256" and report.get("source_receipts") != proof["sessions"]:
        raise ValueError("ARCHIVE_REPORT_SESSION_COUNT_MISMATCH")
    return digest, proof["sessions"]


def fixture_catalog(receipts):
    fixtures = {}
    for receipt in receipts:
        prefix, _, scope_and_season = receipt["resource"].partition("pitchapi:history:fixtures:")
        scope = scope_and_season.split(":")[0]
        if prefix or scope not in SCOPES:
            continue
        rows = receipt["payload"].get("matches", [])
        for row in rows:
            fixture = Fixture(scope, row["id"], row["home_team"]["id"], row["away_team"]["id"],
                              row["time_utc"], row["status"])
            if fixture.match_id in fixtures and fixtures[fixture.match_id] != fixture:
                fixtures[fixture.match_id] = None
            else:
                fixtures[fixture.match_id] = fixture
    return fixtures


def inspect_native_stat(receipt, fixture, metrics):
    payload = receipt["payload"]
    source = Source(payload, receipt["completed_at_utc"], receipt["payload_sha256"])
    counts = validate(fixture, stats=source)
    for target in STAT_FIELDS:
        metrics["stats_validation_reasons"][counts[target]["total"].reason] += 1
    data, error = source_identity(payload, fixture)
    if not error:
        periods, error = native_periods(data)
    if error:
        return
    alls = [period for period in periods if period["period"] == "All"]
    metrics["stats_native_all_period_counts"][str(min(2, len(alls)))] += 1
    if len(alls) == 1:
        items, error = period_items(alls[0])
        if not error:
            for key in CANDIDATE_KEYS:
                if any(item.get("key") == key for item in items):
                    metrics["stats_native_all_field_presence"][key] += 1


def inspect_native_events(receipt, fixture, metrics):
    payload = receipt["payload"]
    data = payload.get("data", payload)
    if not isinstance(data, dict) or data.get("match_id") != fixture.match_id:
        metrics["events_payload_checks"]["NATIVE_MATCH_MISMATCH"] += 1
        return
    events = data.get("events")
    if not isinstance(events, list) or not events:
        metrics["events_payload_checks"]["EMPTY_OR_MISSING"] += 1
        return
    expected_teams = (fixture.home_id, fixture.away_id)
    if any(not isinstance(event, dict) or event.get("team_id") not in expected_teams for event in events):
        metrics["events_payload_checks"]["EVENT_TEAMS_UNVERIFIED"] += 1
    else:
        metrics["events_payload_checks"]["EVENT_TEAMS_IN_SAME_FIXTURE"] += 1
    # This is a source diagnostic. The native timeline has no approved adapter.
    for kind in ("yellowcard", "redcard"):
        if any(isinstance(event, dict) and event.get("event_type") == kind for event in events):
            metrics["event_literal_presence"][kind] += 1


def audit_archives(root, owner_key):
    archives = {}
    inventory = sha256()
    known_fixtures = {}
    metrics = {key: Counter() for key in (
        "stats_validation_reasons", "stats_native_all_period_counts", "stats_native_all_field_presence",
        "events_payload_checks", "event_literal_presence", "excluded_or_unmatched_receipts",
    )}
    if owner_key is not None:
        from src.kb3_pitch_uefa_evidence import restore

    for family, (source_name, report_name, cipher_field) in ARCHIVES.items():
        base = root / "data/pit_sidecar" / family
        files = [{path.parent for path in base.glob(f"*/run-*/{name}")} for name in (
            source_name + ".enc", source_name + ".manifest.json", report_name + ".json",
        )]
        if not files[0] or files[0] != files[1] or files[0] != files[2]:
            raise ValueError("ARCHIVE_INVENTORY_MISSING_OR_ORPHANED")
        family_counts = Counter()
        for folder in sorted(files[0]):
            cipher = folder / (source_name + ".enc")
            manifest_path = folder / (source_name + ".manifest.json")
            report_path = folder / (report_name + ".json")
            digest, sessions = verify_archive(cipher, read_json(manifest_path), read_json(report_path), cipher_field)
            inventory.update(canonical([cipher.relative_to(root).as_posix(), digest,
                                        file_sha(manifest_path), file_sha(report_path)]))
            family_counts["ciphertexts_verified"] += 1
            family_counts["manifest_declared_receipts"] += sessions
            if owner_key is None:
                continue
            archive = restore(cipher, manifest_path, owner_key, include_receipts=True)
            receipts = archive["receipts"]
            family_counts["ciphertexts_decrypted"] += 1
            family_counts["verified_decrypted_receipts"] += len(receipts)
            fixtures = fixture_catalog(receipts)
            for match_id, fixture in fixtures.items():
                if fixture is not None and fixture.status != "finished":
                    continue
                if (match_id not in known_fixtures or
                        (fixture is not None and known_fixtures[match_id] == fixture)):
                    known_fixtures[match_id] = fixture
                else:
                    known_fixtures[match_id] = None
            for receipt in receipts:
                resource = receipt["resource"]
                if resource.startswith("pitchapi:history:stats:"):
                    fixture = fixtures.get(resource.rsplit(":", 1)[1])
                    if fixture is None:
                        metrics["excluded_or_unmatched_receipts"]["TEAM_STATS"] += 1
                    else:
                        inspect_native_stat(receipt, fixture, metrics)
                elif resource.startswith("pitchapi:recheck:events:"):
                    fixture = known_fixtures.get(resource.rsplit(":", 1)[1])
                    if fixture is None:
                        metrics["excluded_or_unmatched_receipts"]["CARD_EVENTS"] += 1
                    else:
                        inspect_native_events(receipt, fixture, metrics)
        archives[family] = {
            key: family_counts[key] for key in ("ciphertexts_verified", "manifest_declared_receipts",
                                               "ciphertexts_decrypted", "verified_decrypted_receipts")
        }
    return {
        "archives": archives,
        "archive_inventory_sha256": inventory.hexdigest(),
        "raw_access": "OWNER_KEY_NOT_AVAILABLE" if owner_key is None else "RESTORED_IN_MEMORY",
        "native_diagnostics": None if owner_key is None else metrics,
    }


def audit_card_rechecks(root):
    path = root / "data/research/historical_multistat/issue_rechecks.sqlite"
    before = file_sha(path)
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("CARD_RECHECK_SQLITE_INTEGRITY_FAIL")
        placeholders = ",".join("?" for _ in SCOPES)
        rows = db.execute(f"""
            SELECT scope,status,COUNT(*),COUNT(original_provider_first_published_at_utc),
                   SUM(yellow_events_home IS NOT NULL AND yellow_events_away IS NOT NULL)
            FROM issue_rechecks
            WHERE issue_type='YELLOW_CARDS' AND scope IN ({placeholders})
            GROUP BY scope,status
        """, SCOPES).fetchall()
    if file_sha(path) != before:
        raise ValueError("CARD_RECHECK_SOURCE_CHANGED")
    per_scope = {scope: {"rows": 0, "legacy_status_counts": {}, "both_event_values_stored": 0,
                         "first_publication_present": 0} for scope in SCOPES}
    for scope, status, n, published, both in rows:
        if status not in RECHECK_STATUSES:
            raise ValueError("CARD_RECHECK_STATUS_UNRECOGNIZED")
        item = per_scope[scope]
        item["rows"] += n
        item["legacy_status_counts"][status] = n
        item["both_event_values_stored"] += both
        item["first_publication_present"] += published
    return {
        "sqlite_sha256": before,
        "rows": sum(item["rows"] for item in per_scope.values()),
        "per_scope": per_scope,
    }


def audit(root, owner_key=None):
    result = audit_archives(root, owner_key)
    per_target = {}
    for target in TARGETS:
        reason = ("NATIVE_CARD_EVENT_SEMANTICS_UNVERIFIED" if target in CARD_TARGETS
                  else "NATIVE_STAT_SEMANTICS_UNVERIFIED")
        per_target[target] = {
            "status": "UNKNOWN",
            "confirmed_native_field": None,
            "candidate_native_field": STAT_FIELDS.get(target),
            "values": dict.fromkeys(("home", "away", "total")),
            "reason": reason,
        }
    return {
        "schema": "kb3-p2-02-source-contract-audit-v1",
        **result,
        "card_event_rechecks": audit_card_rechecks(root),
        "targets": per_target,
        "provider_first_publication_proven": False,
        "independent_host_attestation_verified": False,
        "regular_time_semantics_proven": False,
        "bookmaker_compatibility_proven": False,
        "settlement_eligible": False,
        "provider_api_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-key", type=Path, help="Existing owner key, local use only")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError("AUDIT_OUTPUT_ALREADY_EXISTS")
        result = audit(ROOT, args.owner_key)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as report:
            json.dump(result, report, sort_keys=True, indent=2)
            report.write("\n")
    except Exception as error:
        # Unexpected errors in restored data can contain provider values.
        # Print only a fixed error from this module or from the archive reader.
        code = str(error)
        safe = (type(error) is ValueError and code.startswith(("ARCHIVE_", "CARD_RECHECK_", "AUDIT_", "UEFA_"))
                and code.isascii() and all(c.isupper() or c.isdigit() or c == "_" for c in code))
        raise SystemExit(code if safe else "P2_SOURCE_AUDIT_FAILED") from None


if __name__ == "__main__":
    main()
