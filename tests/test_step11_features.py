"""Step11: synthetic temporal invariants, no API or private data."""
import sqlite3
import unittest
from src.kb3_features import build_features, FeatureSafetyError, digest

SCHEMA = """
CREATE TABLE fixtures (
 fixture_id INTEGER PRIMARY KEY, season_id INTEGER, home_team_id INTEGER,
 away_team_id INTEGER, kickoff_utc TEXT, status TEXT, goals_home_90 INTEGER,
 goals_away_90 INTEGER);
CREATE TABLE fixture_provider_map (
 provider_fixture_id TEXT, fixture_id INTEGER, match_quality TEXT,
 review_status TEXT, source_snapshot_id TEXT);
CREATE TABLE source_snapshots (
 snapshot_id TEXT, captured_at_utc TEXT, published_at_utc TEXT,
 availability_class TEXT);
CREATE TABLE match_stat_observations (
 fixture_id INTEGER,team_id INTEGER,numeric_value REAL,observed_at_utc TEXT,
 snapshot_id TEXT,metric TEXT);
"""

CUTOFF = "2024-08-11T17:00:00Z"


def sample(verified=True):
    db=sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    matches=[
      (1,1,10,20,"2024-08-01T18:00:00Z","FINISHED",2,1),
      (2,1,30,10,"2024-08-04T18:00:00Z","FINISHED",0,0),
      (3,1,20,30,"2024-08-07T18:00:00Z","FINISHED",1,0),
      (4,1,10,20,"2024-08-11T18:00:00Z","SCHEDULED",None,None),
      (5,1,20,30,"2024-08-12T18:00:00Z","FINISHED",99,0),
      (6,1,30,20,"2024-08-09T18:00:00Z","AWARDED",99,0)]
    db.executemany("INSERT INTO fixtures VALUES (?,?,?,?,?,?,?,?)",matches)
    for i in (1,2,3,5,6):
        published={
          1:"2024-08-01T22:00:00Z",
          2:"2024-08-04T22:00:00Z",
          3:"2024-08-07T22:00:00Z",
          5:"2024-08-12T22:00:00Z",
          6:"2024-08-09T22:00:00Z"}[i]
        captured="2024-08-08T12:00:00Z" if i<4 else "2024-08-14T12:00:00Z"
        db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?)",(
          "s"+str(i),captured,published if verified else None,
          "VERIFIED_PREMATCH" if verified else "RETROSPECTIVE"))
        db.execute("INSERT INTO fixture_provider_map VALUES (?,?,?,?,?)",(
          "external"+str(i),i,"STRICT","APPROVED","s"+str(i)))
    return db


class Step11Features(unittest.TestCase):
    def test_verified_history_and_elo(self):
        with sample() as db:
            x=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(x["accepted_predecessor_count"],3)
        self.assertEqual(x["features"]["home_all_5_n"],2)
        self.assertEqual(x["features"]["away_all_5_n"],2)
        self.assertEqual(x["features"]["home_all_5_points_avg"],2)
        self.assertEqual(x["features"]["away_all_5_points_avg"],1.5)
        self.assertNotEqual(x["features"]["home_elo"],1500)
        self.assertFalse(x["training_allowed"])
        self.assertEqual(x["availability_class"],"NOT_VERIFIED")

    def test_no_provenance_means_no_strict_hist(self):
        with sample(False) as db:
            a=build_features(db,4,cutoff_utc=CUTOFF,mode="verified")
            b=build_features(db,4,cutoff_utc=CUTOFF,mode="replay")
        self.assertEqual(a["accepted_predecessor_count"],0)
        self.assertEqual(a["features"]["home_elo"],1500)
        self.assertIsNone(a["features"]["home_all_5_gf_avg"])
        self.assertEqual(b["accepted_predecessor_count"],3)
        self.assertEqual(b["availability_class"],"RETROSPECTIVE")

    def test_future_game_and_target_result_no_leak(self):
        with sample() as db:
            a=build_features(db,4,cutoff_utc=CUTOFF)
            db.execute("UPDATE fixtures SET status='FINISHED', goals_home_90=99,goals_away_90=0 WHERE fixture_id=4")
            db.execute("UPDATE fixtures SET goals_home_90=999 WHERE fixture_id=5")
            b=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(a,b)

    def test_expired_publication_is_excluded(self):
        with sample() as db:
            db.execute("UPDATE source_snapshots SET published_at_utc='2024-09-01T00:00:00Z' WHERE snapshot_id='s3'")
            x=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(x["accepted_predecessor_count"],2)

    def test_no_cutoff_at_or_after_kickoff(self):
        with sample() as db:
            for ts in ("2024-08-11T18:00:00Z","2025-01-01T00:00:00Z"):
                with self.assertRaisesRegex(FeatureSafetyError,"CUTOFF"):
                    build_features(db,4,cutoff_utc=ts)
            with self.assertRaisesRegex(FeatureSafetyError,"NAIVE"):
                build_features(db,4,cutoff_utc="2024-08-11T17:00:00")

    def test_review_id_not_promoted(self):
        with sample() as db:
            db.execute("UPDATE fixture_provider_map SET match_quality='REVIEW',review_status='PENDING' WHERE fixture_id=1")
            x=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(x["accepted_predecessor_count"],2)

    def test_xg_real_missing_or_late(self):
        with sample() as db:
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?)",
                (1,10,1.75,"2024-08-01T22:30:00Z","s1","xG"))
            db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?)",(
                "late","2024-08-15T12:00:00Z","2024-08-15T10:00:00Z","VERIFIED_PREMATCH"))
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?)",
                (2,10,99,"2024-08-15T11:00:00Z","late","xg"))
            x=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(x["features"]["home_all_5_xg_n"],1)
        self.assertEqual(x["features"]["home_all_5_xg_avg"],1.75)
        self.assertIsNone(x["features"]["home_all_5_xga_avg"])
        self.assertTrue(x["missing_flags"]["home_all_5_xg"])

    def test_conflicting_xg_fails_closed(self):
        with sample() as db:
            for value in (1.0,2.0):
                db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?)",
                    (1,10,value,"2024-08-01T22:30:00Z","s1","xg"))
            with self.assertRaisesRegex(FeatureSafetyError,"CONFLICTING_XG"):
                build_features(db,4,cutoff_utc=CUTOFF)

    def test_awarded_not_counted(self):
        with sample() as db:
            x=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(x["excluded"]["awarded"],1)

    def test_same_team_at_same_time_fails(self):
        with sample() as db:
            db.execute("UPDATE fixtures SET kickoff_utc='2024-08-07T18:00:00Z' WHERE fixture_id=2")
            db.execute("UPDATE source_snapshots SET published_at_utc='2024-08-07T22:00:00Z' WHERE snapshot_id='s2'")
            with self.assertRaisesRegex(FeatureSafetyError,"SIMULTANEOUSLY"):
                build_features(db,4,cutoff_utc=CUTOFF)

    def test_repeatable_sha(self):
        with sample() as db:
            a=build_features(db,4,cutoff_utc=CUTOFF)
            b=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(a,b)
        self.assertEqual(a["sha256"],digest({k:v for k,v in a.items() if k!="sha256"}))


if __name__=="__main__":
    unittest.main()
