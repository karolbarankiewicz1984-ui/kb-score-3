"""Check executable workflow boundaries: no automatic fit, API or DB rebase."""
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]

def workflow(name):
    return yaml.load((ROOT/".github/workflows"/name).read_text(),Loader=yaml.BaseLoader)

class WorkflowSafetyTests(unittest.TestCase):
    def test_all_three_league_writers_share_lock_and_refuse_binary_rebase(self):
        names=("kb3-pitchapi-three-league-daily.yml","kb3-m0-one-time-initial-freeze.yml",
               "kb3-m0-real-postmatch-calibration.yml","kb3-m0-shadow-initial-1x2.yml")
        groups=set()
        for name in names:
            w=workflow(name);groups.add(w["concurrency"]["group"])
            self.assertEqual(w["concurrency"]["cancel-in-progress"],"false")
            text=(ROOT/".github/workflows"/name).read_text()
            self.assertNotIn("--rebase",text)
            self.assertNotIn("--force",text)
            self.assertIn("git push origin HEAD:main",text)
        self.assertEqual(len(groups),1)

    def test_m1r_fit_only_after_explicit_manual_input_with_unique_outputs(self):
        w=workflow("kb3-step14-m1r-catboost720-eval374.yml")
        self.assertEqual(w["permissions"],{"contents":"read"})
        self.assertEqual(w["on"]["workflow_dispatch"]["inputs"]["confirm_research_fit"]["default"],"false")
        job=w["jobs"]["independent-research-m1r-catboost"]
        self.assertEqual(job["if"],"github.event_name == 'workflow_dispatch' && inputs.confirm_research_fit == true")
        runs="\n".join(x.get("run","") for x in job["steps"])
        self.assertIn("${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}",runs)
        self.assertNotIn("git push",runs)
        self.assertNotIn("--model models/",runs)

    def test_m1r_automatic_validation_has_no_secret_or_fit(self):
        w=workflow("kb3-step14-m1r-catboost720-eval374.yml")
        steps=w["jobs"]["offline-validation"]["steps"]
        text=str(steps)
        self.assertNotIn("secrets.",text)
        self.assertNotIn("--summary",text)
        self.assertNotIn("PITCHAPI_API_KEY",text)
        self.assertIn("unittest discover",text)

    def test_full_regression_covers_shared_modules_without_provider_secrets(self):
        w=workflow("kb3-codex-offline-regression.yml")
        self.assertEqual(w["permissions"],{"contents":"read"})
        for trigger in ("pull_request","push"):
            for scope in ("src/**","scripts/**","tests/**","migrations/**"):
                self.assertIn(scope,w["on"][trigger]["paths"])
        self.assertNotIn("secrets.",str(w))
        self.assertNotIn("schedule",w["on"])
        self.assertIn("test_codex_offline.py",str(w))

if __name__=="__main__":unittest.main()
