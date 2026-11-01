"""Read-only step15 archive re-audit: NO API, model training or TEST reads.

Verification of original frozen 374 paired forecasts, 2 model hashes and
the archived scorecard. Results are NOT new empirical scores, new forecasts,
PIT certificates, or a replacement for the second provider-label audit.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from scripts.step15_independent_market_audit import _check_market

REL_REPORT = "data/audits/STEP15_ML_VS_M0_374_FULL_REPORT_20261029.json"
REL_SECOND = "data/audits/STEP15_INDEPENDENT_SECOND_SCORE_AUDIT_20261029.json"
REL_FROZEN = "data/forecasts/STEP15_374_PAIR_GOAL_PROBABILITIES_NO_LABELS_20261029.jsonl.gz"
MODELS = {
    "CATBOOST_GOALS_HOME_720.cbm": "models/research/STEP15_CATBOOST_GOALS_HOME_720_20261029.cbm",
    "CATBOOST_GOALS_AWAY_720.cbm": "models/research/STEP15_CATBOOST_GOALS_AWAY_720_20261029.cbm",
}
REPORT_SCHEMA = "kb3-step15-independent-ml-goals-catboost-poisson-720-374-v1"
ROOT = Path(__file__).resolve().parents[1]


class OfflineStep15Error(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise OfflineStep15Error(code)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root=ROOT):
    root = Path(root)
    report_path, second_path, frozen_path = (
        root / REL_REPORT, root / REL_SECOND, root / REL_FROZEN)
    report, second = _safe_json(report_path), _safe_json(second_path)
    require(report.get("schema") == REPORT_SCHEMA, "BAD_REPORT_SCHEMA")
    require(report.get("partition_train") == 720 and
            report.get("partition_validation") == 374 and
            report.get("all_binary_markets") == 22 and
            report.get("unique_markets_for_primary_aggregate") == 18,
            "HISTORICAL_PARTITION_OR_MARKET_DRIFT")
    require(report.get("features_train_only") == 85 and
            report.get("source_class") == "B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT" and
            report.get("historical_native_PIT_proven") is False and
            report.get("sealed_2026_27_test_accessed") is False and
            report.get("model_promoted") is False and
            report.get("val_labels_used_for_training_early_stopping_or_model_selection") is False,
            "RESEARCH_ISOLATION_DRIFT")
    require(second.get("status") == "PASS_INDEPENDENT_SCORE_AND_COHERENCE_VERIFICATION"
            and second.get("score_checks") == 132 and second.get("paired_fixtures") == 374
            and second.get("original_test_accessed") is False and
            second.get("production_promotion") is False,
            "INDEPENDENT_SECOND_AUDIT_NOT_FOUND")
    require(second.get("full_report_sha256") == sha256(report_path),
            "INDEPENDENT_SCORECARD_BYTES_CHANGED")
    require(second.get("frozen_sha256") == sha256(frozen_path)
            == report.get("frozen_prediction_sha256"),
            "FROZEN_FORECAST_BYTES_CHANGED")
    for short, rel in MODELS.items():
        require(sha256(root / rel) == report.get("saved_model_sha256", {}).get(short),
                "FROZEN_MODEL_BYTES_CHANGED_" + short)
    rows = [json.loads(line) for line in
            gzip.decompress(frozen_path.read_bytes()).decode("utf-8").splitlines()
            if line.strip()]
    require(len(rows) == 374 and
            len({str(r.get("fixture_id")) for r in rows}) == 374,
            "FROZEN_FIXTURES_NOT_374_UNIQUE")
    for row in rows:
        require(set(row) == {"fixture_id", "partition", "kickoff_utc", "m0", "ml"}
                and row["partition"] == "VALIDATION"
                and isinstance(row["fixture_id"], str) and bool(row["fixture_id"])
                and isinstance(row["kickoff_utc"], str) and
                row["kickoff_utc"].endswith("Z"),
                "LABEL_LEAK_OR_BAD_FORECAST_METADATA")
        _check_market(row["m0"])
        _check_market(row["ml"])
    markets = report.get("markets", {})
    require(isinstance(markets, dict) and len(markets) == 22,
            "NOT_22_REPORTED_MARKETS")
    unique = report["primary_macro_18_unique"]["events"]
    require(len(unique) == 18 and len(set(unique)) == 18 and
            set(unique) <= set(markets), "PRIMARY_MARKETS_NOT_18_UNIQUE")
    improvements = {"brier": 0, "log_loss": 0}
    for name, entry in markets.items():
        require(entry.get("n") == 374, "REPORTED_N_CHANGED_"+name)
        for metric in improvements:
            h, m = entry["m0"][metric], entry["ml"][metric]
            require(type(h) in (float, int) and type(m) in (float, int)
                    and math.isfinite(h) and math.isfinite(m) and h >= 0 and m >= 0,
                    "INVALID_REPORTED_SCORE_" + name)
            require(abs((m-h)-entry["delta_ml_minus_m0"][metric]["delta_mean"]) < 1e-11,
                    "REPORTED_DELTA_CHANGED_"+name)
            improvements[metric] += int(m < h)
    for metric in improvements:
        require(improvements[metric] ==
                report["counts"]["ml_" + ("brier" if metric == "brier" else "log_loss") +
                                 "_improved_22"], "IMPROVEMENT_COUNT_CHANGED")
        for model in ("m0", "ml"):
            mean = math.fsum(markets[name][model][metric] for name in unique) / 18
            require(abs(mean-report["primary_macro_18_unique"][model][metric]) < 1e-11,
                    "MACRO_18_SCORE_CHANGED")
    return {
        "status": "PASS_OFFLINE_ARCHIVE_INTEGRITY_AND_POISSON_JOINT",
        "paired_fixtures": 374, "market_contracts": 22,
        "model_by_fixture_joint_checks": 748, "unique_primary_events": 18,
        "m0_wins_brier_markets": 22-improvements["brier"],
        "m0_wins_log_loss_markets": 22-improvements["log_loss"],
        "independently_verified_scorecard": "PRIOR_AUDIT_MATCHED_HASH_NOT_NEW_SCORE_REPLAY",
        "report_sha256": sha256(report_path),
        "frozen_sha256": sha256(frozen_path),
        "source_type": "HISTORICAL_RECONSTRUCTED_RESEARCH",
        "provider_api_calls": 0, "test_season_accessed": False,
        "model_fit_or_calibration": False, "production_promotion": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
