"""Static guard: Step16 backup schedules and strict cost/mode policy."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
LIVE=ROOT/".github/workflows/kb3-step16-m0-720-eight-forward.yml"
OFFLINE=ROOT/".github/workflows/kb3-step16-offline-readonly-audit.yml"


class WorkflowBudgetSafetyTests(unittest.TestCase):
    def test_backup_crons_and_idempotent_mode_guard(self):
        contents=LIVE.read_text()
        self.assertIn("cron: '21 6,9,12 * * *'",contents)
        self.assertIn("cron: '17 8,14,22 * * *'",contents)
        self.assertEqual(contents.count("cron:"),2)
        self.assertIn("cancel-in-progress: false",contents)
        self.assertIn("needs: anti-leakage-and-data-safety",contents)
        self.assertIn("PITCHAPI_API_KEY:",contents)
        self.assertIn("run: python -m scripts.step16_m0_mode_guard",contents)
        self.assertIn("if: steps.mode.outputs.mode != 'skip'",contents)

    def test_pip_cache_only_and_existing_versions(self):
        contents=LIVE.read_text()
        self.assertEqual(contents.count("cache: 'pip'"),2)
        safety, live_job = contents.split("  real-eighth-league-fitted-M0-shadow:", 1)
        self.assertEqual(safety.count("cache: 'pip'"), 1)
        self.assertEqual(live_job.count("cache: 'pip'"), 1)
        self.assertIn("cache-dependency-path: config/step16_ci_requirements.txt", safety)
        self.assertNotIn("cache-dependency-path: config/step16_live_requirements.txt", safety)
        self.assertIn("cache-dependency-path: config/step16_live_requirements.txt", live_job)
        self.assertNotIn("cache-dependency-path: config/step16_ci_requirements.txt", live_job)
        for key in ("step16_ci","step16_live"):
            p=ROOT/"config"/f"{key}_requirements.txt"
            self.assertTrue(p.is_file())
            self.assertIn(f"config/{key}_requirements.txt",contents)
        ci=(ROOT/"config/step16_ci_requirements.txt").read_text()
        live=(ROOT/"config/step16_live_requirements.txt").read_text()
        self.assertIn("catboost==1.2.8",ci)
        self.assertIn("cryptography>=42,<47",ci)
        self.assertIn("pitchapi==0.1.6",live)
        self.assertIn("catboost==1.2.8",live)
        self.assertNotIn("pitchapi==0.1.6",ci)

    def test_offline_not_on_schedule_or_with_secrets(self):
        contents=OFFLINE.read_text()
        self.assertIn("pull_request:",contents)
        self.assertNotIn("  schedule:",contents)
        self.assertIn("contents: read",contents)
        self.assertNotIn("secrets.",contents)
        self.assertNotIn("pitchapi==",contents)
        self.assertNotIn("catboost==",contents)
        self.assertIn("cryptography>=42,<47",contents)


if __name__=="__main__":
    unittest.main()
