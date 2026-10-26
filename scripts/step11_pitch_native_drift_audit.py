"""Offline sanitized native PitchAPI revision report from separately restored PIT DBs.

Run only on already authenticated/decrypted archive copies on a trusted
machine. Never use this script to read secrets or call an API.
"""
import argparse
import json
from pathlib import Path
from src.kb3_pitch_native_drift import compare_independent_ledgers

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--older-restored-db",required=True)
    p.add_argument("--newer-restored-db",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=compare_independent_ledgers(a.older_restored_db,a.newer_restored_db)
    target=Path(a.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf8") as stream:
        json.dump(result,stream,sort_keys=True,indent=2)
        stream.write("\n")
    print("KB3_NATIVE_SNAPSHOT_DRIFT_COMPLETE",
          json.dumps({k:v for k,v in result.items()
            if k in ("match_count","changed_kickoffs","changed_statuses",
                     "changed_scores","changed_raw_match_payloads",
                     "observations_on_distinct_utc_dates","training_allowed")},
            sort_keys=True))
if __name__=="__main__":
    main()
