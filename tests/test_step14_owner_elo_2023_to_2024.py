"""Fail-closed tests: no numeric rating or private labels escape."""
import copy,json,unittest
from pathlib import Path
from src.kb3_step14_owner_elo_2023_to_2024 import (
    FULL_2023,SCHEMA,RolloverError,check_pinned_public_evidence,
    allowlist_only_before_2024_targets,crossseason_replay_and_compare,audit
)

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/"data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json"

class OwnerEloRolloverTests(unittest.TestCase):
    def test_exact_frozen_real_independent_gharchive_proof(self):
        record=json.loads(PROOF.read_text(encoding="utf8"))
        check_pinned_public_evidence(record)
        self.assertEqual(FULL_2023["event_id"],"38750359648")
        self.assertEqual(FULL_2023["push"],"2024-05-27T18:05:12Z")
    def test_git_commit_time_not_accepted_instead_of_server_clock(self):
        record=json.loads(PROOF.read_text(encoding="utf8"))
        record["full_season_EPL_2023_24"]["event_server_UTC"]="2024-05-27T18:05:02Z"
        with self.assertRaisesRegex(RolloverError,"PUBLICATION_PROOF"):
            check_pinned_public_evidence(record)
    def test_wrong_hash_blocks(self):
        record=json.loads(PROOF.read_text(encoding="utf8"))
        record["full_season_EPL_2023_24"]["raw_sha256"]="0"*64
        with self.assertRaisesRegex(RolloverError,"PUBLICATION_PROOF"):
            check_pinned_public_evidence(record)
    def test_gate_premature_promotion_is_rejected(self):
        record=json.loads(PROOF.read_text(encoding="utf8"))
        record["GATE14"]="PASS"
        with self.assertRaisesRegex(RolloverError,"PUBLICATION_PROOF"):
            check_pinned_public_evidence(record)
    def test_no_native_archive_does_not_forge_elo_success(self):
        with self.assertRaisesRegex(RolloverError,"OWNER_RSA_NATIVE"):
            audit({},[],b"",b"",{})
    def test_unverified_full_source_cannot_construct_allowlist(self):
        with self.assertRaises(Exception):
            allowlist_only_before_2024_targets({},b'bad source',b'bad')
    def test_no_original_score_or_native_team_data_export_in_contract(self):
        self.assertIn("research",SCHEMA)
        self.assertNotIn("train-ready",SCHEMA)

if __name__=="__main__":unittest.main()
