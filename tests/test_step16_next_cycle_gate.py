"""Postfix watcher must never mark old proof as a new real cycle."""
import json,tempfile,unittest
from pathlib import Path
from scripts.step16_next_cycle_gate import after_merge_run
class NextCycleTests(unittest.TestCase):
 def test_old_receipt_does_not_meet_new_release_gate(self):
    with tempfile.TemporaryDirectory() as root:
      f=Path(root)/"old.json"
      f.write_text(json.dumps({"run_utc":"2026-11-01T20:22:12Z"}))
      self.assertEqual(after_merge_run([f],"2026-11-01T20:23:03Z","run_utc"),[])
 def test_newer_receipt_detected(self):
    with tempfile.TemporaryDirectory() as root:
      f=Path(root)/"new.json"
      f.write_text(json.dumps({"run_utc":"2026-11-02T06:22:00Z"}))
      found=after_merge_run([f],"2026-11-01T20:23:03Z","run_utc")
      self.assertEqual(len(found),1)
if __name__=="__main__":unittest.main()
