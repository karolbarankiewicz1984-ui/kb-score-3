import unittest
from scripts.step14_validation_2025_fpl_historic_source_harvest import audit,CANDIDATES
class FPL2025RealEvidenceTests(unittest.TestCase):
 def test_scope(self):
    self.assertEqual(len(CANDIDATES),5)
    self.assertEqual(sum(x[0]=="2025-26" for x in CANDIDATES),4)
 def test_no_origin_clock_no_approval(self):
    r=audit(probe=lambda c:{"season":c[0],"commit":c[4],"verified_publication":False})
    self.assertEqual(r["independently_verified_sources"],[])
    self.assertFalse(r["training_allowed"])
if __name__=="__main__":unittest.main()
