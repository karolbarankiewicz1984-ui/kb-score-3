"""KB Score 3.0 / step 15: coherent 90-minute goal markets from M0 Poisson.

Pure deterministic research layer. No odds, labels, provider calls, model fitting
or TEST-season access. No promotion or modification of step13 M0.
"""
from __future__ import annotations

import math
from src.kb3_step13_baseline import (
    BaselineParameters, BaselineSafetyError, _poisson_probs, _number, forecast,
)

LINES = ("1.5", "2.5", "3.5")
TOL = 2e-10


def _prob(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not -TOL <= value <= 1 + TOL:
        raise BaselineSafetyError("STEP15_INVALID_" + name)
    return float(value)


def validate_goal_markets(result):
    """Fail closed when any generated 90-minute market is contradictory."""
    if not isinstance(result, dict) or result.get("match_duration") != "REGULAR_90_MINUTES":
        raise BaselineSafetyError("STEP15_NOT_90_MINUTES")
    for name in ("p_1x2", "p_over", "p_under", "p_btts", "team_goals"):
        if not isinstance(result.get(name), dict):
            raise BaselineSafetyError("STEP15_MISSING_" + name)
    w = result["p_1x2"]
    if set(w) != {"1", "X", "2"}:
        raise BaselineSafetyError("STEP15_BAD_1X2_SCHEMA")
    for label, value in w.items():
        _prob(value, "1X2_" + label)
    if abs(math.fsum(w.values()) - 1) > TOL:
        raise BaselineSafetyError("STEP15_1X2_NOT_NORMALIZED")
    if set(result["p_over"]) != set(LINES) or set(result["p_under"]) != set(LINES):
        raise BaselineSafetyError("STEP15_BAD_OU_SCHEMA")
    for line in LINES:
        over = _prob(result["p_over"][line], "OVER")
        under = _prob(result["p_under"][line], "UNDER")
        if abs(over + under - 1) > TOL:
            raise BaselineSafetyError("STEP15_COMPLEMENT_FAIL")
    if not (result["p_over"]["1.5"] + TOL >= result["p_over"]["2.5"]
            >= result["p_over"]["3.5"] - TOL):
        raise BaselineSafetyError("STEP15_OVER_MONOTONICITY")
    if set(result["p_btts"]) != {"yes", "no"}:
        raise BaselineSafetyError("STEP15_BAD_BTTS_SCHEMA")
    btts_yes = _prob(result["p_btts"]["yes"], "BTTS_YES")
    if abs(btts_yes + _prob(result["p_btts"]["no"], "BTTS_NO") - 1) > TOL:
        raise BaselineSafetyError("STEP15_BTTS_COMPLEMENT")
    if set(result["team_goals"]) != {"home", "away"}:
        raise BaselineSafetyError("STEP15_BAD_TEAM_SCHEMA")
    for side in ("home", "away"):
        t = result["team_goals"][side]
        if not isinstance(t, dict) or set(t) != {"exact", "at_least"}:
            raise BaselineSafetyError("STEP15_BAD_TEAM_SCHEMA")
        if set(t["exact"]) != {"0", "1", "2", "3"} or set(t["at_least"]) != {"1+", "2+", "3+"}:
            raise BaselineSafetyError("STEP15_BAD_TEAM_GOAL_LINES")
        for key, value in t["exact"].items():
            _prob(value, side + "_EXACT_" + key)
        for key, value in t["at_least"].items():
            _prob(value, side + "_AT_LEAST_" + key)
        a = t["at_least"]
        e = t["exact"]
        if not (a["1+"] + TOL >= a["2+"] >= a["3+"] - TOL):
            raise BaselineSafetyError("STEP15_TEAM_MONOTONICITY")
        for key, target in (("1+", 1-e["0"]), ("2+", 1-e["0"]-e["1"]),
                            ("3+", 1-e["0"]-e["1"]-e["2"])):
            if abs(a[key]-target) > TOL:
                raise BaselineSafetyError("STEP15_TEAM_EXACT_INCONSISTENT")
    if (btts_yes > result["p_over"]["1.5"] + TOL
            or btts_yes > result["team_goals"]["home"]["at_least"]["1+"] + TOL
            or btts_yes > result["team_goals"]["away"]["at_least"]["1+"] + TOL):
        raise BaselineSafetyError("STEP15_BTTS_IMPOSSIBLE_RELATION")
    scorelines = result.get("top_5_scorelines")
    if not isinstance(scorelines, list) or len(scorelines) != 5:
        raise BaselineSafetyError("STEP15_BAD_SCORELINES")
    keys, probs = set(), []
    for row in scorelines:
        if (not isinstance(row, dict) or set(row) != {"home", "away", "probability"}
                or any(type(row[k]) is not int or row[k] < 0 for k in ("home", "away"))):
            raise BaselineSafetyError("STEP15_BAD_SCORELINE_ROW")
        key = (row["home"], row["away"])
        if key in keys:
            raise BaselineSafetyError("STEP15_DUPLICATE_SCORELINE")
        keys.add(key)
        probs.append(_prob(row["probability"], "SCORELINE"))
    if probs != sorted(probs, reverse=True):
        raise BaselineSafetyError("STEP15_UNSORTED_SCORELINES")
    return True


def markets_from_lambdas(home_lambda, away_lambda, *, params=None):
    """Each market is derived from the SAME normalized joint 90-min score PMF."""
    p = params if params is not None else BaselineParameters()
    if not isinstance(p, BaselineParameters):
        raise BaselineSafetyError("STEP15_INVALID_PARAMETERS")
    h = _number(home_lambda, name="POISSON_LAMBDA", low=1e-6, high=8.0)
    a = _number(away_lambda, name="POISSON_LAMBDA", low=1e-6, high=8.0)
    hp, ap = _poisson_probs(h, p), _poisson_probs(a, p)
    mh, ma = math.fsum(hp), math.fsum(ap)
    mass = mh * ma
    if abs(mass-1) > 2*p.poisson_tail_tolerance + 1e-12:
        raise BaselineSafetyError("STEP15_UNRESOLVED_TAIL")
    joint = [(i, j, x*y/mass) for i, x in enumerate(hp) for j, y in enumerate(ap)]
    p1x2 = {
        "1": math.fsum(v for i, j, v in joint if i > j),
        "X": math.fsum(v for i, j, v in joint if i == j),
        "2": math.fsum(v for i, j, v in joint if i < j),
    }
    over = {line: math.fsum(v for i, j, v in joint if i+j > int(float(line)))
            for line in LINES}
    btts = math.fsum(v for i, j, v in joint if i >= 1 and j >= 1)
    team_goals = {}
    for side, pmf, side_mass in (("home", hp, mh), ("away", ap, ma)):
        exact = {str(k): (pmf[k] if k < len(pmf) else 0.0)/side_mass
                 for k in range(4)}
        atleast = {f"{k}+": math.fsum(pmf[k:])/side_mass for k in (1,2,3)}
        team_goals[side] = {"exact": exact, "at_least": atleast}
    best = sorted(joint, key=lambda v: (-v[2], v[0], v[1]))[:5]
    result = {
        "schema": "kb3-step15-common-joint-goal-markets-v1",
        "model_family": "M0_INDEPENDENT_POISSON_90MIN",
        "status": "RESEARCH_MATH_NOT_CALIBRATED_NOT_PRODUCTION",
        "match_duration": "REGULAR_90_MINUTES",
        "expected_goals": {"home": h, "away": a},
        "p_1x2": p1x2,
        "p_over": over,
        "p_under": {line: 1.0-value for line, value in over.items()},
        "p_btts": {"yes": btts, "no": 1.0-btts},
        "team_goals": team_goals,
        "top_5_scorelines": [
            {"home": i, "away": j, "probability": value}
            for i, j, value in best
        ],
        "retained_joint_mass_before_normalization": mass,
        "test_season_2026_27_read": False,
        "trained_or_calibrated_here": False,
    }
    validate_goal_markets(result)
    return result


def forecast_goal_markets(home_elo, away_elo, params=None):
    """Reuse unchanged M0 parameters and reject divergence in shared markets."""
    old = forecast(home_elo, away_elo, params)
    p = params if params is not None else BaselineParameters()
    new = markets_from_lambdas(old["expected_goals"]["home"],
                               old["expected_goals"]["away"], params=p)
    for group in ("p_1x2", "p_over"):
        for key, value in old[group].items():
            if abs(value-new[group][key]) > TOL:
                raise BaselineSafetyError("STEP15_STEP13_M0_DIVERGENCE")
    if abs(old["p_btts_yes"]-new["p_btts"]["yes"]) > TOL:
        raise BaselineSafetyError("STEP15_STEP13_BTTS_DIVERGENCE")
    return new
