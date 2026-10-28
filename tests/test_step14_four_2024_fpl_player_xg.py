import unittest
from scripts.step14_four_2024_historic_fpl_player_xg_reconstruction import run
class Old2024PlayerXG(unittest.TestCase):
 def test_four_pinned_and_absent_source_blocked(self):
    r=run(fetcher=lambda *args,**kw:b"")
    self.assertEqual(r["four_independent_old_2024_source_clocks_verified"],4)
    self.assertEqual(r["four_real_xg_sources_success"],0)
    self.assertFalse(r["training_allowed"])
 def test_never_auto_convert_player_xg_to_pitchapi(self):
    r=run(fetcher=lambda *args,**kw:b"")
    self.assertTrue(r["FPL_Opta_not_original_PitchAPI_xG"])
    self.assertEqual(r["original_train_pit_eligible"],0)
if __name__=="__main__":unittest.main()
