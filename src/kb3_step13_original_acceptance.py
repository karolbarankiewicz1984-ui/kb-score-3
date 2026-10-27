"""Formal scope-limited Step13 original-baseline acceptance, with independent data guard.

Acceptance is *only* original step's mathematical and retrospective research
deliverable. It does not turn hindsight observations into historical PIT, does
not allow training on unverified observations and does not certify production.
Original frozen evidence, forward forecasts, and original test gates unchanged.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from src.kb3_split import sha,freeze_manifest
from src.kb3_step13_baseline import BaselineParameters,forecast,BaselineSafetyError

SCHEMA="kb3-step13-original-baseline-scope-acceptance-v1"
PINNED={
    "real_retro":("data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json","3d950fff30b57c94a6f71462c7521cfda2cb0b27c666d59d09d274261efca803"),
    "math":("data/audits/STEP13_MATH_INDEPENDENT_2026-10-27.json","5c9d6a790950e07e6ada8d306a38d1dffaefeeede216b0444effa0f0114f98f3"),
    "leakage":("data/audits/STEP13_LEAKAGE_INDEPENDENT_2026-10-27.json","f4b0d1e1c3c89bd15a311407c2906eaa64d960b192340249dd197bb6907ca542"),
    "stability":("data/audits/STEP13_REAL_RETROSPECTIVE_STABILITY_2026-10-27.json","10e75ea0a247ca3d446379238ac4f97aab6be90f8ee55aac6796cf7d83bdeb8e"),
    "paired":("data/audits/STEP13_REAL_PAIRED_UNCERTAINTY_2026-10-27.json","e1a1694da3b43f944696b456521448015b855f47da8d91d181ee5d547a9d47d4"),
    "forward_first":("data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json","9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389"),
    "forward_second":("data/forecasts/STEP13_SECOND_PROSPECTIVE_PREMATCH_2026-10-27.json","bca520ffd20021cf984189c6aa5a15eda078b5a501f32345c87c334d6c3b045e"),
}
GRID_ELO=((1500.,1500.),(1600.,1500.),(1400.,1600.))
ACCEPTANCE="ORIGINAL_STEP13_BASELINE_BUILD_AND_RETROSPECTIVE_RESEARCH_ONLY"

def reject(reason):
    raise BaselineSafetyError("STEP13_ACCEPTANCE_"+reason)

def check_original_scope(*,root="."):
    base=Path(root)
    records={}
    for name,(rel,digest) in PINNED.items():
        file=base/rel
        raw=json.loads(file.read_text(encoding="utf8"))
        if not isinstance(raw,dict) or raw.get("report_sha256")!=digest:
            reject("MISSING_OR_WRONG_SOURCE_"+name)
        if sha({k:v for k,v in raw.items() if k!="report_sha256"})!=digest:
            reject("TAMPERED_"+name)
        records[name]=raw

    retro=records["real_retro"]
    if (retro.get("train_partition_rows")!=760 or retro.get("validation_partition_rows")!=380 or
        retro.get("test_rows_processed")!=0 or retro.get("test_partition_data_requested") is not False or
        retro.get("source_category")!="REAL_PROVIDER_RETRIEVED_NOW_RETROSPECTIVE_EVENTTIME_ONLY" or
        retro.get("historical_pit_backtest_performed") is not False or
        retro.get("gate13_pass") is not False or retro.get("training_allowed") is not False):
        reject("HISTORICAL_PROVENANCE_GUARD")
    folds=retro.get("folds",[])
    if len(folds)!=4 or [f.get("validation_count") for f in folds]!=[60,126,123,71]:
        reject("WALK_FORWARD_FOLDS")
    methods=("EXPANDING","ROLLING_24_CALENDAR_MONTHS")
    expected={
        "EXPANDING":(1.032636740359353,0.6185368951343552,0.07395339036333402),
        "ROLLING_24_CALENDAR_MONTHS":(1.0343803885705523,0.6196881659096319,0.07331600872222804),
    }
    for m in methods:
        v=retro["overall"][m]
        if v["validation_n"]!=380 or any(not math.isclose(v[key],target,abs_tol=1e-12,rel_tol=0) for key,target in zip((
            "multiclass_logloss_fold_weighted","multiclass_brier_sum3_fold_weighted",
            "top_class_ece_5bin_fold_weighted"),expected[m])):
            reject("METRICS_NOT_REPRODUCED")

    mx=records["math"]
    leakage=records["leakage"]
    stability=records["stability"]
    paired=records["paired"]
    a,b=records["forward_first"],records["forward_second"]
    if (mx.get("identity_checks")!=35 or mx.get("result_labels_read")!=0 or
        not all(value<1e-9 for value in mx["numerical_max_absolute_deviation"].values()) or
        leakage.get("test_scores_permitted")!=0 or leakage.get("query_statuses_static")!=["played","upcoming"] or
        leakage.get("result_labels_read")!=0 or
        stability.get("validation_total")!=380 or stability.get("test_rows_read")!=0 or
        stability.get("fold3_overconfidence_detected_both_methods") is not True or
        paired.get("validation_n")!=380 or paired.get("test_rows_read")!=0 or
        any(paired["overall"][k]["interval_includes_zero"] is not True for k in ("log","brier"))):
        reject("RESEARCH_CONTROL_REPORTS_CHANGED")
    if (a["first_snapshot_match_count"]!=10 or b["cohort_target_count"]!=10 or
        a["test_results_accessed"]!=0 or b["TEST_results_read"]!=0 or
        a["training_allowed"] is not False or b["training_allowed"] is not False or
        len({x["fixture_id"] for x in a["forecasts"]}&{x["fixture_id"] for x in b["forecasts"]})!=0):
        reject("FORWARD_SNAPSHOT_GUARDS_CHANGED")
    test_pairs=0
    for rh,ra in GRID_ELO:
        probs=forecast(rh,ra,BaselineParameters())["p_1x2"]
        if set(probs)!={"1","X","2"} or abs(math.fsum(probs.values())-1.0)>1e-12:
            reject("NOT_NORMALIZED")
        test_pairs+=1
    # An honest weak baseline is uniform p(1/X/2)=1/3:
    # purely mathematical, not fitted to any data or used for champion selection.
    uniform_logloss=math.log(3)
    uniform_brier=2/3
    report={
        "schema":SCHEMA,
        "scope":ACCEPTANCE,
        "original_requirements":{
            "elo_poisson_1x2_and_goals_engine":"PASS",
            "1x2_probability_simplex":"PASS",
            "no_bookmaker_odds_as_model_inputs":"PASS",
            "synthetic_reference_cases":"PASS",
            "retrospective_historical_research_test":"PASS_WITH_NON_PIT_LIMITATION",
            "brier_logloss_calibration_dataset_version_report":"PASS",
            "original_step13_checklist":"PASS_LIMITED_SCOPE",
        },
        "evidence_sha256":{name:value[1] for name,value in PINNED.items()},
        "train_rows":760,"retrospective_validation_rows":380,
        "retrospective_validation_folds":[60,126,123,71],
        "historical_test_rows_read":0,
        "forward_prematch_predictions_frozen":20,
        "forward_test_results_read":0,
        "math_test_cases_checked":test_pairs,
        "reference_uniform_random_1x2_logloss":uniform_logloss,
        "reference_uniform_random_1x2_brier_sum3":uniform_brier,
        "reference_is_unfitted_uniform_chance_not_an_empirical_competitor":True,
        "empirical_retro_expanding":retro["overall"]["EXPANDING"],
        "empirical_retro_rolling":retro["overall"]["ROLLING_24_CALENDAR_MONTHS"],
        "paired_95pct_logloss_ci_contains_zero":True,
        "paired_95pct_brier_ci_contains_zero":True,
        "quarter3_overconfidence_remains_open":True,
        "historical_provider_prematch_pit_certified":False,
        "original_unverified_source_promoted_to_training":False,
        "quality_risk_remaining":"REAL_RETROSPECTIVE_NOT_PROVIDER_PIT_AND_ELASTICITY_GRID_EDGE",
        "step13_original_scope_accepted":True,
        "global_production_eligibility_granted":False,
        "external_step11_step12_provenance_training_gate_overridden":False,
        "no_wagering_model_authorized":True,
        "model_champion_selected":False,
        "previous_reports_gate13_pass_values_unchanged":True,
        "original_frozen_elo_poisson_parameters_unchanged":True,
        "step14_next":"OPEN_METHOD_SPEC_ONLY_CATBOOST_UNTIL_PIT_TRAINING_ELIGIBLE",
        "training_allowed":False,
    }
    report["report_sha256"]=sha(report)
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    p=parser.parse_args()
    r=check_original_scope()
    freeze_manifest(r,p.output)
    print("STEP13_ORIGINAL_SCOPE_ACCEPTANCE_PASS_RETRO_NOT_PIT",
          "TRAIN",r["train_rows"],"VALIDATION",r["retrospective_validation_rows"],
          "TEST_OUTCOMES",r["forward_test_results_read"],
          "ELIGIBLE_PRODUCTION",r["global_production_eligibility_granted"],
          "SHA",r["report_sha256"])

if __name__=="__main__":
    main()
