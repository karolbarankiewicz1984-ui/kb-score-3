"""Offline tests for PitchAPI-native chronology and correction detection."""
from __future__ import annotations
import copy
import unittest

from src.kb3_pitch_native_drift import compare_records

def season():
    arr=[]
    for i in range(380):
        finished=i<80
        arr.append({"id":f"m_{i:06d}",
          "time_utc":"2026-08-01T15:00:00Z" if finished else "2027-05-01T15:00:00Z",
          "status":"finished" if finished else "not_started",
          "home_team":{"id":f"t_{2*i:06d}","name":f"Home {i}"},
          "away_team":{"id":f"t_{2*i+1:06d}","name":f"Away {i}"},
          "score_home":1 if finished else None,
          "score_away":0 if finished else None})
    return arr

class NativeDriftTests(unittest.TestCase):
    def setUp(self):
        self.old=season()
        self.new=copy.deepcopy(self.old)

    def diff(self):
        return compare_records(self.old,self.new)

    def test_no_change(self):
        v=self.diff()
        self.assertEqual(v["match_count"],380)
        self.assertEqual(v["changed_raw_match_payloads"],0)
        self.assertEqual(v["changed_kickoffs"],0)
        self.assertEqual(v["changed_scores"],0)
        self.assertEqual(v["status_transitions"],[])
        self.assertFalse(v["training_allowed"])

    def test_rescheduled_fixture_preserves_native_id(self):
        self.new[99]["time_utc"]="2027-05-09T15:00:00Z"
        v=self.diff()
        self.assertEqual(v["changed_kickoffs"],1)
        self.assertEqual(v["changed_raw_match_payloads"],1)
        self.assertEqual(v["changed_statuses"],0)

    def test_result_correction_is_detected(self):
        self.new[0]["score_home"]=2
        self.assertEqual(self.diff()["changed_scores"],1)

    def test_newly_finished_match_is_detected(self):
        self.new[99]["status"]="finished"
        self.new[99]["score_home"]=0
        self.new[99]["score_away"]=2
        v=self.diff()
        self.assertEqual(v["changed_statuses"],1)
        self.assertEqual(v["changed_scores"],1)
        self.assertEqual(v["status_transitions"],
            [{"from":"not_started","to":"finished","count":1}])

    def test_team_display_name_change_is_separate_from_id(self):
        self.new[0]["home_team"]["name"]="Home 0 New"
        v=self.diff()
        self.assertEqual(v["changed_team_display_names"],1)
        self.assertEqual(v["changed_raw_match_payloads"],1)

    def test_team_identity_collision_quarantined(self):
        self.new[0]["away_team"]["id"]="t_888888"
        with self.assertRaisesRegex(ValueError,"TEAM_ID_CHANGED"):
            self.diff()

    def test_missing_match_rejected_even_if_count_kept(self):
        self.new[5]["id"]="m_888888"
        with self.assertRaisesRegex(ValueError,"FIXTURE_SET_CHANGED"):
            self.diff()

    def test_duplicate_match_id_rejected(self):
        self.new[6]["id"]=self.new[5]["id"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            self.diff()

    def test_incomplete_season_rejected(self):
        self.new.pop()
        with self.assertRaisesRegex(ValueError,"SEASON_INCOMPLETE"):
            self.diff()

    def test_no_zero_fill_when_missing_score(self):
        self.new[0]["score_home"]=None
        with self.assertRaisesRegex(ValueError,"FINISHED_WITHOUT_FINAL_SCORE"):
            self.diff()

    def test_input_order_does_not_affect_comparison(self):
        self.new=list(reversed(self.new))
        self.assertEqual(self.diff()["changed_raw_match_payloads"],0)

    def test_full_payload_revision_is_observed(self):
        self.new[0]["provider_extra_status"]="new"
        v=self.diff()
        self.assertEqual(v["changed_raw_match_payloads"],1)
        self.assertEqual(v["changed_statuses"],0)

if __name__=="__main__":
    unittest.main()
