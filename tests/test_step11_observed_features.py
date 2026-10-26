"""Step11 real observation source -> shared Elo/form/xG feature accumulator.

All fixtures and API timestamps in these unit tests are SYNTHETIC; a real
production capture is never backdated or used to claim historical certification.
"""
from __future__ import annotations
import copy
from datetime import datetime,timedelta,timezone
import sqlite3
import unittest

from src.kb3_features import EloParameters,FeatureSafetyError,digest
from src.kb3_observed_features import build_observed_features
from src.kb3_pit_ledger import record_capture,verify_chain
from src.kb3_xg_pit import record_xg,verify_xg


def when(offset):
    return (datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat().replace("+00:00","Z")

def fixture(fid,kickoff,home,away,short,gh=None,ga=None,hname="Arsenal",aname="Chelsea"):
    return {"fixture":{"id":fid,"date":kickoff,"status":{"short":short}},
      "league":{"id":39,"season":2026},
      "teams":{"home":{"id":home,"name":hname},"away":{"id":away,"name":aname}},
      "goals":{"home":gh,"away":ga},
      "score":{"fulltime":{"home":gh,"away":ga}}}

def payload(*,past_status="FT"):
    source=[
      fixture(3001,"2026-08-01T15:00:00Z",25,32,"FT",2,1),
      fixture(3002,"2027-05-01T15:00:00Z",25,32,"NS"),
      fixture(3003,"2026-10-25T14:00:00Z",25,33,past_status,
              1 if past_status=="FT" else None,
              0 if past_status=="FT" else None,aname="Team C")]
    source.extend(fixture(3004+i,"2027-05-01T15:00:00Z",100+i,900+i,"NS")
                  for i in range(377))
    assert len(source)==380
    return {"errors":[],"paging":{"total":1},"response":source}

def pitch():
    return {"id":"m_QATEST","time_utc":"2026-08-01T15:00:00Z",
      "status":"finished",
      "home_team":{"id":"p25","name":"Arsenal FC"},
      "away_team":{"id":"p32","name":"Chelsea"},
      "score_home":2,"score_away":1}

def shots():
    return {"data":{"periods":[{"shots":[
      {"team_id":"p25","expected_goals":0.6},
      {"team_id":"p32","expected_goals":0.3}]}]}}


class TestObservedFeatures(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.old=when(-12)
        self.new=when(-10)
        self.first=self.add_capture(payload(),-12,-10)

    def add_capture(self,data,start,end):
        return record_capture(self.db,data,season=2026,
            started_at_utc=when(start),completed_at_utc=when(end),
            origin="NETWORK_OBSERVED")

    def build(self,cutoff=5,cutoff_value=None,**kw):
        return build_observed_features(self.db,3002,
             cutoff_utc=cutoff_value if cutoff_value is not None else when(cutoff),
             **kw)

    def add_reviewed_xg(self,approved=when(-2)):
        record_xg(self.db,pitch(),shots(),payload()["response"],
                  started_at_utc=when(-6),completed_at_utc=when(-5))
        src=self.db.execute("""
          SELECT observation_id,raw_sha256 FROM pit_xg_observations
        """).fetchone()
        crosswalk={
          "schema":"kb3-step11-reviewed-fixture-crosswalk-v1",
          "generic_name_alias_matching_allowed":False,
          "model_training_allowed":False,
          "source_encrypted_sha256":"SYNTHETIC_SEALED_DIGEST",
          "source_fixture_chain_sha256":verify_chain(self.db)["final_chain_sha256"],
          "review_approval_not_before_utc":approved,
          "review_approval_commit":"https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/1f6032d4562d457e9bcb92381bf28a6cfa56a120",
          "reviewed":[{
            "pitch_match_id":"m_QATEST","pitch_observation_id":src[0],
            "raw_sha256":src[1],"api_fixture_id":3001,
            "pitch_kickoff_utc":"2026-08-01T15:00:00Z",
            "score_home":2,"score_away":1,
            "pitch_home_team_id":"p25","pitch_away_team_id":"p32",
            "api_home_team_id":25,"api_away_team_id":32,
            "pitch_home_name":"Arsenal FC","pitch_away_name":"Chelsea",
            "api_home_name":"Arsenal","api_away_name":"Chelsea"}]}
        return {"encrypted_sha256":"SYNTHETIC_SEALED_DIGEST"},crosswalk

    def test_observed_builder_has_same_elo_and_windows(self):
        v=self.build()
        self.assertEqual(v["mode"],"observed")
        self.assertEqual(v["availability_class"],"OBSERVED_AT_NOT_CERTIFIED")
        self.assertEqual(v["accepted_predecessor_count"],2)
        self.assertEqual(v["features"]["home_games_available"],2)
        self.assertEqual(v["features"]["away_games_available"],1)
        self.assertEqual(v["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(v["features"]["home_all_5_xg_avg"])
        self.assertFalse(v["training_allowed"])
        self.assertFalse(v["target_prematch_snapshot_certified"])
        self.assertTrue(v["row_payload_at_snapshot_proven"])
        self.assertIsNone(v["lineage"][0]["result_published_at_utc"])
        self.assertEqual(v["sha256"],digest({k:v for k,v in v.items() if k!="sha256"}))

    def test_no_observation_asof_cutoff_rejected(self):
        with self.assertRaisesRegex(FeatureSafetyError,"NO_REAL_SOURCE_OBSERVATION"):
            self.build(cutoff=-11)

    def test_target_after_kickoff_rejected(self):
        with self.assertRaisesRegex(FeatureSafetyError,"FEATURE_CUTOFF"):
            build_observed_features(self.db,3002,cutoff_utc="2027-05-01T15:01:00Z")

    def test_source_mode_requires_proper_review_and_manifest_pair(self):
        with self.assertRaisesRegex(FeatureSafetyError,"REQUIRED_TOGETHER"):
            self.build(reviewed_crosswalk={})

    def test_matchbound_xg_enters_rolling_form_after_both_barriers(self):
        mf,cw=self.add_reviewed_xg()
        a=self.build(cutoff=5,archive_manifest=mf,reviewed_crosswalk=cw)
        self.assertEqual(a["features"]["home_all_5_xg_n"],1)
        self.assertEqual(a["features"]["home_all_5_xg_avg"],0.6)
        self.assertEqual(a["features"]["away_all_5_xg_n"],1)
        self.assertEqual(a["features"]["away_all_5_xg_avg"],0.3)
        self.assertEqual(a["lineage"][0]["xg_home"]["pitch_match_id"],"m_QATEST")
        self.assertFalse(a["training_allowed"])

    def test_before_xg_capture_xg_stays_null_even_if_history_known(self):
        mf,cw=self.add_reviewed_xg()
        a=self.build(cutoff=-8,archive_manifest=mf,reviewed_crosswalk=cw)
        self.assertEqual(a["accepted_predecessor_count"],2)
        self.assertEqual(a["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(a["features"]["home_all_5_xg_avg"])

    def test_before_review_approval_xg_stays_null(self):
        mf,cw=self.add_reviewed_xg(approved=when(100))
        cutoff=when(5)
        a=self.build(cutoff_value=cutoff,archive_manifest=mf,reviewed_crosswalk=cw)
        b=self.build(cutoff_value=cutoff)
        self.assertEqual(a["sha256"],b["sha256"])
        self.assertEqual(a["features"]["home_all_5_xg_n"],0)

    def test_invalid_crosswalk_hash_fails_closed(self):
        mf,cw=self.add_reviewed_xg()
        cw["source_encrypted_sha256"]="tampered"
        with self.assertRaisesRegex(FeatureSafetyError,"XG_SOURCE_REVIEW_FAILED"):
            self.build(archive_manifest=mf,reviewed_crosswalk=cw)

    def test_cannot_falsely_claim_review_before_public_merge(self):
        mf,cw=self.add_reviewed_xg(approved="2026-10-26T09:00:00Z")
        with self.assertRaisesRegex(FeatureSafetyError,"REVIEW_APPROVAL_REFERENCE_INVALID"):
            self.build(archive_manifest=mf,reviewed_crosswalk=cw)

    def test_unrecognized_review_commit_is_rejected(self):
        mf,cw=self.add_reviewed_xg()
        cw["review_approval_commit"]="https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/forged"
        with self.assertRaisesRegex(FeatureSafetyError,"REVIEW_APPROVAL_REFERENCE_INVALID"):
            self.build(archive_manifest=mf,reviewed_crosswalk=cw)

    def test_cutoff_earlier_than_later_revised_source_stable(self):
        cutoff=when(-2)
        first=self.build(cutoff_value=cutoff)
        self.add_capture(payload(past_status="PST"),-1,0)
        still=self.build(cutoff_value=cutoff)
        self.assertEqual(first,still)
        after=self.build(cutoff=5)
        self.assertEqual(after["accepted_predecessor_count"],1)
        self.assertEqual(after["features"]["home_games_available"],1)

    def test_no_self_match_xg_or_target_result_in_history(self):
        v=self.build()
        self.assertTrue(all(item["fixture_id"]!=3002 for item in v["lineage"]))
        self.assertEqual(v["fixture_id"],3002)
        self.assertNotIn("result_home_90",v["features"])

    def test_provisional_elo_tuning_not_performed(self):
        default=self.build()
        other=self.build(elo_params=EloParameters(k=12))
        self.assertNotEqual(default["features"]["home_elo"],other["features"]["home_elo"])
        self.assertEqual(default["elo_parameter_status"],"PROVISIONAL_NOT_FITTED")
        self.assertFalse(other["training_allowed"])

    def test_missing_history_before_provenance_never_auto_replayed(self):
        no=build_observed_features(self.db,3002,cutoff_utc=when(4))
        self.assertEqual(no["source_evidence"]["source_class"],
                         "NETWORK_OBSERVED_NOT_PROVIDER_PUBLICATION_CERTIFIED")
        self.assertFalse(no["source_evidence"]["provider_first_publication_time_known"])

if __name__=="__main__":
    unittest.main()
