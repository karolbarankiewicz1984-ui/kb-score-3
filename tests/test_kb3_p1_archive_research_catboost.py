"""Real read-only repository evidence and protected TRAIN/VALIDATION boundaries."""
from __future__ import annotations
import unittest
import copy
import math
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from datetime import timedelta

from scripts.kb3_p1_archived_source_recovery_audit import run as archive,ArchiveSafety
from scripts.kb3_p1_retro_catboost_1007_376 import (
    BASE, WITH_XG, GOALS, CORE, XG, RetroResearchError,
    build_features_without_target_label, load_sets, numeric,
)
from scripts.kb3_p1_historical_eligibility_split import utc,SOURCE_DB,assess


def historical_fixture(match,ko,home,away,goals=(0,0)):
    return {"scope":"ESP","match_id":match,"season":"2024/2025",
            "kickoff_utc":ko,"home_team_id":home,"away_team_id":away,
            "goals_home_90":goals[0],"goals_away_90":goals[1]}


class Tests(unittest.TestCase):
    def test_actual_saved_archive_provenance_is_not_native_eight(self):
        a=archive()
        self.assertEqual(a["old_1140_native_ENG_public_witnessed_snapshots"],13)
        self.assertEqual(a["newer_2025_ENG_public_witnessed_old_source_versions"],25)
        self.assertEqual(a["verified_eight_league_historical_prematch_v2_training_targets"],0)
        self.assertFalse(a["formal_training_approved"])
        self.assertTrue(a["do_not_transfer_public_fpl_xg_to_native_pitchapi"])
        source=a["eight_league_source_observations"]
        self.assertGreaterEqual(source["observed_stats_rows"],1525)
        self.assertGreaterEqual(source["native_eight_stats_rows"],1520)
        self.assertEqual(a["current_inventory_delta_from_archived_experiment"],
                         source["observed_stats_rows"]-1525)
        self.assertEqual(source["provider_first_published_present"],0)
        self.assertEqual(source["fixture_first_published_present"],0)
        self.assertEqual(source["observed_stats_before_target_minus90min"],0)
        self.assertEqual(source["fixture_listed_before_target_minus90min"],0)
        self.assertEqual(source["distinct_history_target_receipts"],0)
        self.assertFalse(a["original_experiment_replayed_on_current_source"])

    def test_actual_retro_source_partition_safety(self):
        tr,val,meta=load_sets()
        current_gate,train_selectors,validation_selectors=assess(SOURCE_DB)
        self.assertEqual(len(tr),len(train_selectors))
        self.assertEqual(len(val),len(validation_selectors))
        self.assertEqual(len(tr)+len(val)+meta["cohort_embargo_discarded"],
                         current_gate["research_reconstruction"][
                             "potential_historical_no_xg_history5"])
        self.assertEqual((meta["cohort_train_n"],meta["cohort_validation_n"]),
                         (len(tr),len(val)))
        self.assertFalse(meta["original_shadow_six_immutable_binary_reused"])
        self.assertFalse(meta["formal_training_allowed"])
        self.assertEqual(meta["feature_count_no_xg"],14)
        self.assertEqual(meta["feature_count_with_xg"],18)
        self.assertTrue(all(x["league"]!="ENG" for x in tr+val))
        self.assertGreaterEqual(min(utc(x["kickoff_utc"]) for x in val)
            -max(utc(x["kickoff_utc"]) for x in tr),timedelta(days=7))
        self.assertTrue(all("target_score" not in x["features"]
                            for x in tr+val))

    def test_pinned_shadow_six_stays_immutable_when_research_history_grows(self):
        manifest=json.loads((Path(__file__).resolve().parents[1] /
            "assets/research/kb3_shadow_six_v1/KB3_CATBOOST_SHADOW_SIX_MANIFEST.json").read_text())
        _,_,meta=load_sets()
        self.assertEqual((manifest["training_rows"],manifest["validation_rows"]),
                         (1007,376))
        self.assertFalse(manifest["production_approved"])
        self.assertFalse(meta["formal_training_allowed"])
        self.assertNotEqual(manifest["retrospective_source_sha256"],
                            meta["historical_source_sha256"],
                            "Growing source must not masquerade as frozen research snapshot")

    def test_forged_original_publication_clock_still_fails_closed(self):
        # Separate disposable SQLite copy: never change the checked-in source.
        with tempfile.TemporaryDirectory() as td:
            copy_db=Path(td)/"observations.sqlite"
            shutil.copyfile(SOURCE_DB,copy_db)
            with sqlite3.connect(copy_db) as db:
                db.execute("""UPDATE observations
                    SET provider_first_published_at_utc=?
                    WHERE rowid=(SELECT MIN(rowid) FROM observations)""",
                    ("2024-01-01T00:00:00Z",))
                db.commit()
            with self.assertRaises(ArchiveSafety):
                archive(db_path=copy_db)

    def test_no_label_leak_even_if_target_result_changes(self):
        fixtures=[historical_fixture(f"f{i}",f"2025-01-{i:02d}T18:00:00Z",
                    "A" if i%2 else "C","B" if i%2 else "A",(i%2,1))
                  for i in range(1,13)]
        target=historical_fixture("target","2025-02-01T18:00:00Z",
                                  "A","B",(3,0))
        clock=[utc(f["kickoff_utc"]) for f in fixtures]
        source={}
        f1,flag1=build_features_without_target_label(target,fixtures,source,clock)
        altered=copy.deepcopy(target)
        altered["goals_home_90"]=0
        altered["goals_away_90"]=12
        f2,flag2=build_features_without_target_label(altered,fixtures,source,clock)
        self.assertEqual(f1,f2)
        self.assertEqual(flag1,flag2)
        self.assertTrue(flag1["history5"])
        self.assertEqual(len(f1),18)
        self.assertTrue(all(f1[k] is None for k in BASE if "fouls" in k))
        self.assertTrue(math.isnan(numeric(None)))

    def test_post_cutoff_fixture_cannot_enter_history(self):
        fixtures=[historical_fixture(f"f{i}",f"2025-01-{i:02d}T18:00:00Z",
                   "A","B") for i in range(1,13)]
        target=historical_fixture("target","2025-02-01T18:00:00Z",
                                  "A","B")
        clock=[utc(f["kickoff_utc"]) for f in fixtures]
        bad=fixtures+[historical_fixture("later","2025-02-02T18:00:00Z","A","B")]
        good,_=build_features_without_target_label(target,fixtures,{},clock)
        badclocks=clock+[utc(bad[-1]["kickoff_utc"])]
        added,_=build_features_without_target_label(target,bad,{},badclocks)
        self.assertEqual(good,added)

    def test_feature_list_exactly_same_fixed_research_semantics(self):
        self.assertEqual(len(BASE),14)
        self.assertEqual(len(WITH_XG),18)
        self.assertTrue(set(BASE)<set(WITH_XG))
        self.assertTrue(all("score" not in v and "label" not in v
                            for v in WITH_XG))


if __name__=="__main__":
    unittest.main()
