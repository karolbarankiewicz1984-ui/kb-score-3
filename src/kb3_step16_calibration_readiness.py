"""KB3 STEP16: read-only evidence gate and per-class 1/X/2 reliability.

Does not fit or activate calibration. Existing authenticated SQLite postmatch
pipeline owns the fit only after 100 historical + 50 genuinely new forecasts.
This audit deliberately rejects replacing real capture receipts with a count.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math

from src.kb3_pit_ledger import canonical
from src.kb3_step14_m1_math_calibration import order_probability, score_predictions

SCHEMA = "kb3-step16-independent-real-forward-calibration-readiness-v1"
LEGACY = "kb3-m0-real-shadow-settlement-logloss-brier-v1"
CURRENT = "kb3-step14-real-network-postmatch-3league-M0-1x2-scoring-v1"
FIT_MIN = 100
HOLDOUT_MIN = 50
CLASSES = ("1", "X", "2")
GRID = (0.7,0.85,1.0,1.15,1.4,1.8,2.2)

class Step16ReadinessError(ValueError):
    pass


def per_class_reliability(predictions, labels, *, bins=5):
    """Independent one-vs-rest reliability table; no parameter fitting."""
    if (not isinstance(predictions,list) or not isinstance(labels,list)
            or len(predictions)!=len(labels) or not predictions
            or type(bins) is not int or not 2<=bins<=20):
        raise Step16ReadinessError("INVALID_RELIABILITY_SCOPE")
    sums={c:[{"n":0,"sum_p":0.0,"positive":0} for _ in range(bins)]
          for c in CLASSES}
    for forecast,label in zip(predictions,labels):
        try:
            p=order_probability(forecast)
        except Exception as exc:
            raise Step16ReadinessError("INVALID_1X2_PROBABILITY") from exc
        if label not in CLASSES:
            raise Step16ReadinessError("INVALID_90MIN_LABEL")
        for j,c in enumerate(CLASSES):
            x=p[j]
            idx=min(bins-1,int(x*bins))
            bucket=sums[c][idx]
            bucket["n"]+=1
            bucket["sum_p"]+=x
            bucket["positive"]+=int(label==c)
    n=len(predictions)
    out={}
    for c in CLASSES:
        table=[{
            "bin":i,"count":v["n"],
            "mean_probability":v["sum_p"]/v["n"] if v["n"] else None,
            "observed_frequency":v["positive"]/v["n"] if v["n"] else None,
        } for i,v in enumerate(sums[c])]
        ece=sum(x["count"]/n*abs(x["mean_probability"]-x["observed_frequency"])
                for x in table if x["count"])
        out[c]={"n":n,"ece_ovr":ece,"reliability":table}
    old=score_predictions(predictions,labels)
    return {
        "n":n,
        "classes":out,
        "multiclass_log_loss":old["log_loss"],
        "multiclass_brier_sum3":old["brier_sum3"],
        "top1_ece_10bins":old["top1_ece_10bins"],
        "training_or_calibration_performed":False,
    }


def audit_initial_real_receipts(shadow, native):
    """Read two actual prior receipts. Counts alone NEVER unlock model fit."""
    if type(shadow) is not dict or type(native) is not dict:
        raise Step16ReadinessError("RECEIPTS_REQUIRED")
    clone={k:v for k,v in shadow.items() if k!="report_sha256"}
    digest=sha256(canonical(clone)).hexdigest()
    if (shadow.get("schema")!=LEGACY or shadow.get("report_sha256")!=digest
            or shadow.get("original_heldout_PL_TEST_accessed") is not False
            or shadow.get("automatic_production_calibration") is not False):
        raise Step16ReadinessError("LEGACY_REPORT_TAMPER_OR_PROTECTED_TEST")
    if (native.get("schema")!=CURRENT
            or native.get("original_Premier_League_TEST_accessed") is not False
            or native.get("calibration_auto_activated") is not False
            or native.get("M1_training_or_original_gate14_pass") is not False
            or native.get("processed_leagues")!=["ESP","ITA","GER"]):
        raise Step16ReadinessError("REAL_NATIVE_REPORT_TAMPER_OR_TEST")
    eval_record=native.get("evaluation")
    settle=native.get("settlement")
    if (not isinstance(eval_record,dict) or not isinstance(settle,dict)
            or eval_record.get("original_TEST_leak") is not False
            or eval_record.get("production_calibration_activated") is not False
            or eval_record.get("temperature_fit_minimum")!=FIT_MIN
            or eval_record.get("future_holdout_minimum")!=HOLDOUT_MIN):
        raise Step16ReadinessError("CALIBRATION_EVALUATION_CONTRACT_DRIFT")
    n_shadow=shadow.get("total_settled")
    n_native=settle.get("total_settled")
    n_evaluation=eval_record.get("scored_independent_matches")
    if any(type(n) is not int or n<0 for n in (n_shadow,n_native,n_evaluation)):
        raise Step16ReadinessError("INVALID_REAL_COUNTS")
    if n_native!=n_evaluation or n_shadow!=n_native:
        raise Step16ReadinessError("TWO_INDEPENDENT_SETTLEMENT_RECORDS_DISAGREE")
    if (shadow.get("newly_settled")!=0 or
            settle.get("newly_settled")!=0 or
            not isinstance(shadow.get("calibration_reviews"),list) or
            len(shadow["calibration_reviews"])!=1):
        raise Step16ReadinessError("UNEXPECTED_SETTLEMENT_EVENTS")
    prior=shadow["calibration_reviews"][0]
    if (prior.get("state")!="COLLECTING"
            or prior.get("n_unique_resolved")!=n_shadow
            or prior.get("calibration_training_min")!=FIT_MIN
            or prior.get("later_independent_holdout_min")!=HOLDOUT_MIN
            or prior.get("production_approved") is not False):
        raise Step16ReadinessError("PSEUDO_CALIBRATION_OR_MULTIPLE_VERSION_DRIFT")
    if (eval_record.get("candidate") is not None
            or eval_record.get("new_calibration_candidate") is not None
            or eval_record.get("new_holdout_review") is not None):
        raise Step16ReadinessError("IMPROPER_EARLY_CALIBRATION")
    # This specific evidence pack is explicitly the initial 0/100 snapshot.
    # If >0, demand a fresh full temporal/identity audit against immutable
    # SQLite, never silently claim that a summary demonstrates PIT provenance.
    if n_shadow!=0 or prior.get("needed_for_first_fit")!=FIT_MIN:
        raise Step16ReadinessError("NONZERO_COUNTS_REQUIRE_FULL_SQLITE_AUDIT")
    pre=native.get("forecast_existing_preflight")
    if (not isinstance(pre,dict)
            or pre.get("independently_existing_repo_forecast_hashes")!=12
            or pre.get("match_hash_identical") is not True):
        raise Step16ReadinessError("FORECAST_RECEIPT_IDENTITY_DRIFT")
    return {
        "schema":SCHEMA,
        "status":"COLLECTING_NOT_READY_FOR_TEMPERATURE",
        "as_of_utc":native.get("captured_at_utc"),
        "source_shadow_sha256":shadow["report_sha256"],
        "source_native_sha256":sha256(canonical(native)).hexdigest(),
        "separate_live_forecasts_preflight":12,
        "real_prematch_first_publication_independently_proven":
            pre.get("server_first_publication_utc_independently_proven") is True,
        "independently_settled_unique_games":0,
        "independent_cold_start_validation_matches_are_not_calibration":True,
        "fit_minimum":FIT_MIN,
        "fit_remaining":FIT_MIN,
        "prospective_holdout_minimum":HOLDOUT_MIN,
        "allowed_temperature_grid":list(GRID),
        "candidate_fitted":False,
        "holdout_evaluated":False,
        "auto_activation":False,
        "protected_test_2026_27_read":False,
        "formal_gate16_pass":False,
        "requires_realtime_FROZEN_SQLITE_integrity_to_proceed":True,
        "note":"Two authentic historical daily receipts with zero settled games. This is not historical native PIT certification or evidence of calibration quality.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shadow",required=True)
    p.add_argument("--native",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    target=Path(a.out)
    if target.exists():
        raise Step16ReadinessError("APPEND_ONLY_AUDIT_EXISTS")
    shadow=json.loads(Path(a.shadow).read_text())
    native=json.loads(Path(a.native).read_text())
    r=audit_initial_real_receipts(shadow,native)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("STEP16_READINESS="+json.dumps({"status":r["status"],"n":r["independently_settled_unique_games"],"fit_remaining":r["fit_remaining"],"gate16":r["formal_gate16_pass"]},sort_keys=True))


if __name__=="__main__":
    main()
