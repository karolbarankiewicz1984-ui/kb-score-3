"""True live Step11 code exercised with synthetic provider receipts and real new CBM.

All fake fixtures stay in unit tests; none is a host-attested true forecast.
"""
from __future__ import annotations
import copy,json,os,sqlite3,tempfile,unittest
from datetime import timedelta
from pathlib import Path

from test_step16_m0_720_eight_forward import fake_receipts,NOW
from src.kb3_step16_m0_720_eight_forward import (
    make_forecasts,freeze_sqlite,trained_params,hashobj)
from src.kb3_p1_prospective_shadow_six_v1 import (
    ShadowSix,ShadowSafetyError,make_vector,freeze_only_new_m0,
    check_model_manifest,DB_SCHEMA)
from scripts.kb3_p1_prospective_six_train import FORWARD_KEYS,MODEL


class ProspectiveShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=os.environ.get("KB3_SHADOW_SIX_MODEL_DIR")
        if not root:
            raise RuntimeError("RESEARCH_SIX_MODEL_DIR_REQUIRED_RUN_TRAIN_FIRST")
        cls.folder=Path(root)
        cls.manifest_path=cls.folder/"KB3_CATBOOST_SHADOW_SIX_MANIFEST.json"
        cls.binary_path=cls.folder/"KB3_CATBOOST_SHADOW_SIX_RESEARCH.cbm"
        cls.manifest=json.loads(cls.manifest_path.read_text())
        cls.engine=ShadowSix(manifest_file=cls.manifest_path,
                             model_file=cls.binary_path,
                             clock=lambda:NOW+timedelta(seconds=15))
        cls.params,cls.sha,cls.manifest_sha=trained_params()
        cls.snapshots=[]
        class Collector:
            def records(self,state,parent):
                cls.snapshots.append((copy.deepcopy(state),copy.deepcopy(parent)))
                return cls.engine.records(state,parent)
        cls.forecasts,_,_=make_forecasts(
            fake_receipts(),cutoff=NOW,params=cls.params,
            param_sha=cls.sha,manifest_sha=cls.manifest_sha,
            challenger_engine=Collector(),challenger_sink=cls._shadow_sink())
        cls.records_list=cls._shadow_sink().records
    @classmethod
    def _shadow_sink(cls):
        # Shared sink for make_forecasts in setUpClass.
        if not hasattr(cls,"_sink"):
            class Sink(list):
                pass
            cls._sink=Sink()
            cls._sink.records=cls._sink
        return cls._sink

    def test_real_trained_model_six_features_and_manifest_hash(self):
        self.assertEqual(list(self.engine.model.feature_names_),list(FORWARD_KEYS))
        self.assertEqual(len(FORWARD_KEYS),6)
        self.assertEqual(self.manifest["training_rows"],1007)
        self.assertEqual(self.manifest["validation_rows"],376)
        self.assertFalse(self.manifest["production_approved"])
        self.assertFalse(self.manifest["formal_asof_v2_trained"])

    def test_fresh_same_cutoff_shadow_has_exact_m0_parent(self):
        self.assertEqual(len(self.forecasts),64)
        self.assertEqual(len(self.records_list),64)
        byid={x["forecast_sha256"]:x for x in self.forecasts}
        self.assertEqual(len(byid),64)
        for child in self.records_list:
            original=byid[child["source_m0_forecast_sha256"]]
            self.assertEqual(child["feature_sha256"],original["feature_sha256"])
            self.assertEqual(child["original_feature_cutoff_utc"],
                             original["feature_cutoff_utc"])
            self.assertEqual(child["source_chain_sha256"],
                             original["source_chain_sha256"])
            self.assertEqual(set(child["p_1x2"]),{"1","X","2"})
            self.assertAlmostEqual(sum(child["p_1x2"].values()),1)
            self.assertFalse(child["shadow_host_artifact_verified"])
            self.assertFalse(child["official_fit_eligible"])
            self.assertFalse(child["production_approved"])

    def test_snapshot_provenance_reject_late_and_labelled_sources(self):
        state,parent=self.snapshots[0]
        bad=copy.deepcopy(state)
        bad["features"]["home_all_5_n"]=4
        with self.assertRaisesRegex(ShadowSafetyError,"MISSING_LAST5_HISTORY"):
            make_vector(bad)
        bad=copy.deepcopy(state)
        bad["availability_class"]="HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT"
        with self.assertRaisesRegex(ShadowSafetyError,"UNVERIFIED_OR_RECONSTRUCTED"):
            make_vector(bad)
        bad=copy.deepcopy(state)
        bad["features"]["home_all_5_gf_avg"]=None
        with self.assertRaisesRegex(ShadowSafetyError,"SIX_FORWARD_REAL_GOAL_FORM"):
            make_vector(bad)
        bad=copy.deepcopy(parent)
        bad["kickoff_utc"]=parent["generated_at_utc"]
        bad["forecast_sha256"]=hashobj({
            k:v for k,v in bad.items() if k!="forecast_sha256"})
        with self.assertRaisesRegex(ShadowSafetyError,
                                   "M0_FEATURE_AND_ASOF_DRIFT|SHADOW_NOT_GENERATED"):
            self.engine.records(state,bad)
        later=ShadowSix(manifest_file=self.manifest_path,
            model_file=self.binary_path,clock=lambda:NOW+timedelta(days=5))
        with self.assertRaisesRegex(ShadowSafetyError,
                                   "SHADOW_NOT_GENERATED_WITH_NEW_EARLY_PARENT"):
            later.records(state,parent)

    def test_manipulated_model_digest_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"changed.cbm"
            file.write_bytes(self.binary_path.read_bytes()+b"modified")
            with self.assertRaisesRegex(ShadowSafetyError,
                                       "SHADOW_MODEL_BYTES_NOT_PINNED"):
                check_model_manifest(self.manifest,file)
        wrong=copy.deepcopy(self.manifest)
        wrong["production_approved"]=True
        with self.assertRaisesRegex(ShadowSafetyError,
                                   "UNEXPECTED_MODEL_MANIFEST_OR_FALSE_PIT"):
            check_model_manifest(wrong,self.binary_path)

    def test_immutable_sqlite_appends_only_for_new_m0(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"m0_staging.sqlite"
            fresh=set()
            n,all_n=freeze_sqlite(db,self.forecasts,param_sha=self.sha,
                 manifest_sha=self.manifest_sha,now=NOW,
                 new_frozen_ids=fresh)
            self.assertEqual((n,all_n),(64,64))
            before=db.read_bytes()
            applied=freeze_only_new_m0(db,self.records_list,new_m0_ids=fresh)
            self.assertEqual((applied["added"],applied["total"]),(64,64))
            self.assertEqual(applied["official_fit_increment"],0)
            with sqlite3.connect(db) as cn:
                self.assertEqual(cn.execute(
                    "SELECT COUNT(*) FROM forecasts").fetchone()[0],64)
                self.assertEqual(cn.execute(
                    "SELECT COUNT(*) FROM kb3_p1_shadow_six_new_only").fetchone()[0],64)
                with self.assertRaises(sqlite3.IntegrityError):
                    cn.execute("UPDATE kb3_p1_shadow_six_new_only SET model_version='wrong'")
                with self.assertRaises(sqlite3.IntegrityError):
                    cn.execute("DELETE FROM kb3_p1_shadow_six_new_only")
            # A later rerun cannot append to any existing parent.
            skipped=freeze_only_new_m0(db,self.records_list,new_m0_ids=set())
            self.assertEqual(skipped["added"],0)
            self.assertEqual(skipped["skipped_old_m0"],64)
            self.assertEqual(skipped["total"],64)

    def test_tampered_forecast_and_shadow_row_refused(self):
        state,parent=self.snapshots[0]
        bad=copy.deepcopy(parent)
        bad["p_1x2"]={"1":.8,"X":.1,"2":.1}
        with self.assertRaisesRegex(ShadowSafetyError,"NOT_ORIGINAL_IMMUTABLE"):
            self.engine.records(state,bad)
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"m0_staging.sqlite"
            fresh=set()
            freeze_sqlite(db,self.forecasts,param_sha=self.sha,
                          manifest_sha=self.manifest_sha,
                          now=NOW,new_frozen_ids=fresh)
            row=copy.deepcopy(self.records_list[0])
            row["p_1x2"]={"1":.8,"X":.1,"2":.1}
            with self.assertRaisesRegex(ShadowSafetyError,
                                       "TAMPERED_OR_PROMOTED"):
                freeze_only_new_m0(db,[row],new_m0_ids=fresh)


if __name__=="__main__":
    unittest.main()
