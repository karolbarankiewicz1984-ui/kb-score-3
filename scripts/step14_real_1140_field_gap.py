"""Real signed Step12 TRAIN/VALIDATION evidence audit, without RSA or TEST.

Runs safely on CI. This is an actual completeness audit of a real signed
manifest, *not* proof of individual private native team identities, and does
not inspect labels or outcome-dependent hashes. Counts only source-backed
historical per-feature receipt availability, never reconstructs clocks.
"""
from pathlib import Path
from collections import Counter
import json

from src.kb3_step14_real_pit_gate import inspect_repo
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step14_full_identity_pit_audit import _feature_family
from src.kb3_split import sha

ROOT=Path(__file__).resolve().parents[1]
BLOB="data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json"
CLOCK="data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json"

def run(root=ROOT):
    root=Path(root)
    real=inspect_repo(root)
    blob=json.loads((root/BLOB).read_text(encoding="utf8"))
    clock=json.loads((root/CLOCK).read_text(encoding="utf8"))
    if real["train_row_count"]!=760 or real["validation_row_count"]!=380:
        raise ValueError("REAL_SOURCE_COUNT_CHANGED")
    if (real["train_missing_feature_cutoff_count"]!=760 or
        real["validation_missing_feature_cutoff_count"]!=380 or
        real["train_proven_pre_match_eligible"]!=0 or
        real["validation_proven_pre_match_eligible"]!=0 or
        real["gate14_pass"] is not False):
        raise ValueError("REAL_PIT_SOURCE_PREMATURELY_RELEASED")
    if (blob["sampled_train"]!=40 or blob["sampled_validation"]!=20 or
        blob["sampled_test"]!=0 or len(blob["records"])!=60 or
        blob["official_pitchapi_training_records_certified"]!=0 or
        clock["native_pitchapi_team_pairs_verified"]!=0):
        raise ValueError("PUBLIC_PREVIOUS_AUDITS_CHANGED")
    totals=Counter(_feature_family(name) for name in EXPECTED_FEATURES)
    missing=Counter(_feature_family(name) for name in EXPECTED_MISSING)
    report={
      "schema":"kb3-step14-original-real-1140-pit-gap-and-field-inventory-v1",
      "source_safe_schedule_sha256":real["source_safe_projection_sha256"],
      "source_real_split_sha256":real["source_real_manifest_sha256"],
      "historical_match_count":1140,
      "real_train_count":760,"real_validation_count":380,
      "real_train_missing_true_prematch_cutoff":760,
      "real_validation_missing_true_prematch_cutoff":380,
      "feature_contract_numeric_nullable_fields":len(EXPECTED_FEATURES),
      "feature_contract_missing_flags":len(EXPECTED_MISSING),
      "per_row_field_evidence_required":len(EXPECTED_FEATURES)+len(EXPECTED_MISSING),
      "feature_families_fields":dict(sorted(totals.items())),
      "feature_families_missing_flags":dict(sorted(missing.items())),
      "family_actual_original_receipt_prematch_proven":{
        k:{"train":0,"validation":0,"cutoffs_missing":1140,
           "actual_original_asof_evidence_available":False}
        for k in sorted(totals)},
      "prematch_fixture_identity_scheduled_vs_field_proof_distinct":True,
      "public_60_candidate_pilot_actual":dict(sorted(blob["status_totals"].items())),
      "third_party_public_push_shas_independently_confirmed":clock["independent_push_sha_samples_corroborated"],
      "third_party_push_not_full_feature_pit":True,
      "original_pitchapi_historical_capture_date":"2026-10-26",
      "original_historical_statistic_publication_at_target_known":False,
      "certified_actual_prematch_train":0,"certified_actual_prematch_validation":0,
      "private_team_pair_decryption_performed_in_this_ci":False,
      "training_allowed":False,"gate14_pass":False,"test_rows_read":0,
      "result_labels_read":0,"sports_api_calls":0,
      "report_scope":"ACTUAL_PINNED_MANIFEST_METADATA_ONLY_NOT_NATIVE_PAIR_LOCAL_DECRYPT",
    }
    report["report_sha256"]=sha(report)
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    opt=p.parse_args()
    report=run()
    dest=Path(opt.out);dest.parent.mkdir(parents=True,exist_ok=True)
    serialized=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if dest.exists():
        if dest.read_text(encoding="utf8")!=serialized:
            raise ValueError("PINNED_REPORT_CHANGED_APPEND_ONLY")
    else:
        dest.write_text(serialized,encoding="utf8")
    print(json.dumps({k:report[k] for k in (
      "historical_match_count","real_train_missing_true_prematch_cutoff",
      "real_validation_missing_true_prematch_cutoff",
      "per_row_field_evidence_required","feature_families_fields",
      "third_party_public_push_shas_independently_confirmed",
      "certified_actual_prematch_train","gate14_pass")},sort_keys=True))
