"""Step14 A/B negative tests. No paid API, no TEST, no product promotion."""
import copy
from datetime import date,timedelta,datetime,timezone
import unittest
from src.kb3_step14_public_research import (
    ResearchSafetyError,load_results,lagged_features,_prob_metrics,run_research,
    SEASONS,POLICY
)
from src.kb3_step14_archive_probe import ArchiveProbeError,validate_roster,scan
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def fake_source():
    teams=[f"CLUB_{i:02d}" for i in range(20)]
    answer={}
    for season in SEASONS:
        sy=int(season[:4])
        matches=[]
        idx=0
        for i in range(20):
            for j in range(20):
                if i==j: continue
                day=date(sy,8,1)+timedelta(days=idx//2)
                gh=(i*7+j)%4
                ga=(j*3+i)%3
                matches.append({"date":day.isoformat(),
                  "team1":teams[i],"team2":teams[j],"score":{"ft":[gh,ga]}})
                idx+=1
        answer[season]={"matches":matches}
    return answer


class RetrospectiveM1Tests(unittest.TestCase):
    def test_exact_three_seasons_760_380(self):
        rs=load_results(fake_source())
        self.assertEqual(len(rs),1140)
        self.assertEqual(len([r for r in rs if r[1]!="2025-26"]),760)
        self.assertEqual(len([r for r in rs if r[1]=="2025-26"]),380)

    def test_target_result_cannot_change_own_features(self):
        a=fake_source()
        base=lagged_features(load_results(a))
        b=copy.deepcopy(a)
        b["2023-24"]["matches"][0]["score"]["ft"]=[12,2]
        alt=lagged_features(load_results(b))
        target=date(2023,8,1).isoformat()
        va=sorted([r["feature_vector"] for r in base if r["date"]==target])
        vb=sorted([r["feature_vector"] for r in alt if r["date"]==target])
        self.assertEqual(va,vb)

    def test_future_season_not_accepted(self):
        a=fake_source()
        a["2026-27"]=a["2025-26"]
        with self.assertRaisesRegex(ResearchSafetyError,"TEST_DENIED"):
            load_results(a)

    def test_odds_field_never_part_of_features(self):
        a=fake_source()
        a["2023-24"]["matches"][0]["B365H"]=1.25
        rows=lagged_features(load_results(a))
        self.assertTrue(all(len(r["feature_vector"])==5 for r in rows))
        self.assertFalse(any("odds" in str(k).lower() for k in rows[0].keys()))

    def test_invalid_missing_scores_refused(self):
        a=fake_source();a["2025-26"]["matches"][0]["score"]={}
        with self.assertRaisesRegex(ResearchSafetyError,"INVALID_FT"):
            load_results(a)

    def test_real_research_catboost_not_production(self):
        try: import catboost
        except ImportError: self.skipTest("catboost optional in local env")
        out=run_research(fake_source(),{s:"synthetic-test-fixture" for s in SEASONS})
        self.assertEqual((out["train_rows"],out["validation_rows"]),(760,380))
        self.assertEqual(out["research_only_policy"],POLICY)
        self.assertFalse(out["official_step12_train_eligibility_changed"])
        self.assertFalse(out["gate14_pass"])
        self.assertFalse(out["real_historical_pit_proven"])
        self.assertFalse(out["production_approved"])
        self.assertEqual(out["test_rows_read"],0)
        self.assertTrue(out["catboost_research_validation"]["log_loss"]>0)

    def test_probabilities_normalized(self):
        q=_prob_metrics([[.5,.2,.3]],["1"])
        self.assertLess(q["log_loss"],1)
        with self.assertRaisesRegex(ResearchSafetyError,"INVALID_P_1X2"):
            _prob_metrics([[.5,.2,.6]],["1"])


class ArchivePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.safe=json.loads((ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
        cls.roster=json.loads((ROOT/"data/research/STEP14_PIT_PILOT_40_TRAIN_20_VALIDATION_2026-10-27.json").read_text())

    def test_sample_40_20_target_free(self):
        a=validate_roster(self.roster,self.safe)
        self.assertEqual((len([r for r in a if r["partition"]=="TRAIN"]),
                          len([r for r in a if r["partition"]=="VALIDATION"])),(40,20))
        self.assertFalse(any(r["partition"]=="TEST" for r in a))

    def test_test_role_injection_blocked(self):
        p=copy.deepcopy(self.roster)
        p["fixtures"][0]["partition"]="TEST"
        with self.assertRaises(ArchiveProbeError):
            validate_roster(p,self.safe)

    def test_commits_preliminary_not_certified(self):
        from src.kb3_step14_archive_probe import _utc
        metadata={s:[] for s in ("2023-24","2024-25","2025-26")}
        metadata["2024-25"]=[(_utc("2024-08-01T00:00:00Z"),"a"*40)]
        res=scan(self.roster,self.safe,metadata)
        self.assertEqual(res["sample_count"],60)
        self.assertEqual(res["eligible_real_train_rows"],0)
        self.assertEqual(res["independently_pit_certified_rows"],0)
        self.assertFalse(res["gate14_pass"])
        self.assertGreaterEqual(res["total_commit_date_candidates"],1)


if __name__=="__main__":
    unittest.main()
