"""Aggregate-only 380-fixture Step11 pilot. No private rows exported."""
import argparse
from collections import Counter
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
from src.kb3_features import build_features,utc_dt,utc_str,FEATURE_VERSION


def audit(dbpath):
    totals=Counter()
    misses=Counter()
    with sqlite3.connect(dbpath) as db:
        matches=db.execute(
            "SELECT fixture_id,kickoff_utc FROM fixtures WHERE status='FINISHED' "
            "ORDER BY kickoff_utc,fixture_id").fetchall()
        if not matches:
            raise ValueError("NO_FINISHED_FIXTURES")
        for fid,start in matches:
            cutoff=utc_str(utc_dt(start)-timedelta(hours=1))
            for mode in ("verified","replay"):
                x=build_features(db,fid,cutoff_utc=cutoff,mode=mode)
                assert not x["training_allowed"]
                totals[mode+"_targets"] += 1
                totals[mode+"_predecessors"] += x["accepted_predecessor_count"]
                totals[mode+"_with_history"] += bool(x["accepted_predecessor_count"])
                misses.update({mode+"_"+k:1 for k,v in x["missing_flags"].items() if v})
    return {
        "schema":"kb3-step11-aggregate-v0.1","feature_version":FEATURE_VERSION,
        "fixture_count":len(matches),"counts":dict(sorted(totals.items())),
        "missing_counts":dict(sorted(misses.items())),
        "training_allowed":False,"trained_model":False,
        "historical_availability_certified":False,
        "note":"Replay values are retrospective research, NOT point-in-time proof."}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=audit(a.db)
    path=Path(a.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("STEP11_AGGREGATES",
          json.dumps({k:v for k,v in result.items() if k!="missing_counts"},sort_keys=True))


if __name__=="__main__":
    main()
