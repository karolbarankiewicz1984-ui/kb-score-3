"""V3-R genuine forward-only freeze safety, without provider or trained models."""
import tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
from scripts.kb3_v3r_forward_shadow import (
    record_for,source_observations,verified_m0_candidates,
    V3RShadowSafety,when,MODEL_VERSION,CONTRACT,
)
from src.kb3_step16_m0_720_eight_forward import hashobj
from scripts.kb3_v3r_forward_shadow import BASE
import sqlite3

NOW=datetime(2026,11,16,13,tzinfo=timezone.utc)
KO="2026-11-22T18:00:00Z"

def ts(t):return t.isoformat().replace("+00:00","Z")

class PredictStub:
    classes_=["1","X","2"]
    def predict_proba(self,x):
        assert len(x)==1 and len(x[0])==14
        return [[0.50,0.20,0.30]]

def scenario():
    target={"league":"ESP","mid":"m_abc123","kickoff_utc":KO,
            "home_team_id":"t_A","away_team_id":"t_B",
            "id":"a"*64,"m0_at":"2026-11-15T10:00:00Z"}
    native={"id":"m_abc123","time_utc":KO,"status":"scheduled",
            "home_team":{"id":"t_A"},"away_team":{"id":"t_B"},
            "score_home":None,"score_away":None}
    fixture=[]
    for i in range(5):
        ko=ts(datetime(2026,10,28,tzinfo=timezone.utc)+timedelta(days=i))
        fixture.append({"scope":"ESP","match_id":"m_g"+str(i),
            "kickoff_utc":ko,"home_team_id":"t_A","away_team_id":"t_B",
            "goals_home_90":i%3,"goals_away_90":(i+1)%3})
    return target,{"m_abc123":native},fixture


class V3RForwardSafetyTests(unittest.TestCase):
    def test_missing_optional_stats_are_nan_and_do_not_stop_prediction(self):
        target,listing,history=scenario()
        r,err=record_for(target,history=history,listing=listing,
                observations={},model=PredictStub(),
                manifest={"binary_sha256":"b"*64,"manifest_sha256":"c"*64},
                at=NOW,source_chain_sha="d"*64)
        self.assertIsNone(err)
        self.assertEqual(r["p_1x2"],{"1":.5,"X":.2,"2":.3})
        self.assertFalse(r["full_14_feature_coverage"])
        self.assertIn("home_fouls",r["missing_optional_features"])
        self.assertEqual(r["missing_value_policy"],"NAN_NOT_ZERO_AND_RETRY")
        self.assertTrue(r["complete_lastfive_history"])
        self.assertTrue(r["independent_host_publication_proof_pending"])
        self.assertFalse(r["production_approved"])
        self.assertEqual(r["model_version"],MODEL_VERSION)
        self.assertEqual(r["schema"],CONTRACT)
        self.assertEqual(r["feature_names"],list(BASE))

    def test_insufficient_true_lastfive_is_nonblocking_m0_fallback(self):
        t,l,h=scenario()
        result,reason=record_for(t,history=h[:4],listing=l,observations={},
                  model=PredictStub(),manifest={"binary_sha256":"x",
                  "manifest_sha256":"y"},at=NOW,source_chain_sha="q"*64)
        self.assertIsNone(result)
        self.assertEqual(reason,"M0_FALLBACK_MISSING_TRUE_HISTORY5")

    def test_provider_identity_drift_quarantines_only_that_target(self):
        t,l,h=scenario()
        l["m_abc123"]["away_team"]["id"]="t_WRONG"
        result,reason=record_for(t,history=h,listing=l,observations={},
                  model=PredictStub(),manifest={"binary_sha256":"x",
                  "manifest_sha256":"y"},at=NOW,source_chain_sha="q"*64)
        self.assertIsNone(result)
        self.assertEqual(reason,"PARENT_PROVIDER_TARGET_IDENTITY_DRIFT")

    def test_unproven_postcapture_stats_are_rejected(self):
        t,l,h=scenario()
        row=h[0]
        obs={("ESP",row["match_id"]):{"home_team_id":"t_A",
            "away_team_id":"t_B","kickoff_utc":row["kickoff_utc"],
            "source_observed_at_utc":"2026-11-17T00:00:00Z",
            "items":[],"xg_status":"MISSING","xg_home":None,
            "xg_away":None}}
        with self.assertRaisesRegex(V3RShadowSafety,"POST_FORECAST"):
            record_for(t,history=h,listing=l,observations=obs,
                       model=PredictStub(),manifest={},at=NOW,
                       source_chain_sha="x"*64)

    def test_original_m0_parent_hash_and_deadline_protect_new_records(self):
        t,l,h=scenario()
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"m0.sqlite"
            with sqlite3.connect(db) as cn:
                cn.execute("""CREATE TABLE forecasts(id TEXT,league TEXT,
                  native_match_id TEXT,kickoff_utc TEXT,captured_at_utc TEXT,
                  home_team_id TEXT,away_team_id TEXT,payload_json TEXT)""")
                p={"model_version":"M0","provider_match_id":t["mid"],
                    "league_country":"ESP","kickoff_utc":KO,
                    "home_team_id":"t_A","away_team_id":"t_B"}
                p["forecast_sha256"]=hashobj(p)
                cn.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                           (p["forecast_sha256"],"ESP",t["mid"],KO,
                            "2026-11-15T10:00:00Z","t_A","t_B",
                            json.dumps(p)))
            records,reasons=verified_m0_candidates(
                db_path=db,now=NOW,out_root=Path(d)/"v3r")
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]["id"],p["forecast_sha256"])
            later=datetime(2026,11,22,17,tzinfo=timezone.utc)
            too_late,_=verified_m0_candidates(
                db_path=db,now=later,out_root=Path(d)/"v3r")
            self.assertEqual(too_late,[])

    def test_m0_does_not_accept_corrupt_parent_sha(self):
        t,l,h=scenario()
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"m0.sqlite"
            with sqlite3.connect(db) as cn:
                cn.execute("""CREATE TABLE forecasts(id TEXT,league TEXT,
                  native_match_id TEXT,kickoff_utc TEXT,captured_at_utc TEXT,
                  home_team_id TEXT,away_team_id TEXT,payload_json TEXT)""")
                cn.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                           ("f"*64,"ESP",t["mid"],KO,
                            "2026-11-15T10:00:00Z","t_A","t_B",
                            json.dumps({"forecast_sha256":"f"*64})))
            with self.assertRaisesRegex(V3RShadowSafety,"M0_FROZEN_PARENT"):
                verified_m0_candidates(db_path=db,now=NOW,
                                        out_root=Path(d)/"v3r")

if __name__=="__main__":
    unittest.main()
