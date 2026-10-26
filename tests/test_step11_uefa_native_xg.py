"""Offline UEFA single-provider xG capture evidence and crypto safety."""
import copy
import tempfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
import unittest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from src.kb3_pitch_uefa_evidence import add_observation,verify_receipts,seal,restore
from scripts.step11_uefa_native_xg_capture_once import (
    select_sample,choose_league,SAMPLE_PER_COMPETITION,MAX_CALLS
)
from src.kb3_pitch_native import verify_native_shots

def now(shift=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=shift)).isoformat().replace("+00:00","Z")

def games(n=54):
    out=[]
    for i in range(n):
        out.append({"id":f"m_{i:06d}",
          "time_utc":f"2026-09-{i%26+1:02d}T15:00:00Z",
          "status":"finished",
          "home_team":{"id":f"t_{(2*i):06d}","name":"Team home"},
          "away_team":{"id":f"t_{(2*i+1):06d}","name":"Team away"},
          "score_home":2,"score_away":0})
    return out

def shots(mid="m_000000"):
    i=int(mid[2:])
    return {"data":{"match_id":mid,"periods":[{"shots":[
      {"team_id":f"t_{2*i:06d}","expected_goals":0.31},
      {"team_id":f"t_{2*i+1:06d}","expected_goals":0.19}]}]}}

class UefaNativeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key=rsa.generate_private_key(public_exponent=65537,key_size=3072)

    def setUp(self):
        self.records=[]
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.pub=self.folder/"pub.pem"
        self.priv=self.folder/"priv.pem"
        self.pub.write_bytes(self.key.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        self.priv.write_bytes(self.key.private_bytes(
            serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        self.start=now(-4);self.end=now(-3)

    def add(self,source="pitchapi:catalog",value=None):
        return add_observation(self.records,resource=source,
            payload={"data":"test"} if value is None else value,
            started=self.start,completed=self.end,origin="SYNTHETIC_TEST")

    def test_bounded_sample_spread_and_determinism(self):
        a,n=select_sample(games(),now())
        b,_=select_sample(list(reversed(games())),now())
        self.assertEqual(len(a),6)
        self.assertEqual(n,54)
        self.assertEqual([v["id"] for v in a],[v["id"] for v in b])
        self.assertGreaterEqual(len({x["time_utc"][:10] for x in a}),5)

    def test_filter_live_and_invalid_ids(self):
        g=games()
        g[0]["status"]="live"
        g[1]["time_utc"]=now(500)
        a,n=select_sample(g,now())
        self.assertEqual(n,52)
        self.assertEqual(len(a),6)
        g[0]["id"]=g[2]["id"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            select_sample(g,now())

    def test_not_enough_finished_matches(self):
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT"):
            select_sample(games(5),now())

    def test_finished_score_must_be_known(self):
        g=games()
        g[0]["score_home"]=None
        with self.assertRaisesRegex(ValueError,"SCORE_MISSING"):
            select_sample(g,now())

    def test_one_uefa_competition_2026_season(self):
        catalog=[{"name":"Europa League","seasons":["2026/2027"],"id":"id_a"},
                 {"name":"Europa League","seasons":["2024/2025"],"id":"id_b"}]
        self.assertEqual(choose_league(catalog,"europa league")["id"],"id_a")
        catalog.append(dict(catalog[0]))
        with self.assertRaisesRegex(ValueError,"NOT_UNIQUE"):
            choose_league(catalog,"europa league")

    def test_shot_response_must_have_correct_native_match_id(self):
        m=games()[0]
        val=verify_native_shots(m,shots(),observed_at_utc=now())
        self.assertEqual(val["shot_state"],"COMPLETE_SHOT_XG")
        self.assertEqual(val["xg_home"],0.31)
        bad=shots("m_000001")
        with self.assertRaisesRegex(ValueError,"FIXTURE_ID_MISMATCH"):
            verify_native_shots(m,bad,observed_at_utc=now())

    def test_no_missing_xg_as_numeric_zero(self):
        m=games()[0]
        feed=shots()
        feed["data"]["periods"][0]["shots"][0]["expected_goals"]=None
        val=verify_native_shots(m,feed,observed_at_utc=now())
        self.assertIsNone(val["xg_home"])
        self.assertIsNone(val["xg_away"])
        self.assertNotEqual(val["shot_state"],"COMPLETE_SHOT_XG")

    def test_chain_no_backdating(self):
        self.add()
        with self.assertRaisesRegex(ValueError,"NONMONOTONIC"):
            add_observation(self.records,resource="pitchapi:uefa:one",
             payload={},started=now(-30),completed=now(-29),origin="SYNTHETIC_TEST")
        with self.assertRaisesRegex(ValueError,"UNTRUSTWORTHY"):
            add_observation(self.records,resource="pitchapi:uefa:one",
             payload={},started=now(-1),completed=now(-2),origin="SYNTHETIC_TEST")

    def test_proof_detects_payload_tamper(self):
        self.add()
        self.records[0]["payload"]["data"]="tamper"
        with self.assertRaisesRegex(ValueError,"TAMPERED"):
            verify_receipts(self.records,allow_synthetic=True)

    def test_proof_rejects_origin_upgrade_and_duplicate_resource(self):
        self.add()
        self.assertRaisesRegex(ValueError,"NON_REAL",
                               verify_receipts,self.records)
        self.add(source="pitchapi:catalog")
        with self.assertRaisesRegex(ValueError,"DUPLICATE_RESOURCE"):
            verify_receipts(self.records,allow_synthetic=True)

    def test_crypto_round_trip_and_cipher_bit_flip(self):
        self.add()
        self.add(source="pitchapi:uefa:le",value={"matches":[{"id":"m_abcdef"}]})
        c=self.folder/"backup.enc"
        mf=self.folder/"backup.manifest.json"
        with self.assertRaisesRegex(ValueError,"NON_REAL"):
            seal(self.records,self.pub,c,mf)
        # Unit test only: the all-synthetic archive is never published.
        from unittest.mock import patch
        import src.kb3_pitch_uefa_evidence as mod
        original=mod.verify_receipts
        with patch.object(mod,"verify_receipts",side_effect=lambda rows:original(rows,allow_synthetic=True)):
            meta=seal(self.records,self.pub,c,mf)
        self.assertNotIn(b"m_abcdef",c.read_bytes())
        self.assertEqual(meta["proof"]["sessions"],2)
        val=restore(c,mf,self.priv,allow_synthetic=True)
        self.assertTrue(val["validated"])
        corrupt=bytearray(c.read_bytes());corrupt[-1]^=1;c.write_bytes(corrupt)
        with self.assertRaisesRegex(ValueError,"CHECKSUM"):
            restore(c,mf,self.priv,allow_synthetic=True)

    def test_budget_does_not_add_second_provider(self):
        self.assertEqual(SAMPLE_PER_COMPETITION,6)
        self.assertEqual(MAX_CALLS,15)

if __name__=="__main__":
    unittest.main()
