"""Offline safety regression for separate 8-league fitted-M0 release."""
import unittest
from datetime import datetime, timedelta, timezone

from scripts.step16_m0_720train_eight_league_live import (
    LEAGUES, MODEL, ResearchStreamError, load_release, match_hash,
    new_forecasts, selected_catalog, settle_existing, verify_seasons,
)

UTC = timezone.utc
NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


def fixture(id_, h, a, when, status, gh=None, ga=None):
    return {"id": "m_" + id_, "home_team": {"id": "t_" + h, "name": h},
            "away_team": {"id": "t_" + a, "name": a},
            "time_utc": when.isoformat().replace("+00:00", "Z"),
            "status": status, "score_home": gh, "score_away": ga}


def samples():
    finished = []
    for i in range(6):
        finished.append(fixture("A%05d" % i, "HOME01", "OTHER1",
                                NOW - timedelta(days=30-i), "finished", 2, 1))
        finished.append(fixture("B%05d" % i, "AWAY01", "OTHER2",
                                NOW - timedelta(days=30-i), "finished", 0, 1))
    future = fixture("ZZ0001", "HOME01", "AWAY01",
                     NOW + timedelta(hours=28), "upcoming")
    return future, finished


class TestM0720Research(unittest.TestCase):
    def test_release_is_exact_fitted_candidate_and_excludes_test(self):
        params, ps, rs = load_release()
        self.assertEqual(len(LEAGUES), 8)
        self.assertEqual([x[0] for x in LEAGUES],
                         ["ESP", "ITA", "GER", "FRA", "NED", "BEL", "TUR", "POL"])
        self.assertNotIn("ENG", [x[0] for x in LEAGUES])
        self.assertEqual((params.base_home_goals, params.elo_goal_elasticity),
                         (1.6447363878515198, 0.6))
        self.assertEqual(len(ps), 64)
        self.assertEqual(len(rs), 64)
        self.assertEqual(MODEL, "M0_720TRAIN_8LEAGUE_RESEARCH_V1")

    def test_real_coverage_respects_309_313_prior(self):
        self.assertEqual(next(x for x in LEAGUES if x[0] == "NED")[4], 309)
        self.assertEqual(next(x for x in LEAGUES if x[0] == "BEL")[4], 313)

    def test_exact_eight_composite_country_and_name(self):
        cat = {"leagues": [
            {"id": "l_%06d" % i, "country_code": code, "name": title,
             "seasons": ["2025/2026", "2026/2027"]}
            for i, (code, title, _, _, _) in enumerate(LEAGUES)]}
        chosen = selected_catalog(cat)
        self.assertEqual(len(chosen), 8)
        cat["leagues"].append({"id": "l_999999", "country_code": "ESP",
                                "name": "LaLiga",
                                "seasons": ["2025/2026", "2026/2027"]})
        with self.assertRaisesRegex(ResearchStreamError, "AMBIGUOUS"):
            selected_catalog(cat)

    def test_prematch_one_unique_fitted_prediction(self):
        p, sha, rel = load_release()
        future, previous = samples()
        rows, coverage = new_forecasts("POL", "Ekstraklasa", [future], previous, NOW,
                            p, sha, rel, "a"*64,
                            NOW.isoformat().replace("+00:00", "Z"), set())
        self.assertEqual(len(rows), 1)
        self.assertEqual(coverage["completed_predecessors"], 12)
        self.assertEqual(rows[0]["parameter_status"],
                         "FITTED_720TRAIN_RESEARCH_UNVALIDATED_TRANSFER")
        self.assertAlmostEqual(sum(rows[0]["p_1x2"].values()), 1.0)
        self.assertGreater(rows[0]["past_matches_home"], 5)
        self.assertFalse(rows[0]["automatic_betting_or_production"])
        no_dup, _ = new_forecasts("POL", "Ekstraklasa", [future], previous, NOW,
                            p, sha, rel, "a"*64,
                            NOW.isoformat().replace("+00:00", "Z"),
                            {("POL", match_hash("POL", future["id"]))})
        self.assertEqual(no_dup, [])

    def test_no_future_finished_result_can_enter_elo(self):
        p, sha, rel = load_release()
        future, previous = samples()
        previous.append(fixture("U00001", "HOME01", "AWAY01",
                                NOW + timedelta(hours=12), "finished", 25, 0))
        rows, info = new_forecasts("POL", "Ekstraklasa", [future], previous, NOW,
                            p, sha, rel, "a"*64,
                            NOW.isoformat().replace("+00:00", "Z"), set())
        self.assertEqual(len(rows), 1)
        self.assertEqual(info["completed_predecessors"], 12)

    def test_90minute_minimum_before_kickoff(self):
        p, sha, rel = load_release()
        future, previous = samples()
        future["time_utc"] = (NOW + timedelta(minutes=89)).isoformat()
        rows, _ = new_forecasts("POL", "Ekstraklasa", [future], previous, NOW,
                            p, sha, rel, "a"*64,
                            NOW.isoformat().replace("+00:00", "Z"), set())
        self.assertEqual(rows, [])

    def test_genuine_later_settlement_and_metrics(self):
        p, sha, rel = load_release()
        future, previous = samples()
        forecasts, _ = new_forecasts("POL", "Ekstraklasa", [future], previous, NOW,
                            p, sha, rel, "a"*64,
                            NOW.isoformat().replace("+00:00", "Z"), set())
        actual = dict(future, status="finished", score_home=3, score_away=1)
        later = NOW + timedelta(days=3)
        prior = {("POL", match_hash("POL", future["id"])): forecasts[0]}
        scores = settle_existing(prior, {}, {"POL": [actual]}, later,
                                later.isoformat().replace("+00:00", "Z"), "b"*64)
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["result_1x2"], "1")
        self.assertGreater(scores[0]["brier_sum3"], 0)
        self.assertGreater(scores[0]["log_loss"], 0)
        self.assertEqual(settle_existing(prior,
            {("POL", match_hash("POL", future["id"])): scores[0]},
            {"POL": [actual]}, later,
            later.isoformat().replace("+00:00", "Z"), "b"*64), [])

    def test_never_accept_finished_target_as_new_forecast(self):
        p, sha, rel = load_release()
        future, previous = samples()
        future["status"] = "finished"
        future["score_home"], future["score_away"] = 1, 0
        rows, _ = new_forecasts("POL", "Ekstraklasa", [future], previous, NOW,
                               p, sha, rel, "a"*64,
                               NOW.isoformat().replace("+00:00", "Z"), set())
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
