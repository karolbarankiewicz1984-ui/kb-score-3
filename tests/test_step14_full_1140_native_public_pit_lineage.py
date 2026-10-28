import copy,json,unittest
from pathlib import Path
from scripts.step14_full_1140_native_public_pit_lineage import (
 independently_pinned_sources,exact_source_map,old_source_rows,ReconstructError,
 native_three_seasons,all_1140_pit)
ROOT=Path(__file__).resolve().parents[1]
class RealHistoryProofTests(unittest.TestCase):
 def test_nine_independent_old_source_receipts(self):
    s=independently_pinned_sources()
    self.assertEqual(len(s),9)
    self.assertEqual([x["ft"] for x in s if x["season"]=="2023-24"],[59,70,140,208,250,313,380])
 def test_no_backdated_old_source_clock(self):
    s=independently_pinned_sources()
    self.assertEqual([x["season"] for x in s].count("2025-26"),1)
    self.assertEqual([x["ft"] for x in s if x["season"]=="2025-26"],[0])
 def test_separate_source_clocks_and_no_assumed_train(self):
    s=independently_pinned_sources()
    self.assertTrue(all(x["push"].endswith("Z") for x in s))
    self.assertEqual(len({x["commit"] for x in s}),9)
 def test_public_to_native_exact_id_not_name_fuzzy(self):
    src={"season":"2024-25","push":"2024-10-02T13:52:44Z"}
    native={"2024-25":[
      {"id":"m_012345","time_utc":"2024-10-05T16:30:00Z",
       "home_team":{"id":"t_012345","name":"Everton FC"},
       "away_team":{"id":"t_654321","name":"Newcastle United FC"}}]}
    p=[{"home":"everton","away":"newcastle united",
        "utc":"2024-10-05T16:30:00Z","finished":False,"source_fixture_id":None}]
    m,miss=exact_source_map(src,p,native,{})
    self.assertEqual((len(m),miss),(1,0))
    p[0]["utc"]="2024-10-05T15:30:00Z"
    m,miss=exact_source_map(src,p,native,{})
    self.assertEqual((len(m),miss),(0,1))
 def test_wrong_2024_team_pair_never_approves(self):
    src={"season":"2024-25"}
    native={"2024-25":[{"id":"m_012345","time_utc":"2024-10-05T16:30:00Z",
       "home_team":{"id":"t_012345","name":"Everton FC"},
       "away_team":{"id":"t_654321","name":"Newcastle United FC"}}]}
    p=[{"home":"everton","away":"liverpool","utc":"2024-10-05T16:30:00Z",
        "finished":False,"source_fixture_id":None}]
    self.assertEqual(exact_source_map(src,p,native,{})[1],1)
 def test_missing_secret_bounded(self):
    with self.assertRaisesRegex(ReconstructError,"KEY_MISSING"):
        native_three_seasons(key="")
 def test_corrupted_independent_archive_json_fails(self):
    from scripts import step14_full_1140_native_public_pit_lineage as mod
    old=mod.NEW_2023_PROOF
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"bad.json"
        d=json.loads(old.read_text())
        d["verified_sources"][0]["ft"]=1
        p.write_text(json.dumps(d))
        mod.NEW_2023_PROOF=p
        try:
            with self.assertRaisesRegex(ReconstructError,"NOT_PINNED"):
                independently_pinned_sources()
        finally:mod.NEW_2023_PROOF=old
if __name__=="__main__":unittest.main()
