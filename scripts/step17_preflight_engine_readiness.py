"""Step17 start preflight: read existing REAL research results; no new TEST/API.
This reports known historical 374 scores and missing fair-comparison engines;
it cannot synthesize row-level predictions, confidence intervals or victories.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from src.kb3_step17_engine_comparison import ENGINES,hash_json

ROOT=Path(__file__).resolve().parents[1]
VALID=ROOT/"data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json"
STEP15=ROOT/"data/audits/STEP15_ML_VS_M0_374_FULL_REPORT_20261029.json"
FORWARD=ROOT/"data/pit_sidecar/m0_720_eight/2026-10-29/settle-204838237706/RECEIPT.json"
OUTPUT=ROOT/"data/audits/STEP17_PREP_ENGINE_COMPARISON_2026-10-29.json"

def make_report(validation,goal,live):
    assert validation["training"]==720 and validation["validation"]==374
    assert validation["original_TEST_2026_27_never_requested"] is True
    assert validation["m0_and_m1r_validation_fixture_population_exact_same"] is True
    assert validation["future_actual_PIT_certified"] is False
    assert goal["partition_validation"]==374 and goal["features_train_only"]==85
    assert goal["source_class"]=="B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT"
    assert live["model_version"]=="M0_ELO_POISSON_RESEARCH_720TRAIN_V1"
    assert live["calibration_readiness"]["eligible_settled_unique"]==0
    a=validation["m0_matched_720_train_reference_poisson_validation"]
    b=validation["catboost_m1r_base_validation"]
    assert a["n"]==374 and b["n"]==374
    assert a["log_loss"]<b["log_loss"] and a["brier_multiclass_sum3"]<b["brier_multiclass_sum3"]
    historical={
      "evaluation_domain":"HISTORICAL_RECONSTRUCTED_RESEARCH",
      "n_same_fixture_validation":374,"n_training":720,
      "model_versions_720_train_fixed":True,
      "features_in_catboost_no_xg":85,
      "m0_elo_poisson":{"brier_sum3":a["brier_multiclass_sum3"],
                       "log_loss":a["log_loss"],"top1_accuracy":a["top1_accuracy"],
                       "top1_ece_5_bins":a["top1_ece_5_bins"]},
      "catboost_no_xg":{"brier_sum3":b["brier_multiclass_sum3"],
                        "log_loss":b["log_loss"],"top1_accuracy":b["top1_accuracy"],
                        "top1_ece_5_bins":b["top1_ece_5_bins"]},
      "ml_minus_m0":{"brier_sum3":b["brier_multiclass_sum3"]-a["brier_multiclass_sum3"],
                     "log_loss":b["log_loss"]-a["log_loss"]},
      "historical_native_provider_PIT_certified":False,
      "repeat_validation_tuning_allowed":False,
      "recomputed_paired_cluster_ci":False,
      "historical_data_not_eligible_to_close_step16":True,
      "not_proof_of_8_league_forward_predictive_success":True}
    readiness={
     "ELO_ONLY":"SPEC_DEFINED_NO_SAME_GAME_FROZEN_PROBS",
     "M0_ELO_POISSON_720TRAIN":"HISTORICAL_374_AND_FORWARD_73_UNSETTLED",
     "CATBOOST_NO_XG":"HISTORICAL_374_ONLY_NOT_LIVE_8_LEAGUE",
     "CATBOOST_WITH_XG":"MISSING_LIVE_HISTORIC_PIT_VALID_XG_AND_MODEL",
     "ENSEMBLE":"MISSING_FROZEN_COMPONENTS_AND_TRAIN_ONLY_WEIGHTS"}
    assert set(readiness)==set(ENGINES)
    result={"schema":"kb3-step17-preparation-live-historical-readiness-v1",
       "step":17,"status":"IN_PROGRESS_PREPARATION_ONLY",
       "predecessor_gate16":"PENDING",
       "step17_gate":"PENDING_DEPENDENCY_STEP16",
       "ready_engines":readiness,
       "historical_720train_374val_reference":historical,
       "independent_8_league_forward_m0":{
         "frozen_predictions":live["calibration_readiness"]["git_server_push_verified_forecasts"],
         "settled_predictions":live["calibration_readiness"]["settled_total"],
         "eligible_settled_predictions":0,
         "other_engines_same_fixtures_frozen_and_settled":False},
       "comparison_protocol":"same_fixtures_same_horizon_same_market_1X2_then_other_markets",
       "paired_bootstrap_unit":"ISO_WEEK_KICKOFF",
       "missing_data_penalty":"explicit_available_and_missing_unique_fixture_counts",
       "no_winner_auto_selected":True,"production_approval":False,
       "original_premier_league_2026_27_test_touched":False,
       "extra_api_cost_pln":0,"data_origin":"EXISTING_PRIVATE_GITHUB_AUDITS"}
    result["sha256"]=hash_json(result)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default=str(OUTPUT))
    args=p.parse_args()
    read=lambda path:json.loads(path.read_text(encoding="utf-8"))
    result=make_report(read(VALID),read(STEP15),read(FORWARD))
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        assert read(output)==result,"STEP17_IMMUTABLE_PREFLIGHT_CHANGED"
        print("STEP17_PREFLIGHT_ALREADY_SAVED_IDENTICAL")
        return
    with output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,sort_keys=True);f.write("\n")
    print("STEP17_PREPARATION",result["status"],"N",result["historical_720train_374val_reference"]["n_same_fixture_validation"])
    print("STEP17_SHA256",result["sha256"])

if __name__=="__main__":main()
