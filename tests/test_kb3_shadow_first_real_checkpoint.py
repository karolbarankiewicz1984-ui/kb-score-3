"""Offline checkpoint tests only: fake records NEVER count as real future matches."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.kb3_shadow_first_real_checkpoint import (
    audit,hash_obj,CheckpointError,PIN_SHA,MODEL)


class RealShadowCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"sample.sqlite"

    def make_base(self):
        with sqlite3.connect(self.db) as db:
            db.executescript("""
            CREATE TABLE forecasts(
              id TEXT PRIMARY KEY,payload_json TEXT NOT NULL,
              captured_at_utc TEXT NOT NULL,kickoff_utc TEXT NOT NULL,
              league TEXT NOT NULL,native_match_id TEXT NOT NULL);
            CREATE TABLE settlements(
              forecast_id TEXT PRIMARY KEY,outcome TEXT);
            """)

    def make_pair(self):
        self.make_base()
        cutoff="2026-11-05T07:10:00Z"
        stamp="2026-11-05T07:11:00Z"
        kick="2026-11-05T12:00:00Z"
        parent={
          "model_version":"M0_ELO_POISSON_RESEARCH_720TRAIN_V1",
          "league_country":"ESP","provider_match_id":"synthetic-fixture",
          "kickoff_utc":kick,"feature_cutoff_utc":cutoff,
          "generated_at_utc":cutoff,
          "feature_sha256":"f"*64,"source_chain_sha256":"c"*64,
          "production_approved":False,"training_allowed":False,
          "p_1x2":{"1":0.4,"X":0.3,"2":0.3}}
        pid=hash_obj(parent)
        parent["forecast_sha256"]=pid
        child={
          "model_version":MODEL,"model_bytes_sha256":PIN_SHA,
          "source_m0_forecast_sha256":pid,
          "kickoff_utc":kick,"shadow_generated_at_utc":stamp,
          "feature_sha256":parent["feature_sha256"],
          "source_chain_sha256":parent["source_chain_sha256"],
          "original_feature_cutoff_utc":cutoff,
          "league_country":"ESP","provider_match_id":"synthetic-fixture",
          "production_approved":False,"official_fit_eligible":False,
          "research_only":True,"p_1x2":{"1":0.5,"X":0.25,"2":0.25}}
        sid=hash_obj(child)
        child["shadow_sha256"]=sid
        with sqlite3.connect(self.db) as db:
            db.execute("""INSERT INTO forecasts(
              id,payload_json,captured_at_utc,kickoff_utc,league,native_match_id)
              VALUES(?,?,?,?,?,?)""",(pid,json.dumps(parent),cutoff,kick,"ESP",
                                       "synthetic-fixture"))
            db.executescript("""
              CREATE TABLE kb3_p1_shadow_six_new_only(
                id TEXT PRIMARY KEY,payload_json TEXT NOT NULL,
                source_m0_forecast_sha256 TEXT NOT NULL,
                model_bytes_sha256 TEXT NOT NULL,
                kickoff_utc TEXT NOT NULL,
                shadow_generated_at_utc TEXT NOT NULL);
            """)
            db.execute("""INSERT INTO kb3_p1_shadow_six_new_only
              (id,payload_json,source_m0_forecast_sha256,model_bytes_sha256,
               kickoff_utc,shadow_generated_at_utc) VALUES(?,?,?,?,?,?)""",
               (sid,json.dumps(child),pid,PIN_SHA,kick,stamp))
        return sid,pid

    def test_absent_db_requires_proof_and_does_not_create_file(self):
        self.assertFalse(self.db.exists())
        a=audit(self.db)
        self.assertEqual(a["state"],"NO_PERSISTED_M0_SQLITE_FOUND")
        self.assertFalse(a["real_pre_match_pair_confirmed"])
        self.assertFalse(self.db.exists())

    def test_old_and_new_m0_without_shadow_are_not_fake_pairs(self):
        self.make_base()
        with sqlite3.connect(self.db) as db:
            db.execute("""INSERT INTO forecasts(id,payload_json,captured_at_utc,
              kickoff_utc,league,native_match_id) VALUES(?,?,?,?,?,?)""",
             ("fake","{}","2026-11-05T07:10:00Z",
              "2026-11-05T12:00:00Z","ESP","synthetic-only"))
        x=audit(self.db)
        self.assertEqual(x["state"],"NEW_M0_CAPTURE_WITHOUT_ELIGIBLE_SHADOW_PAIRS")
        self.assertEqual(x["m0_new_since_activation"],1)
        self.assertEqual(x["m0_shadow_pair_same_source_count"],0)

    def test_one_real_shaped_pair_remains_unattested_until_host_record(self):
        sid,pid=self.make_pair()
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        x=audit(self.db)
        after=hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(before,after,"AUDIT_MODIFIED_SQLITE")
        self.assertEqual(x["state"],
            "REAL_CAPTURED_PAIRS_PENDING_INDEPENDENT_GITHUB_HOST_PROOF")
        self.assertEqual(x["m0_shadow_pair_same_source_count"],1)
        self.assertEqual(x["github_host_verified_shadow_pairs"],0)
        self.assertFalse(x["github_host_artifact_proof_confirmed"])
        self.assertFalse(x["settled_attested_pair_confirmed"])
        self.assertEqual(x["official_fit_increment"],0)

    def test_only_host_proven_and_settled_same_fixture_counts(self):
        sid,pid=self.make_pair()
        with sqlite3.connect(self.db) as db:
            db.executescript("""
             CREATE TABLE kb3_p1_shadow_six_host_proofs(
               shadow_sha256 TEXT PRIMARY KEY,
               github_artifact_id TEXT NOT NULL,
               github_server_artifact_created_utc TEXT NOT NULL);
            """)
            db.execute("""INSERT INTO kb3_p1_shadow_six_host_proofs
              (shadow_sha256,github_artifact_id,
               github_server_artifact_created_utc) VALUES(?,?,?)""",
               (sid,"12345","2026-11-05T07:15:00Z"))
        a=audit(self.db)
        self.assertEqual(a["state"],
          "GENUINE_HOST_ATTESTED_PREMATCH_PAIRS_NOT_SETTLED")
        self.assertEqual(a["github_host_verified_shadow_pairs"],1)
        self.assertEqual(a["settled_github_host_verified_pairs"],0)
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO settlements(forecast_id,outcome) VALUES (?,?)",
                       (pid,"1"))
        b=audit(self.db)
        self.assertEqual(b["state"],"FIRST_GENUINE_HOST_ATTESTED_SETTLED_PAIR")
        self.assertEqual(b["settled_github_host_verified_pairs"],1)
        self.assertEqual(b["official_fit_increment"],0)

    def test_tamper_prevented_not_silently_counted(self):
        sid,pid=self.make_pair()
        with sqlite3.connect(self.db) as db:
            db.execute("""UPDATE kb3_p1_shadow_six_new_only
                SET model_bytes_sha256=? WHERE id=?""",("0"*64,sid))
        with self.assertRaisesRegex(CheckpointError,
                                    "NEW_SHADOW_RESEARCH_VERSION_OR_APPROVAL_DRIFT"):
            audit(self.db)


if __name__=="__main__":
    unittest.main()
