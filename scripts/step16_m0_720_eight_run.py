"""Run separate fixed M0 TRAIN720 shadow collection or settlement from GitHub Actions.

Uses existing PitchAPI key; zero Premier League/TEST requests. No auto promotion.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
from src.kb3_step16_m0_720_eight_forward import run,DB,FORECASTS,SOURCES,Research720Error
from src.kb3_step16_run_policy import forecast_due
from src.kb3_pit_ledger import utc_now
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("forecast","settle"),required=True)
    args=p.parse_args()
    now=datetime.now(timezone.utc)
    print("M0_720_RESEARCH_EXECUTION_INTENT",json.dumps({"mode":args.mode,"utc_day":now.date().isoformat(),"research_only":True,"protected_english_test_access":False},sort_keys=True))
    if args.mode=="forecast":
        due,reason=forecast_due(SOURCES,FORECASTS,now)
        if not due:
            print('M0_720_LOCAL_FORECAST_SKIP',reason)
            return
    key=os.environ.get('PITCHAPI_API_KEY','')
    if not key:raise SystemExit('PITCHAPI_SECRET_NOT_CONFIGURED')
    from pitchapi import PitchAPI
    try:result=run(mode=args.mode,client=PitchAPI(api_key=key,max_retries=0),now=now)
    except Research720Error as exc:
        if str(exc).startswith('FORECAST_NOT_DUE:'):
            print('M0_720_LOCAL_FORECAST_SKIP',str(exc));return
        print('M0_720_CAPTURE_FAILED',json.dumps({"error_type":type(exc).__name__,"error_code":str(exc)[:160],"capture_detail":getattr(exc,'capture_detail',None)},sort_keys=True,ensure_ascii=False))
        raise SystemExit(3)
    except Exception as exc:
        print('M0_720_CAPTURE_FAILED',type(exc).__name__)
        raise SystemExit(3)
    print(json.dumps({k:result[k] for k in (
        "mode","model_version","run_utc","network_calls","league_count",
        "countries","params_sha256","gate16")},sort_keys=True))
    print("M0_720_RESEARCH_RUN_COUNTS",json.dumps({
        k:result[k] for k in ("new_forecasts","total_forecasts","new_settlements",
          "total_settlements") if k in result},sort_keys=True))
if __name__=="__main__":main()
