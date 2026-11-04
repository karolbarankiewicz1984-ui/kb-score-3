"""Single-source shadow feature computation, never certified historical PIT."""
from datetime import datetime,timezone,timedelta
import unittest
from pitch_pair_fixtures import stats
from src.kb3_pitch_native_features import native_shadow_features
from src.kb3_features import FeatureSafetyError,digest


def matches():
    matches=[]
    for i in range(380):
        finished=i<2
        home="t_000001" if i<3 else f"t_{i*2+10:06d}"
        away="t_000002" if i<3 else f"t_{i*2+11:06d}"
        matches.append({
          "id":f"m_{i:06d}",
          "time_utc":("2026-09-01T16:00:00Z" if i==0 else
                      "2026-10-01T16:00:00Z" if i==1 else
                      "2027-04-01T16:00:00Z"),
          "status":"finished" if finished else "not_started",
          "home_team":{"id":home,"name":"Club A" if i<3 else f"Team {i} H"},
          "away_team":{"id":away,"name":"Club B" if i<3 else f"Team {i} A"},
          "score_home":2 if finished else None,
          "score_away":1 if finished else None})
    return matches

def shot(mid="m_000000"):
    return {"match_id":mid,
      "observed_at_utc":"2026-10-26T08:00:00Z",
      "stats_response":stats(mid,"t_000001","t_000002",.7,.4),
      "shots_response":{"data":{"match_id":mid,
             "periods":[{"period":"All","shots":[
                  {"id":"s_1","team_id":"t_000001","expected_goals":0.7},
                  {"id":"s_2","team_id":"t_000002","expected_goals":0.4}]}]}}}

class OneSourceEloTests(unittest.TestCase):
    def setUp(self):
        self.matches=matches()
        self.kw={
            "season":"2026/2027",
            "source_observed_at_utc":"2026-10-26T09:00:00Z",
            "cutoff_utc":"2026-10-26T10:00:00Z"}

    def build(self,**kw):
        return native_shadow_features(self.matches,"m_000002",**dict(self.kw,**kw))

    def test_one_native_id_shots_and_results(self):
        v=self.build(shot_observations=[shot()])
        self.assertEqual(v["accepted_predecessor_count"],2)
        self.assertEqual(v["features"]["home_all_5_xg_n"],1)
        self.assertEqual(v["features"]["home_all_5_xg_avg"],0.7)
        self.assertEqual(v["features"]["away_all_5_xg_avg"],0.4)
        self.assertEqual(v["mode"],"shadow_native")
        self.assertTrue(v["source_evidence"]["single_provider_identity"])
        self.assertFalse(v["training_allowed"])
        self.assertFalse(v["target_prematch_snapshot_certified"])

    def test_missing_xg_is_null_not_zero(self):
        v=self.build()
        self.assertEqual(v["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(v["features"]["home_all_5_xg_avg"])

    def test_shots_captured_after_cutoff_do_not_enter(self):
        x=shot()
        x["observed_at_utc"]="2026-10-26T11:00:00Z"
        v=self.build(shot_observations=[x])
        self.assertEqual(v["features"]["home_all_5_xg_n"],0)

    def test_same_match_not_used_as_pre_match_shot_feature(self):
        own=shot("m_000002")
        with self.assertRaisesRegex(FeatureSafetyError,"INVALID_NATIVE_SHOT_RECORD"):
            self.build(shot_observations=[own])

    def test_old_cutoff_before_source_capture_is_rejected(self):
        with self.assertRaisesRegex(FeatureSafetyError,"SOURCE_OBSERVED_AFTER_CUTOFF"):
            self.build(cutoff_utc="2026-10-26T08:00:00Z")

    def test_frozen_identical_capture_deterministic(self):
        a=self.build(shot_observations=[shot()])
        b=self.build(shot_observations=[shot()])
        self.assertEqual(a["sha256"],b["sha256"])
        self.assertEqual(a["sha256"],digest({k:v for k,v in a.items() if k!="sha256"}))

    def test_no_pre_fetched_model_training_or_odds(self):
        v=self.build()
        self.assertNotIn("bookmaker_odds",v)
        self.assertEqual(v["source_evidence"]["raw_records_archived"],False)
        self.assertTrue(v["source_evidence"]["requires_future_verified_receipt_ledger"])

if __name__=="__main__":
    unittest.main()
