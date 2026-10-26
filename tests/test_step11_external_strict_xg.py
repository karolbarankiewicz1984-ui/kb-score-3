"""Observed-at feature builder with two *separate* independently sealed sources."""
import copy
import sqlite3
from datetime import datetime,timedelta,timezone
import unittest

from src.kb3_observed_features import build_observed_features
from src.kb3_features import FeatureSafetyError
from src.kb3_pit_ledger import record_capture,verify_chain
from src.kb3_xg_pit import record_xg,verify_xg


def utc(seconds):
    return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z")

KICKOFF="2026-08-01T15:00:00Z"
LATER="2027-05-01T15:00:00Z"

def full_response(*,mutate=False):
    rows=[
      {"fixture":{"id":3001,"date":KICKOFF,"status":{"short":"FT"}},
       "league":{"id":39,"season":2026},
       "teams":{"home":{"id":25,"name":"Arsenal"},
                "away":{"id":32,"name":"Chelsea"}},
       "goals":{"home":2,"away":1},
       "score":{"fulltime":{"home":2,"away":1}}}]
    for i in range(379):
        fid=3002+i
        rows.append({"fixture":{"id":fid,"date":LATER,"status":{"short":"NS"}},
           "league":{"id":39,"season":2026},
           "teams":{"home":{"id":25+i*2,"name":"A"},
                    "away":{"id":32+i*2,"name":"B"}},
           "goals":{"home":None,"away":None},
           "score":{"fulltime":{"home":None,"away":None}}})
    if mutate:
        rows[-1]["fixture"]["date"]="2027-05-02T15:00:00Z"
    return {"response":rows,"errors":[],"paging":{"total":1}}

def pitch():
    return {"id":"m_XGTEST1","time_utc":KICKOFF,"status":"finished",
       "home_team":{"id":"pitch25","name":"Arsenal"},
       "away_team":{"id":"pitch32","name":"Chelsea"},
       "score_home":2,"score_away":1}

def shots():
    return {"data":{"periods":[{"shots":[
       {"team_id":"pitch25","expected_goals":0.8},
       {"team_id":"pitch32","expected_goals":0.4}]}]}}


class TestSeparateStrictXg(unittest.TestCase):
    def setUp(self):
        self.primary=sqlite3.connect(":memory:")
        self.extra=sqlite3.connect(":memory:")
        self.addCleanup(self.primary.close)
        self.addCleanup(self.extra.close)
        self.payload=full_response()
        record_capture(self.primary,self.payload,season=2026,
                       started_at_utc=utc(-12),completed_at_utc=utc(-11),
                       origin="NETWORK_OBSERVED")
        record_capture(self.extra,self.payload,season=2026,
                       started_at_utc=utc(-8),completed_at_utc=utc(-7),
                       origin="NETWORK_OBSERVED")
        record_xg(self.extra,pitch(),shots(),self.payload["response"],
                  started_at_utc=utc(-5),completed_at_utc=utc(-4))
        self.manifest={
          "schema":"kb3-pit-sealed-observation-v1",
          "encrypted_sha256":"a"*64,
          "provider_publication_certified":False,
          "training_allowed":False,
          "ledger_evidence":verify_chain(self.extra),
          "xg_evidence":verify_xg(self.extra)
        }

    def features(self,delta,**kw):
        return build_observed_features(self.primary,3002,cutoff_utc=utc(delta),
            strict_xg_db=self.extra,strict_xg_manifest=self.manifest,**kw)

    def test_strict_xg_from_independent_source(self):
        v=self.features(1)
        self.assertEqual(v["accepted_predecessor_count"],1)
        self.assertEqual(v["features"]["home_all_5_xg_n"],1)
        self.assertEqual(v["features"]["home_all_5_xg_avg"],0.8)
        self.assertEqual(v["features"]["away_all_5_xg_avg"],0.4)
        self.assertEqual(v["lineage"][0]["xg_home"]["review_status"],
                         "SOURCE_STRICT_EXACT_TIME_NAMES_SCORE")
        self.assertFalse(v["training_allowed"])
        self.assertIsNone(v["lineage"][0]["xg_home"]["review_approval_not_before_utc"])

    def test_pre_capture_cutoff_no_xg_and_no_future_hash(self):
        cutoff=utc(-10)
        direct=build_observed_features(self.primary,3002,cutoff_utc=cutoff)
        strict=build_observed_features(self.primary,3002,cutoff_utc=cutoff,
            strict_xg_db=self.extra,strict_xg_manifest=self.manifest)
        self.assertEqual(direct,strict)
        self.assertEqual(strict["features"]["home_all_5_xg_n"],0)

    def test_after_fixture_capture_before_shots_xg_still_null(self):
        v=self.features(-6)
        self.assertEqual(v["accepted_predecessor_count"],1)
        self.assertEqual(v["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(v["features"]["home_all_5_xg_avg"])

    def test_manifest_record_count_mismatch_blocks(self):
        bad=copy.deepcopy(self.manifest)
        bad["xg_evidence"]["captured"]=99
        with self.assertRaisesRegex(FeatureSafetyError,"INDEPENDENT_STRICT_XG_SOURCE_REJECTED"):
            self.features(5,strict_xg_manifest=bad)

    def test_different_source_fixture_response_blocks(self):
        other=sqlite3.connect(":memory:")
        self.addCleanup(other.close)
        response=full_response(mutate=True)
        record_capture(other,response,season=2026,
            started_at_utc=utc(-8),completed_at_utc=utc(-7),
            origin="NETWORK_OBSERVED")
        record_xg(other,pitch(),shots(),response["response"],
            started_at_utc=utc(-5),completed_at_utc=utc(-4))
        meta=copy.deepcopy(self.manifest)
        meta["ledger_evidence"]=verify_chain(other)
        meta["xg_evidence"]=verify_xg(other)
        with self.assertRaisesRegex(FeatureSafetyError,"INDEPENDENT_STRICT_XG_SOURCE_REJECTED"):
            build_observed_features(self.primary,3002,cutoff_utc=utc(1),
                strict_xg_db=other,strict_xg_manifest=meta)

    def test_requires_both_source_db_and_manifest(self):
        with self.assertRaisesRegex(FeatureSafetyError,"STRICT_XG_DB_AND_MANIFEST_REQUIRED_TOGETHER"):
            build_observed_features(self.primary,3002,cutoff_utc=utc(1),
                                     strict_xg_db=self.extra)

    def test_source_also_lacks_original_published_time(self):
        v=self.features(1)
        evidence=v["source_evidence"]["strict_external_xg_source"]
        self.assertEqual(evidence["strict_xg_available_at_cutoff"],1)
        self.assertFalse(evidence["provider_initial_published_at_known"])
        self.assertFalse(v["target_prematch_snapshot_certified"])

if __name__=="__main__":
    unittest.main()
