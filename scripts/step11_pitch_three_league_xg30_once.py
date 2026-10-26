"""One-shot 3-league PitchAPI shot-xG coverage audit: 10 finished games per league.

Only one source (PitchAPI), exactly 34 bounded calls (1 catalogue, 3 fixture
lists, 30 native shot feeds). All original source responses are independently
timestamped, hash-chained and sealed to owner's existing RSA public key.
Neither missing xG nor a 10/10 sample proves whole-season completeness.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path

from scripts.pitchapi_step06_audit import norm,to_plain
from scripts.step11_uefa_native_xg_capture_once import select_sample,choose_league
from src.kb3_pitch_native import verify_native_shots,check_season
from src.kb3_pit_ledger import as_utc,utc_now
from src.kb3_pitch_uefa_evidence import add_observation,seal

SEASON="2026/2027"
PER_LEAGUE=10
MAX_CALLS=1+3+3*PER_LEAGUE
COMPETITIONS=(
    ("premier_league","premier league"),
    ("europa_league","europa league"),
    ("conference_league","conference league"),
)

def wilson_lower(complete,total,z=1.96):
    """Conservative descriptive binomial bound, NOT random-sample evidence."""
    if type(complete) is not int or type(total) is not int or not 0<=complete<=total or total<=0:
        raise ValueError("INVALID_COVERAGE_DENOMINATOR")
    p=complete/total
    return round((p+z*z/(2*total)-z*math.sqrt(
        (p*(1-p)+z*z/(4*total))/total))/(1+z*z/total),4)

def choose_unique(catalog,term):
    if term!="premier league":
        return choose_league(catalog,term)
    candidates=[l for l in catalog if norm(l.get("name"))==term
                and str(l.get("country_code") or "").upper()=="ENG"
                and SEASON in (l.get("seasons") or [])]
    if len(candidates)!=1:
        raise ValueError("PL_PROVIDER_LEAGUE_NOT_UNIQUE")
    return candidates[0]

def audit(*,public_key,outdir):
    from pitchapi import PitchAPI
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    if not key:
        raise ValueError("PITCH_API_KEY_MISSING")
    client=PitchAPI(api_key=key)
    receipts=[]
    started=utc_now()
    catalog=to_plain(client.leagues.list())
    ended=utc_now()
    add_observation(receipts,resource="pitchapi:catalog",payload=catalog,
                    started=started,completed=ended)
    leagues=catalog.get("leagues") if isinstance(catalog,dict) else None
    if not isinstance(leagues,list):
        raise ValueError("PITCH_CATALOG_NO_LEAGUES")

    metrics={}
    sampled_ids=set()
    for competition,term in COMPETITIONS:
        league=choose_unique(leagues,term)
        started=utc_now()
        payload=to_plain(client.leagues.matches(
            league["id"],season=SEASON,status="all"))
        ended=utc_now()
        resource=f"pitchapi:coverage:{competition}:{SEASON}"
        add_observation(receipts,resource=resource,payload=payload,
                        started=started,completed=ended)
        matches=payload.get("matches") if isinstance(payload,dict) else None
        if not isinstance(matches,list) or not matches:
            raise ValueError("PITCH_EMPTY_SEASON_LIST")
        # Distinct competitions can have fixture-list lengths different
        # from the Premier League; validation still requires unique native IDs.
        full=check_season(matches,SEASON,
                expected_count=380 if competition=="premier_league" else None)
        chosen,finished=select_sample(matches,ended,count=PER_LEAGUE)
        # This is a deterministic, time-stratified *convenience* sample.
        # Do not claim random coverage or a confidence guarantee.
        state=Counter()
        dates=set()
        for match in chosen:
            mid=match["id"]
            if mid in sampled_ids:
                raise ValueError("PITCH_CROSS_COMPETITION_MATCH_COLLISION")
            sampled_ids.add(mid)
            started=utc_now()
            shotraw=to_plain(client.matches.shots(mid))
            ended=utc_now()
            shot={"data":shotraw.get("data",shotraw)} if isinstance(shotraw,dict) else {"data":shotraw}
            assessment=verify_native_shots(match,shot,observed_at_utc=ended)
            if not assessment.get("shot_state"):
                raise ValueError("PITCH_SHOT_STATE_MISSING")
            add_observation(receipts,resource=f"pitchapi:shots:{mid}",
                            payload=shot,started=started,completed=ended)
            state[assessment["shot_state"]]+=1
            dates.add(as_utc(match["time_utc"]).date().isoformat())
        success=state["COMPLETE_SHOT_XG"]
        metrics[competition]={
            "fixture_list_count":len(matches),
            "fixture_digest_sha256":full["match_digest_sha256"],
            "finished_eligible":finished,
            "sampled_games":len(chosen),
            "sampled_distinct_kickoff_dates":len(dates),
            "shot_state_counts":dict(sorted(state.items())),
            "complete_xg":success,
            "partial_or_missing_xg":len(chosen)-success,
            "observed_sample_complete_fraction":round(success/len(chosen),4),
            "wilson_95pct_lower_if_random_sample_ONLY":wilson_lower(success,len(chosen)),
            "random_sampling_performed":False,
            "whole_competition_completeness_proven":False,
            "missing_xg_is_zero":False,
            "cross_provider_match_join":False,
        }
    if len(receipts)!=MAX_CALLS:
        raise ValueError("PITCH_CALL_OR_RECEIPT_COUNT_MISMATCH")
    root=Path(outdir);root.mkdir(parents=True,exist_ok=True)
    cipher=root/"KB3_PITCH_3_LEAGUES_XG30_20261026.enc"
    manifest=root/"KB3_PITCH_3_LEAGUES_XG30_20261026.manifest.json"
    meta=seal(receipts,public_key,cipher,manifest)
    totals=sum(x["complete_xg"] for x in metrics.values())
    return {"schema":"kb3-step11-three-leagues-xg30-v1",
        "provider":"PitchAPI","season":SEASON,
        "observation_completed_at_utc":ended,
        "competition_results":metrics,
        "samples_total":3*PER_LEAGUE,
        "complete_xg_total":totals,
        "partial_or_missing_total":3*PER_LEAGUE-totals,
        "pitchapi_requests":MAX_CALLS,"api_football_requests":0,
        "source_observations_encrypted":meta["proof"]["sessions"],
        "source_chain_sha256":meta["proof"]["final_chain_sha256"],
        "ciphertext_sha256":meta["ciphertext_sha256"],
        "ciphertext_bytes":meta["ciphertext_bytes"],
        "source_first_published_time_known":False,
        "sampling_random":False,
        "historical_matchtime_PIT_proven":False,
        "offsite_restore_verified":False,
        "training_allowed":False,
        "production_switch_approved":False,
        "gate11":"PENDING"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="audit/step11/xg30")
    p.add_argument("--recipient",default="config/step11_archive_recipient_public.pem")
    a=p.parse_args()
    try:
        result=audit(public_key=a.recipient,outdir=a.outdir)
        path=Path(a.outdir)/"STEP11_PITCH_3LEAGUE_XG30_SAFE_SUMMARY.json"
        with path.open("x",encoding="utf8") as f:
            json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
        print("KB3_XG30_REAL_PITCH_SEALED",json.dumps(result,sort_keys=True))
    except Exception as exc:
        print("KB3_XG30_PITCH_BLOCKED",type(exc).__name__)
        raise SystemExit(3)

if __name__=="__main__":
    main()
