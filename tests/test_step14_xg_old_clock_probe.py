"""No fake historic publication of 2024/25 or 2025/26 player xG."""
import unittest
from src.kb3_step14_xg_old_clock_probe import (
    WINDOWS,SourceClockError,independent_exact_push,select_window_commits,scan_one)
class HistoricalOldXGClocks(unittest.TestCase):
    def test_three_windows_and_no_implied_provider_equivalence(self):
        self.assertEqual(len(WINDOWS),3)
        self.assertEqual({x["season"] for x in WINDOWS},{"2024-25","2025-26"})
    def test_no_sha_event_cannot_be_passed(self):
        r=independent_exact_push("a"*40,"2024-10-02T12:30:00Z",
                     lambda h:{"status":"READ_OK","events":[]})
        self.assertFalse(r["confirmed"])
        self.assertIsNone(r["server_publication_utc"])
    def test_unavailable_archive_not_publication(self):
        r=independent_exact_push("a"*40,"2024-10-02T12:30:00Z",
                     lambda h:{"status":"READ_UNAVAILABLE","events":[]})
        self.assertFalse(r["confirmed"])
    def test_other_repo_event_not_match(self):
        r=independent_exact_push("a"*40,"2024-10-02T12:30:00Z",
              lambda h:{"status":"READ_OK","events":[{
                "repository":"evil/fork","ref":"refs/heads/master","shas":["a"*40],
                "event_id":"1234","server_created_at_utc":"2024-10-02T12:33:00Z"}]})
        self.assertFalse(r["confirmed"])
    def test_independent_exact_event_corroborates(self):
        r=independent_exact_push("a"*40,"2024-10-02T12:30:00Z",
              lambda h:{"status":"READ_OK","events":[{
                "repository":"vaastav/Fantasy-Premier-League",
                "ref":"refs/heads/master","shas":["a"*40],
                "event_id":"1234","server_created_at_utc":"2024-10-02T12:33:00Z"}]})
        self.assertTrue(r["confirmed"])
        self.assertEqual(r["event_id"],"1234")
    def test_committer_clock_only_selects_not_validates(self):
        docs=[{"sha":"a"*40,"commit":{"committer":{"date":"2024-10-02T12:30:00Z"}}}]
        s=select_window_commits(docs,WINDOWS[0])
        self.assertEqual(len(s),1)
        self.assertNotIn("server_publication_utc",s[0])
    def test_no_known_commit_never_promotes(self):
        r=scan_one(WINDOWS[0],fetcher=lambda _:b"[]")
        self.assertEqual(r["status"],"NO_OLD_FILE_COMMIT_IN_WINDOW")
        self.assertFalse(r["pitchapi_original_team_xg_pit_proven"])
    def test_ambiguous_push_event_stops(self):
        ev={"repository":"vaastav/Fantasy-Premier-League",
            "ref":"refs/heads/master","shas":["a"*40],"event_id":"10",
            "server_created_at_utc":"2024-10-02T12:33:00Z"}
        with self.assertRaises(SourceClockError):
            independent_exact_push("a"*40,"2024-10-02T12:30:00Z",
             lambda h:{"status":"READ_OK","events":[ev,ev]})
if __name__=="__main__":unittest.main()
