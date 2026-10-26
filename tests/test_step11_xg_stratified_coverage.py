"""Step11 stratified PitchAPI selection, bounded capture safety (offline)."""
import copy
from datetime import datetime,timedelta,timezone
import unittest

from scripts.step11_xg_stratified_coverage import (
    SAMPLE_SIZE,PITCH_CALL_CAP,choose_stratified
)


def matches(count=60):
    start=datetime(2026,8,1,tzinfo=timezone.utc)
    out=[]
    for i in range(count):
        d=start+timedelta(days=i)
        out.append({"id":f"m_sample_{i:04d}",
          "time_utc":d.isoformat().replace("+00:00","Z"),
          "status":"finished",
          "home_team":{"id":"team_a","name":"Alpha"},
          "away_team":{"id":"team_b","name":"Beta"}})
    return out


class Step11StratifiedCoverage(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,1,tzinfo=timezone.utc)

    def test_deterministic_spread_over_months(self):
        first=choose_stratified(matches(),self.now)
        shuffled=list(reversed(matches()))
        again=choose_stratified(shuffled,self.now)
        self.assertEqual([x["id"] for x in first],[x["id"] for x in again])
        self.assertEqual(len(first),10)
        self.assertEqual(len({x["time_utc"][:10] for x in first}),10)
        self.assertEqual(first[0]["id"],"m_sample_0003")
        self.assertEqual(first[-1]["id"],"m_sample_0057")

    def test_exclude_prior_reviewed_three(self):
        excluded=[f"m_sample_{i:04d}" for i in (3,27,57)]
        samples=choose_stratified(matches(),self.now,excluded_match_ids=excluded)
        self.assertEqual(len(samples),SAMPLE_SIZE)
        self.assertTrue(all(s["id"] not in excluded for s in samples))

    def test_duplicate_provider_match_id_blocks(self):
        games=matches()
        games[8]["id"]=games[7]["id"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PITCH_PROVIDER_ID"):
            choose_stratified(games,self.now)

    def test_no_prematch_and_recent_matches(self):
        games=matches()
        games[0]["status"]="live"
        games[1]["time_utc"]=self.now.isoformat()
        games[2]["time_utc"]=(self.now-timedelta(hours=2)).isoformat()
        chosen=choose_stratified(games,self.now)
        self.assertEqual(len(chosen),10)
        self.assertTrue(all(x["id"] not in {games[i]["id"] for i in (0,1,2)}
                            for x in chosen))

    def test_missing_teams_is_rejected(self):
        games=matches()
        games[0]["home_team"]["id"]=None
        games[1]["away_team"]["name"]=""
        games[2]["home_team"]["id"]="team_b"
        chosen=choose_stratified(games,self.now)
        self.assertEqual(len(chosen),10)
        self.assertFalse({games[i]["id"] for i in (0,1,2)} &
                         {x["id"] for x in chosen})

    def test_not_enough_games_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"NOT_ENOUGH_ELIGIBLE"):
            choose_stratified(matches(9),self.now)

    def test_reject_malformed_naive_datetime(self):
        games=matches()
        games[0]["time_utc"]="2026-08-01T18:00:00"
        chosen=choose_stratified(games,self.now)
        self.assertEqual(len(chosen),10)
        self.assertNotIn(games[0],chosen)

    def test_no_automatic_review_or_fit_side_effects(self):
        self.assertEqual(SAMPLE_SIZE,10)
        self.assertEqual(PITCH_CALL_CAP,12)
        selected=choose_stratified(matches(),self.now)
        self.assertFalse(any("api_fixture_id" in item or
                             "training_allowed" in item for item in selected))


if __name__=="__main__":
    unittest.main()
