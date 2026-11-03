"""No-provider offline checks for accelerated five-batch research backfill."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.kb3_history_accelerated import drive

def fake_capture(*, run_token, max_matches, **kwargs):
    assert max_matches==48
    return {"new_match_stats":48,"new_native_xg_verified":40,
            "provider_requests":131,"cumulative_match_stats":96,
            "source_ciphertext_sha256":"a"*64}

def fake_quality(db, out, **kwargs):
    out=Path(out)
    out.write_text("{}")
    return {"totals":{"total_observed_stats_matches":336,
        "xg_verified_matches":300,"pair_core_5_complete":20,
        "pair_xg_5_complete":55,"pair_xg_10_complete":10,
        "pair_xg_15_complete":4}}

class AcceleratedTests(unittest.TestCase):
    @patch("scripts.kb3_history_accelerated.assess_and_cache",side_effect=fake_quality)
    @patch("scripts.kb3_history_accelerated.recheck",return_value={"status":"OBSERVED_RECHECK"})
    @patch("scripts.kb3_history_accelerated.capture",side_effect=fake_capture)
    def test_five_isolated_source_receipts_equal_240(self,capture,recheck,quality):
        with tempfile.TemporaryDirectory() as d:
            r=drive(object(),run_token="run-123",db=Path(d)/"db.sqlite",
                    archive=Path(d)/"archive",issues_db=Path(d)/"issues.sqlite",
                    issues_root=Path(d)/"rechecks",batches=5)
        self.assertEqual(r["completed_batches"],5)
        self.assertEqual(r["new_match_stats"],240)
        self.assertEqual(r["provider_requests_history"],655)
        self.assertEqual(len(set(x["token"] for x in r["history_batches"])),5)
        self.assertEqual(r["history_batches"][0]["token"],"run-123-b1")
        self.assertEqual(r["history_batches"][-1]["token"],"run-123-b5")
        self.assertFalse(r["provider_original_pit_certified"])
        self.assertTrue(r["original_m0_unchanged"])

    @patch("scripts.kb3_history_accelerated.assess_and_cache",side_effect=fake_quality)
    @patch("scripts.kb3_history_accelerated.recheck",return_value={"status":"NO_NEW_ISSUES"})
    @patch("scripts.kb3_history_accelerated.capture")
    def test_empty_batch_stops_without_fake_progress(self,capture,recheck,quality):
        capture.return_value={"new_match_stats":0,"new_native_xg_verified":0,
            "provider_requests":35,"cumulative_match_stats":96,
            "source_ciphertext_sha256":"c"*64}
        with tempfile.TemporaryDirectory() as d:
            r=drive(object(),run_token="run-124",db=Path(d)/"db.sqlite",
                    archive=Path(d)/"archive",issues_db=Path(d)/"issues.sqlite",
                    issues_root=Path(d)/"rechecks",batches=5)
        self.assertEqual(capture.call_count,1)
        self.assertEqual(r["new_match_stats"],0)

    @patch("scripts.kb3_history_accelerated.assess_and_cache",side_effect=fake_quality)
    @patch("scripts.kb3_history_accelerated.recheck",side_effect=ValueError("provider"))
    @patch("scripts.kb3_history_accelerated.capture",side_effect=fake_capture)
    def test_recheck_failure_is_reported_not_pass(self,capture,recheck,quality):
        with tempfile.TemporaryDirectory() as d:
            r=drive(object(),run_token="run-125",db=Path(d)/"db.sqlite",
                    archive=Path(d)/"archive",issues_db=Path(d)/"issues.sqlite",
                    issues_root=Path(d)/"rechecks",batches=1)
        self.assertEqual(r["issue_status"],"RECHECK_ERROR")
        self.assertEqual(r["issues"]["error_type"],"ValueError")

    def test_unsafe_requested_batches_blocked_before_network(self):
        with self.assertRaisesRegex(ValueError,"UNSAFE_BATCH_COUNT"):
            drive(object(),run_token="r",batches=6)
        with self.assertRaisesRegex(ValueError,"UNSAFE_BATCH_COUNT"):
            drive(object(),run_token="r",batch_size=49)
if __name__=="__main__":
    unittest.main()
