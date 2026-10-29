"""Step16 forward calibration: independent false-ready rejection and class bins."""
import copy
import json
import unittest
from pathlib import Path

from src.kb3_step16_calibration_readiness import (
    audit_initial_real_receipts, per_class_reliability,
    Step16ReadinessError, FIT_MIN, HOLDOUT_MIN,
)

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"data/audits/m0_shadow_settlements/2026-10-29/M0_SETTLEMENT_LOGLOSS_BRIER_AND_CALIBRATION.json"
B=ROOT/"data/pit_sidecar/m0_postmatch/2026-10-29/run-082743157159/M0_POSTMATCH_AND_CALIBRATION_REVIEW.json"


def fixture():
    return json.loads(A.read_text()),json.loads(B.read_text())


class Step16InitialSafety(unittest.TestCase):
    def test_actual_two_reports_same_zero_and_no_t_fit(self):
        a,b=fixture()
        x=audit_initial_real_receipts(a,b)
        self.assertEqual(x["independently_settled_unique_games"],0)
        self.assertEqual(x["fit_remaining"],FIT_MIN)
        self.assertEqual(x["prospective_holdout_minimum"],HOLDOUT_MIN)
        self.assertFalse(x["candidate_fitted"])
        self.assertFalse(x["holdout_evaluated"])
        self.assertFalse(x["formal_gate16_pass"])
        self.assertFalse(x["auto_activation"])
        self.assertFalse(x["protected_test_2026_27_read"])

    def test_forged_old_report_hash_fails(self):
        a,b=fixture()
        a["total_settled"]=100
        with self.assertRaises(Step16ReadinessError):
            audit_initial_real_receipts(a,b)

    def test_fake_second_provider_100_is_not_enough(self):
        a,b=fixture()
        b["settlement"]["total_settled"]=100
        b["evaluation"]["scored_independent_matches"]=100
        with self.assertRaises(Step16ReadinessError):
            audit_initial_real_receipts(a,b)

    def test_no_changing_test_flag(self):
        a,b=fixture()
        b["original_Premier_League_TEST_accessed"]=True
        with self.assertRaises(Step16ReadinessError):
            audit_initial_real_receipts(a,b)

    def test_no_early_candidate_at_zero(self):
        a,b=fixture()
        b["evaluation"]["new_calibration_candidate"]={"temperature":0.7}
        with self.assertRaises(Step16ReadinessError):
            audit_initial_real_receipts(a,b)

    def test_no_fake_server_first_publication_proof(self):
        a,b=fixture()
        x=audit_initial_real_receipts(a,b)
        self.assertFalse(x["real_prematch_first_publication_independently_proven"])

    def test_simple_perclass_exact_bins(self):
        p=[{"1":0.8,"X":0.1,"2":0.1},
           {"1":0.1,"X":0.7,"2":0.2},
           {"1":0.1,"X":0.2,"2":0.7}]
        s=per_class_reliability(p,["1","X","2"],bins=5)
        self.assertEqual(s["n"],3)
        self.assertEqual(set(s["classes"]),{"1","X","2"})
        self.assertTrue(all(sum(v["count"] for v in s["classes"][k]["reliability"])==3
                         for k in ("1","X","2")))
        self.assertGreater(s["multiclass_brier_sum3"],0)
        self.assertFalse(s["training_or_calibration_performed"])

    def test_perclass_reject_invalid(self):
        with self.assertRaises(Step16ReadinessError):
            per_class_reliability([],[])
        with self.assertRaises(Step16ReadinessError):
            per_class_reliability([{"1":.8,"X":.1,"2":.7}],["1"])
        with self.assertRaises(Step16ReadinessError):
            per_class_reliability([{"1":.8,"X":.1,"2":.1}],["not_label"])
        with self.assertRaises(Step16ReadinessError):
            per_class_reliability([{"1":.8,"X":.1,"2":.1}],["1"],bins=1)


if __name__=="__main__":
    unittest.main()
