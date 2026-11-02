"""Read-only audit of the M0-720 eight-league frozen forecast/settlement ledger.

No PitchAPI calls, model fitting, database mutations or ex-post predictions.
Run: python -m scripts.audit_m0720_backlog --db data/forward_m0_720_eight/kb3_forward_eight.sqlite
"""
import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

def columns(con, table):
    return {row[1] for row in con.execute("PRAGMA table_info("+table+")")}

def audit(path, now=None):
    now = now or datetime.now(timezone.utc)
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
        fcols, scols = columns(con, "forecasts"), columns(con, "settlements")
        required = {"id", "league", "kickoff_utc"}
        if not required <= fcols or "forecast_id" not in scols:
            raise ValueError("UNEXPECTED_DATABASE_SCHEMA")
        forecasts = con.execute("SELECT id,league,kickoff_utc FROM forecasts").fetchall()
        settled = {r[0] for r in con.execute("SELECT forecast_id FROM settlements")}
        by_league = {}
        pending = []
        for f in forecasts:
            league = f["league"]
            entry = by_league.setdefault(league, {"forecasts":0,"settled":0,"pending":0})
            entry["forecasts"] += 1
            if f["id"] in settled:
                entry["settled"] += 1
            else:
                entry["pending"] += 1
                kickoff = datetime.fromisoformat(f["kickoff_utc"].replace("Z","+00:00"))
                pending.append({"forecast_id":f["id"],"league":league,
                    "kickoff_utc":f["kickoff_utc"],
                    "status":"RESULT_LOOKUP_REQUIRED" if kickoff < now else "FUTURE_KICKOFF"})
        return {"read_only":True,"checked_at_utc":now.isoformat(),
                "forecasts":len(forecasts),"settlements":len(settled),
                "pending":len(pending),"by_league":by_league,
                "pending_forecasts":pending,
                "warning":"Past kickoff is NOT proof of finished result; check provider and 3h gate. Never backfill forecasts."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",default="data/forward_m0_720_eight/kb3_forward_eight.sqlite")
    parser.add_argument("--out")
    args=parser.parse_args()
    result=audit(args.db)
    payload=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)
    if args.out:Path(args.out).write_text(payload+"\n",encoding="utf8")
    print(payload)

if __name__=="__main__":
    main()
