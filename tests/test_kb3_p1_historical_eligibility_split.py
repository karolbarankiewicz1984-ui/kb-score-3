"""Safety for the separate chronological RECONSTRUCTED vs formal v2 gate."""
from __future__ import annotations
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from scripts.kb3_p1_historical_eligibility_split import (
    _manifest, chronological_split, write_report, assess, SOURCE_DB,
    RECHECK_DB, EligibilityError, SELECTED_HISTORICAL_SEASONS,
)


def fixtures(n=20):
    from datetime import datetime, timezone
    start=datetime(2025,1,1,tzinfo=timezone.utc)
    return [
        {"league": "BEL" if i%2 else "ESP",
         "fixture_id": f"fixture-{i}",
         "season": "2024/2025",
         "kickoff_utc": (start+timedelta(days=i)).isoformat().replace("+00:00","Z"),
         "proxy_cutoff_utc":
         (start+timedelta(days=i)-timedelta(hours=2)).isoformat().replace("+00:00","Z"),
         "history5": True, "core5": i%3==0, "xg5": i%5==0}
        for i in range(n)
    ]


class P1DatasetSplit(unittest.TestCase):
    def test_chronological_with_gap_disjoint(self):
        tr,val,removed,info=chronological_split(fixtures(50))
        self.assertTrue(tr)
        self.assertTrue(val)
        self.assertEqual(len(tr)+len(val)+len(removed),50)
        self.assertTrue(info["chronological_no_overlap"])
        self.assertLess(tr[-1]["kickoff_utc"], val[0]["kickoff_utc"])
        self.assertGreaterEqual(
            (__import__("datetime").datetime.fromisoformat(
                val[0]["kickoff_utc"].replace("Z","+00:00")) -
             __import__("datetime").datetime.fromisoformat(
                tr[-1]["kickoff_utc"].replace("Z","+00:00"))).days, 7)
        self.assertFalse(set((r["league"],r["fixture_id"]) for r in tr) &
                         set((r["league"],r["fixture_id"]) for r in val))

    def test_tied_kickoffs_cannot_cross_train_validation(self):
        src=fixtures(24)
        src[17]["kickoff_utc"]=src[16]["kickoff_utc"]
        src[18]["kickoff_utc"]=src[16]["kickoff_utc"]
        tr,val,removed,info=chronological_split(src, fraction=.70)
        times_train={x["kickoff_utc"] for x in tr}
        times_val={x["kickoff_utc"] for x in val}
        self.assertFalse(times_train & times_val)

    def test_empty_and_too_small_is_explicitly_not_ready(self):
        tr,val,held,meta=chronological_split([])
        self.assertEqual((tr,val,held),([],[],[]))
        self.assertEqual(meta["status"],"INSUFFICIENT_RESEARCH_COHORT")

    def test_reject_current_season_even_when_called_on_raw_candidates(self):
        src=fixtures(20)
        src[0]["season"]="2026/2027"
        with self.assertRaisesRegex(EligibilityError,
                                    "CURRENT_OR_PROTECTED_SEASON_LEAK"):
            chronological_split(src)

    def test_research_selectors_have_no_target_labels(self):
        tr,val,held,meta=chronological_split(fixtures(45))
        selectors=_manifest(tr,"RESEARCH_TRAIN")
        self.assertTrue(selectors)
        self.assertFalse(selectors[0]["train_approved"])
        self.assertFalse(selectors[0]["official_fit_eligible"])
        self.assertFalse(selectors[0]["historical_original_pit_certified"])
        self.assertFalse(any("score" in k or "outcome" in k or "label" in k
                             for x in selectors for k in x))

    def test_formal_train_val_manifest_is_empty_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report={
                "schema":"synthetic", "official_v2_training_eligible":0,
                "official_v2_validation_eligible":0}
            train=_manifest(fixtures(3),"RESEARCH_TRAIN")
            write_report(report,train,[],tmp)
            formal=json.loads((Path(tmp)/
                 "FORMAL_V2_TRAIN_VALIDATION_NO_ELIGIBLE_ROWS.json").read_text())
            self.assertEqual(formal["train"],[])
            self.assertEqual(formal["validation"],[])
            self.assertFalse(formal["fit_allowed"])
            self.assertTrue((Path(tmp)/
                "RECONSTRUCTED_RESEARCH_TRAIN_SELECTORS.json").is_file())

    def test_existing_real_historical_sqlite_integrity_and_not_pit(self):
        # Real checked-in data, no network and no DB mutation. This test can
        # cost ~seconds; source team IDs never printed.
        self.assertTrue(SOURCE_DB.exists())
        report,tr,val=assess(SOURCE_DB,RECHECK_DB)
        self.assertEqual(report["official_v2_training_eligible"],0)
        self.assertEqual(report["official_v2_validation_eligible"],0)
        self.assertFalse(report["source_first_published_proven"])
        self.assertFalse(report["formal_catboost_85_retraining_authorized"])
        self.assertFalse(report["research_reconstruction"][
            "historical_v2_feature_vector_exported"])
        self.assertGreater(report["research_reconstruction"][
            "national_league_observations"],0)
        self.assertTrue(all(x["season"] in SELECTED_HISTORICAL_SEASONS
                            for x in tr+val))
        self.assertFalse(any("outcome" in x or "score" in x for x in tr+val))


if __name__=="__main__":
    unittest.main()
