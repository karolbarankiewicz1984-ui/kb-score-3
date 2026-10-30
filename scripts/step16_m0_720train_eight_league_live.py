"""Independent eight-league real-forward fitted M0 (720 TRAIN) research stream.

Exactly 17 provider requests: catalogue + 2 native fixture seasons per league.
Historical Elo starts at 2025/26, NOT the Elo state used in 2023-25 training.
Read-only existing models; append-only UTC daily archive; no odds or TEST.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain
from scripts.step14_three_league_pitchapi_actual_audit import CURRENT, PREVIOUS
from src.kb3_pit_ledger import as_utc, canonical, hexdigest, utc_now
from src.kb3_pitch_native import check_season
from src.kb3_pitch_uefa_evidence import add_observation, seal
from src.kb3_step13_baseline import BaselineParameters, forecast, update_elo

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "models/research/M0_720_TRAIN_8LEAGUE_SHADOW_LIVE_V1.json"
CANDIDATE = ROOT / "models/research/M0_720_TRAIN_STABLE_CANDIDATE_20261029.json"
MODEL = "M0_720TRAIN_8LEAGUE_RESEARCH_V1"
SCHEMA = "kb3-step16-m0-720train-eight-league-forward-observed-v1"
LAG = timedelta(hours=3)
MIN_PREMATCH = timedelta(minutes=90)
HORIZON = timedelta(hours=96)
PER_LEAGUE_LIMIT = 10
CALL_CAP = 17
LEAGUES = (
    ("ESP", "LaLiga", ("laliga", "laligaeasports", "laligaea", "primeradivision"), 380, 380),
    ("ITA", "Serie A", ("seriea",), 380, 380),
    ("GER", "Bundesliga", ("bundesliga",), 306, 306),
    ("FRA", "Ligue 1", ("ligue1", "ligue1mcdonalds"), 306, 306),
    ("NED", "Eredivisie", ("eredivisie",), 306, 309),
    ("BEL", "Belgian Pro League", ("jupilerproleague", "proleague", "firstdivisiona", "belgianproleague"), 306, 313),
    ("TUR", "Super Lig", ("superlig", "trendyolsuperlig"), 306, 306),
    ("POL", "Ekstraklasa", ("ekstraklasa", "pkobpekstraklasa"), 306, 306),
)

class ResearchStreamError(ValueError):
    pass


def norm(value):
    return "".join(c for c in str(value).casefold() if c.isalnum())


def utc(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def match_hash(country, native_id):
    return hexdigest((country + "|" + native_id).encode("ascii"))


def load_release(release_path=RELEASE, candidate_path=CANDIDATE):
    release = json.loads(Path(release_path).read_text("utf8"))
    candidate = json.loads(Path(candidate_path).read_text("utf8"))
    if (release.get("model_id") != MODEL
        or release.get("research_only") is not True
        or release.get("promotion_automatic") is not False
        or release.get("leagues") != [x[0] for x in LEAGUES]
        or release.get("train_matches") != 720
        or release.get("validation_matches") != 374
        or release.get("candidate_id") != candidate.get("candidate_id")
        or release.get("fitted_parameters") != candidate.get("fitted_parameters")
        or candidate.get("trained_on_real_historical_matches") != 720
        or candidate.get("validation_matches") != 374
        or candidate.get("season_2026_27_original_premier_league_test_opened") is not False):
        raise ResearchStreamError("FITTED_MODEL_IDENTITY_OR_HOLDOUT_MISMATCH")
    params = BaselineParameters(**release["fitted_parameters"])
    return params, hexdigest(canonical(asdict(params))), hexdigest(canonical(release))


def selected_catalog(catalog):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("leagues"), list):
        raise ResearchStreamError("CATALOG_UNAVAILABLE")
    selected = []
    for country, name, aliases, current_count, previous_count in LEAGUES:
        matches = [x for x in catalog["leagues"] if isinstance(x, dict)
                   and str(x.get("country_code", "")).upper() == country
                   and norm(x.get("name", "")) in aliases
                   and CURRENT in (x.get("seasons") or [])
                   and PREVIOUS in (x.get("seasons") or [])]
        if len(matches) != 1 or not isinstance(matches[0].get("id"), str):
            raise ResearchStreamError("LEAGUE_CATALOG_AMBIGUOUS_OR_MISSING_" + country)
        lid = matches[0]["id"]
        if not lid.startswith("l_"):
            raise ResearchStreamError("INVALID_NATIVE_LEAGUE_" + country)
        selected.append((country, name, lid, current_count, previous_count))
    if len({item[2] for item in selected}) != 8:
        raise ResearchStreamError("REUSED_NATIVE_LEAGUE_ID")
    return selected


def verify_seasons(country, current, previous, current_expected, previous_expected):
    # Historical NED=309 / BEL=313 are deliberately accepted; no fabricated 306.
    check_season(current, CURRENT, expected_count=current_expected, require_upcoming=True)
    check_season(previous, PREVIOUS, expected_count=previous_expected)
    if any(m["status"] != "finished" for m in previous):
        raise ResearchStreamError("PREVIOUS_SEASON_UNSETTLED_" + country)
    if len({m["id"] for m in current + previous}) != len(current) + len(previous):
        raise ResearchStreamError("CROSS_SEASON_MATCH_ID_COLLISION_" + country)
    if any(m["status"] == "finished" and
           (type(m["score_home"]) is not int or type(m["score_away"]) is not int)
           for m in current + previous):
        raise ResearchStreamError("FINISHED_RESULT_INVALID_" + country)
    return True


def ratings_before_capture(current, previous, now, params):
    # One result affects the next fixture only when its match ended >=3h ago.
    completed = sorted(
        (m for m in previous + current
         if m["status"] == "finished" and as_utc(m["time_utc"]) + LAG < now),
        key=lambda m: (m["time_utc"], m["id"]))
    ratings = {}
    counts = Counter()
    for m in completed:
        h, a = m["home_team"]["id"], m["away_team"]["id"]
        gh, ga = m["score_home"], m["score_away"]
        result = "H" if gh > ga else "A" if gh < ga else "D"
        h0 = ratings.get(h, params.initial_elo)
        a0 = ratings.get(a, params.initial_elo)
        ratings[h], ratings[a] = update_elo(h0, a0, result, params)
        counts[h] += 1
        counts[a] += 1
    return ratings, counts, len(completed)


def new_forecasts(country, name, current, previous, now, params, params_sha,
                  release_sha, source_chain, observed_at, existing_keys):
    ratings, counts, completed_n = ratings_before_capture(current, previous, now, params)
    futures = sorted(
        (m for m in current if m["status"] in ("upcoming", "not_started", "scheduled")
         and now + MIN_PREMATCH < as_utc(m["time_utc"]) <= now + HORIZON),
        key=lambda m: (m["time_utc"], m["id"]))[:PER_LEAGUE_LIMIT]
    out = []
    skipped_cold = 0
    for m in futures:
        midhash = match_hash(country, m["id"])
        key = (country, midhash)
        if key in existing_keys:
            continue
        ht, at = m["home_team"]["id"], m["away_team"]["id"]
        if counts[ht] < 5 or counts[at] < 5:
            skipped_cold += 1
            continue
        if m.get("score_home") is not None or m.get("score_away") is not None:
            raise ResearchStreamError("TARGET_RESULT_SEEN_BEFORE_FORECAST")
        ko = as_utc(m["time_utc"])
        if not (as_utc(observed_at) <= now < ko - MIN_PREMATCH):
            raise ResearchStreamError("PREMATCH_CUTOFF_NOT_ENFORCED")
        f = forecast(ratings[ht], ratings[at], params)
        p = f["p_1x2"]
        if any(not math.isfinite(v) or not 0 < v < 1 for v in p.values()) or abs(sum(p.values())-1) > 1e-12:
            raise ResearchStreamError("PROBABILITY_SIMPLEX_INVALID")
        item = {
            "schema": SCHEMA, "model_id": MODEL, "params_sha256": params_sha,
            "release_sha256": release_sha, "league": country, "league_name": name,
            "native_match_id_sha256": midhash,
            "home": m["home_team"]["name"], "away": m["away_team"]["name"],
            "kickoff_utc": m["time_utc"], "observed_at_utc": observed_at,
            "frozen_at_utc": utc(now), "source_chain_sha256": source_chain,
            "elo_2025_26_start_home": ratings[ht], "elo_2025_26_start_away": ratings[at],
            "past_matches_home": counts[ht], "past_matches_away": counts[at],
            "p_1x2": p, "expected_goals": f["expected_goals"],
            "parameter_status": "FITTED_720TRAIN_RESEARCH_UNVALIDATED_TRANSFER",
            "feature_source": "REAL_NATIVE_MATCH_SCORES_OBSERVED_AT_UTC",
            "actual_provider_publication_at_unknown": True,
            "phase": "EARLY", "calibrated": False,
            "automatic_betting_or_production": False,
            "test_premier_league_2026_27_touched": False,
        }
        item["forecast_sha256"] = hexdigest(canonical(item))
        out.append(item)
    return out, {"completed_predecessors": completed_n,
                 "targets_96h_considered": len(futures), "cold_start_skipped": skipped_cold}


def read_history(root, *, params_sha, release_sha):
    forecasts = {}; settlements = {}
    for file in sorted(Path(root).glob("*/FROZEN_RESEARCH_M0.json")):
        data = json.loads(file.read_text("utf8"))
        signed = data.pop("report_sha256", None)
        if signed != hexdigest(canonical(data)) or data.get("schema") != SCHEMA:
            raise ResearchStreamError("OLDER_DAILY_RESEARCH_ARCHIVE_TAMPERED")
        data["report_sha256"] = signed
        if data.get("params_sha256") != params_sha or data.get("release_sha256") != release_sha:
            raise ResearchStreamError("VERSION_DRIFT_IN_RESEARCH_ARCHIVE")
        enc = file.parent / "SOURCE.enc"
        manifest = file.parent / "SOURCE.manifest.json"
        if not enc.is_file() or not manifest.is_file():
            raise ResearchStreamError("OLDER_SOURCE_CHAIN_NOT_PERSISTED")
        meta = json.loads(manifest.read_text("utf8"))
        if (hexdigest(enc.read_bytes()) != meta.get("ciphertext_sha256")
            or meta.get("proof", {}).get("final_chain_sha256") != data.get("source_chain_sha256")):
            raise ResearchStreamError("OLDER_SOURCE_CIPHER_AND_CHAIN_MISMATCH")
        for item in data["forecasts"]:
            h = item.get("forecast_sha256")
            payload = {k: v for k, v in item.items() if k != "forecast_sha256"}
            if hexdigest(canonical(payload)) != h:
                raise ResearchStreamError("OLDER_PREDICTION_TAMPERED")
            k = (item["league"], item["native_match_id_sha256"])
            if k in forecasts or item["params_sha256"] != params_sha:
                raise ResearchStreamError("DUPLICATE_OR_DIFFERENT_MODEL_FORECAST")
            forecasts[k] = item
        for item in data["settlements"]:
            h = item.get("settlement_sha256")
            if h != hexdigest(canonical({k: v for k, v in item.items() if k != "settlement_sha256"})):
                raise ResearchStreamError("OLDER_SETTLEMENT_TAMPERED")
            k = (item["league"], item["native_match_id_sha256"])
            if k in settlements or k not in forecasts:
                raise ResearchStreamError("DUPLICATE_OR_ORPHAN_SETTLEMENT")
            if item["forecast_sha256"] != forecasts[k]["forecast_sha256"]:
                raise ResearchStreamError("SETTLEMENT_FORECAST_IDENTITY_CHANGED")
            settlements[k] = item
    return forecasts, settlements


def settle_existing(previous_forecasts, previous_settlements, schedules, now,
                    observed_at, source_chain):
    out = []
    for key, pred in sorted(previous_forecasts.items()):
        if key in previous_settlements:
            continue
        country, digest_id = key
        actual = next((m for m in schedules[country] if match_hash(country, m["id"]) == digest_id), None)
        if actual is None or actual["status"] != "finished":
            continue
        if as_utc(actual["time_utc"]) + LAG >= now:
            continue
        if as_utc(pred["frozen_at_utc"]) >= as_utc(pred["kickoff_utc"]) - MIN_PREMATCH:
            raise ResearchStreamError("PREVIOUS_FORECAST_MISSED_90MIN_MARGIN")
        if (pred["home"] != actual["home_team"]["name"]
            or pred["away"] != actual["away_team"]["name"]):
            raise ResearchStreamError("SETTLEMENT_FIXTURE_IDENTITY_MISMATCH")
        gh, ga = actual["score_home"], actual["score_away"]
        target = "1" if gh > ga else "2" if ga > gh else "X"
        p = pred["p_1x2"]
        brier = math.fsum((p[k] - (1.0 if k == target else 0.0))**2 for k in ("1", "X", "2"))
        logloss = -math.log(max(p[target], 1e-15))
        record = {
            "schema": SCHEMA, "model_id": MODEL,
            "league": country, "native_match_id_sha256": digest_id,
            "forecast_sha256": pred["forecast_sha256"],
            "kickoff_utc": pred["kickoff_utc"],
            "result_observed_at_utc": observed_at, "settled_at_utc": utc(now),
            "source_chain_sha256": source_chain,
            "result_1x2": target, "score_home_90": gh, "score_away_90": ga,
            "brier_sum3": brier, "log_loss": logloss,
            "calibrated": False, "is_test_premier_league": False,
        }
        record["settlement_sha256"] = hexdigest(canonical(record))
        out.append(record)
    return out


def collect(*, base, api_key, public_pem, now=None, client_factory=None):
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() != timedelta(0):
        raise ResearchStreamError("UTC_CLOCK_REQUIRED")
    if not api_key:
        raise ResearchStreamError("EXISTING_PITCHAPI_KEY_MISSING")
    params, params_sha, release_sha = load_release()
    base = Path(base)
    target = base / now.date().isoformat()
    if target.exists():
        raise ResearchStreamError("IMMUTABLE_DAILY_RUN_ALREADY_EXISTS")
    old_forecasts, old_settlements = read_history(base, params_sha=params_sha,
                                                   release_sha=release_sha)
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory = PitchAPI
    client = client_factory(api_key=api_key)
    target.mkdir(parents=True, exist_ok=False)
    try:
        receipts = []; calls = 0
        def read(label, method, *args, **kwargs):
            nonlocal calls
            if calls >= CALL_CAP:
                raise ResearchStreamError("17_API_CALL_CEILING")
            calls += 1
            start = utc_now()
            try:
                result = to_plain(method(*args, **kwargs))
            except Exception as exc:
                raise ResearchStreamError("PITCHAPI_" + type(exc).__name__) from None
            completed = utc_now()
            if not isinstance(result, dict):
                raise ResearchStreamError("NON_DICT_PROVIDER_SOURCE")
            add_observation(receipts, resource=label, payload=result,
                            started=start, completed=completed)
            return result

        chosen = selected_catalog(read("pitchapi:catalog", client.leagues.list))
        schedules = {}; all_new = []; coverage = []
        for country, title, lid, this_n, old_n in chosen:
            current_payload = read("pitchapi:eight:current:" + country,
                                   client.leagues.matches, lid, season=CURRENT, status="all")
            old_payload = read("pitchapi:eight:previous:" + country,
                               client.leagues.matches, lid, season=PREVIOUS)
            current, previous = current_payload.get("matches"), old_payload.get("matches")
            verify_seasons(country, current, previous, this_n, old_n)
            schedules[country] = current
            # Independent receipts for each country contain all previous and current
            # season results; source is sealed, only hashes are exposed in public metadata.
            observed = receipts[-1]["completed_at_utc"]
            new, stat = new_forecasts(country, title, current, previous, as_utc(observed), params,
                                      params_sha, release_sha, receipts[-1]["chain_sha256"],
                                      observed, set(old_forecasts))
            all_new.extend(new)
            coverage.append({"country": country, "league": title,
                             "current_fixtures": len(current), "previous_fixtures": len(previous),
                             "new_frozen": len(new), **stat})
        if calls != CALL_CAP or len(receipts) != CALL_CAP:
            raise ResearchStreamError("INCOMPLETE_8_LEAGUE_SOURCE_CAPTURE")
        observation_end = receipts[-1]["completed_at_utc"]
        if as_utc(observation_end) > now:
            # Now is the model's frozen cutoff. Move forward (never backdate a capture).
            now = as_utc(observation_end)
        for item in all_new:
            if as_utc(item["frozen_at_utc"]) < as_utc(item["observed_at_utc"]):
                raise ResearchStreamError("MODEL_FREEZE_BACKDATED_BEFORE_SOURCE")
        # Settlements are based on the same newly observed native fixture states,
        # never historical TEST; only earlier genuinely frozen model predictions.
        settlements = settle_existing(old_forecasts, old_settlements, schedules, now,
                                       observation_end, receipts[-1]["chain_sha256"])
        sealed = seal(receipts, public_pem, target / "SOURCE.enc",
                      target / "SOURCE.manifest.json")
        report = {
            "schema": SCHEMA, "model_id": MODEL, "utc_day": target.name,
            "model_mode": "FITTED_720TRAIN_PARALLEL_RESEARCH_NOT_PRODUCTION",
            "params_sha256": params_sha, "release_sha256": release_sha,
            "train_matches": 720, "validation_matches": 374,
            "source_observation_start_utc": receipts[0]["started_at_utc"],
            "source_observation_end_utc": observation_end,
            "source_chain_sha256": sealed["proof"]["final_chain_sha256"],
            "encrypted_source_sha256": sealed["ciphertext_sha256"],
            "provider_calls": calls, "max_provider_calls": CALL_CAP,
            "leagues_checked": coverage,
            "forecasts": sorted(all_new, key=lambda f: (f["kickoff_utc"], f["league"], f["native_match_id_sha256"])),
            "settlements": sorted(settlements, key=lambda x: (x["kickoff_utc"], x["league"], x["native_match_id_sha256"])),
            "new_forecast_count": len(all_new), "new_settlement_count": len(settlements),
            "total_forecasts": len(old_forecasts) + len(all_new),
            "total_settled": len(old_settlements) + len(settlements),
            "first_100_cohort_eligible_for_calibration": False,
            "next_50_holdout_started": False,
            "calibration_not_auto_fit": True,
            "gate16": "PENDING",
            "original_model_unchanged": True,
            "original_PL_2026_27_TEST_touched": False,
            "provider_first_published_at_utc_proven": False,
            "not_a_full_121_plus_38_xg_feature_snapshot": True,
            "domain_transfer_validation_required": True,
        }
        report["report_sha256"] = hexdigest(canonical(report))
        (target / "FROZEN_RESEARCH_M0.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf8")
        return report
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="data/forecasts/m0_720train_8league")
    p.add_argument("--public-key", default="config/step11_archive_recipient_public.pem")
    args = p.parse_args()
    day = datetime.now(timezone.utc).date().isoformat()
    if (Path(args.base) / day / "FROZEN_RESEARCH_M0.json").exists():
        params, ps, rs = load_release()
        existing, settled = read_history(args.base, params_sha=ps, release_sha=rs)
        print(json.dumps({"status": "ALREADY_ARCHIVED", "forecasts": len(existing),
                          "settled": len(settled), "utc_day": day}))
        return
    result = collect(base=args.base, api_key=os.environ.get("PITCHAPI_API_KEY", ""),
                     public_pem=args.public_key)
    print(json.dumps({"status": "M0_720TRAIN_EIGHT_LEAGUE_RESEARCH_FROZEN",
                      "utc_day": result["utc_day"], "new": result["new_forecast_count"],
                      "settled": result["new_settlement_count"],
                      "total": result["total_forecasts"], "calls": result["provider_calls"],
                      "report_sha256": result["report_sha256"],
                      "test_touched": result["original_PL_2026_27_TEST_touched"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
