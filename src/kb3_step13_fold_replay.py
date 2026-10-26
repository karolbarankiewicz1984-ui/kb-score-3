"""Step13 v0.2: leakage-safe, explicitly SYNTHETIC fold replay harness.

This harness uses fixed fold-start ELO trained from artificial results only.
It NEVER treats retrospective PitchAPI records as historically observed PIT,
cannot ingest real/unknown labels, cannot see TEST, and cannot confer training
eligibility. The real 1520-fixture schedule is reviewed separately WITHOUT labels.

Outcomes are in a separate ledger and read ONLY after pre-fold ELO forecasts.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import json
from pathlib import Path

from src.kb3_split import SplitSafetyError, sha, timestamp, freeze_manifest
from src.kb3_step12_acceptance import accept_methodology
from src.kb3_step13_baseline import (
    BaselineSafetyError, BaselineParameters, update_elo, forecast,
)
from src.kb3_step13_reference_metrics import score_synthetic_reference

VALID_STRATEGIES = ("EXPANDING", "ROLLING_24_CALENDAR_MONTHS")
RESULT_LAG = timedelta(hours=48)
FIXTURE_KEYS = frozenset((
    "fixture_id", "kickoff_utc", "home_team_id", "away_team_id", "partition",
    "origin",
))
RESULT_KEYS = frozenset((
    "fixture_id", "home_goals_90", "away_goals_90",
    "actual_receipt_at_utc", "origin",
))


def _ids_only(identifier):
    return type(identifier) is str and identifier.strip() and len(identifier) <= 128


def _synthetic_data(fixtures, result_receipts, *, start, stop):
    if not isinstance(fixtures, list) or not isinstance(result_receipts, list):
        raise BaselineSafetyError("STEP13_REPLAY_LISTS_REQUIRED")
    if not fixtures:
        raise BaselineSafetyError("STEP13_REPLAY_FIXTURES_EMPTY")
    records, outcomes = {}, {}
    for rec in fixtures:
        if not isinstance(rec, dict) or set(rec) != FIXTURE_KEYS:
            raise BaselineSafetyError("STEP13_REPLAY_FIXTURE_SCHEMA")
        ident = rec["fixture_id"]
        if not _ids_only(ident) or ident in records:
            raise BaselineSafetyError("STEP13_REPLAY_DUPLICATE_OR_INVALID_FIXTURE")
        if (rec["origin"] != "SYNTHETIC_TEST" or
            rec["partition"] not in ("TRAIN", "VALIDATION") or
            not _ids_only(rec["home_team_id"]) or
            not _ids_only(rec["away_team_id"]) or
            rec["home_team_id"] == rec["away_team_id"]):
            raise BaselineSafetyError("STEP13_REPLAY_UNTRUSTED_OR_TEST_FIXTURE")
        ko = timestamp(rec["kickoff_utc"])
        if start <= ko < stop and rec["partition"] != "VALIDATION":
            raise BaselineSafetyError("STEP13_REPLAY_TARGET_NOT_VALIDATION")
        if ko < start and rec["partition"] == "VALIDATION":
            # Earlier validation fold outcomes MAY enter later TRAIN, but must
            # be explicitly re-labelled as TRAIN in the synthetic fold view.
            raise BaselineSafetyError("STEP13_REPLAY_OLD_VALIDATION_MISLABELED")
        if ko >= stop:
            raise BaselineSafetyError("STEP13_REPLAY_FUTURE_FIXTURE")
        records[ident] = {**rec, "_kickoff": ko}
    for res in result_receipts:
        if not isinstance(res, dict) or set(res) != RESULT_KEYS:
            raise BaselineSafetyError("STEP13_REPLAY_RESULT_SCHEMA")
        ident = res["fixture_id"]
        if not _ids_only(ident) or ident not in records or ident in outcomes:
            raise BaselineSafetyError("STEP13_REPLAY_UNKNOWN_OR_DUPLICATE_RESULT")
        if res["origin"] != "SYNTHETIC_TEST":
            raise BaselineSafetyError("STEP13_REPLAY_RESULT_PROVENANCE_NOT_SYNTHETIC")
        gh, ga = res["home_goals_90"], res["away_goals_90"]
        if type(gh) is not int or type(ga) is not int or not (0 <= gh <= 30 and 0 <= ga <= 30):
            raise BaselineSafetyError("STEP13_REPLAY_INVALID_SCORE_90")
        observed = timestamp(res["actual_receipt_at_utc"])
        if observed < records[ident]["_kickoff"] + timedelta(hours=3):
            raise BaselineSafetyError("STEP13_REPLAY_RESULT_RECEIPT_BEFORE_COMPLETION")
        outcomes[ident] = {**res, "_received_at": observed}
    return records, outcomes


def replay_synthetic_fold(
    fixtures, result_receipts, *, validation_from_utc, validation_to_utc,
    history_from_utc, strategy, params=None,
):
    """Freeze model at fold start; predict synthetic validation without refitting.

    For a historical research replay, observable timestamps require distinct
    policies. This function prohibits external data even with synthetic field
    renaming as best-effort guard; it is NOT a security boundary against forged
    malicious input. Its outputs NEVER count as historical validation.
    """
    if strategy not in VALID_STRATEGIES:
        raise BaselineSafetyError("STEP13_REPLAY_UNKNOWN_STRATEGY")
    p = params if params is not None else BaselineParameters()
    if not isinstance(p, BaselineParameters):
        raise BaselineSafetyError("STEP13_REPLAY_INVALID_PARAMETERS")
    start, stop, lower = (timestamp(x) for x in (
        validation_from_utc, validation_to_utc, history_from_utc))
    if not lower < start < stop:
        raise BaselineSafetyError("STEP13_REPLAY_INVALID_BOUNDARIES")
    if strategy == "ROLLING_24_CALENDAR_MONTHS" and lower != start.replace(year=start.year-2):
        raise BaselineSafetyError("STEP13_REPLAY_NOT_24_CALENDAR_MONTHS")
    fixtures_by_id, results = _synthetic_data(
        fixtures, result_receipts, start=start, stop=stop)
    past = sorted((
        x for x in fixtures_by_id.values()
        if lower <= x["_kickoff"] < start and x["partition"] == "TRAIN"
    ), key=lambda x:(x["_kickoff"],x["fixture_id"]))
    targets = sorted((
        x for x in fixtures_by_id.values()
        if start <= x["_kickoff"] < stop and x["partition"] == "VALIDATION"
    ), key=lambda x:(x["_kickoff"],x["fixture_id"]))
    if not targets:
        raise BaselineSafetyError("STEP13_REPLAY_NO_VALIDATION_FIXTURES")
    ratings={}
    accepted=[]
    excluded=Counter()
    for item in past:
        receipt=results.get(item["fixture_id"])
        if receipt is None:
            excluded["no_result"] += 1
            continue
        if item["_kickoff"]+RESULT_LAG >= start:
            excluded["event_time_48h_embargo"] += 1
            continue
        # Since only synthetic fixtures are accepted, receipts can precede
        # fold start. Real receipts require provider-verified capture and a
        # distinct immutable eligibility gate (NOT this function).
        if receipt["_received_at"] >= start:
            excluded["result_received_after_fold_freeze"] += 1
            continue
        home,away=item["home_team_id"],item["away_team_id"]
        pre_h=ratings.get(home,p.initial_elo)
        pre_a=ratings.get(away,p.initial_elo)
        gh,ga=receipt["home_goals_90"],receipt["away_goals_90"]
        label="H" if gh>ga else "A" if gh<ga else "D"
        new_h,new_a=update_elo(pre_h,pre_a,label,p)
        ratings[home],ratings[away]=new_h,new_a
        accepted.append(item["fixture_id"])
    forecasts=[]
    metric_rows=[]
    for fixture in targets:
        h,a=fixture["home_team_id"],fixture["away_team_id"]
        pred=forecast(ratings.get(h,p.initial_elo),ratings.get(a,p.initial_elo),p)
        if pred["training_allowed"]:
            raise BaselineSafetyError("STEP13_REPLAY_UNAUTHORIZED_TRAINING_FLAG")
        forecasts.append({
            "fixture_id":fixture["fixture_id"],
            "predicted_at_utc":validation_from_utc,
            "p_1x2":pred["p_1x2"],
            "expected_goals":pred["expected_goals"],
            "origin":"SYNTHETIC_TEST",
        })
    # Evaluation is strictly AFTER every forecast is frozen. Never read
    # validation outcomes when constructing ratings or predictions.
    for pred in forecasts:
        target=fixtures_by_id[pred["fixture_id"]]
        res=results.get(pred["fixture_id"])
        if res is None:
            continue
        gh,ga=res["home_goals_90"],res["away_goals_90"]
        label="H" if gh>ga else "A" if gh<ga else "D"
        metric_rows.append({"label":label,"probabilities":pred["p_1x2"]})
    complete=len(metric_rows)==len(targets)
    metrics=(score_synthetic_reference(metric_rows,mode="SYNTHETIC_REFERENCE_ONLY")
             if complete else None)
    return {
        "mode":"SYNTHETIC_REFERENCE_ONLY",
        "strategy":strategy,
        "validation_from_utc":validation_from_utc,
        "validation_to_utc":validation_to_utc,
        "history_from_utc":history_from_utc,
        "history_schedule_candidates":len(past),
        "eligible_synthetic_history":len(accepted),
        "excluded_history_reasons":dict(sorted(excluded.items())),
        "eligible_synthetic_history_ids":accepted,
        "validation_schedule_count":len(targets),
        "synthetic_validation_results_count":len(metric_rows),
        "validation_coverage_complete":complete,
        "frozen_forecasts":forecasts,
        "reference_metrics_if_complete":metrics,
        "historical_metrics_available":False,
        "historical_pit_certified":False,
        "training_allowed":False,
        "gate13_pass":False,
    }


def real_schedule_probe(safe_view, dual_plan):
    """Real 1520-match fixture-only checks with NO labels/receipt data."""
    approval=accept_methodology(safe_view,dual_plan)
    if not approval["step12_gate_pass"] or approval["training_allowed"]:
        raise SplitSafetyError("STEP13_REAL_SOURCE_NOT_APPROVED_METHOD")
    return {
        "schema":"kb3-step13-replay-readiness-v0.2",
        "method_source_sha256":approval["safe_schedule_source_sha256"],
        "dual_window_sha256":approval["frozen_dual_window_plan_sha256"],
        "real_fixture_count":sum(approval["partition_counts"].values()),
        "fold_counts":[{
            "fold":x["fold"],
            "expanding_history_candidates":x["expanding_schedule_candidates"],
            "rolling_24month_candidates":x["rolling_two_year_schedule_candidates"],
            "validation_candidates":x["shared_validation_fixtures"],
            "certified_train_samples":0,
            "certified_validation_samples":0,
        } for x in approval["folds"]],
        "historical_labels_read":False,
        "historical_predictions_made":False,
        "real_training_performed":False,
        "real_backtest_performed":False,
        "real_metrics_available":False,
        "asof_training_eligibility":"BLOCKED_0_OF_1520",
        "model_selection_allowed":False,
        "training_allowed":False,
        "gate13_pass":False,
        "next_requirements":[
            "Genuine result and team-ID receipts for the selected provider.",
            "Independent per-fixture pre-target availability and provenance review.",
            "Choose and document OBSERVED_PIT vs RECONSTRUCTED_EVENT_TIME_RESEARCH policy.",
            "TRAIN fitting and matched VALIDATION scoring only after documented data approval.",
            "Never select parameters using TEST."
        ],
    }


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--safe-view",required=True)
    parser.add_argument("--dual-plan",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    view=json.loads(Path(a.safe_view).read_text(encoding="utf8"))
    plan=json.loads(Path(a.dual_plan).read_text(encoding="utf8"))
    report=real_schedule_probe(view,plan)
    report["report_sha256"]=sha(report)
    print(freeze_manifest(report,a.out))
    print("STEP13_REAL_1520_SCHEDULE_READY_BUT_ZERO_HISTORICAL_PIT",
          report["report_sha256"])


if __name__=="__main__":
    main()
