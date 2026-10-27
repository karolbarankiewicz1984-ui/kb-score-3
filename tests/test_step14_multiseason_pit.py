"""Independent negative tests: clock pinning, stale source and crosswalk."""
import copy, unittest
from datetime import datetime,timezone
from src.kb3_step14_multiseason_pit import (
    SOURCES,UNVERIFIED,SourceAuditError,strict_four_native_crosswalk,
    parse_openfootball,form5_openfootball,utc,london,_score
)

class MultiSeasonAuditTests(unittest.TestCase):
    def test_three_seasons_have_external_pinned_sha(self):
        self.assertEqual([s["season"] for s in SOURCES],["2023-24","2024-25","2025-26"])
        for s in SOURCES:
            self.assertEqual(len(s["commit"]),40)
            self.assertEqual(len(s["sha"]),64)
            self.assertTrue(s["event"].isdigit())
            self.assertLess(utc(s["push"]),datetime(2026,1,1,tzinfo=timezone.utc))
    def test_unverified_candidate_cannot_be_promoted(self):
        self.assertEqual(len(UNVERIFIED),4)
        self.assertTrue(all("push" not in r and "event" not in r for r in UNVERIFIED))
    def test_dont_mistake_2024_pl_clock_for_utc(self):
        self.assertEqual(london("2024-10-05","17:30").isoformat(),"2024-10-05T16:30:00+00:00")
        self.assertEqual(london("2025-08-18","20:00").isoformat(),"2025-08-18T19:00:00+00:00")
    def test_naive_or_local_clock_rejected(self):
        for x in ("2024-10-05T16:30:00","2024-10-05T17:30:00+01:00",""):
            with self.assertRaises(SourceAuditError):utc(x)
    def test_bad_public_xg_score_not_admitted_as_ft(self):
        self.assertFalse(_score({"score":{"ht":[1,0]}}))
        with self.assertRaises(SourceAuditError):
            _score({"score":{"ft":[1,"0"]}})
    def test_2025_preseason_no_eligible_form5(self):
        a=SOURCES[2]
        fake=[{"home":"leeds united","away":"everton",
               "kickoff":london("2025-08-18","20:00"),"ft_published":False}]
        state,_=form5_openfootball(fake,a,fake[0])
        self.assertEqual(state,"FEWER_THAN_FIVE_PREDECESSORS")
    def test_intervening_no_prior_score_blocks(self):
        a=SOURCES[1]
        target={"home":"everton","away":"newcastle united",
                "kickoff":london("2024-10-05","17:30"),"ft_published":False}
        gap={"home":"everton","away":"arsenal",
             "kickoff":london("2024-10-03","20:00"),"ft_published":False}
        state,_=form5_openfootball([gap,target],a,target)
        self.assertEqual(state,"INTERVENING_RESULT_NOT_IN_SNAPSHOT")
    def test_unknown_old_kickoff_blocks(self):
        a=SOURCES[1]
        target={"home":"everton","away":"newcastle united",
                "kickoff":london("2024-10-05","17:30"),"ft_published":False}
        missing={"home":"everton","away":"arsenal",
             "kickoff":None,"ft_published":False}
        state,_=form5_openfootball([missing,target],a,target)
        self.assertEqual(state,"UNKNOWN_TEAM_SCHEDULE")
    def test_known_native_sample_never_grants_train(self):
        source={
            "2023-24":{"public_form5_candidates":[],"finished_earlier_ft_in_blob":70},
            "2024-25":{"public_form5_candidates":[{"home":"everton","away":"newcastle united","kickoff_utc":"2024-10-05T16:30:00Z"}],"finished_earlier_ft_in_blob":60},
            "2025-26":{"public_form5_candidates":[],"finished_earlier_ft_in_blob":0}}
        records=strict_four_native_crosswalk(source)
        self.assertEqual(len(records),4)
        self.assertEqual(sum(x["earlier_public_form5_proven"] for x in records),1)
        self.assertFalse(any(x["official_m1_training_allowed"] for x in records))
        self.assertTrue(any(x["old_public_schedule_revised_after_source_push"] for x in records))
    def test_no_name_only_crosswalk(self):
        data={
            "2023-24":{"public_form5_candidates":[],"finished_earlier_ft_in_blob":70},
            "2024-25":{"public_form5_candidates":[{"home":"everton","away":"newcastle united","kickoff_utc":"2024-10-05T16:31:00Z"}],"finished_earlier_ft_in_blob":60},
            "2025-26":{"public_form5_candidates":[],"finished_earlier_ft_in_blob":0}}
        self.assertEqual(sum(x["earlier_public_form5_proven"] for x in strict_four_native_crosswalk(data)),0)
    def test_future_ft_in_old_public_blob_rejected(self):
        s=copy.deepcopy(SOURCES[1])
        s["sha"]="0"*64
        with self.assertRaises(SourceAuditError):
            parse_openfootball(b'{"matches":[]}',s)

if __name__=="__main__": unittest.main()
