"""Safety regressions for owner-local PitchAPI/FPL matched fixture audit.

Zero API calls and zero RSA/key access: mock the SDK. Tests must never
pass validation / TEST score labels to the semantic comparison.
"""
import json,sys,types,unittest
from unittest.mock import patch
from src.kb3_step14_pitchapi_xg_semantics import SemanticAuditError
from scripts.step14_owner_pitchapi_xg_same_fixture_local import (
    SELECTED_CHRONOLOGICAL_INDICES,MAX_PITCHAPI_REQUESTS,api_replay)
MID="m_Aa1234";H="t_Ab1234";A="t_Bb1234"
def shots():
    return {"match_id":MID,"periods":[{"period":"All","shots":[
       {"id":"s_001","team_id":H,"expected_goals":0.4},
       {"id":"s_002","team_id":A,"expected_goals":0.2}]}]}
def stats():
    return {"match_id":MID,"home_team":{"id":H},"away_team":{"id":A},
       "periods":[{"period":"All","groups":[{"group_name":"Expected goals (xG)",
          "items":[{"key":"expected_goals","format_type":"double","home":"0.40","away":"0.20"}]}]}]}
class FakeSDK:
    calls=[]
    def __init__(self,api_key):
        assert api_key=="PRIVATE_SENTINEL_DO_NOT_ECHO"
        self.matches=types.SimpleNamespace(shots=self.shots,stats=self.stats)
    def shots(self,mid):
        assert mid==MID
        self.calls.append("shots")
        return shots()
    def stats(self,mid):
        assert mid==MID
        self.calls.append("stats")
        return stats()

class OwnerNoLeakTests(unittest.TestCase):
    def test_fixed_six_source_selection_and_12_max_requests(self):
        self.assertEqual(len(SELECTED_CHRONOLOGICAL_INDICES),6)
        self.assertEqual(MAX_PITCHAPI_REQUESTS,12)
    def test_fake_same_native_match_two_endpoints_only(self):
        FakeSDK.calls=[]
        p=types.SimpleNamespace(source_side_xg_values_IN_MEMORY_ONLY=None)
        public={"source_side_xg_values_IN_MEMORY_ONLY":{(123,1):0.5,(123,2):0.25}}
        with patch.dict(sys.modules,{"pitchapi":types.SimpleNamespace(PitchAPI=FakeSDK)}):
            out=api_replay(selected=[(MID,H,A,123,1,2)],
                public=public,key="PRIVATE_SENTINEL_DO_NOT_ECHO")
        self.assertEqual(FakeSDK.calls,["shots","stats"])
        self.assertEqual(out["api_calls"],2)
        self.assertEqual(out["exact_matched_team_sides"],2)
        self.assertFalse(out["historical_PitchAPI_first_publication_proven"])
        self.assertNotIn("PRIVATE_SENTINEL",json.dumps(out))
        self.assertNotIn(MID,json.dumps(out))
    def test_all_twelve_calls_never_cross_budget(self):
        FakeSDK.calls=[]
        public={"source_side_xg_values_IN_MEMORY_ONLY":{(123,1):0.5,(123,2):0.25}}
        with patch.dict(sys.modules,{"pitchapi":types.SimpleNamespace(PitchAPI=FakeSDK)}):
            out=api_replay(selected=[(MID,H,A,123,1,2)]*6,
                public=public,key="PRIVATE_SENTINEL_DO_NOT_ECHO")
        self.assertEqual(out["api_calls"],12)
        self.assertEqual(out["exact_matched_team_sides"],12)
        self.assertEqual(len(FakeSDK.calls),12)
    def test_seven_matches_rejected_before_seventh_call(self):
        FakeSDK.calls=[]
        public={"source_side_xg_values_IN_MEMORY_ONLY":{(123,1):0.5,(123,2):0.25}}
        with patch.dict(sys.modules,{"pitchapi":types.SimpleNamespace(PitchAPI=FakeSDK)}):
            with self.assertRaisesRegex(Exception,"BUDGET"):
                api_replay(selected=[(MID,H,A,123,1,2)]*7,
                    public=public,key="PRIVATE_SENTINEL_DO_NOT_ECHO")
        self.assertEqual(len(FakeSDK.calls),12)
    def test_wrong_match_does_not_compare(self):
        class BadSDK(FakeSDK):
            def shots(self,mid):
                d=shots();d["match_id"]="m_Bb1234";return d
        public={"source_side_xg_values_IN_MEMORY_ONLY":{(123,1):0.5,(123,2):0.25}}
        with patch.dict(sys.modules,{"pitchapi":types.SimpleNamespace(PitchAPI=BadSDK)}):
            with self.assertRaises(SemanticAuditError):
                api_replay(selected=[(MID,H,A,123,1,2)],public=public,
                           key="PRIVATE_SENTINEL_DO_NOT_ECHO")
if __name__=="__main__":unittest.main()
