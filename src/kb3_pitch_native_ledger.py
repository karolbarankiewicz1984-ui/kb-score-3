"""Immutable PitchAPI-only observed-at ledger. Step11, no ML or prediction.

Every API response is kept in full and hashed. Match IDs are native PitchAPI,
not reconstructed using team names or API-Football. Observed-at is the host's
network capture completion, NOT the provider's original publication time.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime,timezone
from src.kb3_pit_ledger import canonical,hexdigest,as_utc,GENESIS
from src.kb3_pitch_native import check_season,verify_native_shots

SEASON="2026/2027"
RESOURCE="pitchapi:premier-league:2026/2027:matches:all"
TYPE_SHOTS="shots"
TYPE_MATCHES="matches"


def init(db):
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS pitch_captures(
        ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
        capture_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL CHECK(kind IN ('matches','shots')),
        resource TEXT NOT NULL,
        season TEXT NOT NULL CHECK(season='2026/2027'),
        started_at_utc TEXT NOT NULL,
        completed_at_utc TEXT NOT NULL,
        origin TEXT NOT NULL CHECK(origin IN ('NETWORK_OBSERVED','SYNTHETIC_TEST')),
        published_at_utc TEXT CHECK(published_at_utc IS NULL),
        response_json TEXT NOT NULL,
        response_sha256 TEXT NOT NULL,
        record_count INTEGER NOT NULL CHECK(record_count>0),
        previous_sha256 TEXT NOT NULL,
        chain_sha256 TEXT NOT NULL UNIQUE,
        training_allowed INTEGER NOT NULL CHECK(training_allowed=0)
      );
      CREATE TABLE IF NOT EXISTS pitch_records(
        capture_id TEXT NOT NULL REFERENCES pitch_captures(capture_id),
        pitch_match_id TEXT NOT NULL,
        record_json TEXT NOT NULL,
        record_sha256 TEXT NOT NULL,
        PRIMARY KEY(capture_id,pitch_match_id)
      );
      CREATE INDEX IF NOT EXISTS idx_pitch_capture_clock
        ON pitch_captures(completed_at_utc,ordinal);
      CREATE INDEX IF NOT EXISTS idx_pitch_match_history
        ON pitch_records(pitch_match_id,capture_id);
      CREATE TRIGGER IF NOT EXISTS pitch_capture_no_update BEFORE UPDATE ON pitch_captures
       BEGIN SELECT RAISE(ABORT,'PITCH_CAPTURE_IMMUTABLE'); END;
      CREATE TRIGGER IF NOT EXISTS pitch_capture_no_delete BEFORE DELETE ON pitch_captures
       BEGIN SELECT RAISE(ABORT,'PITCH_CAPTURE_IMMUTABLE'); END;
      CREATE TRIGGER IF NOT EXISTS pitch_record_no_update BEFORE UPDATE ON pitch_records
       BEGIN SELECT RAISE(ABORT,'PITCH_RECORD_IMMUTABLE'); END;
      CREATE TRIGGER IF NOT EXISTS pitch_record_no_delete BEFORE DELETE ON pitch_records
       BEGIN SELECT RAISE(ABORT,'PITCH_RECORD_IMMUTABLE'); END;
    """)


def _validate_interval(started,completed,origin):
    a,b=as_utc(started),as_utc(completed)
    if a>b or (b-a).total_seconds()>180:
        raise ValueError("PITCH_CAPTURE_INTERVAL_INVALID")
    if origin not in ("NETWORK_OBSERVED","SYNTHETIC_TEST"):
        raise ValueError("PITCH_CAPTURE_ORIGIN_INVALID")
    if origin=="NETWORK_OBSERVED":
        now=datetime.now(timezone.utc)
        if (b-now).total_seconds()>10 or (now-b).total_seconds()>180:
            raise ValueError("PITCH_BACKDATED_OR_FUTURE_NETWORK_CAPTURE")
    return a,b


def _fixture_asof(db,mid,at):
    rows=db.execute("""SELECT c.completed_at_utc,r.record_json
       FROM pitch_records r JOIN pitch_captures c ON c.capture_id=r.capture_id
       WHERE r.pitch_match_id=? AND c.kind='matches' AND c.origin='NETWORK_OBSERVED'
       ORDER BY c.completed_at_utc DESC,c.ordinal DESC""",(mid,)).fetchall()
    for t,raw in rows:
        if as_utc(t)<=at:
            return json.loads(raw)
    return None


def _as_records(db,kind,payload,*,started):
    if kind==TYPE_MATCHES:
        check_season(payload,SEASON,expected_count=380,require_upcoming=True)
        return sorted(((m["id"],m) for m in payload),key=lambda r:r[0])
    if kind==TYPE_SHOTS:
        if not isinstance(payload,dict) or not isinstance(payload.get("data"),dict):
            raise ValueError("PITCH_SHOTS_RESPONSE_INVALID")
        mid=payload["data"].get("match_id")
        if not isinstance(mid,str):
            raise ValueError("PITCH_SHOT_NATIVE_ID_MISSING")
        source=_fixture_asof(db,mid,as_utc(started))
        if source is None:
            raise ValueError("PITCH_SHOTS_REQUIRE_PRIOR_OBSERVED_FIXTURE")
        # Native ID and team IDs re-validated from last pre-shots fixture.
        verify_native_shots(source,payload,observed_at_utc=started)
        return [(mid,payload)]
    raise ValueError("PITCH_UNKNOWN_CAPTURE_KIND")


def record(db,kind,payload,*,started_at_utc,completed_at_utc,
           origin="SYNTHETIC_TEST"):
    init(db)
    start,end=_validate_interval(started_at_utc,completed_at_utc,origin)
    if kind not in (TYPE_SHOTS,TYPE_MATCHES):
        raise ValueError("PITCH_UNKNOWN_CAPTURE_KIND")
    last=db.execute("""SELECT completed_at_utc,chain_sha256
                       FROM pitch_captures ORDER BY ordinal DESC LIMIT 1""").fetchone()
    if last and (start<as_utc(last[0])):
        raise ValueError("PITCH_NON_MONOTONE_CAPTURE")
    rows=_as_records(db,kind,payload,started=started_at_utc)
    resource=RESOURCE if kind==TYPE_MATCHES else f"pitchapi:match:{rows[0][0]}:shots"
    body=[(mid,canonical(obj).decode("utf8"),hexdigest(canonical(obj))) for mid,obj in rows]
    content=canonical(payload).decode("utf8")
    src_hash=hexdigest(content.encode("utf8"))
    prior=last[1] if last else GENESIS
    statement={"provider":"PitchAPI","kind":kind,"resource":resource,
       "season":SEASON,"started_at_utc":started_at_utc,
       "completed_at_utc":completed_at_utc,"origin":origin,
       "published_at_utc":None,"response_sha256":src_hash,
       "record_count":len(body),"previous_sha256":prior,
       "record_sha256":[r[2] for r in body]}
    chain=hexdigest(canonical(statement))
    cid=chain[:32]
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("""INSERT INTO pitch_captures(
           capture_id,kind,resource,season,started_at_utc,completed_at_utc,
           origin,published_at_utc,response_json,response_sha256,
           record_count,previous_sha256,chain_sha256,training_allowed)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
           (cid,kind,resource,SEASON,started_at_utc,completed_at_utc,
            origin,None,content,src_hash,len(body),prior,chain))
        db.executemany("""INSERT INTO pitch_records VALUES(?,?,?,?)""",
                        [(cid,mid,raw,h) for mid,raw,h in body])
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"capture_id":cid,"kind":kind,"count":len(body),
            "observed_at_utc":completed_at_utc,"chain_sha256":chain,
            "response_sha256":src_hash,"training_allowed":False,
            "initial_provider_published_at_utc":None}


def verify(db):
    init(db)
    sessions=db.execute("""SELECT capture_id,kind,resource,season,started_at_utc,
      completed_at_utc,origin,published_at_utc,response_json,response_sha256,
      record_count,previous_sha256,chain_sha256,training_allowed
      FROM pitch_captures ORDER BY ordinal""").fetchall()
    previous=GENESIS
    prev_time=None
    kinds={"matches":0,"shots":0}
    for (cid,kind,resource,season,started,completed,origin,published,
         raw,rawhash,count,prior,chain,train) in sessions:
        a,b=_validate_interval(started,completed,"SYNTHETIC_TEST")
        if (prior!=previous or published is not None or train!=0 or
            season!=SEASON or prev_time is not None and a<prev_time):
            raise ValueError("PITCH_CHAIN_METADATA_INVALID")
        if kind not in kinds:
            raise ValueError("PITCH_UNKNOWN_CAPTURE_KIND")
        expected_resource=RESOURCE if kind=="matches" else None
        if expected_resource and resource!=expected_resource:
            raise ValueError("PITCH_SOURCE_RESOURCE_MISMATCH")
        obj=json.loads(raw)
        if hexdigest(canonical(obj))!=rawhash:
            raise ValueError("PITCH_CAPTURE_SHA_INVALID")
        if kind=="matches":
            expected=sorted(((m["id"],m) for m in obj),key=lambda x:x[0])
            check_season(obj,SEASON,expected_count=380,require_upcoming=True)
        else:
            if not isinstance(obj,dict) or not isinstance(obj.get("data"),dict):
                raise ValueError("PITCH_SHOT_OBJECT_INVALID")
            mid=obj["data"].get("match_id")
            expected=[(mid,obj)]
            if resource!=f"pitchapi:match:{mid}:shots":
                raise ValueError("PITCH_SHOT_RESOURCE_MISMATCH")
            # Recompute source association against latest preceding source.
            source=_fixture_asof(db,mid,a)
            if not source:
                raise ValueError("PITCH_ORPHAN_SHOT_OBSERVATION")
            verify_native_shots(source,obj,observed_at_utc=completed)
        records=db.execute("""SELECT pitch_match_id,record_json,record_sha256
          FROM pitch_records WHERE capture_id=? ORDER BY pitch_match_id""",
          (cid,)).fetchall()
        if len(expected)!=count or len(records)!=count:
            raise ValueError("PITCH_CAPTURE_COUNT_INVALID")
        digests=[]
        for (mid,payload),(actual_id,actual_raw,actual_sha) in zip(expected,records):
            if mid!=actual_id or canonical(payload).decode("utf8")!=actual_raw:
                raise ValueError("PITCH_SOURCE_RECORD_CHANGED")
            h=hexdigest(canonical(payload))
            if actual_sha!=h:
                raise ValueError("PITCH_SOURCE_RECORD_SHA_INVALID")
            digests.append(h)
        statement={"provider":"PitchAPI","kind":kind,"resource":resource,
          "season":season,"started_at_utc":started,
          "completed_at_utc":completed,"origin":origin,
          "published_at_utc":None,"response_sha256":rawhash,
          "record_count":count,"previous_sha256":prior,
          "record_sha256":digests}
        if chain!=hexdigest(canonical(statement)) or cid!=chain[:32]:
            raise ValueError("PITCH_CHAIN_TAMPERED")
        previous=chain
        prev_time=b
        kinds[kind]+=1
    return {"captures":len(sessions),"fixture_captures":kinds["matches"],
      "shot_captures":kinds["shots"],"stored_records":db.execute(
          "SELECT COUNT(*) FROM pitch_records").fetchone()[0],
      "last_chain_sha256":previous,
      "initial_provider_publication_proven":False,
      "training_allowed":False}


def latest_asof(db,forecast_cutoff_utc):
    """Return latest actually observed match state, never post-cutoff revisions."""
    cutoff=as_utc(forecast_cutoff_utc)
    snapshots=db.execute("""SELECT completed_at_utc,response_json
      FROM pitch_captures WHERE kind='matches' AND origin='NETWORK_OBSERVED'
      ORDER BY completed_at_utc DESC,ordinal DESC""").fetchall()
    for t,raw in snapshots:
        if as_utc(t)<=cutoff:
            return {m["id"]:m for m in json.loads(raw)}
    return None


def shots_asof(db,match_id,cutoff_utc):
    cutoff=as_utc(cutoff_utc)
    latest=latest_asof(db,cutoff_utc)
    if latest is None or match_id not in latest:
        return None
    source=latest[match_id]
    rows=db.execute("""SELECT completed_at_utc,response_json
      FROM pitch_captures WHERE kind='shots' AND origin='NETWORK_OBSERVED'
        AND resource=? ORDER BY completed_at_utc DESC,ordinal DESC""",
       (f"pitchapi:match:{match_id}:shots",)).fetchall()
    for t,raw in rows:
        if as_utc(t)>cutoff:
            continue
        if source["status"]!="finished":
            return None
        x=verify_native_shots(source,json.loads(raw),observed_at_utc=t)
        return x if x["shot_state"]=="COMPLETE_SHOT_XG" else None
    return None
