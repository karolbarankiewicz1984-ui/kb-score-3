"""Offline, read-only control contracts for Step16/17 (no provider, no fit).
Input rows are supplied by an independently authenticated exporter. Passing
host_attested=True is NOT independent GitHub attestation; the exporter must
verify the original historical artifact and server-side publication time.
No forecast, settlement, calibrator or protected TEST is ever written.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import math

CLASSES = ("1", "X", "2")
ENGINES = ("M0_ELO_POISSON_720TRAIN", "ELO_ONLY", "CATBOOST_NO_XG")

class OfflineGateError(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise OfflineGateError(reason)

def utc(value):
    require(isinstance(value, str) and value.endswith("Z"), "UTC_Z_REQUIRED")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OfflineGateError("BAD_UTC") from exc
    require(result.utcoffset() == timedelta(0), "UTC_ZERO_REQUIRED")
    return result.astimezone(timezone.utc)

def score(p, outcome):
    require(isinstance(p, dict) and set(p) == set(CLASSES), "BAD_1X2_CLASSES")
    require(outcome in CLASSES, "BAD_OUTCOME")
    require(all(type(p[k]) in (int, float) and math.isfinite(p[k])
                and 0 <= p[k] <= 1 for k in CLASSES), "BAD_PROBABILITY")
    require(abs(sum(p.values()) - 1.0) <= 1e-9, "BAD_SIMPLEX")
    return (-math.log(max(p[outcome], 1e-15)),
            sum((p[k] - float(k == outcome)) ** 2 for k in CLASSES))

def outcome_from_90min(home, away):
    require(type(home) is int and type(away) is int
            and 0 <= home <= 30 and 0 <= away <= 30, "BAD_90MIN_SCORE")
    return "1" if home > away else "2" if home < away else "X"

def verify_settlements(rows, *, require_attestation=True):
    """Independent recalculation; never accepts arbitrary persisted scores."""
    seen = set()
    checked = []
    for row in rows:
        ident = (row["league"], row["fixture_id"])
        require(ident not in seen, "DUPLICATE_FIXTURE")
        seen.add(ident)
        require(row["model_version"] and row["parameter_sha256"],
                "UNVERSIONED_MODEL")
        if require_attestation:
            require(row["host_attested"] is True, "EXTERNAL_PROOF_NOT_VERIFIED")
        freeze, kickoff, observed = (utc(row[k]) for k in
            ("frozen_at_utc", "kickoff_utc", "result_observed_utc"))
        require(freeze <= kickoff-timedelta(minutes=90), "LATE_FREEZE")
        require(observed >= kickoff+timedelta(hours=3), "RESULT_TOO_EARLY")
        label = outcome_from_90min(row["score_home_90"], row["score_away_90"])
        require(row["outcome_1x2"] == label, "WRONG_1X2_SETTLEMENT")
        ll, bs = score(row["p_1x2"], label)
        require(math.isclose(row["log_loss"], ll, rel_tol=0, abs_tol=1e-10),
                "LOGLOSS_MISMATCH")
        require(math.isclose(row["brier_sum3"], bs, rel_tol=0, abs_tol=1e-10),
                "BRIER_SUM3_MISMATCH")
        checked.append(row)
    return sorted(checked, key=lambda r:
                  (utc(r["kickoff_utc"]), r["league"], r["fixture_id"]))

def calibration_100_50(rows, *, fitted_at_utc, reviewed_at_utc,
                       model_version, parameter_sha256):
    """Cohort selection only; no temperature fitting and no auto-approval."""
    fit, review = utc(fitted_at_utc), utc(reviewed_at_utc)
    require(fit < review, "INVALID_FIT_REVIEW_ORDER")
    verified = verify_settlements(rows)
    require(all(r["model_version"] == model_version and
                r["parameter_sha256"] == parameter_sha256 for r in verified),
            "MIXED_MODEL_OR_PARAMETER_SHA")
    before = [r for r in verified if utc(r["kickoff_utc"]) < fit
              and utc(r["result_observed_utc"]) < fit]
    after = [r for r in verified if utc(r["frozen_at_utc"]) > fit
             and utc(r["kickoff_utc"]) > fit
             and utc(r["result_observed_utc"]) <= review]
    chosen_fit, chosen_holdout = before[:100], after[:50]
    fit_ids = {(r["league"], r["fixture_id"]) for r in chosen_fit}
    hold_ids = {(r["league"], r["fixture_id"]) for r in chosen_holdout}
    require(fit_ids.isdisjoint(hold_ids), "FIT_HOLDOUT_OVERLAP")
    return {
        "before_fit_n": len(before),
        "post_fit_independent_n": len(after),
        "fit_first_100": [r["fixture_id"] for r in chosen_fit],
        "holdout_first_50": [r["fixture_id"] for r in chosen_holdout],
        "ready_to_fit": len(before) >= 100,
        "ready_to_review": len(before) >= 100 and len(after) >= 50,
        "no_holdout_used_to_fit": True,
        "production_approved": False,
    }

def compare_three_by_league(games):
    """Same match, cutoff and feature snapshot. Missing engine => excluded."""
    seen = set()
    totals = Counter()
    missing = defaultdict(Counter)
    matched = defaultdict(list)
    for g in games:
        key = (g["league"], g["fixture_id"])
        require(key not in seen, "DUPLICATE_FIXTURE")
        seen.add(key)
        totals[g["league"]] += 1
        kickoff = utc(g["kickoff_utc"])
        require(utc(g["result_observed_utc"]) >= kickoff+timedelta(hours=3),
                "RESULT_TOO_EARLY")
        require(g["outcome_1x2"] in CLASSES, "BAD_OUTCOME")
        preds = g["predictions"]
        require(set(preds) <= set(ENGINES), "UNKNOWN_ENGINE")
        for e in ENGINES:
            if e not in preds:
                missing[g["league"]][e] += 1
        if not all(e in preds for e in ENGINES):
            continue
        versions, snapshots, cutoffs, parents = [], set(), set(), set()
        for e in ENGINES:
            p = preds[e]
            score(p["p_1x2"], g["outcome_1x2"])
            versions.append((e, p["model_version"]))
            snapshots.add(p["feature_sha256"])
            cutoffs.add(p["frozen_at_utc"])
            parents.add(p["source_m0_forecast_sha256"])
            require(p["host_attested"] is True, "ENGINE_NOT_HOST_ATTESTED")
            require(utc(p["frozen_at_utc"]) <= kickoff-timedelta(minutes=90),
                    "LATE_ENGINE_FREEZE")
        require(all(v for _, v in versions), "UNVERSIONED_ENGINE")
        require(len(snapshots) == len(cutoffs) == len(parents) == 1,
                "DIFFERENT_CUTOFF_OR_SOURCE")
        matched[g["league"]].append(g)
    by_league = {}
    for league in sorted(totals):
        matched_games = matched[league]
        scores = {}
        for engine in ENGINES:
            vectors = [score(g["predictions"][engine]["p_1x2"],
                             g["outcome_1x2"]) for g in matched_games]
            hits = [max(CLASSES, key=lambda c:g["predictions"][engine]
                        ["p_1x2"][c]) == g["outcome_1x2"] for g in matched_games]
            scores[engine] = ({
                "n": len(vectors),
                "brier_sum3": sum(v[1] for v in vectors)/len(vectors),
                "log_loss": sum(v[0] for v in vectors)/len(vectors),
                "top1_accuracy": sum(hits)/len(hits),
            } if vectors else None)
        base = scores["M0_ELO_POISSON_720TRAIN"]
        deltas = {e: ({
            "brier_minus_M0": scores[e]["brier_sum3"]-base["brier_sum3"],
            "logloss_minus_M0": scores[e]["log_loss"]-base["log_loss"],
        } if base and scores[e] else None) for e in ENGINES[1:]}
        weeks = {(utc(g["kickoff_utc"]).isocalendar().year,
                  utc(g["kickoff_utc"]).isocalendar().week) for g in matched_games}
        by_league[league] = {
            "eligible_fixtures": totals[league],
            "matched_three_n": len(matched_games),
            "missing_forecasts": dict(missing[league]),
            "per_engine_same_fixtures": scores,
            "paired_deltas": deltas,
            "independent_iso_weeks": len(weeks),
            "uncertainty_status": ("INSUFFICIENT_WEEKS" if len(weeks)<8
                                   else "READY_FOR_CLUSTER_BOOTSTRAP"),
        }
    return {"per_league": by_league,
            "matched_three_n": sum(len(x) for x in matched.values()),
            "excluded_missing_n": len(games)-sum(len(x) for x in matched.values()),
            "winner_auto_selected": False, "gate17": "PENDING"}

def native_xg_last5(history, observed, *, target_kickoff_utc,
                    cutoff_utc, home_team_id, away_team_id):
    """Select last five ACTUAL matches first, then check native xG evidence."""
    target, cutoff = utc(target_kickoff_utc), utc(cutoff_utc)
    require(cutoff <= target-timedelta(minutes=90), "XG_TARGET_LEAKAGE")
    require(home_team_id != away_team_id, "SAME_TEAM_BOTH_SIDES")
    seen = set()
    prior = []
    for m in history:
        require(m["fixture_id"] not in seen, "XG_DUPLICATE_HISTORY")
        seen.add(m["fixture_id"])
        if (m["status"] == "finished"
                and utc(m["kickoff_utc"])+timedelta(hours=3) <= cutoff
                and utc(m["kickoff_utc"]) < target):
            prior.append(m)
    prior.sort(key=lambda m: (utc(m["kickoff_utc"]), m["fixture_id"]),
               reverse=True)
    features = {}
    for side, team in (("home", home_team_id), ("away", away_team_id)):
        last5 = [m for m in prior if team in
                 (m["home_team_id"], m["away_team_id"])][:5]
        missing = []
        values = []
        for m in last5:
            o = observed.get(m["fixture_id"])
            if not o or o.get("provider") != "PitchAPI" or not o.get("verified"):
                missing.append(m["fixture_id"])
                continue
            if utc(o["observed_at_utc"]) > cutoff:
                missing.append(m["fixture_id"])
                continue
            if (o["home_team_id"], o["away_team_id"]) != (
                    m["home_team_id"], m["away_team_id"]):
                missing.append(m["fixture_id"])
                continue
            xh, xa = o["xg_home"], o["xg_away"]
            require(all(type(z) in (float, int) and math.isfinite(z)
                        and 0 <= z <= 30 for z in (xh, xa)), "BAD_NATIVE_XG")
            values.append((xh, xa) if team == m["home_team_id"] else (xa, xh))
        complete = len(last5) == 5 and len(values) == 5
        features[side] = {
            "actual_last5_ids": [m["fixture_id"] for m in last5],
            "missing_xg_ids": missing,
            "xg_last5_complete": complete,
            "xg_for_last5": sum(v[0] for v in values)/5 if complete else None,
            "xga_last5": sum(v[1] for v in values)/5 if complete else None,
        }
    return {"ready_for_xg_research_feature":
            all(v["xg_last5_complete"] for v in features.values()),
            "features": features, "no_missing_xg_replaced_with_zero": True,
            "native_team_xg_only": True, "auto_train": False}
