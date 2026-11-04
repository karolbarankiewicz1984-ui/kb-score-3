"""Explicit, reversible, future-only CatBoost research Shadow activation gate.

Production M0 remains unchanged, no retrospective forecasts, no calibration
updates, no model/champion promotion. Only GitHub scheduled/manual forecast
runs on main can enable. A merge or PR push is never a live run.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.kb3_step16_m0_720_eight_forward import ROOT
from src.kb3_p1_shadow_live_gate import pinned_model_details

POLICY=ROOT/"config/kb3_shadow_six_forward_activation.json"
SCHEMA="kb3-shadow-six-forward-activation-v1"
ALLOWED_EVENTS=frozenset(("schedule","workflow_dispatch"))
BRANCH="refs/heads/main"
REPO="karolbarankiewicz1984-ui/kb-score-3"
MODEL="KB3_CATBOOST_SHADOW_LAST5_GOALS_6_RESEARCH_V1"


class ShadowActivationSafety(ValueError):
    pass


def need(condition,message):
    if not condition:
        raise ShadowActivationSafety(message)


def decide(*,mode,event,ref,repository,policy_path=POLICY,pin_path=None):
    """Return ON only on an actual new M0 FORECAST capture from main.

    A wrongly named event, a non-main branch, or any settlement yields OFF.
    The reviewed model remains research-only; the true CBM byte SHA is checked
    separately before PitchAPI calls in the original workflow.
    """
    if (mode!="forecast" or event not in ALLOWED_EVENTS
            or ref!=BRANCH or repository!=REPO):
        return {"enabled":False,"reason":"NOT_APPROVED_FUTURE_MAIN_FORECAST",
                "research_only":True,"official_fit_increment":0}
    policy=Path(policy_path)
    if not policy.exists():
        return {"enabled":False,"reason":"NO_EXPLICIT_ACTIVATION_POLICY",
                "research_only":True,"official_fit_increment":0}
    data=json.loads(policy.read_text(encoding="utf-8"))
    need(isinstance(data,dict),"INVALID_ACTIVATION_DOCUMENT")
    if data.get("enabled") is False:
        return {"enabled":False,"reason":"EXPLICIT_RESEARCH_SWITCH_OFF",
                "research_only":True,"official_fit_increment":0}
    need(data.get("enabled") is True,"INVALID_ACTIVATION_BOOL")
    need(
        data.get("schema")==SCHEMA
        and data.get("owner_authorized_in_chat") is True
        and data.get("research_only") is True
        and data.get("only_new_m0") is True
        and data.get("eligible_event_types")==["schedule","workflow_dispatch"]
        and data.get("required_branch")==BRANCH
        and data.get("required_repository")==REPO
        and data.get("required_mode")=="forecast"
        and data.get("required_model_version")==MODEL
        and data.get("formal_model_approval") is False
        and data.get("official_fit_increment")==0
        and data.get("allow_retroactive_predictions") is False
        and data.get("allow_champion_promotion") is False,
        "SHADOW_RESEARCH_ACTIVATION_POLICY_DRIFT")
    pin=pinned_model_details() if pin_path is None else pinned_model_details(pin_path)
    need(data["required_model_sha256"]==pin["model_sha256"] and
         data["required_model_version"]==pin["model_version"]
         and pin["production_approved"] is False
         and pin["enabled_by_default"] is False
         and pin["historical_native_pit_certified"] is False,
         "PINNED_RESEARCH_ONLY_MODEL_NOT_APPROVED_FOR_SHADOW")
    return {"enabled":True,"reason":"APPROVED_FUTURE_ONLY_RESEARCH_SHADOW",
            "model_sha256":pin["model_sha256"],
            "research_only":True,"official_fit_increment":0,
            "new_live_forecast_count_claimed":0}


def main():
    status=decide(mode=os.environ.get("RUN_MODE",""),
                  event=os.environ.get("GITHUB_EVENT_NAME",""),
                  ref=os.environ.get("GITHUB_REF",""),
                  repository=os.environ.get("GITHUB_REPOSITORY",""))
    out=os.environ.get("GITHUB_OUTPUT")
    if not out:
        raise ShadowActivationSafety("GITHUB_ACTIONS_OUTPUT_REQUIRED")
    with Path(out).open("a",encoding="utf-8") as file:
        file.write("enabled="+("true" if status["enabled"] else "false")+"\n")
    print("KB3_SHADOW_SIX_RESEARCH_ONLY_ACTIVATION",json.dumps(
        status,sort_keys=True))


if __name__=="__main__":
    main()
