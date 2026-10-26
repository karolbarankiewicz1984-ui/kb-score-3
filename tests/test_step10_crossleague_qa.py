"""Synthetic adversarial tests for Step10 all-league historical source QA."""
import copy
import unittest
from scripts.step10_crossleague_qa import verify_payload

def sample():
    row={"league_id":39,"league":"Premier League","season":2024,
         "n_fixtures":2,"n_finished":2}
    base={
      "league":{"id":39,"season":2024},
      "fixture":{"id":701,"date":"2024-08-17T14:00:00Z","status":{"short":"FT"}},
      "teams":{"home":{"id":1,"name":"One"},"away":{"id":2,"name":"Two"}},
      "score":{"fulltime":{"home":2,"away":1}},"goals":{"home":2,"away":1},
    }
    other=copy.deepcopy(base)
    other["fixture"]["id"]=702
    other["teams"]["home"]["id"]=2
    other["teams"]["away"]["id"]=1
    other["fixture"]["date"]="2025-04-15T14:00:00Z"
    return row,{"errors":[],"paging":{"total":1},"response":[base,other]}

class CrossleagueTests(unittest.TestCase):
    def test_valid_source_rows_have_no_critical(self):
        a,b=sample()
        self.assertEqual(verify_payload(a,b)["critical"],[])
        self.assertEqual(verify_payload(a,b)["finished"],2)

    def test_duplicate_provider_id_blocks(self):
        a,b=sample()
        b["response"][1]["fixture"]["id"]=701
        self.assertIn("INVALID_OR_DUPLICATE_PROVIDER_IDS",verify_payload(a,b)["critical"])

    def test_wrong_league_season_blocks(self):
        a,b=sample()
        b["response"][0]["league"]["season"]=2023
        self.assertIn("WRONG_LEAGUE_OR_SEASON",verify_payload(a,b)["critical"])

    def test_missing_finished_score_blocks(self):
        a,b=sample()
        b["response"][0]["score"]["fulltime"]={"home":None,"away":None}
        b["response"][0]["goals"]={"home":None,"away":None}
        self.assertIn("FINISHED_WITH_MISSING_90MIN_RESULT",verify_payload(a,b)["critical"])

    def test_outside_season_blocks(self):
        a,b=sample()
        b["response"][0]["fixture"]["date"]="2026-01-01T15:00:00Z"
        self.assertIn("IMPOSSIBLE_OR_OUT_OF_SEASON_DATE",verify_payload(a,b)["critical"])

    def test_duplicate_pair_quarantines_instead_of_dropping(self):
        a,b=sample()
        b["response"][1]["teams"]=copy.deepcopy(b["response"][0]["teams"])
        result=verify_payload(a,b)
        self.assertIn("DUPLICATE_HOME_AWAY_PAIR_REVIEW_REQUIRED",result["warnings"])
        self.assertEqual(result["eligibility"],"QUARANTINE")

    def test_error_payload_blocks(self):
        a,b=sample()
        b["errors"]={"invalid":"token"}
        self.assertIn("INVALID_API_PAYLOAD",verify_payload(a,b)["critical"])

    def test_season_in_progress_not_false_fail(self):
        a,b=sample()
        a["season"]=2026
        a["n_finished"]=0
        b["response"][0]["league"]["season"]=2026
        b["response"][1]["league"]["season"]=2026
        b["response"][0]["fixture"]["date"]="2026-08-17T14:00:00Z"
        b["response"][1]["fixture"]["date"]="2026-10-15T14:00:00Z"
        b["response"][0]["fixture"]["status"]["short"]="NS"
        b["response"][1]["fixture"]["status"]["short"]="NS"
        b["response"][0]["score"]["fulltime"]={"home":None,"away":None}
        b["response"][1]["score"]["fulltime"]={"home":None,"away":None}
        result=verify_payload(a,b)
        self.assertEqual(result["critical"],[])
        self.assertIn("IN_PROGRESS_SEASON_NOT_TRAINING_LABEL_COMPLETE",result["warnings"])

    def test_incomplete_pagination_blocks(self):
        a,b=sample()
        b["paging"]["total"]=2
        self.assertIn("INCOMPLETE_PAGINATION",verify_payload(a,b)["critical"])

if __name__=="__main__":
    unittest.main()
