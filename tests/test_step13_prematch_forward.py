"""Step13 pre-kickoff source gates with synthetic schedules and NO TEST scores."""
import copy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from src.kb3_step13_baseline import BaselineParameters,BaselineSafetyError
from src.kb3_split import timestamp,sha
from scripts.step13_prematch_forward_once import (
    build_first_snapshot,train_only,OUTPUT_SCHEMA,REFERENCE_TRAIN_FIT,MIN_LEAD_HOURS
)

SAFE=Path(__file__).resolve().parents[1]/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
START="2026-10-27T06:00:00Z"
DONE="2026-10-27T06:01:00Z"


def synthetic_source():
    safe=json.loads(SAFE.read_text())
    fixtures=[x for x in safe["fixtures"] if x["partition"]=="TEST"
              and timestamp(x["kickoff_utc"])>timestamp("2026-10-31T00:00:00Z")
              and timestamp(x["kickoff_utc"])<timestamp("2026-11-03T23:59:59Z")]
    if len(fixtures)!=10:
        raise AssertionError("STEP13_SYNTHETIC_FROZEN_TEN_FIXTURES_CHANGED")
    rows=[]
    for i,f in enumerate(fixtures):
        h=i%20
        a=(i+8)%20
        rows.append({
            "id":f["fixture_id"],"time_utc":f["kickoff_utc"],
            "status":"not_started",
            "score_home":None,"score_away":None,
            "home_team":{"id":f"t_{h:06d}","name":f"SYN-TEAM-{h}"},
            "away_team":{"id":f"t_{a:06d}","name":f"SYN-TEAM-{a}"},
        })
    return safe,{"matches":rows}


def mock_train_only(seasons,safe):
    p=BaselineParameters(**REFERENCE_TRAIN_FIT)
    return p,{},{"2023/2024":"SYN_ONLY","2024/2025":"SYN_ONLY"},"SYN_DATA_ONLY"


class ForwardPrematchTests(TestCase):
    def test_frozen_ten_predictions_no_test_labels_or_odds(self):
        safe,upcoming=synthetic_source()
        with patch("scripts.step13_prematch_forward_once.train_only",mock_train_only):
            result=build_first_snapshot(train_seasons={},upcoming_payload=upcoming,
                             safe=safe,observed_at=START,completed_at=DONE)
        self.assertEqual(result["schema"],OUTPUT_SCHEMA)
        self.assertEqual(result["train_rows_admitted"],760)
        self.assertEqual(result["validation_rows_admitted"],0)
        self.assertEqual(result["test_results_accessed"],0)
        self.assertEqual(result["test_future_fixture_metadata_used"],10)
        self.assertEqual(len(result["forecasts"]),10)
        self.assertTrue(all(row["scores_at_source"]=={"home":None,"away":None}
                            for row in result["forecasts"]))
        self.assertTrue(all(abs(sum(row["probabilities_1x2"].values())-1)<1e-12
                            for row in result["forecasts"]))
        self.assertEqual(result["report_sha256"],
                         sha({k:v for k,v in result.items() if k!="report_sha256"}))
        self.assertFalse(result["training_allowed"])
        self.assertFalse(result["gate13_pass"])
        self.assertFalse(result["step14_started"])
        self.assertFalse(result["no_model_champion_selected"] is False)

    def test_error_if_provider_returns_result_or_finished(self):
        safe,upcoming=synthetic_source()
        upcoming["matches"][0]["score_home"]=3
        with patch("scripts.step13_prematch_forward_once.train_only",mock_train_only):
            with self.assertRaisesRegex((BaselineSafetyError,ValueError),
                                         "FINISHED_WITHOUT_FINAL_SCORE|FUTURE_CONTAINS_FINAL_SCORE|UPCOMING_HAS_RESULT"):
                build_first_snapshot(train_seasons={},upcoming_payload=upcoming,safe=safe,
                                     observed_at=START,completed_at=DONE)

    def test_original_frozen_test_date_changed_is_rejected(self):
        safe,upcoming=synthetic_source()
        upcoming["matches"][0]["time_utc"]="2026-10-31T13:30:00Z"
        with patch("scripts.step13_prematch_forward_once.train_only",mock_train_only):
            with self.assertRaisesRegex(BaselineSafetyError,"KICKOFF_DRIFT"):
                build_first_snapshot(train_seasons={},upcoming_payload=upcoming,safe=safe,
                                     observed_at=START,completed_at=DONE)

    def test_kickoff_not_after_48h_refused(self):
        safe,upcoming=synthetic_source()
        with patch("scripts.step13_prematch_forward_once.train_only",mock_train_only):
            with self.assertRaisesRegex(BaselineSafetyError,"TARGET_COUNT"):
                build_first_snapshot(train_seasons={},upcoming_payload=upcoming,safe=safe,
                                     observed_at="2026-11-01T21:00:00Z",
                                     completed_at="2026-11-01T21:01:00Z")

    def test_late_freeze_refused(self):
        safe,upcoming=synthetic_source()
        with patch("scripts.step13_prematch_forward_once.train_only",mock_train_only):
            with self.assertRaisesRegex(BaselineSafetyError,"TARGET_COUNT"):
                build_first_snapshot(train_seasons={},upcoming_payload=upcoming,safe=safe,
                                     observed_at="2026-11-03T20:00:00Z",
                                     completed_at="2026-11-03T20:01:00Z")

    def test_train_refuses_any_validation_season(self):
        safe,_=synthetic_source()
        with self.assertRaisesRegex(BaselineSafetyError,"SEASONS_EXACT_ONLY"):
            train_only({"2025/2026":{"matches":[]}},safe)

    def test_train_refuses_modified_partition_or_promotion(self):
        safe,_=synthetic_source()
        safe["training_allowed"]=True
        with self.assertRaisesRegex(BaselineSafetyError,"FROZEN_SPLIT"):
            train_only({"2023/2024":{},"2024/2025":{}},safe)

    def test_upcoming_provider_cannot_contain_test_result_for_another_game(self):
        safe,upcoming=synthetic_source()
        upcoming["matches"].append({
            "id":"m_ZZzz99","time_utc":"2026-11-25T15:00:00Z",
            "status":"finished","score_home":2,"score_away":1,
            "home_team":{"id":"t_001100","name":"SYN-A"},
            "away_team":{"id":"t_001200","name":"SYN-B"}})
        with patch("scripts.step13_prematch_forward_once.train_only",mock_train_only):
            with self.assertRaisesRegex(BaselineSafetyError,"UPCOMING_HAS_RESULT"):
                build_first_snapshot(train_seasons={},upcoming_payload=upcoming,safe=safe,
                                     observed_at=START,completed_at=DONE)

if __name__=="__main__":
    import unittest
    unittest.main()
