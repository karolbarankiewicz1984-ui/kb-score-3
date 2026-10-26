"""Step13: frozen synthetic TRAIN-only Poisson fit proof and real PIT gate state."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from src.kb3_split import freeze_manifest, sha
from src.kb3_step13_poisson_train import (
    fit_synthetic_poisson_train, forecast_from_synthetic_fit,
)


def reference_fixture(i):
    return {
        "fixture_id":f"SYN-MATCH-TRAIN-{i:02d}",
        "home_team_id":f"SYN-TEAM-{i%4:02d}",
        "away_team_id":f"SYN-TEAM-{(i+1)%4:02d}",
        "kickoff_utc":f"2024-10-{i+1:02d}T15:00:00Z",
        "feature_cutoff_utc":f"2024-10-{i+1:02d}T12:00:00Z",
        "result_observed_at_utc":f"2024-10-{i+1:02d}T19:00:00Z",
        "home_elo_before_kickoff":1450.0+(i%4)*40,
        "away_elo_before_kickoff":1500.0+(i%3)*20,
        "goals_home_90":i%3+1,
        "goals_away_90":i%2,
        "partition":"TRAIN",
        "source_type":"SYNTHETIC_REFERENCE_ONLY",
    }


def generate(root):
    gap_path=root/"data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json"
    gap=json.loads(gap_path.read_text(encoding="utf8"))
    if (gap["report_sha256"] != sha({
            k:v for k,v in gap.items() if k!="report_sha256"})
            or gap["real_fixture_count"]!=1520
            or gap["eligible_training_examples"]!=0 or
            gap["training_allowed"] is not False):
        raise ValueError("STEP13_UNTRUSTED_OR_CHANGED_REAL_PIT_GAP")
    candidate=fit_synthetic_poisson_train(
        [reference_fixture(i) for i in range(12)],
        freeze_utc="2025-10-01T00:00:00Z")
    demo=forecast_from_synthetic_fit(candidate,1500,1500)
    outcome={
        "schema":"kb3-step13-poisson-fit-readiness-v0.3",
        "reference_train_data_kind":"SYNTHETIC_REFERENCE_ONLY",
        "frozen_candidate":candidate,
        "synthetic_equal_elo_forecast":demo["p_1x2"],
        "synthetic_parameters_status":demo["parameters_status"],
        "real_step12_gap_report_sha256":gap["report_sha256"],
        "real_step12_schedule_total":gap["real_fixture_count"],
        "real_pit_eligible_training_count":gap["eligible_training_examples"],
        "real_fitted_matches":0,
        "historical_m0_logloss_available":False,
        "historical_m0_brier_available":False,
        "historical_calibration_available":False,
        "parameter_candidate_for_production":False,
        "test_labels_accessed":False,
        "model_promoted":False,
        "gate13_pass":False,
        "training_allowed":False,
        "next":"INDEPENDENT_REAL_SOURCE_PIT_OR_SEPARATELY_APPROVED_RETROSPECTIVE_RESEARCH_CONTRACT_REQUIRED",
    }
    outcome["report_sha256"]=sha(outcome)
    return outcome


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    result=generate(root)
    print(freeze_manifest(result,args.output))
    print("STEP13_SYNTHETIC_TRAIN_FORMULA_PASS_REAL_TRAIN_0",
          result["report_sha256"])


if __name__=="__main__":
    main()
