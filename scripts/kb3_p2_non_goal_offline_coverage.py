"""KB3 P2: read-only native historical statistics coverage, NOT market settlement.

No API, no forecasting, no training, no protected TEST. This inspects EXISTING
normalized research observations only. The original source-period semantics
and provider first-publication time are not certified by these rows.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

SCHEMA = "kb3-p2-nongoal-observed-coverage-readonly-v1"
# Exact names are from the historical parser; no case-fold or guessed aliases.
FIELDS = {
    "FOULS": "fouls",
    "YELLOW_CARDS": "yellow_cards",
    "RED_CARDS": "red_cards",
    "CORNERS": "corners",
    "SHOTS_TOTAL": "total_shots",
    "SHOTS_ON_TARGET": "ShotsOnTarget",
}
SIDES = ("home", "away")
VALUE_RE = re.compile(r"^(?:\d+(?:\.0*)?|\.0+)$")


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_stat(items, key, side):
    """Classify an explicitly named integer stat; fail closed on conflicts.

    The extracted number is research source coverage, not a betting target.
    """
    if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
        return None, "MALFORMED_ITEMS"
    values = [x.get(side) for x in items if x.get("key") == key]
    if not values:
        return None, "FIELD_MISSING"
    parsed = []
    for v in values:
        if isinstance(v, bool) or v is None:
            return None, "VALUE_UNAVAILABLE"
        if isinstance(v, int):
            n = v
        elif isinstance(v, float):
            if not math.isfinite(v) or not v.is_integer():
                return None, "NON_INTEGER_OR_NONFINITE"
            n = int(v)
        elif isinstance(v, str) and VALUE_RE.fullmatch(v.strip()):
            n = int(float(v.strip()))
        else:
            return None, "VALUE_UNAVAILABLE"
        if n < 0:
            return None, "NEGATIVE_COUNT"
        parsed.append(n)
    if len(set(parsed)) != 1:
        return None, "CONFLICTING_DUPLICATE"
    return parsed[0], "VALUE_PRESENT_RESEARCH_ONLY"


def inspect_items(items):
    """Classify per-team counts; never infer source period or market rules."""
    out = {}
    for family, source_key in FIELDS.items():
        home, h_reason = count_stat(items, source_key, "home")
        away, a_reason = count_stat(items, source_key, "away")
        out[family] = {
            "home": home, "away": away,
            "home_status": h_reason, "away_status": a_reason,
            "both_sides_present": home is not None and away is not None,
        }
    # A contradiction cannot be silently "fixed" by guessing missing shots.
    for side in SIDES:
        total = out["SHOTS_TOTAL"][side]
        on_target = out["SHOTS_ON_TARGET"][side]
        if total is not None and on_target is not None and on_target > total:
            for family in ("SHOTS_TOTAL", "SHOTS_ON_TARGET"):
                out[family][side] = None
                out[family][side + "_status"] = "SHOTS_SUBCATEGORY_CONTRADICTION"
    for row in out.values():
        row["both_sides_present"] = row["home"] is not None and row["away"] is not None
    return out


def audit_connection(db):
    db.execute("PRAGMA query_only=ON")
    need(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SOURCE_SQLITE_INTEGRITY_FAIL")
    columns = {row[1] for row in db.execute("PRAGMA table_info(observations)")}
    required = {"scope", "season", "match_id", "home_team_id", "away_team_id", "stat_items_json"}
    need(required.issubset(columns), "OBSERVATION_SCHEMA_CHANGED")
    seen = set()
    coverage = defaultdict(lambda: {
        "observations": 0,
        "complete_pair_by_family": Counter(),
        "side_reason_by_family": defaultdict(Counter),
    })
    totals = Counter()
    query = """SELECT scope,season,match_id,home_team_id,away_team_id,stat_items_json
               FROM observations ORDER BY scope,season,match_id"""
    for scope, season, match, home_id, away_id, raw in db.execute(query):
        need(all(isinstance(v, str) and v.strip() for v in (scope, season, match, home_id, away_id))
             and home_id != away_id, "OBSERVATION_FIXTURE_IDENTITY_INVALID")
        key = (scope, match)
        need(key not in seen, "DUPLICATE_OBSERVATION_MATCH")
        seen.add(key)
        try:
            items = json.loads(raw)
        except (ValueError, TypeError):
            items = None
        evaluation = inspect_items(items)
        sub = coverage[scope]
        sub["observations"] += 1
        totals["observations"] += 1
        for family, item in evaluation.items():
            if item["both_sides_present"]:
                sub["complete_pair_by_family"][family] += 1
            for side in SIDES:
                sub["side_reason_by_family"][family][item[side + "_status"]] += 1
    return {
        "schema": SCHEMA,
        "source": "EXISTING_NORMALIZED_HISTORICAL_OBSERVATIONS_ONLY",
        "observations": totals["observations"],
        "families": dict(FIELDS),
        "per_scope": {
            scope: {
                "observations": data["observations"],
                "complete_pair_by_family": {
                    k: data["complete_pair_by_family"][k] for k in FIELDS
                },
                "side_reason_by_family": {
                    k: dict(sorted(data["side_reason_by_family"][k].items())) for k in FIELDS
                },
            }
            for scope, data in sorted(coverage.items())
        },
        "period_90_minutes_independently_proven": False,
        "first_provider_publication_before_target_kickoff_proven": False,
        "matches_bookmaker_target_definitions": False,
        "settlement_eligible": False,
        "forward_model_trained": False,
        "provider_api_calls": 0,
        "research_only": True,
        "protected_test_read": False,
    }


def audit_sqlite(path):
    source = Path(path).resolve()
    need(source.is_file(), "ORIGINAL_SQLITE_NOT_FOUND")
    before = sha256_file(source)
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
        result = audit_connection(db)
    need(sha256_file(source) == before, "READONLY_SOURCE_CHANGED")
    result["source_sqlite_sha256"] = before
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    need(not args.out.exists(), "APPEND_ONLY_REPORT_PATH_EXISTS")
    result = audit_sqlite(args.db)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as file:
        json.dump(result, file, sort_keys=True, indent=2, ensure_ascii=False)
        file.write("\n")
    print("KB3_P2_NON_GOAL_RESEARCH_COVERAGE_PASS", result["observations"],
          "scopes", len(result["per_scope"]), "no_market_settlement", True)


if __name__ == "__main__":
    main()
