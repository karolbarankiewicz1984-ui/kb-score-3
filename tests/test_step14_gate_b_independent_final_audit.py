"""Negative security/unit tests for revised Step14 B independent gate."""
import unittest,math
from scripts.step14_gate_b_independent_final_audit import (
    independently_score,_verify,Gate14BAuditError)

class GateBAuditTests(unittest.TestCase):
    def test_perfect_forecast_has_zero_brier_ece_and_logloss(self):
        labels=["1","X","2"]*124+["1","X"]
        probs=[{"1":float(y=="1"),"X":float(y=="X"),"2":float(y=="2")}
               for y in labels]
        r=independently_score(probs,labels)
        self.assertEqual(r["n"],374)
        self.assertAlmostEqual(r["log_loss"],0)
        self.assertAlmostEqual(r["brier_multiclass_sum3"],0)
        self.assertAlmostEqual(r["top1_ece_5_bins"],0)
    def test_uniform_class3_brier_and_log_loss_are_known(self):
        r=independently_score([{"1":1/3,"X":1/3,"2":1/3}]*374,
                              ["1","X","2"]*124+["1","X"])
        self.assertAlmostEqual(r["brier_multiclass_sum3"],2/3)
        self.assertAlmostEqual(r["brier_multiclass_mean3"],2/9)
        self.assertAlmostEqual(r["log_loss"],math.log(3))
    def test_reject_invalid_normalization(self):
        with self.assertRaises(Gate14BAuditError):
            independently_score([{"1":.3,"X":.3,"2":.3}]*374,["1"]*374)
    def test_reject_wrong_scope(self):
        with self.assertRaisesRegex(Gate14BAuditError,"MISSING_374"):
            independently_score([{"1":.5,"X":.3,"2":.2}],["1"])
    def test_explicit_fail_closed_guard(self):
        with self.assertRaisesRegex(Gate14BAuditError,"LOOKAHEAD"):
            _verify(False,"LOOKAHEAD")
if __name__=="__main__":unittest.main()
