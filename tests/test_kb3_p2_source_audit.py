import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts.kb3_p2_source_audit import ARCHIVES, ARCHIVE_SCHEMA, audit, file_sha
from test_kb3_p2_source_contract import FIXTURE, source, stats


def make_bundle(root, family, index=0):
    name, report, cipher_field = ARCHIVES[family]
    folder = root / "data/pit_sidecar" / family / "2026-11-01" / f"run-{index}"
    folder.mkdir(parents=True)
    cipher = folder / (name + ".enc")
    cipher.write_bytes(b"KB3UE1\nopaque synthetic bytes")
    digest = file_sha(cipher)
    chain = "a" * 64
    manifest_path = folder / (name + ".manifest.json")
    manifest_path.write_text(json.dumps({
        "schema": ARCHIVE_SCHEMA,
        "algorithms": "AES-256-GCM+RSA-OAEP-SHA256+gzip",
        "ciphertext_sha256": digest,
        "ciphertext_bytes": cipher.stat().st_size,
        "raw_sha256": "b" * 64,
        "recipient_fingerprint_sha256": "c" * 64,
        "provider_publication_proven": False,
        "proof": {"final_chain_sha256": chain, "sessions": 2, "source_first_published_at_known": False},
    }))
    report_path = folder / (report + ".json")
    report_path.write_text(json.dumps({
        cipher_field: digest, "source_chain_sha256": chain, "source_receipts": 2,
    }))
    return cipher, manifest_path, report_path


def make_database(root):
    database = root / "data/research/historical_multistat/issue_rechecks.sqlite"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as db:
        db.execute("""CREATE TABLE issue_rechecks(
            scope, issue_type, status, original_provider_first_published_at_utc,
            yellow_events_home, yellow_events_away
        )""")
        db.executemany("INSERT INTO issue_rechecks VALUES (?,?,?,?,?,?)", [
            ("POL", "YELLOW_CARDS", "EVENT_YELLOW_CONFIRMED", None, 0, 2),
            ("ESP", "YELLOW_CARDS", "EVENTS_EMPTY_OR_MISSING", None, None, None),
            ("POL", "XG", "UNRELATED", None, None, None),
            ("UCL", "YELLOW_CARDS", "OUT_OF_SCOPE_SYNTHETIC", None, None, None),
            ("ENG", "YELLOW_CARDS", "OUT_OF_SCOPE_SYNTHETIC", None, None, None),
        ])
    return database


class SourceAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.history, _, self.report = make_bundle(self.root, "historical_multistat")
        _, self.recheck_manifest, _ = make_bundle(self.root, "historical_issue_rechecks")
        self.database = make_database(self.root)

    def test_hashes_archives_and_only_reports_aggregate_domestic_rechecks(self):
        digests = (file_sha(self.history), file_sha(self.database))
        result = audit(self.root)
        self.assertEqual((file_sha(self.history), file_sha(self.database)), digests)
        self.assertEqual(result["raw_access"], "OWNER_KEY_NOT_AVAILABLE")
        self.assertIsNone(result["native_diagnostics"])
        self.assertEqual(result["archives"]["historical_multistat"]["ciphertexts_verified"], 1)
        self.assertEqual(result["card_event_rechecks"]["rows"], 2)
        self.assertEqual(result["card_event_rechecks"]["per_scope"]["POL"]["both_event_values_stored"], 1)
        self.assertTrue(all(target["status"] == "UNKNOWN" and
                            all(value is None for value in target["values"].values())
                            for target in result["targets"].values()))
        self.assertNotIn("OUT_OF_SCOPE_SYNTHETIC", json.dumps(result))

    def test_rejects_tampered_ciphertext(self):
        self.history.write_bytes(self.history.read_bytes().replace(b"opaque", b"edited"))
        with self.assertRaisesRegex(ValueError, "^ARCHIVE_CIPHERTEXT_CHECKSUM_MISMATCH$"):
            audit(self.root)

    def test_rejects_report_with_different_source_chain(self):
        report = json.loads(self.report.read_text())
        report["source_chain_sha256"] = "d" * 64
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "^ARCHIVE_REPORT_LINEAGE_MISMATCH$"):
            audit(self.root)

    def test_rejects_orphaned_archive(self):
        self.recheck_manifest.unlink()
        with self.assertRaisesRegex(ValueError, "^ARCHIVE_INVENTORY_MISSING_OR_ORPHANED$"):
            audit(self.root)

    def test_optional_restore_uses_original_envelope_and_discloses_only_aggregates(self):
        payload = stats()
        payload["data"]["periods"][0]["period"] = "All"
        stat_source = source(payload)
        listing = {"id": FIXTURE.match_id, "home_team": {"id": FIXTURE.home_id},
                   "away_team": {"id": FIXTURE.away_id}, "time_utc": FIXTURE.kickoff_utc,
                   "status": FIXTURE.status}
        history = [
            {"resource": "pitchapi:history:fixtures:POL:2026/2027", "payload": {"matches": [listing]}},
            {"resource": "pitchapi:history:stats:" + FIXTURE.match_id, "payload": payload,
             "completed_at_utc": stat_source.observed_at_utc, "payload_sha256": stat_source.payload_sha256},
        ]
        recheck = [{"resource": "pitchapi:recheck:events:" + FIXTURE.match_id,
                    "payload": {"match_id": FIXTURE.match_id,
                                "events": [{"event_type": "yellowcard", "team_id": FIXTURE.home_id}]}}]
        with patch("src.kb3_pitch_uefa_evidence.restore",
                   side_effect=[{"receipts": history}, {"receipts": recheck}]) as restore:
            key = self.root / "owner-key-local"
            result = audit(self.root, key)
        self.assertTrue(all(call.args[2] == key and call.kwargs == {"include_receipts": True}
                            for call in restore.call_args_list))
        self.assertEqual(result["native_diagnostics"]["stats_native_all_field_presence"]["fouls"], 1)
        self.assertEqual(result["native_diagnostics"]["event_literal_presence"]["yellowcard"], 1)
        self.assertFalse(result["settlement_eligible"])
        published = json.dumps(result)
        self.assertNotIn(FIXTURE.match_id, published)
        self.assertNotIn(FIXTURE.home_id, published)
        self.assertNotIn(key.name, published)
