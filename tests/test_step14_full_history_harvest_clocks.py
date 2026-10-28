import unittest
from scripts.step14_full_history_harvest_independent_clocks import (
 CANDIDATES, hour_label, probe_one, audit, HarvestError)
class FullArchiveLineageTest(unittest.TestCase):
 def test_three_seasons_candidate_scope(self):
    self.assertEqual(len(CANDIDATES),13)
    self.assertEqual({x[0] for x in CANDIDATES},{"2023-24","2024-25","2025-26"})
 def test_commit_clock_not_original_publication(self):
    src=CANDIDATES[0]
    r=probe_one(src,read_hour=lambda h:{"status":"READ_OK","events":[]},
                fetcher=lambda *a,**kw:b"UNUSED")
    self.assertFalse(r["verified_publication"])
    self.assertIsNone(r["independent_publication_UTC"])
 def test_gh_archive_down_fail_closed(self):
    r=probe_one(CANDIDATES[0],read_hour=lambda h:{"status":"READ_UNAVAILABLE","events":[]},
                fetcher=lambda *a,**kw:b"UNUSED")
    self.assertEqual(r["state"],"NO_EXACT_INDEPENDENT_PUSH_IN_CANDIDATE_HOUR")
 def test_event_wrong_branch_denied(self):
    s=CANDIDATES[0]
    e={"event_id":"123","repository":s[2],"ref":"refs/heads/experimental",
       "shas":[s[4]],"server_created_at_utc":s[5]}
    r=probe_one(s,read_hour=lambda h:{"status":"READ_OK","events":[e]})
    self.assertFalse(r["verified_publication"])
 def test_event_wrong_repo_denied(self):
    s=CANDIDATES[0]
    e={"event_id":"123","repository":"bad/repo","ref":"refs/heads/master",
       "shas":[s[4]],"server_created_at_utc":s[5]}
    self.assertFalse(probe_one(s,read_hour=lambda h:{"events":[e],"status":"READ_OK"})["verified_publication"])
 def test_datetime_hour(self):
    self.assertEqual(hour_label("2025-11-12T05:20:03Z"),"2025-11-12-05")
 def test_fake_positive_without_proof_rejected(self):
    def impossible(c):
        return {"season":c[0],"verified_publication":True,
                "independent_publication_UTC":None,"source_sha256":None}
    with self.assertRaisesRegex(HarvestError,"UNATTESTED"):
        audit(probe=impossible)
if __name__=="__main__":unittest.main()
