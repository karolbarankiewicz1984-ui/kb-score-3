import unittest
from scripts.step14_six_2023_historic_fpl_player_xg_reconstruction import run,inspect_one,FPLLineageError
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources
class OldSixXG(unittest.TestCase):
 def test_six_public_2023_old_clocks(self):
    src=[x for x in independently_pinned_sources() if x["season"]=="2023-24" and x["ft"]<380]
    self.assertEqual([x["ft"] for x in src],[59,70,140,208,250,313])
 def test_source_missing_real_player_blob_rejected(self):
    src=next(x for x in independently_pinned_sources() if x["ft"]==59)
    with self.assertRaises(FPLLineageError):
        inspect_one(src,fetcher=lambda url,**k:b"")
 def test_no_fake_historic_xg_on_missing_bytes(self):
    d=run(fetcher=lambda url,**k:b"")
    self.assertEqual(d["source_count"],6)
    self.assertEqual(d["player_xg_source_verified"],0)
    self.assertFalse(d["training_allowed"])
 def test_no_original_pitchapi_equivalence_in_source_schema(self):
    d=run(fetcher=lambda url,**k:b"")
    self.assertTrue(d["FPL_Opta_player_xg_not_original_PitchAPI_team_xg"])
    self.assertFalse(d["gate14_pass"])
if __name__=="__main__":unittest.main()
