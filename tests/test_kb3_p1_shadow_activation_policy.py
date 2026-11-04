"""No-provider-API checks for explicit future-only Shadow Six activation."""
from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from scripts.kb3_p1_shadow_activation_policy import (
    decide,main,POLICY,SCHEMA,BRANCH,REPO,ShadowActivationSafety
)


class ShadowActivationPolicyTests(unittest.TestCase):
    def test_current_reviewed_policy_enables_only_new_main_schedule(self):
        x=decide(mode="forecast",event="schedule",ref=BRANCH,repository=REPO)
        self.assertTrue(x["enabled"])
        self.assertEqual(x["reason"],"APPROVED_FUTURE_ONLY_RESEARCH_SHADOW")
        self.assertEqual(x["official_fit_increment"],0)
        self.assertEqual(x["new_live_forecast_count_claimed"],0)
        self.assertEqual(len(x["model_sha256"]),64)

    def test_manual_dispatch_forecast_allowed_on_main(self):
        r=decide(mode="forecast",event="workflow_dispatch",
                 ref=BRANCH,repository=REPO)
        self.assertTrue(r["enabled"])

    def test_main_settlement_never_enabled(self):
        for event in ("schedule","workflow_dispatch"):
            r=decide(mode="settle",event=event,ref=BRANCH,repository=REPO)
            self.assertFalse(r["enabled"])

    def test_no_activation_on_branch_pr_push_or_other_repositories(self):
        for opts in (
            {"mode":"forecast","event":"pull_request","ref":BRANCH,"repository":REPO},
            {"mode":"forecast","event":"push","ref":BRANCH,"repository":REPO},
            {"mode":"forecast","event":"schedule",
             "ref":"refs/heads/research/kb3-shadow-six-controlled-live-integration-20261104","repository":REPO},
            {"mode":"forecast","event":"schedule","ref":BRANCH,"repository":"unknown/repo"},
            {"mode":"skip","event":"schedule","ref":BRANCH,"repository":REPO},
        ):
            self.assertFalse(decide(**opts)["enabled"],opts)

    def test_missing_policy_fails_disabled_without_impairing_m0(self):
        with tempfile.TemporaryDirectory() as td:
            r=decide(mode="forecast",event="schedule",ref=BRANCH,
                     repository=REPO,policy_path=Path(td)/"missing.json")
            self.assertFalse(r["enabled"])

    def test_explicit_rollback_disables_shadow_but_not_m0(self):
        with tempfile.TemporaryDirectory() as td:
            content=json.loads(POLICY.read_text())
            content["enabled"]=False
            path=Path(td)/"off.json"
            path.write_text(json.dumps(content))
            r=decide(mode="forecast",event="schedule",ref=BRANCH,
                     repository=REPO,policy_path=path)
            self.assertFalse(r["enabled"])
            self.assertEqual(r["reason"],"EXPLICIT_RESEARCH_SWITCH_OFF")

    def test_invalid_or_auto_promoted_policy_blocked(self):
        original=json.loads(POLICY.read_text())
        for changes in (
            {"enabled":"true"},
            {"required_model_sha256":"a"*64},
            {"production_approved":True},
            {"allow_champion_promotion":True},
            {"official_fit_increment":1},
            {"allow_retroactive_predictions":True},
            {"research_only":False},
            {"eligible_event_types":["push","schedule"]},
        ):
            with tempfile.TemporaryDirectory() as td:
                policy={**original,**changes}
                target=Path(td)/"wrong.json"
                target.write_text(json.dumps(policy))
                with self.assertRaises(ShadowActivationSafety):
                    decide(mode="forecast",event="schedule",ref=BRANCH,
                           repository=REPO,policy_path=target)

    def test_cli_only_writes_reversible_flag_and_never_reports_live_forecasts(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"github_output.txt"
            path.write_text("")
            with patch.dict("os.environ",{
                "RUN_MODE":"forecast","GITHUB_EVENT_NAME":"schedule",
                "GITHUB_REF":BRANCH,"GITHUB_REPOSITORY":REPO,
                "GITHUB_OUTPUT":str(path)}):
                main()
            self.assertEqual(path.read_text(),"enabled=true\n")
            path.write_text("")
            with patch.dict("os.environ",{
                "RUN_MODE":"settle","GITHUB_EVENT_NAME":"schedule",
                "GITHUB_REF":BRANCH,"GITHUB_REPOSITORY":REPO,
                "GITHUB_OUTPUT":str(path)}):
                main()
            self.assertEqual(path.read_text(),"enabled=false\n")


if __name__=="__main__":
    unittest.main()
