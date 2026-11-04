"""Independent narrow GATE11 check against the ORIGINAL acceptance contract.

This accepts the observed-at feature-engineering stage only. It explicitly
does NOT certify retrospective prematch PIT, a trained model, bookmaker odds,
completeness of every xG feed, or future cross-day provider monitoring.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import sqlite3
import unittest
from pitch_pair_fixtures import stats
from src.kb3_pitch_native_ledger import record
from src.kb3_pitch_native_observed_features import build_native_observed
from src.kb3_features import FeatureSafetyError
from src.kb3_step11_field_audit import timestamp
from test_step11_pitch_native_ledger import season,shots

def now(offset=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat().replace("+00:00","Z")

class OriginalGate11ContractTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.games=season()
        self.games[7]["home_team"]=dict(self.games[0]["home_team"])
        self.target=self.games[7]["id"]
        record(self.db,"matches",self.games,started_at_utc=now(-40),
               completed_at_utc=now(-39),origin="NETWORK_OBSERVED")
        self.cutoff=now(5)

    def test_every_feature_and_missing_flag_has_source_clock(self):
        output=build_native_observed(self.db,self.target,cutoff_utc=self.cutoff)
        expected=set(output["features"])|{
            "missing:"+name for name in output["missing_flags"]}
        self.assertEqual(set(output["feature_availability"]),expected)
        self.assertGreaterEqual(len(expected),150)
        self.assertEqual(output["schema"],"kb3-step11-v0.5")
        for name,receipt in output["feature_availability"].items():
            self.assertLessEqual(timestamp(receipt["latest_required_observed_at_utc"]),
                timestamp(self.cutoff),name)
            self.assertIsNone(receipt["provider_original_published_at_utc"])
            self.assertFalse(receipt["training_allowed"])

    def test_missing_xg_is_null_never_fake_zero(self):
        output=build_native_observed(self.db,self.target,cutoff_utc=self.cutoff)
        self.assertIsNone(output["features"]["home_all_5_xg_avg"])
        self.assertEqual(output["features"]["home_all_5_xg_n"],0)
        self.assertTrue(output["missing_flags"]["home_all_5_xg"])
        self.assertFalse(output["training_allowed"])
        self.assertFalse(output["target_prematch_snapshot_certified"])

    def test_complete_native_shot_produces_source_qualified_xg(self):
        record(self.db,"shots",shots(),started_at_utc=now(-14),
               completed_at_utc=now(-13),stats_payload=stats("m_000000","t_000000","t_000001",.5,.2),
               stats_started_at_utc=now(-12),stats_completed_at_utc=now(-11),origin="NETWORK_OBSERVED")
        output=build_native_observed(self.db,self.target,cutoff_utc=self.cutoff)
        self.assertEqual(output["features"]["home_all_5_xg_n"],1)
        self.assertGreater(output["features"]["home_all_5_xg_avg"],0)
        xg_time=timestamp(output["feature_availability"][
            "home_all_5_xg_avg"]["latest_required_observed_at_utc"])
        goal_time=timestamp(output["feature_availability"][
            "home_all_5_gf_avg"]["latest_required_observed_at_utc"])
        self.assertGreater(xg_time,goal_time)
        self.assertLessEqual(xg_time,timestamp(self.cutoff))

    def test_future_snapshot_cannot_be_used_for_old_cutoff(self):
        with self.assertRaises(FeatureSafetyError):
            build_native_observed(self.db,self.target,cutoff_utc=now(-100))

    def test_stage11_completion_never_unblocks_training(self):
        output=build_native_observed(self.db,self.target,cutoff_utc=self.cutoff)
        self.assertFalse(output["training_allowed"])
        self.assertFalse(output["target_prematch_snapshot_certified"])
        self.assertIn("OBSERVED_AT",output["availability_class"])

if __name__=="__main__":
    unittest.main()
