"""Offline history collection safety; fixtures are synthetic, no secret/API."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.kb3_historical_pitchapi_backfill import (
    SEASONS, EIGHT, select_scopes, validate_match_rows, select_batch,
    all_period_stat_items, native_xg_verified, put_rows, existing_ids, BackfillError,
)


def game(mid="m_Aa1234", dt="2025-07-01T12:00:00Z", state="finished"):
    return {"id":mid,"time_utc":dt,"status":state,
            "home_team":{"id":"t_Aa1234"},"away_team":{"id":"t_Bb1234"},
            "score_home":2 if state=="finished" else None,
            "score_away":1 if state=="finished" else None}


def stats(g=None):
    g=g or game()
    return {"match_id":g["id"],
      "home_team":g["home_team"],"away_team":g["away_team"],
      "periods":[{"period":"All","groups":[
        {"group_name":"Expected goals (xG)","items":[
          {"key":"expected_goals","format_type":"double","home":"0.4","away":"0.7"}]},
        {"group_name":"Other","items":[
          {"key":"fouls","home":"13","away":"8"},
          {"key":"corners","home":"4","away":"6"}]}]}]}


def shots(g=None):
    g=g or game()
    return {"match_id":g["id"],"periods":[{"period":"All","shots":[
      {"id":"s_1","team_id":g["home_team"]["id"],"expected_goals":.4},
      {"id":"s_2","team_id":g["away_team"]["id"],"expected_goals":.7}]}]}


class HistoricalBackfillTests(unittest.TestCase):
    def test_scopes_eight_leagues_and_uefa_only_no_eng_test(self):
        entries = []
        for c,n,aliases in EIGHT:
            entries.append({"id":"l_"+c+"123", "country_code":c,
              "name":next(iter(aliases)), "seasons":list(SEASONS), "is_free":True})
        entries += [
          {"id":"l_AAAAAA","name":"AFC Champions League","seasons":list(SEASONS),"is_free":True},
          {"id":"l_BBBBBB","name":"UEFA Champions League","seasons":list(SEASONS),"is_free":True},
          {"id":"l_CCCCCC","name":"Premier League","country_code":"ENG",
           "seasons":list(SEASONS),"is_free":True},
        ]
        scopes,status=select_scopes({"leagues":entries})
        self.assertEqual(status,"UCL_CATALOG_MATCHED")
        self.assertEqual(len(scopes),9*len(SEASONS))
        self.assertTrue(all(x[0] != "ENG" for x in scopes))

    def test_leakage_filter_finished_only_and_three_hour_lag(self):
        older=game("m_Aaaaaa",dt="2025-07-01T12:00:00Z")
        fresh=game("m_Bbbbbb",dt="2025-07-02T10:00:00Z")
        future=game("m_Cccccc",dt="2025-07-03T10:00:00Z",state="not_started")
        valid=validate_match_rows({"matches":[older,fresh,future]},
                                  "ESP","2025/2026","2025-07-02T12:00:00Z")
        self.assertEqual([x["id"] for x in valid],["m_Aaaaaa"])

    def test_duplicate_fixture_and_wrong_team_block(self):
        item=game()
        with self.assertRaisesRegex(BackfillError,"DUPLICATE"):
            validate_match_rows({"matches":[item,item]},"ESP","2025/2026",
                                "2026-05-01T00:00:00Z")
        item=game()
        item["away_team"]["id"]=item["home_team"]["id"]
        with self.assertRaisesRegex(BackfillError,"INVALID_NATIVE_TEAMS"):
            validate_match_rows({"matches":[item]},"ESP","2025/2026",
                                "2026-05-01T00:00:00Z")

    def test_batch_focuses_contiguous_history_not_sparse_one_per_scope(self):
        a=game("m_Aaaaaa")
        b=game("m_Bbbbbb")
        c=game("m_Cccccc")
        groups={("ESP","2025/2026"):[a,b],
                ("POL","2024/2025"):[c]}
        picked=select_batch(groups,set(),max_matches=3)
        self.assertEqual(len(picked),2)
        self.assertTrue(all(scope=="ESP" for scope,_,_ in picked))
        next_batch=select_batch(groups,{("ESP","m_Aaaaaa")},max_matches=3)
        self.assertEqual(len(next_batch),1)
        self.assertEqual(next_batch[0][2]["id"],"m_Bbbbbb")
        done=select_batch(groups,{("ESP","m_Aaaaaa"),("ESP","m_Bbbbbb")},max_matches=3)
        self.assertEqual([x[0] for x in done],["POL"])

    def test_deep_backfill_continues_after_recent_180(self):
        fixtures=[game("m_"+str(i).zfill(6)) for i in range(1,182)]
        known={("ESP",x["id"]) for x in fixtures[:180]}
        remaining=select_batch({("ESP","2025/2026"):fixtures},known,max_matches=3)
        self.assertEqual(len(remaining),1)
        self.assertEqual(remaining[0][2]["id"],"m_000181")
        self.assertEqual(select_batch({("ESP","2025/2026"):fixtures},
                        known|{("ESP","m_000181")}),[])

    def test_priority_source_fetch_uses_actual_last5_predecessors(self):
        fixtures=[]
        for i in range(1,9):
            f=game("m_"+str(i).zfill(6),
                   dt="2025-08-"+str(i).zfill(2)+"T12:00:00Z")
            fixtures.append(f)
        known={("ESP",fixtures[-1]["id"])}
        out=select_batch({("ESP","2025/2026"):fixtures},
                         known,max_matches=4)
        self.assertEqual(len(out),4)
        self.assertEqual(len({x[2]["id"] for x in out}),4)
        self.assertTrue(all(x[2]["id"] in {f["id"] for f in fixtures[2:7]}
                            for x in out))
        self.assertNotIn(fixtures[-1]["id"],{x[2]["id"] for x in out})

    def test_stats_all_period_provider_key_preserved(self):
        raw=stats()
        raw["periods"].append({"period":"First","groups":[
             {"group_name":"Other","items":[{"key":"corners","home":"99","away":"99"}]}]})
        items=all_period_stat_items(raw,game())
        self.assertEqual(len(items),3)
        self.assertEqual(next(x["home"] for x in items if x["key"]=="corners"),"4")

    def test_stats_side_mismatch_not_silently_accepted(self):
        raw=stats()
        raw["away_team"]["id"]="t_Zzzzzz"
        with self.assertRaisesRegex(BackfillError,"STATS_NATIVE_TEAM_SIDE_MISMATCH"):
            all_period_stat_items(raw,game())

    def test_native_xg_verified_requires_shots_and_stats_agreement(self):
        state,*fields=native_xg_verified(stats(),shots(),game())
        self.assertEqual(state,"VERIFIED")
        self.assertEqual(fields[:2],[.4,.7])
        wrong=shots()
        wrong["periods"][0]["shots"][0]["expected_goals"]=.05
        self.assertEqual(native_xg_verified(stats(),wrong,game())[0],
                         "XG_SHOTS_STATS_DISAGREE")
        self.assertEqual(native_xg_verified(stats(),None,game())[0],"SHOTS_UNAVAILABLE")

    def test_database_immutable_deduplicated_and_no_pit_claim(self):
        s={"scope":"ESP","season":"2025/2026","id":"m_Aa1234",
           "time_utc":"2025-07-01T12:00:00Z","home_id":"t_Aa1234",
           "away_id":"t_Bb1234","goals_home":2,"goals_away":1,
           "observed_at":"2026-11-03T12:00:00Z",
           "items":all_period_stat_items(stats(),game()),"stat_key_count":3,
           "xg_status":"VERIFIED","xg_home":.4,"xg_away":.7,
           "shots_home":1,"shots_away":1,"stats_sha":"a"*64,
           "shots_sha":"b"*64,"source_chain":"c"*64}
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"history.sqlite"
            self.assertEqual(put_rows(file,[s]),(1,1))
            self.assertEqual(existing_ids(file),{("ESP","m_Aa1234")})
            with self.assertRaises(sqlite3.IntegrityError):
                put_rows(file,[s])
            with sqlite3.connect(file) as db:
                self.assertIsNone(db.execute(
                    "SELECT provider_first_published_at_utc FROM observations").fetchone()[0])
                with self.assertRaises(sqlite3.DatabaseError):
                    db.execute("UPDATE observations SET goals_home_90=9")


if __name__=="__main__":
    unittest.main()
