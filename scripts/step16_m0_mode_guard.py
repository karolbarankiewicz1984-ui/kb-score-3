"""Local-only M0 action mode selection; delayed GitHub schedules may overlap.

Backups run only if no immutable daily freeze and settlement cadence is stale.
Never change old forecasts, never make a late timestamp look like an early one.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from pathlib import Path
import os
from src.kb3_step16_run_policy import forecast_due,latest_settlement as policy_latest_settlement,SETTLEMENT_GAP

ROOT=Path(__file__).resolve().parents[1]
FORECAST_CRONS=("21 6,9,12 * * *","21 6 * * *")
SETTLE_CRONS=("17 8,14,22 * * *","17 8,22 * * *")
MIN_SETTLE_GAP=SETTLEMENT_GAP

def latest_settlement(root,now):
    return policy_latest_settlement(Path(root)/'data/pit_sidecar/m0_720_eight',now)

def select(*,event,cron,user_mode,now,root):
    if now.tzinfo is None or now.utcoffset()!=timedelta(0):
        raise ValueError("UTC_REQUIRED")
    due,forecast_reason=forecast_due(Path(root)/'data/pit_sidecar/m0_720_eight',
                                    Path(root)/'data/forecasts/m0_720_eight',now)
    last=latest_settlement(root,now)
    stale=last is None or now-last>=MIN_SETTLE_GAP
    if event=="workflow_dispatch" and user_mode=="settle":
        return "settle","MANUAL_SETTLEMENT"
    if event=="schedule" and cron in SETTLE_CRONS:
        return ("settle","SETTLEMENT_DUE") if stale else ("skip","SETTLEMENT_ALREADY_RECENT")
    if event=="schedule" and cron in FORECAST_CRONS:
        return ('forecast',forecast_reason) if due else ('skip',forecast_reason)
    if event=="workflow_dispatch" and user_mode=="forecast":
        return ('forecast',forecast_reason) if due else ('skip',forecast_reason)
    if event=="push":
        return 'skip','CODE_PUSH_NEVER_STARTS_PROVIDER_REQUESTS'
    raise ValueError("UNRECOGNIZED_EVENT_OR_CRON")

def main():
    mode,reason=select(event=os.environ.get("EVENT_KIND",""),
      cron=os.environ.get("CRON",""),user_mode=os.environ.get("USER_MODE",""),
      now=datetime.now(timezone.utc),root=ROOT)
    with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf8") as f:
        f.write("mode="+mode+"\nreason="+reason+"\n")
    print("M0_720_RESEARCH_MODE",mode,reason,
          "explicitly_no_API_if_skip",mode=="skip")
if __name__=="__main__":main()
