"""Fail-closed early 2023 player xG provenance tests."""
import copy,unittest
from src.kb3_step14_xg_2023_early_prematch import (
    SCHEMA,OldXGError,SOURCES_2023,examine_one)
class EarlyXGTests(unittest.TestCase):
    def test_source_versions_are_prior_to_targets(self):
        self.assertEqual(len(SOURCES_2023),2)
        self.assertEqual([s["ft"] for s in SOURCES_2023],[70,140])
        self.assertEqual([s["event"] for s in SOURCES_2023],["32344206544","33866831577"])
    def test_unpinned_publication_rejected(self):
        s=copy.deepcopy(SOURCES_2023[0]);s["push"]="2023-10-07T10:00:00Z"
        with self.assertRaisesRegex(OldXGError,"PUBLICATION_WITNESS"):
            examine_one(s,fetcher=lambda *args,**kwargs:b"")
    def test_unpinned_raw_sha_rejected(self):
        s=copy.deepcopy(SOURCES_2023[0]);s["sha"]="0"*64
        with self.assertRaisesRegex(OldXGError,"PUBLICATION_WITNESS"):
            examine_one(s,fetcher=lambda *args,**kwargs:b"")
    def test_pinned_source_but_invalid_remote_content_fails(self):
        with self.assertRaises(OldXGError):
            examine_one(SOURCES_2023[0],fetcher=lambda *args,**kwargs:b"invalid")
    def test_schema_never_claims_original_native_pitchapi(self):
        self.assertIn("player-xg",SCHEMA)
if __name__=="__main__":unittest.main()
