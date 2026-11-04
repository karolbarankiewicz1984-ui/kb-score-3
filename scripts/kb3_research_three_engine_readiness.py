"""Read-only audit of genuine M0/Elo-only/CatBoost no-xG same-game evidence.

Uses already immutable M0 settlement receipts, not historical M0 replays.
Does not fit, invoke providers, declare winner, or create new predictions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECEIPTS=ROOT/"data/pit_sidecar/m0_720_eight"
REQUIRED_PAIRS=(
    "ELO_ONLY__vs__M0_ELO_POISSON_720TRAIN",
    "ELO_ONLY__vs__CATBOOST_NO_XG",
    "M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG",
)
MIN_PAIRED=100
MIN_INDEPENDENT_WEEKS=8


def require(ok,message):
    if not ok:
        raise ValueError(message)


def latest_settlement(root=RECEIPTS):
    rows=[]
    for path in root.glob("*/settle-*/RECEIPT.json"):
        doc=json.loads(path.read_text())
        if doc.get("mode")=="settle":
            rows.append((datetime.fromisoformat(doc["run_utc"].replace("Z","+00:00")),
                         path,doc))
    require(bool(rows),"NO_ACTUAL_SETTLEMENT_RECEIPTS")
    _,path,doc=max(rows,key=lambda x:x[0])
    return path,doc


def analyze(r):
    require(r["mode"]=="settle" and
            r["model_version"]=="M0_ELO_POISSON_RESEARCH_720TRAIN_V1",
            "WRONG_OR_SYNTHETIC_MODEL")
    require(r["original_2026_27_Premier_League_TEST_accessed"] is False and
            r["production_approved"] is False, "PROTECTED_OR_PRODUCTION_CHANGED")
    ready=r["calibration_readiness"]
    frozen=ready["git_server_push_verified_forecasts"]
    eligible=ready["eligible_settled_unique"]
    settled=ready["settled_total"]
    require(0<=eligible<=settled<=frozen,"INCONSISTENT_FIT_COUNTS")
    require(r["new_settlements"]>=0,"NEGATIVE_SETTLEMENT_COUNT")
    require(r["not_yet_settled"]==frozen-settled,
            "PENDING_SAMPLE_ACCOUNTING_DRIFT")
    require(r["calibration_fitted"] is False and ready["gate16"]=="PENDING",
            "FORMAL_CALIBRATION_GATE_CHANGED")
    comparison=r["step17_paired_same_fixture_readiness"]
    require(comparison["evaluation_domain"]=="FORWARD_GITHUB_HOST_ATTESTED",
            "MIXED_WITH_HISTORICAL_REPLAY")
    require(comparison["winner_auto_selected"] is False and
            comparison["production_model_changed"] is False and
            comparison["sealed_test_accessed"] is False,
            "CHAMPION_OR_PROTECTED_TEST_MUTATED")
    pairs=comparison["fair_same_game_pairwise"]
    n_by_pair={}
    for key in REQUIRED_PAIRS:
        require(key in pairs,"MISSING_REAL_FORWARD_PAIR_REPORT")
        entry=pairs[key]
        require(type(entry["common_n"]) is int and entry["common_n"]>=0,
                "INVALID_PAIR_COUNT")
        n_by_pair[key]=entry["common_n"]
    triplet_floor=min(n_by_pair.values())
    require(comparison["unique_fixtures"]>=triplet_floor,
            "COMMON_MATCHES_EXCEED_UNIQUE_MATCHES")
    flags={
        "original_forward_proofs": r["publication_proof_audit"].get(
            "missing_host_evidence_never_assumed_pre_match") is True,
        "same_fixture_pairing": all(n>=MIN_PAIRED for n in n_by_pair.values()),
        "independent_week_evidence": all(
            pairs[key].get("deltas",{}).get("log_loss",{}).get(
                "week_blocks",0)>=MIN_INDEPENDENT_WEEKS
            for key in REQUIRED_PAIRS),
        "after_formal_gate16": ready["gate16"]=="PASS",
    }
    result={
        "schema":"kb3-research-three-engine-forward-readiness-v1",
        "as_of_run_utc":r["run_utc"],
        "frozen_forecasts":frozen,"eligible_fit":eligible,
        "settled_total":settled,"pending":r["not_yet_settled"],
        "missing_to_fit100":max(0,100-eligible),
        "triplet_same_game_proven_at_least":triplet_floor,
        "paired_counts":n_by_pair,
        "five_engine_common_count":comparison["full_five_common_fixtures"],
        "status":"RESEARCH_ONLY_INSUFFICIENT_INDEPENDENT_FORWARD",
        "formal_comparison_ready":all(flags.values()),
        "criteria":flags,
        "no_auto_winner":True,"gate16":"PENDING","gate17":"PENDING",
        "M0_unchanged":True,"historical_replay_not_combined":True,
    }
    require(result["formal_comparison_ready"] is False,
            "FORMAL_GATE_MUST_BE_SEPARATELY_APPROVED")
    result["report_sha256"]=hashlib.sha256(
        json.dumps(result,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--receipt",type=Path)
    args=parser.parse_args()
    if args.receipt:
        path=args.receipt
        receipt=json.loads(path.read_text())
    else:
        path,receipt=latest_settlement()
    output=analyze(receipt)
    output["source_path"]=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    print(json.dumps(output,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
