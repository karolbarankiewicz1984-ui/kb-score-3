"""Step11: test curated, match-bound evidence without generic alias promotion."""
import copy
import sqlite3
import unittest
from datetime import datetime,timedelta,timezone

from src.kb3_pit_ledger import record_capture,verify_chain
from src.kb3_xg_pit import record_xg
from src.kb3_reviewed_xg import review,select_asof


def now(offset):
    return (datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat().replace("+00:00","Z")

GAME_DATE="2026-08-01T15:00:00Z"
TARGET_DATE="2027-05-01T15:00:00Z"
def single(i,date,short,goals=(2,1),home="Arsenal"):
    return {"fixture":{"id":i,"date":date,"status":{"short":short}},
       "league":{"id":39,"season":2026},
       "teams":{"home":{"id":25,"name":home},
                "away":{"id":32,"name":"Chelsea"}},
       "goals":{"home":goals[0] if short=="FT" else None,
                "away":goals[1] if short=="FT" else None},
       "score":{"fulltime":{"home":goals[0] if short=="FT" else None,
                            "away":goals[1] if short=="FT" else None}}}

def pitch():
    return {"id":"m_QA0001","time_utc":GAME_DATE,"status":"finished",
      "home_team":{"id":"p25","name":"Arsenal FC"},
      "away_team":{"id":"p32","name":"Chelsea"},
      "score_home":2,"score_away":1}

def shotfeed():
    return {"data":{"periods":[{"shots":[
        {"team_id":"p25","expected_goals":0.6},
        {"team_id":"p32","expected_goals":0.3}]}]}}

class TestCuratedXg(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        fixture=single(3001,GAME_DATE,"FT")
        target=single(3002,TARGET_DATE,"NS")
        response=[fixture,target]+[
            single(3003+i,TARGET_DATE,"NS") for i in range(378)]
        payload={"response":response,"errors":[],"paging":{"total":1}}
        record_capture(self.db,payload,season=2026,
                       started_at_utc=now(-6),completed_at_utc=now(-5),
                       origin="NETWORK_OBSERVED")
        record_xg(self.db,pitch(),shotfeed(),response,
                  started_at_utc=now(-3),completed_at_utc=now(-2))
        src=self.db.execute("""SELECT observation_id,raw_sha256,completed_at_utc
                     FROM pit_xg_observations""").fetchone()
        self.crosswalk={"schema":"kb3-step11-reviewed-fixture-crosswalk-v1",
              "generic_name_alias_matching_allowed":False,
              "model_training_allowed":False,
              "source_encrypted_sha256":"SOURCE_ENCRYPTED_TEST_SHA",
              "source_fixture_chain_sha256":verify_chain(self.db)["final_chain_sha256"],
              "reviewed":[{"pitch_match_id":"m_QA0001",
                 "pitch_observation_id":src[0],"raw_sha256":src[1],
                 "api_fixture_id":3001,"pitch_kickoff_utc":GAME_DATE,
                 "score_home":2,"score_away":1,
                 "pitch_home_team_id":"p25","pitch_away_team_id":"p32",
                 "api_home_team_id":25,"api_away_team_id":32,
                 "pitch_home_name":"Arsenal FC","pitch_away_name":"Chelsea",
                 "api_home_name":"Arsenal","api_away_name":"Chelsea"}]}
        self.archive={"encrypted_sha256":"SOURCE_ENCRYPTED_TEST_SHA"}
        self.observed=src[2]

    def good(self):
        return review(self.db,self.archive,self.crosswalk)

    def test_matchbound_manual_pair_is_accepted_without_modifying_original(self):
        x=self.good()
        self.assertEqual(list(x),[3001])
        self.assertEqual(x[3001]["xg_home"],0.6)
        self.assertFalse(x[3001]["training_allowed"])
        row=self.db.execute("""SELECT identity_state,xg_home,api_football_fixture_id
                      FROM pit_xg_observations""").fetchone()
        self.assertEqual(row,("ALIAS_REVIEW_REQUIRED",None,None))

    def test_own_match_never_receives_its_postmatch_xg(self):
        self.assertIsNone(select_asof(self.db,self.archive,self.crosswalk,
                        history_fixture_id=3001,target_fixture_id=3001,
                        cutoff_utc=now(30)))

    def test_cutoff_before_original_xg_capture_is_denied(self):
        self.assertIsNone(select_asof(self.db,self.archive,self.crosswalk,
                        history_fixture_id=3001,target_fixture_id=3002,
                        cutoff_utc=now(-4)))

    def test_later_predicted_match_can_use_prior_observed_history(self):
        value=select_asof(self.db,self.archive,self.crosswalk,
                       history_fixture_id=3001,target_fixture_id=3002,
                       cutoff_utc=now(10))
        self.assertEqual(value["xg_away"],0.3)
        self.assertFalse(value["historical_pit_certified"])
        self.assertIsNone(value["provider_initial_published_at_utc"])

    def test_unknown_reviewer_team_id_is_rejected(self):
        bad=copy.deepcopy(self.crosswalk)
        bad["reviewed"][0]["pitch_home_team_id"]="wrong"
        with self.assertRaisesRegex(ValueError,"PITCH_TEAM_ID"):
            review(self.db,self.archive,bad)

    def test_wrong_football_club_id_is_rejected(self):
        bad=copy.deepcopy(self.crosswalk)
        bad["reviewed"][0]["api_away_team_id"]=999
        with self.assertRaisesRegex(ValueError,"FOOTBALL_TEAM_ID"):
            review(self.db,self.archive,bad)

    def test_wrong_snapshot_digest_is_rejected(self):
        bad=copy.deepcopy(self.archive)
        bad["encrypted_sha256"]="tampered"
        with self.assertRaisesRegex(ValueError,"REVIEW_ARCHIVE_MISMATCH"):
            review(self.db,bad,self.crosswalk)

    def test_source_observation_digest_change_is_rejected(self):
        bad=copy.deepcopy(self.crosswalk)
        bad["reviewed"][0]["raw_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"IMMUTABLE_QUARANTINE"):
            review(self.db,self.archive,bad)

    def test_duplicate_review_link_denied(self):
        bad=copy.deepcopy(self.crosswalk)
        bad["reviewed"].append(copy.deepcopy(bad["reviewed"][0]))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_REVIEWED"):
            review(self.db,self.archive,bad)

    def test_unapproved_generic_alias_mode_denied(self):
        bad=copy.deepcopy(self.crosswalk)
        bad["generic_name_alias_matching_allowed"]=True
        with self.assertRaisesRegex(ValueError,"GENERIC_ALIASES"):
            review(self.db,self.archive,bad)

if __name__=="__main__":
    unittest.main()
