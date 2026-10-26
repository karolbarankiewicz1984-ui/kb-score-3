import copy
import unittest
from scripts.step10_phase_resolution import classify

def season(n=18):
    data=[]
    fid=10000
    for home in range(1,n+1):
        for away in range(1,n+1):
            if home==away:continue
            data.append({"league":{"id":78,"season":2024,"round":"Regular Season - 1"},
              "fixture":{"id":fid,"status":{"short":"FT"}},
              "teams":{"home":{"id":home},"away":{"id":away}}})
            fid+=1
    extra=copy.deepcopy(data[0])
    extra["fixture"]["id"]=fid
    extra["league"]["round"]="Relegation Play-offs - Final"
    data.append(extra)
    return data

class PhaseResolutionTest(unittest.TestCase):
    def test_quarantine_real_playoff_but_accept_306_regular(self):
        r=classify(season(),league=78,year=2024)
        self.assertEqual(r["errors"],[])
        self.assertEqual((r["domestic_regular_fixtures"],r["total_fixture_rows"]),(306,307))
        self.assertEqual(len(r["extra_phases_excluded_from_domestic_training"]),1)

    def test_unknown_extra_phase_rejected(self):
        data=season()
        data[-1]["league"]["round"]="Unverified Round XYZ"
        self.assertIn("UNKNOWN_NONREGULAR_PHASE_MUST_REVIEW",
                      classify(data,league=78,year=2024)["errors"])

    def test_duplicate_regular_fixture_rejected(self):
        data=season()
        data[-1]["league"]["round"]="Regular Season - 1"
        r=classify(data,league=78,year=2024)
        self.assertIn("DUPLICATE_DIRECTED_DOMESTIC_FIXTURE",r["errors"])

    def test_missing_fixture_rejected(self):
        data=season()
        data.pop(50)
        self.assertIn("DOMESTIC_SCHEDULE_INCOMPLETE",
                      classify(data,league=78,year=2024)["errors"])

    def test_missing_outcome_rejected(self):
        data=season()
        data[0]["fixture"]["status"]["short"]="NS"
        self.assertIn("UNFINISHED_DOMESTIC_REGULAR_SEASON_MATCH",
                      classify(data,league=78,year=2024)["errors"])

if __name__=="__main__":
    unittest.main()
