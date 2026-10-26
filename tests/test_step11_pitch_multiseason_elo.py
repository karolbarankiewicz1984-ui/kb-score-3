"""Cross-season native-PitchAPI Elo: 3 full completed seasons + live 2026/27.

All synthetic tests. A real historical provider fetch performed today cannot
establish 2023/24 prematch PIT. No fitting, prices or output predictions.
"""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import sqlite3
import unittest
from src.kb3_pitch_uefa_evidence import add_observation
from src.kb3_pitch_native_ledger import record
from src.kb3_pitch_native_observed_features import build_native_observed
from src.kb3_pitch_multiseason_history import (
    historical_season_history,HISTORICAL_SEASONS,SEASON_RESOURCE)
from src.kb3_features import FeatureSafetyError,digest

def clock(seconds=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z")

def make_season(year,*,current=False,ids_offset=None):
    base=ids_offset if ids_offset is not None else (year-2022)*100000
    rows=[]
    for i in range(380):
        round_number=i//10
        j=i%10
        # Each round contains exactly 10 disjoint team pairs, so ratings are
        # updated simultaneously but never twice for the same team.
        kickoff=(datetime(year,8 if current else 9,1,tzinfo=timezone.utc)
                 +timedelta(days=7*round_number))
        done=not current or i<80
        if current and not done:
            kickoff=datetime(2027,5,1,tzinfo=timezone.utc)
        rows.append({"id":f"m_{base+i:06d}",
           "time_utc":kickoff.isoformat().replace("+00:00","Z"),
           "status":"finished" if done else "not_started",
           "home_team":{"id":f"t_{2*j:06d}","name":f"Team {2*j}"},
           "away_team":{"id":f"t_{2*j+1:06d}","name":f"Team {2*j+1}"},
           "score_home":1 if done else None,
           "score_away":0 if done else None})
    return rows

def past_receipts():
    items=[]
    add_observation(items,resource="pitchapi:catalog",
       payload={"leagues":[{"id":"l_test","name":"Premier League"}]},
       started=clock(-21),completed=clock(-20))
    for year,offset in ((2023,-18),(2024,-15),(2025,-12)):
        add_observation(items,
           resource=SEASON_RESOURCE.format(season=f"{year}/{year+1}"),
           payload={"matches":make_season(year)},
           started=clock(offset),completed=clock(offset+1))
    return items

class NativeHistoricalEloTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.current=make_season(2026,current=True)
        record(self.db,"matches",self.current,started_at_utc=clock(-9),
               completed_at_utc=clock(-8),origin="NETWORK_OBSERVED")
        self.target=self.current[-1]["id"]
        self.past=past_receipts()
        self.cutoff=clock(1)

    def build(self,**kwargs):
        return build_native_observed(self.db,self.target,
           cutoff_utc=self.cutoff,historical_receipts=self.past,**kwargs)

    def test_full_3_historical_seasons_enrich_elo_without_xg_fabrication(self):
        r=self.build()
        self.assertEqual(r["accepted_predecessor_count"],3*380+80)
        self.assertEqual(r["features"]["home_prior_seasons_games_available"],114)
        self.assertEqual(r["features"]["away_prior_seasons_games_available"],114)
        self.assertEqual(r["features"]["home_elo_games_available"],122)
        self.assertEqual(r["features"]["away_elo_games_available"],122)
        self.assertEqual(r["features"]["home_all_5_xg_n"],0)
        self.assertIsNone(r["features"]["home_all_5_xg_avg"])
        self.assertFalse(r["training_allowed"])
        self.assertFalse(r["target_prematch_snapshot_certified"])
        self.assertEqual(r["source_evidence"]["multiseason_elo_status"],
           "RETROSPECTIVE_HISTORY_OBSERVED_BEFORE_TARGET_CUTOFF")

    def test_missing_historical_input_keeps_single_season_behavior(self):
        r=build_native_observed(self.db,self.target,cutoff_utc=self.cutoff)
        self.assertEqual(r["accepted_predecessor_count"],80)
        self.assertEqual(r["features"]["home_prior_seasons_games_available"],0)
        self.assertEqual(r["source_evidence"]["multiseason_elo_status"],
                         "CURRENT_SEASON_ONLY")

    def test_source_field_times_have_no_lookahead(self):
        r=self.build()
        cutoff=datetime.fromisoformat(r["feature_cutoff_utc"].replace("Z","+00:00"))
        for name,info in r["feature_availability"].items():
            stamp=datetime.fromisoformat(
                info["latest_required_observed_at_utc"].replace("Z","+00:00"))
            self.assertLessEqual(stamp,cutoff,name)
            self.assertFalse(info["training_allowed"])
        self.assertEqual(r["sha256"],digest({k:v for k,v in r.items() if k!="sha256"}))

    def test_late_fetched_historical_data_refused(self):
        bad=deepcopy(self.past)
        # Even if the chain is re-signed under unit-test control,
        # historical data captured AFTER the cutoff is never admitted.
        bad=[]
        add_observation(bad,resource="pitchapi:catalog",payload={},
            started=clock(2),completed=clock(3),origin="SYNTHETIC_TEST")
        with self.assertRaisesRegex(FeatureSafetyError,"INVALID_HISTORICAL_SOURCE_CHAIN"):
            historical_season_history(bad,cutoff_utc=clock(1))

    def test_duplicate_historical_native_id_rejected(self):
        rows=deepcopy(self.past)
        # A forged season record fails signed digest/hash-chain verification.
        rows[2]["payload"]["matches"][0]["id"]=rows[1]["payload"]["matches"][0]["id"]
        with self.assertRaisesRegex(FeatureSafetyError,"INVALID_HISTORICAL_SOURCE_CHAIN"):
            historical_season_history(rows,cutoff_utc=clock(1))

    def test_partial_season_has_no_silent_fallback(self):
        rows=deepcopy(self.past)
        rows[1]["payload"]["matches"].pop()
        with self.assertRaisesRegex(FeatureSafetyError,"INVALID_HISTORICAL_SOURCE_CHAIN"):
            historical_season_history(rows,cutoff_utc=clock(1))

    def test_real_receipt_time_after_cutoff_is_refused(self):
        with self.assertRaisesRegex(FeatureSafetyError,"OBSERVED_AFTER_CUTOFF"):
            historical_season_history(self.past,cutoff_utc=clock(-18))

    def test_rehashed_source_with_unstable_team_ids_is_refused(self):
        from src.kb3_pit_ledger import canonical,hexdigest
        rows=deepcopy(self.past)
        for match in rows[2]["payload"]["matches"]:
            for side in ("home_team","away_team"):
                number=int(match[side]["id"][2:])
                match[side]["id"]=f"t_{number+1000:06d}"
                match[side]["name"]=f"Renamed {number+1000}"
        previous="0"*64
        for receipt in rows:
            receipt["payload_sha256"]=hexdigest(canonical(receipt["payload"]))
            receipt["previous_sha256"]=previous
            payload=dict(receipt);payload.pop("chain_sha256")
            receipt["chain_sha256"]=hexdigest(canonical(payload))
            previous=receipt["chain_sha256"]
        with self.assertRaisesRegex(FeatureSafetyError,"UNSTABLE_TEAM_IDENTIFIERS"):
            historical_season_history(rows,cutoff_utc=self.cutoff)

    def test_replayed_history_deterministic(self):
        a=self.build()
        b=self.build()
        self.assertEqual(a["sha256"],b["sha256"])
        self.assertEqual(a["features"]["home_elo"],b["features"]["home_elo"])

    def test_provisional_elo_retains_unfitted_parameters(self):
        a=self.build()
        self.assertEqual(a["elo_parameters"]["initial"],1500.0)
        self.assertEqual(a["elo_parameters"]["season_retention"],0.85)
        self.assertEqual(a["elo_parameter_status"],"PROVISIONAL_NOT_FITTED")

    def test_strict_source_count_requires_three_completed_seasons(self):
        with self.assertRaisesRegex(FeatureSafetyError,"PITCH_HISTORICAL_RECEIPT_COUNT"):
            historical_season_history(self.past[:-1],cutoff_utc=clock(1))

if __name__=="__main__":
    unittest.main()
