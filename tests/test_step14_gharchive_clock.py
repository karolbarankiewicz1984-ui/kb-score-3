"""GH Archive server-clock checks, independent of Git committer metadata."""
from datetime import datetime
from io import BytesIO
import gzip
import json
import unittest

from src.kb3_step14_gharchive_clock import audit_push_clock,read_hour,SAMPLES


class ClockTests(unittest.TestCase):
    def test_real_public_push_head_sha_corroborates_server_event(self):
        hour,sha,fid,kickoff=SAMPLES[0]
        obj={"id":"event-1","type":"PushEvent","repo":{"name":"openfootball/football.json"},
             "created_at":"2024-10-02T13:53:12Z",
             "payload":{"head":sha,"commits":[],"ref":"refs/heads/master"}}
        payload=gzip.compress((json.dumps(obj)+"\n").encode())
        r=read_hour(hour,open_stream=lambda _:BytesIO(payload))
        self.assertEqual(r["status"],"READ_OK")
        self.assertEqual(r["push_events_found"][0]["created_at_utc"],"2024-10-02T13:53:12Z")
        self.assertIn(sha,r["push_events_found"][0]["included_commit_shas"])

    def test_irrelevant_repo_event_is_ignored(self):
        hour,sha,_,_=SAMPLES[0]
        obj={"type":"PushEvent","repo":{"name":"other/football.json"},
             "created_at":"2024-10-02T13:53:12Z",
             "payload":{"head":sha}}
        q=read_hour(hour,open_stream=lambda _:BytesIO(gzip.compress((json.dumps(obj)+"\n").encode())))
        self.assertEqual(q["push_events_found"],[])

    def test_fake_commit_timestamp_does_not_grant_any_pit(self):
        def fake_hour(hour):
            return {"status":"READ_OK","archive_url":"file://unit-test",
                    "push_events_found":[]}
        r=audit_push_clock(fake_hour)
        self.assertEqual(r["independent_push_sha_samples_corroborated"],0)
        self.assertEqual(r["native_pitchapi_team_pairs_verified"],0)
        self.assertFalse(r["gate14_pass"])
        self.assertTrue(all(not x["eligible_for_official_m1"] for x in r["records"]))

    def test_missing_archive_is_explicit_unavailable(self):
        def broken(_):raise ConnectionError("blocked")
        r=read_hour(SAMPLES[0][0],open_stream=broken)
        self.assertEqual(r["status"],"READ_UNAVAILABLE")
        self.assertEqual(r["error_type"],"ConnectionError")


if __name__=="__main__":
    unittest.main()
