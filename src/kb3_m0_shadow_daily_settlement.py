"""Research M0: REAL PitchAPI post-match 90-minute labels, log loss and
multiclass Brier sum3, plus forward-only 100/50 calibration candidates.

Original frozen Elo+Poisson 1/X/2 forecasts are NEVER updated. The Premier
League 2026/27 original TEST is excluded. Provider actual first-published-at
is never inferred; response time is only network observation UTC.

Live workflow uses raw PitchAPI catalog + exact three current seasons, RSA
sealed, 4 network requests. No provider keys or raw content exposed in logs.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_pit_ledger import canonical,as_utc,utc_now
from src.kb3_pitch_native import check_season
from src.kb3_pitch_uefa_evidence import add_observation,seal,verify_receipts
from src.kb3_step14_m1_math_calibration import (
    score_one,score_predictions,fit_temperature,evaluate_calibrated_holdout)
from scripts.step14_three_league_pitchapi_actual_audit import (
    LEAGUES,CURRENT,select_three)
from scripts.pitchapi_step06_audit import to_plain

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-M0-real-result-settlement-logloss-brier-and-100x50-calibration-v1"
MIN_FINISH=timedelta(hours=3)
MAX_CALLS=4
MIN_FIT=100
MIN_HOLDOUT=50
class SettlementSafetyError(ValueError):pass

def sha(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def as_z(t):return t.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def preflight_results(receipts,now,*,allow_synthetic=False):
    proof=verify_receipts(receipts,allow_synthetic=allow_synthetic)
    if len(receipts)!=MAX_CALLS:raise SettlementSafetyError("PITCH_EXPECTED_FOUR_CATALOGUE_AND_LEAGUES")
    if receipts[0]["resource"]!="pitchapi:catalog":
        raise SettlementSafetyError("NO_VERIFIABLE_CATALOGUE")
    actual=select_three(receipts[0]["payload"])
    expected={f"pitchapi:result:{country}:{CURRENT}" for _,country,_,_ in actual}
    if {r["resource"] for r in receipts[1:]}!=expected:
        raise SettlementSafetyError("RESULT_SOURCE_LEAGUES_NOT_THREE_ISOLATED")
    lookup={}
    for title,country,count,lid in actual:
        res=next(r for r in receipts if r["resource"]==f"pitchapi:result:{country}:{CURRENT}")
        complete=as_utc(res["completed_at_utc"])
        if complete>now or (not allow_synthetic and
            abs((datetime.now(timezone.utc)-complete).total_seconds())>180):
            raise SettlementSafetyError("NETWORK_RESULT_TIME_INVALID")
        matches=res["payload"].get("matches")
        check_season(matches,CURRENT,expected_count=count)
        lookup[country]=(res,{m["id"]:m for m in matches})
    return lookup,proof

def classify_result(target,forecast,observed):
    """Return score pair only for actual finished matching named/native fixture,
    with 3-hour lag; never look at scheduled target score or feed status.
    A changed kickoff or team mapping is quarantine/review, no auto-settlement.
    """
    if target is None or target["id"]!=forecast["provider_match_id"]:
        return "MISSING_TARGET",None
    if (target["home_team"]["id"]!=forecast["provider_home_team_id"]
            or target["away_team"]["id"]!=forecast["provider_away_team_id"]):
        return "MISMATCH_TEAM_ID",None
    if as_utc(target["time_utc"])!=as_utc(forecast["kickoff_utc"]):
        return "KICKOFF_CHANGED_NEEDS_REVIEW",None
    ko=as_utc(forecast["kickoff_utc"])
    if target["status"]!="finished":
        return "NOT_FINISHED",None
    if observed<ko+MIN_FINISH:
        return "RESULT_TOO_EARLY",None
    home,away=target["score_home"],target["score_away"]
    if any(type(v) is not int or not 0<=v<=30 for v in (home,away)):
        return "BAD_90MIN_SCORE",None
    y="1" if home>away else "2" if home<away else "X"
    return "SETTLE",(home,away,y)

def _paired(db,version,param):
    return db.execute("""SELECT p.forecast_id,p.model_version_id,p.parameter_sha256,
      p.generated_at_utc,p.kickoff_utc,p.p_1,p.p_x,p.p_2,
      s.result_1x2,s.settlement_id,s.observed_at_utc
      FROM m0_shadow_1x2_settlements s
      JOIN m0_shadow_1x2_forecasts p ON p.forecast_id=s.forecast_id
      WHERE p.model_version_id=? AND p.parameter_sha256=? AND p.phase='EARLY'
      ORDER BY s.observed_at_utc,p.kickoff_utc,p.forecast_id""",(version,param)).fetchall()

def _aggregate(db):
    rows=db.execute("""SELECT p.league_country,p.model_version_id,p.parameter_sha256,
      p.p_1,p.p_x,p.p_2,s.result_1x2
      FROM m0_shadow_1x2_settlements s JOIN m0_shadow_1x2_forecasts p
      ON p.forecast_id=s.forecast_id ORDER BY s.observed_at_utc,p.forecast_id""").fetchall()
    by=defaultdict(lambda:([],[]))
    for league,model,param,one,draw,two,label in rows:
        key=(model,param,"ALL_THREE_LEAGUES")
        by[key][0].append({"1":one,"X":draw,"2":two})
        by[key][1].append(label)
        key=(model,param,league)
        by[key][0].append({"1":one,"X":draw,"2":two})
        by[key][1].append(label)
    return [{"model_version":k[0],"parameter_sha256":k[1],
         "scope":k[2],**score_predictions(*v)} for k,v in
         sorted(by.items(),key=lambda item:item[0])]

def _calibration(db,now):
    """Create immutable candidate at >=100 real settled forecasts. Freeze
    cutoff NOW; evaluate only >=50 forecasts actually generated AFTER cutoff.
    New labels cannot contaminate original temperature. No auto-activation.
    """
    groups=db.execute("""SELECT DISTINCT p.model_version_id,p.parameter_sha256
      FROM m0_shadow_1x2_settlements s
      JOIN m0_shadow_1x2_forecasts p ON p.forecast_id=s.forecast_id
      WHERE p.phase='EARLY' ORDER BY p.model_version_id,p.parameter_sha256""").fetchall()
    proposals=[]
    for version,param in groups:
        rows=_paired(db,version,param)
        if len({r[0] for r in rows})!=len(rows):
            raise SettlementSafetyError("SAME_FIXTURE_MULTIPLE_LABELS")
        candidate=db.execute("""SELECT candidate_id,fit_cutoff_utc,temperature
          FROM m0_shadow_calibration_candidates
          WHERE model_version_id=? AND parameter_sha256=? AND phase='EARLY'
          AND scope='ESP_ITA_GER'""",(version,param)).fetchone()
        if candidate is None and len(rows)>=MIN_FIT:
            frozen=[r for r in rows if as_utc(r[10])<=now]
            if len(frozen)<MIN_FIT:continue
            p=[{"1":r[5],"X":r[6],"2":r[7]} for r in frozen]
            y=[r[8] for r in frozen]
            fitted=fit_temperature(p,y,min_rows=MIN_FIT)
            cut=as_z(now)
            h=sha([r[0:5]+r[8:11] for r in frozen])
            candidate_id=sha({"schema":SCHEMA,"version":version,"param":param,
                "cutoff":cut,"fit_sha":h})
            db.execute("""INSERT INTO m0_shadow_calibration_candidates
              (candidate_id,model_version_id,parameter_sha256,fit_cutoff_utc,
               created_at_utc,fit_n,temperature,fit_records_sha256,
               fit_log_loss_raw,fit_log_loss_calibrated)
              VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (candidate_id,version,param,cut,cut,len(frozen),fitted["temperature"],
               h,fitted["calibration_log_loss_raw"],fitted["calibration_log_loss_fitted"]))
            candidate=(candidate_id,cut,fitted["temperature"])
            proposals.append({"state":"CANDIDATE_FROZEN","candidate_id":candidate_id,
                "fit_n":len(frozen),"temperature":fitted["temperature"]})
        if candidate is not None:
            id,cut,temp=candidate
            exists=db.execute("SELECT 1 FROM m0_shadow_calibration_evaluations WHERE candidate_id=?",
                              (id,)).fetchone()
            if exists:continue
            # Both target kickoff and forecast generation MUST follow cutoff.
            # Prior pre-made forecasts are explicitly excluded from holdout.
            evaluation=[r for r in rows
                 if as_utc(r[3])>as_utc(cut)
                 and as_utc(r[4])>as_utc(cut)
                 and as_utc(r[10])>as_utc(cut)]
            if len(evaluation)>=MIN_HOLDOUT:
                holdout=evaluation[:MIN_HOLDOUT]
                pred=[{"1":r[5],"X":r[6],"2":r[7]} for r in holdout]
                y=[r[8] for r in holdout]
                comparison=evaluate_calibrated_holdout(pred,y,{"temperature":temp})
                raw= comparison["raw"];post=comparison["calibrated"]
                improved=int(post["log_loss"]<raw["log_loss"] and
                             post["brier_sum3"]<raw["brier_sum3"])
                h=sha([r[0:5]+r[8:11] for r in holdout])
                eid=sha({"candidate_id":id,"holdout_sha":h,"schema":SCHEMA})
                db.execute("""INSERT INTO m0_shadow_calibration_evaluations
                (evaluation_id,candidate_id,created_at_utc,holdout_n,
                 holdout_records_sha256,raw_log_loss,calibrated_log_loss,
                 raw_brier_sum3,calibrated_brier_sum3,raw_ece,calibrated_ece,
                 recommended_for_manual_review)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (eid,id,as_z(now),len(holdout),h,raw["log_loss"],
                  post["log_loss"],raw["brier_sum3"],post["brier_sum3"],
                  raw["top1_ece_10bins"],post["top1_ece_10bins"],improved))
                proposals.append({"state":"HOLDO​UT_FROZEN".replace("\u200b",""),
                    "candidate_id":id,"holdout_n":len(holdout),
                    "raw_log_loss":raw["log_loss"],"calibrated_log_loss":post["log_loss"],
                    "raw_brier_sum3":raw["brier_sum3"],"calibrated_brier_sum3":post["brier_sum3"],
                    "manual_review_possible":bool(improved),"auto_activation":False})
    return proposals

def settle_sqlite(db_path,receipts,*,now=None,allow_synthetic=False):
    """Database and prior forecasts must exist. Caller stages a COPY of SQLite.
    Declared synthetic mode is for tests ONLY, live CLI never enables it.
    """
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise SettlementSafetyError("UTC_REQUIRED")
    byleague,proof=preflight_results(receipts,now,allow_synthetic=allow_synthetic)
    path=Path(db_path)
    if not path.is_file():raise SettlementSafetyError("REAL_PREMATCH_DB_MISSING")
    output=[];skipped=Counter();tracked=0
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript((ROOT/"migrations/004_m0_shadow_settlement_and_future_calibration.sql").read_text())
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise SettlementSafetyError("SQLITE_INTEGRITY_FAILED")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise SettlementSafetyError("SQLITE_FK_FAILED")
        records=db.execute("""SELECT p.forecast_id,p.provider_match_id,p.league_country,
          p.kickoff_utc,p.generated_at_utc,p.feature_cutoff_utc,
          p.p_1,p.p_x,p.p_2,p.feature_sha256,p.parameter_sha256,
          mr.provider_home_team_id,mr.provider_away_team_id
          FROM m0_shadow_1x2_forecasts p
          JOIN m0_forward_feature_records mr
            ON mr.feature_snapshot_id=p.feature_snapshot_id
          ORDER BY p.league_country,p.provider_match_id""").fetchall()
        if not records:raise SettlementSafetyError("NO_ACTUAL_FROZEN_M0_FORECASTS_TO_MONITOR")
        db.execute("BEGIN IMMEDIATE")
        try:
            for country,(rec,matches) in byleague.items():
                db.execute("""INSERT OR IGNORE INTO m0_shadow_result_sources
                  (source_id,league_country,season,captured_at_utc,payload_sha256,chain_sha256)
                  VALUES(?,?,?,?,?,?)""",
                  (rec["chain_sha256"],country,CURRENT,rec["completed_at_utc"],
                   rec["payload_sha256"],rec["chain_sha256"]))
            for rec in records:
                (forecast_id,mid,country,kickoff,generated,cutoff,p1,px,p2,
                 feature_sha,param_sha,home_id,away_id)=rec
                tracked+=1
                row={"provider_match_id":mid,"provider_home_team_id":home_id,
                    "provider_away_team_id":away_id,"kickoff_utc":kickoff}
                src,matches=byleague[country]
                status,values=classify_result(matches.get(mid),row,
                                                as_utc(src["completed_at_utc"]))
                prior=db.execute("""SELECT home_goals_90,away_goals_90,source_id
                    FROM m0_shadow_1x2_settlements WHERE forecast_id=?""",
                    (forecast_id,)).fetchone()
                if prior:
                    if status=="SETTLE" and (prior[0],prior[1])!=values[:2]:
                        # Never overwrite a disputed historical outcome.
                        raise SettlementSafetyError("PREVIOUS_FINAL_RESULT_CHANGED_REQUIRES_REVIEW")
                    skipped["ALREADY_SETTLED"]+=1
                    continue
                if status!="SETTLE":
                    skipped[status]+=1
                    continue
                if not as_utc(generated)<as_utc(kickoff)-timedelta(minutes=90):
                    raise SettlementSafetyError("FORECAST_NOT_FROZEN_BEFORE_MATCH")
                if as_utc(cutoff)>as_utc(generated):
                    raise SettlementSafetyError("SOURCE_FEATURES_NOT_AVAILABLE_AT_FORECAST")
                h,a,label=values
                p={"1":p1,"X":px,"2":p2}
                ll,bs=score_one(p,label) # independently tested original math
                winner=max(("1","X","2"),key=lambda k:p[k])
                correct=int(label==winner)
                audit={"schema":SCHEMA,"forecast_id":forecast_id,"fixture_id":mid,
                    "country":country,"source_sha":src["chain_sha256"],
                    "result":{"home":h,"away":a,"label":label},
                    "metrics":{"log_loss":ll,"brier_sum3":bs,"top1_correct":correct}}
                proof_id=sha(audit)
                db.execute("""INSERT INTO m0_shadow_1x2_settlements
                  (settlement_id,forecast_id,source_id,observed_at_utc,
                   provider_match_id,league_country,kickoff_utc,
                   home_goals_90,away_goals_90,result_1x2,
                   log_loss,brier_sum3,top1_correct,audit_sha256)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (proof_id,forecast_id,src["chain_sha256"],src["completed_at_utc"],
                   mid,country,kickoff,h,a,label,ll,bs,correct,proof_id))
                output.append({"forecast_id":forecast_id,"league":country,
                   "result":f"{h}:{a}","result_1x2":label,
                   "log_loss":ll,"brier_sum3":bs,"top1_correct":correct,
                   "source_receipt_sha256":src["chain_sha256"]})
            calibration=_calibration(db,now)
            audits=_aggregate(db)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        total=db.execute("SELECT COUNT(*) FROM m0_shadow_1x2_settlements").fetchone()[0]
        fit=db.execute("SELECT COUNT(*) FROM m0_shadow_calibration_candidates").fetchone()[0]
        evals=db.execute("SELECT COUNT(*) FROM m0_shadow_calibration_evaluations").fetchone()[0]
        if db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]!=0:
            raise SettlementSafetyError("ORIGINAL_STRICT_PIT_PREDICTIONS_MODIFIED")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise SettlementSafetyError("SQLITE_FK_FAILED_AFTER_SETTLEMENT")
    report={"schema":SCHEMA,"run_utc":as_z(now),
       "source_completed_utc":{k:v[0]["completed_at_utc"] for k,v in byleague.items()},
       "source_chain_sha256":proof["final_chain_sha256"],
       "source_requests":len(receipts),"eligible_forecasts_monitored":tracked,
       "newly_settled_1x2":len(output),"cumulative_settled_1x2":total,
       "skipped_counts":dict(sorted(skipped.items())),
       "new_settlements":output,"quality_by_model_and_league":audits,
       "calibration_candidates_total":fit,"holdout_reviews_total":evals,
       "calibration_changes_today":calibration,
       "min_calibration_sample":MIN_FIT,"min_later_unseen_sample":MIN_HOLDOUT,
       "future_calibration_auto_activation":False,
       "original_Premier_League_2026_27_TEST_not_queried":True,
       "original_M1_gate14_pass":False,
       "actual_source_is_network_observed_not_provider_first_published":True}
    report["sha256"]=sha(report)
    return report

def collect(*,db_path,out_dir,public_pem,api_key,client_factory=None,now=None):
    if not api_key:raise SettlementSafetyError("EXISTING_SECRET_MISSING")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise SettlementSafetyError("UTC_REQUIRED")
    directory=Path(out_dir);path=Path(db_path)
    if directory.exists():raise SettlementSafetyError("IMMUTABLE_DAILY_SETTLEMENT_EXISTS")
    if not path.is_file():raise SettlementSafetyError("REAL_SQLITE_MISSING")
    directory.mkdir(parents=True,exist_ok=False)
    staged=directory/"staged.sqlite"
    shutil.copy2(path,staged)
    try:
        client=client_factory(api_key=api_key)
        receipts=[]
        def capture(label,method,*args,**kwargs):
            start=utc_now()
            payload=to_plain(method(*args,**kwargs))
            end=utc_now()
            if not isinstance(payload,dict):raise SettlementSafetyError("NOT_JSON_PITCHAPI")
            add_observation(receipts,resource=label,payload=payload,
                started=start,completed=end)
            return payload
        catalog=capture("pitchapi:catalog",client.leagues.list)
        ids=select_three(catalog)
        for title,country,count,lid in ids:
            capture(f"pitchapi:result:{country}:{CURRENT}",
                client.leagues.matches,lid,season=CURRENT,status="all")
        if len(receipts)!=MAX_CALLS:
            raise SettlementSafetyError("FOUR_ACTUAL_REQUESTS_REQUIRED")
        source=seal(receipts,public_pem,
            directory/"M0_RESULTS_ORIGINAL_PITCHAPI.enc",
            directory/"M0_RESULTS_ORIGINAL_PITCHAPI.manifest.json")
        completed=datetime.now(timezone.utc)
        report=settle_sqlite(staged,receipts,now=completed)
        report["ciphertext_sha256"]=source["ciphertext_sha256"]
        report["source_raw_sha256"]=source["raw_sha256"]
        report["sqlite_sha256"]=hashlib.sha256(staged.read_bytes()).hexdigest()
        report["sha256"]=sha({k:v for k,v in report.items() if k!="sha256"})
        (directory/"M0_DAILY_SETTLEMENT_AUDIT.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
            encoding="utf8")
        os.replace(staged,path)
        return report
    except BaseException:
        shutil.rmtree(directory,ignore_errors=True)
        raise

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",default="data/forward_m0/kb3_forward_m0.sqlite")
    parser.add_argument("--base",default="data/settlements/m0_shadow_daily")
    parser.add_argument("--public-key",default="config/step11_archive_recipient_public.pem")
    args=parser.parse_args()
    day=datetime.now(timezone.utc).date().isoformat()
    out=Path(args.base)/day
    if out.exists():
        print("M0_SETTLEMENT_ALREADY_ARCHIVED_TODAY",day)
        return
    try:
        report=collect(db_path=args.db,out_dir=out,
          public_pem=args.public_key,api_key=os.environ.get("PITCHAPI_API_KEY",""))
        print(json.dumps({"state":"REAL_M0_SETTLEMENT_AUDIT_ARCHIVED",
          "newly_settled":report["newly_settled_1x2"],
          "total_settled":report["cumulative_settled_1x2"],
          "calibration_fit_count":report["calibration_candidates_total"],
          "holdout_evaluation_count":report["holdout_reviews_total"],
          "source_calls":report["source_requests"],"GATE14_PASS":False}))
    except Exception as e:
        print("M0_SETTLEMENT_BLOCKED",type(e).__name__,
              str(e) if isinstance(e,SettlementSafetyError) else "OPAQUE")
        raise SystemExit(3)
if __name__=="__main__":
    main()
