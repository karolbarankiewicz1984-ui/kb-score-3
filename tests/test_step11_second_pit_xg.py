"""Step11 second PIT compare + post-match xG provenance; no real API calls."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from src.kb3_pit_ledger import record_capture, as_utc
from src.kb3_pit_compare import compare
from src.kb3_xg_pit import record_xg,verify_xg,select_xg_asof
from src.kb3_pit_archive import seal,restore

def tm(delta):
    return (datetime.now(timezone.utc)+timedelta(seconds=delta)).isoformat().replace("+00:00","Z")

def fixture_data(status="NS"):
    out=[]
    for i in range(380):
        out.append({"fixture":{"id":1800000+i,"date":"2026-09-01T16:00:00Z",
                  "status":{"short":status if i==0 else "NS"}},
             "league":{"id":39,"season":2026},
             "teams":{"home":{"id":11,"name":"Arsenal"},
                      "away":{"id":22,"name":"Chelsea"}},
             "goals":{"home":2 if status=="FT" and i==0 else None,
                      "away":1 if status=="FT" and i==0 else None},
             "score":{"fulltime":{"home":2 if status=="FT" and i==0 else None,
                                  "away":1 if status=="FT" and i==0 else None}}})
    return {"errors":[],"paging":{"total":1},"response":out}

def af_game(status="FT",h="Arsenal"):
    return {"fixture":{"id":1800000,"date":"2026-09-01T16:00:00Z",
                       "status":{"short":status}},
            "teams":{"home":{"id":11,"name":h},
                     "away":{"id":22,"name":"Chelsea"}},
            "goals":{"home":2,"away":1}}

def pitch_game():
    return {"id":"m_123456","time_utc":"2026-09-01T16:00:00Z",
            "status":"finished","home_team":{"id":"h","name":"Arsenal"},
            "away_team":{"id":"a","name":"Chelsea"},
            "score_home":2,"score_away":1}

def shots(xg=0.4):
    return {"data":{"periods":[{"shots":[
      {"team_id":"h","expected_goals":xg},
      {"team_id":"a","expected_goals":0.2}]}]}}

class Step11Observations(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)
        self.c=sqlite3.connect(self.p/"first.sqlite3")
        self.d=sqlite3.connect(self.p/"second.sqlite3")
        self.addCleanup(self.c.close)
        self.addCleanup(self.d.close)

    def record_fixture(self,db,data,time1,time2):
        return record_capture(db,data,season=2026,
                              started_at_utc=tm(time1),
                              completed_at_utc=tm(time2),
                              origin="NETWORK_OBSERVED")

    def add_xg(self,db,match=None,shotdata=None,football=None):
        return record_xg(db,match or pitch_game(),shots() if shotdata is None else shotdata,
                         [af_game()] if football is None else football,
                         started_at_utc=tm(-3),completed_at_utc=tm(-2))

    def test_two_real_sessions_count_new_final(self):
        self.record_fixture(self.c,fixture_data("NS"),-40,-39)
        self.record_fixture(self.d,fixture_data("FT"),-10,-9)
        r=compare(self.c,self.d)
        self.assertEqual(r["counts"]["changed"],1)
        self.assertEqual(r["counts"]["new_finals"],1)
        self.assertEqual(r["matched_fixture_ids"],380)
        self.assertFalse(r["training_allowed"])

    def test_diff_fails_if_not_monotonic(self):
        self.record_fixture(self.c,fixture_data("NS"),-5,-4)
        self.record_fixture(self.d,fixture_data("FT"),-50,-49)
        with self.assertRaisesRegex(ValueError,"NON_CHRONOLOGICAL"):
            compare(self.c,self.d)

    def test_finished_xg_strict_asof_provenance(self):
        r=self.add_xg(self.c)
        self.assertTrue(r["accepted"])
        x=verify_xg(self.c)
        self.assertEqual(x["strict_complete"],1)
        self.assertIsNone(select_xg_asof(self.c,1800000,tm(-10)))
        ok=select_xg_asof(self.c,1800000,tm(100))
        self.assertEqual(ok["home_xg"],0.4)
        self.assertIsNone(ok["provider_published_at_utc"])
        self.assertFalse(ok["training_allowed"])

    def test_unmatched_team_is_quarantined_null(self):
        r=self.add_xg(self.c,football=[af_game(h="Different Alias")])
        self.assertFalse(r["accepted"])
        self.assertEqual(verify_xg(self.c)["strict_complete"],0)
        self.assertEqual(verify_xg(self.c)["quarantined"],1)
        self.assertIsNone(select_xg_asof(self.c,1800000,tm(100)))
        self.assertEqual(self.c.execute("SELECT xg_home FROM pit_xg_observations").fetchone()[0],None)

    def test_incomplete_shots_never_become_zero(self):
        incomplete={"data":{"periods":[{"shots":[{"team_id":"h",
                                                  "expected_goals":None}]}]}}
        r=self.add_xg(self.c,shotdata=incomplete)
        self.assertFalse(r["accepted"])
        self.assertEqual(verify_xg(self.c)["missing"],1)

    def test_non_final_provider_rejects_even_complete_xg(self):
        r=self.add_xg(self.c,football=[af_game(status="NS")])
        self.assertFalse(r["accepted"])
        self.assertEqual(verify_xg(self.c)["strict_complete"],0)

    def test_reject_backdating_and_xg_before_result(self):
        with self.assertRaisesRegex(ValueError,"XG_NETWORK_CLOCK"):
            record_xg(self.c,pitch_game(),shots(),[af_game()],
                      started_at_utc="2026-10-20T10:00:00Z",
                      completed_at_utc="2026-10-20T10:00:01Z")
        match=pitch_game()
        match["time_utc"]=tm(60)
        with self.assertRaisesRegex(ValueError,"XG_CANNOT_BE_PREMATCH"):
            self.add_xg(self.c,match=match)

    def test_xg_payload_mutation_detected(self):
        self.add_xg(self.c)
        self.c.execute("DROP TRIGGER pit_xg_no_update")
        self.c.execute("UPDATE pit_xg_observations SET raw_json='{}'")
        with self.assertRaisesRegex(ValueError,"XG_RAW_HASH_MISMATCH"):
            verify_xg(self.c)

    def test_encrypted_fixture_plus_xg_roundtrip(self):
        self.record_fixture(self.c,fixture_data("FT"),-40,-39)
        self.add_xg(self.c)
        private=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        pub=self.p/"pub.pem"; key=self.p/"key.pem"
        pub.write_bytes(private.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        key.write_bytes(private.private_bytes(
            serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        enc=self.p/"obs.enc";meta=self.p/"obs.json";target=self.p/"restored.sqlite3"
        info=seal(self.p/"first.sqlite3",pub,enc,meta)
        self.assertEqual(info["xg_evidence"]["strict_complete"],1)
        self.assertFalse(info["training_allowed"])
        r=restore(enc,meta,key,target)
        self.assertTrue(r["restored"])
        with sqlite3.connect(target) as check:
            self.assertEqual(verify_xg(check)["captured"],1)


if __name__=="__main__":
    unittest.main()
