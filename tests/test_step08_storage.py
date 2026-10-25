"""Gate 08: migrate, enforce constraints, verify backup and independent restore."""
import datetime as dt
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.kb3_storage import (
    backup_database, connect, initialize, restore_database, verify_database,
)


class StorageGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = initialize(self.root / "kb3.sqlite3")
        self.now = dt.datetime.now(dt.timezone.utc)
        self.now_utc = self.now.isoformat().replace("+00:00", "Z")
        self.early = (self.now - dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        self.future = (self.now + dt.timedelta(days=365)).isoformat().replace("+00:00", "Z")
        self.past = (self.now - dt.timedelta(days=365)).isoformat().replace("+00:00", "Z")

    def add_reference_fixture(self, *, kickoff=None, prefix="f"):
        kickoff = kickoff or self.future
        with connect(self.database) as c:
            c.execute("INSERT OR IGNORE INTO providers(provider_id,name,created_utc) VALUES (1,'API-Football',?)",(self.now_utc,))
            c.execute("INSERT OR IGNORE INTO providers(provider_id,name,created_utc) VALUES (2,'PitchAPI',?)",(self.now_utc,))
            c.execute("INSERT OR IGNORE INTO competitions(competition_id,name,country) VALUES (1,'Premier League','England')")
            c.execute("INSERT OR IGNORE INTO seasons(season_id,competition_id,start_year,season_label) VALUES (1,1,2029,'2029/30')")
            c.execute("INSERT OR IGNORE INTO teams(team_id,canonical_name) VALUES (1,'Synthetic Team A')")
            c.execute("INSERT OR IGNORE INTO teams(team_id,canonical_name) VALUES (2,'Synthetic Team B')")
            c.execute("""
                INSERT INTO fixtures(season_id,home_team_id,away_team_id,kickoff_utc,
                    status,created_utc,updated_utc)
                VALUES(1,1,2,?,'SCHEDULED',?,?)
            """, (kickoff, self.now_utc, self.now_utc))
            fid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute("INSERT OR IGNORE INTO model_versions(model_version_id,family,code_sha,created_at_utc) VALUES ('baseline-test','TEST','test-sha',?)",(self.now_utc,))
            c.execute("""
                INSERT INTO feature_snapshots(feature_snapshot_id,fixture_id,model_version_id,
                    observed_cutoff_utc,generated_at_utc,feature_hash,availability_class)
                VALUES(?,?,'baseline-test',?,?,'feature-hash','VERIFIED_PREMATCH')
            """,(prefix, fid,self.early,self.now_utc))
        return fid

    def test_schema_migration_repeated_and_integrity(self):
        initialize(self.database) # idempotent
        with connect(self.database) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],1)
            self.assertEqual(verify_database(c)["integrity"],"ok")

    def test_duplicate_fixture_rejected(self):
        self.add_reference_fixture()
        with self.assertRaises(sqlite3.IntegrityError), connect(self.database) as c:
            c.execute("""
                INSERT INTO fixtures(season_id,home_team_id,away_team_id,kickoff_utc,
                    status,created_utc,updated_utc)
                VALUES(1,1,2,?,'SCHEDULED',?,?)
            """,(self.future,self.now_utc,self.now_utc))

    def test_review_pair_cannot_be_promoted_automatically(self):
        fid = self.add_reference_fixture()
        with self.assertRaises(sqlite3.IntegrityError), connect(self.database) as c:
            c.execute("""
                INSERT INTO fixture_provider_map(provider_id,provider_fixture_id,
                    fixture_id,match_quality,review_status)
                VALUES(2,'pending-fixture',?,'REVIEW','PENDING')
            """,(fid,))
        with connect(self.database) as c:
            c.execute("""
                INSERT INTO fixture_provider_map(provider_id,provider_fixture_id,
                    fixture_id,match_quality,review_status)
                VALUES(2,'pending-fixture',NULL,'REVIEW','PENDING')
            """)
            c.execute("""
                INSERT INTO fixture_provider_map(provider_id,provider_fixture_id,
                    fixture_id,match_quality,review_status)
                VALUES(1,'confirmed-fixture',?,'STRICT','APPROVED')
            """,(fid,))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fixture_provider_map").fetchone()[0],2)

    def test_unique_external_mapping(self):
        fid=self.add_reference_fixture()
        with connect(self.database) as c:
            c.execute("""
                INSERT INTO fixture_provider_map(provider_id,provider_fixture_id,
                    fixture_id,match_quality,review_status)
                VALUES(1,'f-1',?,'STRICT','APPROVED')
            """,(fid,))
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("""
                    INSERT INTO fixture_provider_map(provider_id,provider_fixture_id,
                        fixture_id,match_quality,review_status)
                    VALUES(1,'f-2',?,'STRICT','APPROVED')
                """,(fid,))

    def test_missing_is_null_not_zero(self):
        fid=self.add_reference_fixture()
        with connect(self.database) as c:
            c.execute("""
                INSERT INTO source_snapshots(snapshot_id,provider_id,endpoint_label,
                    captured_at_utc,source_data_hash,availability_class)
                VALUES('source1',1,'statistics',?,'hash','RETROSPECTIVE')
            """,(self.now_utc,))
            c.execute("""
                INSERT INTO match_stat_observations(fixture_id,team_id,provider_id,
                    snapshot_id,metric,numeric_value,missing_reason,observed_at_utc)
                VALUES(?,1,1,'source1','Red Cards',NULL,'NOT_AVAILABLE',?)
            """,(fid,self.now_utc))
            row=c.execute("SELECT numeric_value,missing_reason FROM match_stat_observations").fetchone()
            self.assertEqual(row,(None,'NOT_AVAILABLE'))
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("""
                    INSERT INTO match_stat_observations(fixture_id,team_id,provider_id,
                        snapshot_id,metric,numeric_value,missing_reason,observed_at_utc)
                    VALUES(?,2,1,'source1','Red Cards',NULL,NULL,?)
                """,(fid,self.now_utc))

    def insert_prediction(self, fid, *, pred="prediction-live",mode="LIVE",phase="EARLY",generated=None,feature="f"):
        with connect(self.database) as c:
            c.execute("""
                INSERT INTO predictions(prediction_id,fixture_id,model_version_id,
                    feature_snapshot_id,mode,phase,market,selection,p_raw,
                    generated_at_utc,freeze_hash)
                VALUES (?,?,'baseline-test',?,?,?,'1X2','HOME',0.60,?,'freeze-hash')
            """,(pred,fid,feature,mode,phase,generated or self.now_utc))
        return pred

    def test_prediction_is_forever_immutable(self):
        fid=self.add_reference_fixture()
        self.insert_prediction(fid)
        with connect(self.database) as c:
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE predictions SET p_raw=0.95 WHERE prediction_id='prediction-live'")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("DELETE FROM predictions WHERE prediction_id='prediction-live'")
            self.assertEqual(c.execute("SELECT p_raw FROM predictions").fetchone()[0],0.6)

    def test_past_live_prediction_blocked_but_replay_labeled(self):
        fid=self.add_reference_fixture(kickoff=self.past)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_prediction(fid)
        self.insert_prediction(fid, pred="historical",mode="HISTORICAL_REPLAY",phase="BACKTEST")
        with connect(self.database) as c:
            self.assertEqual(c.execute("SELECT mode FROM predictions").fetchone()[0],"HISTORICAL_REPLAY")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("""
                    INSERT INTO prediction_publications(publication_id,prediction_id,
                      published_at_utc,published_hash)
                    VALUES('pub','historical',?,'hash')
                """,(self.now_utc,))

    def test_publication_and_settlement_append_only(self):
        fid=self.add_reference_fixture()
        self.insert_prediction(fid)
        with connect(self.database) as c:
            c.execute("""
                INSERT INTO prediction_publications(publication_id,prediction_id,
                    published_at_utc,published_hash)
                VALUES('pub','prediction-live',?,'hash')
            """,(self.now_utc,))
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("DELETE FROM prediction_publications WHERE publication_id='pub'")
            c.execute("""
                INSERT INTO settlements(settlement_id,prediction_id,outcome,
                    settled_at_utc)
                VALUES('result','prediction-live','WIN',?)
            """,(self.now_utc,))
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE settlements SET outcome='LOSS' WHERE settlement_id='result'")

    def test_database_backup_restore_and_hash(self):
        fid=self.add_reference_fixture()
        self.insert_prediction(fid)
        folder=self.root/"safe-copy"
        manifest, snapshot=backup_database(self.database,folder)
        m=json.loads(manifest.read_text())
        self.assertEqual(m["row_counts"]["predictions"],1)
        self.assertTrue(m["production_encryption_required"])
        restored=self.root/"restored-from-copy.sqlite3"
        check=restore_database(manifest,folder,restored)
        self.assertTrue(check["restored"])
        self.assertEqual(check["source_sha256"],m["sha256"])
        with connect(restored) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE predictions SET p_raw=0 WHERE prediction_id='prediction-live'")
        with self.assertRaises(FileExistsError):
            restore_database(manifest,folder,restored)
        with open(snapshot,"ab") as stream:
            stream.write(b"tamper")
        with self.assertRaisesRegex(ValueError,"BACKUP_CHECKSUM_MISMATCH"):
            restore_database(manifest,folder,self.root/"corrupt-restore.sqlite3")

if __name__ == "__main__":
    unittest.main(verbosity=2)
