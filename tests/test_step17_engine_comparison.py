"""Deterministic Step17 fairness diagnostics only; no TEST, API, CatBoost fit."""
import copy,math,unittest
from datetime import datetime,timedelta,timezone
from src.kb3_step17_engine_comparison import (
    ENGINES,Step17Error,compare,check_payload,paired_ci,MIN_BLOCKS)

BASE=datetime(2026,11,1,12,tzinfo=timezone.utc)
def iso(x):return x.isoformat().replace("+00:00","Z")
def manifest(*,domain="FORWARD_GITHUB_HOST_ATTESTED",weeks=12,mode="only_two"):
    versions={e:e+"_SHA_SAMPLE_VERSION_123" for e in ENGINES}
    rows=[]
    for i in range(weeks):
        ko=BASE+timedelta(days=i*7)
        pred={}
        selected=ENGINES if mode=="five" else (ENGINES[1],ENGINES[2])
        for j,e in enumerate(selected):
            p={"1":0.49-j*.02,"X":0.27,"2":0.24+j*.02}
            pred[e]={"p_1x2":p,"frozen_at_utc":iso(ko-timedelta(hours=4)),
              "model_version":versions[e],"horizon":"EARLY_90MIN_OR_MORE",
              "source_class":"B_RECONSTRUCTED",
              "github_server_artifact_verified":True,
              "forecast_hash_verified":True}
        rows.append({"fixture_id":"synthetic_"+str(i),"league":"ESP",
                     "kickoff_utc":iso(ko),
                     "result_observed_utc":iso(ko+timedelta(hours=4)),
                     "outcome_1x2":("1","X","2")[i%3],
                     "predictions":pred})
    return {"schema":"kb3-step17-paired-engine-input-v1",
            "evaluation_domain":domain,
            "market":"1X2_90MIN",
            "horizon":"EARLY_90MIN_OR_MORE",
            "candidate_versions":versions,
            "protected_test_opened":False,"games":rows}

class Gate17PreparatoryTests(unittest.TestCase):
 def test_pairwise_common_same_games_and_cost_of_missing(self):
    p=manifest()
    result=compare(p,replicates=200)
    self.assertEqual(result["unique_fixtures"],12)
    self.assertEqual(result["full_five_common_fixtures"],0)
    self.assertEqual(result["missing_data_cost"]["M0_ELO_POISSON_720TRAIN"]["available_unique"],12)
    self.assertEqual(result["missing_data_cost"]["CATBOOST_WITH_XG"]["missing_unique"],12)
    pair=result["fair_same_game_pairwise"]["M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"]
    self.assertEqual(pair["common_n"],12)
    self.assertEqual(pair["deltas"]["log_loss"]["week_blocks"],12)
    self.assertEqual(len(pair["deltas"]["log_loss"]["ci95"]),2)
    self.assertFalse(result["enough_for_formal_step17"])
    self.assertFalse(result["winner_auto_selected"])
 def test_all_five_full_common_and_not_auto_champion(self):
    r=compare(manifest(mode="five"),replicates=200)
    self.assertEqual(r["full_five_common_fixtures"],12)
    self.assertEqual(len(r["all_five_common_scores"]),5)
    self.assertTrue(all(x["n"]==12 for x in r["all_five_common_scores"].values()))
    self.assertFalse(r["enough_for_formal_step17"])
 def test_missing_pair_is_not_invented(self):
    p=manifest()
    for g in p["games"][:5]:del g["predictions"]["CATBOOST_NO_XG"]
    r=compare(p,replicates=200)
    self.assertEqual(r["fair_same_game_pairwise"]["M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"]["common_n"],7)
    self.assertEqual(r["missing_data_cost"]["CATBOOST_NO_XG"]["missing_unique"],5)
    d=r["fair_same_game_pairwise"]["M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"]["deltas"]["brier_sum3"]
    self.assertEqual(d["status"],"INSUFFICIENT_INDEPENDENT_WEEKS")
    self.assertIsNone(d["ci95"])
 def test_reject_unattested_forward_and_late_forecast(self):
    p=manifest()
    p["games"][0]["predictions"]["M0_ELO_POISSON_720TRAIN"]["github_server_artifact_verified"]=False
    with self.assertRaisesRegex(Step17Error,"EXTERNAL_ATTESTATION"):
        compare(p,replicates=200)
    p=manifest()
    x=p["games"][0]
    x["predictions"]["M0_ELO_POISSON_720TRAIN"]["frozen_at_utc"]=iso(BASE-timedelta(minutes=20))
    with self.assertRaisesRegex(Step17Error,"LATE_PREDICTION"):
        compare(p,replicates=200)
 def test_reject_other_league_protected_future_and_leakage(self):
    p=manifest()
    p["games"][0]["league"]="ENG_HISTORICAL"
    with self.assertRaisesRegex(Step17Error,"PROTECTED_ENGLISH_TEST"):
        compare(p,replicates=200)
    p=manifest()
    p["games"][0]["result_observed_utc"]=p["games"][0]["kickoff_utc"]
    with self.assertRaisesRegex(Step17Error,"RESULT_NOT_POSTMATCH"):
        compare(p,replicates=200)
    p=manifest()
    p["games"].append(copy.deepcopy(p["games"][0]))
    with self.assertRaisesRegex(Step17Error,"DUPLICATE_FIXTURE"):
        compare(p,replicates=200)
 def test_model_sha_and_horizon_invariant(self):
    p=manifest()
    p["games"][0]["predictions"]["CATBOOST_NO_XG"]["model_version"]="MISMATCH"
    with self.assertRaisesRegex(Step17Error,"MIXED_MODEL_VERSIONS"):
        compare(p,replicates=200)
    p=manifest()
    p["games"][0]["predictions"]["CATBOOST_NO_XG"]["horizon"]="FINAL"
    with self.assertRaisesRegex(Step17Error,"MISMATCHED_PREMATCH_HORIZON"):
        compare(p,replicates=200)
 def test_historical_explicitly_marked_and_never_production(self):
    p=manifest(domain="HISTORICAL_RECONSTRUCTED_RESEARCH")
    r=compare(p,replicates=200)
    self.assertTrue(r["research_historical_not_forward_certified"])
    self.assertFalse(r["winner_auto_selected"])
    self.assertFalse(r["production_model_changed"])
    self.assertFalse(r["sealed_test_accessed"])
 def test_week_block_ci_is_deterministic(self):
    p=manifest()
    a=compare(p,replicates=200)
    b=compare(p,replicates=200)
    key="M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"
    self.assertEqual(a["fair_same_game_pairwise"][key]["deltas"],b["fair_same_game_pairwise"][key]["deltas"])
if __name__=="__main__":unittest.main()
