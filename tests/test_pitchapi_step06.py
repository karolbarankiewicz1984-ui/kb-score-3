"""Offline deterministic tests for PitchAPI Step 06 audit; no tokens or HTTP."""
import unittest
from scripts.pitchapi_step06_audit import find_af_match, norm, parse_shots, select_two

class Step06Tests(unittest.TestCase):
    def test_name_normalizer(self):
        self.assertEqual(norm("Łódź FC."), "odz fc")
        self.assertEqual(norm("Le Havre  AC"), "le havre ac")

    def test_laliga_catalog_alias(self):
        # PitchAPI lists LaLiga, while our report calls it La Liga.
        self.assertEqual(norm("La Liga").replace(" ", ""), norm("LaLiga").replace(" ", ""))
        self.assertNotEqual(norm("La Liga").replace(" ", ""), norm("LaLiga2").replace(" ", ""))

    def test_two_fixed_samples(self):
        arr=[{"id":"m_AAAAAA","status":"finished","time_utc":"2022-01-01T12:00:00Z"}]
        self.assertEqual([x["id"] for x in select_two(arr)[0]],["m_AAAAAA"])
        many=[{"id":f"m_{i:06d}","status":"finished","time_utc":f"2023-02-{i+1:02d}T12:00:00Z"} for i in range(20)]
        self.assertEqual([x["id"] for x in select_two(many)[0]],["m_000005","m_000015"])

    def test_missing_xg_not_zero(self):
        p={"data":{"periods":[{"shots":[{"team_id":"t_AAAAAA","expected_goals":None}]}]}}
        r=parse_shots(p,"t_AAAAAA","t_BBBBBB")
        self.assertEqual(r["state"],"PARTIAL_SHOT_XG")
        self.assertIsNone(r["home_xg_sum"])

    def test_valid_zero_per_team(self):
        p={"data":{"periods":[{"shots":[{"team_id":"t_AAAAAA","expected_goals":0.0},{"team_id":"t_BBBBBB","expected_goals":0.3}]}]}}
        r=parse_shots(p,"t_AAAAAA","t_BBBBBB")
        self.assertEqual(r["state"],"COMPLETE_SHOT_XG")
        self.assertEqual(r["home_xg_sum"],0.0)

    def test_shot_xg_out_of_range_blocked(self):
        p={"data":{"periods":[{"shots":[{"team_id":"t_AAAAAA","expected_goals":1.4}]}]}}
        self.assertEqual(parse_shots(p,"t_AAAAAA","t_BBBBBB")["state"],"PARTIAL_SHOT_XG")

    def test_strict_matching(self):
        p={"time_utc":"2025-10-24T17:00:00Z",
           "home_team":{"name":"Arsenal"},"away_team":{"name":"Chelsea"},
           "score_home":1,"score_away":0}
        f={"fixture":{"id":123,"date":"2025-10-24T17:00:00+00:00"},
           "goals":{"home":1,"away":0},
           "teams":{"home":{"name":"Arsenal"},"away":{"name":"Chelsea"}}}
        r=find_af_match(p,[f])
        self.assertEqual(r["state"],"EXACT_NAMES_DATE_SCORE")
        self.assertEqual(r["api_football_fixture_id"],123)

    def test_ambiguous_pairing_not_claimed(self):
        p={"time_utc":"2025-10-24T17:00:00Z",
           "home_team":{"name":"Arsenal"},"away_team":{"name":"Chelsea"},
           "score_home":1,"score_away":0}
        f={"fixture":{"id":123,"date":"2025-10-24T17:00:00+00:00"},
           "goals":{"home":1,"away":0},
           "teams":{"home":{"name":"Arsenal"},"away":{"name":"Chelsea"}}}
        self.assertEqual(find_af_match(p,[f,f])["state"],"AMBIGUOUS_OR_UNMATCHED")

if __name__=="__main__":
    unittest.main()
