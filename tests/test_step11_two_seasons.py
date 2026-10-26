"""Step11: integrated two-season import + Elo continuity, entirely offline."""
import tempfile
from pathlib import Path
import unittest

from scripts.step09_import_history import (
    import_rows,parse_rows,sha256,canonical_bytes
)
from src.kb3_storage import connect
from src.kb3_features import build_features,EloParameters


def make_payload(season, provider_offset):
    fixtures=[]
    for i,(h,a) in enumerate(((10,20),(10,30),(20,30))):
        fixtures.append({
          "fixture":{"id":provider_offset+i,
                     "date":f"{season}-08-{1+i:02d}T18:00:00Z",
                     "status":{"short":"FT"}},
          "league":{"id":39,"season":season},
          "teams":{"home":{"id":h,"name":f"Team {h}"},
                   "away":{"id":a,"name":f"Team {a}"}},
          "goals":{"home":2,"away":1},
          "score":{"fulltime":{"home":2,"away":1}}
        })
    return {"errors":[],"paging":{"total":1},"response":fixtures}


class Step11IntegratedImport(unittest.TestCase):
    def test_two_seasons_share_teams_not_fixture_ids(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture-history.sqlite3"
            for year,offset in ((2023,33000),(2024,44000)):
                payload=make_payload(year,offset)
                rows=parse_rows(payload,expected_count=3,season=year)
                h=sha256(canonical_bytes(payload))
                one=import_rows(path,rows,h,season=year)
                two=import_rows(path,rows,h,season=year)
                self.assertEqual((one["inserted"],two["reused"]),(3,3))
                self.assertEqual(one["snapshot_id"].split("-")[4],str(year))
            with connect(path) as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0],6)
                self.assertEqual(c.execute("SELECT COUNT(*) FROM teams").fetchone()[0],3)
                self.assertEqual(c.execute("SELECT COUNT(*) FROM seasons").fetchone()[0],2)
                f=c.execute("""
                    SELECT f.fixture_id FROM fixtures f JOIN seasons s ON f.season_id=s.season_id
                    WHERE s.start_year=2024 ORDER BY f.kickoff_utc LIMIT 1
                """).fetchone()[0]
                replay=build_features(c,f,cutoff_utc="2024-08-01T17:00:00Z",mode="replay")
                strict=build_features(c,f,cutoff_utc="2024-08-01T17:00:00Z",mode="verified")
                reset=build_features(c,f,cutoff_utc="2024-08-01T17:00:00Z",mode="replay",
                                     elo_params=EloParameters(season_retention=0))
            self.assertEqual(replay["accepted_predecessor_count"],3)
            self.assertEqual(strict["accepted_predecessor_count"],0)
            self.assertEqual(replay["features"]["home_prior_seasons_games_available"],2)
            self.assertNotEqual(replay["features"]["home_elo"],reset["features"]["home_elo"])
            self.assertEqual(replay["availability_class"],"RETROSPECTIVE")
            self.assertFalse(replay["training_allowed"])

    def test_rejects_season_mismatch(self):
        p=make_payload(2023,33000)
        from scripts.step09_import_history import ImportConflict
        with self.assertRaisesRegex(ImportConflict,"LEAGUE_SEASON_MISMATCH"):
            parse_rows(p,expected_count=3,season=2024)


if __name__=="__main__":
    unittest.main()
