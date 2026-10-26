"""KB3 Step13: retrospective RESEARCH math regression, not verified PIT.

Tests use invented scores only, never the private owner's PitchAPI dataset.
"""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import unittest
from src.kb3_step13_retrospective import retrospective_research,POLICY
from src.kb3_step13_baseline import BaselineSafetyError


def fixture(i,stamp,gh,ga):
    return {
        "fixture_id":f"SYN-RETRO-{i:04d}",
        "home_team_id":f"SYN-T-{i%5:02d}",
        "away_team_id":f"SYN-T-{(i+1)%5:02d}",
        "kickoff_utc":stamp,"goals_home_90":gh,"goals_away_90":ga,
    }


def examples():
    rows=[]
    # Intentionally 8 old events prior to rolling fold2 lower bound (2023-10).
    # Only affects expanding fold2+, never rolling.
    for i in range(8):
        at=datetime(2023,8,2,12,tzinfo=timezone.utc)+timedelta(days=i*4)
        rows.append(fixture(i,at.isoformat().replace("+00:00","Z"),2,0))
    for i in range(8,32):
        at=datetime(2024,2,2,12,tzinfo=timezone.utc)+timedelta(days=(i-8)*8)
        rows.append(fixture(i,at.isoformat().replace("+00:00","Z"),
                            (i%3)+1,i%2))
    for offset,stamp in enumerate((
        "2025-07-12T12:00:00Z","2025-09-12T12:00:00Z",
        "2025-10-12T12:00:00Z","2025-12-12T12:00:00Z",
        "2026-01-12T12:00:00Z","2026-03-12T12:00:00Z",
        "2026-04-12T12:00:00Z","2026-06-12T12:00:00Z",
    ),32):
        rows.append(fixture(offset,stamp,offset%4,offset%2))
    return rows


class Step13RetrospectiveContract(unittest.TestCase):
    def run_research(self,records=None):
        return retrospective_research(
            examples() if records is None else records,policy=POLICY)

    def test_four_folds_matched_and_test_untouched(self):
        r=self.run_research()
        self.assertEqual([f["validation_count"] for f in r["folds"]],[2,2,2,2])
        self.assertEqual(r["test_rows_processed"],0)
        self.assertEqual(r["validation_partition_rows"],8)
        self.assertFalse(r["actual_historical_prematch_receipts_certified"])
        self.assertFalse(r["original_provider_publication_at_matchtime_known"])
        self.assertFalse(r["historical_pit_backtest_performed"])
        self.assertFalse(r["model_production_eligible"])
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["gate13_pass"])
        for f in r["folds"]:
            methods=f["methods"]
            self.assertEqual(methods["EXPANDING"]["validation_fixture_ids_sha256"],
                             methods["ROLLING_24_CALENDAR_MONTHS"]["validation_fixture_ids_sha256"])
            self.assertTrue(all(x["metrics"]["n"]==f["validation_count"]
                                for x in methods.values()))

    def test_rolling_excludes_2023_events_for_elo_and_fitting(self):
        r=self.run_research()
        fold2=r["folds"][1]["methods"]
        self.assertGreater(fold2["EXPANDING"]["training_rows"],
                           fold2["ROLLING_24_CALENDAR_MONTHS"]["training_rows"])
        self.assertNotEqual(
            fold2["EXPANDING"]["fitted_parameters"]["base_home_goals"],
            fold2["ROLLING_24_CALENDAR_MONTHS"]["fitted_parameters"]["base_home_goals"])

    def test_earlier_validation_result_changes_later_fold_but_not_same_fold_predictions(self):
        rows=examples()
        original=self.run_research(rows)
        other=deepcopy(rows)
        other[32]["goals_home_90"]=27
        other[32]["goals_away_90"]=0
        changed=self.run_research(other)
        # Within fold1, both predictions and parameters freeze before labels.
        self.assertEqual(original["folds"][0]["methods"]["EXPANDING"]["fitted_parameters"],
                         changed["folds"][0]["methods"]["EXPANDING"]["fitted_parameters"])
        self.assertNotEqual(
            original["folds"][0]["methods"]["EXPANDING"]["metrics"]["multiclass_logloss"],
            changed["folds"][0]["methods"]["EXPANDING"]["metrics"]["multiclass_logloss"])
        self.assertNotEqual(
            original["folds"][1]["methods"]["EXPANDING"]["fitted_parameters"],
            changed["folds"][1]["methods"]["EXPANDING"]["fitted_parameters"])

    def test_output_is_aggregate_no_frozen_fixture_predictions(self):
        r=self.run_research()
        self.assertNotIn("match_predictions",r)
        for fold in r["folds"]:
            self.assertNotIn("scores",fold)
            self.assertNotIn("prediction_rows",fold)
            for m in fold["methods"].values():
                self.assertTrue(m["parameters_frozen_before_validation"])
                self.assertFalse(m["validation_labels_used_for_fitting"])
                self.assertEqual(sum(v["n"] for v in m["metrics"]["calibration_bins"]),
                                 fold["validation_count"])

    def test_reproducible_math_and_valid_metrics(self):
        a=self.run_research()
        self.assertEqual(a,self.run_research())
        for v in a["overall"].values():
            self.assertEqual(v["validation_n"],8)
            self.assertGreater(v["multiclass_logloss_fold_weighted"],0)
            self.assertGreater(v["multiclass_brier_sum3_fold_weighted"],0)
            self.assertTrue(0<=v["top_class_ece_5bin_fold_weighted"]<=1)

    def test_test_partition_rejected_even_if_results_look_good(self):
        rows=examples()
        rows.append(fixture(99,"2026-10-05T12:00:00Z",2,0))
        with self.assertRaisesRegex(BaselineSafetyError,"TEST_AND_OUT"):
            self.run_research(rows)

    def test_unknown_sources_odds_and_extra_columns_rejected(self):
        rows=examples()
        rows[0]["odds"]=1.8
        with self.assertRaisesRegex(BaselineSafetyError,"SCHEMA_OR_ODDS"):
            self.run_research(rows)

    def test_policy_must_be_explicit(self):
        with self.assertRaisesRegex(BaselineSafetyError,"EXPLICIT_POLICY"):
            retrospective_research(examples(),policy="PIT_BACKTEST")

    def test_duplicate_native_id_rejected(self):
        rows=examples()
        rows[1]["fixture_id"]=rows[0]["fixture_id"]
        with self.assertRaisesRegex(BaselineSafetyError,"IDS_INVALID"):
            self.run_research(rows)

    def test_malformed_goals_and_naive_time_rejected(self):
        for x in (True,-1,5.5,None):
            rows=examples()
            rows[2]["goals_home_90"]=x
            with self.assertRaisesRegex(BaselineSafetyError,"GOALS_INVALID"):
                self.run_research(rows)
        rows=examples()
        rows[0]["kickoff_utc"]="2023-08-02T12:00:00"
        with self.assertRaisesRegex(ValueError,"NAIVE_TIMESTAMP"):
            self.run_research(rows)


if __name__=="__main__":
    unittest.main()
