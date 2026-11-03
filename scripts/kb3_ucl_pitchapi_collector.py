"""Independent KB Score 3.0 UEFA Champions League PitchAPI source collector.

RESEARCH ONLY. Native IDs, observed-at timestamps and sealed raw receipts.
No forecast, no model fit, no changes to the eight-league M0 or protected TEST.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import timedelta
from pathlib import Path

from scripts.pitchapi_step06_audit import norm, to_plain
from src.kb3_pit_ledger import as_utc, canonical, utc_now
from src.kb3_pitch_native import MATCH_ID, TEAM_ID, LAG, verify_native_shots
from src.kb3_pitch_uefa_evidence import add_observation, seal

CURRENT = "2026/2027"
PREVIOUS = "2025/2026"
HORIZON = timedelta(hours=96)
LEAD = timedelta(minutes=90)
CALL_CAP = 7  # catalogue, two seasons, at most two shots + two stats
FINISHED = "finished"
UPCOMING = frozenset(("not_started", "scheduled", "upcoming"))
BLOCKLIST = frozenset(("afc", "caf", "concacaf", "women", "womens", "youth", "junior", "u19", "u17", "qualifying", "qualification"))
SCHEMA = "kb3-ucl-pitchapi-independent-observed-20261103-v1"


class UCLCaptureError(ValueError):
    pass


def _identity_name(league):
    name = norm(league.get("name", "")) if isinstance(league, dict) else ""
    tokens = set(name.split())
    return name.endswith("champions league") and not tokens.intersection(BLOCKLIST)


def choose_ucl(catalog):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("leagues"), list):
        raise UCLCaptureError("CATALOG_INVALID")
    candidates = [x for x in catalog["leagues"] if _identity_name(x)]
    current = [x for x in candidates if CURRENT in (x.get("seasons") or [])]
    if not candidates:
        return None, "UCL_NOT_IN_PROVIDER_CATALOG"
    if not current:
        return None, "UCL_2026_27_NOT_AVAILABLE"
    if len(current) != 1:
        return None, "UCL_CATALOG_AMBIGUOUS"
    one = current[0]
    if not isinstance(one.get("id"), str) or not re.fullmatch(r"l_[A-Za-z0-9]{6}", one["id"]):
        raise UCLCaptureError("UCL_NATIVE_LEAGUE_ID_INVALID")
    if one.get("is_free") is False:
        return None, "UCL_NOT_FREE_IN_CURRENT_PLAN"
    return one, "UCL_CATALOG_MATCHED"


def validate_listing(payload, season):
    if not isinstance(payload, dict) or not isinstance(payload.get("matches"), list):
        raise UCLCaptureError("UCL_SEASON_LISTING_INVALID")
    matches = payload["matches"]
    if not matches or len(matches) > 1500:
        raise UCLCaptureError("UCL_EMPTY_OR_OVERSIZED_LISTING")
    unique = set()
    counts = Counter()
    for game in matches:
        if not isinstance(game, dict):
            raise UCLCaptureError("UCL_NON_OBJECT_GAME")
        mid = game.get("id")
        if not isinstance(mid, str) or not MATCH_ID.fullmatch(mid) or mid in unique:
            raise UCLCaptureError("UCL_DUPLICATE_OR_INVALID_NATIVE_ID")
        unique.add(mid)
        home, away = game.get("home_team"), game.get("away_team")
        if not isinstance(home, dict) or not isinstance(away, dict):
            raise UCLCaptureError("UCL_MISSING_TEAMS")
        ids = [home.get("id"), away.get("id")]
        if any(not isinstance(i, str) or not TEAM_ID.fullmatch(i) for i in ids) or ids[0] == ids[1]:
            raise UCLCaptureError("UCL_INVALID_TEAM_ID")
        ko = as_utc(game.get("time_utc"))
        start_year = int(season[:4])
        if ko.year not in (start_year, start_year + 1):
            raise UCLCaptureError("UCL_KICKOFF_OUTSIDE_SEASON")
        state = game.get("status")
        if state == FINISHED:
            if not all(type(game.get(k)) is int and game[k] >= 0 for k in ("score_home", "score_away")):
                raise UCLCaptureError("UCL_INVALID_FINISHED_SCORE")
        elif state in UPCOMING:
            if game.get("score_home") is not None or game.get("score_away") is not None:
                raise UCLCaptureError("UCL_FUTURE_CONTAINS_SCORE")
        else:
            counts["other_unusable_status"] += 1
        counts[str(state)] += 1
    return matches, dict(sorted(counts.items()))


def prematch_targets(matches, cutoff):
    now = as_utc(cutoff)
    result = [game for game in matches
              if game["status"] in UPCOMING
              and now + LEAD <= as_utc(game["time_utc"]) <= now + HORIZON]
    return sorted(result, key=lambda g: (g["time_utc"], g["id"]))


def historical_samples(current, previous, captured_at, maximum=2):
    cutoff = as_utc(captured_at)
    eligible = [g for g in current + previous if g["status"] == FINISHED
                and as_utc(g["time_utc"]) + LAG <= cutoff]
    eligible.sort(key=lambda g: (g["time_utc"], g["id"]), reverse=True)
    return eligible[:maximum]


def _safe_stat_key_count(payload):
    keys = set()
    for period in payload.get("periods", []) if isinstance(payload, dict) else []:
        for group in period.get("groups", []) if isinstance(period, dict) else []:
            for item in group.get("items", []) if isinstance(group, dict) else []:
                if isinstance(item, dict) and isinstance(item.get("key"), str):
                    keys.add(item["key"])
    return len(keys)


def capture(*, client, out_root, public_key, run_token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_token):
        raise UCLCaptureError("UNSAFE_RUN_TOKEN")
    receipts = []
    calls = 0

    def call(resource, method, *args, **kwargs):
        nonlocal calls
        if calls >= CALL_CAP:
            raise UCLCaptureError("UCL_REQUEST_CAP_REACHED")
        began = utc_now()
        raw = to_plain(method(*args, **kwargs))
        completed = utc_now()
        calls += 1
        add_observation(receipts, resource=resource, payload=raw,
                        started=began, completed=completed)
        return raw, completed

    catalog, _ = call("pitchapi:catalog", client.leagues.list)
    league, status = choose_ucl(catalog)
    report = {
        "schema": SCHEMA, "provider": "PitchAPI",
        "season": CURRENT, "previous_season": PREVIOUS,
        "catalog_status": status, "league_id": None,
        "league_is_free_flag": None, "current_count": None,
        "previous_count": None, "historical_coverage_available": False,
        "upcoming_prematch_targets": 0, "upcoming_target_ids_sha256": None,
        "target_earliest_kickoff_utc": None, "target_latest_kickoff_utc": None,
        "sampled_finished_games": 0, "native_shots_xg_complete": 0,
        "native_shots_xg_missing_or_invalid": 0,
        "sampled_stat_key_counts": [],
        "observed_first_publication_proven": False,
        "original_historic_pit_certified": False,
        "training_allowed": False, "model_fit_performed": False,
        "forecasts_created": 0, "production_approved": False,
        "original_2026_27_premier_league_test_accessed": False,
        "existing_m0_databases_modified": False,
        "max_pitchapi_calls": CALL_CAP,
    }
    if league is not None:
        report["league_id"] = league["id"]
        report["league_is_free_flag"] = league.get("is_free")
        current, observed = call("pitchapi:uefa:ucl:" + CURRENT,
                                 client.leagues.matches, league["id"],
                                 season=CURRENT, status="all")
        fixtures, states = validate_listing(current, CURRENT)
        report["current_count"] = len(fixtures)
        report["current_status_counts"] = states
        older = []
        if PREVIOUS in (league.get("seasons") or []):
            prior, _ = call("pitchapi:uefa:ucl:" + PREVIOUS,
                            client.leagues.matches, league["id"],
                            season=PREVIOUS, status="all")
            older, old_states = validate_listing(prior, PREVIOUS)
            if {g["id"] for g in fixtures}.intersection(g["id"] for g in older):
                raise UCLCaptureError("UCL_CROSS_SEASON_DUPLICATE_ID")
            report["previous_count"] = len(older)
            report["previous_status_counts"] = old_states
            report["historical_coverage_available"] = True
        targets = prematch_targets(fixtures, observed)
        report["upcoming_prematch_targets"] = len(targets)
        report["upcoming_target_ids_sha256"] = (
            hashlib.sha256(canonical([x["id"] for x in targets])).hexdigest()
            if targets else None
        )
        if targets:
            report["target_earliest_kickoff_utc"] = targets[0]["time_utc"]
            report["target_latest_kickoff_utc"] = targets[-1]["time_utc"]
        for game in historical_samples(fixtures, older, utc_now()):
            mid = game["id"]
            shots, shot_at = call("pitchapi:shots:" + mid,
                                  client.matches.shots, mid)
            # A present payload is not proof that xG is complete.
            try:
                wrapped = {"data": shots.get("data", shots)} if isinstance(shots, dict) else {}
                checked = verify_native_shots(game, wrapped, observed_at_utc=shot_at)
                complete = checked.get("shot_state") == "COMPLETE_SHOT_XG"
            except (ValueError, KeyError, TypeError):
                complete = False
            report["native_shots_xg_complete"] += int(complete)
            report["native_shots_xg_missing_or_invalid"] += int(not complete)
            stats, _ = call("pitchapi:uefa:ucl:stats:" + mid,
                             client.matches.stats, mid)
            report["sampled_stat_key_counts"].append(_safe_stat_key_count(stats))
            report["sampled_finished_games"] += 1
        report["catalog_status"] = "UCL_SOURCE_CAPTURED_PREMATCH_RESEARCH_ONLY"
    if calls != len(receipts) or calls > CALL_CAP:
        raise UCLCaptureError("UCL_CALL_ACCOUNTING_MISMATCH")
    day = as_utc(receipts[0]["started_at_utc"]).date().isoformat()
    destination = Path(out_root) / day / ("run-" + run_token)
    if destination.exists():
        raise FileExistsError("UCL_APPEND_ONLY_NO_OVERWRITE")
    destination.mkdir(parents=True, exist_ok=False)
    ciphertext = destination / "UCL_SOURCE.enc"
    manifest = destination / "UCL_SOURCE.manifest.json"
    source_meta = seal(receipts, public_key, ciphertext, manifest)
    report.update({
        "observed_started_utc": receipts[0]["started_at_utc"],
        "observed_completed_utc": receipts[-1]["completed_at_utc"],
        "provider_calls": calls,
        "source_chain_sha256": source_meta["proof"]["final_chain_sha256"],
        "source_ciphertext_sha256": source_meta["ciphertext_sha256"],
        "raw_source_encrypted": True,
        "model_gate": "PENDING_UCL_QUALITY_AND_INDEPENDENT_DECISION",
    })
    with (destination / "UCL_CAPTURE_REPORT.json").open("x", encoding="utf-8") as fd:
        json.dump(report, fd, sort_keys=True, indent=2, ensure_ascii=False)
        fd.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="data/pit_sidecar/ucl_research")
    parser.add_argument("--recipient", default="config/step11_archive_recipient_public.pem")
    parser.add_argument("--run-token", required=True)
    args = parser.parse_args()
    credential = os.environ.get("PITCHAPI_API_KEY", "").strip()
    if not credential:
        raise SystemExit("UCL_MISSING_PITCHAPI_SECRET")
    from pitchapi import PitchAPI
    try:
        result = capture(client=PitchAPI(api_key=credential),
                         out_root=args.base, public_key=args.recipient,
                         run_token=args.run_token)
    except Exception as exc:
        # Never print a provider response, credential, request URL or traceback.
        print("KB3_UCL_CAPTURE_BLOCKED", type(exc).__name__)
        raise SystemExit(3)
    print("KB3_UCL_CAPTURE_REPORT", json.dumps({
        k: result[k] for k in
        ("catalog_status", "provider_calls", "current_count", "previous_count",
         "upcoming_prematch_targets", "sampled_finished_games",
         "native_shots_xg_complete", "model_gate")
    }, sort_keys=True))


if __name__ == "__main__":
    main()
