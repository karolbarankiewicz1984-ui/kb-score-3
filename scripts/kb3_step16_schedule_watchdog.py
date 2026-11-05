"""Read-only, no-secrets M0 scheduler redundancy; only dispatch native guarded workflow.

Watchdog never calls sports providers, never creates forecasts or settlements,
never edits source SQLite, and never bypasses M0's existing run mode guard.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os

from scripts.step16_m0_mode_guard import select

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-m0-native-workflow-watchdog-v1"

def choose(requested,now,root=ROOT):
    if requested not in ("forecast","settle"):
        raise ValueError("WATCHDOG_INVALID_MODE")
    if now.utcoffset()!=timedelta(0):
        raise ValueError("WATCHDOG_UTC_ONLY")
    # Reuse the native scheduler's decision. No synthetic forecast/settle mode.
    cron="21 6,9,12 * * *" if requested=="forecast" else \
         "17 8,14,22 * * *"
    mode,reason=select(event="schedule",cron=cron,user_mode="",
                       now=now,root=root)
    if mode not in ("forecast","settle","skip"):
        raise ValueError("WATCHDOG_UNEXPECTED_DECISION")
    return {
        "schema":SCHEMA,"requested":requested,
        "mode":mode,"reason":reason,
        "will_dispatch_existing_native_workflow":mode==requested,
        "source_data_changed":False,"sports_api_called":False,
        "no_new_key":True,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--requested",choices=("settle","forecast"),required=True)
    p.add_argument("--output",default=os.environ.get("GITHUB_OUTPUT",""))
    args=p.parse_args()
    decision=choose(args.requested,datetime.now(timezone.utc))
    print("KB3_M0_WATCHDOG_DECISION",json.dumps(decision,sort_keys=True))
    if args.output:
        with open(args.output,"a",encoding="utf8") as f:
            f.write("dispatch="+("true" if decision[
                "will_dispatch_existing_native_workflow"] else "false")+"\n")
            f.write("mode="+decision["mode"]+"\n")
if __name__=="__main__":
    main()
