"""Step14 public 1140 target-free reference projection and native-pair joins."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import json
import unittest
from src.kb3_step14_public_1140_fixtures import project,PublicReferenceError
from src.kb3_step14_full_identity_pit_audit import _independent_public_1140,FullNativeAuditError
from src.kb3_split import sha

def make_seasons(with_scores=True):
    datas={}
    native={}
    for s in ("2023-24","2024-25","2025-26"):
        games=[]
        for h in range(20):
            for a in range(20):
                if h==a:continue
                i=len(games)
                when=datetime(int(s[:4]),8,15,12,0,tzinfo=timezone.utc)
                # Fixed legitimate London local time, same-day many concurrent
                local=when.astimezone(ZoneInfo("Europe/London"))
                item={"date":local.date().isoformat(),"time":local.strftime("%H:%M"),
                      "team1":f"Team {h:02d}","team2":f"Team {a:02d}"}
                if with_scores:item["score"]={"ft":[h%5,a%3],"odds":{"danger":1}}
                games.append(item)
                native[f"{s}:{h}:{a}"]={
                   "season":s,"home_name":item["team1"],"away_name":item["team2"],
                   "kickoff_utc":when.isoformat().replace("+00:00","Z")}
        raw=json.dumps({"matches":games},sort_keys=True).encode("utf8")
        assert len(raw)>2000
        datas[s]=raw
    return datas,native

class PublicExternal1140Tests(unittest.TestCase):
    def test_projection_never_exports_scores_or_odds(self):
        docs,_=make_seasons()
        p=project(fetcher=lambda url:docs[url.split("/")[-2]],
            observed_at_utc="2026-10-27T15:00:00Z")
        self.assertEqual(sum(x["reference_matches"] for x in p["source_seasons"].values()),1140)
        self.assertEqual(p["full_coverage_historical_season_fixtures"],1140)
        self.assertNotIn('"score"',json.dumps(p))
        self.assertNotIn('"odds"',json.dumps(p))
        self.assertTrue(p["observation_is_retrospective_not_2023_2026_pit"])
        self.assertFalse(p["training_allowed"])

    def test_matching_public_1140_exact_home_away_and_utc(self):
        docs,native=make_seasons()
        p=project(fetcher=lambda url:docs[url.split("/")[-2]],
                  observed_at_utc="2026-10-27T15:00:00Z")
        result=_independent_public_1140(native,p)
        self.assertEqual(result["checked"],1140)
        self.assertEqual(result["counts"],{"EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF":1140})
        self.assertFalse(result["source_is_historical_pit"])

    def test_rescheduled_public_fixture_counted_as_time_conflict(self):
        docs,native=make_seasons()
        p=project(fetcher=lambda url:docs[url.split("/")[-2]],
                  observed_at_utc="2026-10-27T15:00:00Z")
        native["2025-26:1:2"]["kickoff_utc"]="2026-01-31T20:00:00Z"
        result=_independent_public_1140(native,p)
        self.assertEqual(result["counts"]["EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF"],1139)
        self.assertEqual(result["counts"]["SAME_PUBLIC_TEAM_PAIR_DIFFERENT_UTC_KICKOFF"],1)

    def test_wrong_club_names_do_not_match_based_on_time_only(self):
        docs,native=make_seasons()
        p=project(fetcher=lambda url:docs[url.split("/")[-2]],
                  observed_at_utc="2026-10-27T15:00:00Z")
        native["2025-26:1:2"]["home_name"]="Not a real club"
        result=_independent_public_1140(native,p)
        self.assertEqual(result["counts"]["NO_EXACT_PUBLIC_TEAM_PAIR_SAME_SEASON"],1)

    def test_public_source_cannot_claim_training_allowed_with_new_hash(self):
        docs,native=make_seasons()
        p=project(fetcher=lambda url:docs[url.split("/")[-2]],
                  observed_at_utc="2026-10-27T15:00:00Z")
        p["training_allowed"]=True
        p["projection_sha256"]=sha({k:v for k,v in p.items() if k!="projection_sha256"})
        with self.assertRaisesRegex(FullNativeAuditError,"PUBLIC_1140_REFERENCE_NOT_AUTHENTIC"):
            _independent_public_1140(native,p)

    def test_non_october_retro_clock_does_not_assert_old_pit(self):
        docs,_=make_seasons()
        with self.assertRaisesRegex(PublicReferenceError,"CAPTURE_CLOCK"):
            project(fetcher=lambda url:docs[url.split("/")[-2]],
                    observed_at_utc="2024-08-01T00:00:00Z")

if __name__=="__main__": unittest.main()
