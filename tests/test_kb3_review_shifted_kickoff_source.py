import unittest

from scripts.kb3_review_shifted_kickoff_source import verified_fixture


class ShiftedKickoffSourceTests(unittest.TestCase):
    def setUp(self):
        self.kickoff = "2026-11-07T16:15:00Z"
        self.case = {
            "league": "FRA",
            "native_match_id": "m_example",
            "frozen_capture_utc": "2026-11-04T15:01:00Z",
            "frozen_source_chain_sha256": "a"*64,
            "frozen_home_team_id": "t_home",
            "frozen_away_team_id": "t_away",
        }
        self.match = {"id": "m_example", "time_utc": self.kickoff,
                      "home_team": {"id": "t_home", "name": "Club A"},
                      "away_team": {"id": "t_away", "name": "Club B"}}
        self.source = {"resource": "pitchapi:m0720:fixtures:FRA:2026/2027",
                       "chain_sha256": "a"*64, "completed_at_utc": "2026-11-04T15:00:00Z",
                       "payload": {"matches": [self.match]}}

    def test_extracts_names_only_for_exact_original_side_ids_and_clock(self):
        teams, chain = verified_fixture([self.source], self.case, self.kickoff, frozen=True)
        self.assertEqual(teams, {"home": {"id": "t_home", "name": "Club A"},
                                 "away": {"id": "t_away", "name": "Club B"}})
        self.assertEqual(chain, "a"*64)
        self.match["home_team"], self.match["away_team"] = self.match["away_team"], self.match["home_team"]
        with self.assertRaisesRegex(ValueError, "SHIFTED_KICKOFF_PROVIDER_TEAM_ID_MISMATCH"):
            verified_fixture([self.source], self.case, self.kickoff, frozen=True)

    def test_schedule_match_alone_and_wrong_archive_are_not_evidence(self):
        self.match["away_team"]["name"] = ""
        with self.assertRaisesRegex(ValueError, "SHIFTED_KICKOFF_PROVIDER_TEAM_NAME_MISSING"):
            verified_fixture([self.source], self.case, self.kickoff, frozen=False)
        self.source["chain_sha256"] = "b"*64
        with self.assertRaisesRegex(ValueError, "SHIFTED_KICKOFF_ORIGINAL_SOURCE_CHAIN_OR_CLOCK_MISMATCH"):
            verified_fixture([self.source], self.case, self.kickoff, frozen=True)
