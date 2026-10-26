"""Step13 offline runner provenance tests: fake ZIP only; no key or real data."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import hashlib
import io
import json
import zipfile

from scripts import step13_pitch_retrospective_local as local


CIPHER="KB3_PITCH_PL_HIST_2023_2026_NATIVE.enc"
MANIFEST="KB3_PITCH_PL_HIST_2023_2026_NATIVE.manifest.json"


def archive(path, *, duplicate=False):
    with zipfile.ZipFile(path,"w") as f:
        f.writestr(CIPHER,b"ENCRYPTED_ONLY_SYNTHETIC")
        f.writestr(MANIFEST,b"{}")
        if duplicate:
            f.writestr("nested/"+CIPHER,b"dup")


def setup(tmp, *, duplicate=False):
    root=Path(tmp)
    path=root/"sealed.zip"
    archive(path,duplicate=duplicate)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    audits=root/"data/audits"
    audits.mkdir(parents=True)
    (audits/"STEP11_PITCH_MULTISEASON_ELO_REAL_2026-10-26.json").write_text(
        json.dumps({"history":{
            "encrypted_zip_sha256":digest,
            "cipher_sha256":local.PINNED_CIPHER_SHA256,
            "chain_sha256":local.PINNED_CHAIN_SHA256,
            "finished_fixtures":1140,
            "historical_archive_observed_last_utc":local.HIST_CUTOFF_UTC}}))
    return root,path,digest


class TrustedArchivePolicyTests(TestCase):
    def test_real_archive_cannot_be_substituted(self):
        with TemporaryDirectory() as tmp:
            root,path,_=setup(tmp)
            with self.assertRaisesRegex(ValueError,"SOURCE_AUDIT_CHANGED"):
                local.research_archive_zip_local(
                    archive_zip=path,private_key_path="NEVER_USED",root=root)

    def test_zip_missing_expected_crypto_receipts_rejected(self):
        with TemporaryDirectory() as tmp:
            root,path,digest=setup(tmp,duplicate=True)
            with mock.patch.object(local,"PINNED_ZIP_SHA256",digest):
                with self.assertRaisesRegex(ValueError,"ARCHIVE_CONTENTS_INVALID"):
                    local.research_archive_zip_local(
                        archive_zip=path,private_key_path="NEVER_USED",root=root)

    def test_exact_archived_names_pass_encrypted_bytes_to_local_without_leak(self):
        with TemporaryDirectory() as tmp:
            root,path,digest=setup(tmp)
            def only_encrypted(*,cipher_path,manifest_path,private_key_path,root):
                self.assertEqual(Path(cipher_path).read_bytes(),b"ENCRYPTED_ONLY_SYNTHETIC")
                self.assertEqual(Path(manifest_path).read_bytes(),b"{}")
                self.assertEqual(private_key_path,"SECRET_FILE_PATH_NOT_REAL")
                self.assertNotEqual(Path(cipher_path).parent,Path(private_key_path).parent)
                return {"test_only":"NO_REAL_RESTORE_PERFORMED"}
            with mock.patch.object(local,"PINNED_ZIP_SHA256",digest),mock.patch.object(
                    local,"research_local",side_effect=only_encrypted) as fn:
                result=local.research_archive_zip_local(
                    archive_zip=path,private_key_path="SECRET_FILE_PATH_NOT_REAL",root=root)
            self.assertEqual(result,{"test_only":"NO_REAL_RESTORE_PERFORMED"})
            self.assertEqual(fn.call_count,1)

    def test_unknown_policy_no_override(self):
        self.assertIn("RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT",
                      local.POLICY)


if __name__=="__main__":
    import unittest
    unittest.main()
