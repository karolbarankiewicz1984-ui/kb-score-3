"""KB3 Step16 separate eight-league real 720 TRAIN research stream safety."""
import tempfile,sqlite3,unittest,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from src.kb3_step16_m0_720_eight_forward import (
    MODEL,EIGHT,EIGHT_COUNTRIES,select_eight,trained_params,validate_season,
    make_forecasts,freeze_sqlite,settle_sqlite,Research720Error,hashobj,stamp,
    CALL_CAP_CAPTURE,CALL_CAP_SETTLE)
NOW=datetime.now(timezone.utc)
def season(country,year):
    idx=list(EIGHT_COUNTRIES).index(country)+1
    count=313 if country=="BEL" and year==2025 else 309 if country=="NED" and year==2025 else 380 if country in ("ESP","ITA") else 306
    rows=[]
    for i in range(count):
        if year==2025:
            dt=datetime(2025,8,1,tzinfo=timezone.utc)+timedelta(hours=i*9)
            finished=True
        elif i<250:
            dt=datetime(2026,8,1,tzinfo=timezone.utc)+timedelta(hours=i*5)
            finished=True
        elif i<258:
            dt=NOW+timedelta(hours=5+i-250)
            finished=False
        else:
            dt=NOW+timedelta(days=20+(i-258)//10)
            finished=False
        rows.append({"id":"m_"+str(idx)+"_"+str(year)+"_"+str(i),
            "time_utc":stamp(dt),"status":"finished" if finished else "scheduled",
            "score_home":i%4 if finished else None,
            "score_away":i%3 if finished else None,
            "home_team":{"id":"t_"+str(idx)+"_"+str(i%18),
                "name":"TeamA"+str(idx)},
            "away_team":{"id":"t_"+str(idx)+"_"+str((i+1)%18),
                "name":"TeamB"+str(idx)}})
    return rows
def fake_receipts():
    receipts=[];n=0
    for c,_,_ in EIGHT:
        for year,label in ((2025,"2025/2026"),(2026,"2026/2027")):
            n+=1
            receipts.append({"origin":"NETWORK_OBSERVED",
                "resource":f"pitchapi:m0720:fixtures:{c}:{label}",
                "payload":{"matches":season(c,year)},
                "completed_at_utc":stamp(NOW-timedelta(minutes=5)),
                "chain_sha256":f"{n:064x}"})
    return receipts
class EightForwardTests(unittest.TestCase):
 def test_one_exact_model_train720_hash(self):
    p,sha,manifest=trained_params()
    self.assertEqual(p.elo_goal_elasticity,0.6)
    self.assertAlmostEqual(p.base_home_goals,1.6447363878515198,12)
    self.assertAlmostEqual(p.base_away_goals,1.4381853609496382,12)
    self.assertEqual(len(sha),64)
 def test_true_eight_country_allowlist_no_england(self):
    self.assertEqual(len(EIGHT),8)
    self.assertNotIn("ENG",EIGHT_COUNTRIES)
    self.assertEqual(CALL_CAP_CAPTURE,17)
    self.assertEqual(CALL_CAP_SETTLE,9)
    catalog={"leagues":[{"country_code":c,"name":title,"seasons":["2025/2026","2026/2027"],
                         "id":"l_"+c,"is_free":True} for c,title,_ in EIGHT]
             +[{"country_code":"ENG","name":"Premier League","id":"l_TEST",
                "seasons":["2025/2026","2026/2027"],"is_free":True}]}
    self.assertEqual(len(select_eight(catalog)),8)
    self.assertNotIn("l_TEST",[x[2] for x in select_eight(catalog)])
 def test_unavailable_paid_league_blocks_entire_launch(self):
    catalog={"leagues":[{"country_code":c,"name":title,"seasons":["2025/2026","2026/2027"],
                         "id":"l_"+c,"is_free":c!="POL"} for c,title,_ in EIGHT]}
    with self.assertRaisesRegex(Research720Error,"FREE_ENTITLEMENT"):
        select_eight(catalog)
 def test_313_309_playoff_previous_are_accepted(self):
    self.assertEqual(validate_season(season("BEL",2025),current=False)["all"],313)
    self.assertEqual(validate_season(season("NED",2025),current=False)["all"],309)
 def test_80_immutable_prospective_real_shape(self):
    p,sha,manifest=trained_params()
    items,per,shapes=make_forecasts(fake_receipts(),
                       cutoff=NOW,params=p,param_sha=sha,manifest_sha=manifest)
    self.assertEqual(len(items),64)
    self.assertEqual(per,{c:8 for c,_,_ in EIGHT})
    self.assertEqual(len(shapes),16)
    self.assertEqual(len({(f["league_country"],f["provider_match_id"]) for f in items}),64)
    self.assertTrue(all(f["training_allowed"] is False for f in items))
    self.assertTrue(all(f["original_provider_first_published_at_proven"] is False for f in items))
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"isolated.sqlite"
        added,total=freeze_sqlite(db,items,param_sha=sha,manifest_sha=manifest,now=NOW)
        self.assertEqual((added,total),(64,64))
        added2,total2=freeze_sqlite(db,items,param_sha=sha,manifest_sha=manifest,now=NOW)
        self.assertEqual((added2,total2),(0,64))
        with sqlite3.connect(db) as con:
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(),[])
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM forecasts")
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE forecasts SET kickoff_utc='2000-01-01'")
        # Real result is NEVER retroactively invented: only after kickoff+3h.
        sample=items[0]
        result={"id":sample["provider_match_id"],"time_utc":sample["kickoff_utc"],
                "home_team":{"id":sample["home_team_id"]},
                "away_team":{"id":sample["away_team_id"]},
                "score_home":2,"score_away":1,"status":"finished"}
        old=settle_sqlite(db,{(sample["league_country"],sample["provider_match_id"]):result},
                          observed_at=NOW,source_chain_sha="a"*64)
        self.assertEqual(old["new_settlements"],0)
        new=settle_sqlite(db,{(sample["league_country"],sample["provider_match_id"]):result},
                          observed_at=NOW+timedelta(days=5),source_chain_sha="a"*64)
        self.assertEqual(new["new_settlements"],1)
        self.assertEqual(new["total_settlements"],1)
        self.assertIsNotNone(new["metrics"])
        repeat=settle_sqlite(db,{(sample["league_country"],sample["provider_match_id"]):result},
                          observed_at=NOW+timedelta(days=6),source_chain_sha="b"*64)
        self.assertEqual(repeat["new_settlements"],0)
        self.assertEqual(repeat["total_settlements"],1)
 def test_season_blocks_target_scores_before_kickoff(self):
    rows=season("ESP",2026)
    rows[250]["score_home"]=0
    with self.assertRaisesRegex(Research720Error,"FUTURE_TARGET_CONTAINS_RESULT"):
        validate_season(rows,current=True)
 def test_model_manifest_cannot_be_autopromoted(self):
    p,sha,manifest=trained_params()
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"isolated.sqlite"
        freeze_sqlite(db,[],param_sha=sha,manifest_sha=manifest,now=NOW)
        with sqlite3.connect(db) as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE model_meta SET status='CHAMPION'")
if __name__=="__main__":unittest.main()
