"""Trusted-local ONLY: decrypt pinned PitchAPI archive and run Step13 research.

Invocation requires owner's private RSA key on their own trusted computer.
Do NOT put key in GitHub/Actions, logs, chat, or shared Drive. No network.
Plaintext receipts are only in process memory; no fixture/target record is
printed, committed, or written in the aggregate report.

The output is research, NOT an historical prematch PIT validation, approved
production training, betting picks or Step13 formal GATE PASS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from src.kb3_split import freeze_manifest, sha
from src.kb3_step13_fold_replay import real_schedule_probe
from src.kb3_pitch_uefa_evidence import restore
from src.kb3_pitch_multiseason_history import historical_season_history
from src.kb3_step13_retrospective import POLICY, retrospective_research

HIST_CUTOFF_UTC = "2026-10-26T23:59:00Z"


def research_local(*,cipher_path,manifest_path,private_key_path,root):
    root=Path(root)
    summary=json.loads((root/"data/audits/STEP11_PITCH_MULTISEASON_ELO_REAL_2026-10-26.json").read_text())
    original=root/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
    dual=root/"data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json"
    safe_view=json.loads(original.read_text())
    window_plan=json.loads(dual.read_text())
    permitted=real_schedule_probe(safe_view,window_plan)
    if permitted["real_fixture_count"]!=1520 or permitted["asof_training_eligibility"]!="BLOCKED_0_OF_1520":
        raise ValueError("STEP13_SOURCE_SPLIT_OR_REAL_GATE_CHANGED")
    blob=Path(cipher_path).read_bytes()
    if (hashlib.sha256(blob).hexdigest()!=summary["history"]["cipher_sha256"]
            or len(blob)>20_000_000):
        raise ValueError("STEP13_CIPHER_NOT_PINNED")
    restored=restore(cipher_path,manifest_path,private_key_path,
                     include_receipts=True)
    if not restored["validated"] or restored["proof"]["final_chain_sha256"]!=summary["history"]["chain_sha256"]:
        raise ValueError("STEP13_HISTORIC_CHAIN_NOT_PINNED")
    archived, provenance=historical_season_history(
        restored["receipts"],cutoff_utc=HIST_CUTOFF_UTC)
    if (len(archived)!=1140 or provenance["training_allowed"] is not False
            or provenance["historical_provider_pit_certified"] is not False):
        raise ValueError("STEP13_RETROSPECTIVE_SOURCE_NOT_ISOLATED")
    # Fixed official split, including kickoff, must match every historical ID.
    safe={v["fixture_id"]:v for v in safe_view["fixtures"]}
    matched=[]
    for r in archived:
        check=safe.get(r["fixture_id"])
        if check is None or check["kickoff_utc"]!=r["kickoff_utc"]:
            raise ValueError("STEP13_NATIVE_HISTORY_AND_SAFE_SPLIT_MISMATCH")
        if check["partition"] not in ("TRAIN","VALIDATION"):
            raise ValueError("STEP13_RESEARCH_TEST_PROTECTED")
        matched.append({
            "fixture_id":r["fixture_id"],
            "home_team_id":r["home_team_id"],
            "away_team_id":r["away_team_id"],
            "kickoff_utc":r["kickoff_utc"],
            "goals_home_90":r["goals_home_90"],
            "goals_away_90":r["goals_away_90"],
        })
    if ({r["fixture_id"] for r in matched} !=
            {k for k,v in safe.items() if v["partition"] in ("TRAIN","VALIDATION")}):
        raise ValueError("STEP13_COMPLETE_HISTORICAL_TRAIN_VALIDATION_REQUIRED")
    study=retrospective_research(matched,policy=POLICY)
    if study["train_partition_rows"]!=760 or study["validation_partition_rows"]!=380:
        raise ValueError("STEP13_RESEARCH_EXPECTED_PARTITION_COUNTS")
    if len(study["folds"])!=4 or [f["validation_count"] for f in study["folds"]] != [60,126,123,71]:
        raise ValueError("STEP13_RESEARCH_FOLD_COUNTS_DIFFER")
    study["real_historical_research_parameters_fitted"]=True
    study["original_source_cipher_sha256"]=summary["history"]["cipher_sha256"]
    study["original_source_chain_sha256"]=summary["history"]["chain_sha256"]
    study["original_source_observed_utc"]=summary["history"]["historical_archive_observed_last_utc"]
    study["split_safe_projection_sha256"]=safe_view["projection_sha256"]
    study["split_dual_window_sha256"]=permitted["dual_window_sha256"]
    study["research_input_authority"]="OWNER_LOCAL_DECRYPT_PINNED_REAL_PITCHAPI_ARCHIVE"
    study["does_not_certify_2023_2026_prematch_availability"]=True
    study["actual_historical_pit_pass"]=False
    study["no_provider_requests"]=True
    study["no_betting_recommendations"]=True
    study["historical_production_training_allowed"]=False
    study["gate13_pass"]=False
    study["report_sha256"]=sha(study)
    return study


def main():
    p=argparse.ArgumentParser()
    for opt in ("cipher","manifest","private-key","output"):
        p.add_argument("--"+opt,required=True)
    p.add_argument("--research-policy",required=True,
                   choices=[POLICY],help="Explicit owner opt-in to non-PIT retrospective research")
    a=p.parse_args()
    try:
        study=research_local(cipher_path=a.cipher,
                             manifest_path=a.manifest,
                             private_key_path=a.private_key,
                             root=Path(__file__).resolve().parents[1])
        output=Path(a.output)
        print(freeze_manifest(study,output))
        print("STEP13_RETROSPECTIVE_RESEARCH_NOT_PIT",
              study["report_sha256"],
              "TRAIN",study["train_partition_rows"],
              "VALIDATION",study["validation_partition_rows"],
              "TEST",study["test_rows_processed"],
              "GATE13",study["gate13_pass"])
    except Exception as exc:
        # Never echo a secret-bearing path or provider payload in CI/chat logs.
        print("STEP13_RESEARCH_BLOCKED",type(exc).__name__)
        raise SystemExit(3)


if __name__=="__main__":
    main()
