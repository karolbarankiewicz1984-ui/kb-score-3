"""Regression: last N must follow actual fixture chronology, never xG availability."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from src.kb3_historical_feature_quality import (
    add_fixture_rows, assess_and_cache, rolling_window, raw_stat,
    FEATURE_VERSION, WINDOWS
)
from scripts.kb3_historical_pitchapi_backfill import put_rows

SHA="a"*64
CAPTURE="2026-11-03T12:00:00Z"
HOME="t_Aa1234"
AWAY="t_Bb1234"


def mk_fixture(i,home=HOME,away=AWAY,scope="ESP",year=2025):
    ko=datetime(year,5,1,tzinfo=timezone.utc)+timedelta(days=i)
    return {"id":"m_"+str(i).zfill(6),"time_utc":ko.isoformat().replace("+00:00","Z"),
            "status":"finished","home_team":{"id":home},"away_team":{"id":away},
            "score_home":2,"score_away":1,"scope":scope}


def as_index(f,scope="ESP",season="2024/2025"):
    return (scope,season,f,CAPTURE,SHA)


def db_observation(f,scope="ESP",verified=True):
    return {"scope":scope,"season":"2024/2025","id":f["id"],
            "time_utc":f["time_utc"],"home_id":f["home_team"]["id"],
            "away_id":f["away_team"]["id"],"goals_home":f["score_home"],
            "goals_away":f["score_away"],"observed_at":CAPTURE,
            "items":[{"key":"fouls","home":"12","away":"10"},
                     {"key":"corners","home":"5","away":"4"},
                     {"key":"total_shots","home":"13","away":"9"},
                     {"key":"yellow_cards","home":"2","away":"3"}],
            "stat_key_count":4,
            "xg_status":"VERIFIED" if verified else "XG_INCOMPLETE_OR_INVALID",
            "xg_home":1.25 if verified else None,
            "xg_away":.8 if verified else None,
            "shots_home":8 if verified else None,
            "shots_away":5 if verified else None,
            "stats_sha":SHA,"shots_sha":SHA,"source_chain":SHA}


def dict_fixture(f,scope="ESP"):
    return {"scope":scope,"season":"2024/2025","match_id":f["id"],
            "kickoff_utc":f["time_utc"],
            "home_team_id":f["home_team"]["id"],
            "away_team_id":f["away_team"]["id"],
            "goals_home_90":f["score_home"],
            "goals_away_90":f["score_away"]}


def as_obs(f,verified=True,scope="ESP"):
    return {"items":db_observation(f)["items"],
            "xg_status":"VERIFIED" if verified else "XG_INCOMPLETE_OR_INVALID",
            "xg_home":1.25 if verified else None,
            "xg_away":.8 if verified else None}


class HistoryFeaturesTests(unittest.TestCase):
    def test_last5_is_actual_five_not_five_available_xg(self):
        fixtures=[dict_fixture(mk_fixture(i)) for i in range(1,18)]
        # Exactly last five are 12..16, xG 15 is missing, xG 11 is present.
        observed={("ESP",f["match_id"]):as_obs(mk_fixture(int(f["match_id"][2:])))
                  for f in fixtures[:16] if f["match_id"]!="m_000015"}
        r=rolling_window(fixtures[:16],observed,HOME,5)
        self.assertTrue(r["history_complete"])
        self.assertEqual(r["stats_match_n"],4)
        self.assertEqual(r["metrics"]["xg_for"]["valid_n"],4)
        self.assertIsNone(r["metrics"]["xg_for"]["mean"])
        self.assertFalse(r["xg_complete"])
        self.assertEqual(r["metrics"]["goals_for"]["mean"],2.0)

    def test_last10_and_15_and_home_away(self):
        fixtures=[dict_fixture(mk_fixture(i)) for i in range(1,17)]
        observed={("ESP",f["match_id"]):as_obs(mk_fixture(i))
                  for i,f in enumerate(fixtures,1)}
        for n in WINDOWS:
            r=rolling_window(fixtures,observed,HOME,n)
            self.assertTrue(r["xg_complete"])
            self.assertEqual(r["metrics"]["xg_for"]["mean"],1.25)
        away=rolling_window(fixtures,observed,HOME,5,venue="away")
        self.assertEqual(away["actual_predecessors"],0)
        self.assertFalse(away["history_complete"])
        self.assertIsNone(away["metrics"]["xg_for"]["mean"])

    def test_provider_duplicate_stat_disagreement_is_missing(self):
        row={"items":[{"key":"fouls","home":"12","away":"10"},
                       {"key":"fouls","home":"14","away":"10"}]}
        self.assertIsNone(raw_stat(row,"fouls","home"))
        self.assertEqual(raw_stat(row,"fouls","away"),10)
        self.assertIsNone(raw_stat(row,"does_not_exist","home"))

    def test_no_future_values_and_strict_reconstructed_availability(self):
        fixtures=[dict_fixture(mk_fixture(i)) for i in range(1,18)]
        obs={("ESP",f["match_id"]):as_obs(mk_fixture(i))
             for i,f in enumerate(fixtures,1)}
        history=fixtures[:15]
        r=rolling_window(history,obs,HOME,15)
        self.assertTrue(r["xg_complete"])
        # The target's own statistics, despite being in obs, are not in history.
        self.assertEqual(r["metrics"]["xg_for"]["mean"],1.25)

    def test_fixture_index_immutable_and_quarantines_revision(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"test.sqlite"
            f=mk_fixture(1)
            self.assertEqual(add_fixture_rows(path,[as_index(f)]),(1,1))
            self.assertEqual(add_fixture_rows(path,[as_index(f)]),(0,1))
            broken=mk_fixture(1);broken["score_home"]=9
            with self.assertRaisesRegex(ValueError,"REVISION_QUARANTINE"):
                add_fixture_rows(path,[as_index(broken)])
            with sqlite3.connect(path) as db:
                with self.assertRaises(sqlite3.DatabaseError):
                    db.execute("UPDATE finished_fixture_index SET goals_home_90=9")

    def test_real_database_cache_and_aggregated_quality_report(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"test.sqlite"
            fixtures=[mk_fixture(i) for i in range(1,8)]
            self.assertEqual(add_fixture_rows(db,[as_index(f) for f in fixtures]),(7,7))
            put_rows(db,[db_observation(f) for f in fixtures])
            report=assess_and_cache(db,Path(d)/"quality.json")
            self.assertEqual(report["totals"]["targets_checked"],7)
            # For i=6, true five predecessors are all observed and verified.
            self.assertEqual(report["totals"]["pair_xg_5_complete"],2)
            self.assertEqual(report["totals"]["pair_xg_10_complete"],0)
            self.assertEqual(report["totals"]["pair_xg_15_complete"],0)
            self.assertFalse(report["full_feature_training_approved"])
            with sqlite3.connect(db) as cn:
                r=cn.execute("SELECT feature_json FROM rolling_feature_cache WHERE target_match_id=?",
                             ("m_000006",)).fetchone()
            self.assertIsNotNone(r)
            j=json.loads(r[0])
            self.assertEqual(j["schema"],FEATURE_VERSION)
            self.assertTrue(j["sides"]["home"]["all"]["5"]["xg_complete"])
            self.assertFalse(j["original_pit_certified"])
            self.assertFalse(j["training_approved"])

    def test_missing_one_previous_xg_is_not_allowed_to_look_earlier(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"test.sqlite"
            fixtures=[mk_fixture(i) for i in range(1,8)]
            add_fixture_rows(db,[as_index(f) for f in fixtures])
            # There is valid older xG, but 1 of the true last five is missing.
            put_rows(db,[db_observation(f) for f in fixtures if f["id"]!="m_000005"])
            report=assess_and_cache(db,Path(d)/"quality.json")
            self.assertEqual(report["totals"]["pair_xg_5_complete"],0)
            self.assertGreater(report["totals"]["missing_stat_match_count"],0)


if __name__=="__main__":
    unittest.main()
