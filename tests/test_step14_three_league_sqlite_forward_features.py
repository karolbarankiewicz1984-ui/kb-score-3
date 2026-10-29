import sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_pit_ledger import utc_now
from src.kb3_three_league_sqlite_forward_features import (
    observed_three_league_snapshots,commit_sqlite,opaque_sql_id,M0FreezeError,
    matches_receipts)
from scripts.step14_three_league_pitchapi_actual_audit import LEAGUES,CURRENT,PREVIOUS

NOW=datetime.now(timezone.utc)
def stamp(dt):
    return dt.isoformat().replace("+00:00","Z")
def season_rows(country,n,year):
    idx={"ESP":1,"ITA":2,"GER":3}[country]
    a=[]
    for i in range(n):
        if year==2025:
            kickoff=datetime(2025,8,1,tzinfo=timezone.utc)+timedelta(hours=11*i)
            finished=True
        else:
            kickoff=datetime(2026,8,1,tzinfo=timezone.utc)+timedelta(hours=17*i)
            finished=kickoff+timedelta(hours=3)<NOW-timedelta(hours=2)
        h=i%20+1;away=(i+1)%20+1
        a.append({"id":"m_"+format(idx*100000+(year-2025)*50000+i,"06d"),
                  "time_utc":stamp(kickoff),"status":"finished" if finished else "scheduled",
                  "score_home":(i%4) if finished else None,
                  "score_away":(i%3) if finished else None,
                  "home_team":{"id":"t_"+format(idx*1000+h,"06d"),"name":"Club"+str(idx)+"-"+str(h)},
                  "away_team":{"id":"t_"+format(idx*1000+away,"06d"),"name":"Club"+str(idx)+"-"+str(away)}})
    return a
def fake_capture():
    receipts=[];index=0
    for c,names,n,title in LEAGUES:
        for season,year in ((CURRENT,2026),(PREVIOUS,2025)):
            index+=1
            value={"matches":season_rows(c,n,year)}
            receipts.append({"origin":"NETWORK_OBSERVED",
              "resource":"pitchapi:pilot_daily:"+c+":"+season,
              "payload":value,"completed_at_utc":stamp(NOW),
              "chain_sha256":format(index,"064x"),
              "payload_sha256":format(300+index,"064x")})
    return receipts

class M0SQLFrozenLive(unittest.TestCase):
 def test_12_real_shape_snapshots_fields(self):
    snaps,src,cutoff=observed_three_league_snapshots(fake_capture(),
                                      cutoff_utc=stamp(NOW+timedelta(minutes=1)))
    self.assertEqual((len(snaps),len(src)),(12,6))
    self.assertEqual({r[0] for r in snaps},{"ESP","ITA","GER"})
    for country,title,target,feat in snaps:
        self.assertEqual(len(feat["features"]),121)
        self.assertEqual(len(feat["missing_flags"]),38)
        self.assertEqual(len(feat["feature_availability"]),159)
        self.assertFalse(feat["target_prematch_snapshot_certified"])
        self.assertFalse(feat["training_allowed"])
        self.assertEqual(feat["availability_class"],"OBSERVED_AT_NOT_CERTIFIED")
        self.assertTrue(all(a["provider_original_published_at_utc"] is None
                          for a in feat["feature_availability"].values()))
        self.assertTrue(all(a["latest_required_observed_at_utc"]<=stamp(NOW+timedelta(minutes=1))
                          for a in feat["feature_availability"].values()))
 def test_database_insert_and_freeze_immutable(self):
    with tempfile.TemporaryDirectory() as d:
        db=Path(d)/"features.sqlite"
        out=commit_sqlite(db,fake_capture(),cutoff_utc=stamp(NOW+timedelta(minutes=1)),
                          raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
        self.assertEqual(out["frozen_feature_snapshots_today"],12)
        self.assertEqual(out["by_country"],{"ESP":4,"ITA":4,"GER":4})
        with sqlite3.connect(db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM feature_snapshots").fetchone()[0],12)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM m0_forward_sources").fetchone()[0],6)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM m0_forward_feature_records WHERE eligible_for_original_M1!=0").fetchone()[0],0)
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE m0_forward_feature_records SET source_xg_count=0")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM m0_forward_feature_records")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE feature_snapshots SET feature_hash='wrong'")
 def test_copy_already_frozen_daily_rows_rejected(self):
    with tempfile.TemporaryDirectory() as d:
        db=Path(d)/"features.sqlite"
        kwargs={"cutoff_utc":stamp(NOW+timedelta(minutes=1)),
                "raw_cipher_sha":"a"*64,"raw_chain_sha":"b"*64}
        commit_sqlite(db,fake_capture(),**kwargs)
        with self.assertRaises(sqlite3.IntegrityError):
            commit_sqlite(db,fake_capture(),**kwargs)
 def test_forecast_not_created_by_feature_snapshot(self):
    with tempfile.TemporaryDirectory() as d:
        db=Path(d)/"features.sqlite"
        r=commit_sqlite(db,fake_capture(),cutoff_utc=stamp(NOW+timedelta(minutes=1)),
                        raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
        self.assertFalse(r["model_fit_or_forecast_generated"])
        self.assertFalse(r["original_Gate14_pass"])
 def test_missing_country_does_not_silent_train(self):
    inputs=fake_capture()[:-1]
    with self.assertRaisesRegex(M0FreezeError,"THREE_LEAGUES"):
        observed_three_league_snapshots(inputs,cutoff_utc=stamp(NOW))
 def test_postmatch_or_too_late_target_excluded(self):
    receipts=fake_capture()
    for r in receipts:
        if r["resource"]=="pitchapi:pilot_daily:ESP:"+CURRENT:
            for m in r["payload"]["matches"]:
                if m["status"]=="scheduled":m["time_utc"]=stamp(NOW-timedelta(minutes=10))
    with self.assertRaisesRegex(M0FreezeError,"THREE_TIMES_FOUR"):
        observed_three_league_snapshots(receipts,cutoff_utc=stamp(NOW+timedelta(minutes=1)))
 def test_no_fixture_ID_alias_with_team(self):
    self.assertNotEqual(opaque_sql_id("fixture","m_111111"),
                        opaque_sql_id("team","m_111111"))
if __name__=="__main__":unittest.main()
