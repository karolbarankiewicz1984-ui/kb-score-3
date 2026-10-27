"""Fail-closed synthetic negative tests for Step14 public per-fixture lineage."""
from datetime import timedelta
import copy
import unittest

from src.kb3_step14_fpl_form5_lineage import (
    PUBLIC_AT, CSV_SHA256, EVENT_ID, COMMIT, REPO,
    LineageError, _candidate, utc, verify_evidence,
)


def fixture(fid, home, away, kickoff, finished=True):
    return {"id": str(fid), "team_h": str(home), "team_a": str(away),
            "kickoff_time": kickoff, "finished": str(finished),
            "team_h_score": "2" if finished else "",
            "team_a_score": "1" if finished else ""}


def grid():
    # Five already published completed fixtures for A, five for B, same season.
    rows = []
    for i in range(5):
        day = i + 1
        rows.append(fixture("a" + str(day), "A", str(100 + day),
                            f"2023-09-{day:02d}T12:00:00Z"))
        rows.append(fixture("b" + str(day), "B", str(200 + day),
                            f"2023-09-{day:02d}T15:00:00Z"))
    target = fixture("target", "A", "B", "2023-10-07T14:00:00Z", False)
    rows.append(target)
    return rows, target


class PerFixtureLineageTests(unittest.TestCase):
    def test_known_public_predecessors_are_conditional_not_pitchapi(self):
        rows, target = grid()
        result = _candidate(rows, target, utc(PUBLIC_AT))
        self.assertEqual(result["state"], "PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE")
        self.assertEqual(len(result["home_last5_public_fixture_ids"]), 5)
        self.assertEqual(len(result["away_last5_public_fixture_ids"]), 5)
        self.assertNotIn("target", result["home_last5_public_fixture_ids"])
        self.assertNotIn("team_h_score", str(result))
        self.assertNotIn("team_a_score", str(result))

    def test_latest_unplayed_fixture_blocks_old_stale_snapshot(self):
        rows, target = grid()
        rows.insert(-1, fixture("gap", "A", "Z", "2023-10-06T17:00:00Z", False))
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "INTERVENING_UNVERIFIED_FIXTURE")

    def test_undocumented_future_result_does_not_count(self):
        rows, target = grid()
        rows.insert(-1, fixture("future-result", "A", "Z",
                                "2023-10-06T17:00:00Z", True))
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "INTERVENING_UNVERIFIED_FIXTURE")

    def test_missing_team_schedule_clock_fails_closed(self):
        rows, target = grid()
        rows.insert(-1, fixture("unknown", "B", "Z", "", False))
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "TEAM_SCHEDULE_TIME_UNKNOWN")

    def test_less_than_five_prior_fails_closed(self):
        rows, target = grid()
        rows = [r for r in rows if r["id"] != "a1"]
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "FEWER_THAN_FIVE_PROVEN_PREDECESSORS")

    def test_target_must_be_future_and_unplayed(self):
        rows, target = grid()
        target["kickoff_time"] = PUBLIC_AT
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "NOT_AFTER_VERIFIED_PUBLICATION")
        target["kickoff_time"] = "2023-10-07T14:00:00Z"
        target["finished"] = "True"
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "NO_PREMATCH_TARGET_CLOCK")

    def test_same_team_same_time_conflict(self):
        rows, target = grid()
        rows.insert(-1, fixture("conflict", "A", "C",
                                "2023-10-07T14:00:00Z", False))
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "SAME_TEAM_SAME_KICKOFF")

    def test_postponed_earlier_match_blocks(self):
        rows, target = grid()
        rows.insert(-1, fixture("postponed", "A", "C",
                                "2023-09-19T15:00:00Z", False))
        self.assertEqual(_candidate(rows, target, utc(PUBLIC_AT))["state"],
                         "INTERVENING_UNVERIFIED_FIXTURE")

    def test_utc_must_be_explicit(self):
        for wrong in ("2023-10-05T14:38:59", "2023-10-05T15:38:59+01:00", "bad"):
            with self.assertRaises(LineageError):
                utc(wrong)

    def test_forged_evidence_cannot_promote_git_commit_date(self):
        ev = {"gate14_pass": False, "official_M1_train_allowed": False,
              "records": [{"historic_commit_sha": COMMIT, "public_repo": REPO,
                           "original_publication_timestamp_externally_corroborated": False,
                           "independent_gharchive_hour_status": "READ_OK",
                           "server_confirmed_public_push_utc": PUBLIC_AT,
                           "server_event_id": EVENT_ID,
                           "original_archived_csv_sha256": CSV_SHA256,
                           "finished_ft_records_available_at_historical_source_publication": 70,
                           "unplayed_rows_have_null_scores": 310,
                           "prematch_source_status": "PUBLIC_PUSH_VERIFIED_PARTIAL_FT_ONLY"}]}
        with self.assertRaisesRegex(LineageError, "SOURCE_CLOCK"):
            verify_evidence(ev, b"not-pinned-content")

    def test_only_original_sha_and_public_clock(self):
        self.assertEqual(len(COMMIT), 40)
        self.assertEqual(len(CSV_SHA256), 64)
        self.assertEqual(utc(PUBLIC_AT).year, 2023)
        self.assertTrue(EVENT_ID.isdigit())


if __name__ == "__main__":
    unittest.main()
