import json,sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_three_league_sqlite_forward_features import commit_sqlite
from src.kb3_m0_shadow_1x2_live_freeze import freeze
from src.kb3_m0_live_settlement_calibration import (
    settle,audit_and_prepare_calibration,_source_mapping,ResultSafetyError)
from src.kb3_step14_m1_math_calibration import score_one,score_predictions
from scripts.step14_m0_postmatch_real import verify_original_forecasts,PostmatchRunError
from test_step14_three_league_sqlite_forward_features import fake_capture,season_rows,NOW,stamp
from scripts.step14_three_league_pitchapi_actual_audit import LEAGUES,CURRENT

class SafeRealScoring(unittest.TestCase):
 def prepared(self,t):
    db=Path(t)/"kb3.sqlite";out=Path(t)/"reports"/"2026-10-29"/"FROZEN_M0_SHADOW_1X2.json"
    commit_sqlite(db,fake_capture(),cutoff_utc=stamp(NOW),
          raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
    freeze(db,report_path=out,now=datetime.now(timezone.utc))
    return db,out
 def provider(self):
    result={}
    for c,names,n,title in LEAGUES:
        matches=season_rows(c,n,2026)
        # Do not forge any fixture result after the observed clock.
        result[c]=({"origin":"NETWORK_OBSERVED",
                   "resource":"pitchapi:postmatch:"+c+":"+CURRENT,
                   "completed_at_utc":stamp(datetime.now(timezone.utc)),
                   "payload_sha256":"a"*64},matches)
    return result
 def test_all_12_future_games_are_unsettled_before_actual_matches(self):
    with tempfile.TemporaryDirectory() as t:
        db,out=self.prepared(t)
        report=settle(db,self.provider(),now=datetime.now(timezone.utc)+timedelta(seconds=1))
        self.assertEqual(report["newly_settled"],0)
        self.assertEqual(report["total_settled"],0)
        self.assertEqual(report["pending_unsettled"],12)
        self.assertEqual(report["skipped_reason_counts"]["TOO_EARLY"],12)
        with sqlite3.connect(db) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM m0_shadow_1x2_settlements").fetchone()[0],0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],0)
 def test_100_50_thresholds_cannot_fit_from_empty(self):
    with tempfile.TemporaryDirectory() as t:
        db,out=self.prepared(t)
        audit=audit_and_prepare_calibration(db,now=datetime.now(timezone.utc))
        self.assertEqual(audit["scored_independent_matches"],0)
        self.assertEqual(audit["temperature_fit_minimum"],100)
        self.assertEqual(audit["future_holdout_minimum"],50)
        self.assertIsNone(audit["new_calibration_candidate"])
        self.assertIsNone(audit["new_holdout_review"])
        self.assertFalse(audit["production_calibration_activated"])
 def test_no_external_false_frozen_proof(self):
    with tempfile.TemporaryDirectory() as t:
        db,out=self.prepared(t)
        valid=verify_original_forecasts(db,Path(t)/"reports")
        self.assertEqual(valid["independently_existing_repo_forecast_hashes"],12)
        self.assertFalse(valid["server_first_publication_utc_independently_proven"])
        r=json.loads(out.read_text());r["individual_forecasts"][0]["p_1x2"]["1"]=0.99
        out.write_text(json.dumps(r))
        with self.assertRaisesRegex(PostmatchRunError,"HASH_TAMPERED"):
            verify_original_forecasts(db,Path(t)/"reports")
 def test_only_exact_three_leagues_can_be_settled(self):
    prov=self.provider();del prov["ESP"]
    with self.assertRaisesRegex(ResultSafetyError,"EXACT_THREE"):
        _source_mapping(prov,datetime.now(timezone.utc)+timedelta(seconds=2))
 def test_computed_scores_math_realistic(self):
    p={"1":0.6,"X":0.25,"2":0.15}
    ll,brier=score_one(p,"X")
    self.assertAlmostEqual(ll,1.38629436112,places=8)
    self.assertAlmostEqual(brier,0.945,places=8)
    aggregate=score_predictions([p],["X"])
    self.assertAlmostEqual(aggregate["log_loss"],ll)
    self.assertAlmostEqual(aggregate["brier_sum3"],brier)
 def test_unsafe_fake_provider_observation_fails(self):
    prov=self.provider();src,items=prov["GER"];src["origin"]="REPLAY"
    with self.assertRaisesRegex(ResultSafetyError,"NETWORK_OBSERVED"):
        _source_mapping(prov,datetime.now(timezone.utc)+timedelta(seconds=3))
 def test_unsafe_status_goals_never_enter_settlement(self):
    with tempfile.TemporaryDirectory() as t:
        db,out=self.prepared(t)
        r=self.provider()
        # A post-match claim on an upcoming fixture must not be ingested
        # ahead of the true current server time.
        for country,(source,matches) in r.items():
            for item in matches:
                if item["status"]=="scheduled":
                    item["status"]="finished";item["score_home"]=5;item["score_away"]=0
        settled=settle(db,r,now=datetime.now(timezone.utc)+timedelta(seconds=2))
        self.assertEqual(settled["total_settled"],0)
 def test_missing_model_forecast_can_never_be_created_from_zero(self):
    with tempfile.TemporaryDirectory() as t:
        db=Path(t)/"blank.sqlite"
        with self.assertRaises((sqlite3.OperationalError,FileNotFoundError,ValueError)):
            settle(db,self.provider(),now=datetime.now(timezone.utc)+timedelta(seconds=1))
if __name__=="__main__":unittest.main()
