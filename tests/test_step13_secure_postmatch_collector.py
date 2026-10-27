"""STRICT fake results: never use any real TEST result, API or network."""
import copy,json,unittest,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from src.kb3_pit_ledger import utc_now
from src.kb3_pitch_uefa_evidence import add_observation
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_forward_score import SOURCE_FILE
from scripts.step13_first_ten_secure_postmatch_once import (
   check_earliest_frozen,validate_captured_receipts,seal_evidence,MAGIC,AAD)

FAKE_TIME="2026-11-03T09:30:00Z"

def sample():
    first=json.loads(Path(SOURCE_FILE).read_text("utf8"))
    events=[]
    for n,f in enumerate(sorted(first["forecasts"],key=lambda x:x["fixture_id"])):
        # Source records are SYNTHETIC_TEST origin, not fabricated as network.
        body={"id":f["fixture_id"],"time_utc":f["kickoff_utc"],"status":"finished",
              "home_team":{"id":f["home_team_id"],"name":"SYN HOME"},
              "away_team":{"id":f["away_team_id"],"name":"SYN AWAY"},
              "score_home":n%3,"score_away":(n+1)%4}
        time=f"2026-11-03T09:{n:02d}:00Z"
        add_observation(events,resource=f"pitchapi:step13:final:{f['fixture_id']}",
                        payload=body,started=time,completed=time,origin="SYNTHETIC_TEST")
    return first,events

class Step13PostmatchCollectorOnlySynthetic(unittest.TestCase):
    def test_future_only_for_ten_and_aggregates(self):
        first,events=sample()
        report,proof=validate_captured_receipts(first,events,evaluation_time=FAKE_TIME,allow_synthetic=True)
        self.assertEqual(proof["sessions"],10)
        self.assertEqual(report["result_labels_for_this_prespecified_shadow_sample_read"],10)
        self.assertEqual(report["other_370_test_labels_read_by_this_protocol"],0)
        self.assertEqual(report["other_test_results_requested"],0)
        self.assertTrue(report["capture_chain_locally_verified"])
        self.assertEqual(report["source_evidence_kind"],"SYNTHETIC_TEST_ONLY")
        self.assertFalse(report["gate13_pass"])
        self.assertNotIn("goals_home_90",str(report))
        self.assertNotIn(events[0]["payload"]["id"],str(report))
    def test_real_vs_synthetic_origin_guard(self):
        first,events=sample()
        with self.assertRaisesRegex(BaselineSafetyError,"WRONG_OBSERVATION_ORIGIN"):
            validate_captured_receipts(first,events,evaluation_time=FAKE_TIME)
    def test_no_request_before_last_kickoff_plus_lag(self):
        first,events=sample()
        with self.assertRaisesRegex(BaselineSafetyError,"NO_ACCESS_BEFORE_ALL_FINAL_LAG"):
            check_earliest_frozen(first,"2026-11-02T22:59:59Z")
    def test_exact_id_wrong_or_extra_refused(self):
        first,events=sample()
        events[0]["payload"]["id"]="m_ZZzz99"
        with self.assertRaises(ValueError):
            validate_captured_receipts(first,events,evaluation_time=FAKE_TIME,allow_synthetic=True)
    def test_source_tamper_rejected_by_chain(self):
        first,events=sample()
        events[0]["payload"]["score_home"]=28
        with self.assertRaisesRegex(ValueError,"TAMPERED"):
            validate_captured_receipts(first,events,evaluation_time=FAKE_TIME,allow_synthetic=True)
    def test_unfinished_game_rejected(self):
        first,events=sample()
        # Must update source hash+chain to test STATUS refusal (not hash guard).
        from src.kb3_pit_ledger import hexdigest,canonical
        events[0]["payload"]["status"]="not_started"
        events[0]["payload_sha256"]=hexdigest(canonical(events[0]["payload"]))
        old=dict(events[0]);old.pop("chain_sha256")
        events[0]["chain_sha256"]=hexdigest(canonical(old))
        for idx in range(1,len(events)):
            events[idx]["previous_sha256"]=events[idx-1]["chain_sha256"]
            d=dict(events[idx]);d.pop("chain_sha256")
            events[idx]["chain_sha256"]=hexdigest(canonical(d))
        with self.assertRaisesRegex(BaselineSafetyError,"SOURCE_IDENTITY_OR_STATUS"):
            validate_captured_receipts(first,events,evaluation_time=FAKE_TIME,allow_synthetic=True)
    def test_one_missing_denied(self):
        first,events=sample()
        with self.assertRaisesRegex(BaselineSafetyError,"EXACTLY_10_RECEIPTS"):
            validate_captured_receipts(first,events[:-1],evaluation_time=FAKE_TIME,allow_synthetic=True)
    def test_encrypted_evidence_contains_no_readable_scores_and_no_rewrite(self):
        first,events=sample()
        _,proof=validate_captured_receipts(first,events,evaluation_time=FAKE_TIME,allow_synthetic=True)
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/"encrypted.bin";m=Path(tmp)/"manifest.json"
            x=seal_evidence(events,proof,recipient="config/step11_archive_recipient_public.pem",
               encrypted_path=c,manifest_path=m)
            self.assertTrue(c.read_bytes().startswith(MAGIC))
            self.assertNotIn(b"goals_home_90",c.read_bytes())
            self.assertNotIn(b"score_home",c.read_bytes())
            self.assertEqual(x["resource_count"],10)
            self.assertFalse(x["independent_decryption_verified"])
            self.assertEqual(len(x["encrypted_sha256"]),64)
            with self.assertRaises(FileExistsError):
                seal_evidence(events,proof,recipient="config/step11_archive_recipient_public.pem",
                    encrypted_path=c,manifest_path=m)

if __name__=="__main__":unittest.main()
