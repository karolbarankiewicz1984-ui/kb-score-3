import unittest,tempfile
import json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from scripts.step16_m0_mode_guard import select,FORECAST_CRONS,SETTLE_CRONS
from src.kb3_step16_m0_720_eight_forward import MODEL,hashobj,stamp
NOW=datetime(2026,11,1,13,0,tzinfo=timezone.utc)
class Step16ModeSafety(unittest.TestCase):
    def fixtures(self,root,freeze=False,settle=None):
        if freeze:
            p=Path(root)/"data/forecasts/m0_720_eight"/"2026-11-01"
            p.mkdir(parents=True)
            r={'model_version':MODEL,'mode':'forecast','run_utc':stamp(NOW-timedelta(minutes=30))}
            r['report_sha256']=hashobj(r)
            (p/'FROZEN_M0_720_EIGHT.json').write_text(json.dumps(r))
        if settle:
            day=Path(root)/"data/pit_sidecar/m0_720_eight"/"2026-11-01"/("settle-"+settle)
            day.mkdir(parents=True)
            when=f'2026-11-01T{settle[:2]}:{settle[2:4]}:{settle[4:6]}+00:00'
            r={'model_version':MODEL,'mode':'settle','run_utc':when}
            r['report_sha256']=hashobj(r)
            (day/'RECEIPT.json').write_text(json.dumps(r))
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
            self.fixtures(root,freeze=True,settle="090000000111")
            self.assertEqual(self.mode(root,cron=SETTLE_CRONS[0]),"skip")
            self.assertEqual(self.mode(root,cron=SETTLE_CRONS[0],now=NOW+timedelta(hours=2)),"settle")
    def test_push_avoids_spurious_paid_calls(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixtures(root,freeze=True,settle="120000001234")
            self.assertEqual(self.mode(root,event="push"),"skip")
            self.assertEqual(self.mode(root,event="push",now=NOW+timedelta(hours=10)),"skip")
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
    def test_20261105_first_schedule_forecast_not_blocked_by_night_settlement(self):
        """The 03:29 UTC SETTLE cannot consume the 06:21 UTC FORECAST slot."""
        from scripts.kb3_p1_shadow_activation_policy import decide,BRANCH,REPO
        now=datetime(2026,11,5,6,21,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as root:
            day=Path(root)/"data/pit_sidecar/m0_720_eight"/"2026-11-05"/"settle-032900"
            day.mkdir(parents=True)
            receipt={"model_version":MODEL,"mode":"settle",
                     "run_utc":"2026-11-05T03:29:00+00:00"}
            receipt["report_sha256"]=hashobj(receipt)
            (day/"RECEIPT.json").write_text(json.dumps(receipt))
            mode,reason=select(event="schedule",cron="21 6,9,12 * * *",
                               user_mode="",now=now,root=root)
            self.assertEqual((mode,reason),("forecast","MISSING_OR_NEW_INTRADAY_FORECAST"))
            activation=decide(mode=mode,event="schedule",ref=BRANCH,repository=REPO)
            self.assertTrue(activation["enabled"])
            self.assertEqual(activation["official_fit_increment"],0)
            self.assertEqual(select(event="push",cron="",user_mode="",now=now,
                                    root=root)[0],"skip")
            self.assertEqual(select(event="schedule",cron="17 8,14,22 * * *",
                                    user_mode="",now=now,root=root)[0],"skip")

    def test_manual_forecast_is_eligible_only_until_immutable_attempt_cap(self):
        from scripts.kb3_p1_shadow_activation_policy import decide,BRANCH,REPO
        with tempfile.TemporaryDirectory() as root:
            def mode():
                return select(event="workflow_dispatch",cron="",user_mode="forecast",
                              now=NOW,root=root)
            self.assertEqual(mode()[0],"forecast")
            self.assertTrue(decide(mode="forecast",event="workflow_dispatch",
                                   ref=BRANCH,repository=REPO)["enabled"])
            for minute in (0,20,40):
                when=NOW-timedelta(hours=4)+timedelta(minutes=minute)
                folder=Path(root)/"data/pit_sidecar/m0_720_eight"/"2026-11-01"/(
                    "forecast-"+when.strftime("%H%M"))
                folder.mkdir(parents=True)
                attempt={"model_version":MODEL,"mode":"forecast",
                         "run_utc":stamp(when)}
                attempt["attempt_sha256"]=hashobj(attempt)
                (folder/"ATTEMPT.json").write_text(json.dumps(attempt))
            self.assertEqual(mode(),("skip","FORECAST_ATTEMPT_DAILY_CAP"))

    def test_schedule_crons_are_wired_to_exact_guard_strings(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/kb3-step16-m0-720-eight-forward.yml").read_text()
        for cron in ("21 6,9,12 * * *","17 8,14,22 * * *"):
            self.assertIn("- cron: '"+cron+"'",workflow)
        self.assertIn("21 6,9,12 * * *",FORECAST_CRONS)
        self.assertIn("17 8,14,22 * * *",SETTLE_CRONS)

    def test_live_checkout_refreshes_main_before_mode_and_provider(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/kb3-step16-m0-720-eight-forward.yml").read_text()
        live=workflow.split("  real-eighth-league-fitted-M0-shadow:",1)[1]
        self.assertIn("cancel-in-progress: false",workflow)
        self.assertIn("group: kb3-step16-eight-league-m0-720-research-db",workflow)
        self.assertIn("ref: refs/heads/main",live)
        self.assertIn("git merge --ff-only origin/main",live)
        self.assertLess(live.index("git merge --ff-only origin/main"),
                        live.index("python -m scripts.step16_m0_mode_guard"))
        self.assertLess(live.index("python -m scripts.step16_m0_mode_guard"),
                        live.index("python -m scripts.step16_m0_720_eight_run"))
        self.assertIn("M0_RESEARCH_NOT_APPEND_ONLY_NO_REBASE",live)

if __name__=="__main__":unittest.main()
