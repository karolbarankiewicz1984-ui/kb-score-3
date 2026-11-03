"""Provider-native IDs prevent joining PitchAPI xG to wrong API-Football match."""
from datetime import datetime,timezone,timedelta
import copy
import unittest
from pitch_pair_fixtures import stats

from src.kb3_pitch_native import check_season,verify_native_shots


def sample(season="2026/2027",n=380):
    year=int(season[:4])
    rows=[]
    for i in range(n):
        mid=f"m_{i:06d}"
        rows.append({
            "id":mid,
            "time_utc":(f"{year}-09-01T16:00:00Z" if i==0 else
                        f"{year+1}-04-01T15:00:00Z"),
            "status":"finished" if i==0 else "not_started",
            "home_team":{"id":f"t_{i*2:06d}","name":f"Home {i}"},
            "away_team":{"id":f"t_{i*2+1:06d}","name":f"Away {i}"},
            "score_home":2 if i==0 else None,
            "score_away":1 if i==0 else None})
    return rows


def feed(mid="m_000000",home="t_000000",away="t_000001",xg=0.6):
    return {"data":{"match_id":mid,
                    "periods":[{"period":"All","shots":[{"id":"s_1","team_id":home,"expected_goals":xg},
                                         {"id":"s_2","team_id":away,"expected_goals":0.3}]}]}}


class NativePitchTests(unittest.TestCase):
    def test_same_id_for_results_and_future_fixtures(self):
        v=check_season(sample(),"2026/2027",require_upcoming=True)
        self.assertEqual(v["fixtures"],380)
        self.assertEqual(v["status_counts"],{"finished":1,"not_started":379})
        self.assertFalse(v["cross_provider_join_needed"])
        self.assertFalse(v["training_allowed"])

    def test_duplicate_match_rejected(self):
        s=sample()
        s[1]["id"]=s[0]["id"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            check_season(s,"2026/2027")

    def test_missing_fixture_rejected(self):
        with self.assertRaisesRegex(ValueError,"SEASON_INCOMPLETE"):
            check_season(sample(n=379),"2026/2027")

    def test_legacy_finished_only_cannot_prove_upcoming(self):
        s=sample()
        for x in s:
            x["status"]="finished";x["score_home"]=0;x["score_away"]=0
        with self.assertRaisesRegex(ValueError,"NO_UPCOMING"):
            check_season(s,"2026/2027",require_upcoming=True)

    def test_unfinished_score_is_not_prematch(self):
        s=sample()
        s[1]["score_home"]=1
        with self.assertRaisesRegex(ValueError,"FUTURE_CONTAINS_FINAL_SCORE"):
            check_season(s,"2026/2027")

    def test_malformed_team_id_rejected(self):
        s=sample();s[0]["away_team"]["id"]="api_football_999"
        with self.assertRaisesRegex(ValueError,"TEAM_ID"):
            check_season(s,"2026/2027")

    def test_match_different_season_rejected(self):
        s=sample()
        s[1]["time_utc"]="2029-04-01T15:00:00Z"
        with self.assertRaisesRegex(ValueError,"OUTSIDE_SEASON"):
            check_season(s,"2026/2027")

    def test_native_xg_sum_and_same_match(self):
        x=verify_native_shots(sample()[0],feed(),observed_at_utc="2026-10-26T16:00:00Z",stats_payload=stats("m_000000","t_000000","t_000001",.6,.3))
        self.assertEqual(x["xg_home"],0.6)
        self.assertEqual(x["xg_away"],0.3)
        self.assertIsNone(x["source_provider_published_at_utc"])
        self.assertFalse(x["training_allowed"])

    def test_mismatched_match_id_rejected(self):
        with self.assertRaisesRegex(ValueError,"FIXTURE_ID_MISMATCH"):
            verify_native_shots(sample()[0],feed(mid="m_999999"),
                                observed_at_utc="2026-10-26T16:00:00Z",stats_payload=stats("m_000000","t_000000","t_000001",.6,.3))

    def test_shots_before_match_blocked(self):
        with self.assertRaisesRegex(ValueError,"NOT_AFTER_MATCH"):
            verify_native_shots(sample()[0],feed(),
                                observed_at_utc="2026-09-01T16:30:00Z")

    def test_future_match_shots_blocked(self):
        with self.assertRaisesRegex(ValueError,"FINISHED_MATCH"):
            verify_native_shots(sample()[1],feed(mid="m_000001"),
                                observed_at_utc="2027-06-01T16:00:00Z")

    def test_incomplete_shots_retains_null(self):
        bad=feed()
        bad["data"]["periods"][0]["shots"][0]["expected_goals"]=None
        result=verify_native_shots(sample()[0],bad,
                                   observed_at_utc="2026-10-26T16:00:00Z",stats_payload=stats("m_000000","t_000000","t_000001",.6,.3))
        self.assertIsNone(result["xg_home"])
        self.assertIsNone(result["xg_away"])
        self.assertNotEqual(result["shot_state"],"COMPLETE_SHOT_XG")

    def test_deterministic_payload_digest(self):
        x=sample()
        a=check_season(x,"2026/2027")
        b=check_season(list(reversed(x)),"2026/2027")
        self.assertEqual(a["match_digest_sha256"],b["match_digest_sha256"])

if __name__=="__main__":
    unittest.main()
