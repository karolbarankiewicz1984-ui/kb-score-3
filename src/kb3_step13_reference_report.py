"""Generate an immutable SYNTHETIC ONLY reference mathematics report for step13.

Does not access any fixture database, archived labels, Odds or PitchAPI.
Report cannot be called a historical test and cannot pass GATE13.
"""
from __future__ import annotations
from dataclasses import asdict
import argparse
from pathlib import Path

from src.kb3_split import freeze_manifest, sha
from src.kb3_step13_baseline import BaselineParameters, forecast, update_elo
from src.kb3_step13_reference_metrics import score_synthetic_reference


def reference_report():
    cfg = BaselineParameters()
    examples = [
        ("SYNTHETIC_TEAM_A", "SYNTHETIC_TEAM_B", 1500.0, 1500.0, "H"),
        ("SYNTHETIC_TEAM_C", "SYNTHETIC_TEAM_D", 1600.0, 1500.0, "D"),
        ("SYNTHETIC_TEAM_E", "SYNTHETIC_TEAM_F", 1400.0, 1600.0, "A"),
    ]
    forecasts=[]
    eval_rows=[]
    for h_name,a_name,h_rating,a_rating,demo_result in examples:
        f=forecast(h_rating,a_rating,cfg)
        forecasts.append({
            "illustrative_home_team":h_name,
            "illustrative_away_team":a_name,
            "forecast":f,
            "synthetic_assumed_label_for_formula_check_only":demo_result,
        })
        eval_rows.append({"probabilities":f["p_1x2"],"label":demo_result})
    metrics=score_synthetic_reference(
        eval_rows,mode="SYNTHETIC_REFERENCE_ONLY")
    out={
        "schema":"kb3-step13-m0-reference-v0.1",
        "data_version":"NO_REAL_MATCH_DATA_SYNTHETIC_REFERENCE_ONLY",
        "evaluation_version":"SUM3_BRIER_MULTICLASS_LOGLOSS_TOP1_ECE_5BIN_V1",
        "engine":"KB3_ELO_POISSON_M0_V0_1",
        "default_parameters_status":"ILLUSTRATIVE_NOT_FITTED",
        "default_parameters":asdict(cfg),
        "mathematical_reference_forecasts":forecasts,
        "illustrative_elo_after_home_win":update_elo(1500.0,1500.0,"H",cfg),
        "synthetic_metric_formula_check":metrics,
        "is_real_historical_backtest":False,
        "historical_sample_size":0,
        "trained_on_historical_data":False,
        "historical_metrics_available":False,
        "gate13_pass":False,
        "gate13_reason":"REFERENCE_ENGINE_TESTED_BUT_REAL_HISTORICAL_TEST_AND_METRICS_REQUIRED",
        "training_allowed":False,
        "dependencies":"Step12 split methodology PASS; real historical PIT not certified",
    }
    out["report_sha256"]=sha(out)
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    r=reference_report()
    print(freeze_manifest(r,Path(args.output)))
    print("STEP13_M0_REFERENCE_ONLY_NO_HISTORICAL_METRICS",
          r["report_sha256"])
    for row in r["mathematical_reference_forecasts"]:
        print(row["illustrative_home_team"],
              row["illustrative_away_team"],
              row["forecast"]["p_1x2"])


if __name__=="__main__":
    main()
