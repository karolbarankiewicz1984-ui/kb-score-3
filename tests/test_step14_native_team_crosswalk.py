"""Step14 independent no-key tests: native home/away IDs only, no TEST/odds."""
import copy
import json
from pathlib import Path
import unittest

from src.kb3_step14_native_team_crosswalk import (
    audit_crosswalk,_verify_public_evidence,NativeCrosswalkError,
    REQUIRED,canonical_team_name
)

ROOT=Path(__file__).resolve().parents[1]
NAMES={
    "Everton FC":"t_AAAAAA",
    "Newcastle United FC":"t_BBBBBB",
    "Leeds United":"t_CCCCCC",
    "Liverpool FC":"t_DDDDDD",
    "Arsenal FC":"t_EEEEEE",
    "Sunderland AFC":"t_FFFFFF",
    "Aston Villa":"t_GGGGGG",
}

def fake_receipts():
    receipts=[{"resource":"pitchapi:catalog"}]
    for n,season in enumerate(("2023/2024","2024/2025","2025/2026")):
        games=[]
        for i in range(380):
            games.append({
                "id":"m_"+str(n)+str(i).zfill(5),
                "time_utc":f"{2023+n}-11-11T15:00:00Z",
                "home_team":{"id":"t_HHHHHH","name":"Other Team"},
                "away_team":{"id":"t_IIIIII","name":"Another Team"},
                "score_home":0,"score_away":0,
            })
        targets=[(fid,exp) for fid,exp in REQUIRED.items()
                 if exp["season"]==season.replace("/","-")]
        for i,(fid,exp) in enumerate(targets):
            games[i]={
                "id":fid,"time_utc":exp["kickoff_utc"],
                "home_team":{"id":NAMES[exp["home"]],"name":exp["home"]},
                "away_team":{"id":NAMES[exp["away"]],"name":exp["away"]},
                "score_home":2,"score_away":0,
            }
        receipts.append({
            "resource":f"pitchapi:history:premier-league:{season}:matches:played",
            "payload":{"matches":games}
        })
    return receipts

class LocalNativeFixtureCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.safe=json.loads((ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
        cls.blob=json.loads((ROOT/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json").read_text())
        cls.clock=json.loads((ROOT/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json").read_text())

    def run_proof(self,receipts=None,blob=None,clock=None,safe=None,**kwargs):
        return audit_crosswalk(safe=self.safe if safe is None else safe,
                               blob=self.blob if blob is None else blob,
                               clock=self.clock if clock is None else clock,
                               receipts=fake_receipts() if receipts is None else receipts,
                               **kwargs)

    def test_exact_4_source_native_team_pairs(self):
        a=self.run_proof()
        self.assertEqual(a["total_checked"],4)
        self.assertEqual(a["identity_crosswalk_verified_count"],4)
        self.assertEqual(a["train_verified_identity_count"],1)
        self.assertEqual(a["validation_verified_identity_count"],3)
        self.assertEqual(a["test_records_accessed"],0)
        self.assertFalse(a["production_catboost_training_allowed"])
        self.assertFalse(a["historical_prematch_PIT_certified"])
        self.assertFalse(a["gate14_pass"])
        self.assertTrue(all(x["original_pinned_PitchAPI_native_ids_confirmed"] for x in a["rows"]))
        self.assertEqual(a["rows"][0]["pitch_home_team_id"],"t_AAAAAA")
        self.assertEqual(a["rows"][0]["pitch_away_team_id"],"t_BBBBBB")
        self.assertNotIn("2"," ".join(a.keys()))
        self.assertFalse(any("score" in k for row in a["rows"] for k in row))

    def test_canonical_alias_requires_full_name(self):
        self.assertEqual(canonical_team_name("Everton FC"),canonical_team_name("Everton"))
        self.assertEqual(canonical_team_name("Sunderland AFC"),canonical_team_name("Sunderland"))
        self.assertNotEqual(canonical_team_name("Newcastle"),canonical_team_name("Newcastle United"))

    def test_swapped_home_and_away_fails_identity(self):
        r=fake_receipts()
        season=next(q for q in r if q["resource"].endswith("2024/2025:matches:played"))
        m=next(x for x in season["payload"]["matches"] if x["id"]=="m_3AMymS")
        m["home_team"],m["away_team"]=m["away_team"],m["home_team"]
        a=self.run_proof(r)
        self.assertEqual(a["identity_crosswalk_verified_count"],3)
        self.assertFalse(a["rows"][0]["external_fixture_identity_crosswalk_confirmed"])
        self.assertFalse(a["production_catboost_training_allowed"])

    def test_changed_native_kickoff_fails(self):
        r=fake_receipts()
        season=next(q for q in r if q["resource"].endswith("2024/2025:matches:played"))
        m=next(x for x in season["payload"]["matches"] if x["id"]=="m_3AMymS")
        m["time_utc"]="2024-10-05T15:30:00Z"
        a=self.run_proof(r)
        self.assertFalse(a["rows"][0]["native_kickoff_exact"])
        self.assertEqual(a["identity_crosswalk_verified_count"],3)

    def test_changed_public_candidate_rejected(self):
        b=copy.deepcopy(self.blob)
        rec=next(x for x in b["records"] if x["pitch_fixture_id"]=="m_3AMymS")
        rec["match_by_exact_uk_local_to_utc_kickoff"][0]["home_name_openfootball"]="Leeds United"
        with self.assertRaisesRegex(NativeCrosswalkError,"PUBLIC_BLOB_CANDIDATE_CHANGED"):
            self.run_proof(blob=b)

    def test_clock_must_match_independent_event(self):
        b=copy.deepcopy(self.clock)
        ev=next(x for x in b["records"] if x["candidate_source_commit_sha"]==REQUIRED["m_3AMymS"]["commit"])
        ev["server_created_at_utc"]="2024-10-02T13:52:43Z"
        with self.assertRaisesRegex(NativeCrosswalkError,"INDEPENDENT_PUBLIC_PUSH_NOT_PINNED"):
            self.run_proof(clock=b)

    def test_no_test_role_injected(self):
        s=copy.deepcopy(self.safe)
        row=next(x for x in s["fixtures"] if x["fixture_id"]=="m_3AMymS")
        row["partition"]="TEST"
        with self.assertRaisesRegex(NativeCrosswalkError,"SPLIT_SHA_NOT_PINNED"):
            self.run_proof(safe=s)

    def test_missing_fixture_refused(self):
        r=fake_receipts()
        s=next(x for x in r if x["resource"].endswith("2025/2026:matches:played"))
        i=next(i for i,x in enumerate(s["payload"]["matches"]) if x["id"]=="m_4AseJ9")
        s["payload"]["matches"][i]["id"]="m_222222"
        with self.assertRaisesRegex(NativeCrosswalkError,"NATIVE_FIXTURE_MISSING"):
            self.run_proof(r)

    def test_unpinned_hash_refused(self):
        with self.assertRaisesRegex(NativeCrosswalkError,"ORIGINAL_ARCHIVE_HASH_CHANGED"):
            self.run_proof(source_chain_sha="f"*64)

    def test_wrong_native_id_format_is_hard_refusal(self):
        r=fake_receipts()
        s=next(x for x in r if x["resource"].endswith("2024/2025:matches:played"))
        m=next(x for x in s["payload"]["matches"] if x["id"]=="m_3AMymS")
        m["home_team"]["id"]="INVALID_TEAM_ID"
        with self.assertRaisesRegex(NativeCrosswalkError,"NATIVE_TEAM_ID_INVALID"):
            self.run_proof(r)

if __name__=="__main__":
    unittest.main()
