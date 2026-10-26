"""Offline Step 09 checks: negative cases, idempotence and crash recovery."""
import copy
import datetime as dt
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.step09_import_history import (
    ImportConflict, SimulatedInterruption, canonical_bytes,
    import_rows, parse_rows, sha256,
)
from src.kb3_storage import connect

def example_payload(n=4):
    response=[]
    for i in range(n):
        day=(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=i))
        response.append({
            "fixture":{"id":70000+i,"date":day.isoformat().replace("+00:00","Z"),
                       "status":{"short":"FT"}},
            "league":{"id":39,"season":2024},
            "teams":{"home":{"id":10+(i%4),"name":"Home %s"%(i%4)},
                     "away":{"id":20+(i%4),"name":"Away %s"%(i%4)}},
            "goals":{"home":2,"away":1},
            "score":{"fulltime":{"home":2,"away":1}},
        })
    return {"errors":[],"paging":{"total":1},"response":response}

class Step09Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"pilot.sqlite3"
        self.payload=example_payload()
        self.rows=parse_rows(self.payload,expected_count=4)
        self.hash=sha256(canonical_bytes(self.payload))

    def test_expected_count_and_unique_ids(self):
        self.assertEqual(len(self.rows),4)
        with self.assertRaisesRegex(ImportConflict,"COUNT_MISMATCH"):
            parse_rows(self.payload,expected_count=380)
        broken=copy.deepcopy(self.payload)
        broken["response"][1]["fixture"]["id"]=70000
        with self.assertRaisesRegex(ImportConflict,"DUPLICATE"):
            parse_rows(broken,expected_count=4)

    def test_api_errors_pagination_and_season_mismatch(self):
        for patch,error in [
            (lambda v:v.update(errors={"key":"unauthorized"}),"API_ERRORS"),
            (lambda v:v.update(paging={"total":2}),"PAGINATED"),
            (lambda v:v["response"][0]["league"].update(season=2023),"LEAGUE_SEASON")]:
            broken=copy.deepcopy(self.payload)
            patch(broken)
            with self.assertRaisesRegex(ImportConflict,error):
                parse_rows(broken,expected_count=4)

    def test_bad_kickoff_and_team_ids_blocked(self):
        broken=copy.deepcopy(self.payload)
        broken["response"][0]["fixture"]["date"]="invalid"
        with self.assertRaisesRegex(ImportConflict,"INVALID_KICKOFF"):
            parse_rows(broken,expected_count=4)
        broken=copy.deepcopy(self.payload)
        broken["response"][0]["teams"]["away"]["id"]=broken["response"][0]["teams"]["home"]["id"]
        with self.assertRaisesRegex(ImportConflict,"HOME_EQUALS"):
            parse_rows(broken,expected_count=4)

    def test_regulation_score_never_uses_extra_time_totals(self):
        broken=copy.deepcopy(self.payload)
        broken["response"][0]["fixture"]["status"]["short"]="AET"
        broken["response"][0]["goals"]={"home":4,"away":2}
        broken["response"][0]["score"]["fulltime"]={"home":2,"away":2}
        r=parse_rows(broken,expected_count=4)
        self.assertEqual((r[0]["goals_home_90"],r[0]["goals_away_90"]),(2,2))
        broken["response"][0]["score"]["fulltime"]={"home":None,"away":None}
        with self.assertRaisesRegex(ImportConflict,"FINISHED_WITHOUT_90MIN_RESULT"):
            parse_rows(broken,expected_count=4)

    def test_missing_finished_score_is_error(self):
        broken=copy.deepcopy(self.payload)
        broken["response"][0]["score"]["fulltime"]={"home":None,"away":None}
        broken["response"][0]["goals"]={"home":None,"away":None}
        with self.assertRaisesRegex(ImportConflict,"FINISHED_WITHOUT_90MIN_RESULT"):
            parse_rows(broken,expected_count=4)

    def test_repeat_import_adds_zero_fixtures(self):
        a=import_rows(self.db,self.rows,self.hash)
        b=import_rows(self.db,self.rows,self.hash)
        self.assertEqual((a["inserted"],a["reused"],a["total"]),(4,0,4))
        self.assertEqual((b["inserted"],b["reused"],b["total"]),(0,4,4))
        with connect(self.db) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0],4)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fixture_provider_map").fetchone()[0],4)
            self.assertEqual(c.execute("SELECT DISTINCT availability_class FROM source_snapshots").fetchall(),[("RETROSPECTIVE",)])

    def test_resume_after_real_commits(self):
        with self.assertRaises(SimulatedInterruption):
            import_rows(self.db,self.rows,self.hash,stop_after=2)
        with connect(self.db) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0],2)
        r=import_rows(self.db,self.rows,self.hash)
        self.assertEqual((r["inserted"],r["reused"],r["total"]),(2,2,4))

    def test_kickoff_change_requires_review_not_new_fixture(self):
        import_rows(self.db,self.rows,self.hash)
        changed=copy.deepcopy(self.rows)
        changed[0]["kickoff_utc"]="2025-01-01T15:00:00Z"
        with self.assertRaisesRegex(ImportConflict,"REVIEW_REQUIRED"):
            import_rows(self.db,changed,self.hash)
        with connect(self.db) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0],4)

    def test_unapproved_mapping_never_promoted(self):
        # Existing REVIEW mapping is not allowed to become an approved fixture.
        from src.kb3_storage import initialize
        initialize(self.db)
        with connect(self.db) as c:
            c.execute("INSERT INTO providers(name,created_utc) VALUES ('API-Football','2026-10-26T00:00:00Z')")
            c.execute("""INSERT INTO fixture_provider_map
              (provider_id,provider_fixture_id,match_quality,review_status)
              VALUES(1,'70000','REVIEW','PENDING')""")
        with self.assertRaisesRegex(ImportConflict,"UNAPPROVED"):
            import_rows(self.db,self.rows,self.hash)

    def test_conflicting_result_fails_without_rewrite(self):
        import_rows(self.db,self.rows,self.hash)
        changed=copy.deepcopy(self.rows)
        changed[0]["goals_home_90"]=3
        with self.assertRaisesRegex(ImportConflict,"REVIEW_REQUIRED"):
            import_rows(self.db,changed,self.hash)
        with connect(self.db) as c:
            self.assertEqual(c.execute("SELECT goals_home_90 FROM fixtures ORDER BY fixture_id LIMIT 1").fetchone()[0],2)

if __name__=="__main__":
    unittest.main()
