import unittest,sqlite3,tempfile
from pathlib import Path
from src.kb3_step19_odds_research import validate,freeze,no_vig_complete
CUTOFF="2026-11-01T13:00:00Z"
def quote(side,price="2.40",market="1X2",line=None):
 return {"country":"POL","fixture_provider":"PitchAPI","native_match_id":"m_SYNTHETIC",
   "bookmaker":"EXAMPLE_NOT_REAL","market":market,"selection":side,"line":line,
   "price_decimal":price,"source_sha256":"a"*64,
   "captured_at_utc":"2026-11-01T12:00:00Z","kickoff_utc":"2026-11-01T20:00:00Z",
   "provider_published_at_utc":None}
class OddsTests(unittest.TestCase):
 def test_immutable_idempotent_full_group(self):
    with tempfile.TemporaryDirectory() as td:
      db=Path(td)/"research.sqlite"
      items=[quote("1","2.4"),quote("X","3.1"),quote("2","3.3")]
      self.assertEqual(freeze(db,items,observed_cutoff=CUTOFF)["new_quotes"],3)
      self.assertEqual(freeze(db,items,observed_cutoff=CUTOFF)["new_quotes"],0)
      with sqlite3.connect(db) as c:
        sid=c.execute("SELECT snapshot_sha256 FROM step19_research_quotes LIMIT 1").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
          c.execute("UPDATE step19_research_quotes SET price_decimal='10'")
        with self.assertRaises(sqlite3.IntegrityError):
          c.execute("DELETE FROM step19_research_quotes")
      result=no_vig_complete(db,sid)
      self.assertAlmostEqual(sum(result["no_vig_probabilities"].values()),1.0)
      self.assertTrue(result["ROI_not_estimated"])
 def test_incomplete_group_does_not_make_no_vig(self):
    with tempfile.TemporaryDirectory() as td:
      db=Path(td)/"research.sqlite"
      freeze(db,[quote("1")],observed_cutoff=CUTOFF)
      with sqlite3.connect(db) as c:
        sid=c.execute("SELECT snapshot_sha256 FROM step19_research_quotes").fetchone()[0]
      self.assertIsNone(no_vig_complete(db,sid))
 def test_prematch_and_protected_test(self):
    late=quote("1");late["captured_at_utc"]="2026-11-01T19:45:00Z"
    with self.assertRaisesRegex(ValueError,"EARLY_PREMATCH"):
      validate(late,observed_cutoff="2026-11-01T19:55:00Z")
    eng=quote("1");eng["country"]="ENG"
    with self.assertRaisesRegex(ValueError,"ENGLISH_TEST"):validate(eng,observed_cutoff=CUTOFF)
 def test_lines_and_fake_publication(self):
    with self.assertRaisesRegex(ValueError,"NOT_ALLOWED"):
      validate(quote("1",line=2),observed_cutoff=CUTOFF)
    with self.assertRaisesRegex(ValueError,"NOT_QUARTER"):
      validate(quote("OVER",market="TOTAL",line=2.3),observed_cutoff=CUTOFF)
    bad=quote("1");bad["provider_published_at_utc"]="2026-11-01T11:00:00Z"
    with self.assertRaisesRegex(ValueError,"PUBLICATION"):
      validate(bad,observed_cutoff=CUTOFF)
 def test_asian_handicap_no_vig_requires_reciprocal_line_audit(self):
    with tempfile.TemporaryDirectory() as td:
      db=Path(td)/"research.sqlite"
      freeze(db,[quote("HOME",market="AH",line=-1),
                 quote("AWAY",market="AH",line=-1)],observed_cutoff=CUTOFF)
      with sqlite3.connect(db) as c:
        sid=c.execute("SELECT snapshot_sha256 FROM step19_research_quotes").fetchone()[0]
      self.assertIsNone(no_vig_complete(db,sid))
 def test_conflicting_quote_for_same_source_side_fails(self):
    with tempfile.TemporaryDirectory() as td:
      with self.assertRaises(sqlite3.IntegrityError):
        freeze(Path(td)/"research.sqlite",[quote("1","2.4"),quote("1","2.2")],
              observed_cutoff=CUTOFF)
if __name__=="__main__":unittest.main()
