"""No provider contact and no held-out results."""
import json,unittest
from pathlib import Path
from src.kb3_step13_leakage_audit import audit,source_policy_scan
from src.kb3_step13_baseline import BaselineSafetyError

class LeakAuditTests(unittest.TestCase):
    def test_pre_kickoff_audit(self):
        a=audit()
        self.assertEqual(a["train_scores_permitted"],760)
        self.assertEqual(a["test_scores_permitted"],0)
        self.assertEqual(a["result_labels_read"],0)
        self.assertEqual(a["query_statuses_static"],["played","upcoming"])
        self.assertFalse(a["historical_pit_proven"])
        self.assertFalse(a["gate13_pass"])
    def test_missing_upcoming_guard_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"script.py"
            p.write_text('sdk.leagues.matches("id",status="all")\nTRAIN_SEASONS="A"\nTARGET_SEASON="B"\ntrain_only="X"\nstatus="upcoming"',encoding="utf8")
            with self.assertRaisesRegex(BaselineSafetyError,"QUERY_POLICY_CHANGED"):
                source_policy_scan(p)
    def test_missing_literal_status_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"script.py"
            p.write_text('sdk.leagues.matches("id",status=somevariable)')
            with self.assertRaisesRegex(BaselineSafetyError,"WITHOUT_LITERAL_STATUS"):
                source_policy_scan(p)
if __name__=="__main__":unittest.main()
