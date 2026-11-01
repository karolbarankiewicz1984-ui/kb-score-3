import unittest,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from scripts.step16_m0_mode_guard import select,FORECAST_CRONS,SETTLE_CRONS
NOW=datetime(2026,11,1,13,0,tzinfo=timezone.utc)
class Step16ModeSafety(unittest.TestCase):
    def fixtures(self,root,freeze=False,settle=None):
        if freeze:
            p=Path(root)/"data/forecasts/m0_720_eight"/"2026-11-01"
            p.mkdir(parents=True);(p/"FROZEN_M0_720_EIGHT.json").write_text("{}")
        if settle:
            day=Path(root)/"data/pit_sidecar/m0_720_eight"/"2026-11-01"/("settle-"+settle)
            day.mkdir(parents=True);(day/"RECEIPT.json").write_text("{}")
    def mode(self,root,event="schedule",cron=None,user_mode="",now=NOW):
        return select(event=event,cron=cron or FORECAST_CRONS[0],
                      user_mode=user_mode,now=now,root=root)[0]
    def test_forecast_recovery_if_missing(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.mode(root),"forecast")
            self.fixtures(root,freeze=True)
            self.assertEqual(self.mode(root),"skip")
    def test_settlement_recovery_if_stale(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixtures(root,freeze=True,settle="060000000111")
            self.assertEqual(self.mode(root,cron=SETTLE_CRONS[0]),"skip")
            self.assertEqual(self.mode(root,cron=SETTLE_CRONS[0],now=NOW+timedelta(hours=2)),"settle")
    def test_push_avoids_spurious_paid_calls(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixtures(root,freeze=True,settle="120000001234")
            self.assertEqual(self.mode(root,event="push"),"skip")
            self.assertEqual(self.mode(root,event="push",now=NOW+timedelta(hours=10)),"settle")
    def test_manual_explicit_settle_remains_possible(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.mode(root,event="workflow_dispatch",user_mode="settle"),"settle")
    def test_early_push_does_not_force_forecast(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.mode(root,event="push",now=NOW.replace(hour=3)),"skip")
    def test_invalid_event_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                self.mode(root,event="pull_request")
if __name__=="__main__":unittest.main()
