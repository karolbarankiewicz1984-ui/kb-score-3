"""Strict synthetic TESTS; do not use test-generated results in actual DB."""
import math,json,sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_m0_shadow_daily_settlement import (
    SCHEMA,sha,as_z,classify_result,preflight_results,settle_sqlite,
    _calibration,MIN_FIT,MIN_HOLDOUT,SettlementSafetyError)
from src.kb3_pitch_uefa_evidence import add_observation
from src.kb3_step14_m1_math_calibration import score_one
from src.kb3_three_league_sqlite_forward_features import commit_sqlite
from src.kb3_m0_shadow_1x2_live_freeze import freeze
from test_step14_three_league_sqlite_forward_features import fake_capture,season_rows,stamp,NOW
from scripts.step14_three_league_pitchapi_actual_audit import LEAGUES,CURRENT,PREVIOUS

def fake_result_receipts():
    c={"leagues":[{"id":f"l_{i:06d}","name":name,"country_code":country,
       "seasons":[CURRENT,PREVIOUS]} for i,(country,aliases,n,name) in enumerate(LEAGUES,1)]}
    pairs=[("pitchapi:catalog",c)]
    for country,aliases,n,name in LEAGUES:
        pairs.append((f"pitchapi:result:{country}:{CURRENT}",
                     {"matches":season_rows(country,n,2026)}))
    receipts=[]
    t=datetime.now(timezone.utc)
    for key,payload in pairs:
        add_observation(receipts,resource=key,payload=payload,
                        started=stamp(t),completed=stamp(t),origin="SYNTHETIC_TEST")
    return receipts

class M0SettlementCalibrationTests(unittest.TestCase):
 def make(self,root):
    db=Path(root)/"m0.sqlite"
    commit_sqlite(db,fake_capture(),cutoff_utc=stamp(NOW),
                  raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
    f=freeze(db,now=datetime.now(timezone.utc),strict_initial_count=True)
    self.assertEqual(f["actual_derived_forecasts"],12)
    return db

 def test_math_log_loss_and_brier_sum3_not_divided_by_three(self):
    a,b=score_one({"1":0.5,"X":0.3,"2":0.2},"X")
    self.assertAlmostEqual(a,-math.log(.3),places=12)
    self.assertAlmostEqual(b,.25+.49+.04,places=12)

 def test_only_three_exact_real_provider_scopes(self):
    rec=fake_result_receipts()
    scope,p=preflight_results(rec,datetime.now(timezone.utc),allow_synthetic=True)
    self.assertEqual(set(scope),{"ESP","ITA","GER"})
    self.assertEqual(p["sessions"],4)
    rec[2]["resource"]="pitchapi:result:ENG:2026/2027"
    with self.assertRaises(ValueError):
        preflight_results(rec,datetime.now(timezone.utc),allow_synthetic=True)

 def test_final_result_classification_and_changed_identity_quarantine(self):
    f={"provider_match_id":"m_000111","provider_home_team_id":"t_000111",
       "provider_away_team_id":"t_000222","kickoff_utc":"2026-10-29T10:00:00Z"}
    target={"id":f["provider_match_id"],"time_utc":f["kickoff_utc"],
        "home_team":{"id":"t_000111"},"away_team":{"id":"t_000222"},
        "status":"finished","score_home":2,"score_away":2}
    t=datetime(2026,10,29,14,tzinfo=timezone.utc)
    self.assertEqual(classify_result(target,f,t),("SETTLE",(2,2,"X")))
    self.assertEqual(classify_result(target,f,t-timedelta(hours=2))[0],"RESULT_TOO_EARLY")
    bad=dict(target);bad["away_team"]={"id":"t_000333"}
    self.assertEqual(classify_result(bad,f,t)[0],"MISMATCH_TEAM_ID")
    bad=dict(target);bad["time_utc"]="2026-10-29T11:00:00Z"
    self.assertEqual(classify_result(bad,f,t)[0],"KICKOFF_CHANGED_NEEDS_REVIEW")
    bad=dict(target);bad["status"]="scheduled";bad["score_home"]=None;bad["score_away"]=None
    self.assertEqual(classify_result(bad,f,t)[0],"NOT_FINISHED")

 def test_real_shaped_frozen_12_yet_no_match_has_finished(self):
    with tempfile.TemporaryDirectory() as t:
        db=self.make(t)
        a=settle_sqlite(db,fake_result_receipts(),now=datetime.now(timezone.utc),
                        allow_synthetic=True)
        self.assertEqual(a["newly_settled_1x2"],0)
        self.assertEqual(a["cumulative_settled_1x2"],0)
        self.assertEqual(a["calibration_candidates_total"],0)
        self.assertEqual(a["holdout_reviews_total"],0)
        with sqlite3.connect(db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM m0_shadow_result_sources").fetchone()[0],3)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM m0_shadow_1x2_forecasts").fetchone()[0],12)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM m0_shadow_1x2_settlements").fetchone()[0],0)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(),[])
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE m0_shadow_result_sources SET payload_sha256='FAKE'")
        # Same all-future feed on a second day must not invent 1X2 outcomes.
        b=settle_sqlite(db,fake_result_receipts(),now=datetime.now(timezone.utc),
                        allow_synthetic=True)
        self.assertEqual(b["newly_settled_1x2"],0)

 def test_100_fit_then_50_later_unseen_predictions_and_never_auto_activate(self):
    with sqlite3.connect(":memory:") as db:
        db.execute("""CREATE TABLE m0_shadow_1x2_forecasts (
         forecast_id TEXT,model_version_id TEXT,parameter_sha256 TEXT,
         phase TEXT,generated_at_utc TEXT,kickoff_utc TEXT,
         p_1 REAL,p_x REAL,p_2 REAL)""")
        db.execute("""CREATE TABLE m0_shadow_1x2_settlements
         (forecast_id TEXT,settlement_id TEXT,observed_at_utc TEXT,result_1x2 TEXT)""")
        db.executescript((Path(__file__).resolve().parents[1]/
           "migrations/004_m0_shadow_settlement_and_future_calibration.sql").read_text())
        # Synthetic calibration threshold test bypasses real-result INSERT guard;
        # production never drops the trigger. The separate live-shaped test
        # verifies actual immutable settlement/fixture schema remains intact.
        db.execute("DROP TRIGGER m0_settlement_before_insert")
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        # 99 fake settled outcomes: insufficient for candidate.
        for i in range(99):
            generated=base+timedelta(hours=6*i)
            ko=generated+timedelta(hours=2)
            end=ko+timedelta(hours=4)
            db.execute("INSERT INTO m0_shadow_1x2_forecasts VALUES(?,?,?,?,?,?,?,?,?)",
             (f"syn{i}",'VERSION_A','p'*64,'EARLY',as_z(generated),as_z(ko),.5,.3,.2))
            db.execute("INSERT INTO m0_shadow_1x2_settlements VALUES(?,?,?,?)",
             (f"syn{i}",f"settle{i}",as_z(end),["1","X","2"][i%3]))
        cutoff=base+timedelta(days=31)
        self.assertEqual(_calibration(db,cutoff),[])
        i=99;gen=base+timedelta(hours=6*i);ko=gen+timedelta(hours=2);end=ko+timedelta(hours=4)
        db.execute("INSERT INTO m0_shadow_1x2_forecasts VALUES(?,?,?,?,?,?,?,?,?)",
             (f"syn{i}",'VERSION_A','p'*64,'EARLY',as_z(gen),as_z(ko),.5,.3,.2))
        db.execute("INSERT INTO m0_shadow_1x2_settlements VALUES(?,?,?,?)",
             (f"syn{i}",f"settle{i}",as_z(end),"1"))
        first=_calibration(db,cutoff)
        self.assertEqual(len(first),1)
        self.assertEqual(first[0]["state"],"CANDIDATE_FROZEN")
        self.assertEqual(first[0]["fit_n"],100)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM m0_shadow_calibration_evaluations").fetchone()[0],0)
        # All 50 holdout forecasts must be after the pinned fit date.
        for j in range(49):
            gen=cutoff+timedelta(hours=6*(j+1))
            ko=gen+timedelta(hours=2);end=ko+timedelta(hours=4)
            db.execute("INSERT INTO m0_shadow_1x2_forecasts VALUES(?,?,?,?,?,?,?,?,?)",
             (f"post{j}",'VERSION_A','p'*64,'EARLY',as_z(gen),as_z(ko),.5,.3,.2))
            db.execute("INSERT INTO m0_shadow_1x2_settlements VALUES(?,?,?,?)",
             (f"post{j}",f"result{j}",as_z(end),["1","X","2"][j%3]))
        self.assertEqual(_calibration(db,cutoff+timedelta(days=14)),[])
        j=49;gen=cutoff+timedelta(hours=6*(j+1));ko=gen+timedelta(hours=2);end=ko+timedelta(hours=4)
        db.execute("INSERT INTO m0_shadow_1x2_forecasts VALUES(?,?,?,?,?,?,?,?,?)",
             (f"post{j}",'VERSION_A','p'*64,'EARLY',as_z(gen),as_z(ko),.5,.3,.2))
        db.execute("INSERT INTO m0_shadow_1x2_settlements VALUES(?,?,?,?)",
             (f"post{j}",f"result{j}",as_z(end),"2"))
        reviews=_calibration(db,cutoff+timedelta(days=15))
        self.assertEqual(reviews[0]["state"],"HOLDOUT_FROZEN")
        self.assertEqual(reviews[0]["holdout_n"],50)
        self.assertEqual(db.execute("SELECT automatic_activation FROM m0_shadow_calibration_evaluations").fetchone()[0],0)
        self.assertEqual(_calibration(db,cutoff+timedelta(days=16)),[])

if __name__=="__main__":unittest.main()
