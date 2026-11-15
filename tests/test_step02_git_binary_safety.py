"""Offline guard: no binary SQLite auto-rebase or accidental provider calls."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/kb3-step16-m0-720-eight-forward.yml"

class Step02PublicationSafety(unittest.TestCase):
    def test_failed_binary_push_does_not_rebase_and_reforecast(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("git pull --rebase",text)
        self.assertIn("if ! git push origin HEAD:main; then",text)
        # Only entirely new, non-colliding receipts may survive a push race.
        # Binary SQLite, forecast changes and rewritten ledger evidence still
        # fail closed and preserve the original Action artifact.
        self.assertIn("M0_RESEARCH_BINARY_OR_FORECAST_CHANGED_NO_REBASE",text)
        self.assertIn("M0_RESEARCH_NOT_APPEND_ONLY_NO_REBASE",text)
        self.assertIn("M0_RESEARCH_RECEIPT_PATH_ALREADY_EXISTS_NO_REBASE",text)
        self.assertIn("git cat-file -e \\"origin/main:$path\\"",text)
        self.assertIn("git rebase origin/main",text)
        self.assertIn("M0_RESEARCH_PUSH_REJECTED_KEEP_ORIGINAL_ARTIFACT",text)
        self.assertIn("exit 1",text)

    def test_source_evidence_uploaded_even_on_failed_live_run(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("if: always() && steps.mode.outputs.mode != 'skip'",text)
        self.assertIn("data/pit_sidecar/m0_720_eight/",text)
        self.assertIn("data/forward_m0_720_eight/",text)

    def test_live_job_explicitly_excluded_on_pull_request(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",text)
        self.assertIn("python -m scripts.step16_m0_mode_guard",text)

if __name__=="__main__":unittest.main()
