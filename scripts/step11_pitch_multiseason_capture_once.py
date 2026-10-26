"""ONE bounded PitchAPI-only capture of three completed Premier League seasons.

Historical source observed NOW is *retrospective*, not a 2023-2026 prematch
archive. No training. RSA+AES sealed source responses leave runner; original
team names, scores and payloads never printed in workflow logs.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from scripts.pitchapi_step06_audit import to_plain,norm
from src.kb3_pit_ledger import utc_now
from src.kb3_pitch_native import check_season
from src.kb3_pitch_multiseason_history import HISTORICAL_SEASONS,SEASON_RESOURCE
from src.kb3_pitch_uefa_evidence import add_observation,seal,verify_receipts

EXPECTED_CALLS=1+len(HISTORICAL_SEASONS)

def capture(*,outdir,recipient):
    from pitchapi import PitchAPI
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:
        raise ValueError("MISSING_NATIVE_PITCH_API_CREDENTIAL")
    api=PitchAPI(api_key=key)
    receipts=[]
    start=utc_now()
    catalog=to_plain(api.leagues.list())
    end=utc_now()
    add_observation(receipts,resource="pitchapi:catalog",payload=catalog,
                    started=start,completed=end)
    leagues=catalog.get("leagues") if isinstance(catalog,dict) else None
    if not isinstance(leagues,list):
        raise ValueError("PITCH_NATIVE_CATALOG_INVALID")
    pl=[l for l in leagues if norm(l.get("name"))=="premier league"
        and str(l.get("country_code") or "").upper()=="ENG"]
    if len(pl)!=1:
        raise ValueError("PITCH_PL_CATALOG_AMBIGUOUS")
    league=pl[0]
    if not all(y in (league.get("seasons") or []) for y in HISTORICAL_SEASONS):
        raise ValueError("PITCH_PL_REQUIRED_HISTORICAL_SEASON_MISSING")
    sources={}
    unique_ids=set()
    prior_team_ids=None
    for year in HISTORICAL_SEASONS:
        start=utc_now()
        payload=to_plain(api.leagues.matches(league["id"],season=year,status="played"))
        end=utc_now()
        rows=payload.get("matches") if isinstance(payload,dict) else None
        if not isinstance(rows,list):
            raise ValueError("PITCH_HISTORICAL_LIST_MISSING")
        check=check_season(rows,year,expected_count=380,require_upcoming=False)
        if check["status_counts"]!={"finished":380}:
            raise ValueError("PITCH_HISTORIC_MATCHES_NOT_FULLY_FINISHED")
        match_ids={m["id"] for m in rows}
        if unique_ids & match_ids:
            raise ValueError("PITCH_HISTORICAL_MATCH_ID_OVERLAP")
        unique_ids.update(match_ids)
        team_ids={t["id"] for m in rows for t in (m["home_team"],m["away_team"])}
        overlap=len(team_ids & prior_team_ids) if prior_team_ids is not None else None
        if overlap is not None and overlap<14:
            raise ValueError("PITCH_HISTORIC_TEAM_IDS_NOT_STABLE")
        prior_team_ids=team_ids
        add_observation(receipts,
            resource=SEASON_RESOURCE.format(season=year),
            payload=payload,started=start,completed=end)
        sources[year]={"fixtures":len(rows),"unique_teams":len(team_ids),
            "overlap_with_previous_season":overlap,
            "source_payload_sha256":receipts[-1]["payload_sha256"],
            "source_observed_at_utc":end,"retrospective_source":True}
    if len(receipts)!=EXPECTED_CALLS:
        raise ValueError("PITCH_HISTORICAL_CAPTURE_INCOMPLETE")
    root=Path(outdir);root.mkdir(parents=True,exist_ok=True)
    enc=root/"KB3_PITCH_PL_HIST_2023_2026_NATIVE.enc"
    manifest=root/"KB3_PITCH_PL_HIST_2023_2026_NATIVE.manifest.json"
    meta=seal(receipts,recipient,enc,manifest)
    if meta["proof"]["sessions"]!=EXPECTED_CALLS:
        raise ValueError("HISTORICAL_ARCHIVE_SEAL_FAILED")
    return {"schema":"kb3-pitch-native-3season-history-v1",
        "source":"PitchAPI","seasons":sources,
        "historical_fixtures_total":len(unique_ids),
        "historical_seasons":len(HISTORICAL_SEASONS),
        "pitchapi_requests":EXPECTED_CALLS,
        "api_football_requests":0,
        "sealed_sessions":meta["proof"]["sessions"],
        "final_chain_sha256":meta["proof"]["final_chain_sha256"],
        "cipher_sha256":meta["ciphertext_sha256"],
        "last_real_observed_at_utc":end,
        "original_provider_publication_known":False,
        "historical_prematch_pit_certified":False,
        "training_allowed":False,
        "production_switch_approved":False,
        "independent_drive_restore_verified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="audit/step11/pitch-history")
    p.add_argument("--recipient",default="config/step11_archive_recipient_public.pem")
    a=p.parse_args()
    try:
        result=capture(outdir=a.outdir,recipient=a.recipient)
        with (Path(a.outdir)/"PITCH_PL_HIST_NATIVE_SUMMARY.json").open(
                "x",encoding="utf8") as f:
            json.dump(result,f,indent=2,sort_keys=True);f.write("\n")
        print("KB3_NATIVE_PL_HISTORY_SEALED",
              json.dumps(result,sort_keys=True))
    except Exception as exc:
        print("KB3_NATIVE_PL_HISTORY_BLOCKED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":
    main()
