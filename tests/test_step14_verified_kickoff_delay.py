"""Synthetic-only regression for genuine match-day delay documentation.

Never opens owner RSA, TEST, PitchAPI outcomes or any native IDs.
"""
import copy
import unittest
from src.kb3_step14_verified_kickoff_delay import (
    read_evidence,classify_owner_diagnostic,
    eligible_before_original_schedule,ExceptionEvidenceError,
)

def owner_diagnostic_mock():
    return {
        "schema":"kb3-step14-one-owner-local-kickoff-discrepancy-v1",
        "original_native_match_count_checked":1140,
        "fully_matching_both_teams_and_utc":1139,
        "native_fixture_ids_exported":False,
        "native_team_ids_exported":False,
        "training_allowed":False,"gate14_pass":False,"test_rows_read":0,
        "time_disagreements":[{
           "season":"2024-25","partition":"TRAIN",
           "home_name":"Ipswich Town","away_name":"Everton",
           "pitchapi_kickoff_utc":"2024-10-19T14:15:00Z",
           "openfootball_kickoff_utc":"2024-10-19T14:00:00Z",
           "difference_pitchapi_minus_public_minutes":15,
        }]
    }

class DocumentedIpswichDelay(unittest.TestCase):
    def setUp(self):
        self.evidence=read_evidence()
        self.report=owner_diagnostic_mock()

    def test_exact_official_pair_confirms_only_identity_exception(self):
        r=classify_owner_diagnostic(self.report,self.evidence)
        self.assertEqual(r["matched_external_identity"],1140)
        self.assertEqual(r["identical_source_kickoffs"],1139)
        self.assertEqual(r["explicitly_documented_scheduled_vs_actual_delay"],1)
        self.assertFalse(r["source_correction_needed"])
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["gate14_pass"])
        self.assertEqual(r["test_rows_read"],0)
        self.assertFalse(r["native_ids_exported"])

    def test_other_team_not_allowlisted_even_same_15minutes(self):
        x=copy.deepcopy(self.report)
        x["time_disagreements"][0]["away_name"]="Chelsea"
        with self.assertRaises(ExceptionEvidenceError):
            classify_owner_diagnostic(x,self.evidence)

    def test_inverted_clocks_rejected(self):
        x=copy.deepcopy(self.report)
        x["time_disagreements"][0]["pitchapi_kickoff_utc"]="2024-10-19T14:00:00Z"
        x["time_disagreements"][0]["openfootball_kickoff_utc"]="2024-10-19T14:15:00Z"
        with self.assertRaises(ExceptionEvidenceError):
            classify_owner_diagnostic(x,self.evidence)

    def test_reference_source_removed_or_edited_rejected(self):
        x=copy.deepcopy(self.evidence)
        x["independent_sources"]=x["independent_sources"][:1]
        with self.assertRaises(ExceptionEvidenceError):
            classify_owner_diagnostic(self.report,x)
        x=copy.deepcopy(self.evidence)
        x["originally_scheduled_kickoff_utc"]="2024-10-19T14:15:00Z"
        with self.assertRaises(ExceptionEvidenceError):
            classify_owner_diagnostic(self.report,x)

    def test_cannot_promote_training_gate_based_on_15min_identity(self):
        x=copy.deepcopy(self.report)
        x["training_allowed"]=True
        with self.assertRaises(ExceptionEvidenceError):
            classify_owner_diagnostic(x,self.evidence)

    def test_cutoff_strictly_before_originally_scheduled_start(self):
        self.assertTrue(eligible_before_original_schedule(
             "2024-10-19T13:59:59Z",self.evidence))
        self.assertFalse(eligible_before_original_schedule(
             "2024-10-19T14:00:00Z",self.evidence))
        self.assertFalse(eligible_before_original_schedule(
             "2024-10-19T14:07:00Z",self.evidence))
        self.assertFalse(eligible_before_original_schedule(
             "2024-10-19T14:14:59Z",self.evidence))

    def test_non_utc_or_invalid_clock_rejected(self):
        for stamp in ("2024-10-19T14:01:00","2024-10-19T15:01:00+01:00","not a clock"):
            with self.subTest(stamp=stamp),self.assertRaises(ExceptionEvidenceError):
                eligible_before_original_schedule(stamp,self.evidence)

if __name__=="__main__":
    unittest.main()
