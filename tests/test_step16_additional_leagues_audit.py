"""Offline safety tests for new league audit. Never call real PitchAPI on PR."""
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from scripts.step16_additional_leagues_audit import (
    CANDIDATES,match_catalog,compact_season,LeagueAuditError,audit,
    SCHEMA,MAX_CALLS,digest)

NOW=datetime.now(timezone.utc)
def stamp(x):
    return x.isoformat().replace("+00:00","Z")
def row(i,season,current):
    ko=NOW-timedelta(days=45-i) if (not current or i<22) else NOW+timedelta(days=3)
    played=not current or i<22
    return {"id":"m_"+str(i+int(season[:4])*1000),
            "time_utc":stamp(ko),
            "status":"finished" if played else "scheduled",
            "score_home":2 if played else None,"score_away":1 if played else None,
            "home_team":{"id":"t_"+str(i%14+1)},
            "away_team":{"id":"t_"+str((i+1)%14+1)}}
class AuditTests(unittest.TestCase):
    def test_exact_alias_not_protected_league(self):
        items=[{"country_code":c,"name":title,"id":"l_"+c,
                "seasons":["2025/2026","2026/2027"],"is_free":True}
               for c,title,_ in CANDIDATES]
        items.append({"country_code":"ENG","name":"Premier League",
                      "id":"l_PROTECTED","seasons":["2025/2026","2026/2027"]})
        found=match_catalog({"leagues":items})
        self.assertEqual(len(found),7)
        self.assertTrue(all(x["catalog_both_seasons"] for x in found))
        self.assertNotIn("l_PROTECTED",[x.get("provider_league_id") for x in found])
    def test_missing_both_seasons_not_assumed_available(self):
        found=match_catalog({"leagues":[{"country_code":"FRA","name":"Ligue 1",
                                          "id":"l_FRA","seasons":["2025/2026"]}]})
        self.assertFalse(found[0]["catalog_both_seasons"])
        self.assertFalse(found[1]["catalog_both_seasons"])
    def test_duplicate_country_name_rejected(self):
        leagues=[{"country_code":"FRA","name":"Ligue 1","id":a,
                  "seasons":["2025/2026","2026/2027"]} for a in ("l_a","l_b")]
        with self.assertRaises(LeagueAuditError):
            match_catalog({"leagues":leagues})
    def test_current_scores_must_be_null_for_future(self):
        x=[row(i,"2026/2027",True) for i in range(24)]
        self.assertTrue(compact_season(x,"2026/2027",True)["valid"])
        x[-1]["score_home"]=0
        self.assertFalse(compact_season(x,"2026/2027",True)["valid"])
    def test_previous_must_all_be_finished(self):
        x=[row(i,"2025/2026",False) for i in range(24)]
        self.assertTrue(compact_season(x,"2025/2026",False)["valid"])
        x[-1]["status"]="postponed"
        self.assertFalse(compact_season(x,"2025/2026",False)["valid"])
    def test_no_provider_api_without_catalog(self):
        class Bad:
            class leagues:
                @staticmethod
                def list():raise ValueError("offline")
        with self.assertRaises(LeagueAuditError):
            audit(Bad(),observation_time=NOW)
    def test_digest_stable(self):
        self.assertEqual(digest({"a":1,"b":2}),digest({"b":2,"a":1}))
        self.assertEqual(MAX_CALLS,29)
    def test_candidate_fixture_audit_never_calls_premier_league(self):
        calls=[]
        class Leagues:
            def list(self):
                calls.append(("catalog",))
                return {"leagues":[{"country_code":c,"name":title,
                    "id":"l_"+c,"seasons":["2025/2026","2026/2027"],"is_free":True}
                    for c,title,_ in CANDIDATES]+[{"country_code":"ENG",
                    "name":"Premier League","id":"l_PROTECTED",
                    "seasons":["2025/2026","2026/2027"]}]}
            def matches(self,lid,*,season,status=None):
                calls.append((lid,season,status))
                if lid=="l_PROTECTED":raise ValueError("protected data accessed")
                return {"matches":[row(i,season,season=="2026/2027")
                                   for i in range(24)]}
        class Matches:
            def shots(self,mid):return {"match_id":mid}
            def stats(self,mid):return {"match_id":mid}
        class Client:
            leagues=Leagues()
            matches=Matches()
        with patch("scripts.step16_additional_leagues_audit.parse_native_shots",return_value=(1.,1.,3,3)),patch("scripts.step16_additional_leagues_audit.parse_native_team_stats",return_value=(1.,1.)):
            result=audit(Client(),observation_time=NOW)
        self.assertEqual(result["schema"],SCHEMA)
        self.assertLessEqual(result["provider_calls"],MAX_CALLS)
        self.assertTrue(all(x[0]!="l_PROTECTED" for x in calls))
        self.assertFalse(result["premier_league_2026_27_test_results_requested"])
        self.assertFalse(result["new_leagues_live_pipeline_enabled"])
        self.assertEqual(result["verified_full_1xg_pair_count"],7)
if __name__=="__main__":unittest.main()
