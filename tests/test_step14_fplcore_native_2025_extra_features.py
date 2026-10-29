"""Strict negative unit tests for 18 actual native fixture identities and alternative source."""
import unittest
from scripts.step14_fplcore_native_2025_crosswalk_semantics import (
   NativeJoinError,select_native_catalog,exact_native_join)
from scripts.step14_fplcore_2025_extended_field_recovery import (
   _team_window,_candidate, CoverageError)
from scripts.step14_fpl_core_2025_independent_asof import _utc

class RealJoinAndRecoveredFieldsTests(unittest.TestCase):
    def test_catalog_competition_identity_not_arbitrary_english_team(self):
        cat={"leagues":[{"id":"l_1","name":"Premier League","country_code":"ENG","seasons":["2025/2026"]},
                        {"id":"l_2","name":"Premier League","country_code":"SCO","seasons":["2025/2026"]}]}
        self.assertEqual(select_native_catalog(cat),"l_1")
        with self.assertRaisesRegex(NativeJoinError,"NO_UNIQUE"):
            select_native_catalog({"leagues":[cat["leagues"][0],cat["leagues"][0]]})
    def test_form_windows_do_not_backfill_missing_predecessor_with_future(self):
        games=[]
        past={}
        for k in range(10):
            dt=_utc(f"2025-10-{k+1:02d}T15:00:00Z")
            item={"home":"a","away":str(k),"ko":dt,"key":("a",str(k),dt.isoformat())}
            games.append(item)
            past[item["key"]]={"home_goals":1,"away_goals":0,"home_xg":0.9,"away_xg":0.5}
        target={"home":"a","away":"b","ko":_utc("2025-11-08T15:00:00Z")}
        five=_team_window(target,"a","all",5,games,past,"2025-11-07T17:03:33Z")
        self.assertEqual(five["n"],5)
        self.assertEqual(five["points_avg"],3)
        self.assertFalse(five["history_missing"])
        self.assertEqual(five["xg_n"],5)
        one_missing=dict(past)
        one_missing.pop(games[-1]["key"])
        blocked=_team_window(target,"a","all",5,games,one_missing,"2025-11-07T17:03:33Z")
        self.assertIsNone(blocked["gf_avg"])
        self.assertIsNone(blocked["xg_n"])
        self.assertFalse(blocked["source_asof_complete"])
        venue=_team_window(target,"a","venue",15,games,past,"2025-11-07T17:03:33Z")
        self.assertTrue(venue["history_missing"])
    def test_unknown_elo_not_invented_from_partial_league_history(self):
        games=[]
        before={}
        for n in range(5):
            time=_utc(f"2025-10-{n+11:02d}T15:00:00Z")
            for team,other in (("a",f"x{n}"),("b",f"y{n}")):
                key=(team,other,time.isoformat())
                games.append({"home":team,"away":other,"ko":time,"key":key})
                before[key]={"home_goals":2,"away_goals":1,"home_xg":1.5,"away_xg":0.5}
        target={"home":"a","away":"b","ko":_utc("2025-11-08T15:00:00Z")}
        report=_candidate(target,games+[dict(target,key=("a","b",target["ko"].isoformat()))],
                         before,
                         {"witness":"2025-11-07T17:03:33Z","commit":"test"})
        self.assertEqual(len(report["research_features_not_native_PitchAPI"]),121)
        self.assertEqual(len(report["research_missing_flags_not_native_PitchAPI"]),38)
        self.assertIsNone(report["research_features_not_native_PitchAPI"]["elo_home_minus_away"])
        self.assertIsNone(report["research_features_not_native_PitchAPI"]["home_elo"])
        self.assertEqual(report["research_features_not_native_PitchAPI"]["home_all_5_gf_avg"],2)
        self.assertFalse(report["full_original_pit_eligible"])

if __name__=="__main__":
    unittest.main()
