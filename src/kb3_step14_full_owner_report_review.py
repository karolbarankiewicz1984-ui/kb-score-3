"""Review ONLY owner-produced aggregate after future local RSA decrypt.

This validator neither reads the private RSA key nor claims independently
to have decrypted 1140 matches. A user-supplied JSON can be forged, so this
checks structural consistency and original source hashes, NOT cryptographic
proof the archive was actually decrypted or that TRAIN is PIT-approved.
"""
from __future__ import annotations
from collections import Counter
import json
import re
from pathlib import Path

from src.kb3_step14_full_identity_pit_audit import (
    SCHEMA as INPUT_SCHEMA,PUBLIC_REFERENCE_SHA,
)
from src.kb3_step14_native_team_crosswalk import (
    ARCHIVE_ZIP_SHA,ARCHIVE_CHAIN_SHA,SAFE_SHA,
)

class FullOwnerReviewError(ValueError):pass

ALLOWED_CATEGORIES={
 "EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF",
 "SAME_PUBLIC_TEAM_PAIR_DIFFERENT_UTC_KICKOFF",
 "NO_EXACT_PUBLIC_TEAM_PAIR_SAME_SEASON",
 "PUBLIC_KICKOFF_TIME_UNAVAILABLE",
}
ALLOWED_SAMPLE_CATEGORIES={
 "IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB",
 "NO_PREMATCH_PUBLIC_COMMIT",
 "MATCH_EXACT_TEAMS_AND_SERVER_PUSH_BEFORE_KICKOFF",
 "MATCH_EXACT_TEAMS_GIT_COMMIT_DATE_ONLY",
 "NO_NATIVE_PAIR_MATCH_IN_OLD_PUBLIC_BLOB",
}
NATIVE_ID_PATTERN=re.compile(r"\b(?:m|t)_[A-Za-z0-9]{6}\b")

def _counts(value,required_total,allowed):
    if not isinstance(value,dict) or not set(value)<=allowed:
        raise FullOwnerReviewError("UNRECOGNIZED_RESULT_CATEGORY")
    if not all(type(v) is int and v>=0 for v in value.values()):
        raise FullOwnerReviewError("INVALID_RESULT_COUNTS")
    if sum(value.values())!=required_total:
        raise FullOwnerReviewError("REPORT_COUNTS_DO_NOT_RECONCILE")
    return dict(sorted(value.items()))

def inspect_owner_aggregate(report):
    if not isinstance(report,dict) or report.get("schema")!=INPUT_SCHEMA:
        raise FullOwnerReviewError("ORIGINAL_1140_REPORT_SCHEMA_REQUIRED")
    # Native strings must NEVER leave the user's computer; only aggregates.
    serialized=json.dumps(report,sort_keys=True,ensure_ascii=False)
    if (NATIVE_ID_PATTERN.search(serialized) or
        any(k in report for k in (
            "private_key","secret","score_home","score_away",
            "odds","target_label","labels","rows","receipts","matches"))):
        raise FullOwnerReviewError("OWNER_REPORT_NOT_AGGREGATE_ONLY")
    for field,want in {
       "source_archive_zip_sha256":ARCHIVE_ZIP_SHA,
       "source_chain_sha256":ARCHIVE_CHAIN_SHA,
       "source_safe_projection_sha256":SAFE_SHA,
       "native_identity_fixture_ids_checked":1140,
       "native_identity_within_pitchapi_sealed_source_verified":1140,
       "identity_checked_season_counts":{"2023-24":380,"2024-25":380,"2025-26":380},
       "identity_checked_partition_counts":{"TRAIN":760,"VALIDATION":380},
       "native_season_team_counts":{"2023-24":20,"2024-25":20,"2025-26":20},
       "native_team_id_name_conflicts":0,
       "native_fixture_id_kickoff_role_mismatches":0,
       "native_home_away_duplicate_matches":0,
       "original_retrospective_source_observed_after_target_kickoff":1140,
       "actual_historical_first_publication_for_full_features_proven":0,
       "feature_contract_numeric_nullable_field_count":121,
       "feature_contract_missing_flag_count":38,
       "feature_contract_total_lineage_proofs_expected":159,
       "real_training_prematch_proven_rows":0,
       "real_validation_prematch_proven_rows":0,
       "test_matches_inspected":0,
       "test_labels_read":0,
       "match_results_or_odds_exported":False,
       "native_fixture_ids_or_native_team_ids_exported":False,
       "private_rsa_key_exported":False,
       "sports_api_requests":0,
       "production_model_fitted":False,
       "training_allowed":False,
       "gate14_pass":False,
    }.items():
        if report.get(field)!=want:
            raise FullOwnerReviewError("OWNER_AGGREGATE_INCONSISTENT:"+field)

    full=report.get("external_full_1140_targetfree_crosscheck")
    pilot=report.get("external_archive_crosswalk_sample")
    if not isinstance(full,dict) or not isinstance(pilot,dict):
        raise FullOwnerReviewError("PUBLIC_IDENTITY_AUDITS_REQUIRED")
    if (full.get("checked")!=1140 or
        full.get("target_free_reference_sha256")!=PUBLIC_REFERENCE_SHA or
        full.get("source_is_historical_pit") is not False or
        full.get("status")!="RETROSPECTIVE_PUBLIC_1140_IDENTITY_CROSSCHECK_ONLY" or
        pilot.get("sample_count")!=60 or
        pilot.get("independent_public_push_not_full_feature_PIT") is not True or
        pilot.get("status")!="CHECKED_NATIVE_PAIR_AGAINST_PUBLIC_60_HISTORICAL_CANDIDATES"):
        raise FullOwnerReviewError("EXTERNAL_CROSSWALK_UNVERIFIED")
    all_status=_counts(full.get("counts"),1140,ALLOWED_CATEGORIES)
    pilot_status=_counts(pilot.get("counts"),60,ALLOWED_SAMPLE_CATEGORIES)
    if pilot_status.get("IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB")!=1:
        raise FullOwnerReviewError("SEPTEMBER_RECORDED_SCHEDULE_AMENDMENT_MISSING")
    # A source-verified native match can disagree with external OpenFootball;
    # do not declare an invalid native ID merely because public team aliases
    # differ. Keep every disagreement visible as a category, no override.
    external_need_review={
       k:v for k,v in all_status.items()
       if k!="EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF" and v
    }
    return {
       "schema":"kb3-step14-owner-1140-aggregate-schema-review-v1",
       "native_ids_and_roles_internal_consistency":"PASS_FROM_OWNER_REPORTED_AGGREGATES",
       "actual_archive_decryption_independently_reproduced_here":False,
       "training_PIT_certification":False,
       "full_public_exact_pair_and_kickoff_count":
          all_status.get("EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF",0),
       "full_public_needing_identity_review":external_need_review,
       "full_public_needing_identity_review_count":sum(external_need_review.values()),
       "historical_public_blob_60_counts":pilot_status,
       "review_note":"External disagreements require investigation; native IDs are not published; training remains blocked.",
       "training_allowed":False,
       "gate14_pass":False,
       "test_rows_examined":0,
       "private_key_read":False,
    }

def run(path):
    return inspect_owner_aggregate(json.loads(Path(path).read_text(encoding="utf8")))

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--aggregate",required=True)
    args=p.parse_args()
    try:
        r=run(args.aggregate)
        print(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2))
    except Exception as exc:
        print("OWNER_AGGREGATE_SCHEMA_REVIEW_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
