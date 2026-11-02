"""KB3 Step19 preparatory EXACT 90-minute 1X2 odds mathematics (OFFLINE).

No provider calls, no bets, no live prices and no selection ranking.
A quote belongs to one fixture, bookmaker, provider and capture timestamp.
Provenance/authentic pre-match capture must be verified upstream before use.
"""
from __future__ import annotations
from datetime import datetime, timezone
from math import isfinite
from src.kb3_step14_m1_math_calibration import order_probability

MARKET="FT_90MIN_1X2"
SELECTIONS=("1","X","2")

class MarketContractError(ValueError):pass

def check(ok,message):
    if not ok: raise MarketContractError(message)

def utc(value):
    check(isinstance(value,str),"TIMESTAMP_REQUIRED")
    try: x=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:raise MarketContractError("INVALID_TIMESTAMP") from exc
    check(x.tzinfo is not None and x.utcoffset().total_seconds()==0,
          "TIMESTAMP_MUST_BE_UTC")
    return x

def evaluate_exact_1x2(*,quotes,probabilities,fixture_id,kickoff_utc,cutoff_utc):
    """Score comparable three-way decimal odds in one frozen provider snapshot.

    Returns EV as arithmetic diagnostic, NOT an advice to place a wager.
    """
    check(isinstance(fixture_id,str) and fixture_id
          and isinstance(quotes,list) and len(quotes)==3,
          "EXACT_THREE_QUOTES_REQUIRED")
    kickoff,cutoff=utc(kickoff_utc),utc(cutoff_utc)
    check(cutoff<kickoff,"INVALID_FORECAST_CUTOFF")
    order_probability(probabilities)
    required={"quote_id","fixture_id","kickoff_utc","captured_at_utc",
              "provider","bookmaker","market","selection","line","decimal_odds"}
    seen=set(); keys=set(); odds={}
    for item in quotes:
        check(type(item) is dict and set(item)==required,
              "QUOTE_SCHEMA_MISMATCH")
        check(item["fixture_id"]==fixture_id and
              utc(item["kickoff_utc"])==kickoff,
              "FIXTURE_OR_KICKOFF_CHANGED")
        captured=utc(item["captured_at_utc"])
        check(captured<=cutoff and captured<kickoff,
              "QUOTE_NOT_OBSERVED_BEFORE_CUTOFF")
        check(item["market"]==MARKET and item["line"] is None,
              "MARKET_OR_LINE_MISMATCH")
        check(item["selection"] in SELECTIONS and
              item["selection"] not in odds,"DUPLICATE_OR_UNKNOWN_SELECTION")
        for name in ("quote_id","provider","bookmaker"):
            check(isinstance(item[name],str) and bool(item[name].strip()),
                  "SOURCE_ID_MISSING")
        check(item["quote_id"] not in seen,"DUPLICATE_QUOTE_ID")
        seen.add(item["quote_id"])
        value=item["decimal_odds"]
        check(type(value) in (int,float) and isfinite(value)
              and 1.0<float(value)<=1000,"INVALID_DECIMAL_ODDS")
        odds[item["selection"]]=float(value)
        keys.add((item["provider"],item["bookmaker"],item["captured_at_utc"]))
    check(set(odds)==set(SELECTIONS) and len(keys)==1,
          "MIXED_PROVIDER_BOOKMAKER_OR_CAPTURE")
    implied={k:1.0/odds[k] for k in SELECTIONS}
    total=sum(implied.values())
    check(isfinite(total) and 0.0<total<2.0,"INVALID_MARKET_OVERROUND")
    provider,bookmaker,observed_at=next(iter(keys))
    return {
        "schema":"kb3-step19-exact-1x2-market-math-v1",
        "fixture_id":fixture_id,"kickoff_utc":kickoff_utc,
        "cutoff_utc":cutoff_utc,"quote_observed_utc":observed_at,
        "provider":provider,"bookmaker":bookmaker,"market":MARKET,
        "overround":total-1.0,
        "selection_math":{k:{
            "decimal_odds":odds[k],
            "raw_implied_probability":implied[k],
            "normalized_no_vig_probability":implied[k]/total,
            "model_probability":float(probabilities[k]),
            "probability_edge_vs_no_vig":float(probabilities[k])-implied[k]/total,
            "arithmetic_ev_per_unit":float(probabilities[k])*odds[k]-1.0
            } for k in SELECTIONS},
        "real_source_time_proof_independently_verified":False,
        "quote_synthetic_or_unverified_must_not_be_published_as_live":True,
        "value_pick_recommended":False,"automatic_bet":False,
        "real_money_execution":False,"formal_gate19_pass":False,
    }
