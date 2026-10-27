"""Admission test for original Step13 scope, deliberately without network/TEST."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from src.kb3_step13_original_acceptance import check_original_scope,PINNED,ACCEPTANCE
from src.kb3_step13_baseline import BaselineSafetyError


class OriginalStep13Gate(TestCase):
    def test_all_original_deliverables_are_reproducible_and_separate_production(self):
        a=check_original_scope()
        self.assertEqual(a["scope"],ACCEPTANCE)
        self.assertTrue(a["step13_original_scope_accepted"])
        self.assertEqual(a["train_rows"],760)
        self.assertEqual(a["retrospective_validation_rows"],380)
        self.assertEqual(a["historical_test_rows_read"],0)
        self.assertEqual(a["forward_test_results_read"],0)
        self.assertEqual(a["forward_prematch_predictions_frozen"],20)
        self.assertFalse(a["global_production_eligibility_granted"])
        self.assertFalse(a["historical_provider_prematch_pit_certified"])
        self.assertFalse(a["model_champion_selected"])
        self.assertFalse(a["training_allowed"])
        self.assertEqual(a["original_requirements"]["original_step13_checklist"],"PASS_LIMITED_SCOPE")
        self.assertTrue(a["reference_is_unfitted_uniform_chance_not_an_empirical_competitor"])

    def test_missing_audit_fails_closed(self):
        with TemporaryDirectory() as t:
            with self.assertRaises(FileNotFoundError):
                check_original_scope(root=t)

    def test_hash_tampering_fails_closed(self):
        with TemporaryDirectory() as root:
            root=Path(root)
            for rel,_ in PINNED.values():
                destination=root/rel
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(Path(rel).read_bytes())
            path=root/PINNED["real_retro"][0]
            x=json.loads(path.read_text())
            x["train_partition_rows"]=1000
            path.write_text(json.dumps(x),encoding="utf8")
            with self.assertRaisesRegex(BaselineSafetyError,"TAMPERED_real_retro"):
                check_original_scope(root=root)
