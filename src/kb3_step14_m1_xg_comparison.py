"""CatBoost M1 offline SYNTHETIC 1/X/2 paired xG vs no-xG experiment.

Strictly zero real data access. Both variants get identical 90 training
labels and identical 30 later validation labels. Temperature fitted only
on chronologically *earlier* validation rows, then evaluated later.
No production activation, no real model metrics, no official TEST.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import json
import math
import random

from src.kb3_step14_synthetic import (
    synthetic_rows,validate_dataset,_matrix,SEED,LABELS,BASE,FEATURES,
)
from src.kb3_step14_m1_math_calibration import (
    CLASSES,order_probability,score_predictions,score_one,
    fit_temperature,evaluate_calibrated_holdout
)

SCHEMA="kb3-step14-synthetic-m1-paired-math-xg-calibration-v1"
CONFIG=dict(iterations=36,depth=3,learning_rate=0.08,loss_function="MultiClass",
            random_seed=SEED,thread_count=1,allow_writing_files=False,verbose=False)

class DemoError(ValueError):pass

def _model_predictions(train,valid,use_xg):
    from catboost import CatBoostClassifier,Pool
    xtrain,names=_matrix(train,use_xg)
    xvalid,_=_matrix(valid,use_xg)
    model=CatBoostClassifier(**CONFIG)
    model.fit(Pool(xtrain,[r["label_1x2"] for r in train],feature_names=list(names)))
    classes=[str(x) for x in model.classes_]
    if len(classes)!=3 or set(classes)!=set(CLASSES):
        raise DemoError("CATBOOST_CLASS_ORDER_CHANGED")
    raw=model.predict_proba(Pool(xvalid,feature_names=list(names)))
    predictions=[]
    for row in raw:
        p={label:float(row[classes.index(label)]) for label in CLASSES}
        order_probability(p)
        predictions.append(p)
    return predictions,tuple(names),classes

def _paired_differences(a,b,ys,*,repetitions=1000):
    if not a or len(a)!=len(b) or len(a)!=len(ys):
        raise DemoError("NOT_SAME_VALIDATION_ROWS")
    log=[];brier=[];wins=0;losses=0
    for pa,pb,y in zip(a,b,ys):
        la,ba=score_one(pa,y);lb,bb=score_one(pb,y)
        log.append(lb-la);brier.append(bb-ba)
        wins+=lb<la;losses+=lb>la
    n=len(log)
    mean=sum(log)/n
    rng=random.Random(SEED)
    means=[]
    for _ in range(repetitions):
        means.append(sum(log[rng.randrange(n)] for _ in range(n))/n)
    means.sort()
    return {"label":"WITH_XG_MINUS_NO_XG; negative value means better WITH_XG",
            "n_paired":n,"mean_log_loss_difference":mean,
            "mean_brier_sum3_difference":sum(brier)/n,
            "with_xg_better_rows":wins,"without_xg_better_rows":losses,
            "tie_rows":n-wins-losses,
            "descriptive_paired_bootstrap_95pct_log_loss_interval":
                 [means[int(0.025*(repetitions-1))],means[int(0.975*(repetitions-1))]],
            "bootstrap_seed":SEED,
            "not_a_statistically_independent_real_match_sample":True}

def run_demo():
    train,valid=validate_dataset(synthetic_rows())
    labels=[r["label_1x2"] for r in valid]
    if not (len(train)==90 and len(valid)==30 and
            [r["fixture_id"] for r in valid] ==
            [f"SYNTH14_SYNTH_VALIDATION_{i:03d}" for i in range(30)]):
        raise DemoError("FROZEN_SYNTHETIC_VALIDATION_ROWS_CHANGED")
    variants={}
    forecasts={}
    for use_xg,tag in [(False,"NO_XG"),(True,"WITH_XG_MASKS")]:
        pred,names,model_order=_model_predictions(train,valid,use_xg)
        if (not use_xg and names!=BASE) or (use_xg and names!=FEATURES):
            raise DemoError("FEATURE_CONTRACT_CHANGED")
        forecasts[tag]=pred
        variants[tag]={
            "feature_names":list(names),
            "feature_count":len(names),
            "catboost_native_class_order":model_order,
            "aligned_probability_order":list(CLASSES),
            "all_30_synthetic_valid":score_predictions(pred,labels),
        }
    # Calibration design: time-ordered split. The 30 valid labels
    # cannot simultaneously calibrate and evaluate the same fit.
    ncal=15
    cut_label=valid[ncal]["kickoff_utc"]
    for tag,pred in forecasts.items():
        fit=fit_temperature(pred[:ncal],labels[:ncal],min_rows=10)
        test=evaluate_calibrated_holdout(pred[ncal:],labels[ncal:],fit)
        variants[tag]["calibration_fit_earlier_15"]=fit
        variants[tag]["later_15_untouched_calibration_evaluation"]=test
    diff=_paired_differences(forecasts["NO_XG"][ncal:],
                             forecasts["WITH_XG_MASKS"][ncal:],labels[ncal:])
    missing=[r["features"] for r in valid]
    data_sha=sha256(json.dumps(
        {"rows":synthetic_rows(),"config":CONFIG},sort_keys=True,
        separators=(",",":")).encode()).hexdigest()
    return {
        "schema":SCHEMA,
        "sample_type":"SYNTHETIC_CODE_GENERATED_ONLY",
        "engine":"CatBoost CPU 1.2.8 MultiClass",
        "catboost_fixed_config":CONFIG,
        "synthetic_dataset_and_config_sha256":data_sha,
        "train_count":90,"validation_count":30,
        "validation_calibration_count":15,
        "validation_later_evaluation_count":15,
        "later_evaluation_first_kickoff_utc":cut_label,
        "class_order":list(CLASSES),
        "both_variants_same_frozen_labels_and_fixtures":True,
        "no_xg_uses_xg_or_missing_masks":False,
        "with_xg_preserves_nullable_xg_and_missing_mask":True,
        "validation_partial_or_fully_missing_xg_rows":{
            "home":sum(x["home_all_5_xg_missing"] for x in missing),
            "away":sum(x["away_all_5_xg_missing"] for x in missing),
            "either":sum(x["home_all_5_xg_missing"] or x["away_all_5_xg_missing"] for x in missing),
        },
        "variants":variants,
        "same_later_15_paired_variant_comparison":diff,
        "future_calibration_selection_policy":"fit on past settled forecasts only; compare untouched later block; no same-row refit and evaluation",
        "future_production_activation_requires_separate_pit_and_contemporaneous_ledger":True,
        "evaluation_previously_seen_in_calibration":False,
        "test_rows_read":0,"odds_used":False,
        "original_real_train_PIT_certified":False,
        "synthetic_variants_do_not_rank_official_M1":True,
        "production_approved":False,"gate14_pass":False,
    }

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--report",required=True)
    args=p.parse_args()
    r=run_demo()
    from pathlib import Path
    dest=Path(args.report);dest.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(r,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if dest.exists():
        if dest.read_text(encoding="utf8")!=payload:
            raise DemoError("FROZEN_RESEARCH_COMPARISON_CHANGED")
    else:
        with dest.open("x",encoding="utf8") as f:f.write(payload)
    slim={name:{"log_loss":v["all_30_synthetic_valid"]["log_loss"],
                  "brier_sum3":v["all_30_synthetic_valid"]["brier_sum3"],
                  "temperature":v["calibration_fit_earlier_15"]["temperature"],
                  "later_log_loss_raw":v["later_15_untouched_calibration_evaluation"]["raw"]["log_loss"],
                  "later_log_loss_calibrated":v["later_15_untouched_calibration_evaluation"]["calibrated"]["log_loss"]}
            for name,v in r["variants"].items()}
    print(json.dumps({"synthetic_variants":slim,"paired_later_15":r["same_later_15_paired_variant_comparison"],
                      "real_PIT":False,"gate14_pass":False},sort_keys=True))
