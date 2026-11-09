"""Unit checks for the fail-closed CatBoost research parity audit."""
import unittest
from scripts.kb3_catboost_feature_semantics_gate import assess

class SemanticsGateTests(unittest.TestCase):
    def test_frozen_48h_vs_forward_3h_blocked(self):
        r=assess()
        self.assertFalse(r["same_asof_semantics_proven"])
        self.assertFalse(r["champion_eligible"])
        self.assertIn("P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS",
                      r["blocking_reasons"])

    def test_same_lag_without_proof_still_blocked(self):
        r=assess({"historical_result_lag_hours":3},
                 {"result_maturity_hours":3})
        self.assertFalse(r["same_asof_semantics_proven"])

    def test_same_contract_and_certified_sources_can_pass_parity_only(self):
        train={"historical_result_lag_hours":3,"independent_pit_certified":True,
               "shared_feature_contract_sha256":"verified-contract"}
        forward={"result_maturity_hours":3,"independent_pit_certified":True,
                 "shared_feature_contract_sha256":"verified-contract"}
        r=assess(train,forward)
        self.assertTrue(r["same_asof_semantics_proven"])
        self.assertFalse(r["champion_eligible"])

if __name__=="__main__":
    unittest.main()
