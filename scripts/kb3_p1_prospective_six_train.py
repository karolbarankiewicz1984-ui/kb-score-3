"""Fit strictly research-only 6-feature CatBoost with exact forward Step11 naming.

TRAIN 1007 historical reconstructed rows; VALIDATION 376 later rows.
Never re-label as original PIT. Model and manifest remain private CI artifacts;
cannot be activated automatically in the live M0 pipeline.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json
from scripts.kb3_p1_retro_catboost_1007_376 import (
    load_sets,PARAMS,CLASSES,research_fit,by_league,week_ci
)
from src.kb3_step14_m1_math_calibration import score_predictions
from scripts.kb3_p1_historical_eligibility_split import hash_json

MODEL="KB3_CATBOOST_SHADOW_LAST5_GOALS_6_RESEARCH_V1"
FEATURES=tuple(f"{side}_{kind}" for side in ("home","away")
               for kind in ("goals_for","goals_against","points"))
FORWARD_KEYS=tuple(f"{side}_all_5_{key}_avg" for side in ("home","away")
                   for key in ("gf","ga","points"))
CONTRACT="KB3_CATBOOST_SHADOW_SIX_ASOF_M0_STEP11_V1"

class SixTrainingError(ValueError):pass
def require(ok,msg):
    if not ok:raise SixTrainingError(msg)

def run(*,output):
    root=Path(output)
    require(not root.exists(),"NO_RESEARCH_OUTPUT_REPLACE")
    train,valid,source=load_sets()
    require(len(train)==1007 and len(valid)==376 and
            source["formal_training_allowed"] is False,"UNSAFE_SOURCE_COHORT")
    require(len(FEATURES)==len(FORWARD_KEYS)==6,"FEATURES_NOT_SIX")
    root.mkdir(parents=True,exist_ok=False)
    from catboost import CatBoostClassifier
    train_x=[[float(x["features"][k]) for k in FEATURES] for x in train]
    val_x=[[float(x["features"][k]) for k in FEATURES] for x in valid]
    require(all(len(x)==6 for x in train_x+val_x),"CANDIDATE_SHAPE_INVALID")
    params={**PARAMS,"thread_count":1}
    clf=CatBoostClassifier(**params)
    # Train under forward field names: they become an immutable binary schema.
    clf.fit(train_x,[x["label"] for x in train],feature_names=list(FORWARD_KEYS))
    classes=[str(c) for c in clf.classes_]
    require(set(classes)==set(CLASSES) and
            list(clf.feature_names_)==list(FORWARD_KEYS),"MODEL_SCHEMA_DRIFT")
    raw=clf.predict_proba(val_x)
    p=[{label:float(z[classes.index(label)]) for label in CLASSES} for z in raw]
    y=[x["label"] for x in valid]
    result=score_predictions(p,y)
    bylg=by_league(valid,p)
    priors=Counter(x["label"] for x in train)
    marginal={k:(priors[k]+1)/(len(train)+3) for k in CLASSES}
    simple=[marginal for x in valid]
    baseline=score_predictions(simple,y)
    archive=root/"KB3_CATBOOST_SHADOW_SIX_RESEARCH.cbm"
    clf.save_model(str(archive))
    msha=hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest={
      "schema":CONTRACT,"model_version":MODEL,
      "feature_names":list(FORWARD_KEYS),
      "source_reconstructed_feature_names":list(FEATURES),
      "feature_contract":"SAME_LAST5_ALL_MATCHES_GOALS_FOR_AGAINST_AND_POINTS",
      "features_count":6,"expected_classes":list(CLASSES),
      "trained_on_reconstructed_history":True,
      "formal_asof_v2_trained":False,
      "historic_native_provider_first_published_proven":False,
      "retrospective_source_sha256":source["historical_source_sha256"],
      "training_selector_sha256":source["train_selector_sha256"],
      "validation_selector_sha256":source["validation_selector_sha256"],
      "training_rows":1007,"validation_rows":376,"embargo_days":7,
      "fixed_params":params,
      "model_binary_sha256":msha,
      "production_approved":False,
      "forward_source_observations_prospective_at_freeze_only":True,
      "new_live_forecasts_generated":0,
      "prospective_host_proof_verified":False,
      "gate16":"PENDING","gate17":"PENDING",
    }
    manifest["manifest_sha256"]=hash_json(manifest)
    (root/"KB3_CATBOOST_SHADOW_SIX_MANIFEST.json").write_text(
        json.dumps(manifest,sort_keys=True,indent=2)+"\n")
    report={
      "schema":"kb3-six-feature-cbm-retro-validation-v1",
      "model_version":MODEL,"manifest_sha256":manifest["manifest_sha256"],
      "model_binary_sha256":msha,
      "features":list(FORWARD_KEYS),
      "train_n":len(train),"validation_n":len(valid),
      "training_class_counts":dict(sorted(priors.items())),
      "validation_metrics":result,"validation_by_league":bylg,
      "train_only_class_frequency_baseline":baseline,
      "same_games_and_fixed_parameters":True,
      "source_class":"HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
      "trained_for_future_shadow_experiment_only":True,
      "old_m0_unchanged":True,"production_approved":False,
      "official_fit_increment":0,"gate16":"PENDING","gate17":"PENDING",
    }
    report["report_sha256"]=hash_json(report)
    (root/"KB3_CATBOOST_SHADOW_SIX_RETRO_REPORT.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("KB3_SHADOW_SIX_FITTED_RESEARCH_ONLY",json.dumps({
        "train":len(train),"validation":len(valid),
        "brier":result["brier_sum3"],"log_loss":result["log_loss"],
        "accuracy":result["top1_accuracy"],
        "ece":result["top1_ece_10bins"],
        "model_binary_sha256":msha,
        "manifest_sha256":manifest["manifest_sha256"],
        "pit_certified":False,"shadow_forward_predictions":0},sort_keys=True))
    return manifest,report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    run(output=a.out)
