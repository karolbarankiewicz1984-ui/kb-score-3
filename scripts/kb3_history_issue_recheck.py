"""Append-only rechecks for PitchAPI xG disagreement and absent yellow-card stats.

Authentic re-downloads of shots+stats, independent event timeline for cards.
Never alter historical original observations or invent old publication times.
Recheck evidence is encrypted and independent of model/production forecasts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
from collections import Counter
from datetime import timedelta
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain
from scripts.kb3_historical_pitchapi_backfill import (
    DB, PUBLIC_KEY, ROOT, native_xg_verified,
)
from src.kb3_historical_feature_quality import raw_stat
from src.kb3_pit_ledger import as_utc, utc_now
from src.kb3_pitch_uefa_evidence import add_observation, seal
from src.kb3_step14_pitchapi_xg_semantics import (
    SemanticAuditError, parse_native_shots, parse_native_team_stats,
)

ISSUE_ROOT = ROOT/"data/pit_sidecar/historical_issue_rechecks"
ISSUE_DB = ROOT/"data/research/historical_multistat/issue_rechecks.sqlite"
SCHEMA="kb3-historical-issue-recheck-v1-20261103"
MAX_XG=30
MAX_CARDS=45
MAX_CALLS=115

SQL="""
CREATE TABLE IF NOT EXISTS issue_rechecks(
 scope TEXT NOT NULL, match_id TEXT NOT NULL, issue_type TEXT NOT NULL
    CHECK(issue_type IN ('XG','YELLOW_CARDS')),
 initial_issue TEXT NOT NULL,
 status TEXT NOT NULL,
 observed_at_utc TEXT NOT NULL,
 source_chain_sha256 TEXT NOT NULL,
 source_payload_sha256 TEXT NOT NULL,
 native_home_team_id TEXT NOT NULL, native_away_team_id TEXT NOT NULL,
 stats_xg_home REAL, stats_xg_away REAL,
 shots_xg_home REAL, shots_xg_away REAL,
 xg_abs_delta_home REAL, xg_abs_delta_away REAL,
 xg_verified_home REAL, xg_verified_away REAL,
 yellow_events_home INTEGER, yellow_events_away INTEGER,
 original_provider_first_published_at_utc TEXT
   CHECK(original_provider_first_published_at_utc IS NULL),
 PRIMARY KEY(scope,match_id,issue_type),
 CHECK((status='XG_REVERIFIED'
        AND issue_type='XG'
        AND xg_verified_home IS NOT NULL AND xg_verified_away IS NOT NULL)
       OR status!='XG_REVERIFIED'),
 CHECK((status='EVENT_YELLOW_CONFIRMED'
        AND issue_type='YELLOW_CARDS'
        AND yellow_events_home IS NOT NULL AND yellow_events_away IS NOT NULL)
       OR status!='EVENT_YELLOW_CONFIRMED')
);
CREATE TRIGGER IF NOT EXISTS issue_no_update BEFORE UPDATE ON issue_rechecks
 BEGIN SELECT RAISE(ABORT,'ISSUE_SOURCE_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS issue_no_delete BEFORE DELETE ON issue_rechecks
 BEGIN SELECT RAISE(ABORT,'ISSUE_SOURCE_IMMUTABLE'); END;
"""

def candidates(path, issue_db=ISSUE_DB):
    with sqlite3.connect(path) as db:
        rows=db.execute("""SELECT scope,season,match_id,kickoff_utc,home_team_id,
          away_team_id,stat_items_json,xg_status
          FROM observations ORDER BY scope,match_id""").fetchall()
    attempted=set()
    if Path(issue_db).exists():
        with sqlite3.connect(issue_db) as db:
            attempted=set(db.execute("SELECT scope,match_id,issue_type FROM issue_rechecks"))
    xg=[];cards=[]
    for scope,season,mid,ko,home,away,items,status in rows:
        if scope=="ENG":
            raise ValueError("PROTECTED_TEST_SCOPE")
        f={"id":mid,"time_utc":ko,"home_team":{"id":home},
           "away_team":{"id":away},"season":season,"scope":scope,
           "items":json.loads(items),"xg_status":status}
        if status!="VERIFIED" and (scope,mid,"XG") not in attempted:
            xg.append(f)
        if (raw_stat(f,"yellow_cards","home") is None or
            raw_stat(f,"yellow_cards","away") is None):
            if (scope,mid,"YELLOW_CARDS") not in attempted:
                cards.append(f)
    # Use actual strict last-five targets to prioritize still-untried issues.
    # Missing prior fixture index in minimal legacy tests falls back to stable
    # league/ID ordering; neither branch may fabricate card/xG values.
    from scripts.kb3_history_gain_first import issue_priority_scores, UNDERSERVED
    card_scores,xg_scores=issue_priority_scores(path,issue_db)
    def key(row,scores):
        ident=(row["scope"],row["id"])
        return (-scores.get(ident,0.0),
                0 if row["scope"] in UNDERSERVED else 1,
                row["scope"],row["season"],row["id"])
    xg.sort(key=lambda row:key(row,xg_scores))
    cards.sort(key=lambda row:key(row,card_scores))
    return xg[:MAX_XG],cards[:MAX_CARDS]

def xg_diagnostics(stats,shots,fixture):
    """Strict native-ID and full-match xG; report both source definitions."""
    h_id=fixture["home_team"]["id"];a_id=fixture["away_team"]["id"]
    mid=fixture["id"]
    result={"status":"XG_SOURCE_INVALID","stats_xg_home":None,
            "stats_xg_away":None,"shots_xg_home":None,"shots_xg_away":None,
            "xg_abs_delta_home":None,"xg_abs_delta_away":None,
            "xg_verified_home":None,"xg_verified_away":None}
    if stats is None or shots is None:
        result["status"]="XG_RECHECK_SOURCE_MISSING"
        return result
    try:
        h,a=parse_native_team_stats(stats,mid,h_id,a_id)
        sh,sa,nh,na=parse_native_shots(shots,mid,h_id,a_id)
    except (SemanticAuditError,ValueError,TypeError,KeyError):
        return result
    result.update(stats_xg_home=h,stats_xg_away=a,
                  shots_xg_home=sh,shots_xg_away=sa,
                  xg_abs_delta_home=round(abs(sh-h),6),
                  xg_abs_delta_away=round(abs(sa-a),6))
    if abs(sh-h)<=.15 and abs(sa-a)<=.15:
        result.update(status="XG_REVERIFIED",
                      xg_verified_home=h,xg_verified_away=a)
    else:
        result["status"]="XG_DISAGREEMENT_PERSISTS"
    return result

def card_event_counts(payload, fixture):
    """Only explicit yellowcard events, not red or second-yellow guesses.

    Require a nonempty, correctly identified full timeline; an empty event
    feed is NOT proof of zero yellow cards.
    """
    if not isinstance(payload,dict):
        return "EVENTS_UNAVAILABLE",None,None
    d=payload.get("data",payload)
    if not isinstance(d,dict) or d.get("match_id")!=fixture["id"]:
        return "EVENTS_WRONG_MATCH_ID",None,None
    events=d.get("events")
    if not isinstance(events,list) or not events:
        return "EVENTS_EMPTY_OR_MISSING",None,None
    valid_types={"goal","substitution","yellowcard","redcard","penalty"}
    counts={fixture["home_team"]["id"]:0,fixture["away_team"]["id"]:0}
    for event in events:
        if not isinstance(event,dict):
            return "EVENTS_MALFORMED",None,None
        typ=str(event.get("event_type","")).replace("_","").replace("-","").lower()
        team=event.get("team_id")
        minute=event.get("minute")
        if typ not in valid_types or team not in counts or (
            isinstance(minute,bool) or not isinstance(minute,(int,float))
            or not 0<=minute<=130
        ):
            return "EVENTS_MALFORMED_OR_UNKNOWN",None,None
        if typ=="yellowcard":
            counts[team]+=1
    h=counts[fixture["home_team"]["id"]];a=counts[fixture["away_team"]["id"]]
    # Compare any known team-side value: disagreement blocks inference.
    stat_h=raw_stat(fixture,"yellow_cards","home")
    stat_a=raw_stat(fixture,"yellow_cards","away")
    if ((stat_h is not None and abs(stat_h-h)>0.01) or
        (stat_a is not None and abs(stat_a-a)>0.01)):
        return "EVENTS_TEAM_STATS_CONFLICT",h,a
    return "EVENT_YELLOW_CONFIRMED",h,a

def store_rechecks(path, records):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript(SQL)
        for z in records:
            db.execute("""INSERT INTO issue_rechecks
            (scope,match_id,issue_type,initial_issue,status,observed_at_utc,
             source_chain_sha256,source_payload_sha256,
             native_home_team_id,native_away_team_id,
             stats_xg_home,stats_xg_away,shots_xg_home,shots_xg_away,
             xg_abs_delta_home,xg_abs_delta_away,xg_verified_home,xg_verified_away,
             yellow_events_home,yellow_events_away,original_provider_first_published_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
            (z["scope"],z["match_id"],z["issue_type"],z["initial_issue"],
             z["status"],z["observed_at_utc"],z["chain"],z["sha"],
             z["home"],z["away"],z.get("stats_xg_home"),z.get("stats_xg_away"),
             z.get("shots_xg_home"),z.get("shots_xg_away"),
             z.get("xg_abs_delta_home"),z.get("xg_abs_delta_away"),
             z.get("xg_verified_home"),z.get("xg_verified_away"),
             z.get("yellow_events_home"),z.get("yellow_events_away")))
        assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        db.commit()
        n=db.execute("SELECT COUNT(*) FROM issue_rechecks").fetchone()[0]
    return n

def recheck(client, *, db_path=DB,issue_db=ISSUE_DB, root=ISSUE_ROOT,
            public_key=PUBLIC_KEY,run_token,
            max_xg=MAX_XG, max_cards=MAX_CARDS):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",run_token):
        raise ValueError("UNSAFE_RECHECK_TOKEN")
    if not (0 <= max_xg <= MAX_XG and 0 <= max_cards <= MAX_CARDS and
            2*max_xg+max_cards <= MAX_CALLS):
        raise ValueError("UNSAFE_RECHECK_LIMIT")
    xg,cards=candidates(db_path,issue_db)
    xg,cards=xg[:max_xg],cards[:max_cards]
    if not xg and not cards:
        return {"status":"NO_NEW_ISSUES","requests":0,
                "xg_reviewed":0,"cards_reviewed":0,"new_corrections":0}
    receipts=[];records=[];errors=Counter();calls=0
    def call(resource,fn,*args):
        nonlocal calls
        if calls>=MAX_CALLS:raise ValueError("RECHECK_PROVIDER_CAP")
        start=utc_now()
        try: value=to_plain(fn(*args))
        except Exception as exc:
            calls+=1
            errors[type(exc).__name__]+=1
            return None,None
        ended=utc_now();calls+=1
        if not isinstance(value,dict):
            errors["NON_OBJECT"]+=1
            return None,None
        add_observation(receipts,resource=resource,payload=value,
                        started=start,completed=ended)
        return value,receipts[-1]
    def base(f,kind,status,receipt):
        return {"scope":f["scope"],"match_id":f["id"],"issue_type":kind,
                "initial_issue":f["xg_status"] if kind=="XG" else "MISSING_YELLOW_STAT",
                "status":status,"observed_at_utc":receipt["completed_at_utc"],
                "chain":receipt["chain_sha256"],"sha":receipt["payload_sha256"],
                "home":f["home_team"]["id"],"away":f["away_team"]["id"]}
    for f in xg:
        mid=f["id"]
        stats,sr=call("pitchapi:recheck:stats:"+mid,client.matches.stats,mid)
        shots,sh=call("pitchapi:recheck:shots:"+mid,client.matches.shots,mid)
        if sr is None and sh is None:
            errors["XG_BOTH_PROVIDER_SOURCES_FAILED"]+=1
            continue
        receipt=sh or sr
        diag=xg_diagnostics(stats,shots,f)
        records.append({**base(f,"XG",diag["status"],receipt),**diag})
    for f in cards:
        mid=f["id"]
        events,er=call("pitchapi:recheck:events:"+mid,client.matches.events,mid)
        if er is None:
            errors["CARD_EVENTS_SOURCE_FAILED"]+=1
            continue
        status,h,a=card_event_counts(events,f)
        records.append({**base(f,"YELLOW_CARDS",status,er),
                        "yellow_events_home":h,"yellow_events_away":a})
    if not receipts:
        raise ValueError("RECHECK_NO_AUTHENTIC_EVIDENCE")
    day=as_utc(receipts[0]["started_at_utc"]).date().isoformat()
    dest=Path(root)/day/("run-"+run_token)
    if dest.exists():
        raise FileExistsError("RECHECK_IMMUTABLE_RUN_EXISTS")
    dest.mkdir(parents=True,exist_ok=False)
    stage=dest/"STAGED_ISSUES.sqlite"
    try:
        if Path(issue_db).exists():
            shutil.copy2(issue_db,stage)
        count=store_rechecks(stage,records)
        sealed=seal(receipts,public_key,dest/"ISSUE_SOURCE.enc",
                    dest/"ISSUE_SOURCE.manifest.json")
        statuses=Counter(f["issue_type"]+":"+f["status"] for f in records)
        report={"schema":SCHEMA,"status":"OBSERVED_RECHECK",
                "xg_issues_selected":len(xg),"card_issues_selected":len(cards),
                "provider_requests":calls,"source_receipts":len(receipts),
                "xg_reviewed":sum(r["issue_type"]=="XG" for r in records),
                "cards_reviewed":sum(r["issue_type"]=="YELLOW_CARDS" for r in records),
                "xg_reverified":statuses["XG:XG_REVERIFIED"],
                "yellow_from_events":statuses["YELLOW_CARDS:EVENT_YELLOW_CONFIRMED"],
                "selection": "CORE5_AND_XG5_RESEARCH_TARGET_IMPACT_RANKED",
                "cards_selected_by_scope":dict(Counter(f["scope"] for f in cards)),
                "xg_selected_by_scope":dict(Counter(f["scope"] for f in xg)),
                "status_counts":dict(statuses),"error_types":dict(errors),
                "cumulative_issue_rows":count,
                "observed_at_utc":receipts[-1]["completed_at_utc"],
                "source_cipher_sha256":sealed["ciphertext_sha256"],
                "source_chain_sha256":sealed["proof"]["final_chain_sha256"],
                "original_historical_pit_certified":False,
                "original_rows_modified":False,
                "production_approved":False,"official_training_allowed":False}
        with (dest/"ISSUE_RECHECK_REPORT.json").open("x",encoding="utf8") as fd:
            json.dump(report,fd,sort_keys=True,indent=2)
            fd.write("\n")
        os.replace(stage,issue_db)
        return report
    finally:
        stage.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--run-token",required=True)
    args=p.parse_args()
    key=os.getenv("PITCHAPI_API_KEY","").strip()
    if not key:raise SystemExit("MISSING_PITCHAPI_SECRET")
    from pitchapi import PitchAPI
    try:
        r=recheck(PitchAPI(api_key=key),run_token=args.run_token)
    except Exception as exc:
        print("KB3_ISSUE_RECHECK_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
    print("KB3_ISSUE_RECHECK",json.dumps(r,sort_keys=True))
if __name__=="__main__":
    main()
