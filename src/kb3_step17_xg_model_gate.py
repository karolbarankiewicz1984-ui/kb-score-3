"""KB3 Step17 CatBoost WITH xG — deterministic research-admission gate.

Never infer historical PIT from current retrieval of old sources. Never mix
FPL/Opta player-sum and PitchAPI team-shot expected_goals. Research training
is BLOCKED until matching model and time cohorts contain proven observations.
"""
from __future__ import annotations
import json
from pathlib import Path
from src.kb3_step16_m0_720_eight_forward import ROOT,hashobj,require

HISTORIC=ROOT/"data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_RESEARCH_SUMMARY_2026-10-29.json"
GATE=ROOT/"data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_ORIGINAL_M1_GATE_2026-10-29.json"
RELAXED=ROOT/"data/audits/STEP14_M1R_RELAXED_1140_48H_121x38_SUMMARY_2026-10-29.json"
BASE=ROOT/"data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json"
ENGINE="CATBOOST_WITH_XG"
STATUS="BLOCKED_NO_NATIVE_XG_TRAIN_VALIDATION_COHORT"

def actual_readiness(root=ROOT):
    root=Path(root)
    old=json.loads((root/HISTORIC.relative_to(ROOT)).read_text())
    gate=json.loads((root/GATE.relative_to(ROOT)).read_text())
    relaxed=json.loads((root/RELAXED.relative_to(ROOT)).read_text())
    reference=json.loads((root/BASE.relative_to(ROOT)).read_text())
    require(reference["training"]==720 and reference["validation"]==374,
            "STEP17_XG_CHAMPION_COHORT_CHANGED")
    require(reference.get("original_TEST_2026_27_never_requested") is True
            and gate.get("TEST_2026_27_examined") is False,
            "STEP17_XG_SEALED_TEST_DRIFT")
    require(old["TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5"]==40
            and old["original_380_VALIDATION_ALTERNATIVE_xG5_preserved"]==107
            and gate["source_alternative_FPL_xG_not_original_PitchAPI"] is True
            and relaxed["xg_same_provider_and_48h_coherence_not_automatically_certified"] is True,
            "STEP17_XG_HISTORIC_SOURCE_PROVENANCE_CHANGED")
    require(gate["original_121_plus_38_native_PIT_TRAIN"]==0
            and gate["original_121_plus_38_native_PIT_VALIDATION"]==0
            and gate["original_CatBoost_M1_training_allowed"] is False,
            "STEP17_XG_UNEXPECTED_HISTORIC_NATIVE_PIT_APPROVAL")
    # 40/760 and 107/380 are candidate population counts, not exact
    # intersection with 720/374 eligible native training/validation fixtures.
    report={"schema":"kb3-step17-catboost-native-xg-training-readiness-v1",
       "engine":ENGINE,"status":STATUS,"model_binary_generated":False,
       "model_fitted":False,"production_approved":False,
       "baseline_train_720":720,"baseline_valid_374":374,
       "historical_alternative_FPL_player_xg5_complete_TRAIN_760":40,
       "historical_alternative_FPL_player_xg5_complete_VALIDATION_380":107,
       "unknown_overlap_with_exact_720_train_and_374_valid":True,
       "native_PitchAPI_2023_25_asof_qualified_TRAIN":0,
       "native_PitchAPI_2023_25_asof_qualified_VALIDATION":0,
       "FPL_Opta_player_sum_is_native_pitchapi_team_xg":False,
       "alternative_xg_training_for_original_M1_allowed":False,
       "future_xg_last5_must_use_actual_last5_fixtures_not_last5_observed":True,
       "future_xg_never_uses_target_result":True,
       "native_xg_definition":"PitchAPI exact All-team expected_goals; per-shot expected_goals",
       "native_semantic_pair_max_delta":0.15,
       "legacy_model_CATBOOST_NO_XG_parameters_changed":False,
       "original_M0_720TRAIN_changed":False,
       "test_premier_league_2026_27_opened":False,
       "gate17":"PENDING",
       "next_valid_training_input":"Chronologically prior provider-native xG observed before target freeze, source-receipted, with strictly separated outcome labels and adequate TRAIN/VALIDATION coverage",
       "reason_blocked":"Insufficient, cross-provider and not native historically PIT-certified xG in original 720/374 cohort"}
    report["readiness_sha256"]=hashobj(report)
    return report
