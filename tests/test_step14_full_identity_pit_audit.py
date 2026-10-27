"""Full 1140 TRAIN/VALIDATION owner-only audit: all fixtures synthetic mock.

CI NEVER decrypts real PitchAPI archives or uses the private RSA key. These
checks prove fail-closed behavior, not completed real local verification.
"""
from datetime import datetime
from unittest.mock import patch
import copy,json
from pathlib import Path
import unittest

from src.kb3_step14_full_identity_pit_audit import (
    audit_1140,_validate_safe,_public_sample,_feature_family,FullNativeAuditError
)
from src.kb3_step14_native_team_crosswalk import ARCHIVE_CHAIN_SHA,SAFE_SHA
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING

ROOT=Path(__file__).resolve().parents[1]
OBS="2026-10-26T13:17:47.692940Z"
RES="pitchapi:history:premier-league:{season}:matches:played"


def fixture_source(safe):
    rows=safe["fixtures"]
    sources=[{"resource":"pitchapi:catalog"}]
    for start in (2023,2024,2025):
        fixtures=sorted([x for x in rows
             if x["partition"]!= "TEST" and x["kickoff_utc"][:4]==str(start)
             or x["partition"]!="TEST" and x["kickoff_utc"][:4]==str(start+1)
                  and x["kickoff_utc"][5:7]<"08" ],
            key=lambda x:(x["kickoff_utc"],x["fixture_id"]))
        # Prefer real season window with 380 fixtures, based on August-June.
        fixtures=[x for x in safe["fixtures"] if x["partition"]!="TEST"
                 and f"{start}-08-01"<x["kickoff_utc"][:10]<f"{start+1}-08-01"]
        fixtures.sort(key=lambda x:(x["kickoff_utc"],x["fixture_id"]))
        assert len(fixtures)==380,(start,len(fixtures))
        pairs=[(h,a) for h in range(20) for a in range(20) if h!=a]
        matches=[]
        for item,(h,a) in zip(fixtures,pairs):
            matches.append({
                "id":item["fixture_id"],"time_utc":item["kickoff_utc"],
                "home_team":{"id":f"t_{h:06d}","name":f"Team {h:02d}"},
                "away_team":{"id":f"t_{a:06d}","name":f"Team {a:02d}"},
                # Label-bearing fields deliberately present to prove scrubbed.
                "score_home":h%4,"score_away":a%3,
                "winner":"DONT_READ","odds":{"B365H":1.1},
            })
        sources.append({"resource":RES.format(season=f"{start}/{start+1}"),
                        "completed_at_utc":OBS,"payload":{"matches":matches}})
    return sources


class Full1140Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.safe=json.loads((ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())

    def run_audit(self,receipts=None,safe=None,**kwargs):
        data=fixture_source(self.safe) if receipts is None else receipts
        with patch("src.kb3_step14_full_identity_pit_audit.verify_receipts",
                   return_value={"final_chain_sha256":ARCHIVE_CHAIN_SHA}):
            return audit_1140(safe=self.safe if safe is None else safe,receipts=data,**kwargs)

    def test_original_safe_manifest_is_actually_pinned(self):
        idx=_validate_safe(self.safe)
        self.assertEqual(len(idx),1140)
        self.assertEqual(sum(v[1]=="TRAIN" for v in idx.values()),760)
        self.assertEqual(sum(v[1]=="VALIDATION" for v in idx.values()),380)

    def test_1140_identities_and_all_159_fields_remain_denied(self):
        r=self.run_audit()
        self.assertEqual(r["native_identity_fixture_ids_checked"],1140)
        self.assertEqual(r["native_identity_within_pitchapi_sealed_source_verified"],1140)
        self.assertEqual(r["identity_checked_partition_counts"],{"TRAIN":760,"VALIDATION":380})
        self.assertEqual(r["original_retrospective_source_observed_after_target_kickoff"],1140)
        self.assertEqual(r["feature_contract_numeric_nullable_field_count"],len(EXPECTED_FEATURES))
        self.assertEqual(r["feature_contract_missing_flag_count"],len(EXPECTED_MISSING))
        self.assertEqual(r["feature_contract_total_lineage_proofs_expected"],159)
        self.assertEqual(r["real_training_prematch_proven_rows"],0)
        self.assertEqual(r["test_matches_inspected"],0)
        self.assertFalse(r["match_results_or_odds_exported"])
        self.assertFalse(r["native_fixture_ids_or_native_team_ids_exported"])
        self.assertFalse(r["gate14_pass"])
        self.assertFalse(r["training_allowed"])
        self.assertNotIn("DONT_READ",json.dumps(r))
        self.assertNotIn("B365H",json.dumps(r))
        self.assertNotIn("t_000000",json.dumps(r))

    def test_all_feature_families_are_blocked_from_retrospective_receipt(self):
        r=self.run_audit()
        self.assertEqual(sum(r["field_family_counts"].values()),121)
        self.assertEqual(sum(r["missing_flag_family_counts"].values()),38)
        self.assertEqual(r["prematch_provider_result_history_asof_proven_rows"],0)
        for v in r["prematch_proven_by_original_pitchapi_receipts_by_family"].values():
            self.assertEqual(v["certified_train"],0)
            self.assertEqual(v["validation_missing_asof_proof"],380)

    def test_injected_label_in_safe_projection_is_refused(self):
        tamper=copy.deepcopy(self.safe)
        target=next(r for r in tamper["fixtures"] if r["partition"]=="TRAIN")
        target["result"]="home"
        with self.assertRaisesRegex(FullNativeAuditError,"FROZEN_SAFE_VIEW"):
            self.run_audit(safe=tamper)

    def test_swapped_native_fixture_id_is_refused(self):
        receipts=fixture_source(self.safe)
        receipts[1]["payload"]["matches"][0]["id"]="m_ZZZZZZ"
        with self.assertRaisesRegex(FullNativeAuditError,"NATIVE_ID_NOT_IN_TRAIN_VALIDATION"):
            self.run_audit(receipts=receipts)

    def test_native_wrong_kickoff_is_refused(self):
        receipts=fixture_source(self.safe)
        receipts[1]["payload"]["matches"][0]["time_utc"]="2023-10-01T00:00:00Z"
        with self.assertRaisesRegex(FullNativeAuditError,"NATIVE_ROLE_OR_KICKOFF"):
            self.run_audit(receipts=receipts)

    def test_native_team_id_same_name_collision_is_refused(self):
        receipts=fixture_source(self.safe)
        receipts[1]["payload"]["matches"][0]["home_team"]["name"]="Different Club"
        with self.assertRaisesRegex(FullNativeAuditError,"SAME_NATIVE_ID_DIFFERENT_TEAM_NAME"):
            self.run_audit(receipts=receipts)

    def test_native_same_team_both_sides_refused(self):
        receipts=fixture_source(self.safe)
        receipts[1]["payload"]["matches"][0]["away_team"]=receipts[1]["payload"]["matches"][0]["home_team"].copy()
        with self.assertRaisesRegex(FullNativeAuditError,"DUPLICATE_TEAM_FIXTURE_OR_SELF"):
            self.run_audit(receipts=receipts)

    def test_invalid_archive_hash_refused(self):
        with self.assertRaisesRegex(FullNativeAuditError,"PINNED_ARCHIVE_HASH_CHANGED"):
            self.run_audit(zip_sha="f"*64)

    def test_fake_provider_receipt_before_historical_kickoff_refused(self):
        receipts=fixture_source(self.safe)
        receipts[1]["completed_at_utc"]="2022-01-01T00:00:00Z"
        with self.assertRaisesRegex(FullNativeAuditError,"RETROSPECTIVE_SOURCE_CLOCK_INCONSISTENT"):
            self.run_audit(receipts=receipts)

    def test_provider_receipt_chain_mismatch_refused(self):
        with patch("src.kb3_step14_full_identity_pit_audit.verify_receipts",
                   return_value={"final_chain_sha256":"f"*64}):
            with self.assertRaisesRegex(FullNativeAuditError,"RECEIPT_CHAIN_CHANGED"):
                audit_1140(safe=self.safe,receipts=fixture_source(self.safe))

    def test_public_sample_cannot_be_manufactured_into_pit(self):
        blob=json.loads((ROOT/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json").read_text())
        clock=json.loads((ROOT/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json").read_text())
        native={}
        for r in blob["records"]:
            pairs=r["match_by_exact_uk_local_to_utc_kickoff"]
            home=(pairs[0]["home_name_openfootball"] if pairs else "Unmatched Home")
            away=(pairs[0]["away_name_openfootball"] if pairs else "Unmatched Away")
            if r["pitch_fixture_id"]=="m_0JJdwI":
                home,away="AFC Bournemouth","Newcastle United"
            native[r["pitch_fixture_id"]]={"kickoff_utc":r["kickoff_utc"],
                "season":r["season"],"role":r["partition"],
                "home_name":home,"away_name":away}
        out=_public_sample(native,blob,clock)
        self.assertEqual(out["sample_count"],60)
        self.assertEqual(sum(out["counts"].values()),60)
        self.assertTrue(out["independent_public_push_not_full_feature_PIT"])
        self.assertEqual(out["counts"]["IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB"],1)

if __name__=="__main__":unittest.main()
