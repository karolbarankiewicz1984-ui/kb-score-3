"""Step17 zero-API independent frozen database benchmark regression tests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.kb3_step16_m0_720_eight_forward import DB
from scripts.step17_offline_three_engine_audit import (
    assess, file_sha256, PairedReadOnlyError, PAIR_KEYS,
)

class Step17OfflineReadOnlyTests(unittest.TestCase):
    def test_missing_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(PairedReadOnlyError, "MISSING"):
                assess(Path(td)/"nonexistent.sqlite")

    def test_original_ledger_byte_for_byte_unchanged(self):
        before=file_sha256(DB)
        result=assess(DB)
        self.assertEqual(file_sha256(DB),before)
        self.assertEqual(result["source_m0_sha256"],before)
        self.assertTrue(result["source_db_unchanged"])
        self.assertTrue(result["no_provider_calls"])
        self.assertFalse(result["winner_auto_selected"])
        self.assertFalse(result["protected_test_accessed"])
        self.assertEqual(result["gate17"],"PENDING")
        self.assertEqual(set(result["pairwise_common_n"]),set(PAIR_KEYS))
        self.assertTrue(all(n>=0 for n in result["pairwise_common_n"].values()))
        if result["same_fixture_attested_settled_triplets"]==0:
            self.assertFalse(result["performance_claim_allowed"])
            self.assertTrue(all(x is None for x in
                (pair["left"] for pair in result["pairwise_evaluation"].values()
                 if pair["common_n"]==0)))

    def test_three_way_intersection_requires_both_challenger_proofs(self):
        import sqlite3
        from scripts.step17_offline_three_engine_audit import three_way_count
        with sqlite3.connect(":memory:") as db:
            db.executescript("""
                CREATE TABLE forecasts (id TEXT PRIMARY KEY);
                CREATE TABLE settlements (forecast_id TEXT);
                CREATE TABLE m0720_github_push_proofs (forecast_id TEXT);
                CREATE TABLE step17_frozen_challengers (
                    challenger_sha256 TEXT PRIMARY KEY,
                    source_m0_forecast_sha256 TEXT, engine TEXT);
                CREATE TABLE step17_challenger_host_proofs (challenger_sha256 TEXT);
            """)
            for mid in ("A","B"):
                db.execute("INSERT INTO forecasts VALUES(?)",(mid,))
                db.execute("INSERT INTO settlements VALUES(?)",(mid,))
                db.execute("INSERT INTO m0720_github_push_proofs VALUES(?)",(mid,))
            for mid,engine in (("A","ELO_ONLY"),("A","CATBOOST_NO_XG"),
                               ("B","ELO_ONLY"),("B","CATBOOST_NO_XG")):
                db.execute("INSERT INTO step17_frozen_challengers VALUES(?,?,?)",
                           (mid+engine,mid,engine))
            db.execute("INSERT INTO step17_challenger_host_proofs VALUES(?)",
                       ("AELO_ONLY",))
            db.execute("INSERT INTO step17_challenger_host_proofs VALUES(?)",
                       ("BCATBOOST_NO_XG",))
            schema={x[0] for x in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(three_way_count(db,schema),0)
            db.execute("INSERT INTO step17_challenger_host_proofs VALUES(?)",
                       ("ACATBOOST_NO_XG",))
            self.assertEqual(three_way_count(db,schema),1)
            db.execute("INSERT INTO step17_challenger_host_proofs VALUES(?)",
                       ("BELO_ONLY",))
            self.assertEqual(three_way_count(db,schema),2)

    def test_diagnostic_cannot_claim_comparison_from_empty_proofs(self):
        # Copy-based engine evaluation returns no artificial performance
        # in the original sample with no server-attested new challengers.
        result=assess(DB)
        if result["host_attested_challenger_rows"]==0:
            self.assertEqual(result["same_fixture_attested_settled_triplets"],0)
            self.assertFalse(result["performance_claim_allowed"])

if __name__=="__main__":
    unittest.main()
