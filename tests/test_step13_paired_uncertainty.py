"""All records in this test are SYNTHETIC; no network or held-out TEST."""
import copy
import unittest

from test_step13_pitchapi_live_research import fixtures
from scripts.step13_pitchapi_research_once import extract_research_rows
from scripts.step13_paired_uncertainty_once import paired_uncertainty, quantile
from src.kb3_step13_retrospective import retrospective_research, POLICY
from src.kb3_step13_baseline import BaselineSafetyError


def synthetic_fixture_study():
    safe,seasons=fixtures()
    rows,_=extract_research_rows(seasons,safe_view=safe)
    return rows,retrospective_research(rows,policy=POLICY)


class Step13PairedBootstrapTests(unittest.TestCase):
    def test_original_380_matched_targets_and_no_test(self):
        rows,original=synthetic_fixture_study()
        x=paired_uncertainty(rows,reference=original,replicates=120)
        self.assertEqual(x["validation_n"],380)
        self.assertEqual(x["test_rows_read"],0)
        self.assertEqual([q["validation_n"] for q in x["folds"]],[60,126,123,71])
        self.assertEqual(x["folds"][0]["rolling_minus_expanding_logloss"],0)
        self.assertEqual(x["folds"][0]["rolling_minus_expanding_brier"],0)
        self.assertFalse(x["training_allowed"])
        self.assertFalse(x["gate13_pass"])
        self.assertFalse(x["current_model_parameter_change"])
        self.assertFalse(x["raw_results_exported"])
        self.assertFalse(x["predictions_per_match_exported"])
        self.assertTrue(x["overall"]["log"]["same_match_paired_losses"])

    def test_deterministic_replicates(self):
        rows,reference=synthetic_fixture_study()
        x=paired_uncertainty(rows,reference=reference,replicates=120)
        y=paired_uncertainty(rows,reference=reference,replicates=120)
        self.assertEqual(x,y)

    def test_edited_results_are_rejected_without_refitting(self):
        rows,ref=synthetic_fixture_study()
        rows[0]["goals_home_90"]+=1
        with self.assertRaisesRegex(BaselineSafetyError,"SOURCE_RECORDS_DRIFT"):
            paired_uncertainty(rows,reference=ref,replicates=120)

    def test_tampered_frozen_reference_rejected(self):
        rows,ref=synthetic_fixture_study()
        ref["overall"]["EXPANDING"]["multiclass_logloss_fold_weighted"]=0.0
        with self.assertRaisesRegex(BaselineSafetyError,"UNVERIFIED_REFERENCE"):
            paired_uncertainty(rows,reference=ref,replicates=120)

    def test_expected_reference_hash_is_pinned(self):
        rows,ref=synthetic_fixture_study()
        with self.assertRaisesRegex(BaselineSafetyError,"UNVERIFIED_REFERENCE"):
            paired_uncertainty(rows,reference=ref,expected_reference_sha="wrong",replicates=120)

    def test_ci_quantile_exact_index(self):
        self.assertEqual(quantile([0,1,2,3,4],0.5),2.0)
        self.assertAlmostEqual(quantile([0,1,2,3,4],0.25),1.0)
        self.assertAlmostEqual(quantile([0,1,2,3,4],0.375),1.5)


if __name__=="__main__":
    unittest.main()
