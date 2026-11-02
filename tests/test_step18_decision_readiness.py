import copy
import unittest
from src.kb3_step18_decision_readiness import evaluate, Gate18Error

ELO="ELO_ONLY__vs__M0_ELO_POISSON_720TRAIN"
CAT="M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"

def pair(n=120,delta=(0.01,0.04),weeks=10):
    return {"common_n":n,"deltas":{
        k:{"n":n,"week_blocks":weeks,
           "status":"PAIRED_ISO_WEEK_BOOTSTRAP" if weeks>=8 else "INSUFFICIENT_INDEPENDENT_WEEKS",
           "ci95":list(delta) if weeks>=8 else None}
        for k in ("brier_sum3","log_loss")}}

def valid_report():
    pairs={ELO:pair(delta=(-0.04,-0.01)),CAT:pair(delta=(0.01,0.04))}
    return {"schema":"kb3-step17-offline-three-engine-readonly-v1",
      "source_db_unchanged":True,"no_provider_calls":True,
      "no_new_forecasts_or_backfill":True,"protected_test_accessed":False,
      "winner_auto_selected":False,"gate17":"PENDING","performance_claim_allowed":False,
      "source_m0_sha256":"a"*64,
      "pairwise_evaluation":pairs,
      "pairwise_common_n":{k:v["common_n"] for k,v in pairs.items()}}

class Step18Tests(unittest.TestCase):
    def test_research_signal_does_not_approve_champion(self):
        x=evaluate(valid_report())
        self.assertTrue(x["candidate_diagnostics"]["ELO_ONLY"]["research_statistical_signal_only"])
        self.assertTrue(x["candidate_diagnostics"]["CATBOOST_NO_XG"]["research_statistical_signal_only"])
        self.assertFalse(x["ready_for_human_champion_decision"])
        self.assertFalse(x["candidate_deployment_authorized"])
        self.assertFalse(x["winner_chosen"])
        self.assertEqual(x["formal_step18"],"PENDING_16_17_AND_OWNER_APPROVAL")
    def test_empty_and_small_pairs_remain_pending(self):
        v=valid_report()
        for k in (ELO,CAT):
            v["pairwise_evaluation"][k]={"common_n":0,"deltas":{}}
            v["pairwise_common_n"][k]=0
        x=evaluate(v)
        self.assertFalse(x["candidate_diagnostics"]["CATBOOST_NO_XG"]["research_statistical_signal_only"])
        v=valid_report()
        for k in (ELO,CAT):
            v["pairwise_evaluation"][k]=pair(n=42)
            v["pairwise_common_n"][k]=42
        x=evaluate(v)
        self.assertIn("NOT_ENOUGH_PAIRED_GAMES",x["candidate_diagnostics"]["CATBOOST_NO_XG"]["blocked_reasons"])
    def test_few_weeks_and_ci_crossing_zero_block(self):
        v=valid_report()
        v["pairwise_evaluation"][CAT]=pair(weeks=3)
        x=evaluate(v)
        self.assertIn("TOO_FEW_INDEPENDENT_WEEKS",x["candidate_diagnostics"]["CATBOOST_NO_XG"]["blocked_reasons"])
        v=valid_report()
        v["pairwise_evaluation"][CAT]=pair(delta=(-0.02,0.01))
        x=evaluate(v)
        self.assertFalse(x["candidate_diagnostics"]["CATBOOST_NO_XG"]["research_statistical_signal_only"])
    def test_missing_source_provenance_fails_closed(self):
        v=valid_report()
        for key,value in (("no_provider_calls",False),("protected_test_accessed",True),
                          ("winner_auto_selected",True),("performance_claim_allowed",True)):
            x=copy.deepcopy(v);x[key]=value
            with self.assertRaises(Gate18Error): evaluate(x)
    def test_mismatched_sample_rejected(self):
        v=valid_report();v["pairwise_common_n"][CAT]=121
        with self.assertRaisesRegex(Gate18Error,"PAIRWISE_COUNT_DRIFT"):evaluate(v)

if __name__=="__main__":unittest.main()
