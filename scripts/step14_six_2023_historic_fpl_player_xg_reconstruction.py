"""Expand historically available FPL/Opta player-xG form5 research to SIX 2023 source snapshots.

Four newly GHArchive verified old commits plus original Oct/Dec old commits.
Exact FPL fixture, team ID, home/away, opponent_team, earliest server push,
no latest retrospective PitchAPI xG equivalence or official model training.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from collections import Counter
import argparse,json,datetime
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources
from src.kb3_step14_fpl_form5_lineage import _candidate,parse_fixture_rows
from src.kb3_step14_multiseason_pit import fetch,utc
from src.kb3_step14_xg_four_gates import extract_public_xg,before_target

PATH="data/2023-24/gws/merged_gw.csv"
SCHEMA="kb3-step14-2023-six-independent-old-public-FPL-player-xg-prematch-lineage-v1"
class FPLLineageError(ValueError):pass

def inspect_one(src,*,fetcher=fetch):
    base=f"https://raw.githubusercontent.com/{src['repo']}/{src['commit']}/"
    fixtures=fetcher(base+src["path"],limit=3_000_001)
    players=fetcher(base+PATH,limit=40_000_001)
    if not isinstance(players,bytes) or not 1_000<len(players)<40_000_001:
        raise FPLLineageError("OLD_PLAYER_XG_BLOB_MISSING_OR_OVERSIZED")
    if sha256(fixtures).hexdigest()!=src["sha"]:
        raise FPLLineageError("HISTORICAL_FIXTURE_SHA_CHANGED")
    source=extract_public_xg(fixtures,players,published_at=src["push"],
      pinned_fixture_sha=src["sha"],pinned_player_sha=sha256(players).hexdigest())
    if source["finished_fixtures"]!=src["ft"] or source["fixture_count"]!=380:
        raise FPLLineageError("ORIGINAL_OLD_SEASON_FIXTURE_COUNT_CHANGED")
    rows=parse_fixture_rows(fixtures)
    stamp=utc(src["push"]);count=0;qual=0;points=0
    for target in rows:
        if target["finished"]!="False" or not target["kickoff_time"] or utc(target["kickoff_time"])<=stamp:continue
        case=_candidate(rows,target,stamp)
        if case["state"]!="PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE":continue
        count+=1
        kickoff=utc(target["kickoff_time"])
        cutoff=(kickoff-datetime.timedelta(minutes=1)).isoformat().replace("+00:00","Z")
        all_good=True
        for side,tk in (("home","team_h"),("away","team_a")):
            tid=int(target[tk])
            for fixture_id in case[f"{side}_last5_public_fixture_ids"]:
                points+=1
                try:
                    before_target(prior_fixture=int(fixture_id),prior_team=tid,
                        src=source,cutoff=cutoff,target_kickoff=target["kickoff_time"])
                except Exception:all_good=False
        if all_good:qual+=1
    return {"source_commit":src["commit"],"external_push_event":src.get("event",src.get("event_id")),
         "true_independent_published_utc":src["push"],"fixture_raw_sha":src["sha"],
         "player_xg_original_raw_sha":sha256(players).hexdigest(),
         "player_fixture_rows":source["player_rows"],
         "finished_fixture_sides_with_xg":source["side_count_with_xg"],
         "old_finished_fixtures":src["ft"],
         "source_future_targets_with_both_prior5_result_form":count,
         "source_future_targets_with_both_prior5_FPL_player_xg":qual,
         "precise_previous_game_team_side_xg_checks":points,
         "original_pitchapi_team_xg_first_published_proven":False}

def run(*,fetcher=fetch):
    s=[x for x in independently_pinned_sources() if x["season"]=="2023-24" and x["ft"]<380]
    if len(s)!=6:raise FPLLineageError("SIX_2023_HISTORIC_PROVEN_SOURCES_REQUIRED")
    results=[]
    for src in s:
        try:
            results.append({"state":"OLD_PUBLISHED_PLAYER_XG_CHECKED",**inspect_one(src,fetcher=fetcher)})
        except Exception as e:
            results.append({"source_commit":src["commit"],"state":"BLOCKED_OLD_XG_SOURCE",
               "failure_type":type(e).__name__,"source_future_targets_with_both_prior5_FPL_player_xg":0})
    return {"schema":SCHEMA,"source_count":len(results),
        "independent_public_2023_source_clocks":len(s),
        "player_xg_source_verified":sum(x["state"]=="OLD_PUBLISHED_PLAYER_XG_CHECKED" for x in results),
        "sum_snapshot_target_pairs_confirmed_player_xg":sum(
         x["source_future_targets_with_both_prior5_FPL_player_xg"] for x in results),
        "snapshot_target_pairs_may_overlap_with_same_fixture":True,
        "sources":results,
        "FPL_Opta_player_xg_not_original_PitchAPI_team_xg":True,
        "training_allowed":False,"gate14_pass":False,"test_examined":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FPLLineageError("REPORT_APPEND_ONLY")
    d=run();target.write_text(json.dumps(d,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print(json.dumps({"independent_source_snapshots":d["source_count"],
      "verified_snapshots_with_real_FPL_player_xg":d["player_xg_source_verified"],
      "snapshot_target_pairs_with_real_old_xg":d["sum_snapshot_target_pairs_confirmed_player_xg"],
      "pitchapi_original_m1_pit":False},sort_keys=True))
if __name__=="__main__":main()
