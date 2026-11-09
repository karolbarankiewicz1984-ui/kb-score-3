"""Unit checks for the fail-closed CatBoost research parity audit."""
import unittest
from src.kb3_features import digest
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
        contract={"result_min_lag_hours":3,"ordered_features":["a","b"]}
        sha=digest(contract)
        train={"historical_result_lag_hours":3,"independent_pit_certified":True,
               "shared_feature_contract_sha256":sha}
        forward={"result_maturity_hours":3,"independent_pit_certified":True,
                 "shared_feature_contract_sha256":sha}
        manifest={"feature_contract_sha256":sha}
        manifest["manifest_sha256"]=digest(manifest)
        r=assess(train,forward,contract_document=contract,
                 train_manifest=manifest,forward_manifest=manifest)
        self.assertTrue(r["same_asof_semantics_proven"])
        self.assertFalse(r["champion_eligible"])

    def test_matching_arbitrary_text_and_flags_are_not_proof(self):
        a={"historical_result_lag_hours":3,"independent_pit_certified":True,
           "shared_feature_contract_sha256":"verified-contract"}
        b={**a,"result_maturity_hours":3}
        self.assertFalse(assess(a,b)["same_asof_semantics_proven"])

    def test_nan_infinite_negative_and_boolean_lags_fail_closed(self):
        for lag in (float('nan'),float('inf'),-1,True,None,"3"):
            self.assertFalse(assess({"historical_result_lag_hours":lag},
                {"result_maturity_hours":lag})["same_asof_semantics_proven"])

    def test_same_lag_failure_does_not_misreport_48h_vs_3h(self):
        r=assess({"historical_result_lag_hours":3},{"result_maturity_hours":3})
        self.assertNotIn("P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS",r["blocking_reasons"])

if __name__=="__main__":
    unittest.main()
