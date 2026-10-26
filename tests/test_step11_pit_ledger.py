"""Step11 PIT ledger: synthetic anti-backdating, no-lookahead, immutability tests."""
import json
import sqlite3
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from src.kb3_pit_ledger import (
    record_capture,verify_chain,select_result_asof,utc_now
)
from src.kb3_pit_archive import seal,restore

def iso(d):
    return d.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def payload(status="FT",season=2026):
    matches=[]
    for i in range(380):
        st=status if i==0 else "NS"
        matches.append({
            "fixture":{"id":1800000+i,"date":("2026-08-20T18:00:00Z"
                          if i==0 else "2027-01-20T15:00:00Z"),
                       "status":{"short":st}},
            "league":{"id":39,"season":season},
            "teams":{"home":{"id":10,"name":"A"},
                     "away":{"id":20,"name":"B"}},
            "score":{"fulltime":{"home":2,"away":1} if st=="FT" else
                     {"home":None,"away":None}},
            "goals":{"home":2 if st=="FT" else None,
                     "away":1 if st=="FT" else None}})
    return {"errors":[],"paging":{"total":1},"response":matches}

class TestPitLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        cls.pub=cls.private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.priv=cls.private.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption())

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.path=self.dir/"ledger.sqlite3"
        self.db=sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.now=datetime.now(timezone.utc)
        self.started=iso(self.now-timedelta(seconds=2))
        self.finished=iso(self.now-timedelta(seconds=1))

    def capture(self,*,origin="SYNTHETIC_TEST",data=None):
        return record_capture(self.db,payload() if data is None else data,
          season=2026,started_at_utc=self.started,
          completed_at_utc=self.finished,origin=origin)

    def test_full_payload_hash_chain_and_unavailable_provider_time(self):
        first=self.capture()
        evidence=verify_chain(self.db)
        self.assertEqual(evidence["sessions"],1)
        self.assertEqual(evidence["fixture_records"],380)
        self.assertEqual(first["chain_sha256"],evidence["final_chain_sha256"])
        row=self.db.execute("SELECT source_published_at_utc,source_published_at_state,training_allowed FROM captures").fetchone()
        self.assertEqual(row,(None,"UNAVAILABLE",0))
        self.assertFalse(evidence["training_allowed"])

    def test_no_backdating_or_using_synthetic_history(self):
        self.capture()
        future=iso(self.now+timedelta(days=1))
        self.assertIsNone(select_result_asof(self.db,1800000,future))
        self.assertIsNone(select_result_asof(self.db,1800000,self.started))

    def test_real_observation_future_only_for_finished(self):
        self.capture(origin="NETWORK_OBSERVED")
        before=iso(self.now-timedelta(seconds=3))
        after=iso(self.now+timedelta(days=1))
        self.assertIsNone(select_result_asof(self.db,1800000,before))
        answer=select_result_asof(self.db,1800000,after)
        self.assertEqual(answer["result_home_90"],2)
        self.assertEqual(answer["result_away_90"],1)
        self.assertIsNone(answer["source_published_at_utc"])
        self.assertFalse(answer["historical_prematch_certification"])
        self.assertFalse(answer["training_allowed"])
        self.assertIsNone(select_result_asof(self.db,1800001,after))

    def test_session_and_record_both_immutable(self):
        self.capture()
        with self.assertRaisesRegex(sqlite3.DatabaseError,"CAPTURE_IMMUTABLE"):
            self.db.execute("UPDATE captures SET origin='NETWORK_OBSERVED'")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"RECORD_IMMUTABLE"):
            self.db.execute("DELETE FROM capture_records")
        self.db.rollback()

    def test_tampered_payload_detected_even_if_local_trigger_dropped(self):
        self.capture()
        self.db.execute("DROP TRIGGER capture_record_no_update")
        self.db.execute("UPDATE capture_records SET record_json='{}' WHERE provider_fixture_id=1800000")
        with self.assertRaisesRegex(ValueError,"(TAMPERED|RESPONSE_ROW)"):
            verify_chain(self.db)

    def test_duplicate_id_and_bad_time_rejected(self):
        altered=payload()
        altered["response"][1]["fixture"]["id"]=1800000
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            self.capture(data=altered)
        with self.assertRaisesRegex(ValueError,"UNTRUSTWORTHY"):
            record_capture(self.db,payload(),season=2026,
                started_at_utc=self.finished,completed_at_utc=self.started)

    def test_version_chain_multiple_observations(self):
        self.capture()
        self.now+=timedelta(seconds=1)
        self.started=iso(self.now-timedelta(seconds=1))
        self.finished=iso(self.now)
        self.capture()
        x=verify_chain(self.db)
        self.assertEqual(x["sessions"],2)
        self.assertEqual(x["fixture_records"],760)
        a=self.db.execute("SELECT prev_chain_sha256 FROM captures ORDER BY rowid LIMIT 1 OFFSET 1").fetchone()[0]
        b=self.db.execute("SELECT chain_sha256 FROM captures ORDER BY rowid LIMIT 1").fetchone()[0]
        self.assertEqual(a,b)

    def test_sealed_backup_roundtrip_and_cipher_tamper(self):
        self.capture()
        pub=self.dir/"pub.pem";pub.write_bytes(self.pub)
        priv=self.dir/"priv.pem";priv.write_bytes(self.priv)
        dest=self.dir/"pit.enc";mf=self.dir/"pit.json";target=self.dir/"restore.sqlite3"
        meta=seal(self.path,pub,dest,mf,allow_synthetic=True)
        self.assertFalse(meta["training_allowed"])
        self.assertNotIn(b'1800000',dest.read_bytes())
        out=restore(dest,mf,priv,target)
        self.assertEqual(out["evidence"]["fixture_records"],380)
        self.assertFalse(out["historical_before_observation_certified"])
        self.assertRaises(FileExistsError,restore,dest,mf,priv,target)
        target.unlink()
        b=bytearray(dest.read_bytes());b[-2]^=1;dest.write_bytes(b)
        with self.assertRaisesRegex(ValueError,"ENCRYPTED_CHECKSUM"):
            restore(dest,mf,priv,target)

    def test_newer_postponed_revision_blocks_old_finished_result(self):
        first=self.capture(origin="NETWORK_OBSERVED")
        midpoint=iso(self.now)
        self.now+=timedelta(seconds=2)
        self.started=iso(self.now-timedelta(seconds=1))
        self.finished=iso(self.now)
        revised=payload(status="PST")
        self.capture(origin="NETWORK_OBSERVED",data=revised)
        self.assertIsNotNone(select_result_asof(self.db,1800000,midpoint))
        self.assertIsNone(select_result_asof(
            self.db,1800000,iso(self.now+timedelta(days=1))))
        self.assertEqual(verify_chain(self.db)["sessions"],2)

    def test_no_synthetic_archive_can_claim_real_provenance(self):
        self.capture()
        pub=self.dir/"pub.pem";pub.write_bytes(self.pub)
        with self.assertRaisesRegex(ValueError,"NON_REAL_CAPTURE"):
            seal(self.path,pub,self.dir/"out.enc",self.dir/"out.json")

if __name__=="__main__":
    unittest.main()
