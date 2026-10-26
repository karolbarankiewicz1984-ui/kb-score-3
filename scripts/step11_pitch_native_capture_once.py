"""One-shot PitchAPI-only provider-native real observation, maximum seven requests."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sqlite3
from scripts.pitchapi_step06_audit import to_plain,norm
from src.kb3_pit_ledger import utc_now,as_utc
from src.kb3_pitch_native import LAG,verify_native_shots
from src.kb3_pitch_native_ledger import record,verify
from src.kb3_pitch_native_archive import seal

MAX_REQUESTS=7
SAMPLE=5

def choose(matches,at):
    eligible=[m for m in matches if m.get("status")=="finished"
       and as_utc(m["time_utc"])+LAG<=as_utc(at)]
    eligible.sort(key=lambda m:(m["time_utc"],m["id"]))
    if len(eligible)<SAMPLE:
        raise ValueError("INSUFFICIENT_FINISHED_NATIVE_MATCHES")
    offsets=[(2*i+1)*len(eligible)//(2*SAMPLE) for i in range(SAMPLE)]
    return [eligible[i] for i in offsets]

def capture(outdir,recipient):
    from pitchapi import PitchAPI
    credential=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not credential:
        raise ValueError("PITCH_PROVIDER_CREDENTIAL_UNAVAILABLE")
    sdk=PitchAPI(api_key=credential)
    catalog=to_plain(sdk.leagues.list())
    names=catalog.get("leagues") if isinstance(catalog,dict) else None
    if not isinstance(names,list):
        raise ValueError("INVALID_LEAGUE_CATALOG")
    selected=[x for x in names if norm(x.get("name"))=="premier league"
       and str(x.get("country_code") or "").upper()=="ENG"
       and "2026/2027" in (x.get("seasons") or [])]
    if len(selected)!=1:
        raise ValueError("AMBIGUOUS_PL_LEAGUE")
    first_start=utc_now()
    raw=to_plain(sdk.leagues.matches(selected[0]["id"],
                                      season="2026/2027",status="all"))
    first_end=utc_now()
    matches=raw.get("matches") if isinstance(raw,dict) else None
    root=Path(outdir);root.mkdir(parents=True,exist_ok=True)
    ephemeral=root/"PITCH_NATIVE_TEMP.sqlite3"
    if ephemeral.exists():
        raise FileExistsError("EPHEMERAL_FILE_ALREADY_EXISTS")
    with sqlite3.connect(ephemeral) as db:
        first=record(db,"matches",matches,started_at_utc=first_start,
                     completed_at_utc=first_end,origin="NETWORK_OBSERVED")
        sample=choose(matches,first_end)
        status=Counter()
        for match in sample:
            started=utc_now()
            rawshot=to_plain(sdk.matches.shots(match["id"]))
            completed=utc_now()
            shots={"data":rawshot.get("data",rawshot)}
            record(db,"shots",shots,started_at_utc=started,
                   completed_at_utc=completed,origin="NETWORK_OBSERVED")
            status[verify_native_shots(match,shots,
                     observed_at_utc=completed)["shot_state"]]+=1
        evidence=verify(db)
    if evidence["fixture_captures"]!=1 or evidence["shot_captures"]!=SAMPLE:
        raise ValueError("INCOMPLETE_CAPTURE")
    encrypted=root/"KB3_PITCH_NATIVE_2026-27_PIT.enc"
    mf=root/"KB3_PITCH_NATIVE_2026-27_PIT.manifest.json"
    meta=seal(ephemeral,recipient,encrypted,mf)
    if meta["chain_evidence"]!=evidence:
        raise ValueError("ARCHIVE_EVIDENCE_MISMATCH")
    ephemeral.unlink()
    return {"schema":"kb3-step11-pitch-native-live-receipt-v1",
       "source":"PitchAPI","season":"2026/2027",
       "first_observed_at_utc":first_end,"last_observed_at_utc":completed,
       "fixture_count":first["count"],"shot_receipts":SAMPLE,
       "shot_states":dict(sorted(status.items())),
       "captures":evidence["captures"],"records":evidence["stored_records"],
       "source_payload_sha256":first["response_sha256"],
       "final_chain_sha256":evidence["last_chain_sha256"],
       "cipher_sha256":meta["encrypted_sha256"],
       "provider_requests":2+SAMPLE,
       "other_sports_provider_requests":0,
       "source_initial_publication_known":False,
       "historical_pit_certified":False,
       "offsite_restore_verified":False,"training_allowed":False,
       "production_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="audit/step11/native")
    p.add_argument("--recipient",default="config/step11_archive_recipient_public.pem")
    args=p.parse_args()
    try:
        report=capture(args.outdir,args.recipient)
        target=Path(args.outdir)/"STEP11_PITCH_NATIVE_SAFE_RECEIPT.json"
        with target.open("x",encoding="utf8") as stream:
            json.dump(report,stream,sort_keys=True,indent=2);stream.write("\n")
        print("KB3_NATIVE_OBSERVATION_SEALED",json.dumps(report,sort_keys=True))
    except Exception as exc:
        print("KB3_NATIVE_OBSERVATION_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
