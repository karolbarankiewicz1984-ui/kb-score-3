"""KB Score 3.0 Step13: isolated ONLINE-READY 1X2 probability recalibration.

This is a deterministic train/gate/monitor research module. It DOES NOT pull
PitchAPI, learn from frozen 2026/27 TEST fixtures, modify Elo or Poisson, or
deploy a model. Each future input must be an independently admitted
CALIBRATION fixture outside the reserved TRAIN/VALIDATION/TEST seasons.

After outcomes become available in a permitted stream, temperature scaling
is fitted on earlier observations and only compared on later observations.
Original frozen 1X2 snapshots are never changed. This module alone cannot
verify a provider's publication time or a receipt's cryptographic signature.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
import json
import math
from pathlib import Path
import re

from src.kb3_split import sha, timestamp, freeze_manifest
from src.kb3_step13_baseline import BaselineSafetyError

SCHEMA="kb3-step13-isolated-adaptive-calibration-v1"
GRID=(0.75,0.85,1.0,1.15,1.30,1.5,1.75)
CLASSES=("1","X","2")
FROZEN_HOLDOUT_END="2027-07-01T00:00:00Z"
MIN_FIT=100
MIN_GATE=40
MIN_LAG_HOURS=3
_SOURCE_RE=r"^[0-9a-f]{64}$"
FIELDS=frozenset((
    "fixture_id","partition","origin","kickoff_utc",
    "forecast_frozen_at_utc","result_observed_at_utc",
    "forecast_receipt_sha256","result_receipt_sha256",
    "p_1x2","outcome_90m",
))
ACCEPTED_ORIGINS={"PROSPECTIVE_PROVIDER_RECEIPTS","SYNTHETIC_UNIT_TEST"}
ACCEPTED_ROLES={"FUTURE_CALIBRATION","SYNTHETIC_CALIBRATION"}


def _block(code):
    raise BaselineSafetyError("STEP13_ADAPTIVE_"+code)


def transform(probabilities,temperature):
    """Preserves class order/ranking; smooths/sharpens probability simplex."""
    if type(temperature) not in (int,float) or not math.isfinite(temperature) or not 0.5<=temperature<=3.0:
        _block("TEMPERATURE_INVALID")
    if not isinstance(probabilities,dict) or set(probabilities)!=set(CLASSES):
        _block("PROBABILITY_SCHEMA_INVALID")
    if any(type(probabilities[k]) not in (int,float) or
           not math.isfinite(probabilities[k]) or not 0<probabilities[k]<1
           for k in CLASSES):
        _block("PROBABILITY_VALUES_INVALID")
    if abs(math.fsum(probabilities.values())-1.0)>1e-10:
        _block("PROBABILITY_NOT_NORMALIZED")
    logits=[math.log(probabilities[k])/temperature for k in CLASSES]
    anchor=max(logits)
    weights=[math.exp(z-anchor) for z in logits]
    total=math.fsum(weights)
    return {k:weights[i]/total for i,k in enumerate(CLASSES)}


def metrics(rows,temperature):
    if not rows:_block("METRICS_EMPTY")
    logloss,brier=0.0,0.0
    for r in rows:
        p=transform(r["p_1x2"],temperature)
        label=r["outcome_90m"]
        logloss-=math.log(p[label])
        brier+=math.fsum((p[k]-int(k==label))**2 for k in CLASSES)
    n=len(rows)
    return {"n":n,"multiclass_logloss":logloss/n,
            "multiclass_brier_sum3":brier/n}


def _validate(rows,*,now_utc,forbidden_ids):
    if not isinstance(rows,list):
        _block("RECEIPTS_NOT_LIST")
    now=timestamp(now_utc)
    approved=[]
    seen=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!=FIELDS:
            _block("UNEXPECTED_FIELD_ODDS_OR_MISSING_RECEIPT")
        ident=r["fixture_id"]
        if not isinstance(ident,str) or not ident or ident in seen:
            _block("DUPLICATE_OR_INVALID_FIXTURE")
        seen.add(ident)
        if ident in forbidden_ids or r["partition"] not in ACCEPTED_ROLES:
            _block("RESERVED_TEST_VALIDATION_TRAIN_FIXTURE_FORBIDDEN")
        role=r["partition"]
        origin=r["origin"]
        if ((role=="SYNTHETIC_CALIBRATION" and
             (origin!="SYNTHETIC_UNIT_TEST" or not ident.startswith("SYN-"))) or
            (role=="FUTURE_CALIBRATION" and
             (origin!="PROSPECTIVE_PROVIDER_RECEIPTS" or ident.startswith("SYN-")))):
            _block("ORIGIN_OR_PARTITION_INVALID")
        kick=timestamp(r["kickoff_utc"])
        before=timestamp(r["forecast_frozen_at_utc"])
        receipt=timestamp(r["result_observed_at_utc"])
        if (role=="FUTURE_CALIBRATION" and
            (kick<timestamp(FROZEN_HOLDOUT_END) or
             not before<kick or
             receipt<kick+timedelta(hours=MIN_LAG_HOURS) or
             receipt>now)):
            _block("FUTURE_CALIBRATION_TEMPORAL_LEAKAGE")
        if not before<kick or receipt<kick+timedelta(hours=MIN_LAG_HOURS) or receipt>now:
            _block("EVENT_TIME_OR_RESULT_RECEIPT_INVALID")
        if not all(isinstance(r[k],str) and re.fullmatch(_SOURCE_RE,r[k])
                   for k in ("forecast_receipt_sha256","result_receipt_sha256")):
            _block("SOURCE_RECEIPT_SHA_INVALID")
        transform(r["p_1x2"],1.0)
        if r["outcome_90m"] not in CLASSES:
            _block("OUTCOME_90M_INVALID")
        approved.append(r)
    if len(approved)<MIN_FIT+MIN_GATE:
        _block("INSUFFICIENT_ELIGIBLE_OBSERVATIONS")
    if len({r["partition"] for r in approved})!=1:
        _block("SYNTHETIC_AND_REAL_NEVER_MIXED")
    return sorted(approved,key=lambda r:(r["kickoff_utc"],r["fixture_id"]))


def propose_adaptive_update(rows,*,now_utc, frozen_manifest, min_logloss_gain=0.005):
    """Candidate only: no mutation, no promoted model, no TEST learning.

    The first 70% of allowed observations fits the fixed temperature grid.
    The LAST 30% is a fresh chronological internal gate; holdout TEST never
    appears in either portion. Later gate results cannot influence fitted T.
    """
    if (not isinstance(frozen_manifest,dict) or
        frozen_manifest.get("schema")!="kb3-step12-methodology-v1" or
        frozen_manifest.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380}):
        _block("FROZEN_SPLIT_NOT_VERIFIED")
    if frozen_manifest.get("training_allowed") is not False:
        _block("ORIGINAL_SPLIT_PROMOTION_FORBIDDEN")
    fixtures=frozen_manifest.get("fixtures")
    if not isinstance(fixtures,list) or len(fixtures)!=1520:
        _block("FROZEN_SPLIT_FIXTURE_SET_CHANGED")
    forbidden={r["fixture_id"] for r in fixtures}
    if len(forbidden)!=1520:
        _block("FROZEN_SPLIT_DUPLICATE_FIXTURES")
    if (type(min_logloss_gain) not in (int,float) or
         not math.isfinite(min_logloss_gain) or not 0<=min_logloss_gain<=0.1):
        _block("GAIN_THRESHOLD_INVALID")
    ordered=_validate(rows,now_utc=now_utc,forbidden_ids=forbidden)
    # Bounded, fixed 70/30 train/gate; split date recorded explicitly.
    pivot=int(0.70*len(ordered))
    if pivot<MIN_FIT or len(ordered)-pivot<MIN_GATE:
        _block("NOT_ENOUGH_FIT_OR_GATE")
    fit,gate=ordered[:pivot],ordered[pivot:]
    # Guard against partial look-ahead via match dates at fold boundary:
    # a result from the fit group must be OBSERVED before the first gate
    # prediction, not merely played earlier.
    cutoff=min(timestamp(x["forecast_frozen_at_utc"]) for x in gate)
    if any(timestamp(x["result_observed_at_utc"])>=cutoff for x in fit):
        _block("FITTING_RESULT_OBSERVED_AFTER_GATE_FORECAST")
    fit_grid={t:metrics(fit,t) for t in GRID}
    # Fixed grid selection uses ONLY fit rows.
    fitted=min(GRID,key=lambda t:(fit_grid[t]["multiclass_logloss"],abs(t-1),t))
    baseline=metrics(gate,1.0)
    candidate=metrics(gate,fitted)
    gain=baseline["multiclass_logloss"]-candidate["multiclass_logloss"]
    # Gate does not select different temperature; just checks candidate.
    improves=(fitted!=1.0 and gain>=min_logloss_gain and
              candidate["multiclass_brier_sum3"]<=baseline["multiclass_brier_sum3"]+1e-12)
    result={
        "schema":SCHEMA,
        "source_kind":fit[0]["partition"],
        "frozen_legacy_holdout_test_2026_2027_used":False,
        "original_frozen_split_projection_sha256":frozen_manifest.get("projection_sha256"),
        "observed_at_utc":now_utc,
        "admitted_n":len(ordered),
        "fit_n":len(fit),"independent_gate_n":len(gate),
        "fit_ends_at_kickoff_utc":fit[-1]["kickoff_utc"],
        "gate_starts_at_kickoff_utc":gate[0]["kickoff_utc"],
        "all_fit_result_receipts_before_first_gate_prediction":True,
        "eligible_rows_sha256":sha(ordered),
        "fixed_temperature_grid":list(GRID),
        "selected_fit_only_temperature":fitted,
        "fit_only_grid_logloss":{str(t):fit_grid[t]["multiclass_logloss"] for t in GRID},
        "gate_original_model_metrics":baseline,
        "gate_candidate_model_metrics":candidate,
        "gate_logloss_improvement":gain,
        "min_predeclared_logloss_improvement":min_logloss_gain,
        "gate_candidate_improved":improves,
        "new_temperature_suggested_for_review":fitted if improves else None,
        "no_elo_or_poisson_parameter_change":True,
        "original_snapshot_20_predictions_untouched":True,
        "original_TEST_rows_accessed":0,
        "no_odds_used":True,
        "provider_receipt_hashes_not_cryptographically_certified_in_this_function":True,
        "inference_and_eligibility_subject_to_independent_review":True,
        "automatic_production_deployment":False,
        "training_allowed":False,"gate13_pass":False,
        "step14_started":False,
    }
    result["report_sha256"]=sha(result)
    return result


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--evidence",required=True)
    cli.add_argument("--frozen-split",default="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json")
    cli.add_argument("--observed-at-utc",required=True)
    cli.add_argument("--output",required=True)
    args=cli.parse_args()
    rows=json.loads(Path(args.evidence).read_text(encoding="utf8"))
    safe=json.loads(Path(args.frozen_split).read_text(encoding="utf8"))
    report=propose_adaptive_update(rows,now_utc=args.observed_at_utc,frozen_manifest=safe)
    freeze_manifest(report,args.output)
    print("STEP13_ADAPTIVE_RESEARCH_ONLY",
          "n",report["admitted_n"],
          "temperature",report["selected_fit_only_temperature"],
          "gate_gain",round(report["gate_logloss_improvement"],6),
          "review_needed",report["gate_candidate_improved"],
          "TEST_ROWS",report["original_TEST_rows_accessed"],
          "GATE13",report["gate13_pass"])
if __name__=="__main__":
    main()
