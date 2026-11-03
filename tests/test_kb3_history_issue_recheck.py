"""Offline adversarial tests for historical xG/card source rechecks."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.kb3_history_issue_recheck import (
    card_event_counts, xg_diagnostics, store_rechecks, candidates,
)
from scripts.kb3_historical_pitchapi_backfill import (
    put_rows, all_period_stat_items,
)
from src.kb3_historical_feature_quality import (
    add_fixture_rows, assess_and_cache, effective_stat,
)

MID="m_Aa1234"
HOME="t_Aa1234"
AWAY="t_Bb1234"
T="2025-05-05T17:00:00Z"
SOURCE="2026-11-03T13:00:00Z"
SHA="a"*64

def fixture():
    return {"id":MID,"scope":"ESP","season":"2024/2025",
      "status":"finished","time_utc":T,
      "home_team":{"id":HOME},"away_team":{"id":AWAY},
      "score_home":2,"score_away":0,
      "items":[],"xg_status":"XG_SHOTS_STATS_DISAGREE"}

def stats(h=".5",a=".8",cards=False):
    f=fixture()
    items=[{"key":"expected_goals","format_type":"double",
            "home":h,"away":a},
           {"key":"total_shots","home":"1","away":"1","format_type":"integer"}]
    if cards:
        items.append({"key":"yellow_cards","home":"2","away":None})
    return {"data":{"match_id":MID,"home_team":f["home_team"],
       "away_team":f["away_team"],"periods":[{"period":"All",
       "groups":[{"group_name":"Expected goals (xG)","items":items}]}]}}

def shots(h=.5,a=.8):
    return {"data":{"match_id":MID,"periods":[{"period":"All","shots":[
      {"id":"s_1","team_id":HOME,"expected_goals":h},
      {"id":"s_2","team_id":AWAY,"expected_goals":a}]}]}}

def events(*types):
    e=[]
    for i,(type_,team) in enumerate(types,1):
        e.append({"event_type":type_,"team_id":team,"minute":i*10})
    return {"data":{"match_id":MID,"events":e}}

def row(f=None):
    f=f or fixture()
    return {"scope":"ESP","season":"2024/2025","id":MID,
        "time_utc":T,"home_id":HOME,"away_id":AWAY,
        "goals_home":2,"goals_away":0,"observed_at":SOURCE,
        "items":f["items"],"stat_key_count":len(f["items"]),
        "xg_status":"XG_SHOTS_STATS_DISAGREE",
        "xg_home":None,"xg_away":None,
        "shots_home":None,"shots_away":None,
        "stats_sha":SHA,"shots_sha":SHA,"source_chain":SHA}

def issue(kind,status,**values):
    return {"scope":"ESP","match_id":MID,"issue_type":kind,
      "initial_issue":"SOURCE_MISSING","status":status,
      "observed_at_utc":SOURCE,
      "chain":SHA,"sha":SHA,"home":HOME,"away":AWAY,**values}

class RecheckTests(unittest.TestCase):
    def test_xg_persistent_difference_remains_quarantined(self):
        result=xg_diagnostics(stats(),shots(.1,.8),fixture())
        self.assertEqual(result["status"],"XG_DISAGREEMENT_PERSISTS")
        self.assertEqual(result["xg_abs_delta_home"],.4)
        self.assertIsNone(result["xg_verified_home"])

    def test_xg_reverify_requires_match_and_team_identity(self):
        result=xg_diagnostics(stats(),shots(),fixture())
        self.assertEqual(result["status"],"XG_REVERIFIED")
        self.assertEqual(result["xg_verified_home"],.5)
        wrong=stats();wrong["data"]["away_team"]["id"]="t_Aaaaaa"
        self.assertEqual(xg_diagnostics(wrong,shots(),fixture())["status"],
                         "XG_SOURCE_INVALID")
        other=shots();other["data"]["match_id"]="m_Aaaaaa"
        self.assertEqual(xg_diagnostics(stats(),other,fixture())["status"],
                         "XG_SOURCE_INVALID")

    def test_yellow_cards_explicit_not_red_or_substitution(self):
        status,h,a=card_event_counts(events(
            ("YellowCard",HOME),("RedCard",HOME),("YellowCard",AWAY),
            ("Substitution",HOME)),fixture())
        self.assertEqual((status,h,a),("EVENT_YELLOW_CONFIRMED",1,1))

    def test_no_zero_from_empty_or_wrong_match_or_unhandled_event(self):
        self.assertEqual(card_event_counts(events(),fixture())[0],
                         "EVENTS_EMPTY_OR_MISSING")
        wrong=events(("Goal",HOME));wrong["data"]["match_id"]="m_Bbbbbb"
        self.assertEqual(card_event_counts(wrong,fixture())[0],
                         "EVENTS_WRONG_MATCH_ID")
        self.assertEqual(card_event_counts(events(("OwnUnknown",HOME)),fixture())[0],
                         "EVENTS_MALFORMED_OR_UNKNOWN")
        self.assertEqual(card_event_counts(events(("Goal",HOME)),fixture()),
                         ("EVENT_YELLOW_CONFIRMED",0,0))

    def test_disagreement_with_existing_card_stat_blocks_recovery(self):
        f=fixture()
        f["items"]=[{"key":"yellow_cards","home":"2","away":None}]
        self.assertEqual(card_event_counts(events(("YellowCard",HOME)),f)[0],
                         "EVENTS_TEAM_STATS_CONFLICT")
        self.assertEqual(card_event_counts(events(("YellowCard",HOME),
                        ("YellowCard",HOME)),f),
                         ("EVENT_YELLOW_CONFIRMED",2,0))

    def test_append_only_issue_records_overlay_research_not_original(self):
        with tempfile.TemporaryDirectory() as d:
            original=Path(d)/"original.sqlite"
            rechecks=Path(d)/"rechecks.sqlite"
            f=fixture()
            f["items"]=[{"key":"fouls","home":"9","away":"13"},
                        {"key":"yellow_cards","home":"-","away":"0"}]
            add_fixture_rows(original,[("ESP","2024/2025",f,SOURCE,SHA)])
            put_rows(original,[row(f)])
            x=issue("XG","XG_REVERIFIED",xg_verified_home=.5,
                    xg_verified_away=.8,stats_xg_home=.5,stats_xg_away=.8,
                    shots_xg_home=.5,shots_xg_away=.8,
                    xg_abs_delta_home=0.,xg_abs_delta_away=0.)
            y=issue("YELLOW_CARDS","EVENT_YELLOW_CONFIRMED",
                    yellow_events_home=1,yellow_events_away=0)
            self.assertEqual(store_rechecks(rechecks,[x,y]),2)
            with self.assertRaises(sqlite3.IntegrityError):
                store_rechecks(rechecks,[x])
            with sqlite3.connect(rechecks) as db:
                with self.assertRaises(sqlite3.DatabaseError):
                    db.execute("UPDATE issue_rechecks SET status='FAKE'")
            rep=assess_and_cache(original,Path(d)/"after.json",
                                 recheck_db_path=rechecks)
            self.assertEqual(rep["append_only_recheck_overlays"]["verified_xg_overlay"],1)
            self.assertEqual(rep["append_only_recheck_overlays"]["recovered_yellow_cards"],1)
            self.assertEqual(rep["totals"]["xg_verified_matches"],1)
            with sqlite3.connect(original) as db:
                self.assertEqual(db.execute("SELECT xg_status FROM observations").fetchone()[0],
                                 "XG_SHOTS_STATS_DISAGREE")
                original_items=json.loads(db.execute(
                    "SELECT stat_items_json FROM observations").fetchone()[0])
                self.assertEqual(next(z for z in original_items
                                      if z["key"]=="yellow_cards")["home"],"-")
                obj=json.loads(db.execute(
                    "SELECT feature_json FROM rolling_feature_cache").fetchone()[0])
                self.assertFalse(obj["original_pit_certified"])

    def test_placeholder_does_not_cancel_validated_event_override(self):
        original={"items":[{"key":"yellow_cards","home":"-","away":"0"}],
                  "research_overrides":{"yellow_cards":{"home":2.0}}}
        self.assertEqual(effective_stat(original,"yellow_cards","home"),2.)
        self.assertEqual(effective_stat(original,"yellow_cards","away"),0.)
        self.assertIsNone(effective_stat(
            {"items":original["items"]},"yellow_cards","home"))

    def test_candidates_no_second_attempt_for_same_issue(self):
        with tempfile.TemporaryDirectory() as d:
            original=Path(d)/"original.sqlite"
            rechecks=Path(d)/"rechecks.sqlite"
            f=fixture();add_fixture_rows(original,[("ESP","2024/2025",f,SOURCE,SHA)])
            put_rows(original,[row(f)])
            x,c=candidates(original,rechecks)
            self.assertEqual((len(x),len(c)),(1,1))
            store_rechecks(rechecks,[issue("XG","XG_DISAGREEMENT_PERSISTS"),
                                    issue("YELLOW_CARDS","EVENTS_EMPTY_OR_MISSING")])
            x,c=candidates(original,rechecks)
            self.assertEqual((len(x),len(c)),(0,0))

if __name__=="__main__":
    unittest.main()
