"""Offline tests for larger native-only XG coverage and conservative claims."""
import unittest
from scripts.step11_pitch_three_league_xg30_once import (
    wilson_lower,choose_unique,COMPETITIONS,PER_LEAGUE,MAX_CALLS)
from scripts.step11_uefa_native_xg_capture_once import select_sample
from src.kb3_pitch_native import verify_native_shots
from test_step11_uefa_native_xg import games,shots,now

class ThreeLeagueCoverageTests(unittest.TestCase):
    def test_budget_is_bounded_to_34_one_provider_calls(self):
        self.assertEqual(PER_LEAGUE,10)
        self.assertEqual(MAX_CALLS,34)
        self.assertEqual(len(COMPETITIONS),3)

    def test_native_premier_league_selects_eng_only(self):
        catalog=[
            {"id":"a","name":"Premier League","country_code":"ENG","seasons":["2026/2027"]},
            {"id":"b","name":"Premier League","country_code":"CAN","seasons":["2026/2027"]}]
        self.assertEqual(choose_unique(catalog,"premier league")["id"],"a")

    def test_duplicate_premier_league_rejected(self):
        row={"id":"a","name":"Premier League","country_code":"ENG","seasons":["2026/2027"]}
        with self.assertRaisesRegex(ValueError,"NOT_UNIQUE"):
            choose_unique([row,dict(row)],"premier league")

    def test_sample_spans_many_actual_dates_without_duplicates(self):
        chosen,eligible=select_sample(games(90),now(),count=10)
        self.assertEqual(eligible,90)
        self.assertEqual(len(chosen),10)
        self.assertEqual(len({x["id"] for x in chosen}),10)
        self.assertGreaterEqual(len({x["time_utc"][:10] for x in chosen}),7)

    def test_one_bad_source_is_not_automatically_zero(self):
        fixture=games(1)[0]
        data=shots(fixture["id"])
        data["data"]["periods"][0]["shots"][0]["expected_goals"]=None
        status=verify_native_shots(fixture,data,observed_at_utc=now())
        self.assertIsNone(status["xg_home"])
        self.assertIsNone(status["xg_away"])
        self.assertNotEqual(status["shot_state"],"COMPLETE_SHOT_XG")

    def test_conference_only_two_real_kickoff_dates_is_valid_sample(self):
        source=games(20)
        for i,m in enumerate(source):
            m["time_utc"]="2026-09-01T15:00:00Z" if i%2 else "2026-09-08T15:00:00Z"
        chosen,eligible=select_sample(source,now(),count=10)
        self.assertEqual(len(chosen),10)
        self.assertEqual(eligible,20)
        self.assertEqual(len({m["time_utc"][:10] for m in chosen}),2)

    def test_archive_upload_runs_even_if_assertion_fails(self):
        from pathlib import Path
        workflow=Path(__file__).resolve().parents[1]/".github/workflows/kb3-step11-xg30-once.yml"
        code=workflow.read_text(encoding="utf8")
        self.assertIn("if: always()",code)
        self.assertIn("KB3_PITCH_3_LEAGUES_XG30_20261026.enc",code)

    def test_all_ten_complete_still_not_95pct_full_coverage(self):
        self.assertLess(wilson_lower(10,10),0.8)
        self.assertGreater(wilson_lower(10,10),0.7)

    def test_sample_one_tenth_missing_correctly_reflected(self):
        self.assertGreater(wilson_lower(9,10),0)
        self.assertLess(wilson_lower(9,10),wilson_lower(10,10))

    def test_wilson_rejects_invalid_or_boolean_denominator(self):
        for args in ((0,0),(11,10),(-1,10),(True,10),(1,False)):
            with self.subTest(args=args):
                with self.assertRaisesRegex(ValueError,"INVALID_COVERAGE"):
                    wilson_lower(*args)

if __name__=="__main__":
    unittest.main()
