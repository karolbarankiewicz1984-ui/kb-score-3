"""Isolated append-only KB3 TEST market capture and result settlement runner.

Uses only the tracked original M0 720 SQLite and original GitHub-host-proof rows.
NEVER writes to the original database. Captures ONLY newly observed futures
before 100-min buffer. A later self-GitHub artifact attestation is necessary.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import time
import urllib.request
import zipfile

from src.kb3_pit_ledger import canonical
from src.kb3_test_readonly_markets import utc
from src.kb3_test_market_ledger_v1 import (
    EARLY_DEADLINE, MARKET_MIN_LEAD, MarketLedgerError, make_market_freeze,
    settle_market_freeze, verify_market_freeze, need, digest,
)

ORIGINAL_DB = Path("data/forward_m0_720_eight/kb3_forward_eight.sqlite")
LEDGER = Path("data/test_markets")
ARTIFACT_NAME = "KB3_TEST_NEW_MARKET_FREEZE_INDEPENDENT_HOST_TIME"
REPO = "karolbarankiewicz1984-ui/kb-score-3"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sqlite_original(path):
    file = Path(path).resolve()
    need(file.is_file(), "ORIGINAL_M0_SQLITE_MISSING")
    db = sqlite3.connect(file.as_uri()+"?mode=ro", uri=True)
    db.execute("PRAGMA query_only=ON")
    need(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
         "ORIGINAL_SQLITE_INTEGRITY_FAIL")
    need(db.execute("PRAGMA foreign_key_check").fetchall() == [],
         "ORIGINAL_SQLITE_FOREIGN_KEY_FAIL")
    tables = {x[0] for x in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    need({"forecasts", "m0720_github_push_proofs", "settlements"} <= tables,
         "ORIGINAL_HOST_PROOFS_OR_SETTLEMENTS_MISSING")
    return db


def _original_rows(db):
    return db.execute("""SELECT f.id, f.payload_json, f.kickoff_utc, f.captured_at_utc,
        p.github_server_event_utc, p.source
        FROM forecasts f
        JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
        ORDER BY f.kickoff_utc,f.id""").fetchall()


def _read_parent(thing):
    fid, payload, kickoff, captured, host, source = thing
    p = json.loads(payload)
    need(p.get("forecast_sha256") == fid and
         p.get("kickoff_utc") == kickoff and
         p.get("generated_at_utc") == captured,
         "ORIGINAL_ROW_AND_JSON_MISMATCH")
    return fid, p, host, source


def _write_new(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(canonical(obj))


def capture_new_market_freezes(*, original_db, ledger_root, staging, now_utc,
                               limit=120):
    """Produce stage-only files; NOTHING is published until GH proof verifies."""
    need(1 <= limit <= 150, "CAPTURE_LIMIT_INVALID")
    now = utc(now_utc)
    ledger_root, staging = Path(ledger_root), Path(staging)
    need(not staging.exists() or not any(staging.iterdir()),
         "STAGING_NOT_EMPTY_REPLAY_OR_RACE")
    staging.mkdir(parents=True, exist_ok=True)
    count=0
    with _sqlite_original(original_db) as db:
        for record in _original_rows(db):
            fid, parent, host, source = _read_parent(record)
            if utc(parent["kickoff_utc"]) - MARKET_MIN_LEAD < now:
                continue
            published = ledger_root/"freezes"/(fid+".json")
            proof = ledger_root/"host_proofs"/(fid+".json")
            if published.exists():
                need(proof.is_file(), "EXISTING_FREEZE_WITHOUT_HOST_PROOF")
                continue
            need(not proof.exists(), "ORPHAN_MARKET_HOST_PROOF")
            snapshot = make_market_freeze(
                parent, original_id=fid, parent_host_utc=host,
                parent_host_source=source, captured_at_utc=now_utc)
            _write_new(staging/(fid+".json"), snapshot)
            count+=1
            if count>=limit:
                break
    return count


def _gh_json(url, token):
    need(isinstance(token,str) and len(token)>5, "GITHUB_ACTIONS_TOKEN_REQUIRED")
    req=urllib.request.Request(
        url,headers={"Authorization":"Bearer "+token,
                     "Accept":"application/vnd.github+json",
                     "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read())


def _gh_zip(url,token):
    req=urllib.request.Request(
        url,headers={"Authorization":"Bearer "+token,
                     "Accept":"application/vnd.github+json",
                     "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=50) as response:
        return response.read()


def github_artifact_attest(*, staging, ledger_root, token, run_id,
                           repo=REPO, http_json=_gh_json, http_zip=_gh_zip):
    """Independent GitHub-server-created timestamp + exact ZIP byte evidence."""
    staging, ledger_root=Path(staging),Path(ledger_root)
    records=sorted(staging.glob("*.json"))
    need(records and 1 <= len(records) <= 150, "NO_NEW_FREEZES_TO_ATTEST")
    listing = None
    for attempt in range(5):
        q=http_json("https://api.github.com/repos/"+repo+
                    "/actions/runs/"+str(run_id)+"/artifacts?per_page=100",token)
        found=[a for a in q.get("artifacts",[]) if a.get("name")==ARTIFACT_NAME
               and str((a.get("workflow_run") or {}).get("id"))==str(run_id)
               and not a.get("expired")]
        if len(found)==1:
            listing=found[0]
            break
        if attempt<4:
            time.sleep(3)
    need(listing is not None, "REAL_GITHUB_HOST_ARTIFACT_NOT_AVAILABLE")
    archive=http_zip("https://api.github.com/repos/"+repo+
                     "/actions/artifacts/"+str(listing["id"])+"/zip",token)
    archive_digest="sha256:"+hashlib.sha256(archive).hexdigest()
    need(listing.get("digest")==archive_digest,
         "GITHUB_ZIP_DIGEST_NOT_EQUAL_OR_MISSING")
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_in:
        names=[n for n in zip_in.namelist() if not n.endswith("/")]
        need(set(names)=={z.name for z in records}, "ZIP_FILE_SET_DIFFERENT_FROM_CAPTURE")
        for record in records:
            need(zip_in.read(record.name)==record.read_bytes(),
                 "GITHUB_ORIGINAL_MARKET_FREEZE_BYTES_MISMATCH")
        need(zip_in.testzip() is None, "ZIP_CRC_MISMATCH")
    created=listing.get("created_at")
    host=utc(created)
    # Ensure GitHub observed it after capture (allow rounded host seconds).
    for path in records:
        snapshot=json.loads(path.read_text(encoding="utf-8"))
        captured=utc(snapshot["market_captured_at_utc"])
        kickoff=utc(snapshot["kickoff_utc"])
        need(host + timedelta(seconds=2)>=captured and
             host <= kickoff-EARLY_DEADLINE,
             "GITHUB_SERVER_ARTIFACT_TOO_LATE_FOR_MARKET_FREEZE")
        need(snapshot.get("new_market_snapshot_created") is True
             and snapshot.get("official_fit_increment")==0,
             "RESEARCH_FREEZE_STATE_CHANGED")
        original_id=snapshot["original_m0_forecast_sha256"]
        need(path.name==original_id+".json", "MARKET_ID_FILENAME_DRIFT")
        staged_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        base={
            "schema":"kb3-test-independent-market-host-proof-v1",
            "original_m0_forecast_sha256":original_id,
            "market_freeze_sha256":snapshot["freeze_sha256"],
            "market_freeze_bytes_sha256":staged_hash,
            "market_captured_at_utc":snapshot["market_captured_at_utc"],
            "github_host_artifact_created_utc":created,
            "github_artifact_id":str(listing["id"]),
            "github_actions_run_id":str(run_id),
            "github_artifact_zip_sha256":archive_digest.removeprefix("sha256:"),
            "evidence":"GITHUB_SERVER_ARTIFACT_TIME_PLUS_EXACT_ORIGINAL_ZIP_BYTES",
            "strict_before_kickoff_minus_90min":True,
            "formal_fit_or_champion_approval":False,
        }
        proof={**base,"proof_sha256":digest(base)}
        final=ledger_root/"freezes"/path.name
        pfile=ledger_root/"host_proofs"/path.name
        need(not final.exists() and not pfile.exists(),
             "RACE_DUPLICATE_ORIGINAL_MARKET_CAPTURE")
        _write_new(final,snapshot)
        _write_new(pfile,proof)
    return {"new_host_attested":len(records),"artifact_id":listing["id"],
            "artifact_digest":archive_digest,"host_created_utc":created}


def verify_host_proof(snapshot,proof,original_market_bytes):
    need(isinstance(proof,dict) and proof.get("schema")==
         "kb3-test-independent-market-host-proof-v1","MARKET_GITHUB_PROOF_REQUIRED")
    orig={k:v for k,v in proof.items() if k!="proof_sha256"}
    need(digest(orig)==proof.get("proof_sha256"),"MARKET_HOST_PROOF_SHA_CHANGED")
    need(proof.get("market_freeze_sha256")==snapshot["freeze_sha256"]
         and proof.get("original_m0_forecast_sha256")==
         snapshot["original_m0_forecast_sha256"],"MARKET_HOST_PROOF_WRONG_PARENT")
    need(hashlib.sha256(original_market_bytes).hexdigest()==
         proof.get("market_freeze_bytes_sha256"),"MARKET_HOST_PROOF_WRONG_FROZEN_BYTES")
    host=utc(proof.get("github_host_artifact_created_utc"))
    captured=utc(snapshot["market_captured_at_utc"])
    kick=utc(snapshot["kickoff_utc"])
    need(host+timedelta(seconds=2)>=captured and host<=kick-EARLY_DEADLINE,
         "MARKET_PROOF_AFTER_DEADLINE")
    need(proof.get("evidence")==
         "GITHUB_SERVER_ARTIFACT_TIME_PLUS_EXACT_ORIGINAL_ZIP_BYTES"
         and proof.get("strict_before_kickoff_minus_90min") is True
         and proof.get("formal_fit_or_champion_approval") is False,
         "MARKET_PROOF_UNTRUSTED_SOURCE")
    return True


def settle_existing(*,original_db,ledger_root):
    """New append-only research settlement only after original M0 matured."""
    ledger_root=Path(ledger_root)
    folder=ledger_root/"freezes"
    if not folder.is_dir():
        return {"created":0,"pending":0,"existing":0}
    made=pending=existing=0
    with _sqlite_original(original_db) as db:
        for path in sorted(folder.glob("*.json")):
            original_bytes=path.read_bytes()
            snapshot=json.loads(original_bytes)
            fid=snapshot["original_m0_forecast_sha256"]
            need(path.name==fid+".json","MARKET_FREEZE_NAME_WRONG_PARENT")
            proof_path=ledger_root/"host_proofs"/path.name
            need(proof_path.is_file(),"UNATTESTED_MARKET_FREEZE_IN_LEDGER")
            proof=json.loads(proof_path.read_text(encoding="utf-8"))
            verify_host_proof(snapshot,proof,original_bytes)
            resultpath=ledger_root/"settlements"/path.name
            parent_row=db.execute("""SELECT f.id,f.payload_json,
                f.kickoff_utc,f.captured_at_utc,p.github_server_event_utc,p.source
                FROM forecasts f JOIN m0720_github_push_proofs p
                 ON p.forecast_id=f.id WHERE f.id=?""",(fid,)).fetchone()
            need(parent_row is not None, "MARKET_PARENT_NOT_IN_ORIGINAL_M0")
            _,parent,host,source=_read_parent(parent_row)
            verify_market_freeze(snapshot,parent=parent,parent_id=fid,
                                 host_utc=host,host_source=source)
            s=db.execute("""SELECT settlement_sha256,forecast_id,league,native_match_id,
                    score_home,score_away,outcome,observed_utc,settled_utc,
                    provider_source_chain_sha256,log_loss,brier_sum3
                    FROM settlements WHERE forecast_id=?""",(fid,)).fetchone()
            if not s:
                pending+=1
                need(not resultpath.exists(),
                     "SETTLEMENT_WITHOUT_FINISHED_ORIGINAL_RESULT")
                continue
            keys=("settlement_sha256","forecast_id","league","native_match_id",
                  "score_home","score_away","outcome","observed_utc","settled_utc",
                  "provider_source_chain_sha256","log_loss","brier_sum3")
            settlement=dict(zip(keys,s))
            output=settle_market_freeze(snapshot,settlement,
                original_parent=parent,parent_host_utc=host,
                parent_host_source=source)
            if resultpath.exists():
                need(resultpath.read_bytes()==canonical(output),
                     "MUTATED_OR_DIFFERENT_EXISTING_MARKET_SETTLEMENT")
                existing+=1
                continue
            _write_new(resultpath,output)
            made+=1
    return {"created":made,"pending":pending,"existing":existing}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",required=True,
                        choices=("prepare","attest","settle","preflight"))
    parser.add_argument("--db",type=Path,default=ORIGINAL_DB)
    parser.add_argument("--ledger",type=Path,default=LEDGER)
    parser.add_argument("--staging",type=Path,default=Path(".tmp_kb3_market/new"))
    args=parser.parse_args()
    if args.mode=="preflight":
        with _sqlite_original(args.db) as db:
            n=db.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
            proofs=db.execute(
                "SELECT COUNT(*) FROM m0720_github_push_proofs").fetchone()[0]
        print("KB3_TEST_MARKET_ORIGINAL_READONLY_PREFLIGHT",
              json.dumps({"original_forecasts":n,"parent_host_proofs":proofs}))
    elif args.mode=="prepare":
        result=capture_new_market_freezes(
            original_db=args.db,ledger_root=args.ledger,
            staging=args.staging,now_utc=utc_now())
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as fh:
                fh.write("new_count="+str(result)+"\n")
        print("KB3_TEST_MARKET_PREPARED_NOT_YET_HOST_ATTESTED",result)
    elif args.mode=="attest":
        out=github_artifact_attest(
            staging=args.staging,ledger_root=args.ledger,
            token=os.environ["GH_TOKEN"],
            run_id=os.environ["GITHUB_RUN_ID"])
        print("KB3_TEST_GITHUB_HOST_ATTESTED_NEW_MARKETS",json.dumps(out))
    elif args.mode=="settle":
        out=settle_existing(original_db=args.db,ledger_root=args.ledger)
        print("KB3_TEST_MARKET_REAL_M0_POSTMATCH_SETTLEMENT",json.dumps(out))


if __name__=="__main__":
    main()
