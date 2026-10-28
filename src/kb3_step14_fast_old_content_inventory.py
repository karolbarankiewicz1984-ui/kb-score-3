"""Fast content-only historic inventory: NO external publication-time claims."""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from urllib.parse import urlencode
import argparse,json
from pathlib import Path
from src.kb3_step14_elo_rollover_xg_clock_discovery import SEARCHES,REPO,git_candidates,inspect_ft,inspect_xg
from src.kb3_step14_multiseason_pit import fetch

def run(fetcher=fetch):
    summaries=[]
    for option in SEARCHES:
        out={"kind":option["kind"],"season":option["season"],"path":option["path"],
             "independent_publication_time_proven":False}
        try:
            url=(f"https://api.github.com/repos/{REPO}/commits?"+
                 urlencode({"path":option["path"],"until":option["until"],"per_page":100}))
            commits=git_candidates(json.loads(fetcher(url)),option)
            out["candidate_commits"]=len(commits)
            out["snapshots"]=[]
            for c in commits:
                raw=fetcher(f"https://raw.githubusercontent.com/{REPO}/{c['sha']}/{option['path']}")
                p={"commit":c["sha"],
                   "committer_date_NOT_INDEPENDENT_PUBLICATION":c["git_committer_search_hint_only"],
                   "old_raw_sha256":sha256(raw).hexdigest()}
                if option["kind"]=="ELO_FULL_FT":
                    p.update(inspect_ft(raw,None))
                else:
                    p.update(inspect_xg(raw,None))
                out["snapshots"].append(p)
            out["state"]="HISTORIC_BLOB_CONTENT_OBSERVED"
        except Exception as exc:
            out["state"]="SOURCE_INVENTORY_UNAVAILABLE"
            out["error_type"]=type(exc).__name__
        summaries.append(out)
    return {"schema":"kb3-step14-old-content-no-publication-clock-v1",
            "records":summaries,
            "any_full_380_FT_content_in_2024_window":any(
                s.get("all_380_ended") for x in summaries for s in x.get("snapshots",[])),
            "external_publication_proof":False,"original_native_elo_certified":False,
            "team_xg_pitchapi_equivalence_proven":False,"train_allowed":False,"gate14_pass":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True)
    out=Path(ap.parse_args().output)
    rep=run()
    out.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(rep,sort_keys=True,indent=2)+"\n"
    if out.exists():
        if out.read_text(encoding="utf8")!=data:raise ValueError("REPORT_IMMUTABLE")
    else:out.write_text(data,encoding="utf8")
    print(json.dumps({
       "old_380_full_content_found":rep["any_full_380_FT_content_in_2024_window"],
       "sources":[{"kind":x["kind"],"season":x["season"],"state":x["state"],
           "snapshots":[{"commit":s["commit"],"FT":s.get("old_completed_FT"),
                         "player_xg_header":s.get("old_fpl_row_has_player_expected_goals_column")}
                         for s in x.get("snapshots",[])]} for x in rep["records"]],
       "independent_publication_proven":False,"gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
