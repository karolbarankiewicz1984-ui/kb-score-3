"""KB Score 3.0, step13: transparent ELO + independent-Poisson M0 math.

Offline and deterministic. No odds, provider API, target labels, historical
training or empirical calibration. Defaults are ILLUSTRATIVE, NOT FITTED.
Elo is the pre-match team-strength differential; it shifts log expected goals.
Home-field goal advantage is already embedded in the illustrative base rates,
so the ELO home advantage is used ONLY for ELO updates, not again in lambdas.

Never interpret this module's mathematics as PIT eligibility or as a validated
betting model. Historical scoring remains blocked by the distinct data gate.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math


class BaselineSafetyError(ValueError):
    """Reject any unsafe or nonphysical numerical/model inputs."""


def _number(x, *, name, low=None, high=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise BaselineSafetyError("STEP13_INVALID_" + name)
    n = float(x)
    if (low is not None and n < low) or (high is not None and n > high):
        raise BaselineSafetyError("STEP13_OUT_OF_RANGE_" + name)
    return n


@dataclass(frozen=True)
class BaselineParameters:
    # ELO prior and K mirror the untrained step11 feature defaults.
    initial_elo: float = 1500.0
    elo_k: float = 20.0
    elo_scale: float = 400.0
    elo_home_advantage: float = 65.0
    # NOT fitted to KB3 TRAIN. Demonstration-only mean home/away goals.
    base_home_goals: float = 1.45
    base_away_goals: float = 1.15
    elo_goal_elasticity: float = 0.35
    poisson_max_goals: int = 64
    poisson_tail_tolerance: float = 1e-12

    def __post_init__(self):
        _number(self.initial_elo, name="INITIAL_ELO", low=100, high=4000)
        _number(self.elo_k, name="ELO_K", low=0.001, high=100)
        _number(self.elo_scale, name="ELO_SCALE", low=1, high=2000)
        _number(self.elo_home_advantage, name="ELO_HOME_ADV", low=-400, high=400)
        _number(self.base_home_goals, name="HOME_GOALS", low=0.01, high=5)
        _number(self.base_away_goals, name="AWAY_GOALS", low=0.01, high=5)
        _number(self.elo_goal_elasticity, name="GOAL_ELASTICITY", low=0, high=1)
        if type(self.poisson_max_goals) is not int or not 16 <= self.poisson_max_goals <= 128:
            raise BaselineSafetyError("STEP13_INVALID_POISSON_LIMIT")
        _number(self.poisson_tail_tolerance, name="TAIL", low=1e-15, high=1e-5)


def elo_expected_home_points(home_rating, away_rating, params=None):
    """Standard Elo expected *points* [0,1]; NOT a calibrated win probability."""
    p = params if params is not None else BaselineParameters()
    if not isinstance(p, BaselineParameters):
        raise BaselineSafetyError("STEP13_INVALID_PARAMETERS")
    home = _number(home_rating, name="ELO_HOME", low=100, high=4000)
    away = _number(away_rating, name="ELO_AWAY", low=100, high=4000)
    exponent = (away - home - p.elo_home_advantage) / p.elo_scale
    return 1 / (1 + 10 ** exponent)


def update_elo(home_rating, away_rating, result, params=None):
    """Pure ELO update AFTER a legally/temporally admitted completed result.

    Caller must check event time and actual observation time. This function
    cannot certify retrospective snapshots and does not load them.
    result is 'H', 'D', or 'A', never postulated or inferred from odds.
    """
    p = params if params is not None else BaselineParameters()
    if result not in ("H", "D", "A"):
        raise BaselineSafetyError("STEP13_INVALID_RESULT")
    home = _number(home_rating, name="ELO_HOME", low=100, high=4000)
    away = _number(away_rating, name="ELO_AWAY", low=100, high=4000)
    expected = elo_expected_home_points(home, away, p)
    actual = {"H": 1.0, "D": 0.5, "A": 0.0}[result]
    correction = p.elo_k * (actual - expected)
    return (home + correction, away - correction)


def _poisson_probs(lam, p):
    lam = _number(lam, name="POISSON_LAMBDA", low=0.000001, high=8.0)
    probs = [math.exp(-lam)]
    accum = probs[0]
    for n in range(1, p.poisson_max_goals + 1):
        probs.append(probs[-1] * lam / n)
        accum += probs[-1]
        if 1.0 - accum <= p.poisson_tail_tolerance:
            break
    if 1.0 - accum > p.poisson_tail_tolerance * 2:
        raise BaselineSafetyError("STEP13_POISSON_TAIL_UNRESOLVED")
    return probs


def forecast(home_rating, away_rating, params=None):
    """One match probabilities from independent 90min Poisson goal counts.

    Outputs 1X2, scorelines, over 1.5/2.5/3.5 and BTTS. All markets share
    exactly the same joint probability distribution; no market odds read.
    """
    p = params if params is not None else BaselineParameters()
    if not isinstance(p, BaselineParameters):
        raise BaselineSafetyError("STEP13_INVALID_PARAMETERS")
    home = _number(home_rating, name="ELO_HOME", low=100, high=4000)
    away = _number(away_rating, name="ELO_AWAY", low=100, high=4000)
    # Avoid double-counting home advantage: rates already include it.
    strength = (home - away) / p.elo_scale
    lam_h = p.base_home_goals * math.exp(p.elo_goal_elasticity * strength)
    lam_a = p.base_away_goals * math.exp(-p.elo_goal_elasticity * strength)
    ph = _poisson_probs(lam_h, p)
    pa = _poisson_probs(lam_a, p)
    mass = math.fsum(ph) * math.fsum(pa)
    if mass <= 0:
        raise BaselineSafetyError("STEP13_INVALID_POISSON_MASS")
    win_h = draw = win_a = 0.0
    over = {1: 0.0, 2: 0.0, 3: 0.0}
    btts = 0.0
    candidates = []
    for h, hp in enumerate(ph):
        for a, ap in enumerate(pa):
            prob = hp * ap / mass
            if h > a:
                win_h += prob
            elif h < a:
                win_a += prob
            else:
                draw += prob
            for threshold in over:
                if h + a > threshold:
                    over[threshold] += prob
            if h and a:
                btts += prob
            candidates.append((prob, h, a))
    total = math.fsum((win_h, draw, win_a))
    one = win_h / total
    x = draw / total
    two = max(0.0, 1.0 - one - x)
    # Smallest possible numerical correction is confined to last 1X2 class.
    if abs(one + x + two - 1.0) > 1e-12:
        raise BaselineSafetyError("STEP13_PROBABILITIES_DO_NOT_SUM_TO_ONE")
    best = sorted(candidates, key=lambda t: (-t[0], t[1], t[2]))[:5]
    return {
        "model": "KB3_ELO_POISSON_M0_V0_1",
        "parameters_status": "ILLUSTRATIVE_UNFITTED_NOT_FOR_BETTING",
        "match_duration": "REGULAR_90_MINUTES",
        "elo_home": home,
        "elo_away": away,
        "elo_expected_home_points": elo_expected_home_points(home, away, p),
        "expected_goals": {"home": lam_h, "away": lam_a},
        "p_1x2": {"1": one, "X": x, "2": two},
        "p_over": {"1.5": over[1], "2.5": over[2], "3.5": over[3]},
        "p_btts_yes": btts,
        "top_5_scorelines": [
            {"home": h, "away": a, "probability": chance}
            for chance, h, a in best
        ],
        "poisson_joint_retained_mass": mass,
        "input_parameters": asdict(p),
        "training_allowed": False,
        "historical_test_passed": False,
    }
