"""Regression guard: never spend API-Football requests on normal push/PR."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/kb3-step11-features.yml"

class LegacyCostGuardTests(unittest.TestCase):
    def setUp(self):
        self.code=WORKFLOW.read_text(encoding="utf8")

    def test_both_legacy_network_pilots_manual_only(self):
        for name in ("pilot-380","pilot-760"):
            expression=rf"(?m)^  {name}:\n    if: github\.event_name == 'workflow_dispatch'\n"
            self.assertRegex(self.code,expression,name)

    def test_everyday_push_and_pr_keep_offline_tests(self):
        self.assertIn('  offline-tests:\n',self.code)
        self.assertIn('python -m unittest discover -s tests',self.code)
        self.assertIn('  workflow_dispatch:\n',self.code)
        self.assertIn('  pull_request:\n',self.code)
        self.assertIn('    branches: ["feature/step11-*", "main"]',self.code)

    def test_no_non_manual_legacy_condition(self):
        self.assertNotIn("github.event_name != 'pull_request'",self.code)
        self.assertEqual(self.code.count("if: github.event_name == 'workflow_dispatch'"),2)

if __name__=="__main__":
    unittest.main()
