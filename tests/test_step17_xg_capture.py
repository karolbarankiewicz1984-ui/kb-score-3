"""Step17 native xG: authentic-schema synthetic source tests and strict no lookahead.

Tests use real project RSA public key (never a private key) and zero network/API.
"""
import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from test_step16_m0_720_eight_forward import season,NOW
from src.kb3_step16_m0_720_eight_forward import EIGHT,stamp,Research720Error
from src.kb3_step17_xg_capture import (
    XG_SCHEMA,MAX_CALLS,parse_pair,rank_sources,fixture_groups,run,
    future_xg_coverage,store_samples,connect)

class FakeLeagues:
 def __init__(self,client):self.client=client
 def list(self):
    return {"leagues":[{"country_code":c,"name":title,"id":"l_"+c,
       "is_free":True,"seasons":["2025/2026","2026/2027"]}
       for c,title,_ in EIGHT]}
 def matches(self,lid,season,**kw):
    c=lid[2:]
    return {"matches":self.client.rows[(c,season)]}
class FakeMatches:
 def __init__(self,client):self.client=client
 def shots(self,mid):
    m=self.client.lookup[mid]
    return {"data":{"match_id":mid,"periods":[{"period":"All","shots":[
      {"id":mid+"_shot_1","team_id":m["home_team"]["id"],"expected_goals":0.4},
      {"id":mid+"_shot_2","team_id":m["away_team"]["id"],"expected_goals":0.75}]}]}}
 def stats(self,mid):
    m=self.client.lookup[mid]
    return {"data":{"match_id":mid,"home_team":{"id":m["home_team"]["id"]},
     "away_team":{"id":m["away_team"]["id"]},"periods":[{"period":"All","groups":[{
       "group_name":"Expected goals (xG)","items":[{
          "key":"expected_goals","home":"0.40","away":"0.75","format_type":"double"}]}]}]}}
class FakeClient:
 def __init__(self):
    self.rows={}
    for c,_,_ in EIGHT:
      for year,term in ((2025,"2025/2026"),(2026,"2026/2027")):
        self.rows[(c,term)]=season(c,year)
    self.lookup={m["id"]:m for seq in self.rows.values() for m in seq}
    self.leagues=FakeLeagues(self);self.matches=FakeMatches(self)
class EightXgTests(unittest.TestCase):
 def test_real_shape_8_league_33_calls_and_encrypted_source(self):
    fake=FakeClient()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        summary=run(client=fake,db_path=root/"xg.sqlite",archive=root/"evidence",now=NOW)
        self.assertLessEqual(summary["network_calls"],MAX_CALLS)
        self.assertEqual(summary["network_calls"],33)
        self.assertEqual(summary["prior_matches_selected"],8)
        self.assertEqual(summary["new_shots_stats_xg_verified"],8)
        self.assertEqual(summary["cumulative_verified_xg_matches"],8)
        self.assertFalse(summary["training_ready"])
        self.assertFalse(summary["trained_xg_catboost_exists"])
        self.assertFalse(summary["protected_premier_league_TEST_2026_27_requested"])
        self.assertEqual(summary["xg_semantic_errors"],{})
        p=root/"evidence"/NOW.date().isoformat()
        self.assertTrue((p/"XG_SOURCE.enc").is_file())
        self.assertNotIn(b"expected_goals", (p/"XG_SOURCE.enc").read_bytes())
        self.assertEqual(json.loads((p/"XG_READINESS_RECEIPT.json").read_text())["report_sha256"],
                         summary["report_sha256"])
        with connect(root/"xg.sqlite") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observed_native_xg").fetchone()[0],8)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM observed_native_xg")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE observed_native_xg SET stats_xg_home=0")
        self.assertGreater(summary["future_form5_coverage"]["future_targets_scanned"],0)
        self.assertEqual(summary["future_form5_coverage"]["complete_last5_both_team_xg"],0)
        shadow=summary["last5_priority_shadow_comparison"]
        self.assertEqual(shadow["source"],"IDENTICAL_REAL_FIXTURES_SAME_OBSERVATION_CUTOFF")
        self.assertEqual(shadow["additional_api_calls"],0)
        self.assertFalse(shadow["priority_live_activated"])
        self.assertFalse(shadow["priority_real_outcome_verified"])
        self.assertTrue(shadow["theoretical_if_all_success"]["only_a_theoretical_ceiling_not_observed_gain"])
        self.assertEqual(len(summary["real_missing_last5_predecessor_ids"]),
                         summary["future_form5_coverage"]["future_targets_scanned"])
        self.assertTrue(all(not x["both_teams_last5_verified"]
                            for x in summary["real_missing_last5_predecessor_ids"]))
        self.assertTrue(any(v["missing_native_xg_provider_ids"] for x in
              summary["real_missing_last5_predecessor_ids"] for v in x["teams"].values()))
        with self.assertRaisesRegex(Research720Error,"ALREADY_SAVED"):
            run(client=fake,db_path=root/"xg.sqlite",archive=root/"evidence",now=NOW)
 def test_real_seven_league_capture_when_tur_country_absent(self):
    fake=FakeClient()
    original_list=fake.leagues.list
    fake.leagues.list=lambda: {"leagues": [
        x for x in original_list()["leagues"] if x["country_code"]!="TUR"]}
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        report=run(client=fake,db_path=root/"xg.sqlite",archive=root/"evidence",now=NOW)
        self.assertEqual(report["network_calls"],29)
        self.assertEqual(set(report["leagues"]),{c for c,_,_ in EIGHT}-{"TUR"})
        self.assertEqual(report["missing_catalog_leagues"],["TUR"])
        self.assertTrue(report["partial_source_coverage_research_only"])
        self.assertEqual(report["prior_matches_selected"],7)
        self.assertFalse(report["training_ready"])
        self.assertFalse(report["auto_promotion"])
        self.assertEqual(report["gate17"],"PENDING")
        with connect(root/"xg.sqlite") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observed_native_xg").fetchone()[0],7)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observed_native_xg WHERE country='TUR'").fetchone()[0],0)

 def test_native_semantic_mismatch_blocks_as_predecessor(self):
    fake=FakeClient();m=next(v for v in fake.lookup.values() if v["status"]=="finished")
    shots=fake.matches.shots(m["id"]);stats=fake.matches.stats(m["id"])
    stats["data"]["periods"][0]["groups"][0]["items"][0]["home"]="1.5"
    source={"completed_at_utc":stamp(NOW),"payload_sha256":"a"*64,"chain_sha256":"b"*64}
    with self.assertRaisesRegex(Exception,"DISAGREE"):
        parse_pair(shots,stats,match=m,country="ESP",shot_receipt=source,stat_receipt=source)
 def test_no_last5_cherry_pick_missing_is_not_zero(self):
    fake=FakeClient();group={}
    for c,_,_ in EIGHT:
        group[c]={"history":[m for m in fake.rows[(c,"2026/2027")] if m["status"]=="finished"],
                  "future":[m for m in fake.rows[(c,"2026/2027")] if m["status"]=="scheduled"][:1]}
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"xg.sqlite"
        with connect(db):pass
        summary,_=future_xg_coverage(db,group,NOW)
        self.assertEqual(summary["complete_last5_both_team_xg"],0)
        self.assertEqual(summary["future_targets_scanned"],8)
 def test_no_protected_ENG_and_history_never_uses_unfinished_game(self):
    fake=FakeClient()
    receipts=[]
    for c,_,_ in EIGHT:
        for term in ("2025/2026","2026/2027"):
            receipts.append({"resource":f"pitchapi:step17xg:fixtures:{c}:{term}",
                             "payload":{"matches":fake.rows[(c,term)]}})
    grouped=fixture_groups(receipts)
    selected,groups=rank_sources(grouped,set(),NOW)
    self.assertEqual(len(selected),8)
    self.assertTrue(all(c!="ENG" and m["status"]=="finished"
                        and m["score_home"] is not None
                        and m["score_away"] is not None
                        and datetime.fromisoformat(m["time_utc"].replace("Z","+00:00"))+
                           timedelta(hours=3)<=NOW
                        for c,m in selected))
if __name__=="__main__":unittest.main()
