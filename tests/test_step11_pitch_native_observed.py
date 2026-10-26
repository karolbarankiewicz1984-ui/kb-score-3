"""Native observed-at features built only from network-labeled ephemeral test receipts."""
from datetime import datetime,timedelta,timezone
import sqlite3
import unittest
from src.kb3_pitch_native_ledger import record
from src.kb3_pitch_native_observed_features import build_native_observed
from src.kb3_features import FeatureSafetyError,digest
from tests.test_step11_pitch_native_ledger import season,shots

def t(offset):
    return (datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat().replace("+00:00","Z")

class NativeRealAsOfTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        # Synthetic fixture values, network-like clock strictly local to a unit test.
        self.src=season()
        self.src[7]["home_team"]=dict(self.src[0]["home_team"])
        self.target=self.src[7]["id"]
        record(self.db,"matches",self.src,started_at_utc=t(-12),
               completed_at_utc=t(-11),origin="NETWORK_OBSERVED")
        record(self.db,"shots",shots(),started_at_utc=t(-9),
               completed_at_utc=t(-8),origin="NETWORK_OBSERVED")

    def build(self,at=5):
        return build_native_observed(self.db,self.target,cutoff_utc=t(at))

    def test_fixture_and_shots_are_combined_by_same_pitch_id(self):
        result=self.build()
        self.assertEqual(result["mode"],"observed")
        self.assertEqual(result["accepted_predecessor_count"],7)
        self.assertEqual(result["features"]["home_all_5_xg_n"],1)
        self.assertEqual(result["features"]["home_all_5_xg_avg"],0.5)
        self.assertTrue(result["source_evidence"]["native_ids_only"])
        self.assertFalse(result["training_allowed"])
        self.assertFalse(result["target_prematch_snapshot_certified"])

    def test_shots_omitted_when_cutoff_before_network_shot_capture(self):
        result=self.build(at=-10)
        self.assertEqual(result["accepted_predecessor_count"],7)
        self.assertEqual(result["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(result["features"]["home_all_5_xg_avg"])

    def test_fixture_not_available_before_its_capture(self):
        with self.assertRaisesRegex(FeatureSafetyError,"NO_NATIVE_SOURCE_BEFORE_CUTOFF"):
            self.build(at=-15)

    def test_no_future_target_and_no_own_shot_leak(self):
        result=self.build()
        self.assertTrue(all(x["fixture_id"]!=self.target for x in result["lineage"]))
        self.assertEqual(result["source_evidence"]["provider"],"PitchAPI")
        self.assertEqual(result["sha256"],digest({k:v for k,v in result.items() if k!="sha256"}))

    def test_later_revised_result_cannot_resurrect_old_finished(self):
        start=t(-4);end=t(-3)
        changed=season()
        changed[7]["home_team"]=dict(self.src[0]["home_team"])
        changed[0]["status"]="not_started"
        changed[0]["score_home"]=None
        changed[0]["score_away"]=None
        record(self.db,"matches",changed,started_at_utc=start,
               completed_at_utc=end,origin="NETWORK_OBSERVED")
        before=self.build(at=-5)
        after=self.build(at=2)
        self.assertEqual(before["accepted_predecessor_count"],7)
        self.assertEqual(after["accepted_predecessor_count"],6)
        self.assertEqual(after["features"]["home_all_5_xg_n"],0)

    def test_failed_target_after_kickoff(self):
        with self.assertRaisesRegex(FeatureSafetyError,"TARGET_ALREADY_STARTED"):
            build_native_observed(self.db,"m_000000",cutoff_utc=t(5))

if __name__=="__main__":
    unittest.main()
