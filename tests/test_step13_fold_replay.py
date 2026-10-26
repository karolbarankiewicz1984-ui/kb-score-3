"""Step13 v0.2 safety regression: frozen folds, 48h label embargo and source policy.

ALL match data below are invented tests; never claim real match performance.
"""
import copy
import json
from pathlib import Path
import unittest

from src.kb3_split import sha
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_fold_replay import (
    replay_synthetic_fold, real_schedule_probe,
)

ROOT=Path(__file__).resolve().parents[1]
START="2025-10-01T00:00:00Z"
STOP="2026-01-01T00:00:00Z"


def fixture(mid,ko,h,a,part="TRAIN"):
    return {"fixture_id":mid,"kickoff_utc":ko,"home_team_id":h,
            "away_team_id":a,"partition":part,"origin":"SYNTHETIC_TEST"}


def result(mid,h,a,receipt):
    return {"fixture_id":mid,"home_goals_90":h,"away_goals_90":a,
            "actual_receipt_at_utc":receipt,"origin":"SYNTHETIC_TEST"}


def example():
    fixtures=[
        fixture("old","2023-08-10T12:00:00Z","A","B"),
        fixture("more","2024-04-01T12:00:00Z","A","B"),
        fixture("new","2024-10-05T12:00:00Z","B","C"),
        fixture("last","2025-09-24T12:00:00Z","A","C"),
        fixture("late","2025-09-30T12:00:00Z","B","C"),
        fixture("t1","2025-10-03T18:00:00Z","A","B","VALIDATION"),
        fixture("t2","2025-10-10T18:00:00Z","A","C","VALIDATION"),
    ]
    results=[
        result("old",3,0,"2023-08-11T18:00:00Z"),
        result("more",1,0,"2024-04-02T18:00:00Z"),
        result("new",0,1,"2024-10-06T18:00:00Z"),
        result("last",2,1,"2025-09-25T18:00:00Z"),
        result("late",0,1,"2025-09-30T18:00:00Z"),
        result("t1",2,0,"2025-10-04T18:00:00Z"),
        result("t2",0,1,"2025-10-11T18:00:00Z"),
    ]
    return fixtures,results


def run(fixtures=None,results=None,strategy="EXPANDING",**kw):
    f,r=example()
    return replay_synthetic_fold(
        f if fixtures is None else fixtures,
        r if results is None else results,
        validation_from_utc=START,validation_to_utc=STOP,
        history_from_utc=("2023-10-01T00:00:00Z"
                          if strategy=="ROLLING_24_CALENDAR_MONTHS"
                          else "2023-07-01T00:00:00Z"),
        strategy=strategy,**kw)


class Step13FoldReplayTests(unittest.TestCase):
    def test_expanding_and_rolling_same_validation_set(self):
        e=run()
        r=run(strategy="ROLLING_24_CALENDAR_MONTHS")
        self.assertEqual([x["fixture_id"] for x in e["frozen_forecasts"]],
                         [x["fixture_id"] for x in r["frozen_forecasts"]])
        self.assertEqual(e["history_schedule_candidates"],5)
        self.assertEqual(r["history_schedule_candidates"],4)
        self.assertEqual(e["eligible_synthetic_history"],4)
        self.assertEqual(r["eligible_synthetic_history"],3)
        self.assertEqual(e["excluded_history_reasons"],
                         {"event_time_48h_embargo":1})
        self.assertEqual(e["validation_schedule_count"],2)
        self.assertTrue(e["validation_coverage_complete"])
        self.assertTrue(r["validation_coverage_complete"])

    def test_elo_history_order_and_distinct_strategies(self):
        e,r=run(),run(strategy="ROLLING_24_CALENDAR_MONTHS")
        self.assertNotEqual(e["frozen_forecasts"][0]["p_1x2"],
                            r["frozen_forecasts"][0]["p_1x2"])
        self.assertEqual(e["eligible_synthetic_history_ids"],
                         ["old","more","new","last"])
        self.assertEqual(r["eligible_synthetic_history_ids"],
                         ["more","new","last"])

    def test_validation_label_never_affects_prematch_probability(self):
        fixtures,results=example()
        a=run(fixtures,results)
        other=copy.deepcopy(results)
        for item in other:
            if item["fixture_id"]=="t1":
                item["home_goals_90"],item["away_goals_90"]=0,7
        b=run(fixtures,other)
        self.assertEqual(a["frozen_forecasts"],b["frozen_forecasts"])
        self.assertNotEqual(a["reference_metrics_if_complete"]["multiclass_log_loss"],
                            b["reference_metrics_if_complete"]["multiclass_log_loss"])

    def test_later_validation_result_cannot_leak_into_next_match_same_fold(self):
        fixtures,results=example()
        baseline=run(fixtures,results)["frozen_forecasts"]
        changed=copy.deepcopy(results)
        for row in changed:
            if row["fixture_id"]=="t1":
                row["home_goals_90"]=15
        self.assertEqual(baseline,run(fixtures,changed)["frozen_forecasts"])

    def test_result_received_after_fold_boundary_not_used(self):
        fixtures,results=example()
        for x in results:
            if x["fixture_id"]=="more":
                x["actual_receipt_at_utc"]="2026-02-01T00:00:00Z"
        r=run(fixtures,results)
        self.assertEqual(r["eligible_synthetic_history"],3)
        self.assertEqual(r["excluded_history_reasons"],
                         {"event_time_48h_embargo":1,
                          "result_received_after_fold_freeze":1})

    def test_missing_result_cannot_be_assumed(self):
        fixtures,results=example()
        r=run(fixtures,[x for x in results if x["fixture_id"]!="new"])
        self.assertEqual(r["excluded_history_reasons"],
                         {"event_time_48h_embargo":1,"no_result":1})

    def test_missing_one_validation_label_blocks_all_metrics(self):
        fixtures,results=example()
        r=run(fixtures,[x for x in results if x["fixture_id"]!="t2"])
        self.assertIsNone(r["reference_metrics_if_complete"])
        self.assertFalse(r["validation_coverage_complete"])
        self.assertEqual(r["synthetic_validation_results_count"],1)

    def test_reference_metrics_not_historical_even_if_full(self):
        x=run()
        m=x["reference_metrics_if_complete"]
        self.assertEqual(m["reference_type"],"SYNTHETIC_ONLY_NOT_HISTORICAL")
        self.assertEqual(m["sample_size"],2)
        self.assertFalse(x["historical_metrics_available"])
        self.assertFalse(x["historical_pit_certified"])
        self.assertFalse(x["training_allowed"])
        self.assertFalse(x["gate13_pass"])
        for row in x["frozen_forecasts"]:
            self.assertAlmostEqual(sum(row["p_1x2"].values()),1,places=12)

    def test_no_test_or_unknown_outcome_in_ledger(self):
        f,r=example()
        f[0]["partition"]="TEST"
        with self.assertRaisesRegex(BaselineSafetyError,"UNTRUSTED_OR_TEST_FIXTURE"):
            run(f,r)
        f,r=example()
        r.append(result("test_holdout",1,0,"2025-10-03T20:00:00Z"))
        with self.assertRaisesRegex(BaselineSafetyError,"UNKNOWN_OR_DUPLICATE_RESULT"):
            run(f,r)

    def test_reject_future_result_receipt_before_completion(self):
        f,r=example()
        r[0]["actual_receipt_at_utc"]="2023-08-10T12:00:00Z"
        with self.assertRaisesRegex(BaselineSafetyError,"BEFORE_COMPLETION"):
            run(f,r)

    def test_wrong_source_marked_real_refused(self):
        f,r=example()
        f[0]["origin"]="RETROSPECTIVE_PITCHAPI"
        with self.assertRaisesRegex(BaselineSafetyError,"UNTRUSTED_OR_TEST_FIXTURE"):
            run(f,r)
        f,r=example()
        r[0]["origin"]="VERIFIED_PREMATCH"
        with self.assertRaisesRegex(BaselineSafetyError,"NOT_SYNTHETIC"):
            run(f,r)

    def test_no_odds_or_future_field_in_schema(self):
        f,r=example()
        f[0]["bookmaker_odds"]=1.6
        with self.assertRaisesRegex(BaselineSafetyError,"FIXTURE_SCHEMA"):
            run(f,r)
        f,r=example()
        r[0]["label_90m"]="H"
        with self.assertRaisesRegex(BaselineSafetyError,"RESULT_SCHEMA"):
            run(f,r)

    def test_duplicate_match_or_label_blocked(self):
        f,r=example()
        f.append(copy.deepcopy(f[0]))
        with self.assertRaisesRegex(BaselineSafetyError,"DUPLICATE"):
            run(f,r)
        f,r=example()
        r.append(copy.deepcopy(r[0]))
        with self.assertRaisesRegex(BaselineSafetyError,"DUPLICATE_RESULT"):
            run(f,r)

    def test_invalid_result_and_metadata_rejected(self):
        f,r=example()
        r[0]["home_goals_90"]=True
        with self.assertRaisesRegex(BaselineSafetyError,"INVALID_SCORE"):
            run(f,r)
        f,r=example()
        f[0]["away_team_id"]="A"
        with self.assertRaisesRegex(BaselineSafetyError,"UNTRUSTED"):
            run(f,r)
        f,r=example()
        f[5]["partition"]="TRAIN"
        with self.assertRaisesRegex(BaselineSafetyError,"TARGET_NOT_VALIDATION"):
            run(f,r)

    def test_rolling_wrong_lower_bound_rejected(self):
        f,r=example()
        with self.assertRaisesRegex(BaselineSafetyError,"NOT_24_CALENDAR_MONTHS"):
            replay_synthetic_fold(
                f,r,validation_from_utc=START,validation_to_utc=STOP,
                history_from_utc="2023-09-01T00:00:00Z",
                strategy="ROLLING_24_CALENDAR_MONTHS")

    def test_deterministic_fold_replay(self):
        self.assertEqual(run(),run())
        self.assertEqual(run(strategy="ROLLING_24_CALENDAR_MONTHS"),
                         run(strategy="ROLLING_24_CALENDAR_MONTHS"))


class RealScheduleOnlyReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]
        cls.view=json.loads((root/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
        cls.plan=json.loads((root/"data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json").read_text())

    def test_pinned_real_1520_readiness_has_zero_fitting(self):
        x=real_schedule_probe(self.view,self.plan)
        self.assertEqual(x["real_fixture_count"],1520)
        self.assertEqual([f["validation_candidates"] for f in x["fold_counts"]],
                         [60,126,123,71])
        self.assertEqual([f["rolling_24month_candidates"] for f in x["fold_counts"]],
                         [760,753,750,776])
        self.assertFalse(x["historical_labels_read"])
        self.assertFalse(x["historical_predictions_made"])
        self.assertFalse(x["real_training_performed"])
        self.assertFalse(x["real_backtest_performed"])
        self.assertFalse(x["real_metrics_available"])
        self.assertFalse(x["gate13_pass"])

    def test_cannot_swap_source_even_after_rehash(self):
        bad=copy.deepcopy(self.view)
        bad["fixtures"][0]["kickoff_utc"]="2030-01-01T00:00:00Z"
        bad["projection_sha256"]=sha({k:v for k,v in bad.items()
                                        if k!="projection_sha256"})
        with self.assertRaisesRegex(ValueError,"ACCEPTANCE_VIEW_VERSION_CHANGED"):
            real_schedule_probe(bad,self.plan)


if __name__=="__main__":
    unittest.main()
