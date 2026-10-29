import unittest
from scripts.step14_train_760_decimal_FPL_FT_corrected_v2 import goal,CorrectedScoreError

class HistoricalFPLCorrectlyEncodedScoreTests(unittest.TestCase):
    def test_historic_FPL_integer_scores_accept_decimal_dot_zero(self):
        for raw,number in (("3.0",3),("0.0",0),("11.0",11),("3",3),("0",0),(3,3)):
            self.assertEqual(goal(raw),number)
    def test_never_round_fractional_future_bad_data_or_nan(self):
        for raw in ("",None,"2.5","nan","inf","-1.0","31.0","a","1e100"):
            with self.assertRaises(CorrectedScoreError):
                goal(raw)
    def test_boolean_never_legitimate_goal(self):
        with self.assertRaises(CorrectedScoreError):
            goal(True)

if __name__=="__main__":
    unittest.main()
