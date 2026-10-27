"""Synthetic fixtures only. Exact Step11 -> Step14 bridge regression checks."""
import copy
import unittest
from src.kb3_step14_bridge import (
    EXPECTED_FEATURES, EXPECTED_MISSING, EXPECTED_PROOFS,
    Step14BridgeError, _hash, inspect_step11_contract,
)


def fake_step11_snapshot():
    features = {key: 0.0 for key in EXPECTED_FEATURES}
    missing = {key: True for key in EXPECTED_MISSING}
    for side in ("home", "away"):
        for category in ("all", "venue"):
            for window in (5, 10, 15):
                stem = f"{side}_{category}_{window}"
                features[stem + "_n"] = 0
                for what in ("xg", "xga"):
                    features[stem + "_" + what + "_n"] = 0
                    features[stem + "_" + what + "_avg"] = None
    observed = "2026-10-27T08:00:00Z"
    proofs = {key: {"latest_required_observed_at_utc": observed,
                    "evidence_class": "OBSERVED_AT_NOT_PROVIDER_PUBLISHED",
                    "kind": "RESULT", "included_games": 0,
                    "fixtures_sha256": "a" * 64,
                    "provider_original_published_at_utc": None,
                    "training_allowed": False} for key in EXPECTED_PROOFS}
    result = {
        "schema": "kb3-step11-v0.5", "fixture_id": "SYNTHETIC_FIXTURE_A",
        "elo_parameters": {}, "elo_parameter_status": "PROVISIONAL_NOT_FITTED",
        "result_evidence_policy": "RECORDED_SOURCE_RESPONSE_HASHED_AS_OF_CUTOFF",
        "row_payload_at_snapshot_proven": True,
        "kickoff_utc": "2026-11-03T18:00:00Z",
        "feature_cutoff_utc": "2026-10-27T08:01:00Z",
        "mode": "observed", "availability_class": "OBSERVED_AT_NOT_CERTIFIED",
        "target_prematch_snapshot_certified": False,
        "training_allowed": False, "features": features,
        "missing_flags": missing, "lineage": [],
        "accepted_predecessor_count": 0,
        "excluded": {}, "note": "SYNTHETIC_CONTRACT_ONLY",
        "source_evidence": {"provider": "PitchAPI", "native_ids_only": True,
            "source_capture_id": "SYNTH14_RECEIPT", "source_chain_sha256": "b" * 64,
            "source_observed_at_utc": observed, "hash_chain_verified": True,
            "source_first_publication_time_known": False,
            "historical_pit_certified": False, "training_allowed": False,
            "multiseason_elo_status": "CURRENT_SEASON_ONLY"},
        "feature_availability": proofs,
    }
    result["sha256"] = _hash(result)
    return result


def reseal(value):
    value["sha256"] = _hash({k: v for k, v in value.items() if k != "sha256"})
    return value


class Step14BridgeContract(unittest.TestCase):
    def setUp(self):
        self.source = fake_step11_snapshot()

    def test_current_step11_exact_keys_and_count_without_values(self):
        report = inspect_step11_contract(self.source)
        self.assertEqual((report["full_feature_count"], report["full_missing_flag_count"],
                          report["full_provenance_count"]), (121, 38, 159))
        self.assertNotIn("features", report)
        self.assertNotIn("label_1x2", report)
        self.assertFalse(report["step14_real_fit_permitted"])

    def test_reject_real_training_override_even_with_rehashed_snapshot(self):
        x = copy.deepcopy(self.source)
        x["training_allowed"] = True
        with self.assertRaisesRegex(Step14BridgeError, "UNAPPROVED"):
            inspect_step11_contract(reseal(x))

    def test_reject_target_label_and_odds_extra_columns(self):
        for key in ("label_1x2", "odds_1x2", "goals_home_90"):
            x = copy.deepcopy(self.source)
            x[key] = 1
            with self.subTest(key=key), self.assertRaisesRegex(Step14BridgeError, "EXTRA_TARGET"):
                inspect_step11_contract(reseal(x))

    def test_reject_feature_odds_injection(self):
        x = copy.deepcopy(self.source)
        x["features"]["odds_1x2"] = 1.8
        with self.assertRaisesRegex(Step14BridgeError, "FEATURE_KEY"):
            inspect_step11_contract(reseal(x))

    def test_reject_missing_single_feature_provenance(self):
        x = copy.deepcopy(self.source)
        del x["feature_availability"]["home_all_5_points_avg"]
        with self.assertRaisesRegex(Step14BridgeError, "PROOF_MISSING"):
            inspect_step11_contract(reseal(x))

    def test_reject_future_observed_field_even_with_rehash(self):
        x = copy.deepcopy(self.source)
        x["feature_availability"]["away_all_5_xg_avg"]["latest_required_observed_at_utc"] = "2026-11-04T00:00:00Z"
        with self.assertRaisesRegex(Step14BridgeError, "OUTSIDE_ASOF"):
            inspect_step11_contract(reseal(x))

    def test_reject_unauthorized_provider_time(self):
        x = copy.deepcopy(self.source)
        x["feature_availability"]["home_all_5_xg_avg"]["provider_original_published_at_utc"] = "2026-10-01T00:00:00Z"
        with self.assertRaisesRegex(Step14BridgeError, "MISREPRESENTS"):
            inspect_step11_contract(reseal(x))

    def test_reject_post_cutoff_main_receipt(self):
        x = copy.deepcopy(self.source)
        x["source_evidence"]["source_observed_at_utc"] = "2026-10-27T08:02:00Z"
        with self.assertRaisesRegex(Step14BridgeError, "SOURCE_AFTER_CUTOFF"):
            inspect_step11_contract(reseal(x))

    def test_partial_xg_not_conflated_with_null(self):
        x = copy.deepcopy(self.source)
        stem = "home_all_5"
        x["features"][stem + "_n"] = 5
        x["features"][stem + "_xg_n"] = 2
        x["features"][stem + "_xg_avg"] = 1.2
        x["features"][stem + "_xga_n"] = 0
        x["features"][stem + "_xga_avg"] = None
        x["missing_flags"][stem + "_xg"] = True
        self.assertFalse(inspect_step11_contract(reseal(x))["step14_real_fit_permitted"])
        x["missing_flags"][stem + "_xg"] = False
        with self.assertRaisesRegex(Step14BridgeError, "PARTIAL_XG"):
            inspect_step11_contract(reseal(x))

    def test_reject_unmodified_signature_if_data_changes(self):
        x = copy.deepcopy(self.source)
        x["features"]["elo_home_minus_away"] = 12
        with self.assertRaisesRegex(Step14BridgeError, "SHA_MISMATCH"):
            inspect_step11_contract(x)

    def test_not_observed_mode_refused(self):
        x = copy.deepcopy(self.source)
        x["mode"] = "replay"
        with self.assertRaisesRegex(Step14BridgeError, "NOT_OBSERVED"):
            inspect_step11_contract(reseal(x))


if __name__ == "__main__":
    unittest.main()
