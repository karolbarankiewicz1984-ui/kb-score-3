"""KB3 step15: reproducible real goal-market evaluation on M1-R's 374 VAL.

Retrospective research only: 720 earlier TRAIN / 374 VALIDATION; historic
provider publication times unproved. NEVER reads 2026/27 protected TEST.
Same existing native three-season PitchAPI collection as audited step14.
Validation 90-minute final scores are consulted only after TRAIN-only M0 fit
and all 374 predictions have been generated in memory.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from scripts.step14_m1r_train_real_catboost_720_evaluate_374 import (
    ROOT, load_frozen, prepare_features,
)
from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import (
    _valid_safe, validated_events,
)
from src.kb3_step13_retrospective import _train_poisson
from src.kb3_step15_goal_markets import forecast_goal_markets, validate_goal_markets

SCHEMA = "kb3-step15-374-real-90min-goal-market-validation-research-v1"
MIN_PROB = 1e-15


class Step15EvalError(ValueError):
    pass


def _score_binary(rows):
    """Binary Brier, log loss and 5-bin reliability; rows are (p,y)."""
    if not isinstance(rows, list) or not rows:
        raise Step15EvalError("EMPTY_MARKET_SAMPLE")
    briers, losses = [], []
    bins = [{"n":0,"sum_p":0.0,"positive":0} for _ in range(5)]
    for p, y in rows:
        if (type(p) not in (int, float) or not math.isfinite(p)
                or not 0 <= p <= 1 or type(y) is not int or y not in (0,1)):
            raise Step15EvalError("INVALID_BINARY_SAMPLE")
        briers.append((p-y)**2)
        losses.append(-y*math.log(max(p, MIN_PROB))
                      -(1-y)*math.log(max(1-p,MIN_PROB)))
        rec=bins[min(4,int(5*p))]
        rec["n"]+=1
        rec["sum_p"]+=p
        rec["positive"]+=y
    n=len(rows)
    ece=sum(rec["n"]/n*abs(rec["sum_p"]/rec["n"]-
                           rec["positive"]/rec["n"])
            for rec in bins if rec["n"])
    return {
        "n":n,
        "brier":math.fsum(briers)/n,
        "log_loss":math.fsum(losses)/n,
        "ece_5bins":ece,
        "reliability_5bins":[{
            "bin":i,"n":rec["n"],
            "mean_probability":rec["sum_p"]/rec["n"] if rec["n"] else None,
            "observed_frequency":rec["positive"]/rec["n"] if rec["n"] else None
        } for i,rec in enumerate(bins)],
    }


def _outcomes(gh, ga):
    if type(gh) is not int or type(ga) is not int or not 0 <= gh <= 30 or not 0 <= ga <= 30:
        raise Step15EvalError("INVALID_REAL_90MIN_SCORE")
    n=gh+ga
    result={}
    for line, cut in (("1.5",1),("2.5",2),("3.5",3)):
        result["over_"+line]=int(n>cut)
        result["under_"+line]=int(n<=cut)
    result["btts_yes"]=int(gh>=1 and ga>=1)
    result["btts_no"]=1-result["btts_yes"]
    for side, goals in (("home",gh),("away",ga)):
        for k in range(1,4):
            result[f"{side}_{k}plus"]=int(goals>=k)
        for k in range(4):
            result[f"{side}_exact_{k}"]=int(goals==k)
    return result


def _prediction_markets(pred):
    validate_goal_markets(pred)
    result={}
    for line in ("1.5","2.5","3.5"):
        result["over_"+line]=pred["p_over"][line]
        result["under_"+line]=pred["p_under"][line]
    result["btts_yes"]=pred["p_btts"]["yes"]
    result["btts_no"]=pred["p_btts"]["no"]
    for side in ("home","away"):
        for k in range(1,4):
            result[f"{side}_{k}plus"]=pred["team_goals"][side]["at_least"][str(k)+"+"]
        for k in range(4):
            result[f"{side}_exact_{k}"]=pred["team_goals"][side]["exact"][str(k)]
    return result


def evaluate(*, root=ROOT, native_override=None):
    root=Path(root)
    source, rows=load_frozen(root)
    train, valid, _, _, _=prepare_features(rows)
    allowed=_valid_safe(root)
    if native_override is None:
        token=os.environ.get("PITCHAPI_API_KEY","")
        if not token:
            raise Step15EvalError("EXISTING_PITCHAPI_SECRET_REQUIRED")
        native, calls=native_three_seasons(key=token)
    else:
        native,calls=native_override,0
    events,counts,stable=validated_events(
        {f"{int(k[:4])}/{int(k[:4])+1}":m for k,m in native.items()},allowed)
    actual={m["fixture_id"]:m for m in events}
    if len(actual)!=1140 or len(train)!=720 or len(valid)!=374:
        raise Step15EvalError("UNEXPECTED_FROZEN_PARTITIONS")
    for row in train+valid:
        match=actual.get(row["fixture_id"])
        if (not match or match["partition"]!=row["partition"]
                or match["kickoff"].isoformat().replace("+00:00","Z")!=row["kickoff_utc"]):
            raise Step15EvalError("NATIVE_TARGET_ID_OR_KICKOFF_DRIFT")
    # Only historical TRAIN scores enter fitting. Never choose params on VAL.
    fit_rows=[]
    for row in train:
        goal=actual[row["fixture_id"]]
        elo=row["m1r_BASE_121_numeric_features"]["elo_home_minus_away"]
        fit_rows.append((elo/400,goal["gh"],goal["ga"]))
    fitted=_train_poisson(fit_rows)

    # Freeze every VALIDATION prediction before any VAL target is scored.
    predictions=[]
    for row in valid:
        feat=row["m1r_BASE_121_numeric_features"]
        pred=forecast_goal_markets(feat["home_elo"],feat["away_elo"],fitted)
        predictions.append((row["fixture_id"],_prediction_markets(pred),pred["p_1x2"]))
    n=374
    targets=[_outcomes(actual[ident]["gh"],actual[ident]["ga"])
             for ident,_,_ in predictions]
    markets=sorted(predictions[0][1])
    if any(set(item[1])!=set(markets) for item in predictions):
        raise Step15EvalError("MARKET_COVERAGE_DRIFT")
    evaluated={k:_score_binary([
        (prediction[1][k],labels[k]) for prediction,labels in zip(predictions,targets)
    ]) for k in markets}
    if any(z["n"]!=n for z in evaluated.values()):
        raise Step15EvalError("MISSING_VALIDATION_COVERAGE")
    # Independent 1X2 benchmark must recover the known research M0 720/374.
    logloss, brier = [], []
    for (ident,_,p) in predictions:
        match=actual[ident]
        correct="1" if match["gh"]>match["ga"] else "X" if match["gh"]==match["ga"] else "2"
        logloss.append(-math.log(max(p[correct],MIN_PROB)))
        brier.append(sum((p[k]-int(k==correct))**2 for k in ("1","X","2")))
    old=json.loads((root/"data/audits/STEP14_GATE_B_INDEPENDENT_FINAL_ACCEPTANCE_2026-10-29.json").read_text())
    reference=old["score_comparison"]["m0_same720"]
    if (abs(math.fsum(logloss)/n-reference["log_loss"])>1e-9
            or abs(math.fsum(brier)/n-reference["brier_multiclass_sum3"])>1e-9):
        raise Step15EvalError("M0_1X2_374_REFERENCE_DRIFT")
    return {
        "schema":SCHEMA,
        "status":"RESEARCH_VALIDATION_ONLY_NOT_PRODUCTION",
        "source_class":"B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT",
        "historical_publication_proof":False,
        "train":len(train),
        "validation":len(valid),
        "frozen_1x2_ref_matched":True,
        "reference_1x2_val_log_loss":math.fsum(logloss)/n,
        "reference_1x2_val_brier_sum3":math.fsum(brier)/n,
        "market_count":len(markets),
        "market_metrics":evaluated,
        "source_1140_rows":source["matrix_rows"],
        "native_api_calls":calls,
        "native_counts":counts,
        "native_team_continuity":stable,
        "m0_fitted_on_train_only":True,
        "val_labels_used_in_fit_or_selection":False,
        "protected_test_2026_27_accessed":False,
        "catboost_m1r_retrained":False,
        "model_promoted_or_calibrated":False,
        "gate15_formal_pass":False,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    dest=Path(args.out)
    if dest.exists():
        raise Step15EvalError("APPEND_ONLY_RESULT_EXISTS")
    report=evaluate()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
        "validation":report["validation"],
        "market_count":report["market_count"],
        "over_2.5":report["market_metrics"]["over_2.5"],
        "btts_yes":report["market_metrics"]["btts_yes"],
        "protected_test":report["protected_test_2026_27_accessed"],
    },sort_keys=True))
    print("STEP15_REAL_374_RESEARCH_COMPLETE__GATE15_PENDING")


if __name__=="__main__":
    main()
