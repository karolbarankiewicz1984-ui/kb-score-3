"""Fail-closed unit tests for gain-first historical source selection."""
import unittest
from datetime import datetime,timedelta,timezone
from scripts.kb3_history_gain_first import (
    build_needs,greedy_rank,potential_unlocks,scope_boost,
)

def game(mid,day,home,away,season="2025/2026"):
    return {"scope":"ESP","season":season,"match_id":mid,
        "kickoff_utc":(datetime(2025,9,1,tzinfo=timezone.utc)+
                       timedelta(days=day)).isoformat().replace("+00:00","Z"),
        "home_team_id":home,"away_team_id":away}

def observation(season="2025/2026", cards=True, xg=True):
    fields=("total_shots","fouls","corners")+(
        ("yellow_cards",) if cards else ())
    items=[{"key":k,"home":2.0,"away":2.0} for k in fields]
    return {"season":season,"items":items,
        "xg_status":"VERIFIED" if xg else "MISSING",
        "xg_home":1.0 if xg else None,
        "xg_away":1.0 if xg else None}

def sample():
    fixtures=[game("h"+str(i),i+1,"A","B") for i in range(5)]
    fixtures += [game("a"+str(i),i+1,"C","D") for i in range(5)]
    fixtures += [game("target",10,"A","C")]
    observed={("ESP",f["match_id"]):observation() for f in fixtures}
    return {"ESP":fixtures},observed

class KB3HistoryGainPriorityTests(unittest.TestCase):
    def test_last_missing_predecessor_closes_core_and_xg(self):
        fixt,obs=sample()
        obs.pop(("ESP","h4"))
        needs=build_needs(fixt,obs)
        kinds={x[0] for x in needs["closure_tasks"]}
        self.assertEqual(kinds,{"history","core","joint"})
        rank=greedy_rank(needs["closure_tasks"],{("ESP","h4")},1)
        self.assertEqual(rank,[("ESP","h4")])
        gain,_=potential_unlocks(needs["closure_tasks"],rank)
        self.assertEqual(gain,{"history":1,"core":1,"joint":1})

    def test_xg_disagreement_not_assumed_fixed_by_new_fixture(self):
        fixt,obs=sample()
        obs.pop(("ESP","h4"))
        obs[("ESP","a0")]=observation(xg=False)
        need=build_needs(fixt,obs)
        self.assertNotIn("joint",{x[0] for x in need["closure_tasks"]})
        self.assertIn("core",{x[0] for x in need["closure_tasks"]})

    def test_only_existing_yellow_deficit_needs_recheck_not_new_fetch(self):
        fixt,obs=sample()
        obs[("ESP","h2")]=observation(cards=False)
        need=build_needs(fixt,obs)
        self.assertFalse(need["closure_tasks"])
        self.assertEqual(need["card_tasks"][0][1],frozenset({("ESP","h2")}))

    def test_missing_unobserved_target_never_used_as_training_feature(self):
        fixt,obs=sample()
        obs.pop(("ESP","target"))
        self.assertEqual(build_needs(fixt,obs)["closure_tasks"],[])

    def test_greedy_is_deterministic_and_not_stale_static_ranking(self):
        tasks=[("core","ESP",frozenset({("ESP","z")}),5),
               ("core","ESP",frozenset({("ESP","a"),("ESP","b")}),5)]
        self.assertEqual(greedy_rank(tasks,
                 {("ESP","z"),("ESP","a"),("ESP","b")},2)[0],
                         ("ESP","z"))
        self.assertEqual(greedy_rank(tasks,{("ESP","z")},3),[("ESP","z")])

    def test_no_protected_league_and_research_priority_bonus(self):
        self.assertGreater(scope_boost("POL"),scope_boost("BEL"))
        fixt,obs=sample()
        fixt["ENG"]=[game("eng",1,"X","Y")]
        with self.assertRaisesRegex(ValueError,"PROTECTED"):
            build_needs(fixt,obs)

if __name__=="__main__":
    unittest.main()
