"""Find verifiable 2024/25 full last-season source and in-season 2025/26 FPL snapshots.

Commit date merely nominates GHArchive archive hour. Never backdate.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import argparse,json
from scripts.step14_full_history_harvest_independent_clocks import probe_one

R="vaastav/Fantasy-Premier-League"
CANDIDATES=(
("2024-25","FPL",R,"data/2024-25/fixtures.csv","59c767596750f554ba464de94cf4fce8664a6cbe","2025-06-04T15:20:23Z"),
("2025-26","FPL",R,"data/2025-26/fixtures.csv","46277afda009b340e738336dabc4b0822dd80c57","2025-08-01T08:49:42Z"),
("2025-26","FPL",R,"data/2025-26/fixtures.csv","d8f2ea3f56d1e6c25cfc1ed2773fbd945241fb93","2025-11-01T00:11:46Z"),
("2025-26","FPL",R,"data/2025-26/fixtures.csv","2c43a95002e0a3ec0700b725da76fdd5fefcd1a6","2026-02-05T08:00:25Z"),
("2025-26","FPL",R,"data/2025-26/fixtures.csv","77ab48216404b0f49f55fa724c520af25b32ddae","2026-03-13T01:04:19Z")
)
def audit(probe=probe_one):
    with ThreadPoolExecutor(max_workers=4) as p:
        fs={p.submit(probe,c):i for i,c in enumerate(CANDIDATES)}
        result=[None]*len(CANDIDATES)
        for f in as_completed(fs):result[fs[f]]=f.result()
    yes=[r for r in result if r["verified_publication"]]
    return {"schema":"kb3-step14-last-2024-and-validation-2025-fpl-old-sources-v1",
       "source_candidates":len(result),
       "sources":result,"independently_verified_sources":yes,
       "original_pitchapi_historic_pit_established":False,
       "training_allowed":False,"gate14_pass":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    d=Path(a.out);d.parent.mkdir(parents=True,exist_ok=True)
    if d.exists():raise ValueError("APPEND_ONLY")
    r=audit();d.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"new_FPL_historical_published_at_receipts":len(r["independently_verified_sources"]),
                      "by_season":{s:sum(x["season"]==s for x in r["independently_verified_sources"]) for s in ("2024-25","2025-26")},
                      "original_PitchAPI_feature_pit":False},sort_keys=True))
if __name__=="__main__":main()
