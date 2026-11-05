"""Operator-only read-only KB3 TEST market preview; no network and no DB writes.

This is NOT a new forecast, market freeze, certified FIT or PDF generator.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from src.kb3_test_readonly_markets import read_original_sqlite

DB = Path("data/forward_m0_720_eight/kb3_forward_eight.sqlite")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",type=Path,default=DB)
    parser.add_argument("--as-of-utc",default=None)
    parser.add_argument("--limit",type=int,default=100)
    parser.add_argument("--output",type=Path,default=None)
    args=parser.parse_args()
    at=args.as_of_utc or datetime.now(timezone.utc).isoformat(
        timespec="microseconds").replace("+00:00","Z")
    report=read_original_sqlite(args.db,as_of_utc=at,limit=args.limit)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as file:
            json.dump(report,file,ensure_ascii=False,indent=2,sort_keys=True,
                      allow_nan=False)
            file.write("\n")
    print("KB3_TEST_READONLY_MARKET_PREVIEW",
          json.dumps({k:report[k] for k in (
              "schema","as_of_utc","count","original_sqlite_changed",
              "new_forecasts_created","new_market_freezes_created",
              "official_fit_increment","gate16","gate17")},
              ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
