"""KB3 read-only post-FIT HOLDOUT50 and three-engine forward review.

No provider requests, writes to source DB, retraining, TEST, production or Champion.
The 50 post-FIT games are never reused to fit temperature or select a winner.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/forward_m0_720_eight/kb3_forward_eight.sqlite"
RECEIPTS = ROOT / "data/pit_sidecar/m0_720_eight"
PIT_AUDITS = ROOT / "data/audits"
MODEL = "M0_ELO_POISSON_RESEARCH_720TRAIN_V1"
LABELS = ("1", "X", "2")
LEAGUES = frozenset(("BEL", "ESP", "FRA", "GER", "ITA", "NED", "POL", "TUR"))
EPS = 1e-15


def need(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc(stamp):
    d = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    need(d.tzinfo is not None and d.utcoffset() == timedelta(0), "UTC_REQUIRED")
    return d


def checked(p):
    need(isinstance(p, dict) and set(p) == set(LABELS), "CLASS_KEYS_CHANGED")
    need(all(type(p[k]) in (int, float) and math.isfinite(p[k]) and
             0 <= p[k] <= 1 for k in LABELS), "INVALID_PROBABILITY")
    need(abs(sum(p.values()) - 1) <= 1e-8, "PROBABILITY_SUM")
    return p


def rescale(p, temperature):
    need(type(temperature) in (int, float) and 0.1 <= temperature <= 10,
         "BAD_TEMPERATURE")
    weights = [math.log(max(p[k], EPS)) / temperature for k in LABELS]
    hi = max(weights)
    q = [math.exp(x-hi) for x in weights]
    return dict(zip(LABELS, (x / sum(q) for x in q)))


def metrics(rows):
    if not rows:
        return None
    n = len(rows)
    hit = 0
    brier = 0.0
    logloss = 0.0
    bins = [[0, 0.0, 0] for _ in range(10)]
    for p, y in rows:
        checked(p)
        need(y in LABELS, "RESULT_LABEL_INVALID")
        winner = max(LABELS, key=p.get)
        won = int(winner == y)
        hit += won
        brier += sum((p[k] - int(k == y))**2 for k in LABELS)
        logloss -= math.log(max(p[y], EPS))
        b = bins[min(9, int(p[winner] * 10))]
        b[0] += 1
        b[1] += p[winner]
        b[2] += won
    reliability = [{"bin": i, "count": t[0], "mean_confidence": t[1] / t[0],
                    "observed_top1_accuracy": t[2] / t[0]}
                   for i, t in enumerate(bins) if t[0]]
    return {"n": n, "top1_correct": hit, "top1_accuracy": hit/n,
            "brier_sum3": brier/n, "log_loss": logloss/n,
            "top1_ece_10bins": sum(t["count"]/n *
                abs(t["mean_confidence"] - t["observed_top1_accuracy"])
                for t in reliability)}


def bands(rows):
    limits = [("under40", 0, 0.4), ("40-50", 0.4, 0.5),
              ("50-60", 0.5, 0.6), ("60-70", 0.6, 0.7),
              ("70-100", 0.7, 1.00000001)]
    output = {}
    for title, low, high in limits:
        part = [(p, y) for p, y in rows
                if low <= max(checked(p).values()) < high]
        if not part:
            output[title] = {"n": 0}
            continue
        output[title] = {"n": len(part), "observed_accuracy": metrics(part)["top1_accuracy"],
                         "mean_top1_probability":
                             sum(max(p.values()) for p, _ in part)/len(part)}
    return output


def source_rows(db):
    rows = db.execute("""SELECT f.id, f.league, f.native_match_id, f.payload_json,
      f.kickoff_utc, f.captured_at_utc, s.outcome, s.observed_utc,
      p.github_server_event_utc
      FROM forecasts f
      JOIN settlements s ON s.forecast_id=f.id
      JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
      WHERE f.model=? ORDER BY f.kickoff_utc, f.id""", (MODEL,)).fetchall()
    output = {}
    fixtures = set()
    for r in rows:
        fid, league, native, raw, kick, capture, result, settled, host = r
        need(league in LEAGUES and (league, native) not in fixtures, "FIXTURE_DRIFT")
        fixtures.add((league, native))
        f = json.loads(raw)
        need(f.get("model_version") == MODEL and f.get("league_country") == league
             and f.get("provider_match_id") == native and f.get("phase") == "EARLY"
             and f.get("forecast_sha256") == fid and
             sha({k: v for k, v in f.items() if k != "forecast_sha256"}) == fid,
             "FORECAST_HASH_OR_SCOPE_DRIFT")
        need(utc(capture) <= utc(host) <= utc(kick)-timedelta(minutes=90)
             and utc(settled) >= utc(kick)+timedelta(hours=3),
             "FREEZE_OR_SETTLEMENT_CLOCK_NOT_VERIFIED")
        output[fid] = {"league": league, "kick": kick, "captured": capture,
                       "settled": settled, "p": checked(f["p_1x2"]), "y": result}
    return output


def latest_receipt():
    files = sorted(RECEIPTS.glob("*/settle-*/RECEIPT.json"))
    need(bool(files), "M0_RECEIPT_MISSING")
    return files[-1], json.loads(files[-1].read_text(encoding="utf-8"))


def review(root=ROOT):
    need(DB.is_file(), "SQLITE_NOT_FOUND")
    uri = DB.resolve().as_uri()+"?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        need(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
             "SQLITE_INTEGRITY_FAIL")
        need(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLITE_FOREIGN_KEYS")
        fits = db.execute("""SELECT candidate_sha256, fitted_at_utc, temperature, payload_json,
                             production_approved FROM m0720_calibrators""").fetchall()
        reviews = db.execute("""SELECT review_sha256, candidate_sha256,
              holdout_n, raw_log_loss, calibrated_log_loss, raw_brier_sum3,
              calibrated_brier_sum3, payload_json, production_approved
              FROM m0720_holdout_reviews""").fetchall()
        need(len(fits) == len(reviews) == 1, "EXPECTED_EXACTLY_ONE_FIT_AND_REVIEW")
        fit = fits[0]
        h = reviews[0]
        fit_body = json.loads(fit[3])
        h_body = json.loads(h[7])
        need(fit[4] == h[8] == 0, "PRODUCTION_REMAINS_OFF")
        need(sha(fit_body) == fit[0] == h[1]
             and sha(h_body) == h[0] and
             h_body["candidate_sha256"] == fit[0], "IMMUTABLE_HASH_CHANGED")
        fit_ids = fit_body["training_forecast_ids"]
        holdout_ids = h_body["holdout_forecast_ids"]
        need(len(fit_ids) == len(set(fit_ids)) == 100 and
             len(holdout_ids) == len(set(holdout_ids)) == h[2] == 50 and
             not set(fit_ids).intersection(holdout_ids) and
             sha(fit_ids) == fit_body["training_ids_sha256"] and
             sha(holdout_ids) == h_body["holdout_ids_sha256"], "COHORT_OR_FIT_LEAKAGE")
        rows = source_rows(db)
        need(all(x in rows for x in holdout_ids), "HOLDOUT_ROW_OR_HOST_PROOF_MISSING")
        for fid in holdout_ids:
            row = rows[fid]
            need(utc(row["captured"]) > utc(fit[1]) and
                 utc(row["kick"]) > utc(fit[1]), "HOLDOUT_CREATED_BEFORE_FIT")
        sample = [rows[fid] for fid in holdout_ids]
        raw_rows = [(x["p"], x["y"]) for x in sample]
        post_rows = [(rescale(x["p"], fit[2]), x["y"]) for x in sample]
        raw = metrics(raw_rows)
        calibrated = metrics(post_rows)
        for name, calc, db_value, saved in [
            ("raw_ll", raw["log_loss"], h[3], h_body["holdout_raw"]["log_loss"]),
            ("post_ll", calibrated["log_loss"], h[4], h_body["holdout_calibrated"]["log_loss"]),
            ("raw_brier", raw["brier_sum3"], h[5], h_body["holdout_raw"]["brier_sum3"]),
            ("post_brier", calibrated["brier_sum3"], h[6], h_body["holdout_calibrated"]["brier_sum3"])]:
            need(abs(calc-db_value) < 1e-10 and abs(calc-saved) < 1e-10,
                 "HOLDOUT_METRIC_DRIFT_" + name)
        all_rows = list(rows.values())
        by_league = defaultdict(list)
        for x in all_rows:
            by_league[x["league"]].append((x["p"], x["y"]))
        receipt_path, receipt = latest_receipt()
        need(len(all_rows) == receipt["calibration_readiness"]["eligible_settled_unique"],
             "RECEIPT_VS_DB_COHORT_DRIFT")
        paired = receipt["step17_paired_same_fixture_readiness"]["exact_three_engine_comparison"]
        need(paired["common_n"] > 0 and
             all(paired["scores"][key]["n"] == paired["common_n"]
                 for key in ("M0_ELO_POISSON_720TRAIN", "CATBOOST_NO_XG", "ELO_ONLY")),
             "STEP17_SAME_GAME_COMPARISON_DRIFT")
        weeks = paired["paired_deltas"]["M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"][
            "deltas"]["brier_sum3"]["week_blocks"]
        latest_pit = sorted(PIT_AUDITS.glob("STEP14_INDEPENDENT_RECHECK_*.json"))[-1]
        pit = json.loads(latest_pit.read_text(encoding="utf-8"))
        result = {
            "schema": "kb3-readonly-holdout-weekly-research-v1",
            "source_receipt": str(receipt_path.relative_to(ROOT)),
            "source_holdout_review_sha256": h[0],
            "source_calibrator_sha256": fit[0],
            "source_pit_audit": str(latest_pit.relative_to(ROOT)),
            "research_only": True,
            "production_approved": False,
            "protected_eng_test_read": False,
            "holdout": {
                "fit_n": 100, "holdout_n": 50,
                "additional_post_fit_settled": receipt["calibration_readiness"][
                    "post_fit_newly_created_settled_verified"],
                "fit_temperature": fit[2], "raw": raw, "calibrated": calibrated,
                "calibrated_minus_raw_log_loss": calibrated["log_loss"]-raw["log_loss"],
                "calibrated_minus_raw_brier_sum3": calibrated["brier_sum3"]-raw["brier_sum3"],
                "leakage_checks": "PASS",
                "report_saved_immutably": True
            },
            "m0_overall": metrics([(x["p"], x["y"]) for x in all_rows]),
            "m0_per_league": {k: metrics(v) for k, v in sorted(by_league.items())},
            "m0_top1_confidence_bands": bands([(x["p"], x["y"]) for x in all_rows]),
            "step17_exact_three_engine_paired": {
                "common_n": paired["common_n"], "independent_week_blocks": weeks,
                "scores": paired["scores"],
                "confidence_intervals_ready": weeks >= 4,
                "winner_selected": False
            },
            "history_pit": {
                "original_train_certified": pit["original_historical_pit_train_certified"],
                "original_validation_certified": pit["original_historical_pit_validation_certified"],
                "original_pitchapi_first_xg_publication_proven":
                    pit["original_pitchapi_team_xg_first_publication_proven"],
                "formal_159_field_no_leakage_pass": pit["independent_159_field_no_leakage_pass"],
                "gate14": pit["gate14"]
            },
            "formal_gates": {"gate14": pit["gate14"],
                             "gate16": receipt["gate16"],
                             "gate17": receipt["step17_paired_same_fixture_readiness"]["gate17"]},
            "no_auto_champion": True,
            "recommendation": "RESEARCH_CONTINUE_NO_PROMOTION"
        }
    return result


def self_test():
    p = {"1": .6, "X": .3, "2": .1}
    need(abs(sum(rescale(p, 0.7).values())-1) < 1e-12, "SELFTEST_NORMALIZATION")
    need(rescale(p, 1.0)["1"] > .599999, "SELFTEST_NEUTRAL")
    need(metrics([(p, "1")])["top1_accuracy"] == 1, "SELFTEST_SCORE")
    need(bands([(p, "1")])["60-70"]["n"] == 1, "SELFTEST_BAND")
    need(sha(["a"]) == hashlib.sha256(b'["a"]').hexdigest(), "SELFTEST_HASH")
    print("KB3_HOLDOUT_READONLY_SELFTEST_PASS")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--self-test", action="store_true")
    a.add_argument("--output", type=Path)
    x = a.parse_args()
    if x.self_test:
        self_test()
        return
    need(x.output is not None, "OUTPUT_REQUIRED")
    report = review()
    x.output.parent.mkdir(parents=True, exist_ok=True)
    with x.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")
    summary = {"holdout": report["holdout"], "m0_overall": report["m0_overall"],
               "three_engine": report["step17_exact_three_engine_paired"],
               "formal_gates": report["formal_gates"]}
    print("KB3_HOLDOUT_REAL_READONLY_AUDIT", json.dumps(
        summary, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
