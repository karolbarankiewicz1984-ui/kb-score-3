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

    def test_diagnostic_cannot_claim_comparison_from_empty_proofs(self):
        # Copy-based engine evaluation returns no artificial performance
        # in the original sample with no server-attested new challengers.
        result=assess(DB)
        if result["host_attested_challenger_rows"]==0:
            self.assertEqual(result["same_fixture_attested_settled_triplets"],0)
            self.assertFalse(result["performance_claim_allowed"])

if __name__=="__main__":
    unittest.main()
