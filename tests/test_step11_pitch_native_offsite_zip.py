"""Offline strict ZIP intake of native PitchAPI source evidence, no provider calls."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.step11_pitch_native_compare_offsite_zip import (
    EXPECTED,extract_safe,compare_encrypted_pairs
)

class NativePairZipTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def make_zip(self,name="archive.zip",files=None):
        p=self.root/name
        sources=files if files is not None else {
           "KB3_PITCH_NATIVE_2026-27_PIT.enc":b"ENCRYPTED_TEST_ONLY",
           "KB3_PITCH_NATIVE_2026-27_PIT.manifest.json":b"{}",
           "STEP11_PITCH_NATIVE_SAFE_RECEIPT.json":b"{}"}
        with zipfile.ZipFile(p,"w") as z:
            for path,data in sources.items():
                z.writestr(path,data)
        return p

    def test_only_expected_source_members(self):
        p=self.make_zip()
        target=self.root/"extracted";target.mkdir()
        a,b=extract_safe(p,target)
        self.assertEqual(a.name,"KB3_PITCH_NATIVE_2026-27_PIT.enc")
        self.assertEqual(b.name,"KB3_PITCH_NATIVE_2026-27_PIT.manifest.json")
        self.assertEqual(set(x.name for x in target.iterdir()),EXPECTED)

    def test_rejects_extra_unencrypted_db(self):
        files={n:b"test" for n in EXPECTED}
        files["decrypted.sqlite3"]=b"RAW"
        p=self.make_zip(files=files)
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_NATIVE_ARCHIVE_MEMBERS"):
            extract_safe(p,self.root)

    def test_rejects_missing_manifest(self):
        files={n:b"test" for n in EXPECTED if not n.endswith("manifest.json")}
        p=self.make_zip(files=files)
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_NATIVE_ARCHIVE_MEMBERS"):
            extract_safe(p,self.root)

    def test_rejects_path_traversal(self):
        files={n:b"test" for n in EXPECTED}
        item=files.pop("KB3_PITCH_NATIVE_2026-27_PIT.enc")
        files["../KB3_PITCH_NATIVE_2026-27_PIT.enc"]=item
        p=self.make_zip(files=files)
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_NATIVE_ARCHIVE_MEMBERS"):
            extract_safe(p,self.root)

    def test_rejects_reused_same_snapshot(self):
        p=self.make_zip()
        with self.assertRaisesRegex(ValueError,"SECOND_SNAPSHOT_MUST_BE_DIFFERENT"):
            compare_encrypted_pairs(p,p,self.root/"private-key-not-needed.pem")

    def test_rejects_oversized_member(self):
        files={n:b"test" for n in EXPECTED}
        files["KB3_PITCH_NATIVE_2026-27_PIT.enc"]=b"x"*4_000_001
        p=self.make_zip(files=files)
        with self.assertRaisesRegex(ValueError,"INVALID_NATIVE_ARCHIVE_MEMBER"):
            extract_safe(p,self.root)

if __name__=="__main__":
    unittest.main()
