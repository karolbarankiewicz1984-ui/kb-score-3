"""Step13 encrypted-source preflight: all ZIP data here is fabricated."""
import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.kb3_step13_archive_preflight import (
    verify_original_zip, ArchivePreflightError, ENC, MAN, SUMMARY,
    ZIP_SHA, CIPHER_SHA, CHAIN_SHA, OBSERVED,
)


def sha(b): return hashlib.sha256(b).hexdigest()


def constructed(root, *, fail=None):
    cipher=b"ARTIFICIAL_CIPHER_NO_PROVIDER_DATA"
    chain="f"*64
    m={
        "schema":"kb3-step11-pitch-uefa-evidence-v1",
        "ciphertext_bytes":len(cipher),
        "ciphertext_sha256":sha(cipher),
        "training_allowed":False,
        "historical_prematch_pit_certified":False,
        "provider_publication_proven":False,
        "proof":{"final_chain_sha256":chain,"sessions":4,
                 "source_first_published_at_known":False},
    }
    s={
        "schema":"kb3-pitch-native-3season-history-v1",
        "cipher_sha256":sha(cipher),
        "final_chain_sha256":chain,
        "last_real_observed_at_utc":OBSERVED,
        "historical_fixtures_total":1140,
        "training_allowed":False,
        "historical_prematch_pit_certified":False,
        "seasons":{x:{"fixtures":380,"retrospective_source":True}
                   for x in ("2023/2024","2024/2025","2025/2026")},
    }
    if fail=="bad-manifest-chain":
        m["proof"]["final_chain_sha256"]="0"*64
    if fail=="wrong-count":
        s["seasons"]["2024/2025"]["fixtures"]=379
    if fail=="promoted":
        m["training_allowed"]=True
    p=Path(root)/"synthetic.zip"
    with zipfile.ZipFile(p,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(ENC,cipher)
        z.writestr(MAN,json.dumps(m))
        z.writestr(SUMMARY,json.dumps(s))
        if fail=="extra":
            z.writestr("other",b"n")
    return p,{"expected_zip":sha(p.read_bytes()),
              "expected_cipher":sha(cipher),
              "expected_chain":chain,
              "expected_observed":OBSERVED}


class ArchivePreflightTests(unittest.TestCase):
    def test_reference_is_verified_but_never_called_decrypted(self):
        with tempfile.TemporaryDirectory() as root:
            p,expected=constructed(root)
            result=verify_original_zip(p,**expected)
            self.assertTrue(result["archive_zip_integrity_verified"])
            self.assertTrue(result["manifest_and_summary_consistency_verified"])
            self.assertEqual(result["historical_fixture_count_declared"],1140)
            self.assertFalse(result["archive_decrypted"])
            self.assertFalse(result["real_backtest_performed"])
            self.assertFalse(result["training_allowed"])
            self.assertFalse(result["gate13_pass"])
            self.assertFalse(result["test_partition_accessed"])
            self.assertEqual(len(result["report_sha256"]),64)

    def test_immutable_pinned_original_checksum(self):
        self.assertEqual(ZIP_SHA,"301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e")
        self.assertEqual(CIPHER_SHA,"e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343")
        self.assertEqual(CHAIN_SHA,"33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367")

    def test_synthetic_file_rejected_by_real_default_pin(self):
        with tempfile.TemporaryDirectory() as root:
            p,unused=constructed(root)
            with self.assertRaisesRegex(ArchivePreflightError,"ZIP_HASH"):
                verify_original_zip(p)

    def test_wrong_zip_sha_rejected_before_decompress(self):
        with tempfile.TemporaryDirectory() as root:
            p,expected=constructed(root)
            expected["expected_zip"]="0"*64
            with self.assertRaisesRegex(ArchivePreflightError,"ZIP_HASH"):
                verify_original_zip(p,**expected)

    def test_wrong_cipher_sha_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            p,expected=constructed(root)
            expected["expected_cipher"]="0"*64
            with self.assertRaisesRegex(ArchivePreflightError,"CIPHER_HASH"):
                verify_original_zip(p,**expected)

    def test_extra_zip_member_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            p,expected=constructed(root,fail="extra")
            with self.assertRaisesRegex(ArchivePreflightError,"LAYOUT"):
                verify_original_zip(p,**expected)

    def test_modified_chain_and_promoted_training_are_denied(self):
        for how in ("bad-manifest-chain","promoted"):
            with tempfile.TemporaryDirectory() as root:
                p,expected=constructed(root,fail=how)
                with self.assertRaisesRegex(ArchivePreflightError,"MANIFEST_CONFLICT"):
                    verify_original_zip(p,**expected)

    def test_modified_season_count_is_denied(self):
        with tempfile.TemporaryDirectory() as root:
            p,expected=constructed(root,fail="wrong-count")
            with self.assertRaisesRegex(ArchivePreflightError,"SUMMARY_CONFLICT"):
                verify_original_zip(p,**expected)


if __name__=="__main__":
    unittest.main()
