"""Gate17: authentic older reports explicitly prohibit native xG model fitting."""
import unittest
from src.kb3_step17_xg_model_gate import actual_readiness
from src.kb3_step17_xg_capture import MAX_CALLS,MAX_PAIRS_PER_LEAGUE
class NativeXGModelAdmissionTests(unittest.TestCase):
 def test_real_historical_complete_xg_is_scarce_and_wrong_definition(self):
    j=actual_readiness()
    self.assertEqual(j["historical_alternative_FPL_player_xg5_complete_TRAIN_760"],40)
    self.assertEqual(j["historical_alternative_FPL_player_xg5_complete_VALIDATION_380"],107)
    self.assertEqual(j["native_PitchAPI_2023_25_asof_qualified_TRAIN"],0)
    self.assertEqual(j["native_PitchAPI_2023_25_asof_qualified_VALIDATION"],0)
    self.assertFalse(j["FPL_Opta_player_sum_is_native_pitchapi_team_xg"])
    self.assertFalse(j["model_fitted"])
    self.assertFalse(j["production_approved"])
    self.assertFalse(j["test_premier_league_2026_27_opened"])
    self.assertEqual(j["gate17"],"PENDING")
 def test_budget_is_bounded_and_no_silent_auto_fit(self):
    self.assertEqual((MAX_CALLS,MAX_PAIRS_PER_LEAGUE),(33,1))
    j=actual_readiness()
    self.assertEqual(j["status"],"BLOCKED_NO_NATIVE_XG_TRAIN_VALIDATION_COHORT")
    self.assertTrue(j["unknown_overlap_with_exact_720_train_and_374_valid"])
if __name__=="__main__":unittest.main()
