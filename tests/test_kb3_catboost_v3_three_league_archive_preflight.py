"""Synthetic-only archive fixtures: no API, no decrypting, no real secrets."""
from datetime import datetime, timezone
import copy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import unittest
import zipfile

from scripts.kb3_catboost_v3_three_league_archive_preflight import (
    EvidenceFailure, inspect_archive, json_digest,
)

CONTRACT = json.loads(Path("contracts/kb3_catboost_asof_v3.json").read_text())


def make_archive(*, corrupt_view=False, appended_shadow=False, changed_frozen_row=False):
    day = "2026-11-09"
    prefix = "pit_sidecar/pitchapi_three_league_daily/" + day + "/"
    chain = "a" * 64
    encrypted = b"synthetic-encrypted-bytes"
    cipher_sha = hashlib.sha256(encrypted).hexdigest()
    features = {}
    flags = {}
    clocks = {}
    for spec in CONTRACT["features"]:
        kind, name = spec["name"].split(":", 1)
        if kind == "num":
            features[name] = None if spec["nullable"] else 0.0
            key = name
        else:
            flags[name] = True
            key = "missing:" + name
        clocks[key] = {"latest_required_observed_at_utc": "2026-11-09T11:58:00Z"}
    if corrupt_view:
        del features["home_elo"]
    view = {
        "schema": "kb3-step11-v0.5", "mode": "observed",
        "kickoff_utc": "2026-11-09T14:00:00Z",
        "feature_cutoff_utc": "2026-11-09T12:00:00Z",
        "training_allowed": False, "target_prematch_snapshot_certified": False,
        "features": features, "missing_flags": flags,
        "feature_availability": clocks,
    }
    view["sha256"] = json_digest(view)
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE m0_forward_feature_records (
        league_country TEXT, provider_match_id TEXT, snapshot_day_utc TEXT,
        kickoff_original_utc TEXT, captured_before_kickoff_utc TEXT,
        signed_source_chain_sha256 TEXT, source_ciphertext_sha256 TEXT,
        feature_payload_json TEXT, numeric_fields INTEGER, missing_flag_fields INTEGER,
        eligible_for_original_M1 INTEGER)""")
    c.execute("""INSERT INTO m0_forward_feature_records VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              ("ESP", "synthetic-target", day, view["kickoff_utc"],
               view["feature_cutoff_utc"], chain, cipher_sha,
               json.dumps(view), 121, 38, 0))
    c.commit()
    data = c.serialize()
    if appended_shadow:
        c.execute("CREATE TABLE later_shadow_settlement (id INTEGER PRIMARY KEY, status TEXT)")
        c.execute("INSERT INTO later_shadow_settlement VALUES (1, 'settled')")
    if changed_frozen_row:
        c.execute("UPDATE m0_forward_feature_records SET numeric_fields=122")
    c.commit()
    current = c.serialize()
    c.close()
    receipt = {
        "utc_day": day, "source_ciphertext_sha256": cipher_sha,
        "source_chain_sha256": chain,
        "feature_sqlite_ledger_sha256": hashlib.sha256(data).hexdigest(),
        "observation_end_utc": "2026-11-09T11:59:00Z",
        "original_Premier_League_2026_27_TEST_not_accessed": True,
        "frozen_M0_feature_snapshots": 1, "M0_targets_by_country": {"ESP": 1},
    }
    manifest = {
        "ciphertext_sha256": cipher_sha, "training_allowed": False,
        "offsite_restore_verified": False, "proof": {"final_chain_sha256": chain},
    }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(prefix + "THREE_LEAGUE_DAILY_RECEIPT.json", json.dumps(receipt))
        z.writestr(prefix + "THREE_LEAGUE_DAILY_SOURCE.manifest.json", json.dumps(manifest))
        z.writestr(prefix + "THREE_LEAGUE_DAILY_SOURCE.enc", encrypted)
        if appended_shadow or changed_frozen_row:
            z.writestr(prefix + "M0_CAPTURE_LEDGER.sqlite", data)
        z.writestr("forward_m0/kb3_forward_m0.sqlite", current)
    return bio.getvalue()


def run(raw, created="2026-11-09T12:01:00Z", digest=None):
    return inspect_archive(
        raw, artifact_id=999, artifact_created_at_utc=created,
        artifact_sha256=digest or "sha256:" + hashlib.sha256(raw).hexdigest(),
        day="2026-11-09", contract=CONTRACT,
    )


class ThreeLeagueRealArchiveGate(unittest.TestCase):
    def test_all_87_features_and_all_source_hashes_pass_without_false_admission(self):
        r = run(make_archive())
        self.assertEqual(r["sample_payload_sha256_verified"], 1)
        self.assertEqual(r["contract_87_fields_and_clocks_verified"], 1)
        self.assertEqual(r["prematch_hosted_90min_count"], 1)
        self.assertEqual(r["hosted_before_existing_exact_feature_cutoff_count"], 0)
        self.assertEqual(r["official_v3_admitted_samples"], 0)
        self.assertFalse(r["v3_native_input_verified"])
        self.assertIn("HOST_ARTIFACT_CREATED_AFTER_EXISTING_FEATURE_CUTOFF", r["blockers"])

    def test_host_earlier_than_exact_cutoff_still_cannot_unseal_native(self):
        raw = make_archive()
        r = run(raw, created="2026-11-09T11:59:30Z")
        self.assertEqual(r["hosted_before_existing_exact_feature_cutoff_count"], 1)
        self.assertEqual(r["official_v3_admitted_samples"], 0)
        self.assertNotIn("HOST_ARTIFACT_CREATED_AFTER_EXISTING_FEATURE_CUTOFF", r["blockers"])

    def test_append_only_shadow_does_not_falsify_capture_sha(self):
        result = run(make_archive(appended_shadow=True))
        self.assertTrue(result["sqlite_ledger_sha256_verified"])
        self.assertEqual(result["contract_87_fields_and_clocks_verified"], 1)
        self.assertEqual(result["official_v3_admitted_samples"], 0)

    def test_changing_day_rows_after_capture_is_rejected(self):
        with self.assertRaisesRegex(EvidenceFailure, "POSTCAPTURE_SQLITE_FROZEN_ROWS_CHANGED"):
            run(make_archive(appended_shadow=True, changed_frozen_row=True))

    def test_genuine_archive_is_not_published_on_code_push(self):
        workflow = Path(".github/workflows/kb3-pitchapi-three-league-daily.yml").read_text()
        self.assertIn("steps.true_source_capture.outcome == 'success'", workflow)
        self.assertIn("steps.receipt_verified.outcome == 'success'", workflow)
        self.assertIn("steps.ledger_proof.outputs.immutable_ledger_sha_verified == 'true'", workflow)
        self.assertIn("contains(fromJSON", workflow)
        self.assertIn("NO_CAPTURE_TIME_LEDGER_NO_MAIN_PUBLISH", workflow)

    def test_preflight_requires_original_run_event_not_main_branch_alone(self):
        workflow = Path(".github/workflows/kb3-catboost-v3-three-league-evidence.yml").read_text()
        self.assertIn("run.get('event') in ('schedule','workflow_dispatch')", workflow)
        self.assertIn("run.get('head_branch')=='main'", workflow)
        self.assertIn("CODE_PUSH_ARTIFACTS_REJECTED", workflow)
        self.assertIn("NO_AUTHENTIC_SCHEDULED_OR_MANUAL_CAPTURE_ARTIFACT", workflow)
        self.assertIn("RECEIPT_UTC_DAY_MISMATCH", workflow)
        self.assertIn("STALE_CAPTURE_NOT_REHOSTED_AS_NEW_PIT", workflow)

    def test_github_zip_sha_mismatch_refused(self):
        raw = make_archive()
        with self.assertRaisesRegex(EvidenceFailure, "HOSTED_ZIP_DIGEST_MISMATCH"):
            run(raw, digest="sha256:" + "b" * 64)

    def test_missing_contract_feature_refused(self):
        with self.assertRaisesRegex(EvidenceFailure, "CONTRACT_FEATURE_MISSING"):
            run(make_archive(corrupt_view=True))

    def test_archive_created_too_early_for_capture_refused(self):
        with self.assertRaisesRegex(EvidenceFailure, "HOST_ARCHIVE_CREATED_BEFORE_CAPTURE_FINISHED"):
            run(make_archive(), created="2026-11-09T11:58:30Z")


if __name__ == "__main__":
    unittest.main()
