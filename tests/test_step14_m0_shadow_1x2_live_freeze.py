import copy,json,sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_m0_shadow_1x2_live_freeze import (
    freeze,_verify_snapshot,ForecastFreezeError,MODEL_ENGINE,MIN_MARGIN)
from src.kb3_three_league_sqlite_forward_features import commit_sqlite
from test_step14_three_league_sqlite_forward_features import fake_capture,stamp,NOW

class GenuineM0OneXTwo(unittest.TestCase):
 def make_db(self,tmp):
    path=Path(tmp)/"actual.sqlite"
    commit_sqlite(path,fake_capture(),cutoff_utc=stamp(NOW),
                  raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
    return path
 def test_12_real_shape_1_x_2_frozen_and_individually_hashed(self):
    with tempfile.TemporaryDirectory() as tmp:
        db=self.make_db(tmp)
        output=Path(tmp)/"shadow.json"
        r=freeze(db,report_path=output,now=datetime.now(timezone.utc),
                 strict_initial_count=True)
        self.assertEqual(r["actual_derived_forecasts"],12)
        self.assertEqual({x["league"] for x in r["individual_forecasts"]},
                         {"ESP","ITA","GER"})
        self.assertTrue(output.exists())
        self.assertFalse(r["original_M1_training_or_calibration"])
        self.assertFalse(r["eligible_for_betting_claims"])
        for x in r["individual_forecasts"]:
            p=x["p_1x2"]
            self.assertEqual(set(p),{"1","X","2"})
            self.assertAlmostEqual(sum(p.values()),1,places=12)
            self.assertTrue(all(0<v<1 for v in p.values()))
            self.assertEqual(x["engine"],MODEL_ENGINE)
            self.assertEqual(x["parameter_status"],"ILLUSTRATIVE_UNFITTED_NOT_FOR_BETTING")
            self.assertFalse(x["calibrated"])
            self.assertLess(x["generated_at_utc"],x["kickoff_utc"])
        with sqlite3.connect(db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM m0_shadow_1x2_forecasts").fetchone()[0],12)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],0)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(),[])
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE m0_shadow_1x2_forecasts SET p_1=.7")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM m0_shadow_1x2_forecasts")
 def test_same_fixtures_are_never_refitted(self):
    with tempfile.TemporaryDirectory() as t:
        db=self.make_db(t)
        r1=freeze(db,now=datetime.now(timezone.utc))
        r2=freeze(db,now=datetime.now(timezone.utc))
        self.assertEqual(r1["actual_derived_forecasts"],12)
        self.assertEqual(r2["fresh_forecasts"],0)
        self.assertEqual(r2["total_frozen"],12)
 def test_too_late_to_create_a_backdated_prediction(self):
    with tempfile.TemporaryDirectory() as t:
        db=self.make_db(t)
        r=freeze(db,now=datetime.now(timezone.utc)+timedelta(days=400))
        self.assertEqual(r["fresh_forecasts"],0)
        with sqlite3.connect(db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM m0_shadow_1x2_forecasts").fetchone()[0],0)
 def test_wrong_feature_sha_refused_without_predictions(self):
    with tempfile.TemporaryDirectory() as t:
        db=self.make_db(t)
        with sqlite3.connect(db) as c:
            row=c.execute("""SELECT fs.feature_snapshot_id,fs.fixture_id,fs.model_version_id,
              fs.observed_cutoff_utc,fs.feature_hash,fs.feature_hash,
              mr.league_country,mr.provider_match_id,mr.kickoff_original_utc,
              mr.provider_home_team_id,mr.provider_away_team_id,mr.feature_payload_json,
              fs.missing_flags_json,home.canonical_name,away.canonical_name,
              f.status,fs.availability_class,mv.approval_status,mr.signed_source_chain_sha256
             FROM m0_forward_feature_records mr
             JOIN feature_snapshots fs ON fs.feature_snapshot_id=mr.feature_snapshot_id
             JOIN fixtures f ON f.fixture_id=fs.fixture_id
             JOIN model_versions mv ON mv.model_version_id=fs.model_version_id
             JOIN teams home ON home.team_id=f.home_team_id
             JOIN teams away ON away.team_id=f.away_team_id LIMIT 1""").fetchone()
            arr=list(row);arr[4]="f"*64;arr[5]="f"*64
            with self.assertRaisesRegex(ForecastFreezeError,"TAMPERED"):
                _verify_snapshot(arr,now=datetime.now(timezone.utc))
 def test_no_missing_db_auto_treated_as_true_history(self):
    with tempfile.TemporaryDirectory() as t:
        with self.assertRaisesRegex(ForecastFreezeError,"SQLITE_MISSING"):
            freeze(Path(t)/"missing.sqlite")
 def test_original_immutable_feature_records_remain(self):
    with tempfile.TemporaryDirectory() as t:
        db=self.make_db(t)
        freeze(db,now=datetime.now(timezone.utc))
        with sqlite3.connect(db) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM m0_forward_feature_records").fetchone()[0],12)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM feature_snapshots").fetchone()[0],12)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM m0_forward_feature_records WHERE eligible_for_original_M1=1").fetchone()[0],0)
if __name__=="__main__": unittest.main()
