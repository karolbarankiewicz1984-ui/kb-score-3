"""Offline regression tests for public-only one kickoff explanation.

Every row here is SYNTHETIC constructed from the fixed public, target-free
schedule; owner RSA is not present in CI and real mismatch remains unknown.
"""
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
import copy,json
from pathlib import Path
import unittest

from src.kb3_step14_one_kickoff_diagnosis import diagnose_one
from src.kb3_step14_full_identity_pit_audit import FullNativeAuditError

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json"

def build_fake_native(reference):
    native={}
    for season,document in reference["source_seasons"].items():
        role="VALIDATION" if season=="2025-26" else "TRAIN"
        for idx,row in enumerate(document["fixtures_target_free"]):
            date=row["date"];hour=row["time_london"]
            utc=datetime.fromisoformat(date+"T"+hour).replace(
                tzinfo=ZoneInfo("Europe/London")).astimezone(timezone.utc)
            native[f"SYNTHETIC_NOT_REAL_{season}_{idx}"]={
                "season":season,"role":role,
                "home_name":row["home_name"],"away_name":row["away_name"],
                "kickoff_utc":utc.isoformat().replace("+00:00","Z")}
    assert len(native)==1140
    return native

class OneTimeDisagreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference=json.loads(REFERENCE.read_text(encoding="utf8"))
        cls.native=build_fake_native(cls.reference)

    def test_one_synthetic_hour_difference_is_properly_classified_without_ids(self):
        ns=copy.deepcopy(self.native)
        key=next(iter(ns))
        before=datetime.fromisoformat(ns[key]["kickoff_utc"].replace("Z","+00:00"))
        ns[key]["kickoff_utc"]=(before+timedelta(hours=1)).isoformat().replace("+00:00","Z")
        r=diagnose_one(ns,self.reference)
        self.assertEqual(r["fully_matching_both_teams_and_utc"],1139)
        self.assertEqual(r["original_native_match_count_checked"],1140)
        self.assertEqual(len(r["time_disagreements"]),1)
        self.assertEqual(r["time_disagreements"][0]["difference_pitchapi_minus_public_minutes"],60)
        self.assertEqual(r["time_disagreements"][0]["home_name"],ns[key]["home_name"])
        self.assertNotIn("SYNTHETIC_NOT_REAL_",json.dumps(r))
        self.assertNotIn("fixture_id",json.dumps(r))
        self.assertNotIn("team_id",json.dumps(r))
        self.assertNotIn('"score_home"',json.dumps(r))
        self.assertFalse(r["gate14_pass"])
        self.assertFalse(r["training_allowed"])

    def test_no_difference_is_not_falsely_claimed(self):
        with self.assertRaisesRegex(FullNativeAuditError,"EXPECTED_ONE_KICKOFF"):
            diagnose_one(self.native,self.reference)

    def test_two_disagreements_refused(self):
        ns=copy.deepcopy(self.native)
        for k in list(ns)[:2]:
            utc=datetime.fromisoformat(ns[k]["kickoff_utc"].replace("Z","+00:00"))
            ns[k]["kickoff_utc"]=(utc+timedelta(minutes=30)).isoformat().replace("+00:00","Z")
        with self.assertRaisesRegex(FullNativeAuditError,"EXPECTED_ONE_KICKOFF"):
            diagnose_one(ns,self.reference)

    def test_team_pair_cannot_be_replaced_by_same_hour(self):
        ns=copy.deepcopy(self.native)
        k=next(iter(ns))
        ns[k]["home_name"]="Completely Different Team"
        with self.assertRaisesRegex(FullNativeAuditError,"EXPECTED_ONE_KICKOFF"):
            diagnose_one(ns,self.reference)

    def test_forged_reference_and_resigned_self_hash_refused(self):
        from src.kb3_split import sha
        public=copy.deepcopy(self.reference)
        public["source_seasons"]["2023-24"]["fixtures_target_free"][0]["time_london"]="00:05"
        public["projection_sha256"]=sha({k:v for k,v in public.items() if k!="projection_sha256"})
        ns=copy.deepcopy(self.native)
        k=next(iter(ns))
        before=datetime.fromisoformat(ns[k]["kickoff_utc"].replace("Z","+00:00"))
        ns[k]["kickoff_utc"]=(before+timedelta(hours=1)).isoformat().replace("+00:00","Z")
        with self.assertRaisesRegex(FullNativeAuditError,"PUBLIC_1140_REFERENCE_NOT_AUTHENTIC"):
            diagnose_one(ns,public)

    def test_only_1140_full_original_size_accepted(self):
        ns=copy.deepcopy(self.native)
        del ns[next(iter(ns))]
        with self.assertRaisesRegex(FullNativeAuditError,"NATIVE_SOURCE_NOT_FULL"):
            diagnose_one(ns,self.reference)

if __name__=="__main__":unittest.main()
