"""Codex schema only: independent dry-run on a COPY of real GitHub 3-league SQLite.

This does not apply earlier R1-R6 Python modules or touch any original data/model.
No credentials, network, provider, training or protected TEST.
"""
from pathlib import Path
import hashlib
import sqlite3
import tempfile
import shutil
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/forward_m0/kb3_forward_m0.sqlite"
MIGRATION=ROOT/"migrations/005_m0_publication_proofs.sql"
NEW_TABLES={"m0_shadow_publication_proofs","m0_shadow_calibration_proof_members"}

def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def tables(db):
    return {x[0] for x in db.execute(
       "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

def old_fingerprint(db,names):
    h=hashlib.sha256()
    for name in sorted(names):
        safe='"'+name.replace('"','""')+'"'
        h.update(name.encode())
        for row in db.execute("SELECT * FROM "+safe):
            h.update(repr(row).encode("utf8"))
    return h.hexdigest()

class GenuineSqliteMigrationOnlyTests(unittest.TestCase):
    def test_actual_database_copy_migration_guard(self):
        self.assertTrue(SOURCE.is_file(),"REAL_THREE_LEAGUE_SQLITE_REQUIRED")
        before=sha256(SOURCE)
        self.assertTrue(MIGRATION.is_file())
        sql=MIGRATION.read_text()
        self.assertNotIn("DROP TABLE",sql.upper())
        self.assertNotIn("DELETE FROM",sql.upper())  # BEFORE UPDATE ON is an immutable trigger, not a data mutation
        with tempfile.TemporaryDirectory() as td:
            cp=Path(td)/"kb3_copy.sqlite"
            shutil.copy2(SOURCE,cp)
            with sqlite3.connect(cp) as db:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                original=tables(db)
                self.assertNotIn("m0_shadow_publication_proofs",original)
                original_digest=old_fingerprint(db,original)
                db.executescript(sql)
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                self.assertFalse(db.execute("PRAGMA foreign_key_check").fetchall())
                self.assertEqual(tables(db)-original,NEW_TABLES)
                self.assertEqual(old_fingerprint(db,original),original_digest)
                for trigger in ("m0_publication_no_update","m0_publication_no_delete",
                                "m0_cal_proof_no_update","m0_cal_proof_no_delete"):
                    self.assertIsNotNone(db.execute(
                       "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
                       (trigger,)).fetchone())
                self.assertEqual(db.execute(
                   "SELECT COUNT(*) FROM m0_shadow_publication_proofs").fetchone()[0],0)
                self.assertEqual(db.execute(
                   "SELECT COUNT(*) FROM m0_shadow_calibration_proof_members").fetchone()[0],0)
                print("CODEX_MIGRATION_COPY_ONLY_EXISTING_TABLES",len(original),
                      "ROWS_UNMODIFIED","NEW_TABLES",len(NEW_TABLES),
                      "SOURCE_SHA256",before,"NO_API")
        self.assertEqual(sha256(SOURCE),before,"ORIGINAL_SQLITE_WAS_CHANGED")

    def test_migration_rollback_of_unsafe_operation_on_copy(self):
        with tempfile.TemporaryDirectory() as td:
            cp=Path(td)/"rollback.sqlite"
            shutil.copy2(SOURCE,cp)
            with sqlite3.connect(cp) as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE codex_unsafe_rollback_marker (x INTEGER)")
                db.rollback()
                self.assertNotIn("codex_unsafe_rollback_marker",tables(db))

if __name__=="__main__":
    unittest.main()
