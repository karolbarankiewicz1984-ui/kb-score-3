"""The external 74 revision source cannot be backdated using git commit dates."""
import unittest
from datetime import datetime,timezone
from scripts.step14_fpl74_independent_historic_ancestry import (
    inventory,ProofError,compare_is_ancestor,SCHEMA)
from scripts.step14_fpl74_asof_train_xg_recovery import (
    _candidate_precheck,_last_five,Historic74Error)
from scripts.step14_fpl_core_2025_independent_asof import _utc

class Old74FPLProvablePublicationTests(unittest.TestCase):
    def fakehistory(self):
        return {season:[{"sha":f"{season}-{j}",
                "committer_date_INFORMATIONAL_ONLY":"1900-01-01T00:00:00Z"}
               for j in range(n)] for season,n in (("2023-24",38),("2024-25",36))}
    def test_forged_ancient_committer_date_never_proves_publication(self):
        doc=inventory(revision_override=self.fakehistory(),
          ancestry=lambda cand,anchor:False)
        self.assertEqual(len(doc["fpl_revisions"]),74)
        self.assertEqual(doc["hist_publication_qualified_ancestor_revisions"],0)
        self.assertTrue(all(not x["certified_before_target"] for x in doc["fpl_revisions"]))
        self.assertTrue(doc["committer_time_never_qualifies_as_asof"])
        self.assertFalse(doc["original_M1_train_eligible"])
    def test_verified_git_dag_ancestor_requires_independent_anchor_clock(self):
        h=self.fakehistory()
        doc=inventory(revision_override=h,ancestry=lambda ca,an:True)
        self.assertEqual(doc["hist_publication_qualified_ancestor_revisions"],74)
        self.assertEqual(doc["fpl_revisions"][0]["provenance_kind"],
           "GIT_ANCESTOR_OF_INDEPENDENTLY_CLOCKED_GHARCHIVE_PUSH")
        self.assertTrue(doc["fpl_revisions"][0]["witnessed_public_by_utc"].endswith("Z"))
    def test_simple_prematch_requires_five_finished_precisely_joined_past(self):
        games=[]
        for n in range(5):
            ko=_utc(f"2024-09-{n+5:02d}T12:00:00Z")
            games.extend([
                {"ko":ko,"key":("a",str(n),ko.isoformat()),
                 "home":"a","away":str(n),"native_fixture_id":"a"+str(n)},
                {"ko":ko,"key":("b",str(n),ko.isoformat()),
                 "home":"b","away":str(n),"native_fixture_id":"b"+str(n)}])
        target={"ko":_utc("2024-10-10T15:00:00Z"),
          "home":"a","away":"b","key":("a","b",_utc("2024-10-10T15:00:00Z").isoformat()),
          "native_fixture_id":"target"}
        allrows=games+[target]
        self.assertEqual(len(_last_five(target,allrows,"home")),5)
        past={x["key"]:{"home_goals":1,"away_goals":0} for x in games}
        src={"witness":"2024-10-09T15:00:00Z",
             "schedules":{target["key"]:False},"past":past}
        self.assertTrue(_candidate_precheck(target,allrows,src))
        src["past"].pop(games[0]["key"])
        self.assertFalse(_candidate_precheck(target,allrows,src))
        src["past"]=past
        src["witness"]="2024-10-11T00:00:00Z"
        self.assertFalse(_candidate_precheck(target,allrows,src))

if __name__=="__main__":
    unittest.main()
