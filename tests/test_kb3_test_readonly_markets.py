"""Fail-closed TEST market preview: same frozen M0 and host proof, no writes."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.kb3_step15_goal_markets import markets_from_lambdas
from src.kb3_test_readonly_markets import (
    MODEL, TestMarketGateError, digest, from_frozen_parent, read_original_sqlite,
)

CUTOFF = "2026-11-05T08:18:40Z"
HOST = "2026-11-05T08:20:19Z"
KICKOFF = "2026-11-08T16:00:00Z"
PROOF = "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES"


def parent():
    joint = markets_from_lambdas(1.68, 1.10)
    original = {
        "model_version": MODEL,
        "league_country": "ESP",
        "provider_match_id": "m_AUTHENTIC_SHAPE_NOT_REAL",
        "feature_cutoff_utc": CUTOFF,
        "generated_at_utc": CUTOFF,
        "kickoff_utc": KICKOFF,
        "phase": "EARLY",
        "status": "RESEARCH_TRAIN720_UNCALIBRATED",
        "expected_goals": {"home": 1.68, "away": 1.10},
        "p_1x2": joint["p_1x2"],
        "p_over": joint["p_over"],
        "p_btts_yes": joint["p_btts"]["yes"],
        "source_chain_sha256": "a"*64,
        "feature_sha256": "b"*64,
        "params_sha256": "c"*64,
        "manifest_sha256": "d"*64,
        "original_provider_first_published_at_proven": False,
        "training_allowed": False,
        "production_approved": False,
    }
    original["forecast_sha256"] = digest(original)
    return original


def derive(p):
    return from_frozen_parent(p, original_id=p["forecast_sha256"],
                              host_event_utc=HOST, host_source=PROOF)


def temp_db(path, p, *, with_proof=True, with_settlement=False):
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE forecasts(id TEXT PRIMARY KEY,payload_json TEXT NOT NULL,
              kickoff_utc TEXT NOT NULL,captured_at_utc TEXT NOT NULL);
            CREATE TABLE m0720_github_push_proofs(forecast_id TEXT UNIQUE,
              github_server_event_utc TEXT NOT NULL,source TEXT NOT NULL);
            CREATE TABLE settlements(forecast_id TEXT UNIQUE);
        """)
        db.execute("INSERT INTO forecasts VALUES(?,?,?,?)",
                   (p["forecast_sha256"],json.dumps(p),p["kickoff_utc"],
                    p["generated_at_utc"]))
        if with_proof:
            db.execute("INSERT INTO m0720_github_push_proofs VALUES(?,?,?)",
                       (p["forecast_sha256"],HOST,PROOF))
        if with_settlement:
            db.execute("INSERT INTO settlements VALUES(?)",(p["forecast_sha256"],))
        db.commit()


class ReadonlyMarketTests(unittest.TestCase):
    def test_derived_math_and_complementarity(self):
        m = derive(parent())
        p = m["p_1x2"]
        self.assertAlmostEqual(m["p_double_chance"]["1X"],1-p["2"],places=11)
        self.assertAlmostEqual(m["p_double_chance"]["X2"],1-p["1"],places=11)
        self.assertAlmostEqual(m["p_double_chance"]["12"],1-p["X"],places=11)
        for line in ("1.5","2.5","3.5"):
            self.assertAlmostEqual(m["p_over"][line]+m["p_under"][line],1.0)
        self.assertAlmostEqual(sum(m["p_btts"].values()),1)
        self.assertFalse(m["production_approved"])
        self.assertFalse(m["new_independent_market_freeze_performed"])
        self.assertFalse(m["re_attested_original_artifact_bytes_by_this_reader"])
        self.assertFalse(m["formal_test_generator_gate_pass"])
        self.assertNotIn("odds",m)

    def test_tampered_frozen_parent_cannot_be_used(self):
        p=parent()
        p["expected_goals"]["home"]=9.0
        with self.assertRaisesRegex(TestMarketGateError,"HASH_MISMATCH"):
            derive(p)

    def test_hash_is_not_enough_if_probabilities_mismatch(self):
        p=parent()
        p["p_over"]["2.5"]=0.90
        p["forecast_sha256"]=digest({k:v for k,v in p.items()
                                      if k!="forecast_sha256"})
        with self.assertRaisesRegex(TestMarketGateError,"DIVERGES_FROM_FROZEN_M0"):
            derive(p)

    def test_late_host_proof_and_protected_league_rejected(self):
        p=parent()
        with self.assertRaisesRegex(TestMarketGateError,"HOST_PROOF_TIME"):
            from_frozen_parent(p,original_id=p["forecast_sha256"],
                              host_event_utc="2026-11-08T15:00:01Z",
                              host_source=PROOF)
        p=parent()
        p["league_country"]="ENG"
        p["forecast_sha256"]=digest({k:v for k,v in p.items()
                                     if k!="forecast_sha256"})
        with self.assertRaisesRegex(TestMarketGateError,"PROTECTED"):
            derive(p)

    def test_readonly_sqlite_and_no_retro_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"original.sqlite"
            temp_db(path,parent())
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            out=read_original_sqlite(path,as_of_utc="2026-11-05T16:00:00Z")
            after=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(before,after)
            self.assertEqual(out["count"],1)
            self.assertEqual(out["new_forecasts_created"],0)
            self.assertEqual(out["new_market_freezes_created"],0)
            self.assertEqual(out["official_fit_increment"],0)
            self.assertEqual(out["gate16"],"PENDING")
            self.assertEqual(read_original_sqlite(
                path,as_of_utc="2026-11-08T15:00:00Z")["count"],0)
            self.assertEqual(read_original_sqlite(
                path,as_of_utc="2026-11-09T09:00:00Z")["count"],0)

    def test_no_unattested_or_settled_rows_in_preview(self):
        for with_proof,with_settlement in ((False,False),(True,True)):
            with self.subTest(with_proof=with_proof,settled=with_settlement):
                with tempfile.TemporaryDirectory() as folder:
                    path=Path(folder)/"original.sqlite"
                    temp_db(path,parent(),with_proof=with_proof,
                            with_settlement=with_settlement)
                    out=read_original_sqlite(path,as_of_utc="2026-11-05T16:00:00Z")
                    self.assertEqual(out["count"],0)

    def test_reject_wrong_model_status_and_spoofed_proof(self):
        for key,value,pattern in (
            ("model_version","CATBOOST","NOT_FITTED"),
            ("status","PROMOTED","NOT_UNCHANGED"),
            ("training_allowed",True,"UNAUTHORIZED_APPROVAL"),
        ):
            p=parent()
            p[key]=value
            p["forecast_sha256"]=digest({k:v for k,v in p.items()
                                         if k!="forecast_sha256"})
            with self.subTest(key=key),self.assertRaisesRegex(
                TestMarketGateError,pattern):
                derive(p)
        with self.assertRaisesRegex(TestMarketGateError,"HOST_PROOF_CLASS"):
            p=parent()
            from_frozen_parent(p,original_id=p["forecast_sha256"],
                              host_event_utc=HOST,
                              host_source="USER_DECLARED_TIMESTAMP")


if __name__=="__main__":
    unittest.main()
