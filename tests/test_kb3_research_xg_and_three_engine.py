"""Synthetic regression for read-only coverage and real-receipt validators."""
import copy
import json
import unittest
from pathlib import Path
from scripts.kb3_research_xg_coverage_readonly import analyze as xg_analyze, SUMMARY, CAPTURE
from scripts.kb3_research_three_engine_readiness import (
    analyze as engine_analyze, latest_settlement)


class ResearchAudits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xg=json.loads(SUMMARY.read_text())
        cls.capture=json.loads(CAPTURE.read_text())
        cls.path,cls.settle=latest_settlement()

    def test_research_xg_actual_repository_report_consistent(self):
        r=xg_analyze(self.xg,self.capture)
        self.assertEqual(r["native_xg_verified"],
                         self.capture["effective_xg_verified"])
        self.assertEqual(r["complete_both_teams_windows"]["xg5"],
                         self.xg["totals"]["pair_xg_5_complete"])
        self.assertFalse(r["formal_training_allowed"])
        self.assertFalse(r["historic_original_pit_certified"])

    def test_source_relabel_as_pit_fails_closed(self):
        r=copy.deepcopy(self.xg)
        r["retrospective_provider_original_publication_proven"]=True
        with self.assertRaises(ValueError):
            xg_analyze(r,self.capture)

    def test_corrupt_scope_totals_rejected(self):
        r=copy.deepcopy(self.xg)
        first=next(iter(r["by_scope"]))
        r["by_scope"][first]["pair_xg_5_complete"]+=1
        with self.assertRaises(ValueError):
            xg_analyze(r,self.capture)

    def test_existing_real_receipt_paired_counts(self):
        r=engine_analyze(self.settle)
        self.assertEqual(r["gate16"],"PENDING")
        self.assertFalse(r["formal_comparison_ready"])
        self.assertEqual(r["pending"],r["frozen_forecasts"]-r["settled_total"])

    def test_unverified_source_domain_fails_closed(self):
        r=copy.deepcopy(self.settle)
        r["step17_paired_same_fixture_readiness"]["evaluation_domain"]=(
            "HISTORICAL_RECONSTRUCTED_RESEARCH")
        with self.assertRaises(ValueError):
            engine_analyze(r)

    def test_unrealistic_settlement_counts_rejected(self):
        r=copy.deepcopy(self.settle)
        r["not_yet_settled"]=-1
        with self.assertRaises(ValueError):
            engine_analyze(r)


if __name__=="__main__":
    unittest.main()
