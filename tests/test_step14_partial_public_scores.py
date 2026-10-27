"""Partial public historical result-asof evidence; no original M1 training."""
import copy,json
from pathlib import Path
import unittest
from src.kb3_step14_partial_public_scores import (
    analyse,_scores_before_push,PartialEvidenceError
)

ROOT=Path(__file__).resolve().parents[1]
BLOB=json.loads((ROOT/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json").read_text())
CLOCK=json.loads((ROOT/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json").read_text())

def fake_docs():
    a=[]
    a.append({"date":"2024-10-05","time":"17:30","team1":"Everton FC",
              "team2":"Newcastle United FC","score":None})
    for i in range(60):
        h="Everton FC" if i<6 else "Newcastle United FC" if i<12 else f"Team H {i}"
        a.append({"date":"2024-09-01","team1":h,"team2":f"Team Away {i}",
                  "score":{"ft":[i%4,i%3]}})
    for i in range(319):
        a.append({"date":"2025-01-01","team1":f"Test H{i}","team2":f"Test A{i}","score":None})
    assert len(a)==380
    b=[
      {"date":"2025-08-18","team1":"Leeds United","team2":"Everton FC","score":None},
      {"date":"2025-08-31","team1":"Liverpool FC","team2":"Arsenal FC","score":None},
    ]
    b.extend({"date":"2025-08-01","team1":f"B H{i}","team2":f"B A{i}","score":None} for i in range(378))
    return {"2024-25":{"matches":a},"2025-26":{"matches":b}}


class PartialAsOfProofTests(unittest.TestCase):
    def test_old_public_blob_has_full_previous_scores_asof_public_push(self):
        out=analyse(fake_docs(),BLOB,CLOCK)
        self.assertEqual(out["historical_public_push_2024_10_02_fully_finished_results"],60)
        self.assertEqual(out["historical_public_push_2025_07_30_fully_finished_results"],0)
        record=next(r for r in out["records"] if r["fixture_id"]=="m_3AMymS")
        self.assertEqual(record["completed_predecessor_results_for_home_in_pushed_blob"],6)
        self.assertEqual(record["completed_predecessor_results_for_away_in_pushed_blob"],6)
        self.assertTrue(record["public_within_season_last5_goal_form_inputs_reconstructable"])
        self.assertFalse(record["prematch_native_PitchAPI_form5_certified"])
        self.assertFalse(out["gate14_pass"])

    def test_stale_public_fixture_cannot_be_matching_pitchapi_identity(self):
        out=analyse(fake_docs(),BLOB,CLOCK)
        r=next(q for q in out["records"] if q["fixture_id"]=="m_0JJdwI")
        self.assertFalse(r["public_july_source_contains_actual_native_pair"])
        self.assertFalse(r["official_m1_training_allowed"])

    def test_public_source_target_score_cannot_be_in_pre_match_blob(self):
        d=fake_docs();d["2024-25"]["matches"][0]["score"]={"ft":[2,1]}
        with self.assertRaisesRegex(PartialEvidenceError,"TARGET_SCORE_ALREADY"):
            analyse(d,BLOB,CLOCK)

    def test_pushed_blob_with_future_score_is_refused(self):
        d=fake_docs();d["2024-25"]["matches"][1]["date"]="2024-10-08"
        with self.assertRaisesRegex(PartialEvidenceError,"RESULT_DATE_AT_OR_AFTER"):
            analyse(d,BLOB,CLOCK)

    def test_no_independent_GH_server_clock_is_refused(self):
        c=copy.deepcopy(CLOCK)
        for r in c["records"]:r["independent_public_push_time_corroborated"]=False
        with self.assertRaisesRegex(PartialEvidenceError,"GH_ARCHIVE_PUSH_PROOF"):
            analyse(fake_docs(),BLOB,c)

    def test_no_old_archive_match_is_refused(self):
        b=copy.deepcopy(BLOB)
        t=next(q for q in b["records"] if q["pitch_fixture_id"]=="m_3AMymS")
        t["candidate_commit_sha"]="f"*40
        with self.assertRaisesRegex(PartialEvidenceError,"TARGET_HISTORIC_COMMIT"):
            analyse(fake_docs(),b,CLOCK)

    def test_no_target_results_exported(self):
        a=analyse(fake_docs(),BLOB,CLOCK)
        for r in a["records"]:
            self.assertNotIn("score_home",str(r))
            self.assertNotIn("score_away",str(r))
        self.assertFalse(a["target_match_scores_exported_or_used"])
        self.assertEqual(a["official_M1_train_eligible"],0)

if __name__=="__main__":unittest.main()
