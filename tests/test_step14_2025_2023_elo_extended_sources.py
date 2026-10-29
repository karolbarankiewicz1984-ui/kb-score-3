"""Real replay math tests and exact independent historic source checks."""
import unittest
from datetime import datetime,timezone
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import replay, EloReconstructionError
from scripts.step14_2025_expand_witnessed_form5_asof import ALL,EXTRA,ExtendedEvidenceError,source_at_version
from scripts.step14_fpl_core_2025_independent_asof import _utc,actions_witness
from src.kb3_features import EloParameters

class ThreeSeasonEloAndExtraHistoryTests(unittest.TestCase):
    def event(self,tag,clock,year,home,away,hscore,ascore):
        return {"fixture_id":tag, "kickoff":_utc(clock),
                "year":year,"home_id":home,"away_id":away,
                "season":f"{year}-{(year+1)%100:02d}",
                "partition":"TRAIN" if year<2025 else "VALIDATION",
                "gh":hscore,"ga":ascore}
    def test_three_year_interseason_retention_and_promoted_team_1500(self):
        data=[
            self.event("g23","2023-08-11T12:00:00Z",2023,"a","b",2,0),
            self.event("g24","2024-08-16T12:00:00Z",2024,"a","c",1,1),
            self.event("g25","2025-08-15T12:00:00Z",2025,"a","d",0,1),
        ]
        output,updates,ratings,counts=replay(data,expected_fixtures=3)
        self.assertEqual(len(output),3)
        self.assertEqual(updates["2023-24"],1)
        self.assertEqual(updates["2024-25"],1)
        self.assertEqual(updates["2025-26"],1)
        p=EloParameters()
        before_first=output[0]["research_only_retrospective_19_Elo_field_values"]
        self.assertEqual(before_first["home_elo"],1500)
        self.assertEqual(before_first["away_elo"],1500)
        self.assertEqual(before_first["away_prior_seasons_games_available"],0)
        second=output[1]["research_only_retrospective_19_Elo_field_values"]
        self.assertEqual(second["away_elo"],1500)
        self.assertEqual(second["home_elo_games_available"],1)
        self.assertEqual(second["home_prior_seasons_games_available"],1)
        self.assertNotEqual(second["home_elo"],1500)
        third=output[2]["research_only_retrospective_19_Elo_field_values"]
        self.assertEqual(third["away_elo"],1500)
        self.assertEqual(third["home_prior_seasons_games_available"],2)
        self.assertEqual(third["home_elo_games_available"],2)
        self.assertEqual(len(third),19)
        self.assertNotIn("gh",str(output))
        self.assertNotIn("score",str(output))
    def test_3h_lag_prevents_premature_score_use(self):
        events=[
            self.event("first","2025-10-01T14:00:00Z",2025,"a","b",3,0),
            self.event("second","2025-10-01T15:00:00Z",2025,"a","c",1,1),
        ]
        snapshots,*_=replay(events,expected_fixtures=2)
        second=snapshots[1]["research_only_retrospective_19_Elo_field_values"]
        self.assertEqual(second["home_elo_games_available"],0)
        self.assertEqual(second["home_elo"],1500)
    def test_source_expansion_is_pinned_and_distinct(self):
        self.assertEqual(len(ALL),14)
        self.assertEqual(len(EXTRA),10)
        self.assertEqual(len({s[0] for s in ALL}),14)
        timestamps=[_utc(x[3]) for x in ALL]
        self.assertEqual(timestamps,sorted(timestamps))
        self.assertTrue(all(x[2]>=10 for x in EXTRA))
        self.assertTrue(all(_utc(x[3])<_utc("2026-07-01T00:00:00Z") for x in EXTRA))
    def test_bad_actions_attestation_is_rejected(self):
        c,r,gw,when=EXTRA[0]
        with self.assertRaisesRegex(Exception,"WITNESS_NOT_VERIFIED"):
            actions_witness(c,r,when,lambda url:{"workflow_runs":[{
                "id":r,"head_sha":c,"head_branch":"other","event":"schedule",
                "created_at":when,"conclusion":"success"}]})

if __name__=="__main__":
    unittest.main()
