import unittest
from scripts.step14_2024_fpl_independent_history_harvest import CANDIDATES,audit
class OldFPL2024(unittest.TestCase):
 def test_six_old_fpl_2024_candidate_commits(self):
    self.assertEqual(len(CANDIDATES),6)
    self.assertTrue(all(x[0]=="2024-25" and x[1]=="FPL" for x in CANDIDATES))
 def test_no_history_clock_cannot_be_proven(self):
    r=audit(probe=lambda c:{"season":c[0],"commit":c[4],"verified_publication":False,
       "independent_publication_UTC":None,"state":"NO_SERVER_EVENT"})
    self.assertEqual(r["independently_server_published_source_count"],0)
    self.assertFalse(r["original_M1_train_allowed"])
if __name__=="__main__":unittest.main()
