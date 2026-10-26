"""Step11: synthetic temporal invariants, no API or private data."""
import sqlite3
import unittest
from src.kb3_features import build_features, FeatureSafetyError, EloParameters, digest

SCHEMA = """
CREATE TABLE seasons (season_id INTEGER PRIMARY KEY, competition_id INTEGER, start_year INTEGER);
CREATE TABLE providers (provider_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE fixtures (
 fixture_id INTEGER PRIMARY KEY, season_id INTEGER, home_team_id INTEGER,
 away_team_id INTEGER, kickoff_utc TEXT, status TEXT, goals_home_90 INTEGER,
 goals_away_90 INTEGER, updated_utc TEXT, result_source TEXT);
CREATE TABLE fixture_provider_map (
 provider_id INTEGER, provider_fixture_id TEXT, fixture_id INTEGER, match_quality TEXT,
 review_status TEXT, source_snapshot_id TEXT);
CREATE TABLE source_snapshots (
 provider_id INTEGER, snapshot_id TEXT, captured_at_utc TEXT, published_at_utc TEXT,
 availability_class TEXT);
CREATE TABLE match_stat_observations (
 fixture_id INTEGER,team_id INTEGER,provider_id INTEGER,numeric_value REAL,observed_at_utc TEXT,
 snapshot_id TEXT,metric TEXT);
"""

CUTOFF = "2024-08-11T17:00:00Z"


def sample(verified=True):
    db=sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    db.executemany("INSERT INTO providers VALUES (?,?)",
                   [(1,"API-Football"),(2,"PitchAPI")])
    db.executemany("INSERT INTO seasons VALUES (?,?,?)",
                   [(1,100,2024),(2,100,2023),(3,200,2023),(4,100,2025)])
    matches=[
      (1,1,10,20,"2024-08-01T18:00:00Z","FINISHED",2,1),
      (2,1,30,10,"2024-08-04T18:00:00Z","FINISHED",0,0),
      (3,1,20,30,"2024-08-07T18:00:00Z","FINISHED",1,0),
      (4,1,10,20,"2024-08-11T18:00:00Z","SCHEDULED",None,None),
      (5,1,20,30,"2024-08-12T18:00:00Z","FINISHED",99,0),
      (6,1,30,20,"2024-08-09T18:00:00Z","AWARDED",99,0)]
    db.executemany("INSERT INTO fixtures VALUES (?,?,?,?,?,?,?,?,?,?)",
                   [(*r,r[4][:10]+"T21:00:00Z","API-Football") for r in matches])
    for i in (1,2,3,5,6):
        published={
          1:"2024-08-01T22:00:00Z",
          2:"2024-08-04T22:00:00Z",
          3:"2024-08-07T22:00:00Z",
          5:"2024-08-12T22:00:00Z",
          6:"2024-08-09T22:00:00Z"}[i]
        captured="2024-08-08T12:00:00Z" if i<4 else "2024-08-14T12:00:00Z"
        db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)",(
          1,"s"+str(i),captured,published if verified else None,
          "VERIFIED_PREMATCH" if verified else "RETROSPECTIVE"))
        db.execute("INSERT INTO fixture_provider_map VALUES (?,?,?,?,?,?)",(
          1,"external"+str(i),i,"STRICT","APPROVED","s"+str(i)))
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
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?,?)",
                (1,10,1,1.75,"2024-08-01T22:30:00Z","s1","xG"))
            db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)",(
                1,"late","2024-08-15T12:00:00Z","2024-08-15T10:00:00Z","VERIFIED_PREMATCH"))
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?,?)",
                (2,10,1,99,"2024-08-15T11:00:00Z","late","xg"))
            x=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(x["features"]["home_all_5_xg_n"],1)
        self.assertEqual(x["features"]["home_all_5_xg_avg"],1.75)
        self.assertIsNone(x["features"]["home_all_5_xga_avg"])
        self.assertTrue(x["missing_flags"]["home_all_5_xg"])

    def test_conflicting_xg_fails_closed(self):
        with sample() as db:
            for value in (1.0,2.0):
                db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?,?)",
                    (1,10,1,value,"2024-08-01T22:30:00Z","s1","xg"))
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


    def prior_season(self, db, *, season_id=2, fid=71, year="2023"):
        db.execute("INSERT INTO fixtures VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (fid,season_id,10,20,f"{year}-08-01T18:00:00Z","FINISHED",3,0,
                    f"{year}-08-01T21:00:00Z","API-Football"))
        db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)",
                   (1,f"s{fid}",f"{year}-08-02T12:00:00Z",
                    f"{year}-08-01T22:00:00Z","VERIFIED_PREMATCH"))
        db.execute("INSERT INTO fixture_provider_map VALUES (?,?,?,?,?,?)",
                   (1,f"provider{fid}",fid,"STRICT","APPROVED",f"s{fid}"))

    def test_carries_previous_season_without_retraining(self):
        with sample() as db:
            self.prior_season(db)
            carry=build_features(db,4,cutoff_utc=CUTOFF)
            reset=build_features(db,4,cutoff_utc=CUTOFF,
                                 elo_params=EloParameters(season_retention=0))
        self.assertEqual(carry["accepted_predecessor_count"],4)
        self.assertEqual(carry["features"]["home_prior_seasons_games_available"],1)
        self.assertNotEqual(carry["features"]["home_elo"],reset["features"]["home_elo"])
        self.assertEqual(carry["elo_parameter_status"],"PROVISIONAL_NOT_FITTED")
        self.assertEqual(carry["elo_parameters"]["season_retention"],0.85)
        self.assertFalse(carry["training_allowed"])

    def test_other_league_not_used_in_ratings_or_form(self):
        with sample() as db:
            baseline=build_features(db,4,cutoff_utc=CUTOFF)
            self.prior_season(db,season_id=3,fid=73)
            after=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(baseline["features"],after["features"])
        self.assertEqual(baseline["accepted_predecessor_count"],3)

    def test_future_season_not_used_even_with_wrong_early_kickoff(self):
        with sample() as db:
            baseline=build_features(db,4,cutoff_utc=CUTOFF)
            self.prior_season(db,season_id=4,fid=74,year="2024")
            after=build_features(db,4,cutoff_utc=CUTOFF)
        self.assertEqual(baseline["features"],after["features"])

    def test_interseason_decay_for_multiple_absent_years(self):
        with sample() as db:
            self.prior_season(db,year="2021")
            db.execute("UPDATE seasons SET start_year=2021 WHERE season_id=2")
            before=build_features(db,4,cutoff_utc=CUTOFF,
                                  elo_params=EloParameters(season_retention=0.85))
            zero=build_features(db,4,cutoff_utc=CUTOFF,
                                elo_params=EloParameters(season_retention=0))
        self.assertEqual(before["features"]["home_prior_seasons_games_available"],1)
        self.assertNotEqual(before["features"]["home_elo"],zero["features"]["home_elo"])

    def test_reject_invalid_elo_parameter_objects(self):
        for kw in ({"k":0},{"k":-1},{"scale":0},{"season_retention":1.01},
                   {"season_retention":-0.01},{"initial":float("nan")},
                   {"home_advantage":float("inf")},{"k":True}):
            with self.subTest(kw=kw):
                with self.assertRaisesRegex(FeatureSafetyError,"INVALID_ELO_PARAMETERS"):
                    EloParameters(**kw)
        with sample() as db:
            with self.assertRaisesRegex(FeatureSafetyError,"INVALID_ELO_PARAMETERS"):
                build_features(db,4,cutoff_utc=CUTOFF,elo_params={"k":20})

    def test_changing_elo_params_changes_hash_but_not_history(self):
        with sample() as db:
            x=build_features(db,4,cutoff_utc=CUTOFF)
            y=build_features(db,4,cutoff_utc=CUTOFF,
                             elo_params=EloParameters(k=12,home_advantage=35))
        self.assertEqual(x["accepted_predecessor_count"],y["accepted_predecessor_count"])
        self.assertNotEqual(x["sha256"],y["sha256"])
        self.assertNotEqual(x["features"]["home_elo"],y["features"]["home_elo"])
        self.assertFalse(y["training_allowed"])


    def test_result_revised_after_its_snapshot_is_not_verified(self):
        with sample() as db:
            baseline=build_features(db,4,cutoff_utc=CUTOFF,mode="verified")
            self.assertEqual(baseline["accepted_predecessor_count"],3)
            # A later edit to fixtures cannot inherit a trustworthy old timestamp.
            db.execute("UPDATE fixtures SET updated_utc='2024-08-10T00:00:00Z' WHERE fixture_id=1")
            after=build_features(db,4,cutoff_utc=CUTOFF,mode="verified")
        self.assertEqual(after["accepted_predecessor_count"],2)
        self.assertEqual(after["features"]["home_elo_games_available"],1)
        self.assertFalse(after["row_payload_at_snapshot_proven"])

    def test_two_valid_providers_do_not_duplicate_result_fixture(self):
        with sample() as db:
            db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)",
                       (2,"px1","2024-08-07T12:00:00Z",
                        "2024-08-01T22:00:00Z","VERIFIED_PREMATCH"))
            db.execute("INSERT INTO fixture_provider_map VALUES (?,?,?,?,?,?)",
                       (2,"m_pitch01",1,"STRICT","APPROVED","px1"))
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?,?)",
                       (1,10,2,1.25,"2024-08-07T00:00:00Z","px1","xg"))
            x=build_features(db,4,cutoff_utc=CUTOFF,mode="verified")
        self.assertEqual(x["accepted_predecessor_count"],3)
        self.assertEqual(x["features"]["home_all_5_xg_n"],1)
        self.assertEqual(x["features"]["home_all_5_xg_avg"],1.25)
        self.assertTrue(any(y["xg_home"] and y["xg_home"]["snapshot_id"]=="px1"
                            for y in x["lineage"]))

    def test_unapproved_pitch_mapping_never_contributes_xg(self):
        with sample() as db:
            db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)",
                       (2,"px2","2024-08-07T12:00:00Z",
                        "2024-08-01T22:00:00Z","VERIFIED_PREMATCH"))
            db.execute("INSERT INTO fixture_provider_map VALUES (?,?,?,?,?,?)",
                       (2,"m_pending",1,"REVIEW","PENDING","px2"))
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?,?)",
                       (1,10,2,2.50,"2024-08-07T00:00:00Z","px2","xg"))
            x=build_features(db,4,cutoff_utc=CUTOFF,mode="verified")
        self.assertEqual(x["accepted_predecessor_count"],3)
        self.assertEqual(x["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(x["features"]["home_all_5_xg_avg"])

    def test_stat_snapshot_wrong_provider_cannot_authenticate_xg(self):
        with sample() as db:
            db.execute("INSERT INTO fixture_provider_map VALUES (?,?,?,?,?,?)",
                       (2,"m_pitch01",1,"STRICT","APPROVED","s1"))
            db.execute("INSERT INTO match_stat_observations VALUES (?,?,?,?,?,?,?)",
                       (1,10,2,4.25,"2024-08-02T00:00:00Z","s1","xg"))
            x=build_features(db,4,cutoff_utc=CUTOFF,mode="verified")
        self.assertEqual(x["features"]["home_all_5_xg_n"],0)



if __name__=="__main__":
    unittest.main()
