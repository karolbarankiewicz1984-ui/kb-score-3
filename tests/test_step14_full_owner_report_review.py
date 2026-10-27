"""Step14 owner aggregate acceptance: validate numeric consistency, no keys or TEST."""
import copy
import unittest

from src.kb3_step14_full_owner_report_review import inspect_owner_aggregate,FullOwnerReviewError
from src.kb3_step14_full_identity_pit_audit import SCHEMA,PUBLIC_REFERENCE_SHA
from src.kb3_step14_native_team_crosswalk import (
    ARCHIVE_ZIP_SHA,ARCHIVE_CHAIN_SHA,SAFE_SHA
)

def fake_owner_report():
    return {
        "schema":SCHEMA,
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
        "external_full_1140_targetfree_crosscheck":{
            "checked":1140,"target_free_reference_sha256":PUBLIC_REFERENCE_SHA,
            "source_is_historical_pit":False,
            "status":"RETROSPECTIVE_PUBLIC_1140_IDENTITY_CROSSCHECK_ONLY",
            "counts":{
                "EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF":1120,
                "SAME_PUBLIC_TEAM_PAIR_DIFFERENT_UTC_KICKOFF":12,
                "NO_EXACT_PUBLIC_TEAM_PAIR_SAME_SEASON":8,
            }
        },
        "external_archive_crosswalk_sample":{
            "sample_count":60,
            "independent_public_push_not_full_feature_PIT":True,
            "status":"CHECKED_NATIVE_PAIR_AGAINST_PUBLIC_60_HISTORICAL_CANDIDATES",
            "counts":{
                "IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB":1,
                "MATCH_EXACT_TEAMS_AND_SERVER_PUSH_BEFORE_KICKOFF":3,
                "MATCH_EXACT_TEAMS_GIT_COMMIT_DATE_ONLY":6,
                "NO_PREMATCH_PUBLIC_COMMIT":21,
                "NO_NATIVE_PAIR_MATCH_IN_OLD_PUBLIC_BLOB":29,
            }
        }
    }

class OwnerSummaryReview(unittest.TestCase):
    def test_complete_mock_identity_report_with_external_disagreements(self):
        out=inspect_owner_aggregate(fake_owner_report())
        self.assertEqual(out["full_public_exact_pair_and_kickoff_count"],1120)
        self.assertEqual(out["full_public_needing_identity_review_count"],20)
        self.assertEqual(out["historical_public_blob_60_counts"][
            "IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB"],1)
        self.assertFalse(out["training_allowed"])
        self.assertFalse(out["actual_archive_decryption_independently_reproduced_here"])
        self.assertEqual(out["test_rows_examined"],0)

    def test_summary_cannot_claim_real_M1_train_allowed(self):
        x=fake_owner_report();x["training_allowed"]=True
        with self.assertRaises(FullOwnerReviewError):inspect_owner_aggregate(x)

    def test_fake_identity_check_1139_declined(self):
        x=fake_owner_report();x["native_identity_fixture_ids_checked"]=1139
        with self.assertRaises(FullOwnerReviewError):inspect_owner_aggregate(x)

    def test_public_mismatch_count_not_summing_to_1140_refused(self):
        x=fake_owner_report()
        x["external_full_1140_targetfree_crosscheck"]["counts"][
            "EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF"]=1119
        with self.assertRaises(FullOwnerReviewError):inspect_owner_aggregate(x)

    def test_exposed_native_team_id_is_rejected(self):
        x=fake_owner_report();x["native_team_id"]="t_ABC123"
        with self.assertRaisesRegex(FullOwnerReviewError,"AGGREGATE_ONLY"):
            inspect_owner_aggregate(x)

    def test_exposed_native_fixture_id_is_rejected(self):
        x=fake_owner_report();x["debug"]="m_123ABC"
        with self.assertRaisesRegex(FullOwnerReviewError,"AGGREGATE_ONLY"):
            inspect_owner_aggregate(x)

    def test_partial_public_pilot_only_59_refused(self):
        x=fake_owner_report();x["external_archive_crosswalk_sample"]["counts"][
            "NO_NATIVE_PAIR_MATCH_IN_OLD_PUBLIC_BLOB"]-=1
        with self.assertRaises(FullOwnerReviewError):inspect_owner_aggregate(x)

    def test_omitted_rescheduled_exception_refused(self):
        x=fake_owner_report()
        v=x["external_archive_crosswalk_sample"]["counts"]
        v["MATCH_EXACT_TEAMS_GIT_COMMIT_DATE_ONLY"]+=1
        v["IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB"]-=1
        with self.assertRaises(FullOwnerReviewError):inspect_owner_aggregate(x)

    def test_report_cannot_contain_score_or_odd_export(self):
        x=fake_owner_report();x["rows"]=[{"score_home":3,"odds":4}]
        with self.assertRaisesRegex(FullOwnerReviewError,"AGGREGATE_ONLY"):
            inspect_owner_aggregate(x)

if __name__=="__main__":unittest.main()
