"""Same-cutoff integration smoke on selected pinned CBM, NO live PitchAPI.

These are synthetic provider fixtures and real model binary bytes downloaded
from the previously validated research GitHub artifact; not true forecasts.
"""
import copy
import io
import zipfile
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from test_step16_m0_720_eight_forward import fake_receipts, NOW
from src.kb3_step16_m0_720_eight_forward import (
    make_forecasts,freeze_sqlite,trained_params
)
from src.kb3_step17_forward_challengers import (
    Challengers,freeze_new_challengers
)
from src.kb3_p1_shadow_live_gate import (
    load_opted_shadow,opt_in_enabled,pinned_model_details,
    ENV_NAME,MODEL_DIR_ENV
)
from src.kb3_p1_prospective_shadow_six_v1 import (
    ShadowSafetyError,freeze_only_new_m0
)
from src.kb3_p1_shadow_host_provenance import (
    _archived_shadow,audit_shadow,paired_settled_shadow
)


class NewSixLiveIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pinned=pinned_model_details()
        cls.folder=os.environ.get("KB3_SHADOW_SIX_MODEL_DIR")
        if not cls.folder:
            raise unittest.SkipTest(
                "PINNED_MODEL_ARTIFACT_REQUIRED_ONLY_IN_DEDICATED_SHADOW_CI")
        cls.clock=staticmethod(lambda:NOW+timedelta(seconds=20))
        cls.engine=load_opted_shadow(
            clock=cls.clock,
            environ={ENV_NAME:"true",MODEL_DIR_ENV:cls.folder})
        cls.legacy_engine=Challengers()
        cls.params,cls.params_sha,cls.manifest_sha=trained_params()

    def test_disabled_switch_cannot_load_even_when_folder_present(self):
        self.assertFalse(opt_in_enabled({}))
        self.assertFalse(opt_in_enabled({ENV_NAME:"false"}))
        self.assertIsNone(load_opted_shadow(environ={
            ENV_NAME:"false",MODEL_DIR_ENV:self.folder}))
        with self.assertRaisesRegex(ShadowSafetyError,"SHADOW_SWITCH_INVALID"):
            opt_in_enabled({ENV_NAME:"unreviewed"})

    def test_preflight_requires_specific_proven_artifact_sha(self):
        model=Path(self.folder)/self.pinned["model_filename"]
        manifest=Path(self.folder)/self.pinned["manifest_filename"]
        self.assertTrue(model.is_file())
        self.assertTrue(manifest.is_file())
        self.assertEqual(self.engine.model_sha,self.pinned["model_sha256"])
        with tempfile.TemporaryDirectory() as td:
            badmodel=Path(td)/model.name
            goodmanifest=Path(td)/manifest.name
            badmodel.write_bytes(model.read_bytes()+b"INVALID")
            goodmanifest.write_bytes(manifest.read_bytes())
            with self.assertRaisesRegex(ShadowSafetyError,"BINARY_PIN_MISMATCH"):
                load_opted_shadow(environ={
                    ENV_NAME:"true",MODEL_DIR_ENV:td})
        with self.assertRaisesRegex(ShadowSafetyError,"ARTIFACT_MISSING"):
            load_opted_shadow(environ={
                ENV_NAME:"true",MODEL_DIR_ENV:"/not/a/real/reviewed/artifact"})

    def test_new_m0_legacy_challengers_and_shadow_share_exact_fixture_clock(self):
        original,_,_=make_forecasts(fake_receipts(),cutoff=NOW,
            params=self.params,param_sha=self.params_sha,
            manifest_sha=self.manifest_sha)
        old_rows=[];shadow_rows=[]
        new,_,_=make_forecasts(fake_receipts(),cutoff=NOW,
            params=self.params,param_sha=self.params_sha,
            manifest_sha=self.manifest_sha,
            challenger_engine=self.legacy_engine,challenger_sink=old_rows,
            shadow_engine=self.engine,shadow_sink=shadow_rows,
            wall_clock=self.clock)
        self.assertEqual(len(new),len(original))
        self.assertEqual(len(new),64)
        self.assertEqual(len(old_rows),128)
        self.assertEqual(len(shadow_rows),64)
        self.assertEqual([r["forecast_sha256"] for r in new],
                         [r["forecast_sha256"] for r in original])
        self.assertEqual([r["p_1x2"] for r in new],
                         [r["p_1x2"] for r in original])
        parent={r["forecast_sha256"]:r for r in new}
        for child in shadow_rows:
            original_row=parent[child["source_m0_forecast_sha256"]]
            self.assertEqual(child["feature_sha256"],
                             original_row["feature_sha256"])
            self.assertEqual(child["original_feature_cutoff_utc"],
                             original_row["feature_cutoff_utc"])
            self.assertFalse(child["shadow_host_artifact_verified"])
            self.assertFalse(child["production_approved"])
            self.assertFalse(child["official_fit_eligible"])
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"staging.sqlite"
            new_ids=set()
            n,total=freeze_sqlite(db,new,param_sha=self.params_sha,
                manifest_sha=self.manifest_sha,now=NOW,
                new_frozen_ids=new_ids)
            self.assertEqual((n,total,len(new_ids)),(64,64,64))
            old_stat=freeze_new_challengers(db,old_rows,new_m0_ids=new_ids)
            shadow_stat=freeze_only_new_m0(
                db,shadow_rows,new_m0_ids=new_ids)
            self.assertEqual(old_stat["new_challengers"],128)
            self.assertEqual(shadow_stat["added"],64)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM forecasts").fetchone()[0],64)
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM step17_frozen_challengers").fetchone()[0],128)
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM kb3_p1_shadow_six_new_only").fetchone()[0],64)
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM kb3_p1_shadow_six_new_only "
                    "WHERE model_bytes_sha256=?",
                    (self.pinned["model_sha256"],)).fetchone()[0],64)
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM kb3_p1_shadow_six_new_only s "
                    "JOIN forecasts p ON p.id=s.source_m0_forecast_sha256 "
                    "WHERE s.feature_sha256!=json_extract(p.payload_json,'$.feature_sha256')"
                    ).fetchone()[0],0)
            # Host archive verification reads ORIGINAL zipped SQLite bytes,
            # not merely the locally claimed shadow-generated timestamp.
            buff=io.BytesIO()
            with zipfile.ZipFile(buff,"w",compression=zipfile.ZIP_DEFLATED) as z:
                z.write(db,"data/forward_m0_720_eight/kb3_forward_eight.sqlite")
            old=_archived_shadow(buff.getvalue())
            self.assertEqual(set(old),{
                row["shadow_sha256"] for row in shadow_rows})
            self.assertTrue(all(
                original[3]==self.pinned["model_sha256"]
                for original in old.values()))
            proof_state=audit_shadow(db,token=None,now=NOW+timedelta(days=1))
            self.assertEqual(proof_state["new_host_proofs"],0)
            paired=paired_settled_shadow(db)
            self.assertEqual(paired["paired_settled_host_attested"],0)
            repeated=freeze_only_new_m0(db,shadow_rows,new_m0_ids=set())
            self.assertEqual(repeated["skipped_old_m0"],64)
            self.assertEqual(repeated["added"],0)

    def test_bad_shadow_model_rejected_before_forecast_api(self):
        # The runtime calls the same gate BEFORE calling collect_receipts.
        with self.assertRaisesRegex(ShadowSafetyError,"ARTIFACT_MISSING"):
            load_opted_shadow(environ={
                ENV_NAME:"true",MODEL_DIR_ENV:"/missing/model/not/live"})


if __name__=="__main__":
    unittest.main()
