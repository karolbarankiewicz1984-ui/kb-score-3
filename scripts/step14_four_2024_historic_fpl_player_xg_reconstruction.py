"""2024/25 historic FPL/Opta source player xG — four independently published snapshots.

Research-only xG last5 on exact FPL fixture/team, NOT interchangeable with
original PitchAPI native team-xG; no fake historical PitchAPI published_at.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,csv,io
from scripts.step14_six_2023_historic_fpl_player_xg_reconstruction import inspect_one
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources
from src.kb3_step14_multiseason_pit import fetch
from src.kb3_step14_xg_four_gates import XGFourGateError

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
            row={"source_commit":src["commit"],"state":"BLOCKED_2024_FPL_PLAYER_XG",
                "safe_error_type":type(e).__name__,
                "safe_error_code":str(e) if isinstance(e,XGFourGateError) else None,
                "source_future_targets_with_both_prior5_FPL_player_xg":0}
            if isinstance(e,XGFourGateError) and str(e)=="UNKNOWN_FPL_VENUE_SIDE":
                try:
                    url=f"https://raw.githubusercontent.com/{src['repo']}/{src['commit']}/data/2024-25/gws/merged_gw.csv"
                    raw=fetcher(url,limit=40_000_001)
                    old=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
                    formats=sorted({r.get("was_home","") for r in old})
                    if all(len(x)<30 for x in formats):
                        row["historic_player_was_home_only_encoding_values"]=formats[:12]
                        row["historic_player_rows_inspected_for_format"]=len(old)
                except Exception:
                    row["historic_player_was_home_format_probe"]="UNAVAILABLE"
            results.append(row)
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
