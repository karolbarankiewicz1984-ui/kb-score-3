"""Pure tests for private owner-only historical FT and Elo prerequisites."""
import unittest
from datetime import datetime,timezone
from src.kb3_step14_private_results_equivalence import (
    NativeFTError,integer_goal,replay_elo_batched,native_scores,index_native,audit,
)

class SourceScoreEquivalenceTests(unittest.TestCase):
    def test_fpl_historic_integer_floats(self):
        self.assertEqual(integer_goal("0.0"),0)
        self.assertEqual(integer_goal("12.0"),12)
    def test_fractional_and_negative_scores_rejected(self):
        for val in ("1.5","-1.0","nan",None,True,1.5):
            with self.assertRaises(NativeFTError):integer_goal(val)
    def test_elo_zero_sum_with_real_original_parameters(self):
        ko=datetime(2023,8,12,14,tzinfo=timezone.utc)
        ratings=replay_elo_batched([(ko,"fpl_1","a","b",2,0)])
        self.assertAlmostEqual(ratings["a"]+ratings["b"],3000.0,places=8)
        self.assertGreater(ratings["a"],1500.0)
    def test_elo_same_time_updates_are_independent(self):
        ko=datetime(2023,8,12,14,tzinfo=timezone.utc)
        left=replay_elo_batched([(ko,"a","t1","t2",1,0),(ko,"b","t3","t4",2,2)])
        right=replay_elo_batched([(ko,"b","t3","t4",2,2),(ko,"a","t1","t2",1,0)])
        for team in ("t1","t2","t3","t4"):
            self.assertAlmostEqual(left[team],right[team],places=10)
    def test_elo_rejects_duplicate_team_same_kickoff(self):
        ko=datetime(2023,8,12,14,tzinfo=timezone.utc)
        with self.assertRaisesRegex(NativeFTError,"SIMULTANEOUS"):
            replay_elo_batched([(ko,"a","t1","t2",1,0),(ko,"b","t1","t3",2,2)])
    def test_no_future_or_validation_score_access(self):
        native={}
        sources=[]
        for year,short in (("2023/2024","2023-24"),("2024/2025","2024-25")):
            rows=[]
            for i in range(380):
                mid=f"m_{short[2:4]}{i:04d}"
                n={"season":short,"role":"TRAIN",
                   "kickoff_utc":f"2023-08-12T14:00:00Z",
                   "home_id":"t_000001","away_id":"t_000002"}
                native[mid]=n
                # A deliberately invalid value for all *non-whitelisted*
                # target labels must never be inspected.
                rows.append({"id":mid,"time_utc":n["kickoff_utc"],
                    "home_team":{"id":n["home_id"]},
                    "away_team":{"id":n["away_id"]},
                    "score_home":0 if i==0 and short=="2023-24" else object(),
                    "score_away":1 if i==0 and short=="2023-24" else object()})
            sources.append({"resource":f"pitchapi:history:premier-league:{year}:matches:played",
                            "payload":{"matches":rows}})
        sources.append({"resource":"pitchapi:history:premier-league:2025/2026:matches:played",
                        "payload":{"matches":"NEVER_READ_VALIDATION"}})
        source_id="m_230000"
        result=native_scores(sources,native,{source_id})
        self.assertEqual(result,{source_id:(0,1)})
    def test_missing_allowlisted_prior_is_blocker(self):
        with self.assertRaises(NativeFTError):
            native_scores([],{},{"m_unknown"})
    def test_validation_label_cannot_enter_allowlist(self):
        with self.assertRaisesRegex(NativeFTError,"ALLOWLIST"):
            native_scores([],{"m_123456":{"role":"VALIDATION"}},{"m_123456"})
    def test_private_match_index_never_needs_future_scores(self):
        n={}
        for i in range(380):
            n[f"m_{i:06d}"]={"season":"2023-24",
                 "home_id":f"t_{i:06d}","away_id":"t_999999",
                 "kickoff_utc":"2023-10-06T14:00:00Z"}
        index=index_native(n,{"m_000000":(1,0)},"2023-24")
        self.assertEqual(len(index),380)
        self.assertEqual(sum(x[2] is None for x in index.values()),379)
    def test_no_training_or_pit_release_from_audit(self):
        with self.assertRaisesRegex(NativeFTError,"REQUIRES_ORIGINAL"):
            audit({}, {}, {})

if __name__=="__main__":unittest.main()
