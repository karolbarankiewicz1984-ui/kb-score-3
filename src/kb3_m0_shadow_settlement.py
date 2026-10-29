"""M0: future-only immutable PitchAPI settlements and independent 100+50 review.

No result enters the forecast features. Original frozen probabilities never
change. All outcomes must originate from a CURRENT native 2026/27 live
PitchAPI network response, with 3-hour lag, exact fixture/team/kickoff IDs.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sqlite3,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_pit_ledger import canonical,as_utc,utc_now
from src.kb3_step14_m1_math_calibration import (score_one,score_predictions,fit_temperature,evaluate_calibrated_holdout)
from scripts.pitchapi_step06_audit import to_plain
from scripts.step14_three_league_pitchapi_actual_audit import select_three,CURRENT,LEAGUES
from src.kb3_pitch_native import check_season
ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-m0-real-shadow-settlement-logloss-brier-v1"
MIN_RESULT_LAG=timedelta(hours=3)
class SettlementError(ValueError):pass
def iso(dt):return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
def sha(value):return hashlib.sha256(canonical(value)).hexdigest()

def judge_match(match,forecast,*,observed):
    country,mid,kickoff,published,home_id,away_id,prob=forecast
    if match.get("id")!=mid:raise SettlementError("TARGET_MATCH_ID_MISMATCH")
    if match.get("time_utc")!=kickoff:raise SettlementError("KICKOFF_CHANGED_DO_NOT_SETTLE")
    if match.get("home_team",{}).get("id")!=home_id or match.get("away_team",{}).get("id")!=away_id:
        raise SettlementError("TEAM_IDENTITY_CHANGED")
    kick=as_utc(kickoff)
    if as_utc(published)>=kick-timedelta(minutes=90):
        raise SettlementError("FORECAST_NOT_PREMATCH")
    if observed<kick+MIN_RESULT_LAG:
        return None
    status=match.get("status")
    if status!="finished":return None
    h,a=match.get("score_home"),match.get("score_away")
    if type(h) is not int or type(a) is not int or not(0<=h<=30 and 0<=a<=30):
        raise SettlementError("INVALID_FINAL_90MIN_SCORE")
    label="1" if h>a else "2" if h<a else "X"
    ll,brier=score_one(prob,label)
    return {"result_1x2":label,"goals_home_90":h,"goals_away_90":a,"log_loss":ll,"brier_sum3":brier}

def review_calibration(db,*,now):
    rows=db.execute("""SELECT p.forecast_id,p.kickoff_utc,p.generated_at_utc,p.model_version_id,
       p.parameter_sha256,p.p_1,p.p_x,p.p_2,s.result_1x2,s.settled_at_utc
       FROM m0_shadow_settlements s JOIN m0_shadow_1x2_forecasts p USING(forecast_id)
       ORDER BY p.kickoff_utc,p.forecast_id""").fetchall()
    groups={}
    for r in rows:
        k=(r[3],r[4])
        groups.setdefault(k,[]).append(r)
    out=[]
    for (version,params),items in sorted(groups.items()):
        n=len(items)
        forecasts=[{"1":r[5],"X":r[6],"2":r[7]} for r in items]
        labels=[r[8] for r in items]
        metrics=score_predictions(forecasts,labels) if items else None
        candidate={"model_version":version,"parameter_sha256":params,"phase":"EARLY",
                   "n_unique_resolved":n,"metrics":metrics,"calibration_training_min":100,
                   "later_independent_holdout_min":50,"production_approved":False}
        if n<100:
            candidate["state"]="COLLECTING"
            candidate["needed_for_first_fit"]=100-n
        else:
            fit=fit_temperature(forecasts[:100],labels[:100],min_rows=100)
            candidate["candidate_temperature"]=fit["temperature"]
            candidate["calibration_fit"]=fit
            if n<150:
                candidate["state"]="FITTED_AWAIT_HOLDOUT"
                candidate["needed_for_later_holdout"]=150-n
            else:
                candidate["state"]="EVALUATED_NO_AUTO_APPROVAL"
                candidate["independent_evaluation"]=evaluate_calibrated_holdout(
                    forecasts[100:],labels[100:],fit)
        out.append(candidate)
    if not out:
        out=[{"state":"COLLECTING","n_unique_resolved":0,
              "needed_for_first_fit":100,"calibration_training_min":100,
              "later_independent_holdout_min":50,"production_approved":False}]
    return out

def settle(db_path,client,*,now=None):
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise SettlementError("UTC_REQUIRED")
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript((ROOT/"migrations/004_m0_shadow_settlement_calibration.sql").read_text())
        pending=db.execute("""SELECT p.forecast_id,p.league_country,p.provider_match_id,
            p.kickoff_utc,p.generated_at_utc,mr.provider_home_team_id,
            mr.provider_away_team_id,p.p_1,p.p_x,p.p_2
            FROM m0_shadow_1x2_forecasts p
            JOIN m0_forward_feature_records mr USING(feature_snapshot_id)
            LEFT JOIN m0_shadow_settlements s ON s.forecast_id=p.forecast_id
            WHERE s.forecast_id IS NULL
              AND julianday(p.kickoff_utc)+3.0/24.0<=julianday(?)
            ORDER BY p.kickoff_utc,p.forecast_id""",(iso(now),)).fetchall()
        pending_countries={x[1] for x in pending}
        catalog=to_plain(client.leagues.list()) if pending else None
        selected=select_three(catalog) if pending else []
        ids={x[1]:x[3] for x in selected}
        source={}
        for country in sorted(pending_countries):
            start=datetime.now(timezone.utc)
            resp=to_plain(client.leagues.matches(ids[country],season=CURRENT,status="all"))
            end=datetime.now(timezone.utc)
            expected=next(n for c,aliases,n,title in LEAGUES if c==country)
            m=resp.get("matches")
            check_season(m,CURRENT,expected_count=expected)
            source[country]=(end,{x["id"]:x for x in m},sha(resp))
        saved=[]
        for fid,country,mid,kickoff,generated,h,a,p1,px,p2 in pending:
            if mid not in source[country][1]:
                raise SettlementError("PITCHAPI_TARGET_MISSING_FROM_LIVE_LEAGUE")
            observed,byid,source_sha=source[country]
            result=judge_match(byid[mid],(country,mid,kickoff,generated,h,a,
                                     {"1":p1,"X":px,"2":p2}),observed=observed)
            if result is None:continue
            entry={"forecast_id":fid,"country":country,"source_observed_utc":iso(observed),
                   "source_payload_sha256":source_sha,"source_season":CURRENT,
                   "result_kickoff_utc":kickoff,**result}
            entry["settled_at_utc"]=iso(datetime.now(timezone.utc))
            entry["settlement_sha256"]=sha(entry)
            db.execute("""INSERT INTO m0_shadow_settlements
               (forecast_id,result_1x2,goals_home_90,goals_away_90,
                source_observed_utc,result_kickoff_utc,source_season,
                source_payload_sha256,source_chain_sha256,
                log_loss,brier_sum3,settled_at_utc,settlement_sha256)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                fid,result["result_1x2"],result["goals_home_90"],result["goals_away_90"],
                entry["source_observed_utc"],kickoff,CURRENT,source_sha,
                source_sha,result["log_loss"],result["brier_sum3"],
                entry["settled_at_utc"],entry["settlement_sha256"]))
            saved.append(entry)
        db.commit()
        reviews=review_calibration(db,now=now)
        total=db.execute("SELECT COUNT(*) FROM m0_shadow_settlements").fetchone()[0]
        if db.execute("PRAGMA foreign_key_check").fetchall():raise SettlementError("FOREIGN_KEY_FAILURE")
        if db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]:
            raise SettlementError("ORIGINAL_STRICT_PIT_PREDICTIONS_TOUCHED")
    return {"schema":SCHEMA,"now_utc":iso(now),"newly_settled":len(saved),
            "total_settled":total,"remaining_pending":len(pending)-len(saved),
            "individual_settlements":saved,"calibration_reviews":reviews,
            "automatic_production_calibration":False,
            "original_heldout_PL_TEST_accessed":False,"original_M1_gate14_pass":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="data/forward_m0/kb3_forward_m0.sqlite")
    p.add_argument("--out-dir",default="data/audits/m0_shadow_settlements")
    a=p.parse_args()
    from pitchapi import PitchAPI
    key=os.environ.get("PITCHAPI_API_KEY")
    if not key:raise SystemExit("MISSING_EXISTING_PITCHAPI_API_KEY")
    now=datetime.now(timezone.utc)
    root=Path(a.out_dir)/now.date().isoformat()
    root.mkdir(parents=True,exist_ok=True)
    path=root/"M0_SETTLEMENT_LOGLOSS_BRIER_AND_CALIBRATION.json"
    if path.exists():
        print("SETTLEMENT_DAY_ALREADY_ARCHIVED",path)
        return
    result=settle(a.db,PitchAPI(api_key=key),now=now)
    result["report_sha256"]=sha(result)
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps({"state":"ACTUAL_M0_SETTLEMENT_AUDITED","new":result["newly_settled"],
      "total":result["total_settled"],"reviews":[{"state":x["state"],"n":x["n_unique_resolved"]} for x in result["calibration_reviews"]]}))
if __name__=="__main__":main()
