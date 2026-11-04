"""Offline 8-league fixed 720 M0 calibration: real-time evidence gates, 100/50 holdout.

All fixture rows here are synthetic; no network, no TEST, no user secrets.
"""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import json,sqlite3,tempfile,unittest
from src.kb3_step16_m0_720_eight_forward import (
    MODEL,freeze_sqlite,trained_params,stamp,hashobj,Research720Error)
from src.kb3_step16_m0_720_calibration import (
    append_proofs,calibrate_if_eligible,inspect_event_proofs,MIN_FIT,MIN_HOLDOUT,
    github_events,github_actions_artifact_proofs,_zip_frozen_rows)
NOW=datetime.now(timezone.utc).replace(microsecond=0)
P={"1":0.52,"X":0.27,"2":0.21}
def sample(idx,params_sha,manifest_sha,*,before):
    kickoff=(NOW-timedelta(days=150-idx) if before
             else NOW+timedelta(days=idx-99))
    captured=kickoff-timedelta(hours=4)
    x={"model_version":MODEL,"params_sha256":params_sha,
       "manifest_sha256":manifest_sha,"league_country":"ESP" if idx%2 else "POL",
       "provider_match_id":"m_TEST_SYNTHETIC_"+str(idx),
       "home_team_id":"home"+str(idx),"away_team_id":"away"+str(idx),
       "kickoff_utc":stamp(kickoff),"generated_at_utc":stamp(captured),
       "p_1x2":P,"source_chain_sha256":"a"*64,
       "phase":"EARLY","status":"RESEARCH_TRAIN720_UNCALIBRATED",
       "production_approved":False}
    x["forecast_sha256"]=hashobj(x)
    return x
def add_synthetic_settlements_and_host_proofs(db,items,*,now):
    with sqlite3.connect(db) as cn:
        for i,x in enumerate(items):
            y=("1" if i%3==0 else "X" if i%3==1 else "2")
            rec={"id":x["forecast_sha256"],"league":x["league_country"],
                 "fixture":x["provider_match_id"],"time":x["kickoff_utc"]}
            cn.execute("""INSERT INTO settlements
                  (settlement_sha256,forecast_id,league,native_match_id,
                  score_home,score_away,outcome,observed_utc,settled_utc,
                  provider_source_chain_sha256,log_loss,brier_sum3)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                  ("s"+x["forecast_sha256"][:63],x["forecast_sha256"],
                   x["league_country"],x["provider_match_id"],
                   2 if y=="1" else 1,1 if y=="1" else 2 if y=="2" else 1,y,
                   stamp(as_dt(x["kickoff_utc"])+timedelta(hours=4)),
                   stamp(as_dt(x["kickoff_utc"])+timedelta(hours=4)),
                   "a"*64,1.1,0.7))
        cn.commit()
    proofs=[]
    for i,x in enumerate(items):
        ts=as_dt(x["generated_at_utc"])+timedelta(minutes=1)
        q={"forecast_id":x["forecast_sha256"],"model":MODEL,
           "github_event_id":"123"+str(i),
           "github_commit_sha":"a"*40,
           "github_server_event_utc":stamp(ts),
           "original_forecast_sha256":x["forecast_sha256"],
           "source":"GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES",
           "audit_utc":stamp(now)}
        proofs.append(q|{"proof_id":hashobj(q)})
    return proofs
def as_dt(s):return datetime.fromisoformat(s.replace("Z","+00:00"))

class GateTests(unittest.TestCase):
 def test_absent_events_do_not_generate_fake_proofs(self):
    es,status=github_events("")
    self.assertEqual(es,[])
    self.assertEqual(status,"NO_GITHUB_EVENTS_API_TOKEN")
 def test_read_only_server_push_time_requires_historical_bytes(self):
    p,sha,manifest=trained_params()
    one=sample(0,sha,manifest,before=False)
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"r.sqlite"
        freeze_sqlite(db,[one],param_sha=sha,manifest_sha=manifest,now=NOW)
        events=[{"event_id":"21","head":"a"*40,
                 "event_utc":stamp(as_dt(one["generated_at_utc"])+timedelta(minutes=1))}]
        with patch("src.kb3_step16_m0_720_calibration.historical_snapshot_at_commit",
                   return_value={one["forecast_sha256"]:
                     (one["kickoff_utc"],one["generated_at_utc"],sha)}):
            found,counts=inspect_event_proofs(db,events,now=NOW+timedelta(days=3))
        self.assertEqual(len(found),1)
        self.assertEqual(append_proofs(db,found,now=NOW+timedelta(days=3)),1)
        self.assertEqual(append_proofs(db,found,now=NOW+timedelta(days=3)),1)
        with patch("src.kb3_step16_m0_720_calibration.historical_snapshot_at_commit",
                   return_value={}):
            found2,_=inspect_event_proofs(db,events,now=NOW+timedelta(days=3))
        self.assertEqual(found2,[])
 def test_99_block_100_first_fit_50_only_post_fit_holdout(self):
    p,sha,manifest=trained_params()
    first=[sample(i,sha,manifest,before=True) for i in range(100)]
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"r.sqlite"
        freeze_sqlite(db,first,param_sha=sha,manifest_sha=manifest,
                      now=NOW-timedelta(days=200))
        proofs=add_synthetic_settlements_and_host_proofs(
            db,first,now=NOW)
        self.assertEqual(append_proofs(db,proofs[:99],now=NOW),99)
        pre=calibrate_if_eligible(db,now=NOW)
        self.assertEqual(pre["eligible_settled_unique"],99)
        self.assertFalse(pre["calibrator_exists"])
        self.assertEqual(pre["missing_to_fit"],1)
        self.assertEqual(append_proofs(db,proofs[99:],now=NOW),100)
        fit=calibrate_if_eligible(db,now=NOW)
        self.assertTrue(fit["calibrator_exists"])
        self.assertTrue(fit["calibrator_first_fit_just_written"])
        self.assertFalse(fit["holdout_review_exists"])
        self.assertEqual(fit["missing_post_fit_holdout"],50)
        again=calibrate_if_eligible(db,now=NOW+timedelta(minutes=1))
        self.assertFalse(again["calibrator_first_fit_just_written"])
        after=[sample(i,sha,manifest,before=False) for i in range(100,150)]
        freeze_sqlite(db,after,param_sha=sha,manifest_sha=manifest,now=NOW)
        more_proofs=add_synthetic_settlements_and_host_proofs(db,after,
                                        now=NOW+timedelta(days=65))
        append_proofs(db,more_proofs[:49],now=NOW+timedelta(days=65))
        not_yet=calibrate_if_eligible(db,now=NOW+timedelta(days=65))
        self.assertEqual(not_yet["post_fit_newly_created_settled_verified"],49)
        self.assertFalse(not_yet["holdout_review_exists"])
        append_proofs(db,more_proofs[49:],now=NOW+timedelta(days=65))
        done=calibrate_if_eligible(db,now=NOW+timedelta(days=65))
        self.assertEqual(done["post_fit_newly_created_settled_verified"],50)
        self.assertTrue(done["holdout_review_exists"])
        self.assertTrue(done["holdout_first_review_just_written"])
        self.assertFalse(done["production_approved"])
        with sqlite3.connect(db) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM m0720_calibrators").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM m0720_holdout_reviews").fetchone()[0],1)
            fit_ids=json.loads(c.execute('SELECT payload_json FROM m0720_calibrators').fetchone()[0])['training_forecast_ids']
            holdout_ids=json.loads(c.execute('SELECT payload_json FROM m0720_holdout_reviews').fetchone()[0])['holdout_forecast_ids']
            self.assertEqual((len(set(fit_ids)),len(set(holdout_ids))),(100,50))
            self.assertFalse(set(fit_ids)&set(holdout_ids))
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE m0720_calibrators SET temperature=4")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("DELETE FROM m0720_github_push_proofs")
 def test_github_artifact_server_time_exact_archived_sqlite_not_commit_date(self):
    import io,zipfile
    p,sha,manifest=trained_params()
    one=sample(100,sha,manifest,before=False)
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"proof-source.sqlite"
        freeze_sqlite(db,[one],param_sha=sha,manifest_sha=manifest,now=NOW)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("forward_m0_720_eight/kb3_forward_eight.sqlite",db.read_bytes())
        blob=buf.getvalue()
        self.assertIn(one["forecast_sha256"],_zip_frozen_rows(blob))
        rstart=as_dt(one["generated_at_utc"])-timedelta(minutes=2)
        upload=as_dt(one["generated_at_utc"])+timedelta(minutes=1)
        rend=as_dt(one["generated_at_utc"])+timedelta(minutes=3)
        run={"id":919,"path":".github/workflows/kb3-step16-m0-720-eight-forward.yml",
             "event":"push","status":"completed","conclusion":"success",
             "head_sha":"b"*40,"created_at":stamp(rstart),"updated_at":stamp(rend)}
        artifact={"id":5001,"name":"KB3_STEP16_M0_720_EIGHT_LEAGUE_FREEZE_SETTLEMENT_SOURCE_EVIDENCE",
                  "created_at":stamp(upload),"expired":False,
                  "archive_download_url":"https://api.github.com/test/zip"}
        def api(url,token):
            return {"workflow_runs":[run]} if "/workflows/" in url else {"artifacts":[artifact]}
        with patch("src.kb3_step16_m0_720_calibration._gh_json",side_effect=api),patch(
             "src.kb3_step16_m0_720_calibration._gh_artifact_zip",return_value=blob):
            found,report=github_actions_artifact_proofs(
                db,token="SYNTHETIC_TOKEN",now=NOW+timedelta(days=10))
        self.assertEqual(len(found),1)
        self.assertEqual(report["verified"],1)
        self.assertEqual(found[0]["source"],
                         "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES")
        self.assertEqual(append_proofs(db,found,now=NOW+timedelta(days=10)),1)
        with sqlite3.connect(db) as conn:
            rec=conn.execute("SELECT source FROM m0720_github_push_proofs").fetchone()
            self.assertEqual(rec[0],found[0]["source"])
 def test_github_artifact_after_kickoff_cannot_attest_prognosis(self):
    import io,zipfile
    p,sha,manifest=trained_params()
    one=sample(100,sha,manifest,before=False)
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"proof-source.sqlite"
        freeze_sqlite(db,[one],param_sha=sha,manifest_sha=manifest,now=NOW)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("forward_m0_720_eight/kb3_forward_eight.sqlite",db.read_bytes())
        late=as_dt(one["kickoff_utc"])+timedelta(minutes=1)
        run={"id":929,"path":".github/workflows/kb3-step16-m0-720-eight-forward.yml",
             "event":"push","status":"completed","conclusion":"success",
             "head_sha":"b"*40,
             "created_at":stamp(late-timedelta(minutes=5)),
             "updated_at":stamp(late+timedelta(minutes=2))}
        art={"id":5002,"name":"KB3_STEP16_M0_720_EIGHT_LEAGUE_FREEZE_SETTLEMENT_SOURCE_EVIDENCE",
             "created_at":stamp(late),"expired":False,
             "archive_download_url":"https://api.github.com/test/zip"}
        def api(url,token):
            return {"workflow_runs":[run]} if "/workflows/" in url else {"artifacts":[art]}
        with patch("src.kb3_step16_m0_720_calibration._gh_json",side_effect=api),patch(
             "src.kb3_step16_m0_720_calibration._gh_artifact_zip",return_value=buf.getvalue()):
            found,report=github_actions_artifact_proofs(
                db,token="SYNTHETIC_TOKEN",now=NOW+timedelta(days=10))
        self.assertEqual(found,[])
        self.assertEqual(report["verified"],0)
if __name__=="__main__":unittest.main()
