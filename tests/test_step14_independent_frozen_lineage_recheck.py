"""No provider key or target labels: adversarial unit tests for the frozen PIT recheck."""
import copy
import unittest

from scripts.step14_independent_frozen_lineage_recheck import (
    AuditFailure, check_row, utc, witnesses
)

COMMIT = "a" * 40
WITNESS = {"season": "2023-24", "push": "2023-10-01T12:00:00Z"}

def row():
    return {
        "fixture_id": "synthetic-fixture-1",
        "partition": "TRAIN",
        "season": "2023-24",
        "kickoff_utc": "2023-10-02T16:00:00Z",
        "independent_older_source_candidates_checked": 1,
        "public_result_source_lineage_state":
            "PUBLIC_OLD_RESULTS_ALL_PREDECESSORS_SOURCE_ONLY",
        "best_old_public_source": {
            "source_commit": COMMIT,
            "source_published_at_utc": "2023-10-01T12:00:00Z",
            "verified_exact_native_prior_fixture_count": 10,
            "both_have_five_prior_games": True,
            "all_same_season_predecessor_FT_in_old_source": True,
        },
        "original_PitchAPI_73_nonxg_fields_asof_proven": False,
        "original_PitchAPI_team_xg_first_published_proven": False,
        "actual_provider_historic_feature_cutoff_utc": None,
        "original_121_plus_38_PIT_training_eligible": False,
    }

class IndependentFrozenLineageTests(unittest.TestCase):
    def check(self, r):
        return check_row(r, source_ids={COMMIT}, witness_map={COMMIT: WITNESS})

    def test_valid_public_source_only_does_not_admit_m1(self):
        self.assertEqual(self.check(row()), (True, True))

    def test_future_publication_fails(self):
        r = row()
        r["best_old_public_source"]["source_published_at_utc"] = "2023-10-03T00:00:00Z"
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_witness_clock_mismatch_fails(self):
        r = row()
        r["best_old_public_source"]["source_published_at_utc"] = "2023-09-30T12:00:00Z"
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_unlisted_source_fails(self):
        r = row()
        r["best_old_public_source"]["source_commit"] = "b" * 40
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_original_pit_approval_fails(self):
        r = row()
        r["original_121_plus_38_PIT_training_eligible"] = True
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_provider_first_publication_unsupported_fails(self):
        r = row()
        r["original_PitchAPI_team_xg_first_published_proven"] = True
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_unproven_nonxg_fails(self):
        r = row()
        r["original_PitchAPI_73_nonxg_fields_asof_proven"] = True
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_validation_source_only_fails(self):
        r = row()
        r["season"] = "2025-26"
        r["partition"] = "VALIDATION"
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_missing_source_has_no_positive_status(self):
        r = row()
        r["best_old_public_source"] = None
        with self.assertRaises(AuditFailure):
            self.check(r)
        r["public_result_source_lineage_state"] = "NO_COMPLETE_SOURCE_BACKED_PRIOR_RESULT_CHAIN"
        self.assertEqual(self.check(r), (False, False))

    def test_unexpected_result_field_fails_closed(self):
        r = row()
        r["target_goals"] = [1, 0]
        with self.assertRaises(AuditFailure):
            self.check(r)

    def test_non_utc_fails(self):
        with self.assertRaises(AuditFailure):
            utc("2023-10-01T12:00:00+02:00")

if __name__ == "__main__":
    unittest.main()
