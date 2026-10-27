"""All second-cohort provider data here are invented upcoming-only fixtures."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from src.kb3_split import timestamp
from src.kb3_step13_baseline import BaselineSafetyError,BaselineParameters
from src.kb3_step13_forward_score import SOURCE_FILE
from scripts.step13_second_prematch_once import next_10,SCHEMA,FIRST_TRAIN_SHA

SAFE=Path("data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json")
CLOCK="2026-10-27T08:00:00Z"
LOCK="2026-10-27T08:00:01Z"

def fixture_data():
    safe=json.loads(SAFE.read_text(encoding="utf8"))
    first=json.loads(Path(SOURCE_FILE).read_text(encoding="utf8"))
    target=[f for f in safe["fixtures"] if f["partition"]=="TEST" and
       "2026-11-06T00:00:00Z"<=f["kickoff_utc"]<"2026-11-09T00:00:00Z"]
    assert len(target)==10
    games=[]
    for i,x in enumerate(target):
        h=i%20;a=(i+8)%20
        games.append({"id":x["fixture_id"],"time_utc":x["kickoff_utc"],
            "status":"not_started","score_home":None,"score_away":None,
            "home_team":{"id":f"t_{h:06d}","name":f"SYN-TEAM-{h}"},
            "away_team":{"id":f"t_{a:06d}","name":f"SYN-TEAM-{a}"}})
    return safe,first,{"matches":games}

def fake_train(seasons,safe):
    first=json.loads(Path(SOURCE_FILE).read_text())
    return (BaselineParameters(**first["fit_parameters"]),{},
            {"2023/2024":"SYN","2024/2025":"SYN"},FIRST_TRAIN_SHA)

def build(safe,first,games,at=CLOCK,freeze=LOCK):
    with patch("scripts.step13_second_prematch_once.train_only",fake_train):
        return next_10(train_seasons={},upcoming_payload=games,safe=safe,
            first_snapshot=first,observed_at=at,frozen_at=freeze)

class SecondPrematchSafety(unittest.TestCase):
    def test_ten_fresh_upcoming_only_predictions(self):
        safe,first,games=fixture_data()
        r=build(safe,first,games)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["cohort_target_count"],10)
        self.assertEqual(r["TEST_results_read"],0)
        self.assertEqual(r["VALIDATION_results_read"],0)
        self.assertEqual(r["previous_cohort_overlap_count"],0)
        self.assertFalse(r["gate13_pass"])
        self.assertTrue(all(x["scores_at_source"]=={"home":None,"away":None} for x in r["forecasts"]))
    def test_old_first_forecast_change_rejected(self):
        safe,first,games=fixture_data()
        first["forecasts"][0]["probabilities_1x2"]["1"]+=.01
        with self.assertRaisesRegex(BaselineSafetyError,"ORIGINAL_FORECAST_CHANGED"):
            build(safe,first,games)
    def test_slight_schedule_drift_rejected(self):
        safe,first,games=fixture_data()
        games["matches"][0]["time_utc"]="2026-11-06T21:00:00Z"
        with self.assertRaisesRegex(BaselineSafetyError,"KICKOFF_CHANGED"):
            build(safe,first,games)
    def test_finished_game_anywhere_in_upcoming_denied(self):
        safe,first,games=fixture_data()
        games["matches"][4]["status"]="finished"
        games["matches"][4]["score_home"]=1
        games["matches"][4]["score_away"]=0
        with self.assertRaisesRegex((BaselineSafetyError,ValueError),"UPCOMING_CONTAINS_TEST_LABEL|FINISHED"):
            build(safe,first,games)
    def test_missing_match_denied(self):
        safe,first,games=fixture_data()
        games["matches"].pop()
        with self.assertRaisesRegex(BaselineSafetyError,"MISSING_FIXED_TARGET"):
            build(safe,first,games)
    def test_pre_kickoff_immutable(self):
        safe,first,games=fixture_data()
        with self.assertRaisesRegex(BaselineSafetyError,"FREEZE_NOT_BEFORE_COHORT"):
            build(safe,first,games,at="2026-11-06T23:00:00Z",
                  freeze="2026-11-06T23:00:01Z")
    def test_fitting_or_train_input_changed_denied(self):
        safe,first,games=fixture_data()
        def bad_train(*args):
            p,r,h,input_hash=fake_train(*args)
            return p,r,h,"unapproved-source-hash"
        with patch("scripts.step13_second_prematch_once.train_only",bad_train):
            with self.assertRaisesRegex(BaselineSafetyError,"TRAIN_OR_PARAMETER_DRIFT"):
                next_10(train_seasons={},upcoming_payload=games,safe=safe,
                  first_snapshot=first,observed_at=CLOCK,frozen_at=LOCK)
if __name__=="__main__":unittest.main()
