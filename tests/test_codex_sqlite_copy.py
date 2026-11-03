"""Additional failure injection on copies; authentic migration stays byte-identical."""
import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from test_codex_migration_offline import SOURCE,MIGRATION,tables,old_fingerprint,sha256

class SqliteCopyFailureTests(unittest.TestCase):
    def test_failed_migration_rolls_back_schema_and_all_original_rows(self):
        before=sha256(SOURCE)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"copy.sqlite";shutil.copy2(SOURCE,path)
            with sqlite3.connect(path) as db:
                original=tables(db);fingerprint=old_fingerprint(db,original)
                with self.assertRaises(sqlite3.OperationalError):
                    try:
                        db.executescript("BEGIN IMMEDIATE;\n"+MIGRATION.read_text()+"\nINVALID_MIGRATION_STATEMENT;")
                    except sqlite3.OperationalError:
                        db.rollback();raise
                self.assertEqual(tables(db),original)
                self.assertEqual(old_fingerprint(db,original),fingerprint)
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(sha256(SOURCE),before)

    def test_migrated_proofs_and_members_enforce_actual_update_delete_and_fk(self):
        before=sha256(SOURCE)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"copy.sqlite";shutil.copy2(SOURCE,path)
            with sqlite3.connect(path) as db:
                db.execute("PRAGMA foreign_keys=ON");db.executescript(MIGRATION.read_text())
                fid,sha,model=db.execute("SELECT forecast_id,prediction_payload_sha256,model_version_id FROM m0_shadow_1x2_forecasts LIMIT 1").fetchone()
                db.execute("INSERT INTO m0_shadow_publication_proofs VALUES(?,?,?,?,?,?,?,?)",
                           (fid,sha,"SYNTHETIC_ARTIFACT","SYNTHETIC_RUN","2026-10-01T00:00:00Z","a"*64,"2026-10-01T01:00:00Z","b"*64))
                db.execute("""INSERT INTO m0_shadow_calibration_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  ("SYNTHETIC_COPY_ONLY",model,"EARLY","ESP_ITA_GER_POOLED_RESEARCH","2026-10-01T00:00:00Z","2026-10-01T00:00:00Z",1.0,100,"c"*64,1.0,1.0,"d"*64,0))
                db.execute("INSERT INTO m0_shadow_calibration_proof_members VALUES(?,?,?)",("SYNTHETIC_COPY_ONLY",fid,"FIT"));db.commit()
                for table in ("m0_shadow_publication_proofs","m0_shadow_calibration_proof_members"):
                    for sql in ("DELETE FROM "+table,"UPDATE "+table+" SET forecast_id=forecast_id"):
                        with self.assertRaisesRegex(sqlite3.IntegrityError,"IMMUTABLE"):db.execute(sql)
                        db.rollback()
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("INSERT INTO m0_shadow_calibration_proof_members VALUES(?,?,?)",("MISSING",fid,"HOLDOUT"))
                db.rollback()
                self.assertFalse(db.execute("PRAGMA foreign_key_check").fetchall())
        self.assertEqual(sha256(SOURCE),before)

    def test_native_writers_reject_lock_conflict_without_half_pair(self):
        from src.kb3_pitch_native_ledger import record,verify
        from test_step11_pitch_native_ledger import season
        from test_codex_current_source_integrity import clock,shot_feed,stat_feed
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"source.sqlite"
            a=sqlite3.connect(path,timeout=0);b=sqlite3.connect(path,timeout=0)
            try:
                record(a,"matches",season(),started_at_utc=clock(-30),completed_at_utc=clock(-29))
                a.execute("BEGIN IMMEDIATE")
                with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                    record(b,"shots",shot_feed(),started_at_utc=clock(-20),completed_at_utc=clock(-19),
                        stats_payload=stat_feed(),stats_started_at_utc=clock(-18),stats_completed_at_utc=clock(-17))
                a.rollback();self.assertEqual(verify(a)["captures"],1)
                record(b,"shots",shot_feed(),started_at_utc=clock(-20),completed_at_utc=clock(-19),
                    stats_payload=stat_feed(),stats_started_at_utc=clock(-18),stats_completed_at_utc=clock(-17))
                self.assertEqual(verify(a)["captures"],2)
            finally:a.close();b.close()

if __name__=="__main__":unittest.main()
