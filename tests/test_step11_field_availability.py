"""Step11 field-level availability and adversarial no-lookahead audit."""
from datetime import datetime,timezone,timedelta
import sqlite3
import unittest
from pitch_pair_fixtures import stats
from copy import deepcopy
from src.kb3_pitch_native_ledger import record
from src.kb3_pitch_native_observed_features import build_native_observed
from src.kb3_step11_field_audit import (
    validate_observed_rows,feature_clock_map,source_time,
    TemporalEvidenceError,timestamp
)
from src.kb3_features import FeatureSafetyError,digest
from test_step11_pitch_native_ledger import season,shots

def t(seconds):
    return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z")

class FieldAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.fixtures=season()
        self.fixtures[7]["home_team"]=dict(self.fixtures[0]["home_team"])
        record(self.db,"matches",self.fixtures,
               started_at_utc=t(-25),completed_at_utc=t(-24),
               origin="NETWORK_OBSERVED")
        record(self.db,"shots",shots(),
               started_at_utc=t(-14),completed_at_utc=t(-13),
               stats_payload=stats("m_000000","t_000000","t_000001",.5,.2),
               stats_started_at_utc=t(-12),stats_completed_at_utc=t(-11),
               origin="NETWORK_OBSERVED")
        self.target=self.fixtures[7]["id"]

    def build(self):
        return build_native_observed(self.db,self.target,cutoff_utc=t(5))

    def test_every_feature_and_missing_flag_has_availability_receipt(self):
        r=self.build()
        expected=set(r["features"])|{"missing:"+k for k in r["missing_flags"]}
        self.assertEqual(set(r["feature_availability"]),expected)
        self.assertGreater(len(expected),100)
        self.assertFalse(r["training_allowed"])
        self.assertEqual(r["sha256"],digest({k:v for k,v in r.items() if k!="sha256"}))

    def test_all_field_times_are_observed_pre_cutoff(self):
        r=self.build()
        cutoff=timestamp(r["feature_cutoff_utc"])
        for field,proof in r["feature_availability"].items():
            self.assertLessEqual(timestamp(proof["latest_required_observed_at_utc"]),cutoff,field)
            self.assertEqual(proof["provider_original_published_at_utc"],None)
            self.assertFalse(proof["training_allowed"])
            self.assertEqual(len(proof["fixtures_sha256"]),64)

    def test_xg_field_knows_shots_were_later_than_result_snapshot(self):
        r=self.build()
        xg=r["feature_availability"]["home_all_5_xg_avg"]
        goals=r["feature_availability"]["home_all_5_gf_avg"]
        self.assertEqual(r["features"]["home_all_5_xg_n"],1)
        self.assertGreater(timestamp(xg["latest_required_observed_at_utc"]),
                           timestamp(goals["latest_required_observed_at_utc"]))
        self.assertEqual(xg["kind"],"XG_OBSERVATIONS_AND_RESULTS")

    def test_away_venue_provenance_uses_correct_shot_direction(self):
        other=sqlite3.connect(":memory:")
        self.addCleanup(other.close)
        fixtures=season()
        fixtures[7]["away_team"]=dict(fixtures[0]["away_team"])
        record(other,"matches",fixtures,started_at_utc=t(-25),
               completed_at_utc=t(-24),origin="NETWORK_OBSERVED")
        record(other,"shots",shots(),started_at_utc=t(-14),
               completed_at_utc=t(-13),stats_payload=stats("m_000000","t_000000","t_000001",.5,.2),
               stats_started_at_utc=t(-12),stats_completed_at_utc=t(-11),origin="NETWORK_OBSERVED")
        r=build_native_observed(other,fixtures[7]["id"],cutoff_utc=t(5))
        self.assertEqual(r["features"]["away_all_5_xg_n"],1)
        self.assertGreater(timestamp(
            r["feature_availability"]["away_all_5_xg_avg"]["latest_required_observed_at_utc"]),
            timestamp(r["feature_availability"]["away_all_5_gf_avg"]["latest_required_observed_at_utc"]))

    def test_no_xg_gives_null_but_documented_completeness_receipt(self):
        db=sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        record(db,"matches",self.fixtures,started_at_utc=t(-25),
               completed_at_utc=t(-24),origin="NETWORK_OBSERVED")
        r=build_native_observed(db,self.target,cutoff_utc=t(5))
        self.assertIsNone(r["features"]["home_all_5_xg_avg"])
        self.assertTrue(r["missing_flags"]["home_all_5_xg"])
        self.assertEqual(r["feature_availability"]["home_all_5_xg_avg"]["included_games"],1)

    def test_source_time_rejects_two_ambiguous_capture_fields(self):
        with self.assertRaisesRegex(TemporalEvidenceError,"AMBIGUOUS_XG_SOURCE"):
            source_time({"shot_observed_at_utc":t(-10),
                         "actual_observed_at_utc":t(-9)})

    def test_source_time_applies_review_approval_barrier(self):
        approval=t(-3)
        actual=t(-20)
        self.assertEqual(source_time({"actual_observed_at_utc":actual,
             "review_approval_not_before_utc":approval}),timestamp(approval))

    def test_later_xg_and_approval_cannot_leak_past_cutoff(self):
        current=datetime.now(timezone.utc)
        row={"fixture_id":"m_prev","home_team_id":"t_home","away_team_id":"t_away",
             "date":current-timedelta(days=7),"status":"FINISHED",
             "goals_home_90":1,"goals_away_90":0,
             "captured_at_utc":t(-20),
             "xgh":0.6,"xga":None,"xgh_source":{
               "actual_observed_at_utc":t(-10),
               "review_approval_not_before_utc":t(30)},
             "xga_source":None}
        with self.assertRaisesRegex(TemporalEvidenceError,"XG_KNOWN_AFTER_TARGET_CUTOFF"):
            validate_observed_rows([row],cutoff=timestamp(t(0)),
                kickoff=current+timedelta(days=2),target_id="target",
                target={"home_team_id":"t_home","away_team_id":"t_away"})

    def test_pre_cutoff_fixture_result_backfilled_after_cutoff_rejected(self):
        now=datetime.now(timezone.utc)
        row={"fixture_id":"m_prev","home_team_id":"t_home","away_team_id":"t_away",
             "date":now-timedelta(days=7),"status":"FINISHED",
             "goals_home_90":1,"goals_away_90":0,
             "captured_at_utc":t(40),"xgh":None,"xga":None,
             "xgh_source":None,"xga_source":None}
        with self.assertRaisesRegex(TemporalEvidenceError,"RESULT_KNOWN_AFTER_TARGET_CUTOFF"):
            validate_observed_rows([row],cutoff=timestamp(t(0)),
                kickoff=now+timedelta(days=2),target_id="target",
                target={"home_team_id":"t_home","away_team_id":"t_away"})

    def test_future_fixture_or_own_target_cannot_be_in_history(self):
        now=datetime.now(timezone.utc)
        row={"fixture_id":"target","home_team_id":"t_home","away_team_id":"t_away",
             "date":now-timedelta(days=3),"status":"FINISHED",
             "goals_home_90":1,"goals_away_90":0,"captured_at_utc":t(-20),
             "xgh":None,"xga":None,"xgh_source":None,"xga_source":None}
        with self.assertRaisesRegex(TemporalEvidenceError,"DUPLICATE_OR_TARGET"):
            validate_observed_rows([row],cutoff=timestamp(t(0)),
                kickoff=now+timedelta(days=2),target_id="target",
                target={"home_team_id":"t_home","away_team_id":"t_away"})
        row["fixture_id"]="m_prev"
        row["date"]=now+timedelta(days=1)
        with self.assertRaisesRegex(TemporalEvidenceError,"FUTURE_RESULT"):
            validate_observed_rows([row],cutoff=timestamp(t(0)),
                kickoff=now+timedelta(days=2),target_id="target",
                target={"home_team_id":"t_home","away_team_id":"t_away"})

    def test_snapshot_clock_cannot_be_later_than_cutoff(self):
        r=self.build()
        with self.assertRaisesRegex(TemporalEvidenceError,"LATEST_SOURCE_AFTER_CUTOFF"):
            feature_clock_map({"home_team_id":"t_home","away_team_id":"t_away"},
              [],r["features"],r["missing_flags"],cutoff=timestamp(t(0)),
              source_evidence={"source_observed_at_utc":t(30)})

if __name__=="__main__":
    unittest.main()
