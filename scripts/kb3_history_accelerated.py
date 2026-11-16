"""Execute up to five separately sealed 48-match batches (up to 240 matches).

Each batch has its own immutable observed-at receipts and new SQLite snapshot.
Existing size guard on raw source stays at 16MB per sealed batch. Source/API
errors cannot turn missing statistics into zero or a fake validation PASS.
"""
from __future__ import annotations
import argparse
import json
import os
import re
from datetime import datetime,timezone
from pathlib import Path

from scripts.kb3_historical_pitchapi_backfill import (
    capture, DB, ARCHIVE, ROOT, PUBLIC_KEY,
)
from scripts.kb3_history_issue_recheck import (
    recheck, ISSUE_DB, ISSUE_ROOT,
)
from src.kb3_historical_feature_quality import assess_and_cache

MAX_BATCHES=5
BATCH_SIZE=48
SCHEMA="kb3-accelerated-history-240-and-recheck-v1"

def drive(client,*, run_token,db=DB,archive=ARCHIVE,
          issues_db=ISSUE_DB,issues_root=ISSUE_ROOT,public_key=PUBLIC_KEY,
          batches=MAX_BATCHES,batch_size=BATCH_SIZE):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,42}",run_token):
        raise ValueError("UNSAFE_ACCELERATED_RUN_TOKEN")
    if not 1<=batches<=MAX_BATCHES or not 1<=batch_size<=BATCH_SIZE:
        raise ValueError("UNSAFE_BATCH_COUNT")
    result=[]
    for n in range(1,batches+1):
        sub=run_token+"-b"+str(n)
        report=capture(client=client,db_path=db,root=archive,
                       public_key=public_key,run_token=sub,max_matches=batch_size)
        result.append({"batch":n,"token":sub,
            "requests":report["provider_requests"],
            "new":report["new_match_stats"],
            "verified_xg":report["new_native_xg_verified"],
            "cum":report["cumulative_match_stats"],
            "sha256":report["source_ciphertext_sha256"]})
        if report["new_match_stats"]==0:
            break
    try:
        checked=recheck(client,db_path=db,issue_db=issues_db,
                        root=issues_root,public_key=public_key,
                        run_token=run_token+"-issues",
                        max_xg=3,max_cards=6)
        issue_state=checked["status"]
    except Exception as exc:
        # Source batches are still valid; do not conceal an unresolved issue pass.
        checked={"status":"RECHECK_ERROR","error_type":type(exc).__name__}
        issue_state="RECHECK_ERROR"
    ts=datetime.now(timezone.utc).date().isoformat()
    dest=Path(archive)/ts/("run-"+run_token+"-summary")
    if dest.exists():
        raise FileExistsError("ACCELERATED_REPORT_ALREADY_EXISTS")
    dest.mkdir(parents=True,exist_ok=False)
    quality=assess_and_cache(db,dest/"ROLLING_AFTER_RECHECK.json",
                             recheck_db_path=issues_db)
    summary={"schema":SCHEMA,"run_token":run_token,
        "completed_batches":len(result),
        "new_match_stats":sum(r["new"] for r in result),
        "new_verified_xg":sum(r["verified_xg"] for r in result),
        "provider_requests_history":sum(r["requests"] for r in result),
        "history_batches":result,
        "issues":checked,"issue_status":issue_state,
        "cumulative_match_stats":quality["totals"]["total_observed_stats_matches"],
        "effective_xg_verified":quality["totals"]["xg_verified_matches"],
        "effective_core5_pair_complete":quality["totals"]["pair_core_5_complete"],
        "effective_xg5_pair_complete":quality["totals"]["pair_xg_5_complete"],
        "effective_xg10_pair_complete":quality["totals"]["pair_xg_10_complete"],
        "effective_xg15_pair_complete":quality["totals"]["pair_xg_15_complete"],
        "provider_original_pit_certified":False,
        "research_only":True,"production_approved":False,
        "original_m0_unchanged":True,"protected_english_test_untouched":True,
        "calibration_unchanged":True,"gate16_17":"PENDING"}
    with (dest/"ACCELERATED_CAPTURE_REPORT.json").open("x",encoding="utf8") as f:
        json.dump(summary,f,sort_keys=True,indent=2);f.write("\n")
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--run-token",required=True)
    p.add_argument("--batches",type=int,default=MAX_BATCHES)
    p.add_argument("--batch-size",type=int,default=BATCH_SIZE)
    args=p.parse_args()
    key=os.getenv("PITCHAPI_API_KEY","").strip()
    if not key:raise SystemExit("MISSING_EXISTING_PITCHAPI_SECRET")
    from pitchapi import PitchAPI
    try:
        report=drive(PitchAPI(api_key=key,max_retries=0),run_token=args.run_token,
                     batches=args.batches,batch_size=args.batch_size)
    except Exception as exc:
        print("KB3_ACCELERATED_CAPTURE_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
    print("KB3_ACCELERATED_CAPTURE",json.dumps({k:report[k] for k in (
        "completed_batches","new_match_stats","new_verified_xg",
        "provider_requests_history","cumulative_match_stats",
        "effective_xg5_pair_complete","issue_status","gate16_17")},sort_keys=True))
if __name__=="__main__":
    main()
