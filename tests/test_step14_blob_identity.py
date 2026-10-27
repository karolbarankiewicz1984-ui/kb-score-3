"""Historical file contents and candidate-ID matching, fail-closed tests."""
import copy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import unittest

from src.kb3_step14_blob_identity import (
  inspect_pinned_blob_pilot,_target_candidates,_public_kickoff,SCHEMA
)
from src.kb3_step14_archive_probe import _utc,ArchiveProbeError,SEASONS

ROOT=Path(__file__).resolve().parents[1]


class ArchivedContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=json.loads((ROOT/"data/research/STEP14_PIT_PILOT_40_TRAIN_20_VALIDATION_2026-10-27.json").read_text())
        cls.safe=json.loads((ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())

    @staticmethod
    def fixture_schedules():
        games=[{"date":"2024-10-05","time":"17:30",
                "team1":"Everton FC","team2":"Newcastle United FC","score":{}}]
        games+= [{"date":"2024-01-01","time":"10:00",
                   "team1":f"Mock H{i}","team2":f"Mock A{i}","score":{}}
                for i in range(379)]
        return {"matches":games}

    def test_uk_summer_dst_conversion(self):
        d=self.fixture_schedules()["matches"][0]
        self.assertEqual(_public_kickoff(d),_utc("2024-10-05T16:30:00Z"))

    def test_uk_winter_conversion(self):
        d={"date":"2025-01-12","time":"16:30"}
        self.assertEqual(_public_kickoff(d),_utc("2025-01-12T16:30:00Z"))

    def test_one_match_must_not_become_provider_identity(self):
        found=_target_candidates(self.fixture_schedules(),kickoff=_utc("2024-10-05T16:30:00Z"))
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["home_name_openfootball"],"Everton FC")
        self.assertFalse(found[0]["score_present_in_prematch_candidate_blob"])

    def test_ambiguous_same_kickoff_not_accepted(self):
        doc=self.fixture_schedules()
        doc["matches"][1]={"date":"2024-10-05","time":"17:30",
                           "team1":"Other","team2":"Another","score":{}}
        found=_target_candidates(doc,kickoff=_utc("2024-10-05T16:30:00Z"))
        self.assertEqual(len(found),2)

    def test_score_appearing_before_target_is_flagged(self):
        doc=self.fixture_schedules()
        doc["matches"][0]["score"]={"ft":[3,0]}
        self.assertTrue(_target_candidates(doc,kickoff=_utc("2024-10-05T16:30:00Z"))[0]["score_present_in_prematch_candidate_blob"])

    def test_empty_commit_catalog_no_pit_certifications(self):
        i={s:[] for s in SEASONS}
        def fetch(*a):raise AssertionError("No commit, never fetch")
        r=inspect_pinned_blob_pilot(self.roster,self.safe,commits=i,fetch_blob=fetch)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["historical_source_blob_unique_commits_downloaded"],0)
        self.assertEqual(r["official_pitchapi_training_records_certified"],0)
        self.assertEqual(len(r["records"]),60)
        self.assertFalse(r["historical_publication_time_independently_verified"])
        self.assertFalse(r["official_pitchapi_native_team_pair_identity_verified"])
        self.assertFalse(r["gate14_pass"])

    def test_added_TEST_fixture_rejected(self):
        roster=copy.deepcopy(self.roster)
        roster["fixtures"][0]["partition"]="TEST"
        with self.assertRaises(ArchiveProbeError):
            inspect_pinned_blob_pilot(roster,self.safe,commits={s:[] for s in SEASONS},fetch_blob=lambda *a:None)

    def test_fake_committer_date_never_proves_publication(self):
        fixture=next(x for x in self.roster["fixtures"] if x["season"]=="2024-25")
        ko=_utc(fixture["kickoff_utc"])
        i={s:[] for s in SEASONS}
        i["2024-25"]=[(ko-timedelta(days=4),"a"*40)]
        calls=[]
        def fetch(season,sha):
            calls.append((season,sha))
            return self.fixture_schedules(),"b"*64
        r=inspect_pinned_blob_pilot(self.roster,self.safe,commits=i,fetch_blob=fetch)
        self.assertGreater(len(calls),0)
        self.assertFalse(r["git_committer_timestamp_proves_publication"])
        self.assertEqual(r["official_pitchapi_training_records_certified"],0)
        self.assertTrue(all(x["official_train_eligible"] is False for x in r["records"]))


if __name__=="__main__":
    unittest.main()
