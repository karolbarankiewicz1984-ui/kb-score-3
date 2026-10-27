"""Step13: matched 380-match uncertainty for two FROZEN retrospective baselines.

Uncertainty is descriptive, not PIT, not a winner-selection rule.
Real provider scores and individual forecasts are NEVER serialized, logged,
cached, or exposed in CI artifacts. Uses NO TEST rows, no betting odds, and
fits both variants separately on data before each original quarter boundary.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import argparse
import math
import os
import json
import random
from pathlib import Path

from src.kb3_split import WALK_FORWARD,WINDOWS,timestamp,sha,freeze_manifest
from src.kb3_step13_retrospective import (
    _validate,_historical_states,_train_poisson,retrospective_research,POLICY,
)
from src.kb3_step13_baseline import BaselineSafetyError,forecast
from scripts.pitchapi_step06_audit import to_plain
from scripts.step13_pitchapi_research_once import LEAGUE,SEASONS,extract_research_rows,SAFE_PATH

REFERENCE="data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json"
REFERENCE_SHA="3d950fff30b57c94a6f71462c7521cfda2cb0b27c666d59d09d274261efca803"
METHODS=("EXPANDING","ROLLING_24_CALENDAR_MONTHS")
BOOTSTRAPS=3000
SEED=13082026


def loss(prob,label):
    idx={"H":"1","D":"X","A":"2"}[label]
    return (-math.log(max(prob[idx],1e-15)),
            math.fsum((prob[k]-(1.0 if k==idx else 0.0))**2
                      for k in ("1","X","2")))


def quantile(sorted_values, p):
    v=(len(sorted_values)-1)*p
    lo=int(v)
    hi=min(len(sorted_values)-1,lo+1)
    return sorted_values[lo]*(hi-v)+sorted_values[hi]*(v-lo)


def paired_uncertainty(rows,*,reference,expected_reference_sha=None,replicates=BOOTSTRAPS):
    """No individual prediction or match result is returned.

    Reconstructs same fold-frozen probabilities, cross-checks EVERY fold
    original model metrics before allowing inferential output.
    """
    if (not isinstance(reference,dict) or
        sha({k:v for k,v in reference.items() if k!="report_sha256"})!=reference.get("report_sha256") or
        (expected_reference_sha and reference["report_sha256"]!=expected_reference_sha) or
        reference.get("test_rows_processed")!=0 or
        reference.get("gate13_pass") is not False or
        reference.get("training_allowed") is not False or
        reference.get("validation_partition_rows")!=380 or
        reference.get("train_partition_rows")!=760 or
        reference.get("research_policy")!=POLICY):
        raise BaselineSafetyError("STEP13_PAIRED_UNVERIFIED_REFERENCE")
    if not isinstance(replicates,int) or not 100<=replicates<=20000:
        raise BaselineSafetyError("STEP13_PAIRED_BAD_RESAMPLING_COUNT")
    if sha(rows)!=reference["match_data_sha256"]:
        raise BaselineSafetyError("STEP13_PAIRED_SOURCE_RECORDS_DRIFT")
    checked=_validate(rows)
    if len(checked)!=1140:
        raise BaselineSafetyError("STEP13_PAIRED_ROW_COUNT_CHANGED")
    if not isinstance(reference.get("folds"),list) or len(reference["folds"])!=4:
        raise BaselineSafetyError("STEP13_PAIRED_REFERENCE_FOLDS_CHANGED")
    all_clustered=[]
    per_fold=[]
    edge_flags=0
    for i,(start_s,end_s) in enumerate(WALK_FORWARD):
        start,end=timestamp(start_s),timestamp(end_s)
        ref=reference["folds"][i]
        targets=[t for t in checked if start<=t["_date"]<end]
        if (ref["fold"]!=i+1 or ref["validation_from_utc"]!=start_s or
            ref["validation_to_exclusive_utc"]!=end_s or
            len(targets)!=ref["validation_count"]):
            raise BaselineSafetyError("STEP13_PAIRED_REFERENCE_FOLD_MISMATCH")
        probs={}
        for method in METHODS:
            lower=(timestamp(WINDOWS[0][1]) if method==METHODS[0] else start.replace(year=start.year-2))
            ratings,train=_historical_states(checked,boundary=start,lower=lower)
            p=_train_poisson(train)
            ex=ref["methods"][method]
            if (ex["training_rows"]!=len(train) or
                ex["validation_fixture_ids_sha256"]!=sha([t["fixture_id"] for t in targets]) or
                ex["validation_labels_used_for_fitting"] is not False or
                ex["parameters_frozen_before_validation"] is not True):
                raise BaselineSafetyError("STEP13_PAIRED_TRAIN_OR_TARGETS_MISMATCH")
            params=ex["fitted_parameters"]
            if any(abs(params[key]-getattr(p,key))>1e-12 for key in
                   ("base_home_goals","base_away_goals","elo_goal_elasticity")):
                raise BaselineSafetyError("STEP13_PAIRED_PARAMETER_DRIFT")
            edge_flags+=int(p.elo_goal_elasticity==0.6)
            probs[method]=[
                forecast(ratings.get(t["home_team_id"],p.initial_elo),
                         ratings.get(t["away_team_id"],p.initial_elo),p)["p_1x2"]
                for t in targets
            ]
        permethod={m:{"log":0.0,"brier":0.0} for m in METHODS}
        weekly=defaultdict(lambda:{"n":0,"log_delta":0.0,"brier_delta":0.0})
        for k,t in enumerate(targets):
            lab="H" if t["goals_home_90"]>t["goals_away_90"] else "A" if t["goals_home_90"]<t["goals_away_90"] else "D"
            losses={m:loss(probs[m][k],lab) for m in METHODS}
            for m in METHODS:
                permethod[m]["log"]+=losses[m][0]
                permethod[m]["brier"]+=losses[m][1]
            wk=t["_date"].isocalendar()
            cluster=weekly[(wk.year,wk.week)]
            cluster["n"]+=1
            cluster["log_delta"]+=losses[METHODS[1]][0]-losses[METHODS[0]][0]
            cluster["brier_delta"]+=losses[METHODS[1]][1]-losses[METHODS[0]][1]
        for m in METHODS:
            original=ref["methods"][m]["metrics"]
            if (abs(permethod[m]["log"]/len(targets)-original["multiclass_logloss"])>1e-10 or
                abs(permethod[m]["brier"]/len(targets)-original["multiclass_brier_sum3"])>1e-10):
                raise BaselineSafetyError("STEP13_PAIRED_METRIC_DRIFT")
        chunks=list(weekly.values())
        all_clustered.append(chunks)
        per_fold.append({
            "fold":i+1,"validation_n":len(targets),
            "calendar_week_clusters":len(chunks),
            "rolling_minus_expanding_logloss":(
                permethod[METHODS[1]]["log"]-permethod[METHODS[0]]["log"])/len(targets),
            "rolling_minus_expanding_brier":(
                permethod[METHODS[1]]["brier"]-permethod[METHODS[0]]["brier"])/len(targets),
        })
    total=sum(f["validation_n"] for f in per_fold)
    if total!=380:
        raise BaselineSafetyError("STEP13_PAIRED_NOT_380")
    overall={}
    for measure,ref_metric in (
        ("log","multiclass_logloss_fold_weighted"),
        ("brier","multiclass_brier_sum3_fold_weighted")):
        key=measure+"_delta"
        observed=sum(c[key] for clusters in all_clustered for c in clusters)/total
        pinned=(reference["overall"][METHODS[1]][ref_metric]-
                reference["overall"][METHODS[0]][ref_metric])
        if abs(observed-pinned)>1e-10:
            raise BaselineSafetyError("STEP13_PAIRED_OVERALL_DRIFT")
        rng=random.Random(SEED+(7 if measure=="brier" else 0))
        draws=[]
        for _ in range(replicates):
            score=n=0.0
            for clusters in all_clustered:
                for _ in clusters:
                    c=clusters[rng.randrange(len(clusters))]
                    score+=c[key]
                    n+=c["n"]
            draws.append(score/n)
        ordered=sorted(draws)
        ci=[quantile(ordered,0.025),quantile(ordered,0.975)]
        overall[measure]={
            "rolling_minus_expanding_mean":observed,
            "week_cluster_bootstrap_ci95":ci,
            "interval_includes_zero":ci[0]<=0<=ci[1],
            "week_cluster_resamples":replicates,
            "same_match_paired_losses":True,
        }
    result={
        "schema":"kb3-step13-real-retrospective-paired-week-cluster-uncertainty-v0.8",
        "original_report_sha256":reference["report_sha256"],
        "research_policy":POLICY,
        "training_initial_n":760,
        "validation_n":380,
        "test_rows_read":0,
        "folds":per_fold,
        "week_clusters_total":sum(len(x) for x in all_clustered),
        "resampling":"STRATIFIED_WITHIN_FOLD_CALENDAR_WEEK_CLUSTERS_WITH_REPLACEMENT",
        "resampling_note":"DESCRIPTIVE_CI_NOT_FREQUENTIST_GUARANTEE_FOR_DEPENDENT_FOOTBALL_RESULTS",
        "seed":SEED,
        "overall":overall,
        "elo_elasticity_at_original_grid_boundary_count":edge_flags,
        "current_model_parameter_change":False,
        "original_provider_prematch_publication_verified":False,
        "comparison_statistically_conclusive":False,
        "betting_claims_authorized":False,
        "raw_results_exported":False,
        "predictions_per_match_exported":False,
        "training_allowed":False,
        "gate13_pass":False,
    }
    result["report_sha256"]=sha(result)
    return result


def one_time_pitchapi(*,frozen_file=REFERENCE):
    token=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not token:
        raise BaselineSafetyError("STEP13_PAIRED_PROVIDER_SECRET_MISSING")
    safe=json.loads(Path(SAFE_PATH).read_text(encoding="utf8"))
    if (safe.get("schema")!="kb3-step12-methodology-v1" or safe.get("training_allowed") is not False or
        safe.get("partition_counts")!={"TEST":380,"TRAIN":760,"VALIDATION":380}):
        raise BaselineSafetyError("STEP13_PAIRED_SAFE_SPLIT_CHANGED")
    ref=json.loads(Path(frozen_file).read_text(encoding="utf8"))
    if ref.get("report_sha256")!=REFERENCE_SHA:
        raise BaselineSafetyError("STEP13_PAIRED_ORIGINAL_FROZEN_SHA_CHANGED")
    from pitchapi import PitchAPI
    client=PitchAPI(api_key=token)
    seasons={}
    # Exactly 3 finished historical seasons, never TEST season 2026/27.
    for year in SEASONS:
        seasons[year]=to_plain(client.leagues.matches(LEAGUE,season=year,status="played"))
    rows,_=extract_research_rows(seasons,safe_view=safe)
    return paired_uncertainty(rows,reference=ref,expected_reference_sha=REFERENCE_SHA)


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--output",required=True)
    args=cli.parse_args()
    try:
        report=one_time_pitchapi()
        print(freeze_manifest(report,args.output))
        for metric in ("log","brier"):
            x=report["overall"][metric]
            print("STEP13_REAL_PAIRED_AGGREGATE_ONLY",metric,
                "delta",round(x["rolling_minus_expanding_mean"],7),
                "ci95",[round(v,7) for v in x["week_cluster_bootstrap_ci95"]],
                "includes_zero",x["interval_includes_zero"])
        print("STEP13_PAIRED_NO_TEST_NO_PRODUCTION",
              "VALIDATION",report["validation_n"],
              "TEST",report["test_rows_read"],
              "GATE13",report["gate13_pass"],
              "SHA",report["report_sha256"])
    except Exception as exc:
        print("STEP13_PAIRED_RESEARCH_BLOCKED",type(exc).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
