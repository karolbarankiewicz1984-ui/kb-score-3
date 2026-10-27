"""Offline negative tests for authentic historic FPL per-source PushEvent proof."""
import csv,io,copy
import unittest
from src.kb3_step14_fpl_historic_clock_pilot import (
    SAMPLES,REPO,FPLSourceError,verify_raw_csv,audit
)

def make_csv(n):
    buf=io.StringIO()
    w=csv.DictWriter(buf,fieldnames=["id","team_h","team_a","kickoff_time",
                                     "finished","team_h_score","team_a_score"])
    w.writeheader()
    for i in range(380):
        w.writerow({"id":i+1,"team_h":i%20+1,"team_a":(i+1)%20+1,
            "kickoff_time":"2023-08-11T19:00:00Z",
            "finished":"True" if i<n else "False",
            "team_h_score":"1" if i<n else "",
            "team_a_score":"0" if i<n else ""})
    return buf.getvalue().encode()

class FPL2023EvidenceTests(unittest.TestCase):
    def test_70_prior_ft_rows_never_allow_original_m1(self):
        v=verify_raw_csv(make_csv(70),expected_finished=70,
                         push_time_utc="2023-10-05T14:40:00Z")
        self.assertEqual(v["finished_ft_records_available_at_historical_source_publication"],70)
        self.assertEqual(v["unplayed_rows_have_null_scores"],310)
        self.assertFalse(v["any_future_or_target_score_used"])

    def test_future_score_in_old_blob_rejected(self):
        f=make_csv(70).replace(b"2023-08-11T19:00:00Z",b"2023-10-06T19:00:00Z",1)
        with self.assertRaisesRegex(FPLSourceError,"FUTURE_SCORE"):
            verify_raw_csv(f,expected_finished=70,push_time_utc="2023-10-05T14:40:00Z")

    def test_retroactively_added_score_mismatch_rejected(self):
        with self.assertRaisesRegex(FPLSourceError,"HISTORICAL_SNAPSHOT_COUNT"):
            verify_raw_csv(make_csv(71),expected_finished=70,push_time_utc="2023-10-05T14:40:00Z")

    def test_all_original_samples_need_thirdparty_push(self):
        def reader(hour):
            sha=next(s[1] for s in SAMPLES if s[0]==hour)
            # Strict independent historical server time inside requested hour
            time=hour[:10]+"T"+hour[11:]+":15:00Z"
            return {"status":"READ_OK","hour":hour,"events":[
                {"event_id":"gh123","server_created_at_utc":time,
                 "repository":REPO,"ref":"refs/heads/master","shas":[sha]}]}
        out=audit(read_archived_csv=lambda commit:make_csv(next(s[2] for s in SAMPLES if s[1]==commit)),
                  read_hour=reader)
        self.assertEqual(out["verified_snapshots"],3)
        self.assertEqual([r["finished_ft_records_available_at_historical_source_publication"] for r in out["records"]],[10,70,90])
        self.assertFalse(out["gate14_pass"])
        self.assertFalse(out["native_pitchapi_team_pair_joined"])

    def test_github_committer_date_alone_not_accepted(self):
        with self.assertRaisesRegex(FPLSourceError,"EXACT_SHA_PUBLIC"):
            audit(read_archived_csv=lambda sha:make_csv(10),
                read_hour=lambda hr:{"status":"READ_OK","hour":hr,"events":[]})

    def test_incorrect_source_same_archive_hour_rejected(self):
        def reader(hour):
            sha=next(s[1] for s in SAMPLES if s[0]==hour)
            return {"status":"READ_OK","hour":hour,"events":[
                {"event_id":"gh123","server_created_at_utc":"2026-10-27T12:00:00Z",
                 "repository":REPO,"ref":"refs/heads/master","shas":[sha]}]}
        with self.assertRaisesRegex(FPLSourceError,"GHARCHIVE_SERVER_TIME"):
            audit(read_archived_csv=lambda sha:make_csv(10),read_hour=reader)

    def test_original_2023_2024_only_no_test_or_odds(self):
        self.assertEqual(len(SAMPLES),3)
        self.assertTrue(all(s[0].startswith("2023-") for s in SAMPLES))
        self.assertTrue(all(len(s[1])==40 for s in SAMPLES))

if __name__=="__main__":unittest.main()
