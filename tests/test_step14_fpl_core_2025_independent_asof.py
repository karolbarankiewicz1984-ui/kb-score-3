import unittest
from datetime import datetime, timezone

from scripts.step14_fpl_core_2025_independent_asof import (
    REPO, SOURCES, CandidateError, _read_teams, _read_matches,
    actions_witness, _qualify_target, _name, _utc,
)

class FPLCoreHistoricPreMatchTests(unittest.TestCase):
    def test_four_exact_source_revisions_no_2026_retrospective_head(self):
        self.assertEqual(len(SOURCES),4)
        self.assertEqual(len({x[0] for x in SOURCES}),4)
        self.assertTrue(all(_utc(x[3]) < _utc("2026-04-01T00:00:00Z") for x in SOURCES))
        self.assertEqual(REPO,"olbauday/FPL-Core-Insights")
    def test_actions_clock_server_witness_requires_exact_head_and_branch(self):
        sha, run, _, stamp = SOURCES[1]
        good={"workflow_runs":[{"id":run, "head_sha":sha, "head_branch":"main",
              "event":"schedule","created_at":stamp,"conclusion":"success"}]}
        check=lambda url:good
        p=actions_witness(sha,run,stamp,check)
        self.assertEqual(p["github_run_id"],run)
        self.assertFalse(p["provider_original_xg_first_published_verified"])
        bad={"workflow_runs":[dict(good["workflow_runs"][0],head_branch="old-testing")]}
        with self.assertRaisesRegex(CandidateError,"WITNESS_NOT_VERIFIED"):
            actions_witness(sha,run,stamp,lambda url:bad)
        changed={"workflow_runs":[dict(good["workflow_runs"][0],created_at="2026-10-29T00:00:00Z")]}
        with self.assertRaisesRegex(CandidateError,"WITNESS_NOT_VERIFIED"):
            actions_witness(sha,run,stamp,lambda url:changed)
    def test_old_source_filters_competitions_future_results_and_aliases(self):
        teams="code,id,name,fotmob_name\n1,1,Manchester City,Manchester City\n2,2,Wolves,Wolverhampton Wanderers\n"
        with self.assertRaisesRegex(CandidateError,"NOT_PREMIER_LEAGUE_20_TEAMS"):
            _read_teams(teams.encode())
        prior={1:"manchester city",2:"wolverhampton wanderers"}
        raw=("match_id,finished,kickoff_time,home_team,away_team,home_score,away_score,"
             "home_expected_goals_xg,away_expected_goals_xg\n"
             "25-26-prem-manchester-city-vs-wolves,True,2025-11-01T15:00:00,1,2,2,1,1.5,0.7\n"
             "25-26-efl-cup-future,True,2025-11-01T15:00:00,1,2,20,0,1,1\n"
             "25-26-prem-future,False,2025-11-15T15:00:00,1,2,,,,\n").encode()
        seen=_read_matches(raw,witness="2025-11-07T17:03:33Z",teams=prior)
        self.assertEqual(len(seen),1)
        self.assertAlmostEqual(list(seen.values())[0]["home_xg"],1.5)
        future=raw.replace(b"25-26-prem-future,False,2025-11-15T15:00:00,1,2,,,,",
                           b"25-26-prem-future,True,2025-11-15T15:00:00,1,2,0,1,0.4,0.7")
        with self.assertRaisesRegex(CandidateError,"FUTURE_OR_RECENT"):
            _read_matches(future,witness="2025-11-07T17:03:33Z",teams=prior)
    def test_no_prematch_form5_if_one_of_five_missing(self):
        names=["a","b","c","d","e","f","g","h"]
        games=[]
        prior={}
        for n in range(5):
            when=_utc(f"2025-10-{11+n:02d}T15:00:00Z")
            k=("a",names[n+1],when.isoformat())
            item={"home":"a","away":names[n+1],"ko":when,"key":k}
            games.append(item)
            prior[k]={"home_goals":2,"away_goals":1,"home_xg":1.1,"away_xg":0.4}
        for n in range(5):
            when=_utc(f"2025-10-{21+n:02d}T15:00:00Z")
            k=("h",names[n+1],when.isoformat())
            games.append({"home":"h","away":names[n+1],"ko":when,"key":k})
            prior[k]={"home_goals":1,"away_goals":0,"home_xg":0.8,"away_xg":0.3}
        target={"home":"a","away":"h","ko":_utc("2025-11-08T15:00:00Z"),
                "key":("a","h",_utc("2025-11-08T15:00:00Z").isoformat())}
        result=_qualify_target(target,_utc("2025-11-07T17:03:33Z"),prior,games+[target])
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["prematch_public_FORM5"]["home"]["gf_avg"],2.0)
        self.assertFalse(result["original_121_plus_38_eligible"])
        self.assertFalse(result["native_pitchapi_fixture_id_join_proven"])
        prior.pop(games[0]["key"])
        self.assertIsNone(_qualify_target(target,_utc("2025-11-07T17:03:33Z"),prior,games+[target]))

if __name__=="__main__":
    unittest.main()
