"""Step11: ten finished matches from different dates, bounded real xG coverage.

Exactly one current PL fixture list, PitchAPI catalog + match listing, up to
ten shot endpoints. Sample is *stratified*, not a claim of random or universal
coverage. No secrets, raw shots, names or fixture rows appear in public logs.
All source content is sealed under the existing offline recipient public key.
"""
from __future__ import annotations
from collections import Counter
from datetime import timezone
import argparse
import json
import os
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request

from scripts.pitchapi_step06_audit import Client,PITCH,norm
from src.kb3_pit_ledger import record_capture,verify_chain,utc_now,as_utc
from src.kb3_xg_pit import record_xg,verify_xg,MIN_POSTMATCH_LAG
from src.kb3_pit_archive import seal

SAMPLE_SIZE=10
PITCH_CALL_CAP=12
MAX_HTTP_BYTES=12_000_000
SEASON="2026/2027"

def choose_stratified(matches,now,*,excluded_match_ids=(),sample_size=SAMPLE_SIZE):
    """Deterministic spread across kickoff chronology; no fuzzy aliases."""
    excluded=set(excluded_match_ids)
    eligible=[]
    for m in matches:
        if not isinstance(m,dict) or m.get("status")!="finished":
            continue
        if not isinstance(m.get("id"),str) or not m["id"].startswith("m_") or m["id"] in excluded:
            continue
        try:
            kickoff=as_utc(m["time_utc"])
        except (KeyError,ValueError,TypeError):
            continue
        if kickoff+MIN_POSTMATCH_LAG>now:
            continue
        team_a,team_b=m.get("home_team"),m.get("away_team")
        if not all(isinstance(t,dict) and t.get("id") and t.get("name")
                   for t in (team_a,team_b)):
            continue
        if team_a["id"]==team_b["id"]:
            continue
        eligible.append((kickoff,m["id"],m))
    eligible.sort(key=lambda t:(t[0],t[1]))
    ids=[v[1] for v in eligible]
    if len(ids)!=len(set(ids)):
        raise ValueError("DUPLICATE_PITCH_PROVIDER_ID")
    if len(eligible)<sample_size:
        raise ValueError("NOT_ENOUGH_ELIGIBLE_FINISHED_GAMES")
    positions=[(2*i+1)*len(eligible)//(2*sample_size)
               for i in range(sample_size)]
    if len(set(positions))!=sample_size:
        raise ValueError("NON_UNIQUE_STRATIFIED_POSITIONS")
    return [eligible[i][2] for i in positions]

def capture(*,target_dir,public_key,api_key,excluded_match_ids):
    if not api_key:
        raise ValueError("MISSING_FOOTBALL_KEY")
    target_dir=Path(target_dir)
    target_dir.mkdir(parents=True,exist_ok=True)
    db_path=target_dir/"EPHEMERAL_STRATIFIED_XG.sqlite3"
    if db_path.exists():
        raise FileExistsError("EPHEMERAL_DB_CANNOT_BE_REUSED")
    query=urllib.parse.urlencode({"league":39,"season":2026})
    req=urllib.request.Request(
        "https://v3.football.api-sports.io/fixtures?"+query,
        headers={"x-apisports-key":api_key,"Accept":"application/json",
                 "User-Agent":"KB3-Step11-coverage-2026/1"})
    start=utc_now()
    with urllib.request.urlopen(req,timeout=35) as res:
        if res.status!=200:
            raise ValueError("FOOTBALL_NON_200")
        b=res.read(MAX_HTTP_BYTES+1)
    end=utc_now()
    if len(b)>MAX_HTTP_BYTES:
        raise ValueError("FOOTBALL_TOO_LARGE")
    src=json.loads(b)
    with sqlite3.connect(db_path) as db:
        football_receipt=record_capture(db,src,season=2026,
           started_at_utc=start,completed_at_utc=end,origin="NETWORK_OBSERVED")
        pitch=Client(PITCH,"PITCHAPI_API_KEY","X-API-KEY",PITCH_CALL_CAP)
        catalog=pitch.get("/v1/leagues")
        leagues=(catalog or {}).get("data",{}).get("leagues")
        if not isinstance(leagues,list):
            raise ValueError("PITCH_CATALOG_UNAVAILABLE")
        choices=[x for x in leagues if norm(x.get("name")).replace(" ","")=="premierleague"
          and str(x.get("country_code") or "").upper()=="ENG"]
        if len(choices)!=1 or SEASON not in (choices[0].get("seasons") or []):
            raise ValueError("PITCH_COMPETITION_OR_SEASON_NOT_UNIQUE")
        listing=pitch.get(f"/v1/leagues/{choices[0]['id']}/matches",season=SEASON)
        match_list=(listing or {}).get("data",{}).get("matches")
        if not isinstance(match_list,list):
            raise ValueError("PITCH_MATCH_LIST_UNAVAILABLE")
        sample=choose_stratified(match_list,as_utc(end),
           excluded_match_ids=excluded_match_ids)
        results=[]
        for m in sample:
            t0=utc_now()
            shots=pitch.get(f"/v1/matches/{m['id']}/shots")
            t1=utc_now()
            entry=record_xg(db,m,shots,src["response"],
              started_at_utc=t0,completed_at_utc=t1,
              origin="NETWORK_OBSERVED")
            results.append(entry)
        fixture_evidence=verify_chain(db)
        xg_evidence=verify_xg(db)
    if len(sample)!=SAMPLE_SIZE or pitch.calls>PITCH_CALL_CAP:
        raise ValueError("SAMPLING_CALL_LIMIT")
    archive=target_dir/"KB3_PL_2026-27_XG_10_STRATIFIED.enc"
    manifest=target_dir/"KB3_PL_2026-27_XG_10_STRATIFIED.manifest.json"
    metadata=seal(db_path,public_key,archive,manifest)
    if metadata["xg_evidence"]!=xg_evidence or metadata["ledger_evidence"]!=fixture_evidence:
        raise ValueError("ARCHIVE_EVIDENCE_MISMATCH")
    db_path.unlink()
    state_counts=dict(sorted(Counter(x["xg_state"] for x in results).items()))
    identity_counts=dict(sorted(Counter(x["identity_state"] for x in results).items()))
    days=len(set(as_utc(m["time_utc"]).date() for m in sample))
    return {"schema":"kb3-step11-stratified-xg-observation-v1",
       "sample_policy":"10 evenly spaced finished matches across available current PL 2026/27 dates",
       "excluded_previously_reviewed_count":len(excluded_match_ids),
       "fixture_records":football_receipt["records"],
       "fixture_response_sha256":football_receipt["response_sha256"],
       "fixture_chain_sha256":fixture_receipt_hash(fixture_evidence),
       "source_observed_at_utc":end,
       "distinct_sample_kickoff_dates":days,
       "sample_size":len(sample),
       "complete_xg_samples":xg_evidence["strict_complete"]+
          sum(1 for x in results if x["xg_state"]=="COMPLETE_SHOT_XG" and not x["accepted"]),
       "strict_approved_xg":xg_evidence["strict_complete"],
       "quarantined_xg":xg_evidence["quarantined"],
       "xg_state_counts":state_counts,
       "identity_state_counts":identity_counts,
       "api_football_calls":1,"pitchapi_calls":pitch.calls,
       "pitchapi_max_calls":PITCH_CALL_CAP,
       "provider_error_count":len(pitch.errors),
       "encrypted_sha256":metadata["encrypted_sha256"],
       "source_published_at_utc":None,
       "historical_publication_certified":False,
       "training_allowed":False,"model_fitted":False,
       "offsite_restore_verified":False}

def fixture_receipt_hash(evidence):
    return evidence["final_chain_sha256"]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outdir",default="audit/step11/stratified-xg")
    parser.add_argument("--public-key",default="config/step11_archive_recipient_public.pem")
    parser.add_argument("--exclude-crosswalk",default="config/step11_reviewed_pitch_fixture_crosswalk_20261026.json")
    arg=parser.parse_args()
    try:
        config=json.loads(Path(arg.exclude_crosswalk).read_text("utf8"))
        if config.get("schema")!="kb3-step11-reviewed-fixture-crosswalk-v1":
            raise ValueError("NOT_REVIEWED_CROSSWALK")
        exclusions=[m["pitch_match_id"] for m in config["reviewed"]]
        report=capture(target_dir=arg.outdir,public_key=arg.public_key,
           api_key=os.environ.get("API_FOOTBALL_KEY","").strip(),
           excluded_match_ids=exclusions)
        out=Path(arg.outdir)/"KB3_XG_10_STRATIFIED_SAFE_SUMMARY.json"
        out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
        print("KB3_STRATIFIED_XG_CAPTURE_PASS",json.dumps(report,sort_keys=True))
    except Exception as exc:
        # No raw responses/keys. Ensure CI can report the failure class only.
        print("KB3_STRATIFIED_XG_CAPTURE_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
