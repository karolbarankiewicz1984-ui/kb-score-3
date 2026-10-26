"""Step11 xG readiness selection tests, no provider calls."""
import unittest
from scripts.step11_xg_readiness import select_completed

def match(i, status="finished"):
    return {"id":f"m_{i:06d}","status":status,
            "time_utc":f"2024-09-{i+1:02d}T14:00:00Z",
            "home_team":{"id":1,"name":"Alpha"},"away_team":{"id":2,"name":"Beta"}}

class XgReadinessTests(unittest.TestCase):
    def test_sample_is_deterministic_distinct_and_chronological(self):
        games=[match(i) for i in range(20)]
        a=select_completed(list(reversed(games)),6)
        b=select_completed(games,6)
        self.assertEqual(a,b)
        self.assertEqual(len(a),6)
        self.assertEqual(len(set(x["id"] for x in a)),6)
        self.assertEqual(a[0]["id"],games[0]["id"])
        self.assertEqual(a[-1]["id"],games[-1]["id"])

    def test_unfinished_and_invalid_records_never_sampled(self):
        games=[match(0,"scheduled"),match(1),{"status":"finished"},
               match(3,"cancelled"),match(5)]
        self.assertEqual([m["id"] for m in select_completed(games,3)],
                         [match(1)["id"],match(5)["id"]])

    def test_no_finished_means_empty_not_zero_xg(self):
        self.assertEqual(select_completed([match(1,"live")]),[])
        self.assertEqual(select_completed([]),[])

    def test_invalid_n_is_empty_and_subset_capped(self):
        data=[match(i) for i in range(4)]
        self.assertEqual(select_completed(data,0),[])
        self.assertEqual(len(select_completed(data,10)),4)

if __name__=="__main__":
    unittest.main()
