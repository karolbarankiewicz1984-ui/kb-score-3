import unittest
from scripts.kb3_catboost_v3_eligibility_triage import assess

class EligibilityTriageTests(unittest.TestCase):
    def setUp(self):
        self.inventory=dict(table_counts=dict(observations=4401,finished_fixture_index=8710),
            observations_recorded_after_target_kickoff=4401,
            fixture_listing_recorded_after_target_kickoff=8710,
            observations_with_provider_first_published=0,
            integrity="ok",source_unchanged=True)
    def test_late_history_does_not_become_training(self):
        r=assess(self.inventory)
        self.assertEqual(r["formally_admitted_v3_train_rows"],0)
        self.assertFalse(r["real_v3_training_permitted"])
        self.assertEqual(r["historical_target_late_observations"],4401)
    def test_corrupt_inventory_rejected(self):
        self.inventory["observations_recorded_after_target_kickoff"]=4402
        with self.assertRaises(ValueError):assess(self.inventory)
    def test_untrusted_db_rejected(self):
        self.inventory["source_unchanged"]=False
        with self.assertRaises(ValueError):assess(self.inventory)
    def test_prior_match_late_not_necessarily_late_for_later_target(self):
        r=assess(self.inventory)
        self.assertIn("LATER target cutoff",r["critical_distinction"])
if __name__=="__main__":unittest.main()
