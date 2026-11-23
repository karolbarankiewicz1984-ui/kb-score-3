"""KB3 read-only post-FIT HOLDOUT50 and three-engine forward review.

No provider requests, writes to source DB, retraining, TEST, production or Champion.
The 50 post-FIT games are never reused to fit temperature or select a winner.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
# Match src/kb3_step17_engine_comparison.py::MIN_BLOCKS. Never
# advertise an interval merely because some weeks have elapsed.
STEP17_MIN_WEEK_BLOCKS = 8


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


def valid_paired_ci_evidence(paired):
    """All three 1X2 engines require actual ISO-week block-bootstrap CI data."""
    if not isinstance(paired, dict) or paired.get("common_n", 0) < 100:
        return False
    comparisons = paired.get("paired_deltas", {})
    if len(comparisons) != 3:
        return False
    for pair in comparisons.values():
        if pair.get("common_n") != paired["common_n"]:
            return False
        for metric in ("brier_sum3", "log_loss", "top1_accuracy"):
            block = pair.get("deltas", {}).get(metric, {})
            ci = block.get("ci95")
            if (block.get("week_blocks", 0) < STEP17_MIN_WEEK_BLOCKS
                    or block.get("status") != "PAIRED_ISO_WEEK_BOOTSTRAP"
                    or not isinstance(ci, list) or len(ci) != 2
                    or not all(type(v) in (int, float) and math.isfinite(v)
                               for v in ci)
                    or ci[0] > ci[1]):
                return False
    return True


def pending_settlement_review(db, receipt):
    """Reconcile *all* unclosed frozen matches with the last genuine receipt.

    Read-only: source update timestamps for postponed games are NOT in the
    receipt, so these rows are REVIEW_REQUIRED, never falsely settled.
    """
    decisions = receipt.get("settlement_decisions")
    need(isinstance(decisions, list), "SETTLEMENT_DECISIONS_MISSING")
    reason_counts = Counter(d["reason"] for d in decisions)
    need(dict(reason_counts) == receipt.get("settlement_reason_counts"),
         "SETTLEMENT_REASON_COUNTS_DRIFT")
    need(reason_counts["SETTLED_NEW"] == receipt.get("new_settlements"),
         "NEW_SETTLEMENT_COUNT_DRIFT")
    open_decisions = [d for d in decisions if d["reason"] != "SETTLED_NEW"]
    need(len(open_decisions) == receipt.get("not_yet_settled"),
         "OPEN_DECISIONS_COUNT_DRIFT")
    decision_index = {d["forecast_id"]: d for d in open_decisions}
    need(len(decision_index) == len(open_decisions), "DUPLICATE_PENDING_FORECAST")
    pending = db.execute("""SELECT f.id, f.league, f.native_match_id,
                    f.kickoff_utc, f.captured_at_utc, f.payload_json
          FROM forecasts f LEFT JOIN settlements s ON s.forecast_id=f.id
          WHERE s.forecast_id IS NULL ORDER BY f.kickoff_utc, f.id""").fetchall()
    need(len(pending) == len(open_decisions), "PENDING_DB_VS_RECEIPT_DRIFT")
    need(set(decision_index) == {r[0] for r in pending},
         "PENDING_IDS_VS_RECEIPT_DRIFT")
    by_reason = defaultdict(Counter)
    needs_kickoff_check = []
    missing_results = []
    immature = []
    for fid, league, native, kick, captured, raw in pending:
        d = decision_index[fid]
        frozen = json.loads(raw)
        need(d["league"] == league and d["native_match_id"] == native
             and league in LEAGUES, "PENDING_NATIVE_ID_OR_LEAGUE_DRIFT")
        need(frozen.get("forecast_sha256") == fid
             and sha({k: v for k, v in frozen.items()
                      if k != "forecast_sha256"}) == fid
             and frozen.get("league_country") == league
             and frozen.get("provider_match_id") == native
             and frozen.get("kickoff_utc") == kick
             and frozen.get("model_version") == MODEL,
             "PENDING_FROZEN_SOURCE_INTEGRITY_FAIL")
        lead = (utc(kick) - utc(captured)).total_seconds() / 60
        need(lead > 90, "PENDING_FORECAST_FROZEN_TOO_LATE")
        reason = d["reason"]
        by_reason[reason][league] += 1
        case = {"forecast_id": fid, "league": league,
                "native_match_id": native, "original_frozen_kickoff_utc": kick,
                "frozen_capture_utc": captured,
                "original_capture_lead_minutes": round(lead, 2)}
        if reason == "KICKOFF_CHANGED_REVIEW_REQUIRED":
            revised = d.get("provider_reported_kickoff_utc")
            if revised is not None:
                need(d.get("original_kickoff_utc") == kick
                     and d.get("original_forecast_capture_utc") == captured
                     and utc(revised) != utc(kick)
                     and abs((utc(revised)-utc(kick)).total_seconds()/60
                             - d["kickoff_delta_minutes"]) < 0.001
                     and d.get("manual_review_required") is True
                     and d.get("automatic_settlement_permitted") is False,
                     "PROVIDER_KICKOFF_REVIEW_RECEIPT_MISMATCH")
            needs_kickoff_check.append({**case,
                "state": "MANUAL_PROVIDER_ID_TIME_RECONCILIATION_REQUIRED",
                "provider_revised_kickoff_utc": revised,
                "provider_time_delta_minutes": (d.get("kickoff_delta_minutes")
                                                if revised is not None else None),
                "provider_home_id_matches_original": (
                    d.get("provider_home_id_matches_original")),
                "provider_away_id_matches_original": (
                    d.get("provider_away_id_matches_original")),
                "original_capture_before_earliest_90m_cutoff": (
                    d.get("original_capture_before_earliest_90m_cutoff")),
                "retrospective_result_injected": False,
                "automatic_settlement_allowed": False})
        elif reason == "PROVIDER_RESULT_MISSING":
            missing_results.append(case)
        elif reason == "RESULT_MATURITY_3H_NOT_REACHED":
            immature.append({**case, "earliest_original_maturity_utc":
                 (utc(kick) + timedelta(hours=3)).isoformat()})
        # Unknown reasons remain visible in the per-league counts, not waived.
    return {
        "source_receipt_run_utc": receipt["run_utc"],
        "frozen_not_yet_settled": len(pending),
        "pending_reason_counts": dict(sorted((k, v) for k, v in
                                             reason_counts.items()
                                             if k != "SETTLED_NEW")),
        "by_reason_and_league": {k: dict(sorted(v.items()))
                                for k, v in sorted(by_reason.items())},
        "kickoff_changed_review_cases": needs_kickoff_check,
        "provider_result_missing_cases": missing_results,
        "result_maturity_pending_cases": immature,
        "provider_revised_kickoff_not_proven_by_receipt": True,
        "read_only": True, "existing_forecasts_and_settlements_modified": False,
        "automatic_kickoff_override": False,
    }


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
        settlement_queue = pending_settlement_review(db, receipt)
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
            "pending_settlement_review": settlement_queue,
            "step17_exact_three_engine_paired": {
                "common_n": paired["common_n"], "independent_week_blocks": weeks,
                "scores": paired["scores"],
                "per_league": paired["per_league"],
                "minimum_independent_week_blocks_for_ci": STEP17_MIN_WEEK_BLOCKS,
                "missing_independent_week_blocks_for_ci": max(
                    0, STEP17_MIN_WEEK_BLOCKS-weeks),
                "confidence_intervals_ready": valid_paired_ci_evidence(paired),
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
    metric_block = lambda n, ci: {
        "week_blocks": n, "ci95": ci,
        "status": ("PAIRED_ISO_WEEK_BOOTSTRAP" if ci is not None
                   else "INSUFFICIENT_INDEPENDENT_WEEKS")}
    def paired_sample(n, ci):
        return {"common_n": 135, "paired_deltas": {
            p: {"common_n": 135, "deltas": {
                 m: metric_block(n, ci)
                 for m in ("brier_sum3", "log_loss", "top1_accuracy")}}
            for p in ("ELO_ONLY__vs__CATBOOST_NO_XG",
                      "ELO_ONLY__vs__M0_ELO_POISSON_720TRAIN",
                      "M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG")}}
    need(not valid_paired_ci_evidence(paired_sample(4, [-.01, .01])),
         "SELFTEST_FOUR_WEEKS_PREMATURE_CI")
    need(not valid_paired_ci_evidence(paired_sample(8, None)),
         "SELFTEST_NO_FAKE_CI_WITH_EIGHT_WEEKS")
    need(valid_paired_ci_evidence(paired_sample(8, [-.01, .01])),
         "SELFTEST_EIGHT_WEEKS_VALID_CI_NOT_RECOGNIZED")
    with sqlite3.connect(":memory:") as fake:
        fake.executescript("""CREATE TABLE forecasts(
              id TEXT, league TEXT, native_match_id TEXT, kickoff_utc TEXT,
              captured_at_utc TEXT, payload_json TEXT);
              CREATE TABLE settlements(forecast_id TEXT);""")
        need(bool(fake.execute("SELECT COUNT(*) FROM forecasts").fetchone()),
             "SELFTEST_PENDING_TABLE")
        test_receipt = {"settlement_decisions": [],
                        "settlement_reason_counts": {}, "new_settlements": 0,
                        "not_yet_settled": 0, "run_utc": "2026-11-23T00:00:00Z"}
        need(pending_settlement_review(fake, test_receipt)[
             "frozen_not_yet_settled"] == 0, "SELFTEST_EMPTY_PENDING")
        altered = dict(test_receipt, not_yet_settled=1)
        try:
            pending_settlement_review(fake, altered)
        except ValueError as exc:
            need(str(exc) == "OPEN_DECISIONS_COUNT_DRIFT",
                 "SELFTEST_FAIL_CLOSED_WRONG_REASON")
        else:
            need(False, "SELFTEST_OPEN_COUNT_MUST_FAIL_CLOSED")
        frozen = {"model_version": MODEL, "league_country": "POL",
                  "provider_match_id": "m_fixture",
                  "kickoff_utc": "2026-11-21T20:00:00Z"}
        fid = sha(frozen)
        frozen["forecast_sha256"] = fid
        fake.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?)",
                     (fid, "POL", "m_fixture", frozen["kickoff_utc"],
                      "2026-11-19T10:00:00Z", json.dumps(frozen)))
        reason = "KICKOFF_CHANGED_REVIEW_REQUIRED"
        drift = {"forecast_id": fid, "league": "POL",
                 "native_match_id": "m_fixture", "reason": reason,
                 "original_kickoff_utc": frozen["kickoff_utc"],
                 "provider_reported_kickoff_utc": "2026-11-21T21:00:00Z",
                 "kickoff_delta_minutes": 60.0,
                 "original_forecast_capture_utc": "2026-11-19T10:00:00Z",
                 "manual_review_required": True,
                 "automatic_settlement_permitted": False}
        with_one = dict(test_receipt,
                        settlement_decisions=[drift],
                        settlement_reason_counts={reason: 1},
                        not_yet_settled=1)
        report = pending_settlement_review(fake, with_one)
        need(report["frozen_not_yet_settled"] == 1 and
             report["kickoff_changed_review_cases"][0][
                 "provider_time_delta_minutes"] == 60 and
             report["automatic_kickoff_override"] is False,
             "SELFTEST_DRIFT_READONLY_QUEUE")
        need(fake.execute("SELECT COUNT(*) FROM settlements").fetchone()[0] == 0,
             "SELFTEST_MUST_NOT_SETTLE")
        drift_bad = dict(drift, kickoff_delta_minutes=0)
        invalid = dict(with_one, settlement_decisions=[drift_bad])
        try:
            pending_settlement_review(fake, invalid)
        except ValueError as exc:
            need(str(exc) == "PROVIDER_KICKOFF_REVIEW_RECEIPT_MISMATCH",
                 "SELFTEST_BAD_DELTA_WRONG_FAILURE")
        else:
            need(False, "SELFTEST_FABRICATED_DELTA_ACCEPTED")
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
               "m0_per_league": report["m0_per_league"],
               "m0_top1_confidence_bands": report["m0_top1_confidence_bands"],
               "three_engine": report["step17_exact_three_engine_paired"],
               "pending_settlement_review": {
                    "frozen_not_yet_settled": report["pending_settlement_review"][
                        "frozen_not_yet_settled"],
                    "pending_reason_counts": report["pending_settlement_review"][
                        "pending_reason_counts"],
                    "by_reason_and_league": report["pending_settlement_review"][
                        "by_reason_and_league"],
                    "kickoff_changed_review_cases": report["pending_settlement_review"][
                        "kickoff_changed_review_cases"]},
               "formal_gates": report["formal_gates"]}
    print("KB3_HOLDOUT_REAL_READONLY_AUDIT", json.dumps(
        summary, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
