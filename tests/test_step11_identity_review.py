"""Step11 strict provider identity and full original xG evidence tests."""
import json
import sqlite3
import unittest
from datetime import datetime,timezone,timedelta
from src.kb3_identity_review import inspect_match,aggregate_review
from src.kb3_xg_pit import record_xg,verify_xg,select_xg_asof
from src.kb3_pit_ledger import canonical,hexdigest

def utc(delta):
    return (datetime.now(timezone.utc)+timedelta(seconds=delta)).isoformat().replace("+00:00","Z")

def pitch(name="Arsenal", status="finished", day="2026-10-25T14:00:00Z", score=(2,1)):
    return {"id":"m_123ABC","time_utc":day,"status":status,
      "home_team":{"id":"p_home","name":name},
      "away_team":{"id":"p_away","name":"Chelsea"},
      "score_home":score[0],"score_away":score[1]}

def football(name="Arsenal",date="2026-10-25T14:00:00+00:00",status="FT",fid=3001,score=(2,1)):
    return {"fixture":{"id":fid,"date":date,"status":{"short":status}},
      "teams":{"home":{"id":25,"name":name},"away":{"id":32,"name":"Chelsea"}},
      "goals":{"home":score[0],"away":score[1]}}

def shots():
    return {"data":{"periods":[{"shots":[{"team_id":"p_home","expected_goals":0.4},
                                {"team_id":"p_away","expected_goals":0.3}]}]}}

class TestIdentityReview(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)

    def record(self,p=None,af=None,shotfeed=None):
        return record_xg(self.db,p or pitch(),shots() if shotfeed is None else shotfeed,
            [football()] if af is None else af,
            started_at_utc=utc(-4),completed_at_utc=utc(-3))

    def test_accept_strict_time_names_score_ft(self):
        r=inspect_match(pitch(),[football()])
        self.assertEqual(r["state"],"EXACT_TIME_NAMES_SCORE_FT")
        self.assertEqual(r["fixture_id"],3001)
        saved=self.record()
        self.assertTrue(saved["accepted"])
        check=verify_xg(self.db)
        self.assertEqual(check["strict_complete"],1)
        value=select_xg_asof(self.db,3001,utc(3))
        self.assertEqual(value["home_xg"],0.4)
        self.assertFalse(value["training_allowed"])

    def test_similar_alias_requires_review_never_promoted(self):
        af=[football(name="Arsenal FC")]
        r=inspect_match(pitch(),af)
        self.assertEqual(r["state"],"ALIAS_REVIEW_REQUIRED")
        self.assertIsNone(r["fixture_id"])
        x=self.record(af=af)
        self.assertFalse(x["accepted"])
        self.assertEqual(verify_xg(self.db)["quarantined"],1)
        self.assertIsNone(select_xg_asof(self.db,3001,utc(5)))

    def test_other_score_is_not_accepted(self):
        af=[football(score=(3,1))]
        r=inspect_match(pitch(),af)
        self.assertEqual(r["state"],"SCORE_DISAGREEMENT")
        self.assertIsNone(r["fixture_id"])

    def test_same_day_different_kickoff_cannot_pass(self):
        af=[football(date="2026-10-25T16:30:00Z")]
        r=inspect_match(pitch(),af)
        self.assertEqual(r["state"],"KICKOFF_DISAGREEMENT")
        self.assertIsNone(r["fixture_id"])

    def test_multiple_identical_provider_fixtures_are_quarantined(self):
        af=[football(fid=3001),football(fid=3002)]
        r=inspect_match(pitch(),af)
        self.assertEqual(r["state"],"MULTIPLE_EXACT_FIXTURES_QUARANTINED")
        self.assertIsNone(r["fixture_id"])

    def test_nonfinal_cannot_approve(self):
        self.assertEqual(inspect_match(pitch(),[football(status="NS")])["state"],
                         "NO_FOOTBALL_FIXTURE_IN_WINDOW")

    def test_match_metadata_sealed_in_original_envelope(self):
        self.record(af=[football(name="Arsenal FC")])
        original=self.db.execute("SELECT raw_json FROM pit_xg_observations").fetchone()[0]
        v=json.loads(original)
        self.assertEqual(v["pitch_match"]["home_team"]["name"],"Arsenal")
        self.assertEqual(v["api_football_candidates"][0]["teams"]["home"]["name"],"Arsenal FC")
        self.assertEqual(v["schema"],"kb3-xg-source-envelope-v2")

    def test_xg_sum_inconsistent_with_source_is_caught(self):
        self.record()
        self.db.execute("DROP TRIGGER pit_xg_no_update")
        self.db.execute("UPDATE pit_xg_observations SET xg_home=0.9")
        with self.assertRaisesRegex(ValueError,"(XG_SOURCE_TOTALS|XG_OBSERVATION_HASH)"):
            verify_xg(self.db)

    def test_source_shot_mutation_with_new_rawhash_still_detected(self):
        self.record()
        row=self.db.execute("SELECT raw_json FROM pit_xg_observations").fetchone()[0]
        val=json.loads(row)
        val["shots_response"]["data"]["periods"][0]["shots"][0]["expected_goals"]=0.9
        changed=canonical(val).decode("utf8")
        self.db.execute("DROP TRIGGER pit_xg_no_update")
        self.db.execute("UPDATE pit_xg_observations SET raw_json=?, raw_sha256=?",
                        (changed,hexdigest(changed.encode("utf8"))))
        with self.assertRaisesRegex(ValueError,"(XG_SOURCE_TOTALS|XG_OBSERVATION_HASH)"):
            verify_xg(self.db)

    def test_aggregate_no_sensitive_rows_or_auto_aliases(self):
        arr=[inspect_match(pitch(),[football()]),
             inspect_match(pitch(),[football(name="Arsenal FC")])]
        r=aggregate_review(arr)
        self.assertEqual(r["strict_approved"],1)
        self.assertEqual(r["auto_approved_aliases"],0)
        self.assertNotIn("Arsenal",json.dumps(r))
        self.assertFalse(r["training_allowed"])

if __name__=="__main__":
    unittest.main()
