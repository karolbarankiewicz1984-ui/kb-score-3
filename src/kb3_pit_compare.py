"""Step11: compare two separately observed, sealed PIT snapshots.

Comparison runs on decrypted temporary copies; it publishes *only counts*
and digests. Does not certify pre-2026 data or provider publication time.
"""
from __future__ import annotations
from collections import Counter
import json
import sqlite3
from src.kb3_pit_ledger import verify_chain, as_utc


def read_one(db):
    proof=verify_chain(db)
    if proof["sessions"] != 1 or proof["fixture_records"] != 380:
        raise ValueError("ONE_FULL_SNAPSHOT_REQUIRED")
    row=db.execute("""SELECT capture_id,resource,completed_at_utc,origin
        FROM captures LIMIT 1""").fetchone()
    if row[3]!="NETWORK_OBSERVED":
        raise ValueError("REAL_NETWORK_OBSERVATION_REQUIRED")
    games={}
    for fid,raw,h in db.execute("""SELECT provider_fixture_id,record_json,record_sha256
                                  FROM capture_records"""):
        item=json.loads(raw)
        games[fid]={"hash":h,"date":item["fixture"]["date"],
                    "status":item["fixture"]["status"]["short"],
                    "goals":(item.get("score") or {}).get("fulltime")}
    return {"time":row[2],"resource":row[1],"capture_id":row[0],
            "chain":proof["final_chain_sha256"],"records":games}


def compare(first_db,second_db):
    a,b=read_one(first_db),read_one(second_db)
    if a["resource"] != b["resource"]:
        raise ValueError("DIFFERENT_PROVIDER_SCOPE")
    if as_utc(a["time"]) >= as_utc(b["time"]):
        raise ValueError("NON_CHRONOLOGICAL_SNAPSHOTS")
    if set(a["records"])!=set(b["records"]):
        raise ValueError("FIXTURE_SET_CHANGED_REQUIRES_REVIEW")
    counters=Counter()
    for fid in a["records"]:
        x,y=a["records"][fid],b["records"][fid]
        counters["unchanged" if x["hash"]==y["hash"] else "changed"]+=1
        if x["status"]!=y["status"]:
            counters["status_changed"]+=1
            counters[f"from_{x['status']}_to_{y['status']}"]+=1
        if x["date"]!=y["date"]:
            counters["kickoff_changed"]+=1
        if x["goals"]!=y["goals"]:
            counters["fulltime_score_changed"]+=1
        if x["status"]=="FT" and y["status"]!="FT":
            counters["final_result_invalidated"]+=1
        if x["status"]!="FT" and y["status"]=="FT":
            counters["new_finals"]+=1
    stats={key:counters[key] for key in (
        "unchanged","changed","status_changed","kickoff_changed",
        "fulltime_score_changed","final_result_invalidated","new_finals")}
    return {"schema":"kb3-step11-two-real-snapshots-comparison-v1",
            "source":"API-Football","resource":a["resource"],
            "first_observed_at_utc":a["time"],
            "second_observed_at_utc":b["time"],
            "first_chain_sha256":a["chain"],"second_chain_sha256":b["chain"],
            "matched_fixture_ids":len(a["records"]),
            "counts":stats,
            "ambiguous_id_changes":0,
            "source_original_published_at_utc":None,
            "historical_pit_verified":False,"training_allowed":False,
            "raw_rows_exported":False}
