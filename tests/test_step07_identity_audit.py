"""Offline quality gates for step 07 identity linking; no real API calls."""
import unittest
from scripts.step07_identity_audit import (
    norm, as_utc, classify, evaluate, no_duplicate_mapping,
    verify_fixture_uniqueness, LEAGUE_IDS, MAX_REQUESTS,
)

def football(fid=123, when="2026-10-25T15:00:00Z",
             home="Atletico Madrid", away="Real Sociedad",
             hg=2, ag=1, status="FT"):
    return {"fixture":{"id":fid,"date":when,"status":{"short":status}},
            "teams":{"home":{"id":5,"name":home},"away":{"id":6,"name":away}},
            "goals":{"home":hg,"away":ag}}

def pitch(home="Atlético Madrid", away="Real Sociedad",
          when="2026-10-25T17:00:00+02:00", hg=2, ag=1):
    return {"pitch_match_id":"m_ABC123","league":"La Liga",
            "season":"2026/2027","kickoff_utc":when,
            "home_team":home,"away_team":away,"score_home":hg,
            "score_away":ag,
            "api_football_pair":{"state":"EXACT_NAMES_DATE_SCORE",
                                 "api_football_fixture_id":123}}

class IdentityContractTests(unittest.TestCase):
    def test_contract_and_budget(self):
        self.assertEqual(len(LEAGUE_IDS),5)
        self.assertLessEqual(30, MAX_REQUESTS)
        self.assertLessEqual(MAX_REQUESTS,35)

    def test_diacritics_and_utc_dst_conversion(self):
        self.assertEqual(norm("Atlético Madrid"),"atletico madrid")
        self.assertEqual(as_utc("2026-10-25T17:00:00+02:00"),
                         as_utc("2026-10-25T15:00:00Z"))

    def test_strict_match(self):
        r=classify(pitch(),[football()])
        self.assertEqual(r["state"],"STRICT")
        self.assertEqual(r["football_id"],123)

    def test_changed_score_must_not_auto_match(self):
        r=classify(pitch(hg=1),[football()])
        self.assertNotEqual(r["state"],"STRICT")
        self.assertIsNone(r["football_id"])

    def test_alias_requires_review_not_guessed(self):
        r=classify(pitch(home="Atlético"),[football()])
        self.assertEqual(r["state"],"REVIEW_CANDIDATE")
        self.assertIsNone(r["football_id"])
        self.assertEqual(r["candidates"][0]["football_id"],123)

    def test_postponed_time_requires_review(self):
        r=classify(pitch(when="2026-10-24T15:00:00Z"),[football()])
        self.assertEqual(r["state"],"REVIEW_CANDIDATE")
        self.assertIsNone(r["football_id"])

    def test_swapped_home_and_away_blocked(self):
        r=classify(pitch(home="Real Sociedad",away="Atlético Madrid"),[football()])
        self.assertNotEqual(r["state"],"STRICT")
        self.assertIsNone(r["football_id"])

    def test_two_exact_candidates_are_quarantined(self):
        r=classify(pitch(),[football(123),football(456)])
        self.assertEqual(r["state"],"REVIEW_MULTIPLE_EXACT")
        self.assertIsNone(r["football_id"])

    def test_future_or_unfinished_not_auto_approved(self):
        r=classify(pitch(),[football(status="NS")])
        self.assertNotEqual(r["state"],"STRICT")

    def test_unique_provider_fixtures(self):
        self.assertTrue(verify_fixture_uniqueness([football(123),football(456)]))
        self.assertFalse(verify_fixture_uniqueness([football(123),football(123)]))

    def test_duplicate_pitch_id_invalidates_both(self):
        pair={"state":"STRICT","football_id":123,"matched":{"football_id":123}}
        rows=[{"pitch_match_id":"m_ABC123",**pair},
              {"pitch_match_id":"m_ABC123",**pair}]
        no_duplicate_mapping(rows)
        self.assertTrue(all(r["football_id"] is None for r in rows))
        self.assertTrue(all(r["state"].startswith("REVIEW_DUPLICATE") for r in rows))

    def test_duplicate_football_fixture_invalidates_both(self):
        rows=[{"pitch_match_id":"m_ABC123","football_id":123,"state":"STRICT"},
              {"pitch_match_id":"m_XYZ789","football_id":123,"state":"STRICT"}]
        no_duplicate_mapping(rows)
        self.assertTrue(all(r["football_id"] is None for r in rows))

    def test_previous_verified_id_must_match_independent_match(self):
        s=pitch()
        out=evaluate([s],{("La Liga",2026):[football()]})
        self.assertEqual(out[0]["independent_crosscheck"],"CONSISTENT")
        out=evaluate([s],{("La Liga",2026):[football(456)]})
        self.assertEqual(out[0]["independent_crosscheck"],"CONFLICT")

    def test_missing_or_invalid_kickoff_rejected(self):
        self.assertEqual(classify(pitch(when="not-a-date"),[football()])["state"],
                         "REVIEW_INVALID_KICKOFF")

    def test_null_result_rejected(self):
        p=pitch();p["score_home"]=None
        self.assertNotEqual(classify(p,[football()])["state"],"STRICT")

if __name__=="__main__":
    unittest.main()
