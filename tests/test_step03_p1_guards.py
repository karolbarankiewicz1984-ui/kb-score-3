"""P1-01/P1-02 fail-closed controls, no API, no fit, no model mutation."""
import ast, inspect, sqlite3, unittest
from datetime import datetime, timezone
from src.kb3_m0_shadow_settlement import review_calibration
from src.kb3_m0_live_settlement_calibration import audit_and_prepare_calibration
from src.kb3_step18_decision_readiness import evaluate

class P1Guards(unittest.TestCase):
    def test_100_synthetic_shadow_settlements_never_fit(self):
        db=sqlite3.connect(":memory:")
        db.executescript("""
          CREATE TABLE m0_shadow_settlements(
            forecast_id TEXT, result_1x2 TEXT, settled_at_utc TEXT);
          CREATE TABLE m0_shadow_1x2_forecasts(
            forecast_id TEXT, kickoff_utc TEXT, generated_at_utc TEXT,
            model_version_id TEXT, parameter_sha256 TEXT,
            p_1 REAL, p_x REAL, p_2 REAL);
        """)
        for i in range(100):
            fid=f"fixture-{i:03d}"
            db.execute("INSERT INTO m0_shadow_1x2_forecasts VALUES(?,?,?,?,?,?,?,?)",
                       (fid,"2026-10-05T10:00:00Z","2026-10-04T08:00:00Z",
                        "M0_TEST","a"*64,0.5,0.3,0.2))
            db.execute("INSERT INTO m0_shadow_settlements VALUES(?,?,?)",
                       (fid,"1","2026-10-05T13:00:00Z"))
        with db:
            answer=review_calibration(db,now=datetime(2026,11,4,tzinfo=timezone.utc))
        self.assertEqual(answer[0]["state"],"BLOCKED_UNATTESTED_HOST_PUBLICATION")
        self.assertIsNone(answer[0]["candidate_temperature"])
        self.assertEqual(answer[0]["fit_eligible_proofs"],0)

    def test_legacy_persistent_calibrator_has_no_fit_call_path(self):
        body=inspect.getsource(audit_and_prepare_calibration)
        calls=[n.func.id for n in ast.walk(ast.parse(body))
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertNotIn("fit_temperature",calls)
        self.assertIn("BLOCKED_LEGACY_NO_INDEPENDENT_HOST_PROOF",body)

    def test_train_forward_mismatch_fails_step18_candidate_signal(self):
        key1="ELO_ONLY__vs__M0_ELO_POISSON_720TRAIN"
        key2="M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"
        def pair():
            return {"common_n":120,"deltas":{m:{"n":120,"week_blocks":10,"ci95":[0.01,0.04]}
                    for m in ("brier_sum3","log_loss")}}
        report={"schema":"kb3-step17-offline-three-engine-readonly-v1",
           "source_db_unchanged":True,"no_provider_calls":True,
           "no_new_forecasts_or_backfill":True,"protected_test_accessed":False,
           "winner_auto_selected":False,"gate17":"PENDING",
           "performance_claim_allowed":False,"source_m0_sha256":"a"*64,
           "pairwise_evaluation":{key1:pair(),key2:pair()},
           "pairwise_common_n":{key1:120,key2:120}}
        result=evaluate(report)
        cat=result["candidate_diagnostics"]["CATBOOST_NO_XG"]
        self.assertIn("P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS",cat["blocked_reasons"])
        self.assertFalse(cat["research_statistical_signal_only"])
        self.assertFalse(cat["eligible_for_champion_automatic_promotion"])

if __name__=="__main__":unittest.main()
