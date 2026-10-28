"""Fail-closed schema and historical player xG source tests."""
import csv,io,unittest
from src.kb3_step14_2023_fpl_old_player_xg import inspect,PlayerXGError,SCHEMA

def fixtures():
    fd=io.StringIO()
    wr=csv.DictWriter(fd,fieldnames=["id"])
    wr.writeheader()
    for i in range(380):wr.writerow({"id":i+1})
    return fd.getvalue().encode()

class OldFPLPlayerXGTests(unittest.TestCase):
    def test_only_historical_player_values_never_pitchapi_team_feature(self):
        s=io.StringIO();wr=csv.DictWriter(s,fieldnames=["fixture","team","expected_goals"])
        wr.writeheader()
        for i in range(380):wr.writerow({"fixture":i+1,"team":1,"expected_goals":"0.0"})
        r=inspect(fixtures(),s.getvalue().encode())
        self.assertEqual(r["distinct_FPL_fixture_ids_with_numeric_player_xg"],380)
        self.assertFalse(r["original_pitchapi_team_match_xg_equivalent"])
        self.assertFalse(r["player_xg_each_2023_24_target_prematch_available"])
    def test_no_xg_header_rejected(self):
        with self.assertRaises(PlayerXGError):
            inspect(fixtures(),b"fixture,team,xP\n1,1,2.0\n")
    def test_invalid_xg_rejected(self):
        s="fixture,team,expected_goals\n"+          "".join(f"{i+1},1,0.0\n" for i in range(379))+          "380,1,nan\n"
        with self.assertRaises(PlayerXGError):
            inspect(fixtures(),s.encode())
    def test_no_full_380_grid_fails(self):
        with self.assertRaises(PlayerXGError):
            inspect(b"id\n1\n",b"fixture,team,expected_goals\n1,1,0.1\n")
    def test_version_unchanged(self):
        self.assertIn("player-fixture-xg",SCHEMA)

if __name__=="__main__":unittest.main()
