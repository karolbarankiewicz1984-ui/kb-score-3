"""KB3 Step11: append-only point-in-time *observation* ledger.

An observed API payload proves what this recorder SAW by the recorded completion
time. It does NOT prove the original provider publication time, and does not
backdate the data. No ML/predictions or mutation of existing historical SQLite.
"""
from __future__ import annotations
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone

GENESIS="0"*64
FINAL_STATUS="FT"

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def hexdigest(data):
    return hashlib.sha256(data).hexdigest()

def as_utc(raw):
    if not isinstance(raw,str):
        raise ValueError("TIMESTAMP_MISSING")
    try:
        d=datetime.fromisoformat(raw.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("TIMESTAMP_INVALID") from exc
    if d.utcoffset() is None:
        raise ValueError("TIMESTAMP_NAIVE")
    return d.astimezone(timezone.utc)

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def initialize(db):
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS captures (
      capture_id TEXT PRIMARY KEY,
      provider TEXT NOT NULL CHECK(provider='API-Football'),
      resource TEXT NOT NULL,
      started_at_utc TEXT NOT NULL,
      completed_at_utc TEXT NOT NULL,
      source_published_at_utc TEXT,
      source_published_at_state TEXT NOT NULL
        CHECK(source_published_at_state='UNAVAILABLE'),
      origin TEXT NOT NULL CHECK(origin IN ('NETWORK_OBSERVED','SYNTHETIC_TEST')),
      response_sha256 TEXT NOT NULL,
      response_json TEXT NOT NULL,
      record_count INTEGER NOT NULL CHECK(record_count>0),
      prev_chain_sha256 TEXT NOT NULL,
      chain_sha256 TEXT NOT NULL UNIQUE,
      training_allowed INTEGER NOT NULL DEFAULT 0 CHECK(training_allowed=0)
    );
    CREATE TABLE IF NOT EXISTS capture_records (
      capture_id TEXT NOT NULL REFERENCES captures(capture_id),
      provider_fixture_id INTEGER NOT NULL,
      fixture_kickoff_utc TEXT NOT NULL,
      fixture_status TEXT NOT NULL,
      record_sha256 TEXT NOT NULL,
      record_json TEXT NOT NULL,
      PRIMARY KEY(capture_id, provider_fixture_id)
    );
    CREATE INDEX IF NOT EXISTS idx_capture_finished
      ON captures(completed_at_utc, capture_id);
    CREATE INDEX IF NOT EXISTS idx_record_fixture
      ON capture_records(provider_fixture_id, capture_id);
    CREATE TRIGGER IF NOT EXISTS capture_no_update BEFORE UPDATE ON captures
      BEGIN SELECT RAISE(ABORT,'CAPTURE_IMMUTABLE'); END;
    CREATE TRIGGER IF NOT EXISTS capture_no_delete BEFORE DELETE ON captures
      BEGIN SELECT RAISE(ABORT,'CAPTURE_IMMUTABLE'); END;
    CREATE TRIGGER IF NOT EXISTS capture_record_no_update BEFORE UPDATE ON capture_records
      BEGIN SELECT RAISE(ABORT,'RECORD_IMMUTABLE'); END;
    CREATE TRIGGER IF NOT EXISTS capture_record_no_delete BEFORE DELETE ON capture_records
      BEGIN SELECT RAISE(ABORT,'RECORD_IMMUTABLE'); END;
    """)

def validate_response(payload, season):
    if not isinstance(payload,dict) or payload.get("errors"):
        raise ValueError("INVALID_PROVIDER_RESPONSE")
    if (payload.get("paging") or {}).get("total",1)!=1:
        raise ValueError("INCOMPLETE_PAGING")
    items=payload.get("response")
    if not isinstance(items,list) or len(items)!=380:
        raise ValueError("UNEXPECTED_FIXTURE_COVERAGE")
    unique=set()
    for item in items:
        if not isinstance(item,dict):
            raise ValueError("NON_OBJECT_FIXTURE")
        f=item.get("fixture") or {}
        l=item.get("league") or {}
        fid=f.get("id")
        if (type(fid) is not int or fid<=0 or fid in unique):
            raise ValueError("DUPLICATE_OR_INVALID_ID")
        unique.add(fid)
        if l.get("id")!=39 or l.get("season")!=season:
            raise ValueError("LEAGUE_SEASON_MISMATCH")
        kickoff=as_utc(f.get("date"))
        if kickoff.year<season or kickoff.year>season+1:
            raise ValueError("OUT_OF_SEASON_KICKOFF")
        if not (f.get("status") or {}).get("short"):
            raise ValueError("MISSING_STATUS")
    return sorted(items,key=lambda x:x["fixture"]["id"])

def record_capture(db,payload,*,season,started_at_utc,completed_at_utc,
                   origin="SYNTHETIC_TEST"):
    initialize(db)
    start=as_utc(started_at_utc)
    end=as_utc(completed_at_utc)
    if start>end or (end-start).total_seconds()>180:
        raise ValueError("UNTRUSTWORTHY_CAPTURE_INTERVAL")
    if origin not in ("NETWORK_OBSERVED","SYNTHETIC_TEST"):
        raise ValueError("INVALID_ORIGIN")
    if origin=="NETWORK_OBSERVED":
        now=datetime.now(timezone.utc)
        if (end-now).total_seconds()>10 or (now-end).total_seconds()>180:
            raise ValueError("NETWORK_CAPTURE_CLOCK_INVALID")
    items=validate_response(payload,season)
    resource=f"fixtures?league=39&season={season}"
    response_hash=hexdigest(canonical(payload))
    body_rows=[(x["fixture"]["id"],x["fixture"]["date"],
                x["fixture"]["status"]["short"],canonical(x).decode("utf8"),
                hexdigest(canonical(x))) for x in items]
    db.execute("BEGIN IMMEDIATE")
    try:
        last=db.execute("SELECT chain_sha256 FROM captures ORDER BY rowid DESC LIMIT 1").fetchone()
        prev=last[0] if last else GENESIS
        summary={"provider":"API-Football","resource":resource,
                 "started_at_utc":started_at_utc,"completed_at_utc":completed_at_utc,
                 "source_published_at_utc":None,
                 "source_published_at_state":"UNAVAILABLE",
                 "origin":origin,"response_sha256":response_hash,
                 "record_count":len(items),"prev_chain_sha256":prev,
                 "record_hashes":[x[4] for x in body_rows]}
        chain=hexdigest(canonical(summary))
        capture_id=chain[:32]
        db.execute("""INSERT INTO captures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
                   (capture_id,"API-Football",resource,started_at_utc,completed_at_utc,
                    None,"UNAVAILABLE",origin,response_hash,canonical(payload).decode("utf8"),len(items),prev,chain))
        db.executemany("""INSERT INTO capture_records VALUES(?,?,?,?,?,?)""",
                       [(capture_id,fid,ko,st,h,b)
                        for fid,ko,st,b,h in body_rows])
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"capture_id":capture_id,"chain_sha256":chain,
            "response_sha256":response_hash,"records":len(items),
            "started_at_utc":started_at_utc,"completed_at_utc":completed_at_utc,
            "provider_publication_known":False,"origin":origin,
            "training_allowed":False}

def verify_chain(db):
    initialize(db)
    sessions=db.execute("""SELECT capture_id,provider,resource,started_at_utc,
      completed_at_utc,source_published_at_utc,source_published_at_state,
      origin,response_sha256,response_json,record_count,prev_chain_sha256,chain_sha256
      FROM captures ORDER BY rowid""").fetchall()
    prev=GENESIS
    for row in sessions:
        (cid,provider,resource,started,completed,published,state,origin,
         response_hash,response_json,count,prior,chain)=row
        if prior!=prev or provider!="API-Football" or published is not None or state!="UNAVAILABLE":
            raise ValueError("CAPTURE_CHAIN_METADATA_MISMATCH")
        if as_utc(start)>as_utc(completed):
            raise ValueError("REVERSED_CAPTURE_TIME")
        if hexdigest(canonical(json.loads(response_json)))!=response_hash:
            raise ValueError("TAMPERED_CAPTURE_RESPONSE")
        body=db.execute("""SELECT provider_fixture_id,record_json,record_sha256
                           FROM capture_records WHERE capture_id=?
                           ORDER BY provider_fixture_id""",(cid,)).fetchall()
        if len(body)!=count:
            raise ValueError("CAPTURE_ROW_COUNT_MISMATCH")
        response_items=validate_response(json.loads(response_json),
                            int(resource.split("season=")[-1]))
        if [x["fixture"]["id"] for x in response_items]!=[x[0] for x in body]:
            raise ValueError("RESPONSE_ROW_MISMATCH")
        hashes=[]
        for rowidx,(fid,raw,h) in enumerate(body):
            if canonical(response_items[rowidx]).decode("utf8")!=raw:
                raise ValueError("RESPONSE_ROW_PAYLOAD_MISMATCH")
            data=json.loads(raw)
            if data["fixture"]["id"]!=fid or hexdigest(canonical(data))!=h:
                raise ValueError("TAMPERED_CAPTURE_RECORD")
            hashes.append(h)
        summary={"provider":provider,"resource":resource,
                 "started_at_utc":started,"completed_at_utc":completed,
                 "source_published_at_utc":None,"source_published_at_state":state,
                 "origin":origin,"response_sha256":response_hash,
                 "record_count":count,"prev_chain_sha256":prev,
                 "record_hashes":hashes}
        if cid!=chain[:32] or hexdigest(canonical(summary))!=chain:
            raise ValueError("CAPTURE_CHAIN_HASH_MISMATCH")
        prev=chain
    return {"sessions":len(sessions),
            "fixture_records":db.execute("SELECT COUNT(*) FROM capture_records").fetchone()[0],
            "final_chain_sha256":prev,
            "provider_published_times_known":0,
            "training_allowed":False}

def select_result_asof(db,provider_fixture_id,forecast_cutoff_utc):
    """Evidence is restricted to *actual* archived observations before cutoff.

    Missing provider publication date stays null; result can only be used from
    a previous captured instant, and ONLY if after its historical fixture.
    No guarantee of a fully validated feature snapshot or of training approval.
    """
    cutoff=as_utc(forecast_cutoff_utc)
    found=db.execute("""
      SELECT c.completed_at_utc,c.origin,r.fixture_kickoff_utc,r.record_json,
             r.record_sha256,c.capture_id
      FROM capture_records r JOIN captures c ON c.capture_id=r.capture_id
      WHERE r.provider_fixture_id=?
      ORDER BY c.completed_at_utc DESC,c.capture_id DESC
    """,(provider_fixture_id,)).fetchall()
    for observed,origin,kickoff,raw,h,cid in found:
        if origin!="NETWORK_OBSERVED" or as_utc(observed)>cutoff or as_utc(kickoff)>=cutoff:
            continue
        item=json.loads(raw)
        if hexdigest(canonical(item))!=h:
            raise ValueError("TAMPERED_SOURCE_RECORD")
        if (item["fixture"]["status"]["short"]!=FINAL_STATUS):
            continue
        score=(item.get("score") or {}).get("fulltime") or {}
        gh,ga=score.get("home"),score.get("away")
        if not all(type(n) is int and n>=0 for n in (gh,ga)):
            continue
        return {"fixture_id":provider_fixture_id,
                "result_home_90":gh,"result_away_90":ga,
                "capture_id":cid,"observed_completed_at_utc":observed,
                "source_published_at_utc":None,
                "observed_before_forecast_cutoff":True,
                "historical_prematch_certification":False,
                "training_allowed":False}
    return None
