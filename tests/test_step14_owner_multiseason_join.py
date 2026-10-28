"""Trusted-local mapping: synthetic exact 20-team fingerprints, no private archive."""
import unittest
from datetime import datetime,timezone
from scripts.step14_multiseason_owner_native_join_local import (
    map_fpl_team_ids_by_finished_clock,PrivateJoinError,ADDITIONAL_2023
)

def synthetic():
    rows=[];native={}
    for i in range(10):
        kickoff=f"2023-09-{i+1:02d}T17:00:00Z"
        h=str(i*2+1);a=str(i*2+2)
        rows.append({"id":str(i),"team_h":h,"team_a":a,
             "kickoff_time":kickoff,"finished":"True",
             "team_h_score":"1.0","team_a_score":"0.0"})
        native[f"m_{i:06d}"]={
            "season":"2023-24","kickoff_utc":kickoff,
            "home_id":f"t_{i*2+1:06d}","away_id":f"t_{i*2+2:06d}",
            "home_name":f"Club{i*2+1}","away_name":f"Club{i*2+2}"}
    return rows,native

class OwnerMappingTests(unittest.TestCase):
    def test_exact_twenty_team_fingerprint_reconstructs_names_without_scores(self):
        rows,native=synthetic()
        mapping=map_fpl_team_ids_by_finished_clock(rows,native,
                    season="2023-24",published_at="2023-10-05T14:38:59Z",
                    expected_finished=10)
        self.assertEqual(len(mapping),20)
        self.assertEqual(len(set(mapping.values())),20)
    def test_one_wrong_kickoff_blocks_all_map(self):
        rows,native=synthetic()
        rows[0]["kickoff_time"]="2023-09-01T18:00:00Z"
        with self.assertRaisesRegex(PrivateJoinError,"INCOMPLETE_OR_AMBIGUOUS"):
            map_fpl_team_ids_by_finished_clock(rows,native,
                 season="2023-24",published_at="2023-10-05T14:38:59Z",
                 expected_finished=10)
    def test_one_wrong_team_direction_blocks_all_map(self):
        rows,native=synthetic()
        # Two meetings for the same two teams make a contradictory swapped
        # orientation detectable; one anonymous game alone is symmetric.
        second={"id":"extra","team_h":"1","team_a":"2",
              "kickoff_time":"2023-09-21T17:00:00Z",
              "finished":"True","team_h_score":"1.0","team_a_score":"0.0"}
        rows.append(second)
        native["m_999999"]={"season":"2023-24",
            "kickoff_utc":"2023-09-21T17:00:00Z",
            "home_id":"t_000001","away_id":"t_000002",
            "home_name":"Club1","away_name":"Club2"}
        rows[0]["team_h"],rows[0]["team_a"]=rows[0]["team_a"],rows[0]["team_h"]
        with self.assertRaisesRegex(PrivateJoinError,"INCOMPLETE_OR_AMBIGUOUS"):
            map_fpl_team_ids_by_finished_clock(rows,native,
                 season="2023-24",published_at="2023-10-05T14:38:59Z",
                 expected_finished=11)
    def test_retrospective_relabeling_cannot_complete_history(self):
        rows,native=synthetic()
        native[next(iter(native))]["kickoff_utc"]="2023-11-01T17:00:00Z"
        with self.assertRaisesRegex(PrivateJoinError,"PUBLIC_VS_NATIVE_PRIOR"):
            map_fpl_team_ids_by_finished_clock(rows,native,
                 season="2023-24",published_at="2023-10-05T14:38:59Z",
                 expected_finished=10)
    def test_2023_december_extra_source_pin(self):
        self.assertEqual(ADDITIONAL_2023["event"],"33866831577")
        self.assertEqual(len(ADDITIONAL_2023["sha"]),64)
        self.assertEqual(ADDITIONAL_2023["ft"],140)

if __name__=="__main__":unittest.main()
