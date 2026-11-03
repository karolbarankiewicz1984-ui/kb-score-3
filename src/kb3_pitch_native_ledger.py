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
from src.kb3_pitch_native import check_season,verify_native_shots,_verify_native_shots_v1
from src.kb3_pitch_source_pair import MAX_PAIR_SECONDS

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
      CREATE TABLE IF NOT EXISTS pitch_source_pairs(
        capture_id TEXT PRIMARY KEY REFERENCES pitch_captures(capture_id),
        stats_json TEXT NOT NULL, stats_sha256 TEXT NOT NULL,
        stats_started_at_utc TEXT NOT NULL, stats_completed_at_utc TEXT NOT NULL,
        origin TEXT NOT NULL, pair_sha256 TEXT NOT NULL UNIQUE
      );
      CREATE TRIGGER IF NOT EXISTS pitch_pair_no_update BEFORE UPDATE ON pitch_source_pairs
       BEGIN SELECT RAISE(ABORT,'PITCH_PAIR_IMMUTABLE'); END;
      CREATE TRIGGER IF NOT EXISTS pitch_pair_no_delete BEFORE DELETE ON pitch_source_pairs
       BEGIN SELECT RAISE(ABORT,'PITCH_PAIR_IMMUTABLE'); END;
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


def _fixture_asof(db,mid,at,*,include_synthetic=False):
    rows=db.execute("""SELECT c.completed_at_utc,r.record_json,c.origin
       FROM pitch_records r JOIN pitch_captures c ON c.capture_id=r.capture_id
       WHERE r.pitch_match_id=? AND c.kind='matches'
       ORDER BY c.completed_at_utc DESC,c.ordinal DESC""",(mid,)).fetchall()
    for t,raw,origin in rows:
        if as_utc(t)<=at and (origin=="NETWORK_OBSERVED" or include_synthetic):
            return json.loads(raw)
    return None


def _as_records(db,kind,payload,*,started,origin):
    if kind==TYPE_MATCHES:
        check_season(payload,SEASON,expected_count=380,require_upcoming=False)
        return sorted(((m["id"],m) for m in payload),key=lambda r:r[0])
    if kind==TYPE_SHOTS:
        if not isinstance(payload,dict) or not isinstance(payload.get("data"),dict):
            raise ValueError("PITCH_SHOTS_RESPONSE_INVALID")
        mid=payload["data"].get("match_id")
        if not isinstance(mid,str):
            raise ValueError("PITCH_SHOT_NATIVE_ID_MISSING")
        source=_fixture_asof(db,mid,as_utc(started),include_synthetic=origin=="SYNTHETIC_TEST")
        if source is None:
            raise ValueError("PITCH_SHOTS_REQUIRE_PRIOR_OBSERVED_FIXTURE")
        # Native ID and team IDs re-validated from last pre-shots fixture.
        verify_native_shots(source,payload,observed_at_utc=started)
        return [(mid,payload)]
    raise ValueError("PITCH_UNKNOWN_CAPTURE_KIND")


def _pair_statement(payload,stats,started,completed,stats_started,stats_completed,origin):
    a,b=_validate_interval(stats_started,stats_completed,"SYNTHETIC_TEST")
    if as_utc(completed)>a or (b-as_utc(started)).total_seconds()>MAX_PAIR_SECONDS:
        raise ValueError("PITCH_PAIR_CAPTURE_WINDOW_INVALID")
    return {"shots_sha256":hexdigest(canonical(payload)),
            "stats_sha256":hexdigest(canonical(stats)),"stats_started_at_utc":stats_started,
            "stats_completed_at_utc":stats_completed,"origin":origin}

def record(db,kind,payload,*,started_at_utc,completed_at_utc,
           origin="SYNTHETIC_TEST",stats_payload=None,
           stats_started_at_utc=None,stats_completed_at_utc=None):
    if db.in_transaction:
        raise ValueError("PITCH_CALLER_TRANSACTION_ACTIVE")
    init(db)
    start,end=_validate_interval(started_at_utc,completed_at_utc,origin)
    if kind not in (TYPE_SHOTS,TYPE_MATCHES):
        raise ValueError("PITCH_UNKNOWN_CAPTURE_KIND")
    db.execute("BEGIN IMMEDIATE")
    try:
        # Read the previous chain only after acquiring the writer lock.
        last=db.execute("""SELECT COALESCE(p.stats_completed_at_utc,c.completed_at_utc),c.chain_sha256
          FROM pitch_captures c LEFT JOIN pitch_source_pairs p USING(capture_id)
          ORDER BY c.ordinal DESC LIMIT 1""").fetchone()
        if last and start<as_utc(last[0]):
            raise ValueError("PITCH_NON_MONOTONE_CAPTURE")
        rows=_as_records(db,kind,payload,started=started_at_utc,origin=origin)
        resource=RESOURCE if kind==TYPE_MATCHES else f"pitchapi:match:{rows[0][0]}:shots:unpaired-v2"
        pair=None
        if stats_payload is not None:
            if kind!=TYPE_SHOTS:
                raise ValueError("PITCH_STATS_REQUIRE_SHOTS")
            _validate_interval(stats_started_at_utc,stats_completed_at_utc,origin)
            pair=_pair_statement(payload,stats_payload,started_at_utc,completed_at_utc,
                                 stats_started_at_utc,stats_completed_at_utc,origin)
            source=_fixture_asof(db,rows[0][0],start,include_synthetic=origin=="SYNTHETIC_TEST")
            result=verify_native_shots(source,payload,observed_at_utc=started_at_utc,
                                       stats_payload=stats_payload)
            if result["shot_state"]!="COMPLETE_SHOT_XG":
                raise ValueError("PITCH_SOURCE_PAIR_INCOMPLETE:"+result.get("reason",""))
            resource=f"pitchapi:match:{rows[0][0]}:shots:paired-v2"
        elif stats_started_at_utc is not None or stats_completed_at_utc is not None:
            raise ValueError("PITCH_STATS_PAYLOAD_MISSING")
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
        if pair is not None:
            statement["pair_sha256"]=hexdigest(canonical(pair))
        chain=hexdigest(canonical(statement));cid=chain[:32]
        db.execute("""INSERT INTO pitch_captures(
           capture_id,kind,resource,season,started_at_utc,completed_at_utc,
           origin,published_at_utc,response_json,response_sha256,
           record_count,previous_sha256,chain_sha256,training_allowed)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
           (cid,kind,resource,SEASON,started_at_utc,completed_at_utc,
            origin,None,content,src_hash,len(body),prior,chain))
        db.executemany("""INSERT INTO pitch_records VALUES(?,?,?,?)""",
                        [(cid,mid,raw,h) for mid,raw,h in body])
        if pair is not None:
            db.execute("INSERT INTO pitch_source_pairs VALUES(?,?,?,?,?,?,?)",
              (cid,canonical(stats_payload).decode("utf8"),pair["stats_sha256"],
               stats_started_at_utc,stats_completed_at_utc,origin,statement["pair_sha256"]))
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("PITCH_PAIR_FOREIGN_KEY_ERROR")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"capture_id":cid,"kind":kind,"count":len(body),
            "observed_at_utc":completed_at_utc,"chain_sha256":chain,
            "response_sha256":src_hash,"training_allowed":False,
            "initial_provider_published_at_utc":None}

def _stored_pair(db,cid,obj,source,started,completed,origin):
    row=db.execute("SELECT stats_json,stats_sha256,stats_started_at_utc,stats_completed_at_utc,origin,pair_sha256 FROM pitch_source_pairs WHERE capture_id=?",(cid,)).fetchone()
    if row is None:
        raise ValueError("PITCH_SOURCE_PAIR_MISSING")
    raw,digest,a,b,pair_origin,pair_sha=row
    stats=json.loads(raw)
    pair=_pair_statement(obj,stats,started,completed,a,b,origin)
    if pair_origin!=origin or digest!=pair["stats_sha256"] or pair_sha!=hexdigest(canonical(pair)):
        raise ValueError("PITCH_SOURCE_PAIR_TAMPERED")
    # shots_asof() must authenticate the pair's anchor even without verify().
    c=db.execute("""SELECT kind,resource,season,started_at_utc,completed_at_utc,origin,
        response_json,response_sha256,record_count,previous_sha256,chain_sha256
        FROM pitch_captures WHERE capture_id=?""",(cid,)).fetchone()
    if c is None:
        raise ValueError("PITCH_SOURCE_PAIR_CAPTURE_MISSING")
    kind,resource,season,start,end,org,shot_raw,shot_sha,count,prior,chain=c
    records=db.execute("SELECT pitch_match_id,record_json,record_sha256 FROM pitch_records WHERE capture_id=?",(cid,)).fetchall()
    if (kind!="shots" or not resource.endswith(":shots:paired-v2")
        or (start,end,org)!=(started,completed,origin) or count!=1 or len(records)!=1
        or shot_raw!=canonical(obj).decode("utf8") or shot_sha!=pair["shots_sha256"]
        or records[0]!=(obj["data"]["match_id"],shot_raw,shot_sha)):
        raise ValueError("PITCH_SOURCE_PAIR_ANCHOR_CHANGED")
    statement={"provider":"PitchAPI","kind":kind,"resource":resource,"season":season,
        "started_at_utc":start,"completed_at_utc":end,"origin":org,"published_at_utc":None,
        "response_sha256":shot_sha,"record_count":1,"previous_sha256":prior,
        "record_sha256":[shot_sha],"pair_sha256":pair_sha}
    if chain!=hexdigest(canonical(statement)) or cid!=chain[:32]:
        raise ValueError("PITCH_SOURCE_PAIR_ANCHOR_CHANGED")
    result=verify_native_shots(source,obj,observed_at_utc=started,stats_payload=stats)
    if result["shot_state"]!="COMPLETE_SHOT_XG":
        raise ValueError("PITCH_SOURCE_PAIR_INVALID")
    result["captured_at_utc"]=b
    return pair_sha,b,result


def verify(db):
    # Read-only authentication must NEVER initialize DDL on a restored mode=ro
    # database; SQLite attempts writes even for CREATE IF NOT EXISTS.
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pitch_source_pairs'").fetchone():
        if db.execute("""SELECT 1 FROM pitch_source_pairs p LEFT JOIN pitch_captures c USING(capture_id)
             WHERE c.capture_id IS NULL OR c.resource NOT LIKE '%:shots:paired-v2' LIMIT 1""").fetchone():
            raise ValueError("PITCH_ORPHAN_SOURCE_PAIR")
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
            origin not in ("NETWORK_OBSERVED","SYNTHETIC_TEST") or
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
            check_season(obj,SEASON,expected_count=380,require_upcoming=False)
        else:
            if not isinstance(obj,dict) or not isinstance(obj.get("data"),dict):
                raise ValueError("PITCH_SHOT_OBJECT_INVALID")
            mid=obj["data"].get("match_id")
            expected=[(mid,obj)]
            if resource not in (f"pitchapi:match:{mid}:shots",f"pitchapi:match:{mid}:shots:unpaired-v2",f"pitchapi:match:{mid}:shots:paired-v2"):
                raise ValueError("PITCH_SHOT_RESOURCE_MISMATCH")
            # Recompute source association against latest preceding source.
            source=_fixture_asof(db,mid,a,include_synthetic=origin=="SYNTHETIC_TEST")
            if not source:
                raise ValueError("PITCH_ORPHAN_SHOT_OBSERVATION")
            # Authenticate old bytes without recertifying V1 as paired evidence.
            _verify_native_shots_v1(source,obj,observed_at_utc=completed)
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
        if resource.endswith(":shots:paired-v2"):
            pair_sha,pair_end,_=_stored_pair(db,cid,obj,source,started,completed,origin)
            statement["pair_sha256"]=pair_sha
            b=as_utc(pair_end)
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
    rows=db.execute("""SELECT completed_at_utc,response_json,capture_id,started_at_utc,resource
      FROM pitch_captures WHERE kind='shots' AND origin='NETWORK_OBSERVED'
        AND resource IN (?,?,?) ORDER BY completed_at_utc DESC,ordinal DESC""",
       tuple(f"pitchapi:match:{match_id}:shots"+suffix for suffix in ("",":unpaired-v2",":paired-v2"))).fetchall()
    for t,raw,cid,started,resource in rows:
        if as_utc(t)>cutoff:
            continue
        if source["status"]!="finished":
            return None
        if not resource.endswith(":paired-v2"):
            return None
        _,completed,x=_stored_pair(db,cid,json.loads(raw),source,started,t,"NETWORK_OBSERVED")
        return x if as_utc(completed)<=cutoff else None
    return None
