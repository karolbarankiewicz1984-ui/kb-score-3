"""Actual future-only M0 SHADOW 1X2 settlement, log loss, Brier and safe calibration.

Strictly separated from original M1 GATE14 and frozen PL TEST 2026/27.
Labels ONLY from authenticated real current fixture responses observed after
target end (+3h). No result may change an existing forecast or settlement.
Calibrator fit at first >=100 independent fixtures; holdout >=50 fixtures
whose actual kickoffs are AFTER fitted_at. No automatic model activation.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
from hashlib import sha256
import json,math,sqlite3
from src.kb3_pit_ledger import as_utc,canonical
from src.kb3_step14_m1_math_calibration import (
    score_one,score_predictions,fit_temperature,evaluate_calibrated_holdout)
from src.kb3_three_league_sqlite_forward_features import MODEL,ROOT
from src.kb3_m0_shadow_1x2_live_freeze import VERSION as FORECAST_SCHEMA
from scripts.step14_three_league_pitchapi_actual_audit import CURRENT,LEAGUES
from src.kb3_pitch_native import check_season

RESULT_LAG=timedelta(hours=3)
POLICY_MODEL="M0_ELO_POISSON_UNFITTED_SHADOW_FEATURES_V1"
SCHEMA="kb3-real-PitchAPI-M0-1X2-settle-logloss-brier-sum3-and-forward-calibration-v1"
SCOPE="ESP_ITA_GER_POOLED_RESEARCH"
class ResultSafetyError(ValueError):pass

def utc_string(d):
    return d.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
def sealhash(obj):
    return sha256(canonical(obj)).hexdigest()

def _source_mapping(real_observations,now):
    """Require full native league season identity and authentic network clocks."""
    expected={c:n for c,_,n,_ in LEAGUES}
    if set(real_observations)!=set(expected):
        raise ResultSafetyError("NEED_EXACT_THREE_LEAGUE_REAL_NETWORK_SOURCES")
    catalog={}
    for country,(source,items) in real_observations.items():
        if source.get("origin")!="NETWORK_OBSERVED":
            raise ResultSafetyError("RESULTS_NOT_NETWORK_OBSERVED")
        if source.get("resource")!="pitchapi:postmatch:"+country+":"+CURRENT:
            raise ResultSafetyError("RESULT_SOURCE_WRONG_COMPETITION_OR_YEAR")
        if as_utc(source["completed_at_utc"])>now:
            raise ResultSafetyError("RESULT_OBSERVED_IN_FUTURE")
        if (not isinstance(source.get("payload_sha256"),str)
            or len(source["payload_sha256"])!=64):
            raise ResultSafetyError("ORIGINAL_RESPONSE_HASH_REQUIRED")
        if not isinstance(items,list):raise ResultSafetyError("INVALID_MATCH_FIXTURE_SOURCE")
        check_season(items,CURRENT,expected_count=expected[country])
        ids=set()
        for game in items:
            if game["id"] in ids:raise ResultSafetyError("DUPLICATE_MATCH_IN_PROVIDER")
            ids.add(game["id"])
        catalog[country]=(source,{m["id"]:m for m in items})
    return catalog

def _forecast_index(db):
    rows=db.execute("""SELECT p.forecast_id,p.fixture_id,p.league_country,
       p.provider_match_id,p.kickoff_utc,p.generated_at_utc,
       p.p_1,p.p_x,p.p_2,p.prediction_payload_sha256,p.feature_snapshot_id,
       f.kickoff_utc,mr.provider_home_team_id,mr.provider_away_team_id,
       p.status,p.model_version_id,p.phase,fs.feature_hash,
       mr.signed_source_chain_sha256
      FROM m0_shadow_1x2_forecasts p
      JOIN fixtures f ON f.fixture_id=p.fixture_id
      JOIN m0_forward_feature_records mr ON mr.feature_snapshot_id=p.feature_snapshot_id
      JOIN feature_snapshots fs ON fs.feature_snapshot_id=mr.feature_snapshot_id
      WHERE NOT EXISTS (SELECT 1 FROM m0_shadow_1x2_settlements s
          WHERE s.forecast_id=p.forecast_id)
      ORDER BY p.kickoff_utc,p.forecast_id""").fetchall()
    return rows

def settle(db_path,real_observations,*,now=None):
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise ResultSafetyError("UTC_REQUIRED")
    sources=_source_mapping(real_observations,now)
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript((ROOT/"migrations/004_m0_shadow_settlements_and_calibration.sql").read_text())
        pending=_forecast_index(db); accepted=[]; skipped={}; errors=[]
        for (fid,fixture_id,country,mid,kickoff_utc,pred_time,p1,px,p2,
             pred_sha,source_feature_id,db_kickoff,home_id,away_id,status,model,phase,
             fhash,chain) in pending:
            if country not in ("ESP","ITA","GER") or model!=MODEL or phase!="EARLY" or status!="SHADOW_UNFITTED_NOT_FOR_BETTING":
                raise ResultSafetyError("NONRESEARCH_MODEL_OR_TEST_PREDICTION")
            if db_kickoff!=kickoff_utc or not chain or len(chain)!=64:
                raise ResultSafetyError("FROZEN_ID_OR_ORIGINAL_SOURCE_CHANGED")
            kickoff=as_utc(kickoff_utc)
            if not as_utc(pred_time)+timedelta(minutes=90)<kickoff:
                raise ResultSafetyError("PREDICTION_NOT_FROZEN_90_MIN_EARLY")
            if not (0<p1<1 and 0<px<1 and 0<p2<1) or abs(p1+px+p2-1)>1e-10:
                raise ResultSafetyError("FROZEN_1X2_INVALID")
            if kickoff+RESULT_LAG>now:
                skipped["TOO_EARLY"] =skipped.get("TOO_EARLY",0)+1;continue
            src,byid=sources[country]
            m=byid.get(mid)
            if m is None:raise ResultSafetyError("FORECAST_FIXTURE_MISSING_IN_PROVIDER_"+country)
            if (m["time_utc"]!=kickoff_utc or m["home_team"]["id"]!=home_id
                 or m["away_team"]["id"]!=away_id):
                errors.append({"forecast":fid,"reason":"FIXTURE_ID_OR_KICKOFF_CHANGED"})
                continue
            if m["status"]!="finished":
                skipped["NOT_FINAL"] =skipped.get("NOT_FINAL",0)+1
                continue
            gh,ga=m.get("score_home"),m.get("score_away")
            if type(gh) is not int or type(ga) is not int or not (0<=gh<=30 and 0<=ga<=30):
                errors.append({"forecast":fid,"reason":"INVALID_REGULATION_RESULT"})
                continue
            settled_at=as_utc(src["completed_at_utc"])
            if settled_at<kickoff+RESULT_LAG:
                raise ResultSafetyError("SOURCE_FINISHED_BEFORE_MINIMUM_LAG")
            label="1" if gh>ga else "2" if gh<ga else "X"
            ll,brier=score_one({"1":p1,"X":px,"2":p2},label)
            item={"schema":SCHEMA,"forecast_id":fid,"league_country":country,
                "provider_match_id":mid,"frozen_kickoff_utc":kickoff_utc,
                "forecast_sha256":pred_sha,"observed_at_utc":src["completed_at_utc"],
                "source_sha256":src["payload_sha256"],"score_home":gh,"score_away":ga,
                "label_1x2":label,"log_loss":ll,"brier_sum3":brier}
            sid=sealhash(item);accepted.append((item,sid))
        # Invalid provider correction/fixture ID is a review condition,
        # no silently accepted result for this fixture.
        db.execute("BEGIN IMMEDIATE")
        try:
            for item,sid in accepted:
                db.execute("""INSERT INTO m0_shadow_1x2_settlements
                  (settlement_id,forecast_id,league_country,provider_match_id,
                   frozen_kickoff_utc,actual_result_observed_at_utc,
                   source_snapshot_sha256,observed_score_home,observed_score_away,
                   outcome_1x2,log_loss,brier_sum3,settlement_sha256)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (sid,item["forecast_id"],item["league_country"],item["provider_match_id"],
                   item["frozen_kickoff_utc"],item["observed_at_utc"],item["source_sha256"],
                   item["score_home"],item["score_away"],item["label_1x2"],
                   item["log_loss"],item["brier_sum3"],sid))
            db.commit()
        except BaseException:db.rollback();raise
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ResultSafetyError("SQLITE_FK_POSTMATCH_FAILURE")
        total=db.execute("SELECT COUNT(*) FROM m0_shadow_1x2_settlements").fetchone()[0]
    return {"schema":SCHEMA,"actual_server_check_at_utc":utc_string(now),
        "newly_settled":len(accepted),"total_settled":total,
        "pending_unsettled":len(pending)-len(accepted),
        "skipped_reason_counts":skipped,"review_needed":errors,
        "new_settlements":[item|{"settlement_sha256":sid} for item,sid in accepted],
        "original_M1_gate14_pass":False,"original_PL_2026_27_TEST_used":False}

def _historical_pairs(db,*,model_version=MODEL):
    rows=db.execute("""SELECT s.forecast_id,p.kickoff_utc,s.actual_result_observed_at_utc,
          p.p_1,p.p_x,p.p_2,s.outcome_1x2,p.model_version_id,p.phase,
          p.parameter_sha256,p.generated_at_utc
       FROM m0_shadow_1x2_settlements s
       JOIN m0_shadow_1x2_forecasts p ON p.forecast_id=s.forecast_id
       WHERE p.model_version_id=? AND p.phase='EARLY'
       ORDER BY p.kickoff_utc,p.forecast_id""",(model_version,)).fetchall()
    return [{"id":r[0],"kickoff":as_utc(r[1]),"settled":as_utc(r[2]),
      "p":{"1":r[3],"X":r[4],"2":r[5]},"label":r[6],
      "parameter_sha256":r[9],"generated":as_utc(r[10])} for r in rows]

def _homogeneous_m0_parameter_contract(pairs):
    """Never pool forecasts of distinct parameter snapshots under same model ID."""
    keys={r["parameter_sha256"] for r in pairs}
    if len(keys)>1:
        raise ResultSafetyError("MIXED_M0_PARAMETER_VERSIONS_CANNOT_BE_CALIBRATED_TOGETHER")
    if pairs and (not keys or not all(isinstance(k,str) and len(k)==64 for k in keys)):
        raise ResultSafetyError("M0_PARAMETER_VERSION_SHA_MISSING")
    return next(iter(keys)) if keys else None

def _strict_post_fit_holdout(pairs,fit_at_utc,review_at_utc):
    """Independent post-fit forecasts and outcomes; not pre-fitted future kickoffs."""
    return [r for r in pairs
        if r["generated"]>fit_at_utc
        and r["kickoff"]>fit_at_utc
        and r["settled"]<=review_at_utc]

def audit_and_prepare_calibration(db_path,*,now=None):
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise ResultSafetyError("UTC_REQUIRED")
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript((ROOT/"migrations/004_m0_shadow_settlements_and_calibration.sql").read_text())
        pairs=_historical_pairs(db)
        _homogeneous_m0_parameter_contract(pairs)
        metrics=(score_predictions([x["p"] for x in pairs],[x["label"] for x in pairs])
                 if pairs else None)
        candidate=db.execute("""SELECT candidate_id,fitted_at_utc,fitted_temperature,
           fitting_sample_size FROM m0_shadow_calibration_candidates
           WHERE model_version_id=? AND phase='EARLY' AND scope=?""",
           (MODEL,SCOPE)).fetchone()
        new_candidate=None;review=None;new_review=None
        if candidate is None and len(pairs)>=100:
            sample=[x for x in pairs if x["settled"]<=now][:100]
            if len(sample)>=100:
                fit=fit_temperature([x["p"] for x in sample],
                                    [x["label"] for x in sample],min_rows=100)
                trainsha=sealhash([x["id"] for x in sample])
                payload={"schema":SCHEMA,"scope":SCOPE,"model_version_id":MODEL,
                  "phase":"EARLY","fit_at_utc":utc_string(now),
                  "training_rows":len(sample),"training_ids_sha":trainsha,
                  "temperature":fit["temperature"],"raw_log_loss":fit["calibration_log_loss_raw"],
                  "fit_log_loss":fit["calibration_log_loss_fitted"],
                  "no_auto_activation":True}
                cid=sealhash(payload)
                db.execute("""INSERT INTO m0_shadow_calibration_candidates
                  (candidate_id,model_version_id,phase,scope,calibration_cutoff_utc,
                   fitted_at_utc,fitted_temperature,fitting_sample_size,
                   training_forecast_ids_sha256,raw_fit_log_loss,calibrated_fit_log_loss,
                   candidate_payload_sha256)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (cid,MODEL,"EARLY",SCOPE,utc_string(now),utc_string(now),
                   fit["temperature"],len(sample),trainsha,fit["calibration_log_loss_raw"],
                   fit["calibration_log_loss_fitted"],cid))
                db.commit();candidate=(cid,utc_string(now),fit["temperature"],len(sample))
                new_candidate=payload|{"candidate_sha256":cid}
        if candidate is not None:
            cid,created,temperature,n=candidate
            after=_strict_post_fit_holdout(pairs,as_utc(created),now)
            already_reviewed=db.execute("""SELECT review_id FROM
                m0_shadow_calibration_holdout_reviews WHERE candidate_id=?""",(cid,)).fetchone()
            if len(after)>=50 and not already_reviewed:
                sample=after[:50]
                evaluated=evaluate_calibrated_holdout(
                    [x["p"] for x in sample],[x["label"] for x in sample],
                    {"temperature":temperature})
                raw=evaluated["raw"];cal=evaluated["calibrated"]
                positive=(cal["log_loss"]<raw["log_loss"]
                    and cal["brier_sum3"]<raw["brier_sum3"])
                payload={"schema":SCHEMA,"candidate_id":cid,"reviewed_at_utc":utc_string(now),
                 "holdout_samples":len(sample),"holdout_forecast_ids_sha256":
                     sealhash([x["id"] for x in sample]),
                 "raw_log_loss":raw["log_loss"],"calibrated_log_loss":cal["log_loss"],
                 "raw_brier_sum3":raw["brier_sum3"],"calibrated_brier_sum3":cal["brier_sum3"],
                 "raw_ece_top1":raw["top1_ece_10bins"],
                 "calibrated_ece_top1":cal["top1_ece_10bins"],
                 "positive_both_primary_metrics":positive,
                 "independent_after_fit_kickoff":True,"approved_for_production":False}
                rid=sealhash(payload)
                db.execute("""INSERT INTO m0_shadow_calibration_holdout_reviews
                  (review_id,candidate_id,reviewed_at_utc,independent_post_fit_matches,
                   holdout_forecast_ids_sha256,raw_log_loss,calibrated_log_loss,
                   raw_brier_sum3,calibrated_brier_sum3,raw_ece_top1,calibrated_ece_top1,
                   improvement_confirmed,approved_for_production,review_sha256)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0,?)""",
                  (rid,cid,utc_string(now),50,payload["holdout_forecast_ids_sha256"],
                   raw["log_loss"],cal["log_loss"],raw["brier_sum3"],cal["brier_sum3"],
                   raw["top1_ece_10bins"],cal["top1_ece_10bins"],int(positive),rid))
                db.commit();new_review=payload|{"review_sha256":rid}
            review={"candidate_id":cid,"temperature":temperature,
                "fitted_rows":n,"future_post_candidate_kickoffs_settled":len(after),
                "holdout_minimum":50,
                "review_completed":bool(already_reviewed or new_review),
                "automatic_activation":False}
        if db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]!=0:
            raise ResultSafetyError("ORIGINAL_STRICT_M1_PREDICTIONS_TOUCHED")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ResultSafetyError("CALIBRATION_FOREIGN_KEY_FAILURE")
    return {"schema":SCHEMA,"as_of_utc":utc_string(now),"scored_independent_matches":len(pairs),
     "diagnostics_available":len(pairs)>=20,"temperature_fit_minimum":100,
     "future_holdout_minimum":50,
     "aggregate_score":metrics,"candidate":review,
     "new_calibration_candidate":new_candidate,"new_holdout_review":new_review,
     "production_calibration_activated":False,"original_TEST_leak":False,
     "historic_M1_gate14_pass":False}
