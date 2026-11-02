"""Offline, no provider or protected TEST access."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from src.kb3_pit_ledger import canonical
from src.kb3_step16_progressive_shadow import (
    MODEL, ShadowAuditError, assess, verified_rows,
)

UTC = timezone.utc

def make_rows(n=42):
    base = datetime(2026, 9, 1, tzinfo=UTC)
    rows=[]
    for i in range(n):
        ko=base+timedelta(days=i)
        rows.append({"id":f"test{i}","league":"ESP",
                     "kickoff":ko,"settled":ko+timedelta(hours=4),
                     "p":{"1":0.5,"X":0.25,"2":0.25},
                     "label":("1","X","2")[i%3]})
    return rows

class ProgressiveShadowTests(unittest.TestCase):
    def test_progressively_fits_only_on_past_settled_rows(self):
        r=assess(make_rows(42),min_prior=30)
        self.assertEqual(r["diagnostic_evaluated_rows"],12)
        self.assertEqual(r["sample_evaluation_provenance"][0]["prior_settled_n"],30)
        self.assertFalse(r["production_calibrator_changed"])
        self.assertFalse(r["catboost_retrained"])
        self.assertFalse(r["formal_gate16_pass"])
        self.assertIsNotNone(r["raw_metrics"])

    def test_no_future_or_same_kickoff_settlement_in_training(self):
        rows=make_rows(34)
        rows[1]["settled"]=rows[33]["kickoff"]+timedelta(days=2)
        r=assess(rows,min_prior=30)
        # 33rd match has only 29 valid earlier known results (excluded row 1).
        self.assertEqual(r["diagnostic_evaluated_rows"],3)
        self.assertEqual(r["sample_evaluation_provenance"][0]["prior_settled_n"],30)
        self.assertEqual(r["sample_evaluation_provenance"][0]["forecast_id"],"test31")
        self.assertTrue(r["does_not_substitute_formal_100_plus_new_50"])

    def test_duplicates_rejected(self):
        rows=make_rows(32);rows[5]["id"]=rows[4]["id"]
        with self.assertRaises(ShadowAuditError):
            assess(rows)

    def test_not_enough_results_no_phantom_metrics(self):
        r=assess(make_rows(12))
        self.assertEqual(r["status"],"COLLECTING_NO_EVALUATION")
        self.assertIsNone(r["raw_metrics"])
        self.assertEqual(r["diagnostic_evaluated_rows"],0)

    def test_db_requires_host_proofs_and_exact_forecast(self):
        with tempfile.TemporaryDirectory() as t:
            db_path=Path(t)/"staging.sqlite"
            ko=datetime(2026,9,3,tzinfo=UTC)
            cap=ko-timedelta(hours=5); proof=ko-timedelta(hours=3)
            with sqlite3.connect(db_path) as c:
                c.executescript("""
                CREATE TABLE model_meta(model TEXT);
                CREATE TABLE forecasts(id TEXT,model TEXT,league TEXT,
                  native_match_id TEXT,kickoff_utc TEXT,captured_at_utc TEXT,payload_json TEXT);
                CREATE TABLE settlements(forecast_id TEXT,outcome TEXT,settled_utc TEXT);
                CREATE TABLE m0720_github_push_proofs(
                  forecast_id TEXT,github_server_event_utc TEXT,source TEXT);
                """)
                c.execute("INSERT INTO model_meta VALUES(?)",(MODEL,))
                body={"model_version":MODEL,"phase":"EARLY",
                      "provider_match_id":"m_demo","league_country":"ESP",
                      "p_1x2":{"1":0.5,"X":0.25,"2":0.25}}
                fid=sha256(canonical(body)).hexdigest()
                body["forecast_sha256"]=fid
                c.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?,?)",
                          (fid,MODEL,"ESP","m_demo",ko.isoformat(),cap.isoformat(),json.dumps(body)))
                c.execute("INSERT INTO settlements VALUES(?,?,?)",
                          (fid,"1",(ko+timedelta(hours=4)).isoformat()))
                # Commit the fixture before the independent read-only connection.
                c.commit()
                # Missing authenticated proof: no eligible rows.
                self.assertEqual(verified_rows(db_path),[])
                c.execute("INSERT INTO m0720_github_push_proofs VALUES(?,?,?)",
                          (fid,proof.isoformat(),
                           "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES"))
            self.assertEqual(len(verified_rows(db_path)),1)
            with sqlite3.connect(db_path) as c:
                c.execute("UPDATE m0720_github_push_proofs SET github_server_event_utc=?",
                          ((ko+timedelta(minutes=1)).isoformat(),))
            with self.assertRaisesRegex(ShadowAuditError,"TIME_OR_HOST_PROOF"):
                verified_rows(db_path)

if __name__=="__main__":
    unittest.main()
