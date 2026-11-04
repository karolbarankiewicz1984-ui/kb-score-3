"""Pure-clock regression only; synthetic examples never become FIT or forecasts."""
import unittest
from src.kb3_research_train_forward_contract import audit_target, audit_batch, ParityError
from scripts.kb3_research_parity_audit import inspect_source


def sample():
    return {
        "league": "ESP", "fixture_id": "target-1",
        "kickoff_utc": "2026-11-04T20:00:00Z",
        "capture_cutoff_utc": "2026-11-04T18:00:00Z",
        "predecessors": [
            {"fixture_id": "old", "kickoff_utc": "2026-11-01T12:00:00Z"},
            {"fixture_id": "recent", "kickoff_utc": "2026-11-04T14:00:00Z"},
        ]
    }


class ResearchParityTests(unittest.TestCase):
    def test_true_48h_vs_3h_difference_and_age_reference(self):
        r = audit_target(sample())
        self.assertEqual(r["legacy48h_predecessor_ids"], ["old"])
        self.assertEqual(r["forward3h_clock_only_predecessor_ids"], ["old", "recent"])
        self.assertEqual(r["only_forward_clock_ids"], ["recent"])
        self.assertNotEqual(r["legacy_days_since_last_kickoff_at_target"],
                            r["forward_days_since_last_kickoff_at_capture"])
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["independent_source_evidence_verified"])

    def test_input_claim_never_counts_as_independently_attested(self):
        row = sample()
        row["predecessors"][1].update({
            "source_provenance": "ORIGINAL_PREMATCH_ATTESTED",
            "source_published_at_utc": "2026-11-04T17:05:00Z",
            "source_observed_at_utc": "2026-11-04T17:20:00Z",
        })
        r = audit_target(row)
        self.assertEqual(r["forward3h_unverified_evidence_claim_ids"], ["recent"])
        self.assertFalse(r["independent_source_evidence_verified"])
        self.assertFalse(r["original_historical_pit_certified"])

    def test_reject_protected_test_and_late_cutoff(self):
        row = sample()
        row["league"] = "ENG"
        with self.assertRaises(ParityError):
            audit_target(row)
        row = sample()
        row["capture_cutoff_utc"] = "2026-11-04T19:00:00Z"
        with self.assertRaises(ParityError):
            audit_target(row)

    def test_reject_target_as_predecessor_and_duplicated_targets(self):
        row = sample()
        row["predecessors"].append(
            {"fixture_id": "target-1", "kickoff_utc": "2026-11-02T00:00:00Z"})
        with self.assertRaises(ParityError):
            audit_target(row)
        with self.assertRaises(ParityError):
            audit_batch([sample(), sample()])

    def test_missing_publication_never_becomes_pit(self):
        row = sample()
        row["predecessors"][1]["source_provenance"] = "ORIGINAL_PREMATCH_ATTESTED"
        r = audit_target(row)
        self.assertEqual(r["forward3h_unverified_evidence_claim_ids"], [])
        self.assertEqual(r["reasons"]["PIT_EVIDENCE_NOT_SUPPLIED"], 2)

    def test_source_contract_policy_markers(self):
        f = ('RESULT_LAG=timedelta(hours=3)\n'
             'start + RESULT_LAG <= published <= captured <= cutoff\n'
             'round((cutoff-utc_dt(all_games[-1]["kickoff_utc"])).total_seconds())')
        h = ('LAG=timedelta(hours=48)\n'
             'round((ko-previous[-1]["ko"]).total_seconds())\n'
             'B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT')
        r = inspect_source(f, h)
        self.assertEqual(r["remediation_status"], "OPEN_NOT_FIXED")
        with self.assertRaises(ValueError):
            inspect_source("unexpected", h)


if __name__ == "__main__":
    unittest.main()
