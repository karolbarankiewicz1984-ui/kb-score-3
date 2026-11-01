"""Local-only M0 action mode selection; delayed GitHub schedules may overlap.

Backups run only if no immutable daily freeze and settlement cadence is stale.
Never change old forecasts, never make a late timestamp look like an early one.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[1]
FORECAST_CRONS=("21 6,9,12 * * *","21 6 * * *")
SETTLE_CRONS=("17 8,14,22 * * *","17 8,22 * * *")
MIN_SETTLE_GAP=timedelta(hours=8)

def latest_settlement(root,now):
    base=Path(root)/"data/pit_sidecar/m0_720_eight"
    times=[]
    for lookback in range(3):
        day=(now.date()-timedelta(days=lookback)).isoformat()
        for rec in (base/day).glob("settle-*/RECEIPT.json"):
            hh=rec.parent.name.removeprefix("settle-")
            if len(hh)<6 or not hh[:6].isdigit():continue
            try:
                ts=datetime.fromisoformat(f"{day}T{hh[:2]}:{hh[2:4]}:{hh[4:6]}+00:00")
            except ValueError:continue
            if ts<=now:times.append(ts)
    return max(times,default=None)

def select(*,event,cron,user_mode,now,root):
    if now.tzinfo is None or now.utcoffset()!=timedelta(0):
        raise ValueError("UTC_REQUIRED")
    today=now.date().isoformat()
    frozen=(Path(root)/"data/forecasts/m0_720_eight"/today/"FROZEN_M0_720_EIGHT.json").is_file()
    last=latest_settlement(root,now)
    stale=last is None or now-last>=MIN_SETTLE_GAP
    if event=="workflow_dispatch" and user_mode=="settle":
        return "settle","MANUAL_SETTLEMENT"
    if event=="schedule" and cron in SETTLE_CRONS:
        return ("settle","SETTLEMENT_DUE") if stale else ("skip","SETTLEMENT_ALREADY_RECENT")
    if event=="schedule" and cron in FORECAST_CRONS:
        return ("skip","TODAY_ALREADY_FROZEN") if frozen else ("forecast","MISSING_DAILY_FORECAST")
    if event=="workflow_dispatch" and user_mode=="forecast":
        return ("skip","TODAY_ALREADY_FROZEN") if frozen else ("forecast","MANUAL_FORECAST")
    if event=="push":
        if not frozen and now.hour>=6:
            return "forecast","PUSH_RECOVERY_NO_FREEZE"
        if frozen and stale:
            return "settle","PUSH_RECOVERY_STALE_SETTLEMENT"
        return "skip","NO_NEEDED_PAID_PROVIDER_REQUEST"
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
