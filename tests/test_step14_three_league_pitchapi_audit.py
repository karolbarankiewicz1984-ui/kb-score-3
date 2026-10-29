import tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.step14_three_league_pitchapi_actual_audit import (
    select_three,coverage,collect,ThreeLeagueError,LEAGUES,LIMIT)
NOW=datetime(2026,10,29,12,tzinfo=timezone.utc)
def season(year,num,title):
    a=[]
    for i in range(num):
        ko=datetime(year,8,1,tzinfo=timezone.utc)+timedelta(hours=24*i)
        status="finished" if ko<NOW-timedelta(hours=3) else "not_started"
        if year==2025:status="finished"
        a.append({"id":"m_"+format(i+1+(year-2025)*800,"06d"),
           "time_utc":ko.isoformat().replace("+00:00","Z"),
           "status":status,
           "score_home":1 if status=="finished" else None,
           "score_away":0 if status=="finished" else None,
           "home_team":{"id":"t_"+format(1+i%20,"06d"),"name":"H"+str(i%20)},
           "away_team":{"id":"t_"+format(1+(i+1)%20,"06d"),"name":"H"+str((i+1)%20)}})
    return a
class ThreeLeagueAudit(unittest.TestCase):
 def test_three_exact_not_premier_league(self):
    r={"leagues":[{"id":"l_"+format(i+1,"06d"),
       "name":title,"country_code":country,
       "seasons":["2025/2026","2026/2027"]}
       for i,(country,aliases,n,title) in enumerate(LEAGUES)]}
    s=select_three(r)
    self.assertEqual(len(s),3)
    self.assertEqual({x[1] for x in s},{"ESP","ITA","GER"})
    self.assertTrue(all(x[1]!="ENG" for x in s))
 def test_missing_historic_year_fails(self):
    with self.assertRaisesRegex(ThreeLeagueError,"UNAVAILABLE"):
        select_three({"leagues":[{"id":"l_000001","name":"LaLiga",
            "country_code":"ESP","seasons":["2026/2027"]}]})
 def test_no_test_premier_league_substitution(self):
    with self.assertRaisesRegex(ThreeLeagueError,"UNAVAILABLE"):
        select_three({"leagues":[{"id":"l_000001","name":"Premier League",
            "country_code":"ENG","seasons":["2026/2027","2025/2026"]}]})
 def test_realistic_full_year_match_graph_and_future(self):
    for country,aliases,n,title in LEAGUES:
        try:
            c,sample=coverage(season(2026,n,title),season(2025,n,title),NOW,n,title)
        except Exception as e: self.fail(str(e))
        self.assertEqual(c["fixtures_this_season"],n)
        self.assertEqual(c["previous_season_finished_fixtures"],n)
        self.assertEqual(c["next_four_upcoming_test_targets"],4)
        self.assertGreater(c["target_team_sides_with_prior_15_of_15"],0)
        self.assertEqual(c["provider_original_published_at"],None)
        self.assertEqual(sample["status"],"finished")
 def test_same_team_wrong_kickoff_forbidden(self):
    items=season(2026,380,"LaLiga")
    items[0]["away_team"]=items[0]["home_team"]
    with self.assertRaises(ValueError):
        coverage(items,season(2025,380,"LaLiga"),NOW,380,"LaLiga")
 def test_wrong_finished_score_forbidden(self):
    items=season(2026,306,"Bundesliga")
    items[0]["score_home"]=None
    with self.assertRaises(ValueError):
        coverage(items,season(2025,306,"Bundesliga"),NOW,306,"Bundesliga")
 def test_missing_existing_secret_fails_without_directory(self):
    with tempfile.TemporaryDirectory() as path:
        target=Path(path)/"audit"
        with self.assertRaisesRegex(ThreeLeagueError,"SECRET_MISSING"):
            collect(dest=target,key="",public_pem="")
        self.assertFalse(target.exists())
 def test_budget_and_league_order(self):
    self.assertEqual(LIMIT,13)
    self.assertEqual([x[0] for x in LEAGUES],["ESP","ITA","GER"])
if __name__=="__main__":unittest.main()
