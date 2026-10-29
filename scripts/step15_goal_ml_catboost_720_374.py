"""KB3 Step15: independent CatBoost Poisson goal-regression challenger vs M0.

One pre-registered experiment: 720 earlier TRAIN, 374 later VALIDATION,
same 85 train-only selected prior-match features, no historical xG, no odds.
Use separate CatBoost Poisson regressors for home and away expected goals,
THEN derive every market from a common independent Poisson score PMF.
This guarantees internal market coherence, NOT a better statistical fit.

Historical 48h source lag is retrospective RESEARCH, not proven PitchAPI PIT.
No 2026/27 protected TEST, validation-based fit, tuning, early stopping,
new API purchase, calibration, production promotion, or modified M0/M1-R.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
from collections import defaultdict
from pathlib import Path

from scripts.step14_m1r_train_real_catboost_720_evaluate_374 import (
    ROOT, load_frozen, prepare_features,
)
from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import (
    _valid_safe, validated_events,
)
from src.kb3_step13_retrospective import _train_poisson
from src.kb3_step15_goal_markets import (
    forecast_goal_markets, markets_from_lambdas, validate_goal_markets,
)
from scripts.step15_real_validation_374_goal_markets import (
    _score_binary, _outcomes, _prediction_markets,
)

SCHEMA = "kb3-step15-independent-ml-goals-catboost-poisson-720-374-v1"
PARAMS = {
    "iterations": 350, "depth": 4, "learning_rate": 0.035,
    "l2_leaf_reg": 8.0, "loss_function": "Poisson",
    "random_seed": 20261029, "thread_count": 2,
    "nan_mode": "Min", "verbose": False, "allow_writing_files": False,
}
# Declared BEFORE reading validation labels; no hyperparameter search.
RATE_MIN, RATE_MAX = 1e-6, 8.0
BOOTSTRAP_SEED, BOOTSTRAPS = 20261029, 1000
MARKETS_UNIQUE = (
    "over_1.5", "over_2.5", "over_3.5", "btts_yes",
    *tuple(f"{s}_{k}plus" for s in ("home", "away") for k in (1, 2, 3)),
    *tuple(f"{s}_exact_{k}" for s in ("home", "away") for k in range(4)),
)
if len(MARKETS_UNIQUE) != 18 or len(set(MARKETS_UNIQUE)) != 18:
    raise RuntimeError("PRIMARY_MARKET_POLICY_INVALID")


class GoalMLError(ValueError):
    pass


def _bounded_rate(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise GoalMLError("NONFINITE_ML_EXPECTED_GOALS")
    return min(RATE_MAX, max(RATE_MIN, float(value)))


def _binary_losses(p, y):
    if (type(p) not in (int, float) or not math.isfinite(p)
        or not 0 <= p <= 1 or type(y) is not int or y not in (0,1)):
        raise GoalMLError("INVALID_PROBABILITY_OR_TARGET")
    return (p-y)**2, -y*math.log(max(p,1e-15))-(1-y)*math.log(max(1-p,1e-15))


def _week(date):
    # Fixed iso-week bootstrap clusters; separate matches in one week are dependent.
    return date[:10] if not isinstance(date, str) or len(date)<10 else __import__("datetime").date.fromisoformat(date[:10]).strftime("%G-W%V")


def _ci_by_week(deltas, weeks, *, seed=BOOTSTRAP_SEED, boots=BOOTSTRAPS):
    """Week-cluster paired percentile CI, same fixture sets for M0 and ML."""
    if len(deltas)!=len(weeks) or not deltas:
        raise GoalMLError("PAIRED_CI_SAMPLE_INVALID")
    groups=defaultdict(list)
    for diff, week in zip(deltas, weeks):
        if not math.isfinite(diff): raise GoalMLError("NONFINITE_PAIRED_DIFFERENCE")
        groups[week].append(diff)
    buckets=[groups[k] for k in sorted(groups)]
    if len(buckets)<10:
        raise GoalMLError("INSUFFICIENT_WEEK_CLUSTERS")
    sums=[math.fsum(x) for x in buckets]
    sizes=[len(x) for x in buckets]
    rng=random.Random(seed)
    candidates=[]
    for _ in range(boots):
        indices=[rng.randrange(len(buckets)) for _ in buckets]
        candidates.append(math.fsum(sums[j] for j in indices)/sum(sizes[j] for j in indices))
    candidates.sort()
    return {
        "delta_mean":math.fsum(deltas)/len(deltas),
        "ci95_lower":candidates[int(.025*boots)],
        "ci95_upper":candidates[int(.975*boots)],
        "bootstrap_clusters":len(buckets),
        "bootstrap_replicates":boots,
        "cluster_unit":"ISO_WEEK_KICKOFF",
        "negative_favors_ml":True,
    }


def compare_predictions(preds, labels, weeks):
    """Compare 22 matched binary contracts and prespecified 18 unique events.

    True validation results are admitted ONLY here after probability freeze.
    No model is chosen, tuned or retrained based on these scores.
    """
    if len(preds)!=374 or len(labels)!=374 or len(weeks)!=374:
        raise GoalMLError("FROZEN_VALIDATION_374_ONLY")
    names=sorted(_prediction_markets(preds[0]["ml"]))
    if len(names)!=22 or len(MARKETS_UNIQUE)!=18 or not set(MARKETS_UNIQUE)<=set(names):
        raise GoalMLError("INVALID_22_MARKET_SCOPE")
    loss_track={name:{"brier":[],"log_loss":[]} for name in names}
    match_primary_brier=[]
    match_primary_log=[]
    scores={}
    for name in names:
        row_m0=[(_prediction_markets(p["m0"])[name],target[name]) for p,target in zip(preds,labels)]
        row_ml=[(_prediction_markets(p["ml"])[name],target[name]) for p,target in zip(preds,labels)]
        m0=_score_binary(row_m0)
        ml=_score_binary(row_ml)
        for (m0p,y),(mlp,y2) in zip(row_m0,row_ml):
            if y!=y2: raise GoalMLError("PAIRED_LABEL_DRIFT")
            bb0,ll0=_binary_losses(m0p,y)
            bb1,ll1=_binary_losses(mlp,y)
            loss_track[name]["brier"].append(bb1-bb0)
            loss_track[name]["log_loss"].append(ll1-ll0)
        scores[name]={
            "n":374,"m0":{k:m0[k] for k in ("brier","log_loss","ece_5bins")},
            "ml":{k:ml[k] for k in ("brier","log_loss","ece_5bins")},
            "delta_ml_minus_m0":{
                "brier":_ci_by_week(loss_track[name]["brier"],weeks),
                "log_loss":_ci_by_week(loss_track[name]["log_loss"],weeks),
            },
        }
    for i in range(374):
        match_primary_brier.append(
            math.fsum(loss_track[k]["brier"][i] for k in MARKETS_UNIQUE)/18)
        match_primary_log.append(
            math.fsum(loss_track[k]["log_loss"][i] for k in MARKETS_UNIQUE)/18)
    aggregate={
        "unit":"equal_weight_18_distinct_binary_events_per_match",
        "events":list(MARKETS_UNIQUE),
        "n_matched_fixtures":374,
        "m0":{m:math.fsum(scores[k]["m0"][m] for k in MARKETS_UNIQUE)/18
              for m in ("brier","log_loss")},
        "ml":{m:math.fsum(scores[k]["ml"][m] for k in MARKETS_UNIQUE)/18
              for m in ("brier","log_loss")},
        "delta_ml_minus_m0":{
            "brier":_ci_by_week(match_primary_brier,weeks),
            "log_loss":_ci_by_week(match_primary_log,weeks),
        },
    }
    for metric in ("brier","log_loss"):
        if abs((aggregate["ml"][metric]-aggregate["m0"][metric])
               -aggregate["delta_ml_minus_m0"][metric]["delta_mean"])>1e-12:
            raise GoalMLError("PAIRED_AGGREGATION_MISMATCH")
    flags={}
    for name in names:
        d=scores[name]["delta_ml_minus_m0"]
        flags[name]={
            "improves_brier":d["brier"]["delta_mean"]<0,
            "improves_log_loss":d["log_loss"]["delta_mean"]<0,
            "ci95_both_favor_ml":d["brier"]["ci95_upper"]<0 and d["log_loss"]["ci95_upper"]<0,
        }
    winner="ML" if all(
        aggregate["delta_ml_minus_m0"][m]["ci95_upper"]<0
        for m in ("brier","log_loss")
    ) else "NO_CONFIRMED_AGGREGATE_ML_IMPROVEMENT"
    return scores,aggregate,flags,winner


def train_compare(*,root=ROOT,native_override=None,output_dir=None):
    """Train home/away separately, freeze predictions first, score afterwards."""
    from catboost import CatBoostRegressor,Pool,CatBoost
    root=Path(root)
    old,rows=load_frozen(root)
    train,valid,features,Xtr,Xval=prepare_features(rows)
    if len(features)!=85 or len(train)!=720 or len(valid)!=374:
        raise GoalMLError("FROZEN_85_720_374_CONTRACT_DRIFT")
    valid_ids=[r["fixture_id"] for r in valid]
    if len(set(valid_ids))!=374 or any(r["partition"]!="VALIDATION" for r in valid):
        raise GoalMLError("VALIDATION_ID_OR_ROLE_DRIFT")
    allowed=_valid_safe(root)
    if native_override is None:
        key=os.environ.get("PITCHAPI_API_KEY","")
        if not key: raise GoalMLError("EXISTING_PITCHAPI_SECRET_MISSING")
        native,calls=native_three_seasons(key=key)
    else:
        native,calls=native_override,0
    events,counts,stable=validated_events(
        {f"{int(k[:4])}/{int(k[:4])+1}":m for k,m in native.items()},allowed)
    actual={m["fixture_id"]:m for m in events}
    if len(actual)!=1140:
        raise GoalMLError("RESEARCH_HISTORY_1140_NOT_VERIFIED")
    for row in train+valid:
        m=actual.get(row["fixture_id"])
        if (not m or m["partition"]!=row["partition"]
            or m["kickoff"].isoformat().replace("+00:00","Z")!=row["kickoff_utc"]):
            raise GoalMLError("NATIVE_FIXTURE_ID_OR_CUTOFF_DRIFT")
    # Native outcomes of 374 validation matches MUST NEVER enter fitting.
    gh=[actual[r["fixture_id"]]["gh"] for r in train]
    ga=[actual[r["fixture_id"]]["ga"] for r in train]
    if not all(type(v) is int and 0<=v<=30 for v in gh+ga):
        raise GoalMLError("INVALID_TRAIN_GOALS")
    train_data=Pool(Xtr,feature_names=features)
    h_model=CatBoostRegressor(**PARAMS)
    a_model=CatBoostRegressor(**{**PARAMS,"random_seed":PARAMS["random_seed"]+1})
    h_model.fit(Pool(Xtr,label=gh,feature_names=features))
    a_model.fit(Pool(Xtr,label=ga,feature_names=features))
    home_rates=list(h_model.predict(Pool(Xval,feature_names=features),
                                    prediction_type="Exponent"))
    away_rates=list(a_model.predict(Pool(Xval,feature_names=features),
                                    prediction_type="Exponent"))
    if len(home_rates)!=374 or len(away_rates)!=374:
        raise GoalMLError("ML_PREDICTIONS_NOT_374")
    exposure=[
        (r["m1r_BASE_121_numeric_features"]["elo_home_minus_away"]/400,
         actual[r["fixture_id"]]["gh"],actual[r["fixture_id"]]["ga"])
        for r in train
    ]
    m0_params=_train_poisson(exposure)
    frozen=[]
    capped=0
    for row,hr,ar in zip(valid,home_rates,away_rates):
        bounded_h,bounded_a=_bounded_rate(float(hr)),_bounded_rate(float(ar))
        capped+=int(bounded_h!=float(hr))+int(bounded_a!=float(ar))
        new=markets_from_lambdas(bounded_h,bounded_a)
        inp=row["m1r_BASE_121_numeric_features"]
        baseline=forecast_goal_markets(inp["home_elo"],inp["away_elo"],m0_params)
        validate_goal_markets(new)
        validate_goal_markets(baseline)
        frozen.append({"fixture_id":row["fixture_id"],"partition":"VALIDATION",
            "kickoff_utc":row["kickoff_utc"],
            "m0":baseline,"ml":new})
    # Independent M0 check against previous step15 accepted metrics.
    prior=json.loads((root/"data/audits/STEP15_REAL_374_VERIFIED_SELECTED_GOAL_METRICS_2026-10-29.json").read_text())
    expected={
        "over_2.5":prior["over_2_5"],
        "btts_yes":prior["btts_yes"],
    }
    # Immutable per-fixture prediction file is written BEFORE reading any
    # individual validation goals. It contains NO target outcomes.
    saved_models={}
    if output_dir is not None:
        out=Path(output_dir)
        if out.exists(): raise GoalMLError("RESEARCH_APPEND_ONLY_OUTPUT_REQUIRED")
        out.mkdir(parents=True)
        model_h=out/"CATBOOST_GOALS_HOME_720.cbm"
        model_a=out/"CATBOOST_GOALS_AWAY_720.cbm"
        h_model.save_model(str(model_h))
        a_model.save_model(str(model_a))
        saved_models={
            model_h.name:hashlib.sha256(model_h.read_bytes()).hexdigest(),
            model_a.name:hashlib.sha256(model_a.read_bytes()).hexdigest(),
        }
        # Explicit Exponent (not default) on reload guards CatBoost link semantics.
        for name,model,path,rates in (
            ("home",h_model,model_h,home_rates),
            ("away",a_model,model_a,away_rates),
        ):
            restored=CatBoost()
            restored.load_model(str(path))
            re=list(restored.predict(Pool(Xval,feature_names=features),prediction_type="Exponent"))
            if len(re)!=374 or any(abs(float(x)-float(y))>1e-10 for x,y in zip(re,rates)):
                raise GoalMLError("SAVED_MODEL_RATE_REPLAY_DRIFT_"+name)
        prob_file=out/"STEP15_374_PAIR_GOAL_PROBABILITIES_NO_LABELS.jsonl.gz"
        encoded="".join(
            json.dumps(rec,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n" for rec in frozen
        ).encode("utf8")
        prob_file.write_bytes(gzip.compress(encoded,compresslevel=7,mtime=0))
        prob_sha=hashlib.sha256(prob_file.read_bytes()).hexdigest()
    else:
        prob_sha=None
    # Only NOW consult actual 374 VALIDATION scores for metrics, not model fit.
    targets=[_outcomes(actual[rec["fixture_id"]]["gh"],actual[rec["fixture_id"]]["ga"])
             for rec in frozen]
    weeks=[_week(rec["kickoff_utc"]) for rec in frozen]
    result,aggregate,flags,winner=compare_predictions(frozen,targets,weeks)
    for name,reference in expected.items():
        for metric in ("brier","log_loss","ece_5bins"):
            if abs(result[name]["m0"][metric]-reference[metric])>1e-9:
                raise GoalMLError("PREVIOUS_MATCHED_M0_REFERENCE_NOT_REPRODUCED_"+name+"_"+metric)
    # First-order M0 1X2 should be unchanged in paired runs; external gate
    # from step15 previous run validates complete distribution and 374 coverage.
    meta={
        "schema":SCHEMA,
        "status":"ONE_SHOT_RESEARCH_VALIDATION_NOT_PRODUCTION",
        "fixed_params_home":PARAMS,
        "fixed_params_away":{**PARAMS,"random_seed":PARAMS["random_seed"]+1},
        "ml_design":"two_independent_catboost_poisson_rate_regressors_one_per_team",
        "ml_goal_distribution":"SAME_INDEPENDENT_POISSON_JOINT_PMF",
        "features_train_only":len(features),"xg_features_excluded":True,
        "partition_train":len(train),"partition_validation":len(valid),
        "source_matrix_sha256":old.get("matrix_gzip_sha256"),
        "source_class":"B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT",
        "historical_native_PIT_proven":False,
        "sealed_2026_27_test_accessed":False,
        "val_labels_used_for_training_early_stopping_or_model_selection":False,
        "hyperparameters_fixed_before_val":True,
        "baseline_m0_reference_matches_step15_prior":True,
        "unique_markets_for_primary_aggregate":18,
        "all_binary_markets":22,
        "all_374_matched_without_skips":True,
        "ml_rate_bounds":[RATE_MIN,RATE_MAX],
        "ml_rates_clipped_count_home_and_away":capped,
        "native_api_calls":calls,
        "native_season_counts":counts,
        "native_team_continuity":stable,
        "saved_model_sha256":saved_models,
        "frozen_prediction_sha256":prob_sha,
        "markets":result,
        "primary_macro_18_unique":aggregate,
        "flags":flags,
        "counts":{
            "ml_brier_improved_22":sum(v["improves_brier"] for v in flags.values()),
            "ml_log_loss_improved_22":sum(v["improves_log_loss"] for v in flags.values()),
            "ml_both_improved_22":sum(v["improves_brier"] and v["improves_log_loss"]
                                      for v in flags.values()),
            "ml_both_ci95_22":sum(v["ci95_both_favor_ml"] for v in flags.values()),
        },
        "research_winner":winner,
        "formal_gate15_pass":False,
        "model_promoted":False,
    }
    if output_dir is not None:
        (Path(output_dir)/"STEP15_ML_VS_M0_374_FULL_REPORT.json").write_text(
            json.dumps(meta,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out-dir",required=True)
    args=p.parse_args()
    report=train_compare(output_dir=args.out_dir)
    compact={
        "n":report["partition_validation"],
        "markets":report["all_binary_markets"],
        "unique_primary":report["unique_markets_for_primary_aggregate"],
        "ml_rates_clipped":report["ml_rates_clipped_count_home_and_away"],
        "macro_18":report["primary_macro_18_unique"],
        "counts":report["counts"],
        "research_winner":report["research_winner"],
        "selected_markets":{k:report["markets"][k] for k in
                            ("over_1.5","over_2.5","over_3.5","btts_yes")},
        "model_hashes":report["saved_model_sha256"],
        "prediction_sha":report["frozen_prediction_sha256"],
        "test_access":report["sealed_2026_27_test_accessed"],
    }
    print("STEP15_COMPARISON_SUMMARY_JSON="+json.dumps(compact,sort_keys=True,allow_nan=False))
    print("STEP15_ONE_SHOT_RESEARCH_COMPARISON_DONE__GATE15_PENDING")

if __name__=="__main__":
    main()
