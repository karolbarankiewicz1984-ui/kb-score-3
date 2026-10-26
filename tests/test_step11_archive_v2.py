"""Step11 v2 archive: isolated synthetic two-season crypto and restore audit."""
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from scripts.step09_import_history import import_rows,sha256,canonical_bytes
from scripts.step11_archive_v2 import encrypt,restore
from src.kb3_storage import connect


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        k=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        cls.priv=k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption())
        cls.pub=k.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.db=self.root/"source.sqlite3"
        self.pub_path=self.root/"recipient.pem"
        self.priv_path=self.root/"private.pem"
        self.pub_path.write_bytes(self.pub)
        self.priv_path.write_bytes(self.priv)
        self.archive=self.root/"archive.enc"
        self.manifest=self.root/"archive.manifest.json"
        self.target=self.root/"restored.sqlite3"
        for year in (2023,2024):
            rows=[]
            for j,(home,away) in enumerate(((20,30),(30,20))):
                rows.append({
                   "provider_fixture_id":str(year*1000+j),
                   "home_provider_id":str(home),"home_name":"Club "+str(home),
                   "away_provider_id":str(away),"away_name":"Club "+str(away),
                   "kickoff_utc":f"{year}-08-0{j+1}T15:00:00Z",
                   "status":"FINISHED","goals_home_90":2,"goals_away_90":1,
                   "source_status":"FT"})
            h=sha256(canonical_bytes(rows))
            a=import_rows(self.db,rows,h,season=year)
            self.assertEqual(a["inserted"],2)

    def seal(self):
        return encrypt(self.db,self.pub_path,self.archive,self.manifest,
                       expected_fixtures=4,expected_by_year={"2023":2,"2024":2})

    def test_encrypt_decrypt_two_seasons(self):
        meta=self.seal()
        self.assertEqual(meta["evidence"]["fixtures"],4)
        self.assertFalse(meta["historical_point_in_time_certified"])
        self.assertNotIn(b"Club 20",self.archive.read_bytes())
        result=restore(self.archive,self.manifest,self.priv_path,self.target)
        self.assertEqual(result["fixtures"],4)
        self.assertFalse(result["training_allowed"])
        with connect(self.target) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM teams").fetchone()[0],2)

    def test_archive_tamper_is_rejected(self):
        self.seal()
        data=bytearray(self.archive.read_bytes())
        data[-4]^=1
        self.archive.write_bytes(data)
        with self.assertRaisesRegex(ValueError,"CIPHERTEXT_CHECKSUM"):
            restore(self.archive,self.manifest,self.priv_path,self.target)
        self.assertFalse(self.target.exists())

    def test_manifest_tamper_is_rejected(self):
        self.seal()
        d=json.loads(self.manifest.read_text())
        d["encrypted_sha256"]="00"*32
        self.manifest.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"CIPHERTEXT_CHECKSUM"):
            restore(self.archive,self.manifest,self.priv_path,self.target)

    def test_wrong_private_key_is_rejected(self):
        self.seal()
        wrong=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        self.priv_path.write_bytes(wrong.private_bytes(
            serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        with self.assertRaisesRegex(ValueError,"RECIPIENT_KEY_MISMATCH"):
            restore(self.archive,self.manifest,self.priv_path,self.target)
        self.assertFalse(self.target.exists())

    def test_never_overwrite_and_missing_season_blocked(self):
        self.seal()
        with self.assertRaises(FileExistsError):
            self.seal()
        self.target.write_bytes(b"DO-NOT-OVERWRITE")
        with self.assertRaises(FileExistsError):
            restore(self.archive,self.manifest,self.priv_path,self.target)
        self.assertEqual(self.target.read_bytes(),b"DO-NOT-OVERWRITE")

    def test_missing_expected_season_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"ARCHIVE_SOURCE_NOT_APPROVED_REPLAY"):
            encrypt(self.db,self.pub_path,self.archive,self.manifest,
                    expected_fixtures=4,expected_by_year={"2023":1,"2024":3})
        self.assertFalse(self.archive.exists())


if __name__=="__main__":
    unittest.main()
