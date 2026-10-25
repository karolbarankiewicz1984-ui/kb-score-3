"""Tests for bounded PitchAPI xG audit. No network and no credentials."""
import unittest
from scripts.pitchapi_xg_coverage_audit import norm, picked, league_lookup, shots_summary, matching_pitch_to_football, Client, PITCH_MAX


class Gate06Tests(unittest.TestCase):
    def test_norm_alias(self):
        self.assertEqual(norm("FC Barcelona"), "barcelona")
        self.assertEqual(norm("Barcelóna"), "barcelona")

    def test_deterministic_sample(self):
        seq=list(range(100))
        self.assertEqual(picked(seq),picked(seq))
        self.assertEqual(len(picked(seq)),3)
        self.assertEqual(picked([]),[])

    def test_missing_is_not_zero(self):
        data=shots_summary(None,"h","a")
        self.assertEqual(data["state"],"MISSING")
        self.assertIsNone(data["xg_home"])
        self.assertIsNone(data["xg_away"])

    def test_both_team_numeric_xg(self):
        data={"periods":[{"shots":[
            {"team_id":"h","expected_goals":.3},
            {"team_id":"a","expected_goals":.2}
        ]}]}
        out=shots_summary(data,"h","a")
        self.assertEqual(out["state"],"COMPLETE_WITH_XG")
        self.assertEqual(out["xg_home"],.3)
        self.assertEqual(out["xg_away"],.2)

    def test_xg_boolean_invalid_and_partial(self):
        data={"periods":[{"shots":[
            {"team_id":"h","expected_goals":True},
            {"team_id":"a","expected_goals":.2}
        ]}]}
        out=shots_summary(data,"h","a")
        self.assertEqual(out["state"],"PARTIAL_XG")
        self.assertEqual(out["with_xg"],1)

    def test_correct_match_and_swapped_teams_not_accepted(self):
        pitch={"time_utc":"2025-08-10T17:00:00Z","home_team":{"name":"FC Barcelona"},
               "away_team":{"name":"Real Madrid"},"score_home":2,"score_away":1}
        games=[{"fixture":{"date":"2025-08-10T17:00:00+00:00","id":42},
                "teams":{"home":{"name":"Barcelona"},"away":{"name":"Real Madrid"}},
                "goals":{"home":2,"away":1}}]
        self.assertEqual(matching_pitch_to_football(pitch,games)["state"],"MATCHED")
        games[0]["teams"]["home"]["name"]="Real Madrid"
        games[0]["teams"]["away"]["name"]="Barcelona"
        self.assertNotEqual(matching_pitch_to_football(pitch,games)["state"],"MATCHED")

    def test_unlisted_league(self):
        cat={"leagues":[{"name":"Premier League","country_code":"ENG","id":"l_abc","seasons":["2025/2026"]}]}
        self.assertEqual(league_lookup(cat,"ENG",("premier league",))["id"],"l_abc")
        self.assertIsNone(league_lookup(cat,"ESP",("laliga",)))

    def test_hard_request_ceiling_before_network(self):
        fake=Client("pitchapi","https://invalid.invalid","fake",PITCH_MAX,"X-API-KEY")
        fake.calls=PITCH_MAX
        with self.assertRaisesRegex(RuntimeError,"HARD_REQUEST_BUDGET"):
            fake.get("/v1/leagues")


if __name__=="__main__":
    unittest.main()
