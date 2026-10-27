"""Real score-free temporal collision audit and immutable source negative tests."""
import copy,json
from pathlib import Path
import unittest

from src.kb3_step14_calendar_collision_audit import audit_calendar,run
from src.kb3_step14_full_identity_pit_audit import FullNativeAuditError
from src.kb3_split import sha

ROOT=Path(__file__).resolve().parents[1]
SAFE=ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
PUBLIC=ROOT/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json"

class CalendarCollisionAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.safe=json.loads(SAFE.read_text(encoding="utf8"))
        cls.public=json.loads(PUBLIC.read_text(encoding="utf8"))

    def test_all_1140_real_safe_kickoffs_without_reading_test(self):
        r=run(ROOT)
        self.assertEqual(r["total_train_validation_utc_kickoffs_examined"],1140)
        self.assertEqual(r["total_test_rows_examined"],0)
        self.assertTrue(r["same_kickoff_is_not_fixture_identity_proof"])
        self.assertEqual(sum(r["candidate_count_statuses"].values()),1140)
        self.assertEqual(sum(r["by_role"]["TRAIN"].values()),760)
        self.assertEqual(sum(r["by_role"]["VALIDATION"].values()),380)
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["gate14_pass"])
        self.assertNotIn("score_home",json.dumps(r))

    def test_resigned_public_reference_with_changed_kickoff_cannot_pass(self):
        fake=copy.deepcopy(self.public)
        fake["source_seasons"]["2025-26"]["fixtures_target_free"][0]["time_london"]="11:00"
        fake["projection_sha256"]=sha({k:v for k,v in fake.items() if k!="projection_sha256"})
        with self.assertRaisesRegex(FullNativeAuditError,"PUBLIC_1140_REFERENCE_NOT_AUTHENTIC"):
            audit_calendar(self.safe,fake)

    def test_modifying_train_fixture_is_rejected_even_if_schedule_self_resigned(self):
        fake=copy.deepcopy(self.safe)
        row=next(v for v in fake["fixtures"] if v["partition"]=="TRAIN")
        row["kickoff_utc"]="2024-02-02T12:00:00Z"
        fake["projection_sha256"]=sha({k:v for k,v in fake.items() if k!="projection_sha256"})
        with self.assertRaisesRegex(FullNativeAuditError,"FROZEN_SAFE_VIEW_NOT_VERIFIED"):
            audit_calendar(fake,self.public)

    def test_actual_2025_sep_21_kickoff_has_public_candidate(self):
        # This was the user-discovered false identity (Bournemouth-Newcastle
        # vs Sunderland-Villa). Schedule-only can never attest team identity.
        r=run(ROOT)
        self.assertGreaterEqual(
            r["candidate_count_statuses"].get("MULTIPLE_PUBLIC_SAME_KICKOFF",0),1)

    def test_no_test_fixture_identity_or_score_in_report(self):
        r=run(ROOT)
        self.assertEqual(r["independently_verified_teams_by_kickoff_in_this_audit"],0)
        self.assertEqual(r["total_test_rows_examined"],0)
        self.assertNotIn("fixture_id",json.dumps(r))
        self.assertNotIn("score",json.dumps(r))
        self.assertNotIn("odds",json.dumps(r))

if __name__=="__main__":unittest.main()
