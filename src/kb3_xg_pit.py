"""Step11: append-only post-match PitchAPI xG observed-at ledger.

Optional historical xG can only be used in later predictions *after*
an authenticated capture. Unknown publication time remains NULL.
Strict provider fixture matches only; null never substituted by zero.
"""
from __future__ import annotations
import hashlib
import json
import math
import sqlite3
from datetime import timedelta,datetime,timezone
from src.kb3_pit_ledger import canonical,hexdigest,as_utc
from scripts.pitchapi_step06_audit import parse_shots
from src.kb3_identity_review import inspect_match

MIN_POSTMATCH_LAG=timedelta(hours=3)

def initialize_xg(db):
    db.executescript("""
      CREATE TABLE IF NOT EXISTS pit_xg_observations(
        observation_id TEXT PRIMARY KEY,
        pitch_match_id TEXT NOT NULL,
        api_football_fixture_id INTEGER,
        pitch_kickoff_utc TEXT NOT NULL,
        result_state TEXT NOT NULL CHECK(result_state IN
          ('COMPLETE_SHOT_XG','PARTIAL_SHOT_XG','NO_SHOTS','NO_PERIOD_LIST','INVALID_RESPONSE','INCOMPLETE_PERIOD')),
        identity_state TEXT NOT NULL,
        started_at_utc TEXT NOT NULL,
        completed_at_utc TEXT NOT NULL,
        provider_published_at_utc TEXT,
        xg_home REAL,
        xg_away REAL,
        raw_json TEXT NOT NULL,
        raw_sha256 TEXT NOT NULL,
        observation_sha256 TEXT NOT NULL,
        training_allowed INTEGER NOT NULL DEFAULT 0 CHECK(training_allowed=0),
        CHECK(provider_published_at_utc IS NULL),
        CHECK((xg_home IS NULL AND xg_away IS NULL) OR
              (xg_home>=0 AND xg_away>=0))
      );
      CREATE TRIGGER IF NOT EXISTS pit_xg_no_update BEFORE UPDATE ON pit_xg_observations
       BEGIN SELECT RAISE(ABORT,'XG_OBSERVATION_IMMUTABLE'); END;
      CREATE TRIGGER IF NOT EXISTS pit_xg_no_delete BEFORE DELETE ON pit_xg_observations
       BEGIN SELECT RAISE(ABORT,'XG_OBSERVATION_IMMUTABLE'); END;
    """)

def _inspect(record):
    (oid,match_id,fixture_id,kickoff,state,identity,started,completed,
     published,xgh,xga,raw,rawhash,recordhash,allow)=record
    if published is not None or allow!=0:
        raise ValueError("XG_PROVENANCE_VIOLATION")
    if as_utc(started)>as_utc(completed) or (as_utc(completed)-as_utc(started)).total_seconds()>180:
        raise ValueError("XG_TIME_NOT_CREDIBLE")
    envelope=json.loads(raw)
    if hexdigest(canonical(envelope))!=rawhash:
        raise ValueError("XG_RAW_HASH_MISMATCH")
    info={"pitch_match_id":match_id,"api_football_fixture_id":fixture_id,
          "pitch_kickoff_utc":kickoff,"result_state":state,
          "identity_state":identity,"started_at_utc":started,
          "completed_at_utc":completed,"xg_home":xgh,
          "xg_away":xga,"raw_sha256":rawhash}
    if oid!=recordhash[:32] or hexdigest(canonical(info))!=recordhash:
        raise ValueError("XG_OBSERVATION_HASH_MISMATCH")
    # Version-2 observations contain enough original provider metadata to
    # independently recompute matching and xG from the archived raw payload.
    if isinstance(envelope,dict) and envelope.get("schema")=="kb3-xg-source-envelope-v2":
        match=envelope.get("pitch_match")
        shots=envelope.get("shots_response")
        fixture_candidates=envelope.get("api_football_candidates")
        if not isinstance(match,dict) or not isinstance(fixture_candidates,list):
            raise ValueError("XG_SOURCE_ENVELOPE_INVALID")
        if match.get("id")!=match_id or match.get("time_utc")!=kickoff:
            raise ValueError("XG_SOURCE_MATCH_METADATA_MISMATCH")
        res=inspect_match(match,fixture_candidates)
        if res["state"]!=identity:
            raise ValueError("XG_IDENTITY_RECOMPUTATION_MISMATCH")
        source_teams=(match.get("home_team") or {}).get("id"),(match.get("away_team") or {}).get("id")
        parsed=parse_shots(shots,*source_teams)
        if parsed.get("state")!=state:
            raise ValueError("XG_SOURCE_STATE_MISMATCH")
        strict_source=(identity=="EXACT_TIME_NAMES_SCORE_FT" and state=="COMPLETE_SHOT_XG")
        expected_fid=res["fixture_id"] if strict_source else None
        if fixture_id!=expected_fid:
            raise ValueError("XG_CANONICAL_FIXTURE_MISMATCH")
        expected_home=parsed.get("home_xg_sum") if strict_source else None
        expected_away=parsed.get("away_xg_sum") if strict_source else None
        if xgh!=expected_home or xga!=expected_away:
            raise ValueError("XG_SOURCE_TOTALS_MISMATCH")
    else:
        # Legacy observations lacked match metadata: keep quarantine, never
        # retroactively promote to strict or certified evidence.
        if identity in ("EXACT_NAMES_DATE_SCORE","EXACT_TIME_NAMES_SCORE_FT"):
            raise ValueError("XG_LEGACY_SOURCE_METADATA_MISSING")
    if (identity!="EXACT_TIME_NAMES_SCORE_FT" or state!="COMPLETE_SHOT_XG"):
        if xgh is not None or xga is not None or fixture_id is not None:
            raise ValueError("UNVERIFIED_XG_MUST_BE_NULL")
    else:
        if not (type(fixture_id) is int and type(xgh) in (int,float) and
                type(xga) in (int,float) and math.isfinite(xgh) and
                math.isfinite(xga)):
            raise ValueError("MISSING_VERIFIED_XG")
        if as_utc(completed)<as_utc(kickoff)+MIN_POSTMATCH_LAG:
            raise ValueError("XG_TOO_SOON_AFTER_MATCH")
    return info

def record_xg(db, match, shots_response, football_fixtures, *,
              started_at_utc, completed_at_utc, origin="NETWORK_OBSERVED"):
    if origin!="NETWORK_OBSERVED":
        raise ValueError("SYNTHETIC_NOT_PIT")
    initialize_xg(db)
    started=as_utc(started_at_utc);completed=as_utc(completed_at_utc)
    if started>completed or (completed-started).total_seconds()>180:
        raise ValueError("XG_TIME_RANGE_INVALID")
    host_clock=datetime.now(timezone.utc)
    if (completed-host_clock).total_seconds()>10 or (host_clock-completed).total_seconds()>180:
        raise ValueError("XG_NETWORK_CLOCK_NOT_CURRENT")
    if as_utc(match["time_utc"])+MIN_POSTMATCH_LAG>completed:
        raise ValueError("XG_CANNOT_BE_PREMATCH")
    mid=match["id"]
    if not isinstance(mid,str) or not mid.startswith("m_"):
        raise ValueError("INVALID_PITCH_MATCH_ID")
    teams=(match.get("home_team") or {}).get("id"),(match.get("away_team") or {}).get("id")
    if not all(teams) or teams[0]==teams[1]:
        raise ValueError("INVALID_PITCH_TEAM_IDS")
    result=parse_shots(shots_response,teams[0],teams[1])
    # Preserve what was sent by both sources inside encrypted payload, so
    # the identity decision can be re-evaluated independently years later.
    candidates=[]
    for game in football_fixtures:
        try:
            game_time=as_utc((game.get("fixture") or {})["date"])
        except (KeyError,TypeError,ValueError,AttributeError):
            continue
        if abs(game_time-as_utc(match["time_utc"])).total_seconds()<=3*3600:
            candidates.append(game)
    link=inspect_match(match,candidates)
    state=result.get("state","INVALID_RESPONSE")
    if state not in ("COMPLETE_SHOT_XG","PARTIAL_SHOT_XG","NO_SHOTS",
                     "NO_PERIOD_LIST","INVALID_RESPONSE","INCOMPLETE_PERIOD"):
        state="INVALID_RESPONSE"
    strict=(link["state"]=="EXACT_TIME_NAMES_SCORE_FT" and state=="COMPLETE_SHOT_XG")
    xgh=result.get("home_xg_sum") if strict else None
    xga=result.get("away_xg_sum") if strict else None
    fid=link["fixture_id"] if strict else None
    envelope={"schema":"kb3-xg-source-envelope-v2",
              "pitch_match":match,"shots_response":shots_response,
              "api_football_candidates":candidates,
              "review_candidate_ids":link.get("review_candidates",[])}
    raw=canonical(envelope).decode("utf8")
    info={"pitch_match_id":mid,"api_football_fixture_id":fid,
          "pitch_kickoff_utc":match["time_utc"],"result_state":state,
          "identity_state":link["state"],"started_at_utc":started_at_utc,
          "completed_at_utc":completed_at_utc,"xg_home":xgh,
          "xg_away":xga,"raw_sha256":hexdigest(raw.encode("utf8"))}
    recordhash=hexdigest(canonical(info))
    db.execute("INSERT INTO pit_xg_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
       (recordhash[:32],mid,fid,match["time_utc"],state,
        link["state"],started_at_utc,completed_at_utc,None,
        xgh,xga,raw,info["raw_sha256"],recordhash))
    db.commit()
    return {"accepted":strict,"identity_state":link["state"],"xg_state":state,
            "observation_id":recordhash[:32],"captured_at_utc":completed_at_utc,
            "training_allowed":False}

def verify_xg(db):
    initialize_xg(db)
    rows=db.execute("SELECT * FROM pit_xg_observations ORDER BY rowid").fetchall()
    stats={"captured":len(rows),"strict_complete":0,"quarantined":0,
           "missing":0,"last_observation_sha256":None,
           "provider_publication_confirmed":0,"training_allowed":False}
    for row in rows:
        info=_inspect(row)
        if info["identity_state"]=="EXACT_TIME_NAMES_SCORE_FT" and info["result_state"]=="COMPLETE_SHOT_XG":
            stats["strict_complete"]+=1
        else:
            stats["quarantined"]+=1
            stats["missing"]+=int(info["result_state"]!="COMPLETE_SHOT_XG")
        stats["last_observation_sha256"]=row[13]
    return stats

def select_xg_asof(db,fixture_id,cutoff_utc):
    cutoff=as_utc(cutoff_utc)
    rows=db.execute("""SELECT * FROM pit_xg_observations
                       WHERE api_football_fixture_id=?
                       ORDER BY completed_at_utc DESC,observation_id DESC""",
                    (fixture_id,)).fetchall()
    for row in rows:
        info=_inspect(row)
        if as_utc(info["completed_at_utc"])>cutoff:
            continue
        if info["identity_state"]!="EXACT_TIME_NAMES_SCORE_FT" or info["result_state"]!="COMPLETE_SHOT_XG":
            return None
        return {"home_xg":info["xg_home"],"away_xg":info["xg_away"],
                "observed_completed_at_utc":info["completed_at_utc"],
                "origin":"NETWORK_OBSERVED",
                "provider_published_at_utc":None,"training_allowed":False}
    return None
