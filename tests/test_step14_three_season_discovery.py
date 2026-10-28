"""Synthetic negative tests for external publication clocks of new Git SHAs."""
import unittest
from src.kb3_step14_three_season_discovery import CANDIDATES,pinned_selection,probe_public_push

class DiscoveryTests(unittest.TestCase):
    def test_historical_windows_cover_every_original_season(self):
        self.assertEqual(len(CANDIDATES),5)
        self.assertEqual(set(x["season"] for x in CANDIDATES),{"2023-24","2024-25","2025-26"})
    def test_git_date_only_discovers_not_proves(self):
        src=CANDIDATES[0]
        got=pinned_selection(src,[{"sha":"a"*40,"commit":{"committer":{"date":"2023-11-15T13:00:00Z"}}}])
        self.assertIn("DISCOVERY_ONLY",list(got)[1])
        self.assertNotIn("published_at_utc",got)
    def test_missing_archive_cannot_prove_publication(self):
        r=probe_public_push("vaastav/Fantasy-Premier-League","a"*40,
                            "2023-11-15T13:00:00Z",
                            lambda hour:{"status":"READ_UNAVAILABLE","events":[]})
        self.assertFalse(r["independent_clock_verified"])
        self.assertIsNone(r["published_at_utc"])
    def test_foreign_repo_wrong_sha_never_promotes(self):
        r=probe_public_push("vaastav/Fantasy-Premier-League","a"*40,
           "2023-11-15T13:00:00Z",
           lambda hour:{"status":"READ_OK","events":[{
              "repository":"other/repo","ref":"refs/heads/main",
              "shas":["a"*40],"server_created_at_utc":"2023-11-15T13:01:00Z","event_id":"123"}]})
        self.assertFalse(r["independent_clock_verified"])
    def test_correct_exact_fpl_push_event(self):
        r=probe_public_push("vaastav/Fantasy-Premier-League","a"*40,
           "2023-11-15T13:00:00Z",
           lambda hour:{"status":"READ_OK","events":[{
              "repository":"vaastav/Fantasy-Premier-League","ref":"refs/heads/master",
              "shas":["a"*40],"server_created_at_utc":"2023-11-15T13:01:00Z","event_id":"123"}]})
        self.assertTrue(r["independent_clock_verified"])
        self.assertEqual(r["independent_event_id"],"123")
    def test_openfootball_wrong_ref_rejected(self):
        r=probe_public_push("openfootball/football.json","a"*40,
          "2025-10-17T15:00:00Z",
          lambda hour:{"status":"READ_OK","push_events_found":[{
             "event_repo_name":"openfootball/football.json",
             "push_ref":"refs/heads/unreviewed",
             "included_commit_shas":["a"*40],
             "created_at_utc":"2025-10-17T15:05:00Z","event_id":"34"}]})
        self.assertFalse(r["independent_clock_verified"])
    def test_correct_openfootball_exact_push(self):
        r=probe_public_push("openfootball/football.json","a"*40,
          "2025-10-17T15:00:00Z",
          lambda hour:{"status":"READ_OK","push_events_found":[{
             "event_repo_name":"openfootball/football.json",
             "push_ref":"refs/heads/master",
             "included_commit_shas":["a"*40],
             "created_at_utc":"2025-10-17T15:05:00Z","event_id":"34"}]})
        self.assertTrue(r["independent_clock_verified"])
        self.assertEqual(r["independent_event_id"],"34")

if __name__=="__main__":unittest.main()
