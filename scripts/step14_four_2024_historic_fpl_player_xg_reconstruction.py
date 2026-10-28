"""2024/25 historic FPL/Opta source player xG — four independently published snapshots.

Research-only xG last5 on exact FPL fixture/team, NOT interchangeable with
original PitchAPI native team-xG; no fake historical PitchAPI published_at.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json
from scripts.step14_six_2023_historic_fpl_player_xg_reconstruction import inspect_one
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources
from src.kb3_step14_multiseason_pit import fetch

SCHEMA="kb3-step14-2024-four-real-published-FPL-Opta-player-xg-last5-v1"
def run(fetcher=fetch):
    old=[s for s in independently_pinned_sources() if s["season"]=="2024-25" and s.get("provider")=="FPL"]
    if len(old)!=4:raise ValueError("FOUR_2024_FPL_SOURCE_PROOFS_REQUIRED")
    results=[]
    for src in old:
        try:
            results.append({"state":"HISTORICAL_2024_FPL_XG_MEASURED",
                **inspect_one(src,fetcher=fetcher)})
        except Exception as e:
            results.append({"source_commit":src["commit"],"state":"BLOCKED_2024_FPL_PLAYER_XG",
                "safe_error_type":type(e).__name__,
                "source_future_targets_with_both_prior5_FPL_player_xg":0})
    return {"schema":SCHEMA,"four_independent_old_2024_source_clocks_verified":4,
        "four_real_xg_sources_success":sum(x["state"]=="HISTORICAL_2024_FPL_XG_MEASURED" for x in results),
        "source_target_pairs_with_pre_target_FPL_player_xg":sum(x["source_future_targets_with_both_prior5_FPL_player_xg"] for x in results),
        "sources":results,"FPL_Opta_not_original_PitchAPI_xG":True,
        "train_original_121_plus_38_not_approved":True,
        "original_train_pit_eligible":0,"original_validation_pit_eligible":0,
        "training_allowed":False,"gate14_pass":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise ValueError("APPEND_ONLY")
    r=run();path.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"new_old_2024_FPL_source_xG_OK":r["four_real_xg_sources_success"],
                      "pre_match_source_FPL_player_xG_target_pairs":r["source_target_pairs_with_pre_target_FPL_player_xg"],
                      "original_PitchAPI_PIT":False},sort_keys=True))
if __name__=="__main__":main()
