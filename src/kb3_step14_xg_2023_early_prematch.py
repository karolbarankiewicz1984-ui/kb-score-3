"""2023/24 actual pre-target historic FPL player-xG, two independently dated blobs.

Exact FPL player fixture+team-side / prior 5 fixtures / server timestamp.
No PitchAPI native xG equivalence asserted; no private archive; no targets'
goals, player names, or xG numeric values exported or trained.
"""
from __future__ import annotations
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from src.kb3_step14_multiseason_pit import fetch,utc,SOURCES
from src.kb3_step14_fpl_form5_lineage import _candidate,parse_fixture_rows
from src.kb3_step14_xg_four_gates import extract_public_xg,before_target
from scripts.step14_multiseason_owner_native_join_local import ADDITIONAL_2023

SCHEMA="kb3-step14-2023-genuine-early-prematch-player-xg-form5-v1"
SOURCES_2023=(SOURCES[0],ADDITIONAL_2023)
PATH="data/2023-24/gws/merged_gw.csv"
class OldXGError(ValueError):pass

def examine_one(s,fetcher=fetch):
    base=f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/"
    fix=fetcher(base+s["path"],limit=3_000_001)
    players=fetcher(base+PATH,limit=40_000_001)
    if len(players)>=40_000_001:
        raise OldXGError("SOURCE_TOO_LARGE")
    if sha256(fix).hexdigest()!=s["sha"]:
        raise OldXGError("PUBLIC_FIXTURES_SOURCE_SHA_CHANGED")
    clock=utc(s["push"])
    src=extract_public_xg(fix,players,published_at=s["push"],
        pinned_fixture_sha=s["sha"],
        pinned_player_sha=sha256(players).hexdigest())
    if src["finished_fixtures"]!=s["ft"] or src["fixture_count"]!=380:
        raise OldXGError("GATE_FINISHED_FIXTURE_COUNT_CHANGED")
    targets=parse_fixture_rows(fix)
    counters=Counter();forms=0
    total_prior_sides=0
    for t in targets:
        if t["finished"]!="False" or not t["kickoff_time"] or utc(t["kickoff_time"])<=clock:
            continue
        case=_candidate(targets,t,clock)
        if case["state"]!="PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE":
            continue
        forms+=1
        cutoff=utc(t["kickoff_time"]).replace(second=0)
        cutoff_utc=(cutoff-__import__("datetime").timedelta(minutes=1)).isoformat().replace("+00:00","Z")
        good=True
        for side,tid_key in (("home","team_h"),("away","team_a")):
            tid=int(t[tid_key])
            for oldid in case[f"{side}_last5_public_fixture_ids"]:
                old=int(oldid)
                total_prior_sides+=1
                try:
                    before_target(prior_fixture=old,prior_team=tid,src=src,
                        cutoff=cutoff_utc,target_kickoff=t["kickoff_time"])
                except Exception as exc:
                    counters[type(exc).__name__+"_"+str(exc)]+=1
                    good=False
        if good:counters["BOTH_TEAM_LAST5_PLAYER_XG_SOURCE_AVAILABLE"]+=1
        else:counters["AT_LEAST_ONE_LAST5_XG_PREMATCH_GAP"]+=1
    return {"season":"2023-24","old_commit":s["commit"],
        "old_fixture_sha":s["sha"],
        "old_player_xg_sha256":sha256(players).hexdigest(),
        "old_push_utc":s["push"],
        "external_push_event_id":s["event"],
        "finished_FT_in_old_source":s["ft"],
        "old_source_player_rows":src["player_rows"],
        "old_source_both_team_xg_fixture_count":src["fixtures_with_both_sides_player_xg"],
        "public_targets_with_5_prior_results_each_team":forms,
        "source_last5_xg_comparison_points":total_prior_sides,
        "status_counts":dict(sorted(counters.items())),
        "xg_definition":"FPL_OPTA_PLAYER_SHOT_XG_SUM_NOT_PITCHAPI_TEAM",
        "source_publication_before_target_utc_verified":True,
        "original_PitchAPI_xg_semantics_or_numeric_equivalence":False,
        "original_native_121_plus_38_pit_eligible":0,
        "original_M1_training_allowed":False}

def audit():
    out=[]
    for s in SOURCES_2023:
        try:
            r=examine_one(s)
        except Exception as e:
            r={"season":"2023-24","old_commit":s["commit"],
               "old_push_utc":s["push"],"source_evaluation":"FAIL_CLOSED_OR_UNAVAILABLE",
               "error_class":type(e).__name__,
               "original_PitchAPI_xg_semantics_or_numeric_equivalence":False,
               "original_native_121_plus_38_pit_eligible":0,
               "original_M1_training_allowed":False}
        out.append(r)
    return {"schema":SCHEMA,"historical_early_2023_source_snapshots":out,
            "real_prematch_FPL_player_xg_only_not_original_PitchAPI":True,
            "original_train_pit_eligible":0,"original_validation_pit_eligible":0,
            "test_2026_27_examined":False,"paid_sports_api_calls":0,
            "training_allowed":False,"gate14_pass":False}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    path=Path(p.parse_args().output)
    out=audit()
    path.parent.mkdir(parents=True,exist_ok=True)
    body=json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if path.exists():
        if path.read_text(encoding="utf8")!=body:raise OldXGError("REPORT_IMMUTABLE_CONFLICT")
    else:path.write_text(body,encoding="utf8")
    print(json.dumps({"sources":[{"commit":x["old_commit"],
              "old_earlier_xg_matches":x.get("old_source_both_team_xg_fixture_count"),
              "form5_prematch_targets":x.get("public_targets_with_5_prior_results_each_team"),
              "counts":x.get("status_counts"),
              "state":x.get("source_evaluation","ACTUAL_SOURCE_CHECKED")}
              for x in out["historical_early_2023_source_snapshots"]],
              "original_PitchAPI_xg_PIT":False,"gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
