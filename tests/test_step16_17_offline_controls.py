"""Controlled offline vectors only. No network, GitHub Actions, TEST or DB writes."""
import copy
import math
import unittest
from datetime import datetime, timedelta, timezone
from src.kb3_step16_17_offline_controls import (
    OfflineGateError, score, outcome_from_90min, verify_settlements,
    calibration_100_50, compare_three_by_league, native_xg_last5, ENGINES)

FIT = datetime(2026, 10, 30, 18, tzinfo=timezone.utc)
P = {"1": .6, "X": .3, "2": .1}

def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")

def settlement(i, *, after=False, attested=True):
    ko = FIT + timedelta(days=10+i) if after else FIT-timedelta(days=200-i)
    y = ("1", "X", "2")[i % 3]
    sh, sa = {"1": (2,1), "X":(1,1), "2":(0,2)}[y]
    ll, bs = score(P,y)
    return {"league": "ESP" if i % 2 else "POL",
            "fixture_id": "SYNTHETIC_"+("POST_" if after else "PRE_")+str(i),
            "model_version": "M0_RESEARCH_FIXED",
            "parameter_sha256": "a"*64,
            "host_attested": attested,
            "frozen_at_utc": iso(ko-timedelta(hours=4)),
            "kickoff_utc": iso(ko),
            "result_observed_utc": iso(ko+timedelta(hours=4)),
            "p_1x2": dict(P), "score_home_90": sh, "score_away_90":sa,
            "outcome_1x2": y, "log_loss":ll, "brier_sum3":bs}

def pair(league, i, *, omit=None, modified=None):
    ko = FIT+timedelta(days=i+1)
    freeze=iso(ko-timedelta(hours=4))
    pred={}
    for name in ENGINES:
        if name==omit:continue
        pred[name]={"p_1x2":dict(P),"frozen_at_utc":freeze,
              "feature_sha256":"f"*64,
              "source_m0_forecast_sha256":"m"*64,
              "model_version":name+"_V1",
              "host_attested":True}
    if modified:
        pred[modified[0]][modified[1]]=modified[2]
    return {"league":league,"fixture_id":"SYN_"+league+str(i),
            "kickoff_utc":iso(ko),
            "result_observed_utc":iso(ko+timedelta(hours=4)),
            "outcome_1x2":("1","X","2")[i%3],
            "predictions":pred}

class OfflineControls(unittest.TestCase):
    def test_manual_brier_sum3_and_logloss_are_not_binary_or_divided_by_three(self):
        expected={"1":(.5108256237659907,.26),
                  "X":(1.2039728043259361,.86),
                  "2":(2.302585092994046,1.26)}
        for label,(ll,bs) in expected.items():
            got=score(P,label)
            self.assertAlmostEqual(got[0],ll,12)
            self.assertAlmostEqual(got[1],bs,12)
        self.assertEqual(outcome_from_90min(2,1),"1")
        self.assertEqual(outcome_from_90min(1,1),"X")
        self.assertEqual(outcome_from_90min(0,2),"2")
        with self.assertRaisesRegex(OfflineGateError,"BAD_SIMPLEX"):
            score({"1":.6,"X":.3,"2":.2},"1")
    def test_settlement_cross_checks_90min_label_and_persisted_scores(self):
        a=settlement(0)
        self.assertEqual(len(verify_settlements([a])),1)
        b=copy.deepcopy(a);b["outcome_1x2"]="X"
        with self.assertRaisesRegex(OfflineGateError,"WRONG_1X2"):
            verify_settlements([b])
        b=copy.deepcopy(a);b["brier_sum3"]=b["brier_sum3"]/3
        with self.assertRaisesRegex(OfflineGateError,"BRIER_SUM3_MISMATCH"):
            verify_settlements([b])
        b=copy.deepcopy(a);b["log_loss"]=0.0
        with self.assertRaisesRegex(OfflineGateError,"LOGLOSS_MISMATCH"):
            verify_settlements([b])
        b=copy.deepcopy(a);b["host_attested"]=False
        with self.assertRaisesRegex(OfflineGateError,"EXTERNAL_PROOF"):
            verify_settlements([b])
    def test_calibration_99_100_and_49_50_prospective_only(self):
        pre=[settlement(i) for i in range(100)]
        post=[settlement(i,after=True) for i in range(50)]
        args={"fitted_at_utc":iso(FIT),
              "reviewed_at_utc":iso(FIT+timedelta(days=100)),
              "model_version":"M0_RESEARCH_FIXED","parameter_sha256":"a"*64}
        r=calibration_100_50(pre[:99]+post,**args)
        self.assertFalse(r["ready_to_fit"])
        self.assertFalse(r["ready_to_review"])
        r=calibration_100_50(pre+post[:49],**args)
        self.assertTrue(r["ready_to_fit"])
        self.assertFalse(r["ready_to_review"])
        r=calibration_100_50(pre+post,**args)
        self.assertTrue(r["ready_to_review"])
        self.assertEqual(len(r["fit_first_100"]),100)
        self.assertEqual(len(r["holdout_first_50"]),50)
        self.assertFalse(r["production_approved"])
        contaminated=copy.deepcopy(post[0])
        contaminated["frozen_at_utc"]=iso(FIT-timedelta(days=2))
        r=calibration_100_50(pre+[contaminated]+post[1:],**args)
        self.assertEqual(r["post_fit_independent_n"],49)
        self.assertFalse(r["ready_to_review"])
    def test_calibration_rejects_new_parameter_sha_and_duplicates(self):
        rows=[settlement(0)]
        changed=copy.deepcopy(rows[0]);changed["parameter_sha256"]="b"*64
        with self.assertRaisesRegex(OfflineGateError,"MIXED_MODEL"):
            calibration_100_50([changed],fitted_at_utc=iso(FIT),
              reviewed_at_utc=iso(FIT+timedelta(days=1)),
              model_version="M0_RESEARCH_FIXED",parameter_sha256="a"*64)
        with self.assertRaisesRegex(OfflineGateError,"DUPLICATE_FIXTURE"):
            verify_settlements(rows+rows)
    def test_step17_identical_match_per_league_no_backfill(self):
        data=[pair("ESP",0),pair("ESP",1,omit="CATBOOST_NO_XG"),
              pair("POL",2),pair("POL",3,omit="ELO_ONLY")]
        r=compare_three_by_league(data)
        self.assertEqual(r["matched_three_n"],2)
        self.assertEqual(r["excluded_missing_n"],2)
        self.assertEqual(r["per_league"]["ESP"]["matched_three_n"],1)
        self.assertEqual(r["per_league"]["POL"]["matched_three_n"],1)
        self.assertEqual(r["per_league"]["ESP"]["missing_forecasts"],
                         {"CATBOOST_NO_XG":1})
        self.assertEqual(r["per_league"]["POL"]["per_engine_same_fixtures"]
                         ["ELO_ONLY"]["n"],1)
        self.assertFalse(r["winner_auto_selected"])
    def test_step17_blocks_mixed_cutoff_features_or_fake_proof(self):
        for field,bad,expected in (("frozen_at_utc",iso(FIT),"DIFFERENT_CUTOFF"),
                ("feature_sha256","b"*64,"DIFFERENT_CUTOFF"),
                ("source_m0_forecast_sha256","b"*64,"DIFFERENT_CUTOFF"),
                ("host_attested",False,"ENGINE_NOT_HOST")):
            g=pair("ESP",0,modified=("ELO_ONLY",field,bad))
            with self.assertRaisesRegex(OfflineGateError,expected):
                compare_three_by_league([g])
    def test_xg_actual_last5_missing_not_imputed_and_date_gate(self):
        history=[]; observations={}
        for side in ("HOME","AWAY"):
            for i in range(5):
                ko=FIT-timedelta(days=30-i)
                mid=side+str(i)
                history.append({"fixture_id":mid,"kickoff_utc":iso(ko),
                    "status":"finished","home_team_id":side,
                    "away_team_id":"OPP_"+mid})
                observations[mid]={"provider":"PitchAPI","verified":True,
                    "home_team_id":side,"away_team_id":"OPP_"+mid,
                    "xg_home":0.0 if i==0 else 1.2,"xg_away":0.8,
                    "observed_at_utc":iso(ko+timedelta(hours=4))}
        kw={"target_kickoff_utc":iso(FIT+timedelta(days=2)),
            "cutoff_utc":iso(FIT),"home_team_id":"HOME","away_team_id":"AWAY"}
        r=native_xg_last5(history, observations, **kw)
        self.assertTrue(r["ready_for_xg_research_feature"])
        self.assertAlmostEqual(r["features"]["home"]["xg_for_last5"],.96)
        del observations["HOME3"]
        r=native_xg_last5(history,observations,**kw)
        self.assertFalse(r["ready_for_xg_research_feature"])
        self.assertIsNone(r["features"]["home"]["xg_for_last5"])
        self.assertEqual(r["features"]["home"]["missing_xg_ids"],["HOME3"])
        self.assertTrue(r["no_missing_xg_replaced_with_zero"])
    def test_xg_no_late_source_and_no_other_provider(self):
        ko=FIT-timedelta(days=3)
        h=[{"fixture_id":"match1","kickoff_utc":iso(ko),
            "status":"finished","home_team_id":"HOME","away_team_id":"AWAY"}]
        obs={"match1":{"provider":"FPL/Opta","verified":True,
            "home_team_id":"HOME","away_team_id":"AWAY","xg_home":1,
            "xg_away":1,"observed_at_utc":iso(FIT+timedelta(days=1))}}
        r=native_xg_last5(h,obs,target_kickoff_utc=iso(FIT+timedelta(days=2)),
                          cutoff_utc=iso(FIT),home_team_id="HOME",
                          away_team_id="AWAY")
        self.assertFalse(r["ready_for_xg_research_feature"])
        self.assertIsNone(r["features"]["home"]["xg_for_last5"])

if __name__=="__main__":
    unittest.main()
