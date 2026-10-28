"""Negative controls on xG: fixture/team/side/published_at/definition."""
import csv,io,hashlib,unittest
from src.kb3_step14_xg_four_gates import extract_public_xg,before_target,XGFourGateError,METHOD

def csv_bytes(rows,fields):
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields);w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf8")
def samples():
    fixtures=csv_bytes([dict(id="11",team_h="1",team_a="2",
            kickoff_time="2023-08-12T14:00:00Z",finished="True")],
            ("id","team_h","team_a","kickoff_time","finished"))
    players=csv_bytes([
        dict(fixture="11",opponent_team="2",was_home="True",team="Alpha",
             element="101",expected_goals="1.2"),
        dict(fixture="11",opponent_team="1",was_home="False",team="Beta",
             element="202",expected_goals="0.4")],
        ("fixture","opponent_team","was_home","team","element","expected_goals"))
    return fixtures,players
def audit(f,p):
    return extract_public_xg(f,p,published_at="2024-05-27T18:05:12Z",
             pinned_fixture_sha=hashlib.sha256(f).hexdigest(),
             pinned_player_sha=hashlib.sha256(p).hexdigest(),
             require_full_grid=False)

class FourGateTests(unittest.TestCase):
    def test_same_fixture_both_teams_and_source_clock(self):
        f,p=samples();s=audit(f,p)
        self.assertEqual(s["fixtures_with_both_sides_player_xg"],1)
        self.assertEqual(s["source_side_xg_values_IN_MEMORY_ONLY"][(11,1)],1.2)
        self.assertEqual(s["source_side_xg_values_IN_MEMORY_ONLY"][(11,2)],0.4)
        self.assertTrue(before_target(prior_fixture=11,prior_team=1,src=s,
              cutoff="2024-10-01T19:00:00Z",target_kickoff="2024-10-02T15:00:00Z"))
    def test_wrong_fixture_never_borrow_nearest(self):
        _,p=samples();f,p=samples();s=audit(f,p)
        with self.assertRaisesRegex(XGFourGateError,"FIXTURE"):
            before_target(prior_fixture=12,prior_team=1,src=s,
                 cutoff="2024-10-01T19:00:00Z",target_kickoff="2024-10-02T15:00:00Z")
    def test_wrong_team_never_credited(self):
        f,p=samples();s=audit(f,p)
        with self.assertRaisesRegex(XGFourGateError,"PARTICIPANT"):
            before_target(prior_fixture=11,prior_team=3,src=s,
              cutoff="2024-10-01T19:00:00Z",target_kickoff="2024-10-02T15:00:00Z")
    def test_wrong_opponent_side_is_fatal(self):
        f,p=samples();p=p.replace(b"11,2,True",b"11,1,True")
        with self.assertRaisesRegex(XGFourGateError,"WRONG_OPPONENT"):
            audit(f,p)
    def test_wrong_venue_flag_fatal(self):
        f,p=samples();p=p.replace(b"11,2,True",b"11,2,Unknown")
        with self.assertRaisesRegex(XGFourGateError,"UNKNOWN_FPL_VENUE"):
            audit(f,p)
    def test_duplicate_player_fixture_rejected_not_double_sum(self):
        f,p=samples();lines=p.decode().splitlines()
        p=("\n".join(lines+[lines[1]])+"\n").encode()
        with self.assertRaisesRegex(XGFourGateError,"DUPLICATE_PLAYER"):
            audit(f,p)
    def test_duplicated_fixture_rejected(self):
        f,p=samples();line=f.decode().splitlines()
        f=("\n".join(line+[line[1]])+"\n").encode()
        with self.assertRaisesRegex(XGFourGateError,"DUPLICATE_OR_INVALID_FIXTURE"):
            audit(f,p)
    def test_old_source_after_target_cutoff_rejected(self):
        f,p=samples();s=audit(f,p)
        with self.assertRaisesRegex(XGFourGateError,"PUBLIC_BEFORE"):
            before_target(prior_fixture=11,prior_team=1,src=s,
                 cutoff="2024-05-01T19:00:00Z",target_kickoff="2024-05-19T15:00:00Z")
    def test_future_publication_not_before_target(self):
        f,p=samples();s=audit(f,p)
        with self.assertRaisesRegex(XGFourGateError,"PUBLIC_BEFORE"):
            before_target(prior_fixture=11,prior_team=1,src=s,
                 cutoff="2024-06-01T20:00:00Z",target_kickoff="2024-05-19T15:00:00Z")
    def test_wrong_semantics_understat_or_pitchapi_not_equivalent(self):
        f,p=samples();s=audit(f,p)
        with self.assertRaisesRegex(XGFourGateError,"SEMANTICS"):
            before_target(prior_fixture=11,prior_team=1,src=s,
                 cutoff="2024-10-01T19:00:00Z",target_kickoff="2024-10-02T15:00:00Z",
                 definition="PITCHAPI_TEAM_MATCH_XG")
    def test_wrong_raw_hash_rejected(self):
        f,p=samples()
        with self.assertRaisesRegex(XGFourGateError,"HASH_MISMATCH"):
            extract_public_xg(f,p,published_at="2024-05-27T18:05:12Z",
                pinned_fixture_sha="0"*64,pinned_player_sha=hashlib.sha256(p).hexdigest(),
                require_full_grid=False)
    def test_nonfinite_negative_missing_xg_rejected(self):
        for v in (b"nan",b"-0.1",b""):
            f,p=samples();p=p.replace(b"1.2",v,1)
            with self.assertRaises(XGFourGateError):audit(f,p)
    def test_missing_team_field_rejected(self):
        f,p=samples();p=p.replace(b"team",b"club",1)
        with self.assertRaisesRegex(XGFourGateError,"SCHEMA"):
            audit(f,p)
    def test_team_label_collision_rejected(self):
        f,p=samples();p=p.replace(b"Beta",b"Alpha")
        with self.assertRaisesRegex(XGFourGateError,"AMBIGUOUS"):
            audit(f,p)
    def test_xga_not_derived_from_repeated_player_expected_conceded(self):
        self.assertEqual(METHOD,"FPL_OPTA_PLAYER_SHOT_XG_SUM_BY_ORIGINAL_FIXTURE_SIDE")
if __name__=="__main__":unittest.main()
