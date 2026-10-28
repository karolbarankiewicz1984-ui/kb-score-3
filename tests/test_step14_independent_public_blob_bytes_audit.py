"""Offline negative tests for the independent historical public blob byte verifier."""
from hashlib import sha256
import unittest

from scripts.step14_independent_public_blob_bytes_audit import verify_blob
from scripts.step14_independent_frozen_lineage_recheck import AuditFailure

def fixture_bytes(*, duplicate=False, finished_count=50, future=True):
    out = ["id,team_h,team_a,kickoff_time,finished,team_h_score,team_a_score"]
    for i in range(380):
        ident = "1" if duplicate and i == 2 else str(i + 1)
        is_finished = i < finished_count
        ko = "2024-08-01T16:00:00Z" if is_finished or not future else "2024-10-01T16:00:00Z"
        out.append(f"{ident},1,2,{ko},{is_finished},NOT_READ,NOT_READ")
    return ("\n".join(out) + "\n").encode()

def item(raw):
    return {"sha": sha256(raw).hexdigest(), "ft": 50,
            "push": "2024-09-01T12:00:00Z", "commit": "a" * 40,
            "season": "2024-25"}

class OldPublicBlobByteTests(unittest.TestCase):
    def test_sha_and_380_fixture_flags_pass(self):
        raw = fixture_bytes()
        report = verify_blob(item(raw), raw)
        self.assertEqual(report["fixture_identity_count"], 380)
        self.assertEqual(report["public_finished_fixture_flags"], 50)

    def test_changed_raw_bytes_rejected(self):
        raw = fixture_bytes()
        source = item(raw)
        with self.assertRaises(AuditFailure):
            verify_blob(source, raw + b"changed")

    def test_duplicate_fixture_id_rejected(self):
        raw = fixture_bytes(duplicate=True)
        with self.assertRaises(AuditFailure):
            verify_blob(item(raw), raw)

    def test_false_finished_count_rejected(self):
        raw = fixture_bytes(finished_count=49)
        with self.assertRaises(AuditFailure):
            verify_blob(item(raw), raw)

    def test_no_future_unplayed_fixture_rejected(self):
        raw = fixture_bytes(future=False)
        with self.assertRaises(AuditFailure):
            verify_blob(item(raw), raw)

if __name__ == "__main__":
    unittest.main()
