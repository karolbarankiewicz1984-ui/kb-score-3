"""GATE11 one-time real UEFA EL + UECL PitchAPI-only shot xG audit.

15 maximum SDK calls: 1 catalog + 2 league seasons + 12 native-ID shots.
Raw sources are persisted only in RSA+AES sealed evidence; report only counts.
Missing or partial shots never become zero-valued xG or 'complete' observations.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_pit_ledger import as_utc,utc_now
from src.kb3_pitch_native import verify_native_shots,LAG,MATCH_ID,TEAM_ID
from scripts.pitchapi_step06_audit import to_plain,norm

SEASON="2026/2027"
SAMPLE_PER_COMPETITION=6
MAX_CALLS=15
LEAGUES=(("europa_league","europa league"),("conference_league","conference league"))

def select_sample(matches,now,count=SAMPLE_PER_COMPETITION):
    seen=set()
    eligible=[]
    for m in matches:
        if not isinstance(m,dict):
            raise ValueError("UEFA_FIXTURE_NOT_OBJECT")
        mid=m.get("id")
        if not isinstance(mid,str) or not MATCH_ID.fullmatch(mid) or mid in seen:
            raise ValueError("UEFA_INVALID_OR_DUPLICATE_FIXTURE")
        seen.add(mid)
        if m.get("status")!="finished":continue
        if as_utc(m["time_utc"])+LAG>as_utc(now):continue
        home,away=m.get("home_team"),m.get("away_team")
        if not isinstance(home,dict) or not isinstance(away,dict):
            raise ValueError("UEFA_TEAM_OBJECT_MISSING")
        if not all(isinstance(t.get("id"),str) and TEAM_ID.fullmatch(t["id"])
                   for t in (home,away)) or home["id"]==away["id"]:
            raise ValueError("UEFA_TEAM_NATIVE_ID_INVALID")
        if not all(type(m.get(k)) is int and m[k]>=0
                   for k in ("score_home","score_away")):
            raise ValueError("UEFA_FINISHED_SCORE_MISSING")
        eligible.append(m)
    eligible.sort(key=lambda m:(as_utc(m["time_utc"]),m["id"]))
    if len(eligible)<count:
        raise ValueError("UEFA_INSUFFICIENT_FINISHED_MATCHES")
    indices=[(2*i+1)*len(eligible)//(2*count) for i in range(count)]
    if len(set(indices))!=count:
        raise ValueError("UEFA_DUPLICATED_SAMPLING_POSITION")
    return [eligible[i] for i in indices],len(eligible)

def choose_league(leagues,term):
    active=[l for l in leagues if norm(l.get("name"))==term and
            SEASON in (l.get("seasons") or [])]
    if len(active)!=1:
        raise ValueError("UEFA_LEAGUE_NOT_UNIQUE")
    return active[0]

def audit(*,public_key,outdir):
    from pitchapi import PitchAPI
    credential=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not credential:
        raise ValueError("UEFA_PITCH_CREDENTIAL_MISSING")
    sdk=PitchAPI(api_key=credential)
    calls=0;receipts=[]
    started=utc_now()
    catalog=to_plain(sdk.leagues.list());calls+=1
    completed=utc_now()
    add_observation(receipts,resource="pitchapi:catalog",payload=catalog,
                    started=started,completed=completed)
    catalog_leagues=catalog.get("leagues") if isinstance(catalog,dict) else None
    if not isinstance(catalog_leagues,list):
        raise ValueError("UEFA_BAD_CATALOG")
    report={}
    for name,term in LEAGUES:
        league=choose_league(catalog_leagues,term)
        started=utc_now()
        raw=to_plain(sdk.leagues.matches(league["id"],season=SEASON,status="all"));calls+=1
        completed=utc_now()
        add_observation(receipts,resource=f"pitchapi:uefa:{name}:{SEASON}",
                        payload=raw,started=started,completed=completed)
        matches=raw.get("matches") if isinstance(raw,dict) else None
        if not isinstance(matches,list) or not matches:
            raise ValueError("UEFA_LISTING_UNAVAILABLE")
        sample,finished_eligible=select_sample(matches,completed)
        states=Counter();days=set()
        for m in sample:
            started=utc_now()
            rawshot=to_plain(sdk.matches.shots(m["id"]));calls+=1
            completed_shot=utc_now()
            shot={"data":rawshot.get("data",rawshot)} if isinstance(rawshot,dict) else {"data":rawshot}
            # IMPORTANT: do not expose the raw match / shot feed in the report.
            result=verify_native_shots(m,shot,observed_at_utc=completed_shot)
            add_observation(receipts,resource=f"pitchapi:shots:{m['id']}",
                            payload=shot,started=started,completed=completed_shot)
            states[result["shot_state"]]+=1
            days.add(as_utc(m["time_utc"]).date().isoformat())
        report[name]={
          "fixtures_in_provider_listing":len(matches),
          "eligible_finished_matches":finished_eligible,
          "sample_size":len(sample),
          "sample_distinct_dates":len(days),
          "complete_shot_xg":states["COMPLETE_SHOT_XG"],
          "missing_or_partial_xg":len(sample)-states["COMPLETE_SHOT_XG"],
          "shot_state_counts":dict(sorted(states.items())),
          "native_match_id_cross_provider_join_needed":False,
          "all_fixture_xg_coverage_not_certified":True,
          "training_allowed":False}
    if calls!=MAX_CALLS or len(receipts)!=MAX_CALLS:
        raise ValueError("UEFA_CALL_BUDGET_OR_CAPTURE_INCOMPLETE")
    root=Path(outdir);root.mkdir(parents=True,exist_ok=True)
    encrypted=root/"KB3_UEFA_EL_UECL_XG_NATIVE_20261026.enc"
    manifest=root/"KB3_UEFA_EL_UECL_XG_NATIVE_20261026.manifest.json"
    meta=seal(receipts,public_key,encrypted,manifest)
    return {"schema":"kb3-step11-uefa-native-xg-coverage-v1",
        "source":"PitchAPI",
        "observation_completed_at_utc":completed_shot,
        "season":SEASON,
        "competitions":report,
        "samples_total":2*SAMPLE_PER_COMPETITION,
        "requests_pitchapi":calls,
        "requests_api_football":0,
        "sealed_source_sessions":meta["proof"]["sessions"],
        "sealed_final_chain_sha256":meta["proof"]["final_chain_sha256"],
        "ciphertext_sha256":meta["ciphertext_sha256"],
        "provider_original_published_at_known":False,
        "historical_prematch_pit_certified":False,
        "offsite_restore_verified":False,
        "training_allowed":False,
        "production_switch_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="audit/step11/native-uefa")
    p.add_argument("--recipient",default="config/step11_archive_recipient_public.pem")
    args=p.parse_args()
    try:
        result=audit(public_key=args.recipient,outdir=args.outdir)
        f=Path(args.outdir)/"STEP11_UEFA_NATIVE_XG_AGGREGATES.json"
        with f.open("x",encoding="utf8") as output:
            json.dump(result,output,indent=2,sort_keys=True);output.write("\n")
        print("KB3_UEFA_NATIVE_XG_AUDIT_PASS",json.dumps(result,sort_keys=True))
    except Exception as exc:
        print("KB3_UEFA_NATIVE_XG_AUDIT_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
