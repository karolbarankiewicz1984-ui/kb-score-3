"""KB3 independent multi-stat historical PitchAPI backfill (observed in 2026).

Research-only, never reconstruct provider first-published timestamps. Does not
modify live M0 forecasts, existing step17 xG, TEST or fitted models.
Archives full provider payloads encrypted; stores validated native per-match
statistics for later *separate* feature/ML research.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain
from scripts.kb3_ucl_pitchapi_collector import choose_ucl
from src.kb3_pit_ledger import as_utc, canonical, utc_now
from src.kb3_pitch_native import MATCH_ID, TEAM_ID
from src.kb3_pitch_uefa_evidence import add_observation, seal
from src.kb3_step14_pitchapi_xg_semantics import (
    SemanticAuditError, parse_native_shots, parse_native_team_stats,
)
from src.kb3_step16_m0_720_eight_forward import ROOT, EIGHT, select_eight

SEASONS = ("2023/2024", "2024/2025", "2025/2026", "2026/2027")
MAIN_SEASONS = ("2024/2025", "2025/2026", "2026/2027")
MAX_MATCHES = 48
MAX_CALLS = 150
MAX_STAT_ITEMS = 350
ARCHIVE = ROOT / "data/pit_sidecar/historical_multistat"
DB = ROOT / "data/research/historical_multistat/observations.sqlite"
PUBLIC_KEY = ROOT / "config/step11_archive_recipient_public.pem"
SCHEMA = "kb3-historical-multistat-backfill-observed-20261103-v1"


class BackfillError(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise BackfillError(why)


def stamp(dt):
    return as_utc(dt).isoformat(timespec="microseconds").replace("+00:00", "Z")


def hashobj(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def select_scopes(catalog):
    """Eight fixed national leagues, optional exact UEFA UCL; no English TEST."""
    selected = select_eight(catalog)
    leagues = catalog["leagues"]
    lookup = {item["id"]: item for item in leagues if isinstance(item, dict) and isinstance(item.get("id"), str)}
    scopes = []
    for country, name, league_id in selected:
        listing = lookup[league_id]
        for season in SEASONS:
            if season in listing.get("seasons", []):
                scopes.append((country, league_id, season))
    ucl, status = choose_ucl(catalog)
    if ucl is not None:
        for season in SEASONS:
            if season in ucl.get("seasons", []):
                scopes.append(("UCL", ucl["id"], season))
    require(len({(a, c) for a, _, c in scopes}) == len(scopes), "DUPLICATE_COMPETITION_SEASON")
    require(all(a != "ENG" for a, _, _ in scopes), "PROTECTED_PREMIER_LEAGUE_SCOPE")
    require(all(any(a == country and s in MAIN_SEASONS for a, _, s in scopes)
                for country, _, _ in selected), "EIGHT_LEAGUE_HISTORY_NOT_AVAILABLE")
    return scopes, status


def validate_match_rows(payload, scope, season, observed):
    """Return ended fixtures only; no future labels, duplicates or invalid teams."""
    require(isinstance(payload, dict) and isinstance(payload.get("matches"), list),
            "LISTING_NOT_A_MATCH_COLLECTION")
    matches = payload["matches"]
    require(0 < len(matches) <= 1500, "EMPTY_OR_OVERSIZED_LISTING")
    seen = set()
    valid = []
    year = int(season[:4])
    for m in matches:
        require(isinstance(m, dict), "INVALID_NATIVE_MATCH_OBJECT")
        mid = m.get("id")
        require(isinstance(mid, str) and MATCH_ID.fullmatch(mid) and mid not in seen,
                "DUPLICATE_OR_INVALID_MATCH_ID")
        seen.add(mid)
        a, b = m.get("home_team"), m.get("away_team")
        require(isinstance(a, dict) and isinstance(b, dict), "MISSING_TEAM_ID")
        require(all(isinstance(t.get("id"), str) and TEAM_ID.fullmatch(t["id"]) for t in (a, b))
                and a["id"] != b["id"], "INVALID_NATIVE_TEAMS")
        ko = as_utc(m.get("time_utc"))
        require(ko.year in (year, year + 1), "MATCH_OUTSIDE_PROVIDER_SEASON")
        if m.get("status") != "finished":
            continue
        require(all(type(m.get(k)) is int and 0 <= m[k] <= 30
                    for k in ("score_home", "score_away")), "INVALID_FINISHED_90M_RESULT")
        if ko + timedelta(hours=3) <= as_utc(observed):
            valid.append(m)
    return valid


def select_batch(groups, known, max_matches=MAX_MATCHES):
    """Interleave competitions/seasons so recent form and 2024/25 both progress."""
    require(1 <= max_matches <= MAX_MATCHES, "MATCH_BATCH_LIMIT")
    # Alternate current, recent history, historical training and form warmup.
    priority = {"2026/2027": 0, "2025/2026": 1,
                "2024/2025": 2, "2023/2024": 3}
    queues = []
    for (scope, season), rows in sorted(groups.items(),
                                      key=lambda x: (priority[x[0][1]], x[0][0])):
        remaining = [m for m in rows if (scope, m["id"]) not in known]
        remaining.sort(key=lambda m: (m["time_utc"], m["id"]), reverse=True)
        if remaining:
            queues.append((scope, season, remaining))
    chosen = []
    # A whole round traverses all available scope-season queues before the next.
    for index in range(max_matches):
        if not queues:
            break
        scope, season, pending = queues.pop(0)
        m = pending.pop(0)
        chosen.append((scope, season, m))
        if pending:
            queues.append((scope, season, pending))
    require(len({(scope, m["id"]) for scope, _, m in chosen}) == len(chosen),
            "DUPLICATE_BACKFILL_MATCH")
    return chosen


def all_period_stat_items(payload, match):
    """Validate identities, retain all *All-period* items with provider labels."""
    d = payload.get("data", payload) if isinstance(payload, dict) else None
    require(isinstance(d, dict) and d.get("match_id") == match["id"],
            "STATS_NOT_SAME_NATIVE_MATCH")
    require(isinstance(d.get("home_team"), dict) and isinstance(d.get("away_team"), dict)
            and d["home_team"].get("id") == match["home_team"]["id"]
            and d["away_team"].get("id") == match["away_team"]["id"],
            "STATS_NATIVE_TEAM_SIDE_MISMATCH")
    periods = d.get("periods")
    require(isinstance(periods, list), "STATS_PERIODS_MISSING")
    alls = [p for p in periods if isinstance(p, dict) and p.get("period") == "All"]
    require(len(alls) == 1, "FULL_MATCH_STATS_PERIOD_NOT_UNIQUE")
    rows = []
    for group in alls[0].get("groups", []):
        require(isinstance(group, dict) and isinstance(group.get("items"), list),
                "INVALID_STATS_GROUP")
        title = str(group.get("name") or group.get("group_name") or group.get("title") or "")
        for item in group["items"]:
            require(isinstance(item, dict), "INVALID_STATS_ITEM")
            key = item.get("key")
            if not isinstance(key, str) or not key or len(key) > 120:
                continue
            def val(x):
                if x is None or isinstance(x, (dict, list, bool)):
                    return None
                s = str(x).strip()
                return s[:100] if s else None
            rows.append({"group": title[:120], "key": key,
                         "format_type": val(item.get("format_type")),
                         "home": val(item.get("home")),
                         "away": val(item.get("away"))})
    require(0 < len(rows) <= MAX_STAT_ITEMS, "EMPTY_OR_OVERSIZED_STATS_ITEMS")
    return rows


def native_xg_verified(stats, shots, match):
    """Cross-check independent source-native shot and team xG, without imputation."""
    if not isinstance(shots, dict):
        return "SHOTS_UNAVAILABLE", None, None, None, None
    mid = match["id"]
    home, away = match["home_team"]["id"], match["away_team"]["id"]
    try:
        h, a = parse_native_team_stats(stats, mid, home, away)
        sh, sa, nh, na = parse_native_shots(shots, mid, home, away)
        if abs(h - sh) > .15 or abs(a - sa) > .15:
            return "XG_SHOTS_STATS_DISAGREE", None, None, None, None
        return "VERIFIED", h, a, nh, na
    except (SemanticAuditError, ValueError, TypeError, KeyError):
        return "XG_INCOMPLETE_OR_INVALID", None, None, None, None


SQL = """
CREATE TABLE IF NOT EXISTS observations (
 scope TEXT NOT NULL, season TEXT NOT NULL, match_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL, home_team_id TEXT NOT NULL, away_team_id TEXT NOT NULL,
 goals_home_90 INTEGER NOT NULL, goals_away_90 INTEGER NOT NULL,
 source_observed_at_utc TEXT NOT NULL, provider_first_published_at_utc TEXT,
 stat_items_json TEXT NOT NULL, stat_key_count INTEGER NOT NULL,
 xg_status TEXT NOT NULL, xg_home REAL, xg_away REAL,
 shots_home INTEGER, shots_away INTEGER,
 stats_payload_sha256 TEXT NOT NULL, shots_payload_sha256 TEXT,
 source_chain_sha256 TEXT NOT NULL, research_only INTEGER NOT NULL CHECK(research_only=1),
 PRIMARY KEY(scope,match_id),
 CHECK(provider_first_published_at_utc IS NULL),
 CHECK((xg_status='VERIFIED' AND xg_home IS NOT NULL AND xg_away IS NOT NULL)
       OR (xg_status!='VERIFIED' AND xg_home IS NULL AND xg_away IS NULL))
);
CREATE TRIGGER IF NOT EXISTS observations_no_update BEFORE UPDATE ON observations
 BEGIN SELECT RAISE(ABORT,'IMMUTABLE_HISTORICAL_SOURCE'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete BEFORE DELETE ON observations
 BEGIN SELECT RAISE(ABORT,'IMMUTABLE_HISTORICAL_SOURCE'); END;
"""


def existing_ids(path):
    if not Path(path).exists():
        return set()
    with sqlite3.connect(path) as db:
        db.executescript(SQL)
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "BACKFILL_DB_CORRUPTION")
        return set(db.execute("SELECT scope,match_id FROM observations"))


def put_rows(path, samples):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript(SQL)
        for s in samples:
            db.execute("""INSERT INTO observations
              (scope,season,match_id,kickoff_utc,home_team_id,away_team_id,
               goals_home_90,goals_away_90,source_observed_at_utc,
               provider_first_published_at_utc,stat_items_json,stat_key_count,
               xg_status,xg_home,xg_away,shots_home,shots_away,
               stats_payload_sha256,shots_payload_sha256,source_chain_sha256,research_only)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
               (s["scope"],s["season"],s["id"],s["time_utc"],s["home_id"],s["away_id"],
                s["goals_home"],s["goals_away"],s["observed_at"],None,
                json.dumps(s["items"],sort_keys=True),s["stat_key_count"],
                s["xg_status"],s["xg_home"],s["xg_away"],s["shots_home"],s["shots_away"],
                s["stats_sha"],s["shots_sha"],s["source_chain"]))
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "BACKFILL_DB_CORRUPTION")
        n, verified = db.execute(
            "SELECT COUNT(*),SUM(CASE WHEN xg_status='VERIFIED' THEN 1 ELSE 0 END) FROM observations"
        ).fetchone()
        db.commit()
    return n, verified or 0


def capture(*, client, root=ARCHIVE, db_path=DB, public_key=PUBLIC_KEY,
            run_token, max_matches=MAX_MATCHES):
    require(bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_token)), "INVALID_RUN_TOKEN")
    require(1 <= max_matches <= MAX_MATCHES, "UNSAFE_MATCH_LIMIT")
    known = existing_ids(db_path)
    receipts = []
    errors = Counter()
    calls = 0
    def call(resource, fn, *args, **kwargs):
        nonlocal calls
        require(calls < MAX_CALLS, "HISTORICAL_PROVIDER_CALL_CAP")
        started = utc_now()
        try:
            payload = to_plain(fn(*args, **kwargs))
        except Exception as exc:
            calls += 1
            errors[type(exc).__name__] += 1
            return None, None
        ended = utc_now()
        calls += 1
        require(isinstance(payload, dict), "NON_OBJECT_SOURCE_PAYLOAD")
        add_observation(receipts, resource=resource, payload=payload,
                        started=started, completed=ended)
        return payload, receipts[-1]
    catalog, receipt = call("pitchapi:catalog", client.leagues.list)
    require(catalog is not None, "PITCHAPI_CATALOG_UNAVAILABLE")
    scopes, ucl_status = select_scopes(catalog)
    groups = {}
    source_counts = {}
    for scope, lid, season in scopes:
        listing, r = call("pitchapi:history:fixtures:" + scope + ":" + season,
                          client.leagues.matches, lid, season=season, status="all")
        if listing is None:
            errors["MISSING_SEASON_" + scope + "_" + season] += 1
            continue
        rows = validate_match_rows(listing, scope, season, r["completed_at_utc"])
        groups[(scope, season)] = rows
        source_counts[scope + "/" + season] = len(rows)
    require(bool(groups), "NO_VALID_HISTORICAL_MATCHES")
    selected = select_batch(groups, known, max_matches=max_matches)
    samples = []
    stat_keys = set()
    missing_stats = 0
    for scope, season, m in selected:
        mid = m["id"]
        stats, sr = call("pitchapi:history:stats:" + mid, client.matches.stats, mid)
        if stats is None:
            missing_stats += 1
            continue
        try:
            items = all_period_stat_items(stats, m)
        except (BackfillError, TypeError, KeyError):
            errors["STATS_SHAPE_OR_IDENTITY"] += 1
            missing_stats += 1
            continue
        shots, sh = call("pitchapi:history:shots:" + mid, client.matches.shots, mid)
        state, xh, xa, nh, na = native_xg_verified(stats, shots, m)
        stat_keys.update(i["key"] for i in items)
        samples.append({"scope": scope, "season": season, "id": mid,
            "time_utc": m["time_utc"], "home_id": m["home_team"]["id"],
            "away_id": m["away_team"]["id"], "goals_home": m["score_home"],
            "goals_away": m["score_away"], "observed_at": sr["completed_at_utc"],
            "items": items, "stat_key_count": len({i["key"] for i in items}),
            "xg_status": state, "xg_home": xh, "xg_away": xa,
            "shots_home": nh, "shots_away": na,
            "stats_sha": sr["payload_sha256"],
            "shots_sha": sh["payload_sha256"] if sh else None,
            "source_chain": (sh or sr)["chain_sha256"]})
    require(calls <= MAX_CALLS, "HISTORICAL_PROVIDER_CALL_BUDGET_OVERFLOW")
    started_day = as_utc(receipts[0]["started_at_utc"]).date().isoformat()
    dest = Path(root) / started_day / ("run-" + run_token)
    require(not dest.exists(), "HISTORICAL_IMMUTABLE_RUN_ALREADY_EXISTS")
    dest.mkdir(parents=True, exist_ok=False)
    staged = dest / "STAGED_HISTORICAL.sqlite"
    try:
        if Path(db_path).exists():
            shutil.copy2(db_path, staged)
        total, verified = put_rows(staged, samples)
        sealed = seal(receipts, public_key, dest / "HISTORICAL_SOURCE.enc",
                      dest / "HISTORICAL_SOURCE.manifest.json")
        report = {"schema": SCHEMA, "source": "PitchAPI",
            "started_utc": receipts[0]["started_at_utc"],
            "ended_utc": receipts[-1]["completed_at_utc"],
            "run_token": run_token, "provider_requests": calls,
            "provider_call_cap": MAX_CALLS, "match_request_limit": max_matches,
            "source_seasons": list(SEASONS),
            "scopes_catalogued": len(scopes), "scopes_observed": len(groups),
            "source_finished_counts": source_counts,
            "ucl_catalog_status": ucl_status,
            "new_match_stats": len(samples), "missing_stats": missing_stats,
            "new_native_xg_verified": sum(s["xg_status"] == "VERIFIED" for s in samples),
            "new_xg_missing_or_invalid": sum(s["xg_status"] != "VERIFIED" for s in samples),
            "unique_stat_keys_observed": len(stat_keys),
            "stat_key_names": sorted(stat_keys),
            "cumulative_match_stats": total,
            "cumulative_xg_verified": verified,
            "source_ciphertext_sha256": sealed["ciphertext_sha256"],
            "source_chain_sha256": sealed["proof"]["final_chain_sha256"],
            "source_payloads_encrypted": True,
            "original_2023_2025_provider_published_at_proven": False,
            "historical_pit_certified": False,
            "research_reconstruction_possible": bool(total),
            "research_training_performed": False,
            "official_training_allowed": False,
            "calibration_changed": False,
            "existing_m0_modified": False,
            "protected_premier_league_test_accessed": False,
            "gate16_gate17": "PENDING",
            "errors_by_type": dict(errors)}
        with (dest / "HISTORICAL_BACKFILL_REPORT.json").open("x", encoding="utf8") as f:
            json.dump(report, f, sort_keys=True, indent=2)
            f.write("\n")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, db_path)
        return report
    finally:
        staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-token", required=True)
    parser.add_argument("--max-matches", type=int, default=MAX_MATCHES)
    args = parser.parse_args()
    key = os.getenv("PITCHAPI_API_KEY", "").strip()
    if not key:
        raise SystemExit("EXISTING_PITCHAPI_SECRET_NOT_CONFIGURED")
    from pitchapi import PitchAPI
    try:
        result = capture(client=PitchAPI(api_key=key),
                         run_token=args.run_token, max_matches=args.max_matches)
    except Exception as err:
        # Never include provider responses, tokens, fixture/team names in logs.
        print("KB3_HISTORY_CAPTURE_BLOCKED", type(err).__name__)
        raise SystemExit(3)
    print("KB3_HISTORY_CAPTURE", json.dumps({k: result[k] for k in (
        "provider_requests", "new_match_stats", "new_native_xg_verified",
        "cumulative_match_stats", "cumulative_xg_verified",
        "scopes_observed", "historical_pit_certified", "gate16_gate17"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
