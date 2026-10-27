"""KB Score 3.0 existing Step13: offline post-hoc stability DIAGNOSTIC.

Accepts only the frozen AGGREGATE real-retrospective report. Does not read
individual match results, odds, provider API, the held-out TEST, or private
archive. It does not tune, retrain, promote a winner, or prove historical PIT.
All calibration comparisons are descriptive post-hoc validation diagnostics.
"""
from __future__ import annotations
import argparse
import copy
import math
from pathlib import Path
import json

from src.kb3_split import sha, freeze_manifest
from src.kb3_step13_baseline import BaselineSafetyError

SOURCE_SHA="3d950fff30b57c94a6f71462c7521cfda2cb0b27c666d59d09d274261efca803"
SOURCE="data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json"
SCHEMA="kb3-step13-aggregate-calibration-stability-v0.6"
METHODS=("EXPANDING","ROLLING_24_CALENDAR_MONTHS")
FOLDS=(60,126,123,71)
EXPECTED_START=("2025-07-01T00:00:00Z","2025-10-01T00:00:00Z",
                "2026-01-01T00:00:00Z","2026-04-01T00:00:00Z")
BIN_COUNT=5


def _finite_unit(value,label):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1:
        raise BaselineSafetyError("STEP13_STABILITY_INVALID_"+label)
    return float(value)


def audit_stability(source):
    if not isinstance(source,dict) or source.get("report_sha256")!=SOURCE_SHA:
        raise BaselineSafetyError("STEP13_STABILITY_WRONG_PINNED_REPORT")
    if sha({k:v for k,v in source.items() if k!="report_sha256"})!=SOURCE_SHA:
        raise BaselineSafetyError("STEP13_STABILITY_TAMPERED_REPORT")
    if (source.get("schema")!="kb3-step13-live-reread-research-v0.5"
            or source.get("source_category")!="REAL_PROVIDER_RETRIEVED_NOW_RETROSPECTIVE_EVENTTIME_ONLY"
            or source.get("train_partition_rows")!=760
            or source.get("validation_partition_rows")!=380
            or source.get("test_rows_processed")!=0
            or source.get("test_partition_data_requested") is not False
            or source.get("source_scores_in_report") is not False
            or source.get("historical_pit_backtest_performed") is not False
            or source.get("training_allowed") is not False
            or source.get("gate13_pass") is not False):
        raise BaselineSafetyError("STEP13_STABILITY_EVIDENCE_OR_TEST_GATE_CHANGED")
    folds=source.get("folds")
    if (not isinstance(folds,list) or len(folds)!=4 or
            [f.get("validation_count") for f in folds]!=list(FOLDS) or
            [f.get("validation_from_utc") for f in folds]!=list(EXPECTED_START)):
        raise BaselineSafetyError("STEP13_STABILITY_EXPECTED_FOLDS_MISSING")
    overall=source.get("overall")
    if not isinstance(overall,dict) or set(overall)!=set(METHODS):
        raise BaselineSafetyError("STEP13_STABILITY_METHODS_CHANGED")
    per_method={}
    for name in METHODS:
        merged_bins=[{"n":0,"correct":0.0,"confidence_total":0.0} for _ in range(BIN_COUNT)]
        each=[]
        n_total=0
        ll_total=brier_total=ece_weighted=0.0
        boundary_hits=0
        for ix,fold in enumerate(folds,1):
            methods=fold.get("methods")
            if not isinstance(methods,dict) or set(methods)!=set(METHODS):
                raise BaselineSafetyError("STEP13_STABILITY_FOLD_METHODS_CHANGED")
            entry=methods[name]
            if entry.get("validation_labels_used_for_fitting") is not False or entry.get("parameters_frozen_before_validation") is not True:
                raise BaselineSafetyError("STEP13_STABILITY_LOOKAHEAD_GUARD_CHANGED")
            other=methods[METHODS[1-METHODS.index(name)]]
            if entry.get("validation_fixture_ids_sha256")!=other.get("validation_fixture_ids_sha256"):
                raise BaselineSafetyError("STEP13_STABILITY_UNPAIRED_FOLD_TARGETS")
            met=entry["metrics"]
            n=fold["validation_count"]
            if met.get("n")!=n or not isinstance(met.get("calibration_bins"),list) or len(met["calibration_bins"])!=BIN_COUNT:
                raise BaselineSafetyError("STEP13_STABILITY_BIN_SHAPE_INVALID")
            current_hits=current_conf=0.0
            binned=0
            ece=0.0
            for bidx,bin_ in enumerate(met["calibration_bins"]):
                bn=bin_.get("n")
                if type(bn) is not int or bn<0:
                    raise BaselineSafetyError("STEP13_STABILITY_BIN_N_INVALID")
                if bn:
                    confidence=_finite_unit(bin_.get("confidence"),"BIN_CONFIDENCE")
                    accuracy=_finite_unit(bin_.get("accuracy"),"BIN_ACCURACY")
                    if not bidx/5<=confidence<=min(1,(bidx+1)/5+1e-12):
                        raise BaselineSafetyError("STEP13_STABILITY_BIN_BOUNDARY_INVALID")
                    if abs(bn*accuracy-round(bn*accuracy))>1e-8:
                        raise BaselineSafetyError("STEP13_STABILITY_HITS_NOT_INTEGER")
                    current_hits+=bn*accuracy
                    current_conf+=bn*confidence
                    merged_bins[bidx]["n"]+=bn
                    merged_bins[bidx]["correct"]+=bn*accuracy
                    merged_bins[bidx]["confidence_total"]+=bn*confidence
                    ece+=bn*abs(accuracy-confidence)/n
                elif bin_.get("accuracy") is not None or bin_.get("confidence") is not None:
                    raise BaselineSafetyError("STEP13_STABILITY_EMPTY_BIN_NOT_NULL")
                binned+=bn
            if binned!=n or abs(ece-met["top_class_ece_5bin"])>1e-10:
                raise BaselineSafetyError("STEP13_STABILITY_BIN_AGGREGATION_MISMATCH")
            ll=met["multiclass_logloss"]
            brier=met["multiclass_brier_sum3"]
            if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=3 for x in (ll,brier)):
                raise BaselineSafetyError("STEP13_STABILITY_INVALID_METRIC")
            p=entry["fitted_parameters"]
            boundary_hits+=int(p["elo_goal_elasticity"]==0.6)
            each.append({
                "fold":ix, "validation_n":n,
                "top1_correct_count":int(round(current_hits)),
                "top1_accuracy":current_hits/n,
                "mean_top1_confidence":current_conf/n,
                "accuracy_minus_confidence":(current_hits-current_conf)/n,
                "top1_ece_5bin":ece,
                "multiclass_logloss":ll,
                "multiclass_brier_sum3":brier,
                "elo_elasticity_at_original_grid_upper_edge":p["elo_goal_elasticity"]==0.6,
            })
            n_total+=n
            ll_total+=n*ll
            brier_total+=n*brier
            ece_weighted+=n*ece
        if n_total!=380:
            raise BaselineSafetyError("STEP13_STABILITY_WRONG_TOTAL")
        pooled_ece=sum(abs(b["correct"]-b["confidence_total"])/n_total
                       for b in merged_bins if b["n"])
        hits=sum(b["correct"] for b in merged_bins)
        expected=sum(b["confidence_total"] for b in merged_bins)
        score=overall[name]
        if (score.get("validation_n")!=n_total
                or abs(score.get("multiclass_logloss_fold_weighted")-ll_total/n_total)>1e-10
                or abs(score.get("multiclass_brier_sum3_fold_weighted")-brier_total/n_total)>1e-10
                or abs(score.get("top_class_ece_5bin_fold_weighted")-ece_weighted/n_total)>1e-10):
            raise BaselineSafetyError("STEP13_STABILITY_OVERALL_METRIC_MISMATCH")
        per_method[name]={
            "validation_n":n_total,"quarterly":each,
            "top1_correct_count":int(round(hits)),
            "top1_accuracy":hits/n_total,
            "mean_top1_confidence":expected/n_total,
            "accuracy_minus_confidence":(hits-expected)/n_total,
            "top1_ece_pooled_5bin_descriptive_only":pooled_ece,
            "top1_ece_fold_weighted_5bin":ece_weighted/n_total,
            "elo_elasticity_grid_upper_edge_folds":boundary_hits,
            "merged_bins":merged_bins,
        }
    exp=per_method[METHODS[0]]["quarterly"]
    roll=per_method[METHODS[1]]["quarterly"]
    ll_delta=overall[METHODS[1]]["multiclass_logloss_fold_weighted"]-overall[METHODS[0]]["multiclass_logloss_fold_weighted"]
    brier_delta=overall[METHODS[1]]["multiclass_brier_sum3_fold_weighted"]-overall[METHODS[0]]["multiclass_brier_sum3_fold_weighted"]
    result={
        "schema":SCHEMA,
        "original_aggregate_report_sha256":SOURCE_SHA,
        "original_report_file":SOURCE,
        "data_class":"REAL_RETROSPECTIVE_PROVIDER_RESULTS_AGGREGATES_ONLY_NOT_PIT",
        "same_380_validation_fixtures_across_methods":True,
        "train_initial":760,
        "validation_total":380,
        "test_rows_read":0,
        "methods":per_method,
        "logloss_rolling_minus_expanding":ll_delta,
        "brier_rolling_minus_expanding":brier_delta,
        "folds_with_lower_expanding_logloss":sum(e["multiclass_logloss"]<r["multiclass_logloss"] for e,r in zip(exp,roll)),
        "folds_with_lower_rolling_logloss":sum(e["multiclass_logloss"]>r["multiclass_logloss"] for e,r in zip(exp,roll)),
        "folds_with_equal_logloss":sum(e["multiclass_logloss"]==r["multiclass_logloss"] for e,r in zip(exp,roll)),
        "fold3_expanding_accuracy_minus_confidence":exp[2]["accuracy_minus_confidence"],
        "fold3_rolling_accuracy_minus_confidence":roll[2]["accuracy_minus_confidence"],
        "fold3_overconfidence_detected_both_methods":exp[2]["accuracy_minus_confidence"]<-0.09 and roll[2]["accuracy_minus_confidence"]<-0.09,
        "all_eight_elasticity_fits_at_original_grid_upper_edge":all(x["elo_elasticity_grid_upper_edge_folds"]==4 for x in per_method.values()),
        "pooled_ece_may_mask_quarterly_sign_changes":True,
        "real_historical_pit_proven":False,
        "retraining_or_parameter_grid_change_performed":False,
        "comparison_statistically_significant":None,
        "per_match_paired_confidence_intervals_available":False,
        "model_winner_promoted":False,
        "training_allowed":False,
        "gate13_pass":False,
        "next":"STEP13_FORWARD_PIT_COLLECTION_AND_PREDECLARED_TRAIN_ONLY_ELASTICITY_DIAGNOSTICS",
    }
    result["report_sha256"]=sha(result)
    return result


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--source",default=SOURCE)
    cli.add_argument("--output",required=True)
    opts=cli.parse_args()
    report=json.loads(Path(opts.source).read_text(encoding="utf8"))
    result=audit_stability(report)
    print(freeze_manifest(result,opts.output))
    print("KB3_STEP13_CALIBRATION_STABILITY_AGGREGATE_ONLY",
          "fold3_exp_gap",round(result["fold3_expanding_accuracy_minus_confidence"],6),
          "fold3_roll_gap",round(result["fold3_rolling_accuracy_minus_confidence"],6),
          "grid_upper_8of8",result["all_eight_elasticity_fits_at_original_grid_upper_edge"],
          "GATE13",result["gate13_pass"])


if __name__=="__main__":
    main()
