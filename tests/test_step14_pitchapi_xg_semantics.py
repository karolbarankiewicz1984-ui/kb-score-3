"""Adversarial safety and semantic separation checks, no API/owner secret."""
import copy,unittest
from src.kb3_step14_pitchapi_xg_semantics import (
    SemanticAuditError,parse_native_team_stats,parse_native_shots,
    side_comparison,aggregate,classify_historical_publication)
MID="m_Aa1234";HOME="t_Ab1234";AWAY="t_Bb1234"
def shots():
    return {"data":{"match_id":MID,"periods":[{"period":"All","shots":[
        {"id":"s_12","team_id":HOME,"expected_goals":0.4,"expected_goals_on_target":0.81},
        {"id":"s_13","team_id":AWAY,"expected_goals":0.75}]}]}}
def stats():
    return {"data":{"match_id":MID,"home_team":{"id":HOME},
      "away_team":{"id":AWAY},"periods":[{"period":"All",
      "groups":[{"group_name":"Expected goals (xG)","items":[
          {"key":"expected_goals","home":"0.40","away":"0.75","format_type":"double"},
          {"key":"expected_goals_on_target","home":"0.81","away":"0.0","format_type":"double"},
          {"key":"npxg","home":"0.40","away":"0.00","format_type":"double"}]}]}]}}
class PitchSemanticsTests(unittest.TestCase):
    def test_exact_two_teams_and_true_fullmatch_shot_total(self):
        x=parse_native_shots(shots(),MID,HOME,AWAY)
        self.assertEqual(x,(0.4,0.75,1,1))
        self.assertEqual(parse_native_team_stats(stats(),MID,HOME,AWAY),(0.4,0.75))
    def test_conservatively_avoid_xgot_and_npxg(self):
        s=stats();s["data"]["periods"][0]["groups"][0]["items"]=[
            s["data"]["periods"][0]["groups"][0]["items"][1]]
        with self.assertRaisesRegex(SemanticAuditError,"NOT_UNIQUE"):
            parse_native_team_stats(s,MID,HOME,AWAY)
    def test_wrong_pitch_match_id_fails(self):
        s=stats();s["data"]["match_id"]="m_Zz1234"
        with self.assertRaisesRegex(SemanticAuditError,"FIXTURE_MISMATCH"):
            parse_native_team_stats(s,MID,HOME,AWAY)
    def test_wrong_pitch_team_id_fails(self):
        s=stats();s["data"]["away_team"]["id"]="t_Zz1234"
        with self.assertRaisesRegex(SemanticAuditError,"SIDE_ID_MISMATCH"):
            parse_native_team_stats(s,MID,HOME,AWAY)
    def test_real_pitchapi_repeated_xg_in_top_stats_agrees(self):
        s=stats()
        s["data"]["periods"][0]["groups"].append({
            "group_name":"Top stats",
            "items":[{"key":"expected_goals","format_type":"double","home":"0.40","away":"0.75"}]})
        self.assertEqual(parse_native_team_stats(s,MID,HOME,AWAY),(.4,.75))
    def test_real_pitchapi_repeated_xg_conflict_blocks(self):
        s=stats()
        s["data"]["periods"][0]["groups"].append({
            "group_name":"Top stats",
            "items":[{"key":"expected_goals","format_type":"double","home":"0.92","away":"0.75"}]})
        with self.assertRaisesRegex(SemanticAuditError,"CONFLICT"):
            parse_native_team_stats(s,MID,HOME,AWAY)
    def test_duplicate_stats_key_fails(self):
        s=stats();s["data"]["periods"][0]["groups"][0]["items"].append(
            {"key":"expected_goals","home":"0.4","away":"0.75","format_type":"double"})
        with self.assertRaisesRegex(SemanticAuditError,"NOT_UNIQUE"):
            parse_native_team_stats(s,MID,HOME,AWAY)
    def test_first_half_stat_cannot_replace_all(self):
        s=stats();s["data"]["periods"][0]["period"]="First"
        with self.assertRaisesRegex(SemanticAuditError,"PERIOD_NOT_UNIQUE"):
            parse_native_team_stats(s,MID,HOME,AWAY)
    def test_wrong_shot_team_fails(self):
        s=shots();s["data"]["periods"][0]["shots"][0]["team_id"]="t_Zz1234"
        with self.assertRaisesRegex(SemanticAuditError,"SHOT_WRONG_TEAM"):
            parse_native_shots(s,MID,HOME,AWAY)
    def test_duplicate_shot_id_blocks_double_count(self):
        s=shots();s["data"]["periods"][0]["shots"].append(
            copy.deepcopy(s["data"]["periods"][0]["shots"][0]))
        with self.assertRaisesRegex(SemanticAuditError,"DUPLICATE"):
            parse_native_shots(s,MID,HOME,AWAY)
    def test_nan_and_bool_and_missing_never_zero(self):
        for val in (float("nan"),True,None):
            s=shots();s["data"]["periods"][0]["shots"][0]["expected_goals"]=val
            with self.assertRaises(SemanticAuditError):
                parse_native_shots(s,MID,HOME,AWAY)
    def test_zero_shots_not_automatically_zero_xg(self):
        s=shots();s["data"]["periods"]=[{"period":"All","shots":[]}]
        with self.assertRaisesRegex(SemanticAuditError,"EMPTY"):
            parse_native_shots(s,MID,HOME,AWAY)
    def test_exact_fpl_side_match_only(self):
        r=side_comparison(match_id=MID,home_id=HOME,away_id=AWAY,
            source_shots=shots(),source_stats=stats(),
            fpl_side_values={(101,1):0.4,(101,2):1.10},
            public_fixture_id=101,fpl_home_id=1,fpl_away_id=2)
        a=aggregate(r)
        self.assertEqual(a["exact_matched_team_sides"],2)
        self.assertEqual(a["PITCH_SHOTS_XG_vs_PITCH_FULL_MATCH_STATS_XG"]["within_0_02"],2)
        self.assertEqual(a["FPL_OPTA_PLAYER_SUM_XG_vs_PITCH_FULL_MATCH_STATS_XG"]["over_0_25"],1)
        self.assertFalse(a["equivalence_of_provider_xg_definitions_proven"])
    def test_wrong_fpl_team_or_match_never_pair(self):
        with self.assertRaisesRegex(SemanticAuditError,"NO_FPL"):
            side_comparison(match_id=MID,home_id=HOME,away_id=AWAY,
                source_shots=shots(),source_stats=stats(),
                fpl_side_values={(101,1):0.4,(101,2):1.10},
                public_fixture_id=102,fpl_home_id=1,fpl_away_id=2)
    def test_missing_provider_first_publication_always_blocked(self):
        for r in ({},{"captured_at_utc":"2026-10-28T10:00:00Z"},
                  {"provider_original_publication_evidence_verified":True}):
            result=classify_historical_publication(r,target_cutoff_utc="2024-09-01T00:00:00Z")
            self.assertFalse(result["pit_eligible"])
    def test_retro_observations_never_train(self):
        r=side_comparison(match_id=MID,home_id=HOME,away_id=AWAY,
            source_shots=shots(),source_stats=stats(),
            fpl_side_values={(101,1):.4,(101,2):.75},
            public_fixture_id=101,fpl_home_id=1,fpl_away_id=2)
        a=aggregate(r)
        self.assertFalse(a["training_allowed"])
        self.assertFalse(a["historical_PitchAPI_first_publication_proven"])
        self.assertNotIn(MID,str(a))
        self.assertNotIn("xg_for",str(a))
if __name__=="__main__":unittest.main()
