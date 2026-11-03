"""Offline isolation, catalogue identity, chronology, no-future-result tests."""
import copy
import unittest

from scripts.kb3_ucl_pitchapi_collector import (
    choose_ucl, validate_listing, prematch_targets, historical_samples,
    UCLCaptureError, CURRENT, PREVIOUS,
)


def fixture(mid="m_ABC123", ko="2026-11-03T20:00:00Z", status="not_started"):
    return {
        "id": mid, "time_utc": ko, "status": status,
        "home_team": {"id": "t_ABC123", "name": "Example Home"},
        "away_team": {"id": "t_DEF456", "name": "Example Away"},
        "score_home": None if status != "finished" else 2,
        "score_away": None if status != "finished" else 1,
    }


class UCLCollectorTests(unittest.TestCase):
    def test_catalog_selects_exact_uefa_not_afc_or_womens(self):
        cat = {"leagues": [
            {"id": "l_AAAAAA", "name": "AFC Champions League", "seasons": [CURRENT]},
            {"id": "l_BBBBBB", "name": "UEFA Women's Champions League", "seasons": [CURRENT]},
            {"id": "l_CCCCCC", "name": "UEFA Champions League", "seasons": [PREVIOUS, CURRENT], "is_free": True}
        ]}
        league, state = choose_ucl(cat)
        self.assertEqual(state, "UCL_CATALOG_MATCHED")
        self.assertEqual(league["id"], "l_CCCCCC")

    def test_catalog_missing_not_promoted_to_available(self):
        league, state = choose_ucl({"leagues": []})
        self.assertIsNone(league)
        self.assertEqual(state, "UCL_NOT_IN_PROVIDER_CATALOG")
        self.assertEqual(choose_ucl({"leagues": [
            {"id": "l_AAAAAA", "name": "UEFA Champions League", "seasons": [PREVIOUS]}
        ]})[1], "UCL_2026_27_NOT_AVAILABLE")

    def test_catalog_rejects_paid_scope_without_upgrading(self):
        league, state = choose_ucl({"leagues": [
            {"id": "l_AAAAAA", "name": "UEFA Champions League",
             "seasons": [CURRENT], "is_free": False}
        ]})
        self.assertIsNone(league)
        self.assertEqual(state, "UCL_NOT_FREE_IN_CURRENT_PLAN")

    def test_duplicate_native_match_id_rejected(self):
        game = fixture()
        with self.assertRaises(UCLCaptureError):
            validate_listing({"matches": [game, copy.deepcopy(game)]}, CURRENT)

    def test_future_score_rejected_as_leakage(self):
        game = fixture()
        game["score_home"] = 1
        with self.assertRaises(UCLCaptureError):
            validate_listing({"matches": [game]}, CURRENT)

    def test_prematch_90_min_and_96h(self):
        base = "2026-11-03T11:00:00Z"
        games = [
            fixture("m_AAAAAA", "2026-11-03T12:20:00Z"),
            fixture("m_BBBBBB", "2026-11-03T12:30:00Z"),
            fixture("m_CCCCCC", "2026-11-03T20:00:00Z"),
            fixture("m_DDDDDD", "2026-11-07T11:01:00Z"),
            fixture("m_EEEEEE", "2026-11-03T20:00:00Z", "finished"),
        ]
        self.assertEqual([x["id"] for x in prematch_targets(games, base)],
                         ["m_BBBBBB", "m_CCCCCC"])

    def test_only_finished_matches_three_hours_old_sampled(self):
        history = [
            fixture("m_AAAAAA", "2026-11-03T10:00:00Z", "finished"),
            fixture("m_BBBBBB", "2026-11-03T08:59:00Z", "finished"),
            fixture("m_CCCCCC", "2026-11-02T20:00:00Z", "finished"),
            fixture("m_DDDDDD", "2026-11-01T20:00:00Z", "not_started"),
        ]
        actual = historical_samples(history, [], "2026-11-03T12:00:00Z")
        self.assertEqual([x["id"] for x in actual], ["m_BBBBBB", "m_CCCCCC"])

    def test_valid_native_fixture_and_no_special_expected_count(self):
        games, states = validate_listing({"matches": [
            fixture("m_AAAAAA"), fixture("m_BBBBBB", "2026-11-01T20:00:00Z", "finished")
        ]}, CURRENT)
        self.assertEqual(len(games), 2)
        self.assertEqual(states["finished"], 1)


if __name__ == "__main__":
    unittest.main()
