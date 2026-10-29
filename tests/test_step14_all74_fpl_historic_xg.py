import unittest,csv,io
from scripts.step14_inventory_all_74_historic_fpl_revisions_xg import REVISIONS,_player_agg

class All74FPLHistoricalXGAuditTests(unittest.TestCase):
    def test_all_74_are_distinct_and_pinned(self):
        self.assertEqual((len(REVISIONS["2023-24"]),len(REVISIONS["2024-25"])),(38,36))
        self.assertEqual(len(set(REVISIONS["2023-24"]+REVISIONS["2024-25"])),74)
    def test_old_player_xg_exact_fixture_opponent_and_11_players_required(self):
        fixtures=[{"id":"10","team_h":"1","team_a":"2","finished":"True"}]
        rows=[]
        for tid in range(11):
            rows.append({"fixture":"10","element":str(100+tid),"opponent_team":"2",
                         "was_home":"True","expected_goals":"0.1","minutes":"90"})
        for tid in range(11):
            rows.append({"fixture":"10","element":str(200+tid),"opponent_team":"1",
                         "was_home":"False","expected_goals":"0.2","minutes":"90"})
        fp=io.StringIO()
        writer=csv.DictWriter(fp,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        audit,tot=_player_agg(fp.getvalue().encode(),fixtures)
        self.assertEqual(audit["all_xg_rows_strict_validation"],"PASS")
        self.assertEqual(audit["side_records_valid_at_least_11_played"],2)
        self.assertAlmostEqual(tot[("10","1")],1.1,places=4)
        self.assertAlmostEqual(tot[("10","2")],2.2,places=4)
    def test_unknown_or_duplicate_player_invalidates_entire_xg_source(self):
        fixtures=[{"id":"10","team_h":"1","team_a":"2","finished":"True"}]
        x=("fixture,element,opponent_team,was_home,expected_goals,minutes\n"
           "10,1,2,True,0.3,90\n10,1,2,True,0.3,90\n")
        audit,values=_player_agg(x.encode(),fixtures)
        self.assertGreater(audit["invalid_rows"],0)
        self.assertEqual(values,{})
    def test_unplayed_target_player_xg_is_not_accepted(self):
        fixtures=[{"id":"10","team_h":"1","team_a":"2","finished":"False"}]
        x=("fixture,element,opponent_team,was_home,expected_goals,minutes\n10,1,2,True,0.3,90\n")
        audit,values=_player_agg(x.encode(),fixtures)
        self.assertGreater(audit["invalid_rows"],0)
        self.assertEqual(values,{})
if __name__=="__main__":unittest.main()
