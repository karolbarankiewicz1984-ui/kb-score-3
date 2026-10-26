"""One-shot live observation capture: 2026/27 PL fixture feed.

No schedule; one API-Football request via existing secret. Provider publication
time is unknown. Raw payload is ONLY retained inside encrypted offsite ledger.
No prematch predictions, model training, historic PIT backdating, or xG import.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request

from src.kb3_pit_ledger import record_capture,utc_now,verify_chain,as_utc
from src.kb3_pit_archive import seal

MAX_HTTP_BYTES=12_000_000

def capture_once(*,key,public_key,outdir,season=2026):
    if not key:
        raise RuntimeError("API_FOOTBALL_KEY_MISSING")
    if season!=2026:
        raise ValueError("ONLY_CURRENT_SEASON_IS_ALLOWED")
    root=Path(outdir)
    root.mkdir(parents=True,exist_ok=True)
    db_path=root/"EPHEMERAL_PIT_LEDGER.sqlite3"
    if db_path.exists():
        raise FileExistsError("NEVER_REUSE_EPHEMERAL_SNAPSHOT_DB")
    url="https://v3.football.api-sports.io/fixtures?"+urllib.parse.urlencode(
        {"league":39,"season":season})
    request=urllib.request.Request(url,headers={
        "x-apisports-key":key,"Accept":"application/json",
        "User-Agent":"KBScore3-Step11-PIT-2026/1.0"})
    started=utc_now()
    with urllib.request.urlopen(request,timeout=35) as res:
        if res.status!=200:
            raise ValueError("SOURCE_NOT_HTTP_200")
        raw=res.read(MAX_HTTP_BYTES+1)
    completed=utc_now()
    if len(raw)>MAX_HTTP_BYTES:
        raise ValueError("SOURCE_RESPONSE_OVERSIZED")
    payload=json.loads(raw)
    with sqlite3.connect(db_path) as db:
        event=record_capture(db,payload,season=season,
          started_at_utc=started,completed_at_utc=completed,
          origin="NETWORK_OBSERVED")
        audit=verify_chain(db)
    archive=root/"KB3_PL_2026-27_PIT_CAPTURE.enc"
    manifest=root/"KB3_PL_2026-27_PIT_CAPTURE.manifest.json"
    seal_meta=seal(db_path,public_key,archive,manifest)
    if audit!=seal_meta["ledger_evidence"]:
        raise ValueError("LEDGER_SEAL_MISMATCH")
    # Do not leave the raw DB or response JSON in a published artifact.
    db_path.unlink()
    items=payload["response"]
    captured_at=as_utc(completed)
    earlier=sum(as_utc(x["fixture"]["date"])<=captured_at for x in items)
    future=len(items)-earlier
    finished=sum(x["fixture"]["status"]["short"]=="FT" for x in items)
    return {"schema":"kb3-step11-live-pit-receipt-v1",
            "season":"2026/27","source":"API-Football",
            "capture_started_at_utc":started,"capture_completed_at_utc":completed,
            "capture_id":event["capture_id"],"chain_sha256":audit["final_chain_sha256"],
            "source_payload_sha256":event["response_sha256"],
            "record_count":audit["fixture_records"],
            "fixtures_kickoff_not_yet_passed":future,
            "fixtures_kickoff_already_passed":earlier,
            "finished_results_observed_now":finished,
            "source_publication_time_known":False,
            "source_published_at_utc":None,
            "archived_canonical_content":True,
            "archive_cipher_sha256":seal_meta["encrypted_sha256"],
            "archive_restored_independently_from_drive":False,
            "historical_before_observation_certified":False,
            "training_allowed":False,"trained_model":False,
            "forecast_generated":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="audit/step11/pit")
    p.add_argument("--public-key",default="config/step11_archive_recipient_public.pem")
    a=p.parse_args()
    target=Path(a.outdir)
    try:
        report=capture_once(key=os.environ.get("API_FOOTBALL_KEY",""),
            public_key=a.public_key,outdir=target)
        (target/"STEP11_PIT_SANITIZED_RECEIPT.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
        print("KB3_PIT_CAPTURE_OK",json.dumps(report,sort_keys=True))
    except Exception as exc:
        # Don't print provider responses, raw exception bodies, auth headers.
        print("KB3_PIT_CAPTURE_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
