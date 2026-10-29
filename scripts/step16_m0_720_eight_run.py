"""Run separate fixed M0 TRAIN720 shadow collection or settlement from GitHub Actions.

Uses existing PitchAPI key; zero Premier League/TEST requests. No auto promotion.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
from src.kb3_step16_m0_720_eight_forward import run,DB,FORECASTS,SOURCES
from src.kb3_pit_ledger import utc_now
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("forecast","settle"),required=True)
    args=p.parse_args()
    key=os.environ.get("PITCHAPI_API_KEY","")
    if not key:raise SystemExit("PITCHAPI_SECRET_NOT_CONFIGURED")
    now=datetime.now(timezone.utc)
    if args.mode=="forecast":
        existing=FORECASTS/now.date().isoformat()/"FROZEN_M0_720_EIGHT.json"
        if existing.is_file():
            j=json.loads(existing.read_text())
            if j.get("model_version")!="M0_ELO_POISSON_RESEARCH_720TRAIN_V1":
                raise SystemExit("FROZEN_FORECAST_VERSION_MISMATCH")
            print("RESEARCH720_DAILY_FORECAST_ALREADY_FROZEN",existing)
            return
    from pitchapi import PitchAPI
    result=run(mode=args.mode,client=PitchAPI(api_key=key),now=now)
    print(json.dumps({k:result[k] for k in (
        "mode","model_version","run_utc","network_calls","league_count",
        "countries","params_sha256","gate16")},sort_keys=True))
    print("M0_720_RESEARCH_RUN_COUNTS",json.dumps({
        k:result[k] for k in ("new_forecasts","total_forecasts","new_settlements",
          "total_settlements") if k in result},sort_keys=True))
if __name__=="__main__":main()
