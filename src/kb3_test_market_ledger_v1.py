"""KB3 TEST: strictly prospective, append-only, independent *market* snapshots.

Inputs: an ORIGINAL M0-720 SQLite forecast with existing GitHub-host proof.
Each new market freeze gets its OWN later GitHub Actions artifact/host time proof.
This never modifies the original M0 forecasts, models, FIT or provider sources.
"""
from __future__ import annotations

from datetime import timedelta
import math

from src.kb3_test_readonly_markets import (
    TestMarketGateError, from_frozen_parent, digest, utc,
)

SCHEMA = "kb3-test-independent-market-freeze-v1"
SETTLE_SCHEMA = "kb3-test-independent-market-settlement-v1"
MARKET_MIN_LEAD = timedelta(minutes=100)  # reserve 10min for GitHub upload/attestation
EARLY_DEADLINE = timedelta(minutes=90)


class MarketLedgerError(TestMarketGateError):
    pass


def need(condition, reason):
    if not condition:
        raise MarketLedgerError(reason)


def _market(family, selection, probability, *, line=None, side=None, push=0.0):
    need(type(probability) in (float, int) and math.isfinite(probability)
         and 0 <= probability <= 1, "INVALID_MARKET_PROBABILITY")
    need(type(push) in (int, float) and math.isfinite(push)
         and 0 <= push <= 1 and probability + push <= 1+1e-10,
         "INVALID_MARKET_PUSH_MASS")
    row = {"family": family, "selection": selection, "line": line,
           "side": side, "p_win": float(probability), "p_push": float(push),
           "period": "REGULAR_90_MINUTES"}
    return {**row, "row_sha256": digest(row)}


def _markets(derived):
    p = derived["p_1x2"]
    rows = [_market("FT_1X2", k, p[k]) for k in ("1", "X", "2")]
    rows += [_market("FT_DOUBLE_CHANCE", k, derived["p_double_chance"][k])
             for k in ("1X", "X2", "12")]
    for line in ("1.5", "2.5", "3.5"):
        rows.append(_market("FT_TOTAL_GOALS_OU", "OVER", derived["p_over"][line], line=line))
        rows.append(_market("FT_TOTAL_GOALS_OU", "UNDER", derived["p_under"][line], line=line))
    rows += [_market("FT_BTTS", k.upper(), derived["p_btts"][k])
             for k in ("yes", "no")]
    for side in ("home", "away"):
        for line, key in (("0.5", "1+"), ("1.5", "2+"), ("2.5", "3+")):
            p_over = derived["team_goals"][side]["at_least"][key]
            rows.append(_market("FT_TEAM_GOALS_OU", "OVER", p_over, line=line, side=side))
            rows.append(_market("FT_TEAM_GOALS_OU", "UNDER", 1-p_over, line=line, side=side))
    # Exact 2.0 integer line has push mass P(T=2), not a binary Over/Under bet.
    push = derived["p_over"]["1.5"] - derived["p_over"]["2.5"]
    need(push >= -1e-10, "NON_MONOTONE_POISSON_INTEGER_PUSH")
    push = max(0.0, push)
    rows.append(_market("FT_TOTAL_GOALS_INTEGER_OU", "OVER",
                        derived["p_over"]["2.5"], line="2.0", push=push))
    rows.append(_market("FT_TOTAL_GOALS_INTEGER_OU", "UNDER",
                        derived["p_under"]["1.5"], line="2.0", push=push))
    keys = [(x["family"], x["side"], x["line"], x["selection"]) for x in rows]
    need(len(rows) == 28 and len(set(keys)) == 28, "MARKET_LIST_DUPLICATE_OR_INCOMPLETE")
    return rows


def make_market_freeze(parent, *, original_id, parent_host_utc,
                       parent_host_source, captured_at_utc):
    """True NEW market freeze created NOW, not backdated to its M0 parent time."""
    derived = from_frozen_parent(
        parent, original_id=original_id, host_event_utc=parent_host_utc,
        host_source=parent_host_source)
    captured, kickoff, first_host = (
        utc(captured_at_utc), utc(parent["kickoff_utc"]), utc(parent_host_utc))
    need(first_host <= captured, "MARKET_CAPTURE_BEFORE_ORIGINAL_M0_HOST")
    need(captured <= kickoff - MARKET_MIN_LEAD, "MARKET_CAPTURE_TOO_LATE_FOR_HOST_BUFFER")
    base = {
        "schema": SCHEMA,
        "kind": "GENUINE_NEW_PREGAME_DERIVED_M0_RESEARCH_MARKET_FREEZE",
        "original_m0_forecast_sha256": original_id,
        "league": derived["league"],
        "native_match_id": derived["native_match_id"],
        "kickoff_utc": derived["kickoff_utc"],
        "market_captured_at_utc": captured_at_utc,
        "original_m0_first_host_attested_utc": parent_host_utc,
        "original_m0_host_proof_source": parent_host_source,
        "original_m0_feature_sha256": derived["source_feature_sha256"],
        "original_m0_params_sha256": derived["original_params_sha256"],
        "market_rows": _markets(derived),
        "market_row_count": 28,
        "market_host_attestation_pending_until_GitHub_artifact_checked": True,
        "source_provider_first_published_at_historically_certified": False,
        "new_m0_forecast_created": False,
        "new_market_snapshot_created": True,
        "official_fit_increment": 0,
        "production_approved": False,
        "research_only": True,
        "price_or_ev_included": False,
    }
    return {**base, "freeze_sha256": digest(base)}


def verify_market_freeze(snapshot, *, parent, parent_id, host_utc, host_source):
    """Reconstruct byte-identical snapshot from original stored M0 evidence."""
    need(isinstance(snapshot, dict) and snapshot.get("schema") == SCHEMA,
         "INVALID_MARKET_FREEZE_SCHEMA")
    old = {k: v for k, v in snapshot.items() if k != "freeze_sha256"}
    need(digest(old) == snapshot.get("freeze_sha256"),
         "MUTATED_MARKET_FREEZE")
    regenerated = make_market_freeze(
        parent, original_id=parent_id, parent_host_utc=host_utc,
        parent_host_source=host_source,
        captured_at_utc=snapshot["market_captured_at_utc"])
    need(regenerated == snapshot, "MARKET_FREEZE_NOT_DERIVED_FROM_ORIGINAL_M0")
    return True


def market_label(row, gh, ga, *, confirmed_void=False):
    """Return WIN/LOSS/PUSH/VOID; VOID must be independently confirmed upstream."""
    need(isinstance(row, dict) and "row_sha256" in row, "MARKET_ROW_REQUIRED")
    orig = {k: v for k, v in row.items() if k != "row_sha256"}
    need(digest(orig) == row["row_sha256"], "MARKET_ROW_TAMPERED")
    if confirmed_void:
        return "VOID"
    need(type(gh) is int and type(ga) is int and 0 <= gh <= 30 and 0 <= ga <= 30,
         "FINAL_90MIN_SCORE_REQUIRED")
    fam, choice, line, side = (
        row["family"], row["selection"], row["line"], row["side"])
    one = "1" if gh > ga else "2" if gh < ga else "X"
    if fam == "FT_1X2":
        won = choice == one
    elif fam == "FT_DOUBLE_CHANCE":
        won = one in choice
    elif fam == "FT_BTTS":
        yes = gh > 0 and ga > 0
        won = yes if choice == "YES" else not yes
    elif fam in ("FT_TOTAL_GOALS_OU", "FT_TOTAL_GOALS_INTEGER_OU",
                 "FT_TEAM_GOALS_OU"):
        total = gh+ga if fam != "FT_TEAM_GOALS_OU" else (
            gh if side == "home" else ga)
        need(isinstance(line, str), "NUMERIC_LINE_REQUIRED")
        threshold = float(line)
        if total == threshold:
            need(fam == "FT_TOTAL_GOALS_INTEGER_OU" and threshold == 2.0,
                 "UNDECLARED_PUSH_LINE")
            return "PUSH"
        won = total > threshold if choice == "OVER" else total < threshold
    else:
        raise MarketLedgerError("UNKNOWN_MARKET_FAMILY")
    return "WIN" if won else "LOSS"


def score_market_row(row, outcome):
    """Binary log-loss/Brier, conditioning on no PUSH for integer goal line."""
    need(outcome in ("WIN", "LOSS", "PUSH", "VOID"), "BAD_MARKET_OUTCOME")
    if outcome in ("PUSH", "VOID"):
        return {"settlement": outcome, "binary_brier": None, "binary_log_loss": None,
                "p_win_conditional_no_push": None}
    no_push = 1.0-row["p_push"]
    need(no_push > 0, "ZERO_NONPUSH_PROBABILITY")
    p = row["p_win"]/no_push
    need(-1e-10 <= p <= 1+1e-10, "BAD_CONDITIONAL_PROBABILITY")
    p = min(1-1e-12, max(1e-12, p))
    observed = 1 if outcome == "WIN" else 0
    return {"settlement": outcome,
            "binary_brier": (p-observed)**2,
            "binary_log_loss": -(math.log(p) if observed else math.log1p(-p)),
            "p_win_conditional_no_push": p}


def settle_market_freeze(snapshot, settlement, *,
                         original_parent, parent_host_utc, parent_host_source):
    """Only real matured original M0 settlement can authorize a market result."""
    need(isinstance(settlement, dict), "REAL_M0_SETTLEMENT_REQUIRED")
    pid = snapshot.get("original_m0_forecast_sha256")
    verify_market_freeze(snapshot, parent=original_parent, parent_id=pid,
                         host_utc=parent_host_utc, host_source=parent_host_source)
    need(settlement.get("forecast_id") == pid and
         settlement.get("league") == snapshot["league"] and
         settlement.get("native_match_id") == snapshot["native_match_id"],
         "RESULT_FIXTURE_OR_PARENT_MISMATCH")
    ko = utc(snapshot["kickoff_utc"])
    observed, settled = utc(settlement.get("observed_utc")), utc(settlement.get("settled_utc"))
    need(observed >= ko + timedelta(hours=3) and
         settled >= ko + timedelta(hours=3), "RESULT_NOT_THREE_HOURS_MATURE")
    gh, ga = settlement.get("score_home"), settlement.get("score_away")
    need(type(gh) is int and type(ga) is int and 0 <= gh <= 30 and 0 <= ga <= 30,
         "RESULT_SCORE_INVALID")
    one = "1" if gh > ga else "2" if gh < ga else "X"
    need(one == settlement.get("outcome"), "RESULT_1X2_MISMATCH")
    need(isinstance(settlement.get("provider_source_chain_sha256"), str)
         and len(settlement["provider_source_chain_sha256"]) == 64,
         "PROVIDER_RESULT_SOURCE_SHA_MISSING")
    # Exactly the immutable source record calculated by existing M0 settlement.
    orig = {
        "forecast_id": pid,
        "league": snapshot["league"],
        "native_match_id": snapshot["native_match_id"],
        "score_home": gh, "score_away": ga,
        "outcome": one,
        "observed_utc": settlement["observed_utc"],
        "source_chain_sha256": settlement["provider_source_chain_sha256"],
        "log_loss": settlement.get("log_loss"),
        "brier_sum3": settlement.get("brier_sum3"),
    }
    need(digest(orig) == settlement.get("settlement_sha256"),
         "ORIGINAL_M0_SETTLEMENT_HASH_MISMATCH")
    results = []
    for row in snapshot["market_rows"]:
        outcome = market_label(row, gh, ga)
        results.append({
            "market_row_sha256": row["row_sha256"],
            "family": row["family"], "line": row["line"],
            "side": row["side"], "selection": row["selection"],
            **score_market_row(row, outcome),
        })
    base = {
        "schema": SETTLE_SCHEMA,
        "origin_market_freeze_sha256": snapshot["freeze_sha256"],
        "original_m0_forecast_sha256": pid,
        "original_m0_settlement_sha256": settlement["settlement_sha256"],
        "original_result_observed_at_utc": settlement["observed_utc"],
        "original_result_source_chain_sha256": settlement["provider_source_chain_sha256"],
        "result_home_90min": gh, "result_away_90min": ga,
        "market_rows": results,
        "market_count": len(results),
        "real_fully_finished_result_only": True,
        "void_without_independently_confirmed_source_never_assumed": True,
        "official_fit_increment": 0,
        "production_approved": False,
        "roi_without_real_odds": None,
    }
    return {**base, "market_settlement_sha256": digest(base)}
