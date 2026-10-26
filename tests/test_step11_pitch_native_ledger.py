"""Native-only immutable source and sealed restore tests (offline synthetic)."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from src.kb3_pitch_native_ledger import record,verify,latest_asof,shots_asof
from src.kb3_pitch_native_archive import seal,restore
from scripts.step11_pitch_native_capture_once import choose


def when(seconds):
    return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z")

def season():
    rows=[]
    for i in range(380):
        rows.append({"id":f"m_{i:06d}",
            "time_utc":"2026-09-01T16:00:00Z" if i<7 else "2027-03-01T15:00:00Z",
            "status":"finished" if i<7 else "not_started",
            "home_team":{"id":f"t_{(i*2):06d}","name":f"Home {i}"},
            "away_team":{"id":f"t_{(i*2+1):06d}","name":f"Away {i}"},
            "score_home":1 if i<7 else None,
            "score_away":0 if i<7 else None})
    return rows

def shots(mid="m_000000",value=0.5):
    i=int(mid[2:])
    return {"data":{"match_id":mid,"periods":[{"shots":[
       {"team_id":f"t_{i*2:06d}","expected_goals":value},
       {"team_id":f"t_{i*2+1:06d}","expected_goals":0.2}]}]}}

class TestPitchNativeImmutableLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private=rsa.generate_private_key(public_exponent=65537,key_size=3072)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.db=sqlite3.connect(self.root/"source.sqlite3")
        self.addCleanup(self.db.close)
        self.data=season()
        self.insert_fixture()

    def insert_fixture(self,origin="SYNTHETIC_TEST"):
        return record(self.db,"matches",self.data,
             started_at_utc=when(-10),completed_at_utc=when(-9),origin=origin)

    def insert_shots(self,origin="SYNTHETIC_TEST"):
        return record(self.db,"shots",shots(),
             started_at_utc=when(-7),completed_at_utc=when(-6),origin=origin)

    def test_integrity_verification_works_on_strict_readonly_database(self):
        self.insert_shots()
        db_path=self.root/"source.sqlite3"
        with sqlite3.connect("file:"+str(db_path.resolve())+"?mode=ro",uri=True) as readonly:
            outcome=verify(readonly)
        self.assertEqual(outcome["stored_records"],381)
        self.assertEqual(outcome["shot_captures"],1)

    def test_native_380_and_hash_immutability(self):
        p=verify(self.db)
        self.assertEqual(p["fixture_captures"],1)
        self.assertEqual(p["stored_records"],380)
        self.assertFalse(p["initial_provider_publication_proven"])
        self.assertFalse(p["training_allowed"])
        with self.assertRaisesRegex(sqlite3.DatabaseError,"IMMUTABLE"):
            self.db.execute("DELETE FROM pitch_captures")
        self.db.rollback()

    def test_shots_use_same_native_id_and_hash_chain(self):
        self.insert_shots()
        p=verify(self.db)
        self.assertEqual(p["captures"],2)
        self.assertEqual(p["shot_captures"],1)
        self.assertEqual(p["stored_records"],381)
        self.assertEqual(p["last_chain_sha256"],
                         self.db.execute("SELECT chain_sha256 FROM pitch_captures ORDER BY ordinal DESC LIMIT 1").fetchone()[0])

    def test_wrong_match_id_and_future_shots_denied(self):
        with self.assertRaisesRegex(ValueError,"PRIOR_OBSERVED_FIXTURE"):
            record(self.db,"shots",shots("m_999999"),
                   started_at_utc=when(-7),completed_at_utc=when(-6))
        with self.assertRaisesRegex(ValueError,"PITCH_XG_REQUIRES_FINISHED_MATCH"):
            record(self.db,"shots",shots("m_000010"),
                   started_at_utc=when(-7),completed_at_utc=when(-6))

    def test_unsafe_backdating_and_nonmonotonic_session(self):
        with self.assertRaisesRegex(ValueError,"NON_MONOTONE"):
            record(self.db,"shots",shots(),started_at_utc=when(-40),
                   completed_at_utc=when(-39))
        with self.assertRaisesRegex(ValueError,"CAPTURE_INTERVAL"):
            record(self.db,"shots",shots(),started_at_utc=when(-5),
                   completed_at_utc=when(-15))

    def test_synthetic_records_cannot_pass_as_prospective(self):
        self.insert_shots()
        self.assertIsNone(latest_asof(self.db,when(30)))
        self.assertIsNone(shots_asof(self.db,"m_000000",when(30)))

    def test_real_capture_cannot_claim_old_host_clock(self):
        with self.assertRaisesRegex(ValueError,"BACKDATED"):
            record(self.db,"matches",self.data,
                  started_at_utc="2026-10-01T00:00:00Z",
                  completed_at_utc="2026-10-01T00:00:01Z",
                  origin="NETWORK_OBSERVED")

    def test_raw_row_tamper_detected(self):
        self.insert_shots()
        self.db.execute("DROP TRIGGER pitch_record_no_update")
        self.db.execute("UPDATE pitch_records SET record_json='{}' WHERE pitch_match_id='m_000000'")
        with self.assertRaisesRegex(ValueError,"(PITCH_SOURCE_RECORD_CHANGED|PITCH_SOURCE_RECORD_SHA)"):
            verify(self.db)

    def test_cipher_roundtrip_and_corruption(self):
        self.insert_shots()
        pub=self.root/"recipient.pub.pem"
        pub.write_bytes(self.private.public_key().public_bytes(
          serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        priv=self.root/"receiver.key.pem"
        priv.write_bytes(self.private.private_bytes(
          serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
          serialization.NoEncryption()))
        enc=self.root/"source.enc";manifest=self.root/"source.json"
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_NATIVE_OBSERVATION"):
            seal(self.root/"source.sqlite3",pub,enc,manifest)
        data=seal(self.root/"source.sqlite3",pub,enc,manifest,allow_synthetic=True)
        self.assertNotIn(b"m_000000",enc.read_bytes())
        self.assertFalse(data["training_allowed"])
        recovered=self.root/"restore.sqlite3"
        output=restore(enc,manifest,priv,recovered)
        self.assertEqual(output["evidence"]["stored_records"],381)
        self.assertRaises(FileExistsError,restore,enc,manifest,priv,recovered)
        recovered.unlink()
        modified=bytearray(enc.read_bytes());modified[-1]^=1;enc.write_bytes(modified)
        with self.assertRaisesRegex(ValueError,"CIPHERTEXT_SHA"):
            restore(enc,manifest,priv,recovered)

    def test_stratified_native_five_samples(self):
        chosen=choose(self.data,when(10))
        self.assertEqual(len(chosen),5)
        self.assertEqual(len({x["id"] for x in chosen}),5)

if __name__=="__main__":
    unittest.main()
