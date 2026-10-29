"""KB3 separate M1-R BASE CatBoost research fit 720 TRAIN / score 374 VAL.

No historical PIT certification, no 2026/27 TEST, no model promotion.
Feature engineering is pre-frozen in step14 M1-R 48h replay.
Historical 90m results are READ separately from the 121-feature matrix for
TRAIN labels. VALIDATION labels are never passed to .fit, feature selection,
hyperparameter choice, or M0 fit; used only after frozen predictions for scores.
Any derived model is a purely retrospective research candidate.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,os
from collections import Counter
from dataclasses import asdict,replace
from pathlib import Path

from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import _valid_safe,validated_events
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step13_baseline import BaselineParameters,forecast
from src.kb3_step13_retrospective import _train_poisson,_eval
from scripts.step13_prematch_forward_once import REFERENCE_TRAIN_FIT
from scripts.step14_m1r_recompute_1140_relaxed_48h import ROOT

SCHEMA="kb3-step14-m1r-base-catboost-720-train-374-val-fixed-research-v1"
SOURCE_SUMMARY="data/audits/STEP14_M1R_RELAXED_1140_48H_121x38_SUMMARY_2026-10-29.json"
SOURCE_MATRIX="data/audits/STEP14_M1R_RELAXED_1140_48H_121x38_RESEARCH_2026-10-29.jsonl.gz"
CLASSES=("1","X","2")
PARAMS={"iterations":400,"depth":4,"learning_rate":0.035,"l2_leaf_reg":8.0,
        "loss_function":"MultiClass","random_seed":20261029,"thread_count":2,
        "nan_mode":"Min","verbose":False,"allow_writing_files":False}
class M1RFitSafetyError(ValueError):pass

def _as_label(gh,ga):
    if type(gh) is not int or type(ga) is not int or not 0<=gh<=30 or not 0<=ga<=30:
        raise M1RFitSafetyError("INVALID_90_MIN_LABEL")
    return "1" if gh>ga else "X" if gh==ga else "2"

def load_frozen(root=ROOT):
    root=Path(root)
    report=json.loads((root/SOURCE_SUMMARY).read_text())
    p=root/SOURCE_MATRIX
    compressed=p.read_bytes()
    if (report.get("schema")!="kb3-m1r-1140-three-seasons-relaxed-48h-121x38-research-only-v1"
        or report.get("matrix_gzip_sha256")!=hashlib.sha256(compressed).hexdigest()
        or report.get("matrix_rows")!=1140
        or report.get("m1r_BASE_eligible_by_partition")!={"TRAIN":720,"VALIDATION":374}
        or report.get("m1r_BASE_cold_start_by_partition")!={"TRAIN":40,"VALIDATION":6}
        or report.get("original_M1_Gate14")!="PENDING"
        or report.get("original_2026_27_TEST_examined") is not False):
        raise M1RFitSafetyError("FROZEN_M1R_1140_SOURCE_CHANGED")
    with gzip.open(p,"rt",encoding="utf8") as stream:
        rows=[json.loads(line) for line in stream if line.strip()]
    if len(rows)!=1140 or len({r["fixture_id"] for r in rows})!=1140:
        raise M1RFitSafetyError("SOURCE_DUPLICATES_OR_1140_INCOMPLETE")
    return report,rows

def prepare_features(rows):
    """Train-only variable-feature selection. ALL source xG disabled for BASE."""
    for r in rows:
        if (set(r["m1r_BASE_121_numeric_features"])!=EXPECTED_FEATURES
            or set(r["m1r_BASE_38_missing_flags"])!=EXPECTED_MISSING
            or r["original_M1_159_PIT_certified"] is not False
            or r["source_class"]!="B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT"):
            raise M1RFitSafetyError("UNTRUSTED_FEATURE_SCHEMA_OR_PIT")
    training=sorted((r for r in rows if r["partition"]=="TRAIN" and r["m1r_base_eligible"]),
                    key=lambda r:(r["kickoff_utc"],r["fixture_id"]))
    valid=sorted((r for r in rows if r["partition"]=="VALIDATION" and r["m1r_base_eligible"]),
                 key=lambda r:(r["kickoff_utc"],r["fixture_id"]))
    if len(training)!=720 or len(valid)!=374:
        raise M1RFitSafetyError("WRONG_FROZEN_720_374")
    def allowed(name):
        # Do not expose optional xG or xG missingness to BASE, even if
        # other source variants supply these values in the future.
        return not (name.endswith(("_xg_n","_xg_avg","_xga_n","_xga_avg",
                                   "_xg","_xga")))
    all_names=sorted(["num:"+k for k in EXPECTED_FEATURES if allowed(k)]+
                     ["miss:"+k for k in EXPECTED_MISSING if allowed(k)])
    def get(r,name):
        kind,key=name.split(":",1)
        v=(r["m1r_BASE_121_numeric_features"].get(key) if kind=="num" else
           r["m1r_BASE_38_missing_flags"].get(key))
        if v is None:return float("nan")
        if type(v) not in (bool,int,float) or not math.isfinite(v):
            raise M1RFitSafetyError("BAD_FEATURE_NUMERIC")
        return float(v)
    def signature(vals):
        return tuple("nan" if math.isnan(v) else v for v in vals)
    # Feature availability is selected exclusively using 720 TRAIN.
    # Remove exact constant columns; especially all missing xG variables.
    selected=[]
    for name in all_names:
        values=[get(row,name) for row in training]
        if len(set(signature(values)))!=1:  # wrong: signature returns one tuple
            selected.append(name)
    # corrected below: use distinct train observed+missing signatures.
    selected=[name for name in all_names if len(set(
         "nan" if math.isnan(get(row,name)) else get(row,name) for row in training))>1]
    if len(selected)<15 or len(selected)>159:
        raise M1RFitSafetyError("UNEXPECTED_TRAIN_SELECTED_COLUMNS")
    mat_train=[[get(r,k) for k in selected] for r in training]
    mat_valid=[[get(r,k) for k in selected] for r in valid]
    return training,valid,selected,mat_train,mat_valid

def _validate_label_sets(training,valid,actual):
    if len(actual)!=1140:
        raise M1RFitSafetyError("NOT_1140_NATIVE_LABEL_IDENTITIES")
    for row in training+valid:
        source=actual.get(row["fixture_id"])
        if (source is None or source["partition"]!=row["partition"] or
            source["kickoff"].isoformat().replace("+00:00","Z")!=row["kickoff_utc"]):
            raise M1RFitSafetyError("NATIVE_TARGET_JOIN_DRIFT")
    yt=[_as_label(actual[r["fixture_id"]]["gh"],actual[r["fixture_id"]]["ga"]) for r in training]
    yv=[_as_label(actual[r["fixture_id"]]["gh"],actual[r["fixture_id"]]["ga"]) for r in valid]
    if len(set(yt))!=3:return (_ for _ in ()).throw(M1RFitSafetyError("TRAIN_MISSING_1X2_CLASS"))
    return yt,yv

def _score(probs,labels):
    """Independent multiclass scores, ECE and per-class 5-bin calibration."""
    if len(probs)!=len(labels) or not labels:raise M1RFitSafetyError("INVALID_EVAL_LENGTH")
    result=[]
    conf=[{"count":0,"forecast_sum":0.0,"correct":0} for _ in range(5)]
    per={c:[{"count":0,"sum_p":0.0,"events":0} for _ in range(5)] for c in CLASSES}
    correct=0
    for p,y in zip(probs,labels):
        if (y not in CLASSES or set(p)!=set(CLASSES)
            or any(not isinstance(p[c],(float,int)) or not math.isfinite(p[c])
                   or not 0<=p[c]<=1 for c in CLASSES)
            or abs(sum(p.values())-1)>1e-8):
            raise M1RFitSafetyError("INVALID_MULTICLASS_PROBABILITIES")
        top=max(CLASSES,key=lambda c:p[c])
        correct+=int(top==y)
        ix=min(4,int(p[top]*5))
        conf[ix]["count"]+=1;conf[ix]["forecast_sum"]+=p[top]
        conf[ix]["correct"]+=int(top==y)
        for c in CLASSES:
            j=min(4,int(p[c]*5))
            per[c][j]["count"]+=1;per[c][j]["sum_p"]+=p[c]
            per[c][j]["events"]+=int(y==c)
        result.append((-math.log(max(p[y],1e-15)),
                        sum((p[c]-int(c==y))**2 for c in CLASSES)))
    n=len(labels)
    calibration=[{"bin":i,"count":z["count"],
                  "mean_confidence":z["forecast_sum"]/z["count"] if z["count"] else None,
                  "observed_accuracy":z["correct"]/z["count"] if z["count"] else None}
                 for i,z in enumerate(conf)]
    byclass={c:[{"bin":i,"count":z["count"],
                 "mean_probability":z["sum_p"]/z["count"] if z["count"] else None,
                 "observed_frequency":z["events"]/z["count"] if z["count"] else None}
                for i,z in enumerate(per[c])] for c in CLASSES}
    ece=sum((z["count"]/n)*abs(z["forecast_sum"]/z["count"]-
              z["correct"]/z["count"]) for z in conf if z["count"])
    out={"n":n,"log_loss":sum(x[0] for x in result)/n,
         "brier_multiclass_sum3":sum(x[1] for x in result)/n,
         "brier_multiclass_mean3":sum(x[1] for x in result)/(3*n),
         "top1_accuracy":correct/n,"top1_ece_5_bins":ece,
         "top1_reliability_5_bins":calibration,
         "per_class_reliability_5_bins":byclass}
    # Cross-check the previous project's independently implemented scoring.
    legacy=_eval(probs,[{"1":"H","X":"D","2":"A"}[y] for y in labels])
    if any(abs(out[k]-legacy[old])>1e-12 for k,old in (
            ("log_loss","multiclass_logloss"),("brier_multiclass_sum3","multiclass_brier_sum3"),
            ("top1_ece_5_bins","top_class_ece_5bin"))):
        raise M1RFitSafetyError("METRIC_INCONSISTENT_WITH_KB3_M0")
    return out

def train_evaluate(*,root=ROOT,native_override=None,model_out=None):
    from catboost import CatBoostClassifier
    root=Path(root)
    source,rows=load_frozen(root)
    train,valid,features,Xtr,Xval=prepare_features(rows)
    safe=_valid_safe(root)
    if native_override is None:
        native,api_calls=native_three_seasons(key=os.environ.get("PITCHAPI_API_KEY",""))
    else:native=native_override;api_calls=0
    events,counts,stable=validated_events(
        {f"{int(k[:4])}/{int(k[:4])+1}":m for k,m in native.items()},safe)
    actual={x["fixture_id"]:x for x in events}
    yt,yv=_validate_label_sets(train,valid,actual)
    # Fixed parameters and feature selection before reading validation labels
    # for scoring. No eval_set, early_stopping_rounds, validation weights,
    # or optimization against the held-out season.
    clf=CatBoostClassifier(**PARAMS)
    clf.fit(Xtr,yt,feature_names=features)
    classes=list(clf.classes_)
    if set(classes)!=set(CLASSES):raise M1RFitSafetyError("CATBOOST_NOT_ALL_1X2")
    cb_raw=clf.predict_proba(Xval)
    cat=[{c:float(row[classes.index(c)]) for c in CLASSES} for row in cb_raw]
    # Matched original M0 method: same 720 TRAIN, same precomputed M1-R Elo
    # snapshots, train-only profile MLE for goal rates and fixed elasticity grid.
    poisson_train=[]
    for r in train:
        match=actual[r["fixture_id"]]
        delta=r["m1r_BASE_121_numeric_features"]["elo_home_minus_away"]/400
        poisson_train.append((delta,match["gh"],match["ga"]))
    fitted=_train_poisson(poisson_train)
    m0=[forecast(r["m1r_BASE_121_numeric_features"]["home_elo"],
                  r["m1r_BASE_121_numeric_features"]["away_elo"],fitted)["p_1x2"]
        for r in valid]
    # Also evaluate the existing frozen M0 760 TRAIN fit (separate Elo
    # preprocessing provenance; this is a secondary contextual comparator).
    published=replace(BaselineParameters(),**REFERENCE_TRAIN_FIT)
    m0_reference=[forecast(r["m1r_BASE_121_numeric_features"]["home_elo"],
                           r["m1r_BASE_121_numeric_features"]["away_elo"],published)["p_1x2"]
                  for r in valid]
    # All 374 forecasts are now frozen before evaluating yv.
    eval_cat=_score(cat,yv)
    eval_m0=_score(m0,yv)
    eval_ref=_score(m0_reference,yv)
    # Freeze model to a separate research directory, no model-production path.
    if model_out is not None:
        destination=Path(model_out)
        if destination.exists():raise M1RFitSafetyError("MODEL_APPEND_ONLY")
        destination.parent.mkdir(parents=True,exist_ok=True)
        clf.save_model(str(destination))
    else:destination=None
    probabilities=[]
    for r,c,m,ref in zip(valid,cat,m0,m0_reference):
        probabilities.append({"fixture_id":r["fixture_id"],"partition":"VALIDATION",
           "kickoff_utc":r["kickoff_utc"],"catboost_m1r_base_1x2":c,
           "matched_720_train_m0_1x2":m,"reference_frozen_760_train_m0_1x2":ref,
           "true_90min_label_not_in_prediction_file":True})
    report={"schema":SCHEMA,"status":"TRAINED_ISOLATED_RESEARCH_ONLY",
        "catboost_version":__import__("catboost").__version__,
        "training_algorithm":"CatBoostClassifier MultiClass independent research M1-R BASE",
        "fixed_hyperparameters":PARAMS,
        "frozen_feature_names":features,"frozen_feature_count":len(features),
        "feature_selection_based_only_on_TRAIN_720":True,
        "all_OPTIONAL_xg_and_source_overlay_excluded":True,
        "training":720,"validation":374,"cold_start_excluded_TRAIN":40,
        "cold_start_excluded_VALIDATION":6,
        "all_1140_source_rows_matched":len(events),
        "original_760_380_partition_intact":True,
        "real_PitchAPI_API_calls":api_calls,
        "native_three_season_counts":counts,
        "native_team_continuity":stable,
        "model_classes_1x2":classes,
        "metric_definition":"Brier=sum_{c in 1,X,2}(p_c-y_c)^2; also Brier/3",
        "validation_evaluation_once_no_early_stopping":True,
        "catboost_m1r_base_validation":eval_cat,
        "m0_matched_720_train_reference_poisson_validation":eval_m0,
        "m0_original_760_train_frozen_reference_validation":eval_ref,
        "m0_matched_720_fitted_train_parameters":asdict(fitted),
        "m0_original_760_train_params_from_prior_frozen_report":asdict(published),
        "delta_M1R_minus_M0_720_train_log_loss":eval_cat["log_loss"]-eval_m0["log_loss"],
        "delta_M1R_minus_M0_720_train_brier_sum3":eval_cat["brier_multiclass_sum3"]-eval_m0["brier_multiclass_sum3"],
        "delta_M1R_minus_M0_720_train_ece":eval_cat["top1_ece_5_bins"]-eval_m0["top1_ece_5_bins"],
        "m0_and_m1r_validation_fixture_population_exact_same":True,
        "original_m1_untouched":True,"original_GATE14":"PENDING",
        "original_TEST_2026_27_never_requested":True,
        "original_M0_predictions_untouched":True,
        "future_actual_PIT_certified":False,
        "research_frozen_source_matrix_sha256":source["matrix_gzip_sha256"],
        "trained_model_sha256":hashlib.sha256(destination.read_bytes()).hexdigest() if destination else None,
        "training_labels_1X2_counts":dict(Counter(yt)),
        "validation_labels_1X2_counts":dict(Counter(yv)),
        "target_labels_never_saved_in_prediction_file":True}
    return report,probabilities

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",required=True)
    p.add_argument("--predictions",required=True)
    p.add_argument("--model",required=True)
    opt=p.parse_args()
    summary=Path(opt.summary);pred=Path(opt.predictions);model=Path(opt.model)
    if any(x.exists() for x in (summary,pred,model)):
        raise M1RFitSafetyError("APPEND_ONLY_OUTPUT_EXISTS")
    report,prob=train_evaluate(model_out=model)
    summary.parent.mkdir(parents=True,exist_ok=True);pred.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(pred,"wt",encoding="utf8",compresslevel=7) as f:
        for row in prob:f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n")
    report["predictions_sha256"]=hashlib.sha256(pred.read_bytes()).hexdigest()
    report["prediction_rows"]=len(prob)
    summary.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    for key in ("catboost_m1r_base_validation","m0_matched_720_train_reference_poisson_validation",
                "m0_original_760_train_frozen_reference_validation"):
        m=report[key]
        print(key,{"n":m["n"],"log_loss":m["log_loss"],"brier":m["brier_multiclass_sum3"],
                   "ece":m["top1_ece_5_bins"],"accuracy":m["top1_accuracy"]})
    print("M1-R frozen 720 train 374 val, original GATE14 PENDING")
if __name__=="__main__":main()
