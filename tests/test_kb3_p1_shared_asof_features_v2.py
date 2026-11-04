"""P1-01: no-network negative safety tests and deterministic TRAIN/FORWARD parity.

All rows below are synthetic, NOT real signed host/provider receipts or FIT.
"""
from __future__ import annotations
import copy
import unittest

from src.kb3_p1_shared_asof_features_v2 import (
    SCHEMA, SharedAsOfError, build_shared_features, compare_same_asof,
)

H = "a" * 64
X = "b" * 64


def snapshot(time="2026-11-04T17:40:00Z"):
    return {"source_class": "NETWORK_OBSERVED",
            "observed_completed_at_utc": time, "source_sha256": H}


def sample():
    target = {"league": "ESP", "fixture_id": "m_target",
              "home_team_id": "A", "away_team_id": "B",
              "kickoff_utc": "2026-11-04T20:00:00Z",
              "season_start_year": 2026}
    old = {"league": "ESP", "fixture_id": "m_old",
           "home_team_id": "A", "away_team_id": "C",
           "kickoff_utc": "2026-11-01T12:00:00Z",
           "season_start_year": 2026, "status": "FINISHED",
           "goals_home_90": 2, "goals_away_90": 1,
           "result_receipt": {
               "source_class": "NETWORK_OBSERVED",
               "observed_completed_at_utc": "2026-11-01T16:00:00Z",
               "captured_at_utc": "2026-11-01T16:10:00Z",
               "source_sha256": H}}
    recent = copy.deepcopy(old)
    recent.update({
        "fixture_id": "m_recent",
        "home_team_id": "D", "away_team_id": "A",
        "kickoff_utc": "2026-11-04T14:00:00Z",
        "goals_home_90": 1, "goals_away_90": 1,
        "result_receipt": {
            "source_class": "NETWORK_OBSERVED",
            "observed_completed_at_utc": "2026-11-04T17:20:00Z",
            "captured_at_utc": "2026-11-04T17:30:00Z",
            "source_sha256": H,
        },
        "xgh": 1.3, "xga": 0.7,
        "xgh_receipt": {
            "source_class": "NETWORK_OBSERVED",
            "observed_completed_at_utc": "2026-11-04T17:25:00Z",
            "captured_at_utc": "2026-11-04T17:35:00Z",
            "source_sha256": X,
        },
        "xga_receipt": {
            "source_class": "NETWORK_OBSERVED",
            "observed_completed_at_utc": "2026-11-04T17:25:00Z",
            "captured_at_utc": "2026-11-04T17:35:00Z",
            "source_sha256": X,
        }
    })
    for_away = copy.deepcopy(old)
    for_away.update({
        "fixture_id": "m_away",
        "home_team_id": "B", "away_team_id": "E",
        "kickoff_utc": "2026-11-02T12:00:00Z",
        "goals_home_90": 0, "goals_away_90": 1,
        "result_receipt": {
            "source_class": "NETWORK_OBSERVED",
            "observed_completed_at_utc": "2026-11-02T16:00:00Z",
            "captured_at_utc": "2026-11-02T16:05:00Z",
            "source_sha256": H,
        },
    })
    return {"target": target, "cutoff_utc": "2026-11-04T18:00:00Z",
            "target_receipt": snapshot(),
            "predecessor_rows": [recent, old, for_away]}


def run(purpose="TRAIN", **updates):
    args = sample()
    args.update(updates)
    return build_shared_features(purpose=purpose, **args)


class SharedAsOfV2Safety(unittest.TestCase):
    def test_true_same_asof_train_forward_same_features_hash_lineage(self):
        a = run("TRAIN")
        b = run("FORWARD")
        self.assertEqual(a["schema"], SCHEMA)
        self.assertEqual(a["canonical_features_sha256"],
                         b["canonical_features_sha256"])
        self.assertEqual(a["features"], b["features"])
        self.assertEqual(a["missing_flags"], b["missing_flags"])
        self.assertEqual(a["lineage"], b["lineage"])
        self.assertEqual(a["feature_availability"], b["feature_availability"])
        self.assertTrue(compare_same_asof(a, b)["same_asof_feature_parity"])
        self.assertFalse(a["training_allowed"])
        self.assertFalse(b["production_approved"])

    def test_nearby_predecessor_captured_before_cutoff_but_under_48h(self):
        a = run()
        self.assertEqual(a["accepted_predecessor_count"], 3)
        self.assertEqual(a["features"]["home_games_available"], 2)
        self.assertEqual(a["features"]["home_days_since_last_kickoff"],
                         round(4/24, 4))
        self.assertTrue(any(x["fixture_id"] == "m_recent" for x in a["lineage"]))
        self.assertFalse(a["original_provider_first_published_at_certified"])

    def test_result_after_cutoff_is_not_used(self):
        s = sample()
        s["predecessor_rows"][0]["result_receipt"][
            "captured_at_utc"] = "2026-11-04T18:01:00Z"
        a = build_shared_features(purpose="TRAIN", **s)
        self.assertEqual(a["accepted_predecessor_count"], 2)
        self.assertEqual(a["features"]["home_days_since_last_kickoff"],
                         round((__import__("datetime").datetime.fromisoformat(
                             "2026-11-04T18:00:00+00:00") -
                             __import__("datetime").datetime.fromisoformat(
                             "2026-11-01T12:00:00+00:00")
                         ).total_seconds()/86400,4))

    def test_result_source_observed_before_three_hour_minimum_is_excluded(self):
        s = sample()
        s["predecessor_rows"][0]["result_receipt"].update({
            "observed_completed_at_utc": "2026-11-04T16:59:00Z",
            "captured_at_utc": "2026-11-04T17:40:00Z",
        })
        a = build_shared_features(purpose="FORWARD", **s)
        self.assertEqual(a["accepted_predecessor_count"], 2)
        self.assertEqual(a["excluded"]["RESULT_NOT_AVAILABLE_AT_CUTOFF"], 1)

    def test_missing_xg_is_null_never_zero(self):
        s = sample()
        s["predecessor_rows"][0]["xga"] = None
        s["predecessor_rows"][0]["xga_receipt"] = None
        r = build_shared_features(purpose="TRAIN", **s)
        self.assertEqual(r["features"]["home_all_5_xga_n"], 0)
        self.assertEqual(r["features"]["home_all_5_xga_avg"], None)
        self.assertTrue(r["missing_flags"]["home_all_5_xga"])

    def test_xg_after_cutoff_does_not_leak_to_model(self):
        s = sample()
        s["predecessor_rows"][0]["xga_receipt"]["captured_at_utc"] = (
            "2026-11-04T18:01:00Z")
        r = build_shared_features(purpose="TRAIN", **s)
        self.assertEqual(r["features"]["home_all_5_xga_n"], 0)
        self.assertEqual(r["excluded"]["XG_SOURCE_NOT_AVAILABLE_AT_CUTOFF"], 1)
        self.assertEqual(r["accepted_predecessor_count"], 3)

    def test_future_target_result_cannot_be_feature(self):
        s = sample()
        s["target"]["score_home"] = 4
        with self.assertRaisesRegex(SharedAsOfError, "TARGET_LABEL_IN_FEATURE_SOURCE"):
            build_shared_features(purpose="TRAIN", **s)

    def test_reconstructed_history_refused(self):
        s = sample()
        s["predecessor_rows"][0]["result_receipt"]["source_class"] = (
            "HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT")
        with self.assertRaisesRegex(SharedAsOfError,
                                    "HISTORICAL_LATER_RECONSTRUCTION_NOT_PIT"):
            build_shared_features(purpose="TRAIN", **s)

    def test_forecast_after_90min_refused(self):
        s = sample()
        s["cutoff_utc"] = "2026-11-04T19:00:00Z"
        with self.assertRaisesRegex(SharedAsOfError,
                                    "TARGET_EARLY_90MIN_REQUIRED"):
            build_shared_features(purpose="FORWARD", **s)

    def test_protected_english_fixture_refused(self):
        s = sample()
        s["target"]["league"] = "ENG"
        with self.assertRaisesRegex(SharedAsOfError, "PROTECTED_OR_UNKNOWN_LEAGUE"):
            build_shared_features(purpose="TRAIN", **s)

    def test_duplicate_or_target_as_predecessor_refused(self):
        s = sample()
        s["predecessor_rows"].append(copy.deepcopy(s["predecessor_rows"][0]))
        with self.assertRaisesRegex(SharedAsOfError, "DUPLICATE_PREDECESSOR_ID"):
            build_shared_features(purpose="TRAIN", **s)
        s = sample()
        s["predecessor_rows"][0]["fixture_id"] = "m_target"
        with self.assertRaisesRegex(SharedAsOfError, "TARGET_RESULT_LEAK"):
            build_shared_features(purpose="FORWARD", **s)

    def test_bad_or_missing_receipt_proof_refused(self):
        s = sample()
        s["predecessor_rows"][0]["result_receipt"]["source_sha256"] = "selfhash"
        with self.assertRaisesRegex(SharedAsOfError, "REAL_RECEIPT_SHA256_REQUIRED"):
            build_shared_features(purpose="TRAIN", **s)
        s = sample()
        s["target_receipt"]["source_class"] = "RECONSTRUCTED"
        with self.assertRaisesRegex(SharedAsOfError,
                                    "TARGET_RECONSTRUCTED_OR_UNOBSERVED"):
            build_shared_features(purpose="FORWARD", **s)

    def test_source_row_revision_after_snapshot_refused(self):
        s = sample()
        s["predecessor_rows"][0]["result_receipt"][
            "result_record_updated_at_utc"] = "2026-11-04T19:00:00Z"
        with self.assertRaisesRegex(SharedAsOfError,
                                    "RESULT_ROW_MUTATED_AFTER_CAPTURE"):
            build_shared_features(purpose="TRAIN", **s)

    def test_same_fixture_different_cutoff_detects_drift(self):
        s = sample()
        a = build_shared_features(purpose="TRAIN", **s)
        s["cutoff_utc"] = "2026-11-04T17:00:00Z"
        s["target_receipt"] = snapshot("2026-11-04T16:30:00Z")
        b = build_shared_features(purpose="FORWARD", **s)
        with self.assertRaisesRegex(SharedAsOfError,
                                    "TRAIN_FORWARD_FEATURE_CONTRACT_DRIFT"):
            compare_same_asof(a,b)

    def test_deterministic_over_input_order_and_hash(self):
        s=sample()
        a=build_shared_features(purpose="TRAIN", **s)
        s["predecessor_rows"].reverse()
        b=build_shared_features(purpose="TRAIN", **s)
        self.assertEqual(a["canonical_features_sha256"],
                         b["canonical_features_sha256"])


if __name__ == "__main__":
    unittest.main()
