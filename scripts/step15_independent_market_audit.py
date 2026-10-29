"""KB Score 3.0 / step15 independent real market review.

Audit frozen 374 probability rows and reported 22 market scores WITHOUT
importing the research scorer or fitting either model. Read original
provider result labels a second time only for verification, never training.
Protected 2026/27 TEST is excluded by the original safe source manifest.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
import os
from datetime import date
from pathlib import Path
from collections import defaultdict

from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import (
    _valid_safe,validated_events,
)

FULL="STEP15_ML_VS_M0_374_FULL_REPORT.json"
PROB="STEP15_374_PAIR_GOAL_PROBABILITIES_NO_LABELS.jsonl.gz"
HOME="CATBOOST_GOALS_HOME_720.cbm"
AWAY="CATBOOST_GOALS_AWAY_720.cbm"
SCHEMA="kb3-step15-independent-second-real-provider-score-audit-v1"

class IndependentAuditError(ValueError):pass


def _almost(a,b,tol=1e-10):
    return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol

def _fraction(v):
    if type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>1:
        raise IndependentAuditError("UNSAFE_PROBABILITY")
    return v

def _check_market(pred):
    if not isinstance(pred,dict) or pred.get("match_duration")!="REGULAR_90_MINUTES":
        raise IndependentAuditError("INVALID_DURATION")
    if pred.get("trained_or_calibrated_here") is not False:
        raise IndependentAuditError("UNEXPECTED_CALIBRATOR")
    x=pred["p_1x2"]
    if set(x)!={"1","X","2"} or not _almost(sum(_fraction(v) for v in x.values()),1):
        raise IndependentAuditError("INVALID_NORMALIZATION")
    for key in ("1.5","2.5","3.5"):
        if not _almost(_fraction(pred["p_over"][key])+_fraction(pred["p_under"][key]),1):
            raise IndependentAuditError("OVER_UNDER_NOT_COMPLEMENTS")
    if not (pred["p_over"]["1.5"]>=pred["p_over"]["2.5"]-1e-10
            and pred["p_over"]["2.5"]>=pred["p_over"]["3.5"]-1e-10):
        raise IndependentAuditError("OVER_MONOTONICITY_FAIL")
    if not _almost(_fraction(pred["p_btts"]["yes"])+_fraction(pred["p_btts"]["no"]),1):
        raise IndependentAuditError("BTTS_NOT_COMPLEMENTS")
    if pred["p_btts"]["yes"]>pred["p_over"]["1.5"]+1e-10:
        raise IndependentAuditError("BTTS_GREATER_THAN_OVER15")
    for side in ("home","away"):
        exact=pred["team_goals"][side]["exact"]
        more=pred["team_goals"][side]["at_least"]
        if set(exact)!={"0","1","2","3"} or set(more)!={"1+","2+","3+"}:
            raise IndependentAuditError("TEAM_GOALS_SCHEMA")
        for k in range(4):_fraction(exact[str(k)])
        for k in (1,2,3):_fraction(more[str(k)+"+"])
        if not (more["1+"]>=more["2+"]-1e-10 and more["2+"]>=more["3+"]-1e-10):
            raise IndependentAuditError("TEAM_GOAL_MONOTONICITY")
        if not all(_almost(more[str(k)+"+"],1-sum(exact[str(i)] for i in range(k)))
                   for k in (1,2,3)):
            raise IndependentAuditError("EXACT_VS_ATLEAST_INCONSISTENT")
        if pred["p_btts"]["yes"]>more["1+"]+1e-10:
            raise IndependentAuditError("BTTS_TEAM_CONTRADICTION")
    if pred["retained_joint_mass_before_normalization"]<.99999999999:
        raise IndependentAuditError("EXCESS_POISSON_TAIL")
    top=pred["top_5_scorelines"]
    if len(top)!=5 or len({(s["home"],s["away"]) for s in top})!=5:
        raise IndependentAuditError("SCORELINES_MISSING")
    if [x["probability"] for x in top] != sorted(
            (x["probability"] for x in top),reverse=True):
        raise IndependentAuditError("SCORELINE_ORDER")
    return True


def _labels(gh,ga):
    if type(gh) is not int or type(ga) is not int or not 0<=gh<=30 or not 0<=ga<=30:
        raise IndependentAuditError("INVALID_PROVIDER_90MIN_GOALS")
    total=gh+ga
    result={}
    for line in ("1.5","2.5","3.5"):
        at=int(total>float(line))
        result["over_"+line]=at
        result["under_"+line]=1-at
    result["btts_yes"]=int(gh>0 and ga>0)
    result["btts_no"]=1-result["btts_yes"]
    for team,goals in (("home",gh),("away",ga)):
        for n in (1,2,3):result[f"{team}_{n}plus"]=int(goals>=n)
        for n in range(4):result[f"{team}_exact_{n}"]=int(goals==n)
    if len(result)!=22:raise IndependentAuditError("22_LABEL_CONTRACT_FAIL")
    return result


def _binary(pred,labels,name):
    ps=[]; counts=[{"sum_p":0.0,"yes":0,"n":0} for _ in range(5)]
    for r,y in zip(pred,labels):
        p=r[name]
        event=y[name]
        _fraction(p)
        if type(event) is not int or event not in (0,1):
            raise IndependentAuditError("INVALID_LABEL")
        loss_b=(p-event)**2
        loss_l=-(event*math.log(max(p,1e-15))+
                 (1-event)*math.log(max(1-p,1e-15)))
        ps.append((loss_b,loss_l))
        cell=counts[min(4,int(p*5))]
        cell["sum_p"]+=p;cell["yes"]+=event;cell["n"]+=1
    n=len(ps)
    ece=sum(z["n"]/n*abs(z["sum_p"]/z["n"]-z["yes"]/z["n"]) for z in counts if z["n"])
    return {"brier":math.fsum(v[0] for v in ps)/n,
            "log_loss":math.fsum(v[1] for v in ps)/n,
            "ece_5bins":ece}


def _market_dict(x):
    out={}
    for k in ("1.5","2.5","3.5"):
        out["over_"+k]=x["p_over"][k]
        out["under_"+k]=x["p_under"][k]
    out["btts_yes"]=x["p_btts"]["yes"]
    out["btts_no"]=x["p_btts"]["no"]
    for side in ("home","away"):
        for k in (1,2,3):
            out[f"{side}_{k}plus"]=x["team_goals"][side]["at_least"][f"{k}+"]
        for k in range(4):
            out[f"{side}_exact_{k}"]=x["team_goals"][side]["exact"][str(k)]
    if len(out)!=22:return None
    return out


def independent_audit(directory, *, root, native_override=None):
    directory=Path(directory)
    report=json.loads((directory/FULL).read_text())
    if (report.get("schema")!="kb3-step15-independent-ml-goals-catboost-poisson-720-374-v1"
       or report.get("partition_train")!=720
       or report.get("partition_validation")!=374
       or report.get("features_train_only")!=85
       or report.get("all_binary_markets")!=22
       or report.get("unique_markets_for_primary_aggregate")!=18
       or report.get("source_class")!="B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT"
       or report.get("historical_native_PIT_proven") is not False
       or report.get("sealed_2026_27_test_accessed") is not False
       or report.get("val_labels_used_for_training_early_stopping_or_model_selection") is not False
       or report.get("model_promoted") is not False):
        raise IndependentAuditError("RESEARCH_GATE_DRIFT")
    for name in (HOME,AWAY):
        actual_sha=hashlib.sha256((directory/name).read_bytes()).hexdigest()
        if actual_sha!=report["saved_model_sha256"][name]:
            raise IndependentAuditError("MODEL_BYTES_DRIFT_"+name)
    file=directory/PROB
    if hashlib.sha256(file.read_bytes()).hexdigest()!=report["frozen_prediction_sha256"]:
        raise IndependentAuditError("FROZEN_PROBABILITY_HASH_DRIFT")
    frozen=[json.loads(line) for line in gzip.decompress(file.read_bytes()).decode().splitlines()
            if line.strip()]
    ids=[rec["fixture_id"] for rec in frozen]
    if len(ids)!=374 or len(set(ids))!=374:
        raise IndependentAuditError("FROZEN_VALIDATION_IDS_BAD")
    for x in frozen:
        if set(x)!={"fixture_id","partition","kickoff_utc","m0","ml"} or x["partition"]!="VALIDATION":
            raise IndependentAuditError("FROZEN_FILE_CONTAINS_TARGET_OR_UNEXPECTED_FIELD")
        _check_market(x["m0"])
        _check_market(x["ml"])
    original=_valid_safe(root)
    if native_override is None:
        key=os.environ.get("PITCHAPI_API_KEY","")
        if not key:raise IndependentAuditError("PITCHAPI_SECRET_NOT_FOUND")
        native,calls=native_three_seasons(key=key)
    else:native,calls=native_override,0
    result,season_counts,_=validated_events(
        {f"{int(k[:4])}/{int(k[:4])+1}":a for k,a in native.items()},original)
    actual={x["fixture_id"]:x for x in result}
    if len(actual)!=1140:raise IndependentAuditError("NATIVE_1140_NOT_RECHECKED")
    ys=[]
    for x in frozen:
        rec=actual.get(x["fixture_id"])
        if not rec or rec["partition"]!="VALIDATION" or (
            rec["kickoff"].isoformat().replace("+00:00","Z")!=x["kickoff_utc"]
        ):raise IndependentAuditError("FROZEN_PREDICTION_WRONG_NATIVE_RESULT")
        ys.append(_labels(rec["gh"],rec["ga"]))
    pl={k:[_market_dict(row[k]) for row in frozen] for k in ("m0","ml")}
    keys=set(pl["m0"][0])
    if len(keys)!=22 or any(set(p)!=keys for seq in pl.values() for p in seq):
        raise IndependentAuditError("22_MARKET_COVERAGE_FAIL")
    checks=0
    for market in sorted(keys):
        for which in ("m0","ml"):
            recomputed=_binary(pl[which],ys,market)
            supplied=report["markets"][market][which]
            if report["markets"][market]["n"]!=374:
                raise IndependentAuditError("UNMATCHED_N")
            for metric in ("brier","log_loss","ece_5bins"):
                if not _almost(recomputed[metric],supplied[metric],1e-12):
                    raise IndependentAuditError("SCORE_DRIFT_"+market+"_"+which+"_"+metric)
                checks+=1
        for metric in ("brier","log_loss"):
            diff=report["markets"][market]["ml"][metric]-report["markets"][market]["m0"][metric]
            supplied=report["markets"][market]["delta_ml_minus_m0"][metric]
            if not _almost(diff,supplied["delta_mean"],1e-12):
                raise IndependentAuditError("INVALID_PAIRWISE_DELTA_"+market)
            # Interval validation against mean, monotonic sign and finite values.
            if not all(math.isfinite(supplied[k]) for k in ("ci95_lower","ci95_upper")):
                raise IndependentAuditError("NONFINITE_INTERVAL")
            if supplied["ci95_lower"]>supplied["ci95_upper"]:
                raise IndependentAuditError("REVERSED_INTERVAL")
    all_unique=report["primary_macro_18_unique"]["events"]
    if len(all_unique)!=18 or len(set(all_unique))!=18 or not set(all_unique)<=keys:
        raise IndependentAuditError("DUPLICATED_MACRO_MARKETS")
    for which in ("m0","ml"):
        for metric in ("brier","log_loss"):
            macro=math.fsum(report["markets"][k][which][metric] for k in all_unique)/18
            if not _almost(macro,report["primary_macro_18_unique"][which][metric],1e-12):
                raise IndependentAuditError("PRIMARY_MACRO_DRIFT_"+which+"_"+metric)
    actual_counts={}
    for metric in ("brier","log_loss"):
        actual_counts[metric]=sum(report["markets"][k]["ml"][metric]<
                                  report["markets"][k]["m0"][metric] for k in keys)
    if actual_counts["brier"]!=report["counts"]["ml_brier_improved_22"]:
        raise IndependentAuditError("BRIER_IMPROVED_COUNT_DRIFT")
    if actual_counts["log_loss"]!=report["counts"]["ml_log_loss_improved_22"]:
        raise IndependentAuditError("LOGLOSS_IMPROVED_COUNT_DRIFT")
    return {
        "schema":SCHEMA,
        "status":"PASS_INDEPENDENT_SCORE_AND_COHERENCE_VERIFICATION",
        "paired_fixtures":374,
        "all_22_market_score_pairs_verified":True,
        "score_checks":checks,
        "score_types":["binary_brier","binary_log_loss","five_bin_ECE"],
        "models_verified_sha256":True,
        "predictions_verified_sha256":True,
        "all_748_model_by_fixture_market_coherence_checks_pass":True,
        "all_market_definition_labels_from_native_90min_rebuilt":True,
        "actual_counts":actual_counts,
        "macro_18_verified":True,
        "original_test_accessed":False,
        "historical_provider_pit_certified":False,
        "production_promotion":False,
        "formal_step15_pass":False,
        "external_native_provider_calls":calls,
        "full_report_sha256":hashlib.sha256((directory/FULL).read_bytes()).hexdigest(),
        "frozen_sha256":report["frozen_prediction_sha256"],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    report=independent_audit(args.source_dir,root=Path(__file__).resolve().parents[1])
    target=Path(args.out)
    if target.exists():raise IndependentAuditError("APPEND_ONLY")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print("STEP15_INDEPENDENT_AUDIT="+json.dumps(report,sort_keys=True))
    print("STEP15_INDEPENDENT_AUDIT_PASS_AND_G15_PENDING")

if __name__=="__main__":
    main()
