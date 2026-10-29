import json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.step14_three_league_pitchapi_daily_asof import (
    candidate_predecessors,already_sampled,opaque_hash,capture,
    MAX_PRIORS_PER_LEAGUE,MAX_CALLS,SCHEMA,DailyLeagueError)

NOW=datetime(2026,10,29,12,tzinfo=timezone.utc)
def fixture(i,ko,status,home=1,away=2):
    return {"id":"m_"+format(i,"06d"),"time_utc":ko.isoformat().replace("+00:00","Z"),
       "status":status,"score_home":1 if status=="finished" else None,
       "score_away":0 if status=="finished" else None,
       "home_team":{"id":"t_"+format(home,"06d"),"name":"A"},
       "away_team":{"id":"t_"+format(away,"06d"),"name":"B"}}
class NewIncremental(unittest.TestCase):
 def test_only_history_for_next_four_future_fixtures(self):
    previous=[fixture(i,NOW-timedelta(days=30-i),"finished") for i in range(1,26)]
    now=[fixture(501,NOW+timedelta(days=2),"not_started"),
         fixture(502,NOW+timedelta(days=4),"scheduled")]
    future,chosen,needed,unseen=candidate_predecessors(now,previous,NOW,set(),"ESP")
    self.assertEqual(len(future),2)
    self.assertEqual(needed,15)
    self.assertEqual(unseen,15)
    self.assertEqual(len(chosen),6)
    self.assertTrue(all(m["status"]=="finished" for m in chosen))
 def test_dedup_in_following_days(self):
    previous=[fixture(i,NOW-timedelta(days=30-i),"finished") for i in range(1,26)]
    now=[fixture(501,NOW+timedelta(days=2),"not_started")]
    _,first,_,_=candidate_predecessors(now,previous,NOW,set(),"GER")
    seen={("GER",opaque_hash("GER",r["id"])) for r in first}
    _,next_batch,total,unseen=candidate_predecessors(now,previous,NOW,seen,"GER")
    self.assertEqual(total,15)
    self.assertEqual(unseen,9)
    self.assertEqual(len(next_batch),6)
    self.assertFalse(any(x["id"] in {v["id"] for v in first} for x in next_batch))
 def test_no_lookahead_result_or_future_match_as_predecessor(self):
    past=[fixture(1,NOW-timedelta(hours=1),"finished"),
         fixture(2,NOW-timedelta(days=2),"finished")]
    nxt=[fixture(500,NOW+timedelta(days=1),"scheduled")]
    _,older,needed,_=candidate_predecessors(nxt,past,NOW,set(),"ITA")
    self.assertEqual((needed,len(older)),(1,1))
    self.assertEqual(older[0]["id"],"m_000002")
 def test_step16_10_eligible_in_four_day_window_no_more_calls(self):
    prior=[fixture(i,NOW-timedelta(days=30-i),"finished") for i in range(1,26)]
    future=[fixture(500+i,NOW+timedelta(hours=4+i*4),"scheduled") for i in range(12)]
    chosen,history,needed,unseen=candidate_predecessors(
        future,prior,NOW,set(),"ESP",target_limit=10,horizon_hours=96)
    self.assertEqual(len(chosen),10)
    self.assertEqual(len(history),MAX_PRIORS_PER_LEAGUE)
    self.assertEqual(MAX_CALLS,43)
    self.assertEqual({x["id"] for x in chosen},{x["id"] for x in future[:10]})
    self.assertTrue(all(x["status"]=="finished" for x in history))
 def test_step16_96h_does_not_backfill_far_targets(self):
    prior=[fixture(i,NOW-timedelta(days=i+2),"finished") for i in range(1,20)]
    future=[fixture(501,NOW+timedelta(hours=12),"scheduled"),
            fixture(502,NOW+timedelta(hours=110),"scheduled")]
    chosen,_,_,_=candidate_predecessors(future,prior,NOW,set(),"GER",
                        target_limit=10,horizon_hours=96)
    self.assertEqual([x["id"] for x in chosen],["m_000501"])
 def test_one_competition_not_same_hash(self):
    self.assertNotEqual(opaque_hash("ESP","m_123456"),
                        opaque_hash("ITA","m_123456"))
 def test_immutable_already_hashed_success_readback(self):
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp)/"2026-10-29";folder.mkdir()
        items=[{"country":"ESP","native_match_id_sha256":opaque_hash("ESP","m_000001"),
                "state":"SOURCE_STATS_XG_VERIFIED"},
               {"country":"GER","native_match_id_sha256":opaque_hash("GER","m_000002"),
                "state":"SCHEMA_REJECTED_XG_MISSING"}]
        (folder/"THREE_LEAGUE_DAILY_RECEIPT.json").write_text(json.dumps({
            "schema":SCHEMA,"source_payloads_RSA_sealed":True,"sampled":items}))
        seen=already_sampled(temp)
        self.assertEqual(seen,{("ESP",opaque_hash("ESP","m_000001"))})
 def test_absent_api_key_no_work(self):
    with tempfile.TemporaryDirectory() as t:
        with self.assertRaisesRegex(DailyLeagueError,"SECRET_MISSING"):
            capture(root=t,key="",public_pem="bad")
 def test_bounded_no_premier_league_pollution(self):
    self.assertEqual((MAX_PRIORS_PER_LEAGUE,MAX_CALLS),(6,43))
if __name__=="__main__":unittest.main()
