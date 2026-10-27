"""KB Score 3.0 / Step 13: PRE-REGISTERED prospective outcome scoring contract.

This module MUST NOT access a network or historical/test dataset by itself.
It can only score the EXACT ten predictions irreversibly frozen on Oct 27, 2026,
after their games finish. Call it with ten explicit post-match provider receipts
in memory; never silently query the other 370 held-out TEST fixtures.

Outcomes are never included in the aggregate result. A supplied clock or
receipt is not itself proof of a provider capture; preserve separate evidence.
This report is for research only, not training, model selection, or wagering.
"""
from __future__ import annotations
from datetime import timedelta
import math
import re

from src.kb3_split import sha,timestamp
from src.kb3_step13_baseline import BaselineSafetyError

SOURCE_FILE="data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json"
SOURCE_HASH="9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389"
OUTPUT_SCHEMA="kb3-step13-locked-ten-prospective-evaluation-protocol-v1"
RECEIPT_KEYS=frozenset({
    "fixture_id","home_team_id","away_team_id","kickoff_utc","status",
    "goals_home_90","goals_away_90","observed_at_utc",
    "source","capture_sha256",
})
MIN_FINAL_LAG=timedelta(hours=3)
_SHA=re.compile(r"^[a-f0-9]{64}$")


def _reject(code):
    raise BaselineSafetyError("STEP13_FORWARD_SCORE_"+code)


def _check_snapshot(snapshot):
    if not isinstance(snapshot,dict) or snapshot.get("report_sha256")!=SOURCE_HASH:
        _reject("ORIGINAL_SNAPSHOT_SHA_MISMATCH")
    if sha({k:v for k,v in snapshot.items() if k!="report_sha256"})!=SOURCE_HASH:
        _reject("ORIGINAL_SNAPSHOT_TAMPERED")
    if (snapshot.get("schema")!="kb3-step13-prospective-first-frozen-shadow-v0.9"
            or snapshot.get("first_snapshot_match_count")!=10
            or len(snapshot.get("forecasts",[]))!=10
            or snapshot.get("train_rows_admitted")!=760
            or snapshot.get("validation_rows_admitted")!=0
            or snapshot.get("test_results_accessed")!=0
            or snapshot.get("training_allowed") is not False
            or snapshot.get("gate13_pass") is not False):
        _reject("ORIGINAL_SNAPSHOT_SAFETY_CHANGED")
    seen=set()
    frozen=timestamp(snapshot["forecast_frozen_at_utc"])
    original_seen=timestamp(snapshot["observed_at_utc"])
    if frozen<original_seen:
        _reject("SNAPSHOT_FROZEN_BEFORE_CAPTURE")
    for f in snapshot["forecasts"]:
        fid=f["fixture_id"]
        if fid in seen:
            _reject("DUPLICATED_PREDICTION")
        seen.add(fid)
        if (timestamp(f["forecast_frozen_at_utc"])!=frozen
                or timestamp(f["source_observed_at_utc"])!=original_seen
                or timestamp(f["kickoff_utc"])<=frozen
                or f["scores_at_source"]!={"home":None,"away":None}
                or f["target_result_known_before_forecast"] is not False):
            _reject("NOT_PREMATCH_FROZEN")
        probs=f["probabilities_1x2"]
        if (not isinstance(probs,dict) or set(probs)!={"1","X","2"}
            or any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 or v>=1
                   for v in probs.values()) or
                not math.isclose(sum(probs.values()),1,abs_tol=1e-12)):
            _reject("PROBABILITY_INVALID")
    return {f["fixture_id"]:f for f in snapshot["forecasts"]}


def _check_receipts(predictions, final_receipts, *, scoring_observed_at_utc):
    if not isinstance(final_receipts,list) or len(final_receipts)!=10:
        _reject("MUST_HAVE_EXACTLY_TEN_RESULTS")
    clock=timestamp(scoring_observed_at_utc)
    if clock<max(timestamp(f["kickoff_utc"])+MIN_FINAL_LAG
                 for f in predictions.values()):
        _reject("SCORE_JOB_BEFORE_ALL_MATCHES_FINISHED")
    ids=set()
    for receipt in final_receipts:
        if not isinstance(receipt,dict) or set(receipt)!=RECEIPT_KEYS:
            _reject("RECEIPT_FIELDS_UNEXPECTED_OR_MISSING")
        fid=receipt["fixture_id"]
        if fid in ids or fid not in predictions:
            _reject("RECEIPT_DUPLICATED_OR_NON_TARGET_TEST")
        ids.add(fid)
        prediction=predictions[fid]
        if (receipt["source"]!="PitchAPI" or receipt["status"]!="finished"
                or receipt["home_team_id"]!=prediction["home_team_id"]
                or receipt["away_team_id"]!=prediction["away_team_id"]
                or timestamp(receipt["kickoff_utc"])!=timestamp(prediction["kickoff_utc"])):
            _reject("RECEIPT_SOURCE_IDENTITY_OR_STATUS_INVALID")
        captured=timestamp(receipt["observed_at_utc"])
        if (captured < timestamp(receipt["kickoff_utc"])+MIN_FINAL_LAG or
                captured > clock or captured <= timestamp(prediction["forecast_frozen_at_utc"])):
            _reject("RECEIPT_NOT_GENUINELY_AFTER_MATCH")
        for field in ("goals_home_90","goals_away_90"):
            value=receipt[field]
            if type(value) is not int or not 0<=value<=30:
                _reject("INVALID_NINETY_MINUTE_SCORE")
        sig=receipt["capture_sha256"]
        if not isinstance(sig,str) or not _SHA.fullmatch(sig):
            _reject("MISSING_CAPTURE_DIGEST")
    if ids!=set(predictions):
        _reject("INCOMPLETE_RESULT_IDS")
    return clock


def score_locked_first_ten(snapshot, final_receipts, *, scoring_observed_at_utc):
    """Return safe aggregate scoring ONLY; no individual score/forecast leakage.

    Pure calculation uses supplied receipts; separate source verification is
    required before claiming trustworthy forward metrics in production.
    """
    predictions=_check_snapshot(snapshot)
    _check_receipts(predictions,final_receipts,
                    scoring_observed_at_utc=scoring_observed_at_utc)
    n=10
    correct=0
    loss=0.0
    brier=0.0
    goal_mae=0.0
    goal_nll=0.0
    bins=[{"n":0,"conf_total":0.0,"hits":0} for _ in range(5)]
    labels={"1","X","2"}
    for receipt in final_receipts:
        g_h,g_a=receipt["goals_home_90"],receipt["goals_away_90"]
        observed="1" if g_h>g_a else ("2" if g_h<g_a else "X")
        p=predictions[receipt["fixture_id"]]
        probabilities=p["probabilities_1x2"]
        maximum=max(("1","X","2"),key=lambda k:probabilities[k])
        correct+=int(maximum==observed)
        loss+=-math.log(probabilities[observed])
        brier+=math.fsum((probabilities[k]-int(k==observed))**2
                         for k in ("1","X","2"))
        for side,goals in (("home",g_h),("away",g_a)):
            expected=p["expected_goals"][side]
            if type(expected) not in (int,float) or not math.isfinite(expected) or expected<=0:
                _reject("GOAL_EXPECTATION_INVALID")
            goal_mae+=abs(expected-goals)
            goal_nll+=expected-goals*math.log(expected)+math.lgamma(goals+1)
        conf=probabilities[maximum]
        bucket=bins[min(4,int(conf*5))]
        bucket["n"]+=1
        bucket["conf_total"]+=conf
        bucket["hits"]+=int(maximum==observed)
    ece=sum(abs(b["hits"]-b["conf_total"])/n for b in bins)
    outcome={
        "schema":OUTPUT_SCHEMA,
        "snapshot_file":SOURCE_FILE,
        "frozen_forecast_sha256":SOURCE_HASH,
        "first_snapshot_frozen_at_utc":snapshot["forecast_frozen_at_utc"],
        "outcomes_observed_at_utc":scoring_observed_at_utc,
        "prospective_evaluation_target_count":10,
        "used_locked_original_predictions":True,
        "result_labels_for_this_prespecified_shadow_sample_read":10,
        "other_370_test_labels_read_by_this_protocol":0,
        "only_native_pitchapi_match_ids":True,
        "top1_1x2_accuracy":correct/n,
        "top1_1x2_correct_count":correct,
        "multiclass_1x2_logloss":loss/n,
        "multiclass_1x2_brier_sum3":brier/n,
        "top_class_1x2_ece_5bins_exploratory":ece,
        "goal_poisson_nll_per_match_two_teams":goal_nll/n,
        "goal_mae_per_team":goal_mae/(2*n),
        "source_receipt_count":len(final_receipts),
        "source_capture_digests_sha256":sha(sorted(x["capture_sha256"] for x in final_receipts)),
        "original_provider_publication_asof_kickoff_proven":False,
        "actual_provider_receipt_chain_separately_verified":False,
        "tiny_ten_game_sample_no_reliable_calibration_or_significance":True,
        "no_result_or_per_game_predictions_in_output":True,
        "not_for_parameter_selection_or_retraining":True,
        "no_betting_claim":True,
        "training_allowed":False,
        "gate13_pass":False,
        "step14_started":False,
        "retrospective_historical_pit_certified":False,
    }
    outcome["report_sha256"]=sha(outcome)
    return outcome
