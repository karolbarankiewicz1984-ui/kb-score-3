import unittest
from scripts.kb3_catboost_v3_archive_cutoff_audit import classify
class ArchiveCutoffAuditTests(unittest.TestCase):
    def setUp(self):
        self.a=[dict(id=13643613735,name="M0",created_at="2026-11-09T01:45:39Z",expired=False)]
        self.t=[dict(fixture_id="fixture-1",league="POL",feature_cutoff_utc="2026-11-09T02:00:00Z")]
    def test_archive_before_target_is_candidate_not_admitted(self):
        r=classify(self.a,self.t)
        self.assertTrue(r["rows"][0]["metadata_time_candidate"])
        self.assertFalse(r["rows"][0]["formally_training_eligible"])
    def test_archive_after_target_rejected(self):
        self.t[0]["feature_cutoff_utc"]="2026-11-09T01:00:00Z"
        self.assertFalse(classify(self.a,self.t)["rows"][0]["metadata_time_candidate"])
    def test_expired_archive_rejected(self):
        self.a[0]["expired"]=True
        self.assertFalse(classify(self.a,self.t)["rows"][0]["metadata_time_candidate"])
    def test_missing_target_rejected(self):
        self.t[0]["fixture_id"]=""
        with self.assertRaises(ValueError):classify(self.a,self.t)
if __name__=="__main__":unittest.main()
