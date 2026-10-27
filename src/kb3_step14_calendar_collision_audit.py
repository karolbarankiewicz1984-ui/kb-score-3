"""Offline actual Step14 schedule-time collision audit: TRAIN + VALIDATION only.

A chronological fixture ID has *no team name* in the frozen SAFE projection.
Therefore a matching public kickoff time is NEVER proof of fixture identity.
Analyse how many public fixture candidates exist per season+UTC to quantify
the danger of a naive kickoff-only join; no secrets, TEST, scores, targets.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import json
from pathlib import Path

from src.kb3_step14_full_identity_pit_audit import (
    _validate_safe,_independent_public_1140,_utc,FullNativeAuditError,
    PUBLIC_REFERENCE_SHA)
from src.kb3_split import sha

ROOT=Path(__file__).resolve().parents[1]
SAFE=ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
PUBLIC=ROOT/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json"
SCHEMA="kb3-step14-no-label-schedule-kickoff-collision-audit-v1"

def audit_calendar(safe,reference):
    idx=_validate_safe(safe)
    # Check the *specific* pinned October capture as immutable, never treat it
    # as historical PIT. We require no private decrypt to perform this audit.
    _independent_public_1140({},reference)
    public={}
    for season,record in reference["source_seasons"].items():
        candidate_counts=Counter()
        for row in record["fixtures_target_free"]:
            t=row["time_london"]
            if t is None:
                continue
            try:
                utc=(datetime.fromisoformat(row["date"]+"T"+t)
                     .replace(tzinfo=ZoneInfo("Europe/London"))
                     .astimezone(timezone.utc)
                     .isoformat().replace("+00:00","Z"))
            except ValueError as exc:
                raise FullNativeAuditError("CALENDAR_TIME_INVALID") from exc
            candidate_counts[utc]+=1
        public[season]=candidate_counts
    history_utc=[]
    by_role=defaultdict(Counter)
    cross=Counter()
    by_season=defaultdict(Counter)
    for fid,(kickoff,role) in idx.items():
        utc=_utc(kickoff)
        season=(f"{utc.year}-{(utc.year+1)%100:02d}" if utc.month>=8
                else f"{utc.year-1}-{utc.year%100:02d}")
        if season not in public:
            raise FullNativeAuditError("OUT_OF_FROZEN_TRAIN_VALIDATION_SEASONS")
        candidates=public[season][utc.isoformat().replace("+00:00","Z")]
        label="ZERO_PUBLIC_SAME_KICKOFF" if candidates==0 else (
            "EXACTLY_ONE_PUBLIC_SAME_KICKOFF_NOT_IDENTITY_PROOF" if candidates==1
            else "MULTIPLE_PUBLIC_SAME_KICKOFF")
        by_role[role][label]+=1
        by_season[season][label]+=1
        cross[label]+=1
    if sum(cross.values())!=1140:
        raise FullNativeAuditError("COLLISION_SOURCE_COUNT_MISMATCH")
    return {
        "schema":SCHEMA,
        "source":"FROZEN_1140_PITCHAPI_TARGETFREE_SAFE_SCHEDULE_VS_FROZEN_OPENFOOTBALL_PUBLIC_SCHEDULE",
        "safe_view_sha256":safe["projection_sha256"],
        "public_reference_sha256":PUBLIC_REFERENCE_SHA,
        "historical_public_snapshot_retrieved_in_october_2026":True,
        "no_native_home_away_ids_or_names_in_safe_match_rows":True,
        "same_kickoff_is_not_fixture_identity_proof":True,
        "total_test_rows_examined":0,
        "total_train_validation_utc_kickoffs_examined":1140,
        "candidate_count_statuses":dict(sorted(cross.items())),
        "by_role":{k:dict(sorted(v.items())) for k,v in sorted(by_role.items())},
        "by_season":{k:dict(sorted(v.items())) for k,v in sorted(by_season.items())},
        "independently_verified_teams_by_kickoff_in_this_audit":0,
        "training_allowed":False,"gate14_pass":False,"new_sports_api_calls":0,
    }

def run(root=ROOT):
    base=Path(root)
    safe=json.loads((base/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
    public=json.loads((base/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json").read_text())
    result=audit_calendar(safe,public)
    result["audit_sha256"]=sha(result)
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    args=p.parse_args()
    output=Path(args.output)
    result=run();payload=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        if output.read_text(encoding="utf8")!=payload:
            raise FullNativeAuditError("FROZEN_COLLISION_REPORT_CHANGED")
    else:
        with output.open("x",encoding="utf8") as f:f.write(payload)
    print(json.dumps({"total":result["total_train_validation_utc_kickoffs_examined"],
                      "candidate_count_statuses":result["candidate_count_statuses"],
                      "test_rows_examined":result["total_test_rows_examined"],
                      "gate14_pass":result["gate14_pass"]},sort_keys=True))
