"""Fail-closed Elo and xG readiness tests; no training or real TEST."""
import copy,unittest
from src.kb3_features import EloParameters
from src.kb3_step14_elo_xg_readiness import (
    ChainError,validate_contract,_full_elo_chain_gates,_xg_gates,assess,
)
from src.kb3_step14_multiseason_pit import SCHEMA as SOURCE_SCHEMA

def fake():
    return {
     "schema":SOURCE_SCHEMA,"gate14_pass":False,"m1_fit_allowed":False,
     "verified_three_season_public_sources":{
       "2023-24":{"finished_earlier_ft_in_blob":70},
       "2024-25":{"finished_earlier_ft_in_blob":60},
       "2025-26":{"finished_earlier_ft_in_blob":0}},
     "owner_local_four_fixture_source_join":[{
        "official_m1_training_allowed":False,
        "full_historical_pitchapi_pit_proven":False}],
    }

class EloXGReadinessTests(unittest.TestCase):
    def test_original_elo_defaults_must_stay_frozen(self):
        validate_contract(EloParameters())
        with self.assertRaisesRegex(ChainError,"ORIGINAL_ELO"):
            validate_contract(EloParameters(k=25.0))
    def test_full_chain_not_conflated_with_partial_public_results(self):
        e=_full_elo_chain_gates(fake())
        self.assertFalse(e["full_original_pitchapi_native_elo_chain_historical_pit_certified"])
        self.assertFalse(e["historical_input_full_380_by_season"]["2023-24"]["full_380_proven"])
        self.assertFalse(e["historical_input_full_380_by_season"]["2024-25"]["full_380_proven"])
    def test_xg_real_october2026_not_historical_public_clock(self):
        x=_xg_gates(__import__("pathlib").Path(__file__).resolve().parents[1])
        self.assertFalse(x["original_pitchapi_2023_2026_historical_team_xg_published_at_proven"])
        self.assertFalse(x["historical_xg_valid_for_official_m1"])
        self.assertTrue(x["fpl_player_xg_is_NOT_assumed_equivalent_to_pitchapi_team_xg"])
    def test_eligibility_not_auto_escalated(self):
        e=assess(fake())
        self.assertFalse(e["independent_eligibility_decision"]["training_allowed"])
        self.assertEqual(e["independent_eligibility_decision"]["train_pit_eligible"],0)
    def test_fake_native_training_flag_rejected(self):
        f=fake();f["owner_local_four_fixture_source_join"][0]["official_m1_training_allowed"]=True
        with self.assertRaisesRegex(ChainError,"PREMATURE_NATIVE"):
            assess(f)
    def test_source_gate_cannot_be_promoted(self):
        f=fake();f["gate14_pass"]=True
        with self.assertRaisesRegex(ChainError,"ESCALATED"):
            assess(f)
    def test_changed_source_counts_cannot_fake_full_elo(self):
        f=fake();f["verified_three_season_public_sources"]["2024-25"]["finished_earlier_ft_in_blob"]=380
        with self.assertRaisesRegex(ChainError,"SOURCE_COUNTS"):
            _full_elo_chain_gates(f)
    def test_prematch_xg_not_backfilled_with_zero(self):
        x=_xg_gates(__import__("pathlib").Path(__file__).resolve().parents[1])
        self.assertFalse(x["missing_historical_xg_replaced_by_zero"])

if __name__=="__main__":unittest.main()
