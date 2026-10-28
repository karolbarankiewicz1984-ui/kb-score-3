"""Unit gates for public-only, in-season Elo (not original cross-season Elo)."""
import copy,unittest
from src.kb3_step14_openfootball_elo_prefix import (
    SCHEMA,PublicEloError,analyze
)
from src.kb3_step14_multiseason_pit import SOURCES

class Isolated2024EloTests(unittest.TestCase):
    def test_wrong_public_blob_sha_fails_closed(self):
        with self.assertRaisesRegex(PublicEloError,"HASH_CHANGED"):
            analyze(b'{"matches":[]}')
    def test_wrong_commit_not_allowed(self):
        copy_source=copy.deepcopy(SOURCES[1])
        copy_source["commit"]="a"*40
        with self.assertRaisesRegex(PublicEloError,"UNVERIFIED_PUBLIC_SOURCE"):
            analyze(b'{"matches":[]}',copy_source)
    def test_new_schema_never_claims_m1_train(self):
        self.assertEqual(SCHEMA,"kb3-step14-2024-public-only-within-season-elo-prefix-v1")
        self.assertNotIn("production",SCHEMA)

if __name__=="__main__":unittest.main()
