"""KB3 TEST-only derived market preview of ORIGINAL, host-proofed frozen M0.

Read-only consumer. Not a new forecast, not a market freeze, not FIT,
not real odds or wagering advice. Uses the existing Step15 joint Poisson
distribution, never a separately fitted or revised model.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from src.kb3_pit_ledger import canonical
from src.kb3_step15_goal_markets import markets_from_lambdas

MODEL = "M0_ELO_POISSON_RESEARCH_720TRAIN_V1"
SCHEMA = "kb3-test-readonly-derived-markets-v1"
ALLOWED_LEAGUES = frozenset(("ESP", "ITA", "GER", "FRA", "NED", "BEL", "TUR", "POL"))
PROOF_CLASSES = frozenset((
    "GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES",
    "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES",
))
TOL = 2e-10


class TestMarketGateError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise TestMarketGateError(reason)


def utc(value):
    require(isinstance(value, str) and value.endswith("Z"), "CANONICAL_UTC_REQUIRED")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TestMarketGateError("INVALID_UTC") from exc
    require(timestamp.utcoffset() == timedelta(0), "UTC_REQUIRED")
    return timestamp


def digest(value):
    return sha256(canonical(value)).hexdigest()


def from_frozen_parent(parent, *, original_id, host_event_utc, host_source):
    """Check an immutable M0 parent, then derive math using its frozen lambdas.

    Host fields MUST originate from an actual stored proof row, not a timestamp
    supplied by a user or a file name. This layer does not re-attest archive bytes.
    """
    require(isinstance(parent, dict), "FROZEN_PARENT_REQUIRED")
    require(parent.get("model_version") == MODEL, "NOT_FITTED_M0_720_PARENT")
    require(parent.get("league_country") in ALLOWED_LEAGUES, "PROTECTED_OR_UNKNOWN_LEAGUE")
    require(parent.get("phase") == "EARLY", "NOT_EARLY_FORECAST")
    require(parent.get("status") == "RESEARCH_TRAIN720_UNCALIBRATED",
            "NOT_UNCHANGED_RESEARCH_M0")
    require(parent.get("training_allowed") is False
            and parent.get("production_approved") is False, "UNAUTHORIZED_APPROVAL")
    require(parent.get("original_provider_first_published_at_proven") is False,
            "ORIGINAL_PROVIDER_PIT_MISLABELED")
    require(parent.get("forecast_sha256") == original_id, "PARENT_ID_MISMATCH")
    original = {key: value for key, value in parent.items() if key != "forecast_sha256"}
    require(digest(original) == original_id, "ORIGINAL_FROZEN_PAYLOAD_HASH_MISMATCH")
    require(host_source in PROOF_CLASSES, "NOT_AN_ACCEPTED_HOST_PROOF_CLASS")
    require(parent.get("source_chain_sha256") and parent.get("feature_sha256")
            and parent.get("params_sha256") and parent.get("manifest_sha256"),
            "MISSING_SOURCE_OR_MODEL_LINEAGE")
    kickoff = utc(parent.get("kickoff_utc"))
    cutoff = utc(parent.get("feature_cutoff_utc"))
    frozen = utc(parent.get("generated_at_utc"))
    host = utc(host_event_utc)
    require(cutoff <= frozen <= host <= kickoff - timedelta(minutes=90),
            "EARLY_OR_HOST_PROOF_TIME_INVALID")
    require(str(parent.get("provider_match_id", "")).startswith("m_"),
            "NATIVE_FIXTURE_ID_REQUIRED")
    expected = parent.get("expected_goals")
    require(isinstance(expected, dict) and set(expected) == {"home", "away"},
            "FROZEN_EXPECTED_GOALS_REQUIRED")
    derived = markets_from_lambdas(expected["home"], expected["away"])
    for group in ("p_1x2", "p_over"):
        actual = parent.get(group)
        require(isinstance(actual, dict) and set(actual) == set(derived[group]),
                "M0_MARKET_SCHEMA_MISMATCH_" + group)
        for key, value in actual.items():
            require(type(value) in (int, float) and
                    abs(value - derived[group][key]) <= TOL,
                    "DERIVED_MARKET_DIVERGES_FROM_FROZEN_M0_" + group)
    require(type(parent.get("p_btts_yes")) in (int, float) and
            abs(parent["p_btts_yes"] - derived["p_btts"]["yes"]) <= TOL,
            "DERIVED_BTTS_DIVERGES_FROM_FROZEN_M0")
    p = derived["p_1x2"]
    double_chance = {
        "1X": p["1"] + p["X"],
        "X2": p["X"] + p["2"],
        "12": p["1"] + p["2"],
    }
    require(all(0 <= x <= 1 + TOL for x in double_chance.values())
            and abs(double_chance["1X"] - (1-p["2"])) <= TOL
            and abs(double_chance["X2"] - (1-p["1"])) <= TOL
            and abs(double_chance["12"] - (1-p["X"])) <= TOL,
            "DOUBLE_CHANCE_MATH_FAIL")
    return {
        "schema": SCHEMA,
        "original_m0_forecast_sha256": original_id,
        "league": parent["league_country"],
        "native_match_id": parent["provider_match_id"],
        "kickoff_utc": parent["kickoff_utc"],
        "original_feature_cutoff_utc": parent["feature_cutoff_utc"],
        "original_host_proof_utc": host_event_utc,
        "proof_class": host_source,
        "source_feature_sha256": parent["feature_sha256"],
        "original_params_sha256": parent["params_sha256"],
        "market_period": "REGULAR_90_MINUTES",
        "p_1x2": derived["p_1x2"],
        "p_double_chance": double_chance,
        "p_over": derived["p_over"],
        "p_under": derived["p_under"],
        "p_btts": derived["p_btts"],
        "team_goals": derived["team_goals"],
        "derived_from_original_probabilities_not_new_prematch_market_freeze": True,
        "host_proof_stored_row_required": True,
        "re_attested_original_artifact_bytes_by_this_reader": False,
        "new_independent_market_freeze_performed": False,
        "official_fit_increment": 0,
        "production_approved": False,
        "research_only": True,
        "bookmaker_odds_included": False,
        "market_recommendation": False,
        "formal_test_generator_gate_pass": False,
    }


def read_original_sqlite(db_path, *, as_of_utc, limit=100):
    """SELECT only, with SQLite opened mode=ro/query_only. Never derive retro picks."""
    require(type(limit) is int and 1 <= limit <= 500, "INVALID_READ_LIMIT")
    as_of = utc(as_of_utc)
    path = Path(db_path).resolve()
    require(path.is_file(), "ORIGINAL_SQLITE_NOT_FOUND")
    uri = path.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "ORIGINAL_SQLITE_CORRUPT")
        tables = {x[0] for x in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        require({"forecasts", "m0720_github_push_proofs"} <= tables,
                "HOST_PROOF_TABLE_REQUIRED")
        sql = """SELECT f.id,f.payload_json,p.github_server_event_utc,p.source,
                        f.kickoff_utc,f.captured_at_utc
                 FROM forecasts f
                 JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
                 WHERE NOT EXISTS(SELECT 1 FROM settlements s WHERE s.forecast_id=f.id)
                 ORDER BY f.kickoff_utc,f.id"""
        require("settlements" in tables, "SETTLEMENT_TABLE_REQUIRED")
        seen = set()
        rows = []
        for fid, raw, host, source, kick, captured in db.execute(sql):
            if utc(kick) <= as_of + timedelta(minutes=90):
                continue
            require(fid not in seen, "DUPLICATE_FROZEN_PARENT")
            seen.add(fid)
            item = json.loads(raw)
            require(item.get("kickoff_utc") == kick
                    and item.get("generated_at_utc") == captured,
                    "SQLITE_FROZEN_ROW_PAYLOAD_MISMATCH")
            rows.append(from_frozen_parent(
                item, original_id=fid, host_event_utc=host, host_source=source))
            if len(rows) >= limit:
                break
    return {
        "schema": SCHEMA,
        "as_of_utc": as_of_utc,
        "count": len(rows),
        "derived_previews": rows,
        "original_sqlite_changed": False,
        "new_forecasts_created": 0,
        "new_market_freezes_created": 0,
        "official_fit_increment": 0,
        "production_approved": False,
        "gate16": "PENDING",
        "gate17": "PENDING",
    }
