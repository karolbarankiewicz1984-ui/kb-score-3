"""No-false-PIT safeguards for NED/POL source pilot and native schedule watchdog."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from scripts.kb3_secondary_source_pilot import strict_match, MAX_SAMPLES
from scripts.kb3_step16_schedule_watchdog import choose

class SecondaryYellowPilotTests(unittest.TestCase):
    def setUp(self):
        self.p={"scope":"NED","season":"2025/2026",
                "pitchapi_match_id":"1234",
                "kickoff_utc":"2026-01-04T13:00:00Z",
                "home_team_id":"17","away_team_id":"18",
                "fulltime_home_goals":2,"fulltime_away_goals":1}
        self.s={"source_name":"LICENSED_SECONDARY",
                "source_uri":"https://example.org/match/444",
                "secondary_match_id":"444","home_team_name":"Club A",
                "away_team_name":"Club B","scope":"NED","season":"2025/2026",
                "kickoff_utc":"2026-01-04T13:00:00Z",
                "fulltime_home_goals":2,"fulltime_away_goals":1,
                "yellow_home":3,"yellow_away":1,
                "yellow_semantics":"FULLTIME_YELLOW_EVENTS_INCLUDING_SECOND_YELLOW",
                "license_reviewed_for_intended_use":True}
        self.x={
            ("NED","2025/2026","LICENSED_SECONDARY","Club A"):
                {"verified":True,"original_pitchapi_team_id":"17","evidence_uri":"https://example.org/a"},
            ("NED","2025/2026","LICENSED_SECONDARY","Club B"):
                {"verified":True,"original_pitchapi_team_id":"18","evidence_uri":"https://example.org/b"}
        }

    def test_only_truly_independent_source_and_team_crosswalk_accepted(self):
        self.assertEqual(strict_match(self.p,self.s,self.x),
            "MATCHED_RESEARCH_ONLY_NOT_ORIGINAL_HISTORICAL_PIT")

    def test_reject_missing_license_review(self):
        d={**self.s,"license_reviewed_for_intended_use":False}
        self.assertEqual(strict_match(self.p,d,self.x),
                         "REJECT_SOURCE_RIGHTS_NOT_REVIEWED")

    def test_reject_swapped_or_missing_club_mapping(self):
        self.assertEqual(strict_match(self.p,self.s,{}),
                         "REJECT_UNVERIFIED_TEAM_CROSSWALK")
        d={**self.x,("NED","2025/2026","LICENSED_SECONDARY","Club A"):
            {"verified":True,"original_pitchapi_team_id":"18",
             "evidence_uri":"https://example.org/a"}}
        self.assertEqual(strict_match(self.p,self.s,d),
                         "REJECT_UNVERIFIED_TEAM_CROSSWALK")

    def test_reject_score_and_kickoff(self):
        self.assertEqual(strict_match(self.p,{**self.s,"fulltime_home_goals":3},self.x),
                         "REJECT_SCORE_MISMATCH")
        self.assertEqual(strict_match(self.p,{**self.s,"kickoff_utc":"2026-01-04T17:00:00Z"},self.x),
                         "REJECT_KICKOFF_CLOCK")

    def test_reject_ambiguous_yellow_definition_and_null(self):
        self.assertEqual(strict_match(self.p,{**self.s,"yellow_semantics":"UNKNOWN"},self.x),
                         "REJECT_YELLOW_SEMANTICS_UNCERTAIN")
        self.assertEqual(strict_match(self.p,{**self.s,"yellow_home":None},self.x),
                         "REJECT_INVALID_YELLOW")

    def test_max_pilot_is_30(self):
        self.assertEqual(MAX_SAMPLES,30)

class M0WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,5,15,40,tzinfo=timezone.utc)

    @patch("scripts.kb3_step16_schedule_watchdog.select")
    def test_passes_native_guard_only(self,mock_select):
        mock_select.return_value=("settle","SETTLEMENT_DUE")
        v=choose("settle",self.now,root="/tmp/unrelated")
        self.assertTrue(v["will_dispatch_existing_native_workflow"])
        self.assertEqual(v["mode"],"settle")
        self.assertFalse(v["sports_api_called"])
        self.assertFalse(v["source_data_changed"])
        self.assertTrue(v["no_new_key"])
        self.assertEqual(mock_select.call_args.kwargs["event"],"schedule")

    @patch("scripts.kb3_step16_schedule_watchdog.select")
    def test_skip_when_recent(self,mock_select):
        mock_select.return_value=("skip","SETTLEMENT_ALREADY_RECENT")
        v=choose("settle",self.now)
        self.assertFalse(v["will_dispatch_existing_native_workflow"])

    @patch("scripts.kb3_step16_schedule_watchdog.select")
    def test_forecast_uses_native_due_check(self,mock_select):
        mock_select.return_value=("forecast","MISSING_DAILY_FORECAST")
        v=choose("forecast",self.now)
        self.assertTrue(v["will_dispatch_existing_native_workflow"])
        self.assertIn("21 6,9,12",mock_select.call_args.kwargs["cron"])

    def test_other_modes_rejected(self):
        with self.assertRaises(ValueError):choose("force_settle",self.now)

if __name__=="__main__":
    unittest.main()
