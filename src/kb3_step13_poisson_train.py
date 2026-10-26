"""Step13 M0: fit Poisson rates/elo elasticity on STRICTLY SYNTHETIC TRAIN.

This is an offline training algorithm prototype, not a real trained model,
not a retroactive PIT certificate, and not evidence of sporting success.

For each fixed Elo-goal-elasticity candidate we use the exact conditional
MLE of home/away base goal rates under independent Poisson scores, then
select by total TRAIN Poisson negative log likelihood, never VALIDATION/TEST.
ELO snapshots are separately supplied by synthetic controls; this module
DOES NOT certify their as-of provenance. Actual data require independent
source proof and a *different* admission mechanism.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import timedelta
import math

from src.kb3_split import timestamp, sha, SplitSafetyError
from src.kb3_step13_baseline import BaselineParameters, BaselineSafetyError, forecast

SCHEMA = "kb3-step13-synthetic-poisson-train-v0.3"
FIXED_GRID = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
REQUIRED = frozenset((
    "fixture_id", "home_team_id", "away_team_id", "kickoff_utc",
    "feature_cutoff_utc", "result_observed_at_utc",
    "home_elo_before_kickoff", "away_elo_before_kickoff",
    "goals_home_90", "goals_away_90",
    "partition", "source_type",
))
MIN_TRAIN_SAMPLES = 8


def _fixture(row, boundary):
    if not isinstance(row, dict) or set(row) != REQUIRED:
        raise BaselineSafetyError("STEP13_FIT_SCHEMA_OR_ODDS_FIELD_REJECTED")
    if row["partition"] != "TRAIN" or row["source_type"] != "SYNTHETIC_REFERENCE_ONLY":
        raise BaselineSafetyError("STEP13_FIT_NON_SYNTHETIC_OR_NON_TRAIN")
    if (not isinstance(row["fixture_id"], str)
            or not row["fixture_id"].startswith("SYN-MATCH-")
            or any(not isinstance(row[k], str) or
                   not row[k].startswith("SYN-TEAM-")
                   for k in ("home_team_id", "away_team_id"))
            or row["home_team_id"] == row["away_team_id"]):
        raise BaselineSafetyError("STEP13_FIT_INVALID_SYNTHETIC_ID")
    ko = timestamp(row["kickoff_utc"])
    cutoff = timestamp(row["feature_cutoff_utc"])
    receipt = timestamp(row["result_observed_at_utc"])
    if not cutoff < ko < boundary:
        raise BaselineSafetyError("STEP13_FIT_FUTURE_OR_POSTMATCH_FEATURES")
    if not ko + timedelta(hours=3) <= receipt < boundary:
        raise BaselineSafetyError("STEP13_FIT_RESULT_RECEIPT_AFTER_FREEZE")
    goals = (row["goals_home_90"], row["goals_away_90"])
    if any(type(n) is not int or not 0 <= n <= 30 for n in goals):
        raise BaselineSafetyError("STEP13_FIT_INVALID_90MIN_GOALS")
    ratings = (row["home_elo_before_kickoff"],row["away_elo_before_kickoff"])
    if any(type(x) not in (int,float) or not math.isfinite(x)
           or not 100 <= x <= 4000 for x in ratings):
        raise BaselineSafetyError("STEP13_FIT_INVALID_ELO")
    return ((float(ratings[0])-float(ratings[1]))/400.0,
            goals[0],goals[1])


def fit_synthetic_poisson_train(rows, *, freeze_utc):
    """No real rows admitted. Fold's TRAIN-only parameters chosen via MLE."""
    if not isinstance(rows,list) or len(rows)<MIN_TRAIN_SAMPLES:
        raise BaselineSafetyError("STEP13_FIT_INSUFFICIENT_SYNTHETIC_TRAIN")
    boundary = timestamp(freeze_utc)
    ids = set()
    data = []
    for row in rows:
        if isinstance(row,dict) and row.get("fixture_id") in ids:
            raise BaselineSafetyError("STEP13_FIT_DUPLICATE_FIXTURE")
        data.append(_fixture(row,boundary))
        ids.add(row["fixture_id"])
    # All train candidate data are accepted before fit begins; no silent skip.
    nh = sum(x[1] for x in data)
    na = sum(x[2] for x in data)
    if nh == 0 or na == 0:
        raise BaselineSafetyError("STEP13_FIT_DEGENERATE_TRAIN_GOAL_TOTAL")
    leaderboard = []
    for elasticity in FIXED_GRID:
        exposures_h = [math.exp(elasticity*d) for d,_,_ in data]
        exposures_a = [math.exp(-elasticity*d) for d,_,_ in data]
        rate_h = nh / math.fsum(exposures_h)
        rate_a = na / math.fsum(exposures_a)
        # We restrict fitted params to reasonable engine bounds, rather than
        # clipping at bounds (clipping would no longer be the MLE).
        if not (0.01<=rate_h<=5 and 0.01<=rate_a<=5):
            continue
        nll = 0.0
        for (d,gh,ga), eh,ea in zip(data,exposures_h,exposures_a):
            lam_h,lam_a=rate_h*eh,rate_a*ea
            if not (0.000001<=lam_h<=8 and 0.000001<=lam_a<=8):
                nll=math.inf
                break
            nll += (lam_h-gh*math.log(lam_h)+math.lgamma(gh+1)
                    +lam_a-ga*math.log(lam_a)+math.lgamma(ga+1))
        if math.isfinite(nll):
            leaderboard.append((nll,elasticity,rate_h,rate_a))
    if not leaderboard:
        raise BaselineSafetyError("STEP13_FIT_NO_VALID_PARAMETER_CANDIDATE")
    # Stable tie-break by elasticity, then home/away rate.
    nll,elasticity,rate_h,rate_a=min(leaderboard)
    trained = replace(BaselineParameters(),base_home_goals=rate_h,
                      base_away_goals=rate_a,
                      elo_goal_elasticity=elasticity)
    candidate={
        "schema":SCHEMA,
        "data_kind":"SYNTHETIC_REFERENCE_ONLY",
        "fit_role":"TRAIN_ONLY",
        "freeze_utc":freeze_utc,
        "synthetic_train_n":len(data),
        "synthetic_input_sha256":sha(rows),
        "parameter_selection":"TRAIN_POISSON_NLL_GRID_EXACT_PROFILE_MLE_V1",
        "fixed_elasticity_grid":list(FIXED_GRID),
        "selected_train_nll_total":nll,
        "synthetic_train_mean_nll":nll/len(data),
        "fitted_parameters":asdict(trained),
        "validation_labels_read":False,
        "test_labels_read":False,
        "real_historical_model_fitted":False,
        "independent_pit_training_approval":False,
        "empirical_historical_performance":False,
        "training_allowed":False,
        "gate13_pass":False,
    }
    candidate["report_sha256"]=sha(candidate)
    return candidate


def forecast_from_synthetic_fit(candidate, home_rating, away_rating):
    """Never upgrade synthetic fitted parameters to real model status."""
    if (not isinstance(candidate,dict) or
            candidate.get("schema")!=SCHEMA or
            candidate.get("data_kind")!="SYNTHETIC_REFERENCE_ONLY" or
            candidate.get("training_allowed") is not False or
            candidate.get("report_sha256") != sha({
                k:v for k,v in candidate.items() if k!="report_sha256"})):
        raise BaselineSafetyError("STEP13_FIT_UNVERIFIED_SYNTHETIC_CANDIDATE")
    p=BaselineParameters(**candidate["fitted_parameters"])
    pred=forecast(home_rating,away_rating,p)
    pred["parameters_status"]="SYNTHETIC_FITTED_REFERENCE_ONLY_NOT_FOR_BETTING"
    pred["synthetic_fit_report_sha256"]=candidate["report_sha256"]
    pred["training_allowed"]=False
    return pred
