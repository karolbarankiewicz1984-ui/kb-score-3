"""No paid calls: upcoming real M0 last-five fetch selector unit tests."""
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from scripts.kb3_v3r_last5_priority import (
    prioritize_live_last5, future_m0_targets, LastFiveSelectionError,
)

NOW=datetime(2026,11,16,10,tzinfo=timezone.utc)
def stamp(v):return v.isoformat().replace("+00:00","Z")

def game(i,ko,home="t_A",away="t_B",status="finished"):
    return {"id":f"m_{i}","time_utc":stamp(ko),"home_team":{"id":home},
            "away_team":{"id":away},"status":status,
            "score_home":1 if status=="finished" else None,
            "score_away":0 if status=="finished" else None}

class V3RBackfillPriorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"m0.sqlite"
        with sqlite3.connect(self.db) as d:
            d.execute("""CREATE TABLE forecasts(
                 league TEXT,native_match_id TEXT,kickoff_utc TEXT,
                 home_team_id TEXT,away_team_id TEXT,captured_at_utc TEXT)""")
            d.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?)",(
                "ESP","m_future",stamp(NOW+timedelta(days=3)),
                "t_A","t_B",stamp(NOW-timedelta(hours=4))))
        self.history=[game(i,NOW-timedelta(days=12-i)) for i in range(10)]
        self.future=game("future",NOW+timedelta(days=3),status="scheduled")
        self.groups={("ESP","2026/2027"):self.history}
        self.catalog={"ESP":{"matches":self.history+[self.future]}}

    def test_true_recent_five_prioritized_and_missing_remain_queued(self):
        selected,report=prioritize_live_last5(
            self.groups,self.catalog,set(),db_path=self.db,now=NOW,limit=3)
        self.assertEqual([x[2]["id"] for x in selected],[
            "m_9","m_8","m_7"])
        self.assertEqual(report["missing_lastfive_unique_fixture_stat_candidates"],5)
        self.assertEqual(report["missing_after_selection_remains_queued"],2)
        self.assertTrue(report["no_missing_values_filled_with_zero"])
        self.assertEqual(report["native_live_verified_future_targets"],1)

    def test_known_data_are_not_refetched_but_missing_are(self):
        known={("ESP","m_9"),("ESP","m_7")}
        selected,report=prioritize_live_last5(
            self.groups,self.catalog,known,db_path=self.db,now=NOW,limit=9)
        self.assertEqual({x[2]["id"] for x in selected},
                         {"m_5","m_6","m_8"})
        self.assertEqual(report["already_observed_lastfive_fixture_stat_rows"],2)
        self.assertEqual(report["missing_after_selection_remains_queued"],0)

    def test_catalog_mismatch_quarantines_target_doesnt_stop_other_runs(self):
        bad={"ESP":{"matches":[{**self.future,"home_team":{"id":"other"}}]}}
        selected,report=prioritize_live_last5(
            self.groups,bad,set(),db_path=self.db,now=NOW)
        self.assertEqual(selected,[])
        self.assertEqual(report["real_future_m0_candidates"],1)
        self.assertEqual(report["target_identity_quarantine"],
                         {"LIVE_TARGET_IDENTITY_OR_STATUS_CHANGED":1})

    def test_no_current_catalog_is_nonfatal(self):
        rows,rep=prioritize_live_last5(
            self.groups,{},set(),db_path=self.db,now=NOW)
        self.assertEqual(rows,[])
        self.assertEqual(rep["target_identity_quarantine"],
                         {"NO_CURRENT_LIVE_LISTING":1})

    def test_no_m0_source_is_nonfatal(self):
        rows,rep=prioritize_live_last5(
            self.groups,self.catalog,set(),
            db_path=Path(self.tmp.name)/"missing",now=NOW)
        self.assertEqual(rows,[])
        self.assertEqual(rep["m0_source_state"],"NO_M0_DB")

    def test_future_match_is_not_stats_predecessor(self):
        later=game("later",NOW+timedelta(days=1))
        grp={("ESP","2026/2027"):self.history+[later]}
        rows,_=prioritize_live_last5(
            grp,self.catalog,set(),db_path=self.db,now=NOW,limit=10)
        self.assertNotIn("m_later",{m["id"] for _,_,m in rows})
        self.assertNotIn("m_future",{m["id"] for _,_,m in rows})

    def test_m0_source_never_includes_protected_eng(self):
        with sqlite3.connect(self.db) as d:
            d.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?)",(
                "ENG","protected",stamp(NOW+timedelta(days=2)),
                "t_X","t_Y",stamp(NOW-timedelta(hours=4))))
        with self.assertRaisesRegex(LastFiveSelectionError,"PROTECTED"):
            future_m0_targets(self.db,NOW)

if __name__=="__main__":
    unittest.main()
