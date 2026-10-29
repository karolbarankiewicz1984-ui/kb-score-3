"""KB3 step14 — enumerate all 74 actual historic FPL fixture-file revisions.

The Git COMMITTER date is not accepted as as-of proof. Instead require
an independently GHArchive-timestamped old public push of a DESCENDANT of the
candidate SHA. GitHub compare DAG proves ancestry; earliest such old push
is used as a conservative *publication upper bound*. Later snapshots, even
ones with an old-looking committer date, cannot pass for earlier kickoff.

Pure inventory/research, no production training and no 2026/27 TEST.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import csv,io,json,os,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources
from scripts.step14_fpl_core_2025_independent_asof import _utc

REPO="vaastav/Fantasy-Premier-League"
SEASONS=("2023-24","2024-25")
SCHEMA="kb3-step14-74-FPL-revisions-historic-GHArchive-ancestor-witnesses-v1"
class ProofError(ValueError):pass

def api(url,token=None,attempts=4):
    headers={"User-Agent":"kb3-independent-74-historic-source-verify",
             "Accept":"application/vnd.github+json"}
    if token:headers["Authorization"]="Bearer "+token
    for attempt in range(attempts):
        try:
            with urlopen(Request(url,headers=headers),timeout=40) as f:
                return json.loads(f.read(9_000_000))
        except (HTTPError,URLError,TimeoutError) as exc:
            if attempt==attempts-1:raise ProofError("GITHUB_API_FETCH_FAILED") from exc
            time.sleep(1+2*attempt)

def list_revisions(season,fetcher=api,token=None):
    path=f"data/{season}/fixtures.csv"
    encoded=path.replace("/","%2F")
    url=f"https://api.github.com/repos/{REPO}/commits?path={encoded}&per_page=100"
    doc=fetcher(url,token=token)
    if not isinstance(doc,list):raise ProofError("NOT_A_COMMIT_LIST")
    return [{"sha":x["sha"],"committer_date_INFORMATIONAL_ONLY":x["commit"]["committer"]["date"]}
            for x in doc]

def compare_is_ancestor(candidate,anchor,fetcher=api,token=None,cache=None):
    cache=cache if cache is not None else {}
    key=(candidate,anchor)
    if key in cache:return cache[key]
    url=f"https://api.github.com/repos/{REPO}/compare/{candidate}...{anchor}"
    item=fetcher(url,token=token)
    status=item.get("status")
    if status not in ("ahead","identical","diverged","behind"):
        raise ProofError("UNRECOGNIZED_GIT_GRAPH_STATUS")
    result=status in ("ahead","identical") and item.get("behind_by")==0
    cache[key]=result
    return result

def inventory(*,fetcher=api,token=None,revision_override=None,ancestry=None):
    old=independently_pinned_sources()
    anchors={s:sorted([x for x in old
          if x.get("season")==s and x.get("provider")=="FPL"],
          key=lambda x:_utc(x["push"])) for s in SEASONS}
    if not all(anchors.values()):raise ProofError("HISTORIC_EXTERNAL_PUSH_ANCHORS_ABSENT")
    expected={"2023-24":38,"2024-25":36}
    rev={s:list_revisions(s,fetcher=fetcher,token=token)
         if revision_override is None else revision_override[s] for s in SEASONS}
    if {s:len(x) for s,x in rev.items()}!=expected:
        raise ProofError("FPL_HISTORY_IS_NOT_38_PLUS_36")
    if any(len({x["sha"] for x in rev[s]})!=expected[s] for s in SEASONS):
        raise ProofError("DUPLICATE_FPL_REVISION")
    cache={}
    record=[]
    for season in SEASONS:
        for candidate in rev[season]:
            sha=candidate["sha"]
            candidates=anchors[season]
            # First prove ancestry of latest historically attested public head.
            checker=ancestry if ancestry is not None else lambda a,b:compare_is_ancestor(
                  a,b,fetcher=fetcher,token=token,cache=cache)
            if not checker(sha,candidates[-1]["commit"]):
                record.append({"season":season,"sha":sha,
                   "status":"NOT_ANCESTOR_OF_ANY_ACCEPTED_OLD_PUBLIC_ANCHOR",
                   "committer_date_UNTRUSTED":candidate["committer_date_INFORMATIONAL_ONLY"],
                   "certified_before_target":False})
                continue
            left=0;right=len(candidates)-1
            while left<right:
                mid=(left+right)//2
                if checker(sha,candidates[mid]["commit"]):right=mid
                else:left=mid+1
            anchor=candidates[left]
            record.append({"season":season,"sha":sha,
              "status":"OLD_GITHUB_SHA_GIT_ANCESTRY_PUBLISHED_BY_VERIFIED_PUSH",
              "committer_date_UNTRUSTED":candidate["committer_date_INFORMATIONAL_ONLY"],
              "witnessed_public_by_utc":anchor["push"],
              "old_public_descendant_anchor_sha":anchor["commit"],
              "external_GHArchive_event_id":str(anchor.get("event",anchor.get("event_id"))),
              "provenance_kind":"GIT_ANCESTOR_OF_INDEPENDENTLY_CLOCKED_GHARCHIVE_PUSH",
              "certified_before_target":True})
    if len(record)!=74:raise ProofError("NOT_ALL_74_INVENTORIED")
    return {"schema":SCHEMA,
       "historical_fixture_file_revisions_by_season":expected,
       "all_74_source_revisions_inventoried":True,
       "verified_old_external_GHArchive_anchors":{s:len(anchors[s]) for s in SEASONS},
       "committer_time_never_qualifies_as_asof":True,
       "hist_publication_qualified_ancestor_revisions":
           sum(x["certified_before_target"] for x in record),
       "not_externally_witnessed_revisions":
           sum(not x["certified_before_target"] for x in record),
       "fpl_revisions":record,
       "original_M1_train_eligible":False,
       "TEST_read":False,"GATE14":"PENDING"}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    a=p.parse_args()
    dest=Path(a.out)
    if dest.exists():raise ProofError("APPEND_ONLY")
    report=inventory(token=os.environ.get("GH_PUBLIC_TOKEN"))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"all_revisions":74,
         "verified_ancestry_public":report["hist_publication_qualified_ancestor_revisions"],
         "unverified":report["not_externally_witnessed_revisions"],
         "gate":"PENDING"},sort_keys=True))

if __name__=="__main__":main()
