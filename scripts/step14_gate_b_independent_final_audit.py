"""Independent GATE14-B acceptance audit: versioned relaxed historical M1-R.

Original strict 159-field PitchAPI historical publication gate remains PENDING.
Do not look at protected 2026/27 TEST. Audit immutable trained model artefacts
and recompute real independent 374-label multiclass metrics.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,os
from collections import Counter
from pathlib import Path
from catboost import CatBoostClassifier
from scripts.step14_m1r_train_real_catboost_720_evaluate_374 import (
    ROOT,load_frozen,prepare_features,_as_label)
from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import (
    _valid_safe,validated_events)
from src.kb3_step13_baseline import forecast,BaselineParameters
from src.kb3_step13_retrospective import _train_poisson
from dataclasses import replace

METRICS="data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json"
PREDS="data/audits/STEP14_M1R_BASE_CATBOOST_374_FROZEN_PROBS_2026-10-29.jsonl.gz"
MODEL="models/research/M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm"
SCHEMA="kb3-gate14-variant-B-independent-audit-v1"
TOL=1e-8
class Gate14BAuditError(ValueError):pass

def _verify(condition,error):
    if not condition:raise Gate14BAuditError(error)

def independently_score(probabilities,labels):
    """No use of M1-R original scoring code."""
    _verify(len(probabilities)==len(labels)==374,"MISSING_374_VALIDATION")
    order=("1","X","2")
    ll=0.;br=0.;n_correct=0
    top_bins=[{"n":0,"p_sum":0.,"hits":0} for _ in range(5)]
    class_bins={c:[{"n":0,"p_sum":0.,"hits":0} for _ in range(5)] for c in order}
    for probs,y in zip(probabilities,labels):
        _verify(y in order and set(probs)==set(order),"INVALID_1X2_LABEL_KEYS")
        _verify(all(type(probs[c]) in (int,float) and math.isfinite(probs[c]) and 0<=probs[c]<=1 for c in order),"INVALID_P")
        _verify(abs(sum(probs.values())-1)<1e-9,"NORMALIZATION_DRIFT")
        ll-=math.log(max(1e-15,probs[y]))
        br+=sum((probs[c]-(1.0 if c==y else 0.0))**2 for c in order)
        top=max(order,key=lambda c:probs[c])
        n_correct+=int(top==y)
        t=top_bins[min(4,int(probs[top]*5))]
        t["n"]+=1;t["p_sum"]+=probs[top];t["hits"]+=int(top==y)
        for c in order:
            q=class_bins[c][min(4,int(probs[c]*5))]
            q["n"]+=1;q["p_sum"]+=probs[c];q["hits"]+=int(c==y)
    n=len(labels)
    ece=sum(abs(x["p_sum"]/x["n"]-x["hits"]/x["n"])*x["n"]/n for x in top_bins if x["n"])
    byclass={c:[{"bin":i,"count":x["n"],
         "mean_probability":x["p_sum"]/x["n"] if x["n"] else None,
         "observed_frequency":x["hits"]/x["n"] if x["n"] else None}
            for i,x in enumerate(rows)] for c,rows in class_bins.items()}
    return {"n":n,"log_loss":ll/n,"brier_multiclass_sum3":br/n,
            "brier_multiclass_mean3":br/(3*n),
            "top1_accuracy":n_correct/n,"top1_ece_5_bins":ece,
            "per_class_reliability_5_bins":byclass}

def _check_saved(candidate,report,name):
    for field in ("n","log_loss","brier_multiclass_sum3","brier_multiclass_mean3",
                  "top1_accuracy","top1_ece_5_bins"):
        _verify(abs(candidate[field]-report[name][field])<=1e-11,
                "ORIGINAL_METRIC_OR_CALIBRATION_DRIFT_"+name+"_"+field)
    for c in ("1","X","2"):
        actual=candidate["per_class_reliability_5_bins"][c]
        expected=report[name]["per_class_reliability_5_bins"][c]
        for a,b in zip(actual,expected):
            _verify(a["count"]==b["count"],"CALIBRATION_BIN_N_DRIFT")
            for fld in ("mean_probability","observed_frequency"):
                if a[fld] is None:_verify(b[fld] is None,"CALIBRATION_MISSING_BIN_DRIFT")
                else:_verify(abs(a[fld]-b[fld])<=1e-11,"CLASS_CALIBRATION_DRIFT_"+c)

def audit(*,root=ROOT,native_override=None):
    root=Path(root)
    old,rows=load_frozen(root)
    train,val,features,Xtrain,Xval=prepare_features(rows)
    p=root/METRICS;prediction=root/PREDS;model=root/MODEL
    saved=json.loads(p.read_text(encoding="utf8"))
    _verify(saved.get("schema")=="kb3-step14-m1r-base-catboost-720-train-374-val-fixed-research-v1",
            "OLD_REPORT_VERSION_CHANGED")
    _verify(saved.get("original_GATE14")=="PENDING" and saved.get("original_TEST_2026_27_never_requested"),
            "ORIGINAL_GATE_OR_TEST_CHANGED")
    _verify(saved.get("training")==720 and saved.get("validation")==374,
            "LOCKED_TRAIN_VAL_DRIFT")
    _verify(saved["research_frozen_source_matrix_sha256"]==old["matrix_gzip_sha256"],
            "LOCKED_SOURCE_SHA_DRIFT")
    _verify(saved["trained_model_sha256"]==hashlib.sha256(model.read_bytes()).hexdigest(),
            "MODEL_BINARY_SHA_DRIFT")
    _verify(saved["predictions_sha256"]==hashlib.sha256(prediction.read_bytes()).hexdigest(),
            "PREDICTION_SHA_DRIFT")
    _verify(saved["frozen_feature_names"]==features and len(features)==85,
            "TRAIN_SELECTED_FEATURES_CHANGED")
    _verify(all("_xg" not in x and "_xga" not in x for x in features),
            "ALTERNATIVE_XG_EXPOSED_IN_BASE")
    _verify(all(r["source_class"]=="B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT" and
      not r["original_M1_159_PIT_certified"] for r in rows),
      "FALSE_HISTORIC_NATIVE_PIT_CERTIFICATION")
    _verify(all(r["previous_score_release_lag_hours"]==48 for r in rows),
            "LAG_SIMULATION_CHANGED")
    _verify(Counter(r["partition"] for r in rows)=={"TRAIN":760,"VALIDATION":380},
            "SPLIT_MUTATION")
    _verify(Counter(r["partition"] for r in rows if r["m1r_base_eligible"])==
            {"TRAIN":720,"VALIDATION":374},"COLDS_TAINT")
    _verify(not set(r["fixture_id"] for r in train)&set(r["fixture_id"] for r in val),
            "TRAIN_VALID_ID_OVERLAP")
    _verify(max(r["kickoff_utc"] for r in train)<min(r["kickoff_utc"] for r in val),
            "TRAIN_VALID_CHRONOLOGY_MIXED")
    with gzip.open(prediction,"rt",encoding="utf8") as stream:
        frozen=[json.loads(x) for x in stream if x.strip()]
    _verify(len(frozen)==374 and len({x["fixture_id"] for x in frozen})==374,
            "NOT_FROZEN_374_UNIQUE")
    _verify([x["fixture_id"] for x in frozen]==[v["fixture_id"] for v in val],
            "FROZEN_VALID_ORDER_OR_ID_DRIFT")
    allowed={"fixture_id","partition","kickoff_utc","catboost_m1r_base_1x2",
             "matched_720_train_m0_1x2","reference_frozen_760_train_m0_1x2",
             "true_90min_label_not_in_prediction_file"}
    for row in frozen:
        _verify(set(row)==allowed and row["partition"]=="VALIDATION" and
                row["true_90min_label_not_in_prediction_file"] is True,
                "TARGET_LABEL_IN_PREDICTIONS_OR_SCHEMA_DRIFT")
    trained=CatBoostClassifier()
    trained.load_model(str(model))
    _verify(set(trained.classes_)=={"1","X","2"},"CATBOOST_CLASSES_DRIFT")
    _verify(list(trained.feature_names_)==features,"TRAINED_MODEL_FEATURE_NAMES_DRIFT")
    cb_probas=trained.predict_proba(Xval)
    classes=list(trained.classes_)
    for prediction_row,prob in zip(frozen,cb_probas):
        for c in ("1","X","2"):
            _verify(abs(float(prob[classes.index(c)])-
                        prediction_row["catboost_m1r_base_1x2"][c])<=TOL,
                    "FROZEN_CB_MODEL_PREDICTION_MISMATCH")
    safe=_valid_safe(root)
    if native_override is None:
        native,calls=native_three_seasons(key=os.environ.get("PITCHAPI_API_KEY",""))
    else:native=native_override;calls=0
    events,_,_=validated_events(
      {f"{int(k[:4])}/{int(k[:4])+1}":v for k,v in native.items()},safe)
    ix={e["fixture_id"]:e for e in events}
    _verify(len(ix)==1140,"LABELS_NOT_ORIGINAL_1140")
    yv=[_as_label(ix[v["fixture_id"]]["gh"],ix[v["fixture_id"]]["ga"]) for v in val]
    yt=[_as_label(ix[v["fixture_id"]]["gh"],ix[v["fixture_id"]]["ga"]) for v in train]
    _verify(Counter(yt)==saved["training_labels_1X2_counts"] and
            Counter(yv)==saved["validation_labels_1X2_counts"],
            "ACTUAL_1X2_LABEL_COUNTS_CHANGED")
    fitted_train=[(r["m1r_BASE_121_numeric_features"]["elo_home_minus_away"]/400,
          ix[r["fixture_id"]]["gh"],ix[r["fixture_id"]]["ga"]) for r in train]
    m0_fit=_train_poisson(fitted_train)
    for k,v in saved["m0_matched_720_fitted_train_parameters"].items():
        _verify(abs(getattr(m0_fit,k)-v)<=1e-11 if type(v) in (int,float) else getattr(m0_fit,k)==v,
                "M0_TRAIN_720_FIT_DRIFT")
    for r,freeze in zip(val,frozen):
        vals=r["m1r_BASE_121_numeric_features"]
        real=forecast(vals["home_elo"],vals["away_elo"],m0_fit)["p_1x2"]
        for c in ("1","X","2"):
            _verify(abs(real[c]-freeze["matched_720_train_m0_1x2"][c])<=1e-10,
                    "FROZEN_MATCHED_M0_DRIFT")
    vals_by_model={
       "catboost_m1r_base_validation":[p["catboost_m1r_base_1x2"] for p in frozen],
       "m0_matched_720_train_reference_poisson_validation":[p["matched_720_train_m0_1x2"] for p in frozen],
       "m0_original_760_train_frozen_reference_validation":[p["reference_frozen_760_train_m0_1x2"] for p in frozen]}
    own={}
    for name,probs in vals_by_model.items():
        own[name]=independently_score(probs,yv)
        _check_saved(own[name],saved,name)
    cb=own["catboost_m1r_base_validation"];m0=own["m0_matched_720_train_reference_poisson_validation"]
    winner=("M0_MATCHED_720" if
            all(m0[m]<cb[m] for m in ("log_loss","brier_multiclass_sum3","top1_ece_5_bins"))
            and m0["top1_accuracy"]>cb["top1_accuracy"] else "NO_DECISION")
    _verify(winner=="M0_MATCHED_720","CHAMPION_INFERENCE_CHANGED")
    return {"schema":SCHEMA,"date":"2026-10-29","status":"PASS_REVISED_GATE14_B",
       "original_STRICT_GATE14":"PENDING_NOT_CERTIFIED",
       "formal_step14_variant_B":True,
       "formal_objective":"FIT_INDEPENDENT_CATBOOST_1X2_AND_EVALUATE_REPRODUCIBLY",
       "real_1140_pitchapi_fixture_ids_matched":len(ix),
       "real_provider_calls":calls,
       "original_TEST_2026_27_queried_or_processed":False,
       "original_760_380_split_preserved":True,
       "research_retro_not_historical_native_pit":True,
       "verified_48h_event_time_lag_assumption_not_publication_proof":True,
       "M1_R_720_TRAIN_and_374_VALIDATION":["TRAIN=720","VALIDATION=374"],
       "COLD_START":["TRAIN=40","VALIDATION=6"],
       "catboost_model_sha256":saved["trained_model_sha256"],
       "frozen_prediction_sha256":saved["predictions_sha256"],
       "source_feature_matrix_sha256":old["matrix_gzip_sha256"],
       "85_features_loaded_in_real_cbm":True,
       "serialized_model_374_probas_reproduced_with_tolerance":TOL,
       "374_unique_validation_labels_verified_against_native_results":True,
       "374_frozen_probability_sets_1X2_normalized":True,
       "all_metrics_Brier_logloss_accuracy_ECE_and_class_bins_independently_recomputed":True,
       "training_fit_only_720_source_no_validation_labels":True,
       "old_m1_not_fitted":True,
       "production_or_champion_promotion":False,
       "score_comparison":{"m1r":cb,"m0_same720":m0},
       "research_winner":winner,
       "risk_register":["historical_48h_not_true_original_provider_publication",
           "match_end_time_simplified_kickoff_plus48h",
           "VALIDATION_used_once_avoid_tuning_repeat",
           "M1_R_less_predictive_than_M0",
           "TEST_2026_27_sealed",
           "requires_explicit_champion_approval_future"],
       "no_new_api_purchase":True,
       "audit_conclusion":"VERSIONED_VARIANT_B_STEP14_RESEARCH_REQUIREMENTS_PASS_ORIGINAL_STRICT_PIT_PENDING"}

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);args=p.parse_args()
    out=Path(args.out)
    if out.exists():raise Gate14BAuditError("NO_OVERWRITE")
    result=audit()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(json.dumps({"status":result["status"],"TRAIN":720,"VALIDATION":374,
      "model_sha":result["catboost_model_sha256"],
      "logloss_M1R":result["score_comparison"]["m1r"]["log_loss"],
      "logloss_M0":result["score_comparison"]["m0_same720"]["log_loss"],
      "original_GATE14":"PENDING_NOT_CERTIFIED"}))
if __name__=="__main__":main()
