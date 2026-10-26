"""Immutable step13 replay demonstration: SYNTHETIC ONLY, never real backtest."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from src.kb3_split import freeze_manifest, sha
from src.kb3_step13_replay import compare_synthetic_fold


def fixture(fid, ko, observed, label, role):
    return {
        "fixture_id": "SYN-MATCH-" + fid,
        "home_team_id": "SYN-TEAM-A",
        "away_team_id": "SYN-TEAM-B",
        "kickoff_utc": ko, "result_observed_at_utc": observed,
        "label_90m": label, "partition": role,
    }


def report():
    data = {"dataset_kind": "SYNTHETIC_REFERENCE_ONLY", "fixtures": [
        fixture("OLD", "2023-08-01T12:00:00Z", "2023-08-01T16:00:00Z", "H", "TRAIN"),
        fixture("RECENT", "2024-08-01T12:00:00Z", "2024-08-01T16:00:00Z", "A", "TRAIN"),
        fixture("VAL1", "2025-10-05T12:00:00Z", "2025-10-05T16:00:00Z", "H", "VALIDATION"),
        fixture("VAL2", "2025-10-06T12:00:00Z", "2025-10-06T16:00:00Z", "D", "VALIDATION"),
    ]}
    experiment = compare_synthetic_fold(
        data, fold=2, evaluation_asof_utc="2026-01-03T00:00:00Z")
    out = {
        "schema": "kb3-step13-replay-control-report-v0.2",
        "dataset": "100_PERCENT_SYNTHETIC_NO_PROVIDER_MATCHES",
        "purpose": "VERIFY_ORDER_OF_EVENTS_AND_INFORMATION_AVAILABILITY",
        "synthetic_source_sha256": sha(data),
        "comparison": experiment,
        "validation_fixture_count_synthetic": 2,
        "real_historical_matches_scored": 0,
        "real_historical_brier_available": False,
        "real_historical_log_loss_available": False,
        "model_fitted": False,
        "real_pit_proven": False,
        "historical_training_allowed": False,
        "gate13_pass": False,
        "conclusion": "REPLAY_TEMPORAL_UNIT_TESTS_ONLY_HISTORICAL_PIT_STILL_BLOCKED",
    }
    out["report_sha256"] = sha(out)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    result = report()
    print(freeze_manifest(result, Path(args.out)))
    print("STEP13_REPLAY_SYNTHETIC_ONLY", result["report_sha256"],
          "REAL_HISTORICAL_GAMES", result["real_historical_matches_scored"])


if __name__ == "__main__":
    main()
