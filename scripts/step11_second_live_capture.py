"""One-shot second PL 2026/27 fixture observation + bounded PitchAPI xG.

Network: exactly one API-Football fixtures request, <=6 PitchAPI requests.
Payloads never printed; sealed with recipient public key, private key off-runner.
The current observation is NOT backdated to the older kickoff of a match.
"""
from __future__ import annotations
import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request

from scripts.pitchapi_step06_audit import Client,PITCH,norm
from src.kb3_pit_ledger import record_capture,utc_now,as_utc,verify_chain
from src.kb3_xg_pit import record_xg,verify_xg,MIN_POSTMATCH_LAG
from src.kb3_pit_archive import seal

PITCH_CALL_LIMIT=6
XG_SAMPLE_LIMIT=3
MAX_BYTES=12_000_000

def choose(matches,now):
    eligible=[m for m in matches if isinstance(m,dict) and m.get("status")=="finished"
              and isinstance(m.get("id"),str) and m["id"].startswith("m_")
              and isinstance(m.get("time_utc"),str)
              and isinstance(m.get("home_team"),dict)
              and isinstance(m.get("away_team"),dict)
              and as_utc(m["time_utc"])+MIN_POSTMATCH_LAG<=now]
    eligible.sort(key=lambda m:(m["time_utc"],m["id"]),reverse=True)
    return eligible[:XG_SAMPLE_LIMIT]

def capture(outdir,public_key,api_key):
    if not api_key:
        raise ValueError("MISSING_FOOTBALL_KEY")
    out=Path(outdir)
    out.mkdir(parents=True,exist_ok=True)
    db_path=out/"EPHEMERAL_TWO_SOURCE_PIT.sqlite3"
    if db_path.exists():
        raise FileExistsError("EPHEMERAL_DB_ALREADY_EXISTS")
    query=urllib.parse.urlencode({"league":39,"season":2026})
    req=urllib.request.Request("https://v3.football.api-sports.io/fixtures?"+query,
         headers={"x-apisports-key":api_key,"Accept":"application/json",
                  "User-Agent":"KB3-PIT-v2/1.0"})
    start=utc_now()
    with urllib.request.urlopen(req,timeout=35) as res:
        if res.status!=200:
            raise ValueError("FOOTBALL_NON_200")
        raw=res.read(MAX_BYTES+1)
    end=utc_now()
    if len(raw)>MAX_BYTES:raise ValueError("FOOTBALL_RESPONSE_TOO_LARGE")
    fixtures=json.loads(raw)
    af=fixtures.get("response",[])
    with sqlite3.connect(db_path) as db:
        capture_event=record_capture(db,fixtures,season=2026,
            started_at_utc=start,completed_at_utc=end,origin="NETWORK_OBSERVED")
        pitch=Client(PITCH,"PITCHAPI_API_KEY","X-API-KEY",PITCH_CALL_LIMIT)
        catalog=pitch.get("/v1/leagues")
        names=(catalog or {}).get("data",{}).get("leagues")
        if not isinstance(names,list):
            raise ValueError("PITCH_CATALOG_UNAVAILABLE")
        leagues=[l for l in names if norm(l.get("name")).replace(" ","")=="premierleague"
                 and str(l.get("country_code") or "").upper()=="ENG"]
        if len(leagues)!=1 or "2026/2027" not in (leagues[0].get("seasons") or []):
            raise ValueError("PITCH_PL_2026_SEASON_UNAVAILABLE")
        listing=pitch.get(f"/v1/leagues/{leagues[0]['id']}/matches",season="2026/2027")
        matches=(listing or {}).get("data",{}).get("matches")
        if not isinstance(matches,list):
            raise ValueError("PITCH_MATCHES_UNAVAILABLE")
        picked=choose(matches,as_utc(end))
        if len(picked)!=XG_SAMPLE_LIMIT:
            raise ValueError("INSUFFICIENT_FINISHED_XG_MATCHES")
        samples=[]
        for match in picked:
            t0=utc_now()
            shots=pitch.get(f"/v1/matches/{match['id']}/shots")
            t1=utc_now()
            result=record_xg(db,match,shots,af,
               started_at_utc=t0,completed_at_utc=t1,
               origin="NETWORK_OBSERVED")
            samples.append(result)
        ledger=verify_chain(db)
        xg=verify_xg(db)
    enc=out/"KB3_PL_2026-27_SECOND_PIT_AND_XG.enc"
    manifest=out/"KB3_PL_2026-27_SECOND_PIT_AND_XG.manifest.json"
    sealed=seal(db_path,public_key,enc,manifest)
    if sealed["ledger_evidence"]!=ledger or sealed["xg_evidence"]!=xg:
        raise ValueError("SOURCE_SEAL_MISMATCH")
    db_path.unlink()
    return {"schema":"kb3-step11-second-pit-plus-xg-v1",
        "observation_started_at_utc":start,
        "observation_completed_at_utc":end,
        "fixture_records":capture_event["records"],
        "fixture_chain_sha256":capture_event["chain_sha256"],
        "fixture_source_sha256":capture_event["response_sha256"],
        "xg_audit":xg,
        "pitchapi_calls":pitch.calls,"pitchapi_hard_ceiling":PITCH_CALL_LIMIT,
        "api_football_calls":1,"sample_selected":len(picked),
        "provider_errors_count":len(pitch.errors),
        "encrypted_sha256":sealed["encrypted_sha256"],
        "provider_initial_published_time_known":False,
        "provider_published_at_utc":None,
        "no_prematch_snapshot_certification":True,
        "historical_before_observation_certified":False,
        "training_allowed":False,"trained_model":False,
        "original_snapshot_not_modified":True,
        "offsite_restore_verified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="audit/step11/second-pit")
    p.add_argument("--public-key",default="config/step11_archive_recipient_public.pem")
    a=p.parse_args()
    out=Path(a.outdir)
    try:
        report=capture(out,a.public_key,os.environ.get("API_FOOTBALL_KEY","").strip())
        (out/"STEP11_SECOND_PIT_SANITIZED.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
        print("STEP11_SECOND_PIT_XG_PASS",json.dumps(report,sort_keys=True))
    except Exception as exc:
        print("STEP11_SECOND_PIT_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":
    main()
