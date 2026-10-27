"""Only existing forecast and synthetic rating values; never read TEST results."""
import copy,json,unittest
from pathlib import Path
from src.kb3_step13_math_independent_audit import check_math
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_forward_score import SOURCE_FILE

class Step13IndependentMath(unittest.TestCase):
    def load(self):return json.loads(Path(SOURCE_FILE).read_text(encoding="utf8"))
    def test_algebra_and_ten_frozen_prematch_predictions(self):
        r=check_math(self.load())
        self.assertEqual(r["identity_checks"],35)
        self.assertEqual(r["result_labels_read"],0)
        self.assertEqual(r["api_requests"],0)
        self.assertFalse(r["training_allowed"])
        self.assertTrue(all(v<1e-9 for v in r["numerical_max_absolute_deviation"].values()))
    def test_even_one_modified_prediction_fails(self):
        r=self.load()
        r["forecasts"][0]["probabilities_1x2"]["1"]+=.001
        with self.assertRaisesRegex(BaselineSafetyError,"SNAPSHOT_CHANGED"):
            check_math(r)
    def test_production_gate_cannot_override_snapshot(self):
        r=self.load()
        r["test_results_accessed"]=1
        with self.assertRaisesRegex(BaselineSafetyError,"SNAPSHOT_CHANGED"):
            check_math(r)
if __name__=="__main__":unittest.main()
