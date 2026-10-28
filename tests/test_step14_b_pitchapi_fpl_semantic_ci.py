import json,unittest
from scripts.step14_b_pitchapi_fpl_semantic_ci_once import (
    compare_live,exact_current_native_graph_join,BSourceError,MAX_CALLS,SAMPLE_INDICES)
class Step14B(unittest.TestCase):
 def test_fixed_sampling_and_request_budget(self):
    self.assertEqual(MAX_CALLS,14)
    self.assertEqual(SAMPLE_INDICES,(20,84,148,212,276,340))
 def test_missing_secret_stops_before_any_network(self):
    with self.assertRaisesRegex(BSourceError,"SECRET_UNAVAILABLE"):
        compare_live("",provider_factory=lambda **kwargs:None,fetcher=lambda *a,**k:b"")
 def test_missing_native_games_fails(self):
    with self.assertRaises(Exception):
        exact_current_native_graph_join([],[],{"source_side_xg_values_IN_MEMORY_ONLY":{}})
 def test_never_approve_pitchapi_first_published_from_current_capture(self):
    from src.kb3_step14_pitchapi_xg_semantics import classify_historical_publication
    self.assertFalse(classify_historical_publication(
       {"captured_at_utc":"2026-10-28T15:00:00Z"},
       target_cutoff_utc="2023-09-15T18:00:00Z")["pit_eligible"])
if __name__=="__main__":unittest.main()
