"""V3-R forward readiness: no invented historical as-of or API access."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from scripts.kb3_v3r_forward_readiness import (
    asof_observations, audit_target, V3RReadinessError,
)

CUTOFF="2026-11-15T20:09:18Z"
TARGET={
    "league":"ESP", "native_match_id":"future_native_1",
    "home_team_id":"team_A", "away_team_id":"team_B",
    "kickoff_utc":"2026-11-22T20:00:00Z",
    "captured_at_utc":CUTOFF,
}


def fixtures_and_observations():
    fixtures=[]; observations=[]
    for i in range(10):
        kickoff=(datetime(2026,10,28,tzinfo=timezone.utc)+
                 timedelta(days=i)).isoformat().replace("+00:00","Z")
        row={"scope":"ESP","match_id":f"m_{i}","kickoff_utc":kickoff,
             "home_team_id":"team_A","away_team_id":"team_B",
             "goals_home_90":i%3,"goals_away_90":(i+1)%2,
             "listed_at_utc":"2026-11-13T10:00:00Z"}
        fixtures.append(row)
        observations.append({
            "scope":"ESP","match_id":row["match_id"],
            "home_team_id":"team_A","away_team_id":"team_B",
            "kickoff_utc":kickoff,
            "observed_at_utc":"2026-11-14T08:00:00Z",
            "items":[{"key":k,"home":11,"away":9}
                     for k in ("total_shots","fouls","corners","yellow_cards")],
            "xg_status":"VERIFIED","xg_home":1.2,"xg_away":0.9})
    return fixtures,observations


class ForwardReadinessTests(unittest.TestCase):
    def test_complete_asof_14_and_18_sets(self):
        fixtures,obs=fixtures_and_observations()
        d=audit_target(TARGET,fixtures,obs)
        self.assertEqual(d["status"],"CANDIDATE_ALL_18")
        self.assertTrue(d["xg5"])
        self.assertTrue(d["core5"])

    def test_late_xg_stats_not_used_as_if_observed_before_freeze(self):
        fixtures,obs=fixtures_and_observations()
        for o in obs:
            o["observed_at_utc"]="2026-11-16T00:00:00Z"
        d=audit_target(TARGET,fixtures,obs)
        self.assertEqual(d["status"],"STATISTICS_LAST5_INCOMPLETE")
        self.assertTrue(d["history5"])
        self.assertFalse(d["core5"])

    def test_incomplete_xg_leaves_core14_candidate_only(self):
        fixtures,obs=fixtures_and_observations()
        obs[9]["xg_status"]="UNVERIFIED"
        obs[9]["xg_home"]=None;obs[9]["xg_away"]=None
        d=audit_target(TARGET,fixtures,obs)
        self.assertEqual(d["status"],"CANDIDATE_14_ONLY")

    def test_missing_recent_source_fails_closed(self):
        fixtures,obs=fixtures_and_observations()
        for row in fixtures:
            row["listed_at_utc"]="2026-11-16T00:00:00Z"
        d=audit_target(TARGET,fixtures,obs)
        self.assertEqual(d["status"],"HISTORY5_NOT_IN_SOURCE_INDEX")

    def test_protected_and_late_m0_capture_rejected(self):
        f,o=fixtures_and_observations()
        with self.assertRaises(V3RReadinessError):
            audit_target({**TARGET,"league":"ENG"},f,o)
        with self.assertRaises(V3RReadinessError):
            audit_target({**TARGET,"captured_at_utc":"2026-11-22T19:00:00Z"},f,o)

    def test_identical_native_id_with_different_team_is_rejected(self):
        f,o=fixtures_and_observations()
        o[5]["home_team_id"]="tampered"
        with self.assertRaisesRegex(V3RReadinessError,"IDENTITY_CHANGED"):
            audit_target(TARGET,f,o)

    def test_no_UCL_or_postfreeze_source_enters_asof(self):
        _,o=fixtures_and_observations()
        item=copy.deepcopy(o[0]);item["scope"]="UCL"
        filtered=asof_observations(o+[item],CUTOFF)
        self.assertEqual(len(filtered),10)
        self.assertNotIn(("UCL",item["match_id"]),filtered)


if __name__=="__main__":
    unittest.main()
