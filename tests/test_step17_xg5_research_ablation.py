"""Offline safety tests for actual research-only chronological CatBoost xG5 ablation."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from scripts.step17_xg5_research_ablation import (
    build_example, chronological_split, load_examples, run, score,
    ResearchSafetyError, MIN_TOTAL,
)
from src.kb3_historical_feature_quality import FEATURE_VERSION

START=datetime(2025,1,2,tzinfo=timezone.utc)

def kickoff(i):
    return (START+timedelta(days=i)).isoformat().replace("+00:00","Z")

def example(i,scope="BEL"):
    ko=kickoff(i)
    base=[float(i%6+1)]*14
    return {"scope":scope,"season":"2024/2025",
            "match_id":"m_"+str(i).zfill(6),"kickoff_utc":ko,
            "base":base,"with_xg":base+[1.2,.8,1.1,.9],
            "y":("1","X","2")[i%3]}

def sample_feature(mid="m_000001",i=1,scope="BEL",xg_ok=True):
    metrics={}
    for key in ("goals_for","goals_against","points","xg_for","xg_against",
                "total_shots","fouls","corners","yellow_cards"):
        val=1.2 if key.startswith("xg_") else 2.0
        metrics[key]={"valid_n":5 if xg_ok or not key.startswith("xg_") else 4,
                      "complete":xg_ok or not key.startswith("xg_"),
                      "mean":val if xg_ok or not key.startswith("xg_") else None}
    window={"requested_n":5,"actual_predecessors":5,"history_complete":True,
            "xg_complete":xg_ok,"metrics":metrics}
    return {"schema":FEATURE_VERSION,"source":"PitchAPI",
            "availability_class":"HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
            "original_pit_certified":False,"training_approved":False,
            "actual_source_first_published_at_known":False,
            "scope":scope,"target_match_id":mid,"target_kickoff_utc":kickoff(i),
            "sides":{"home":{"all":{"5":window}},
                     "away":{"all":{"5":window}}}}

def fixture(mid="m_000001",i=1,scope="BEL"):
    return {"scope":scope,"season":"2024/2025",
            "match_id":mid,"kickoff_utc":kickoff(i),
            "goals_home_90":2,"goals_away_90":1}

def seed_db(path,fixtures=3,scope="BEL",include_ENG=False):
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE finished_fixture_index(
        scope TEXT,season TEXT,match_id TEXT,kickoff_utc TEXT,
        goals_home_90 INTEGER,goals_away_90 INTEGER);
        CREATE TABLE observations(scope TEXT,match_id TEXT);
        CREATE TABLE rolling_feature_cache(
        scope TEXT,target_match_id TEXT,target_kickoff_utc TEXT,
        feature_json TEXT,research_only INTEGER,
        provider_original_pit_certified INTEGER,feature_version TEXT);
        """)
        for i in range(1,fixtures+1):
            mid="m_"+str(i).zfill(6)
            league="ENG" if include_ENG and i==fixtures else scope
            f=fixture(mid,i,league)
            feature=sample_feature(mid,i,league)
            db.execute("INSERT INTO finished_fixture_index VALUES(?,?,?,?,?,?)",
                       (league,f["season"],mid,f["kickoff_utc"],2,1))
            db.execute("INSERT INTO observations VALUES(?,?)",(league,mid))
            db.execute("INSERT INTO rolling_feature_cache VALUES(?,?,?,?,?,?,?)",
                       (league,mid,f["kickoff_utc"],json.dumps(feature),
                        1,0,FEATURE_VERSION))

class Xg5AblationSafetyTests(unittest.TestCase):
    def test_complete_input_only_predecessor_aggregates_target_outcome_separate(self):
        row=build_example(sample_feature(),fixture())
        self.assertEqual(row["y"],"1")
        self.assertEqual(len(row["base"]),14)
        self.assertEqual(len(row["with_xg"]),18)
        self.assertNotIn("goals_home_90",row)
        self.assertNotIn("goals_away_90",row)

    def test_missing_one_true_last5_xg_is_rejected(self):
        with self.assertRaisesRegex(ResearchSafetyError,"TRUE_LAST5_XG_INCOMPLETE"):
            build_example(sample_feature(xg_ok=False),fixture())

    def test_retrospective_metadata_cannot_be_falsely_promoted(self):
        f=sample_feature()
        f["training_approved"]=True
        with self.assertRaisesRegex(ResearchSafetyError,"HISTORICAL_PIT_CANNOT_BE_CERTIFIED"):
            build_example(f,fixture())

    def test_no_protected_english_test_or_ucl_mixed(self):
        with self.assertRaisesRegex(ResearchSafetyError,"PROTECTED_OR_UNAPPROVED_SCOPE"):
            build_example(sample_feature(scope="ENG"),fixture(scope="ENG"))
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"test.sqlite"
            seed_db(db,include_ENG=True)
            with self.assertRaisesRegex(ResearchSafetyError,"PROTECTED_ENGLISH_TEST_OBSERVED"):
                load_examples(db)

    def test_readonly_sqlite_load_and_no_fake_training(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"test.sqlite"
            seed_db(db,fixtures=3)
            rows,detail=load_examples(db)
            self.assertEqual(len(rows),3)
            self.assertEqual(detail["full_xg5_by_scope"],{"BEL":3})
            r=run(db,fit=False)
            self.assertEqual(r["research_fit_status"],"NO_GO")
            self.assertFalse(r["historical_original_pit_certified"])
            self.assertFalse(r["champion_promotion_authorized"])
            self.assertEqual(r["gates_16_17"],"PENDING")

    def test_split_strict_kickoff_and_same_game_dedup(self):
        examples=[example(i,scope="BEL" if i%3 else "ESP")
                  for i in range(MIN_TOTAL+20)]
        split,why=chronological_split(examples)
        self.assertIsNone(why)
        train,val=split
        self.assertGreaterEqual(len(train),80)
        self.assertGreaterEqual(len(val),25)
        self.assertLess(train[-1]["kickoff_utc"],val[0]["kickoff_utc"])
        with self.assertRaisesRegex(ResearchSafetyError,"NOT_CHRONOLOGICAL"):
            chronological_split(list(reversed(examples)))

    def test_known_brier_and_logloss_and_bad_probability(self):
        p={"1":.8,"X":.1,"2":.1}
        res=score([(p,"1")])
        self.assertAlmostEqual(res["brier_sum3"],.06)
        self.assertAlmostEqual(res["log_loss"],-__import__("math").log(.8))
        with self.assertRaisesRegex(ResearchSafetyError,"NON_NORMALIZED_P"):
            score([({"1":.8,"X":.8,"2":.1},"1")])

    def test_equal_kickoff_must_not_split_between_train_and_val(self):
        rows=[example(i) for i in range(MIN_TOTAL+20)]
        cut=int(len(rows)*.70)
        rows[cut]["kickoff_utc"]=rows[cut-1]["kickoff_utc"]
        split,why=chronological_split(rows)
        self.assertIsNone(why)
        self.assertNotEqual(split[0][-1]["kickoff_utc"],split[1][0]["kickoff_utc"])

if __name__=="__main__":
    unittest.main()
