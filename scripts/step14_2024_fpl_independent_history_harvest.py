"""2024/25 FPL historical source harvest: six real candidate old commits.

Commit timestamp is only an hour to inspect; independent GHArchive exact
PushEvent and immutable original source bytes needed before prematch admission.
No PitchAPI secret/private PEM, no training/test/target scores.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
from pathlib import Path
import argparse,json
from scripts.step14_full_history_harvest_independent_clocks import probe_one

REPO="vaastav/Fantasy-Premier-League"
FILE="data/2024-25/fixtures.csv"
CANDIDATES=tuple(("2024-25","FPL",REPO,FILE,sha,stamp) for sha,stamp in (
 ("f42ed38d279afc705448ebc2b89e48838a0fdfba","2024-09-23T21:15:45Z"),
 ("e3135daf0fcb706cc41f237e5c691517bd3432c1","2024-11-20T00:44:27Z"),
 ("b9618a5d9eebce9bc5ab0e6683bfb8fc420ac848","2025-01-18T05:15:44Z"),
 ("58de8250c856e3476d45557422b257a3659b2b26","2025-03-11T11:53:12Z"),
 ("29e6c2f4590b1a03f218552ca676b9495539cfdc","2025-04-11T12:32:01Z"),
 ("a7089bab28e2a6012cde62b4fbd692f975792a55","2025-05-24T12:26:14Z")
))
def audit(probe=probe_one):
    with ThreadPoolExecutor(max_workers=4) as pool:
        f={pool.submit(probe,c):i for i,c in enumerate(CANDIDATES)}
        ret=[None]*len(CANDIDATES)
        for future in as_completed(f):
            ret[f[future]]=future.result()
    good=[x for x in ret if x["verified_publication"]]
    return {"schema":"kb3-step14-2024-25-old-FPL-six-GHArchive-source-harvest-v1",
        "candidates":len(ret),"independently_server_published_source_count":len(good),
        "sources":ret,"verified_sources":good,
        "original_pitchapi_team_xg_first_published_proven":False,
        "original_M1_train_allowed":False,"gate14_pass":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);args=p.parse_args()
    dest=Path(args.out)
    if dest.exists():raise ValueError("APPEND_ONLY")
    dest.parent.mkdir(parents=True,exist_ok=True)
    r=audit();dest.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"candidate_old_2024_source_commits":r["candidates"],
                       "independent_2024_FPL_published_receipts":r["independently_server_published_source_count"],
                       "gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
