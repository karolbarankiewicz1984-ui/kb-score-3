"""Harvest actual old public match snapshots with independent GH Archive PushEvents.

Git committer times NOMINATE archive hours, NEVER certify publication.
Only exact independent repository/branch/head SHA GHArchive server events
with commit-addressed immutable raw bytes receive HISTORIC_PUBLIC.
Network failures are explicitly not evidence of absence. No PitchAPI key,
native IDs, result labels/TEST, xG substitutions or backdated source times.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
import argparse,csv,io,json
from src.kb3_step14_fpl_historic_clock_pilot import gharchive_one_hour,verify_raw_csv
from src.kb3_step14_multiseason_pit import fetch,utc,parse_openfootball

SCHEMA="kb3-step14-historical-full-three-season-old-public-snapshots-source-harvest-v1"
# Commit dates only direct lookups to determine a candidate hour, not proof.
CANDIDATES=(
 ("2023-24","FPL","vaastav/Fantasy-Premier-League","data/2023-24/fixtures.csv","8b05861fb33ee89bae34c2b6d06564449a5885db","2023-09-25T15:34:01Z"),
 ("2023-24","FPL","vaastav/Fantasy-Premier-League","data/2023-24/fixtures.csv","546143eb5d0ae6d250e074374152e8be4b15719b","2024-01-23T13:01:20Z"),
 ("2023-24","FPL","vaastav/Fantasy-Premier-League","data/2023-24/fixtures.csv","f061aafa88a921dd70fd2b0f72b8020889d8e589","2024-02-22T10:23:39Z"),
 ("2023-24","FPL","vaastav/Fantasy-Premier-League","data/2023-24/fixtures.csv","436f1ff2d306783d3e3892dc3d3ce21712cbc08e","2024-04-08T10:31:08Z"),
 ("2024-25","OpenFootball","openfootball/football.json","2024-25/en.1.json","d278eea6fc32c276be0121a23b01fa3c15ca5f0a","2024-09-19T17:02:13Z"),
 ("2024-25","OpenFootball","openfootball/football.json","2024-25/en.1.json","d0a780d5a22b34375f320a51e52e723814d59aff","2024-11-05T05:10:39Z"),
 ("2024-25","OpenFootball","openfootball/football.json","2024-25/en.1.json","97a50f4d2ba526666bbbe1d0a2e14315f22a53ee","2025-01-18T19:26:27Z"),
 ("2024-25","OpenFootball","openfootball/football.json","2024-25/en.1.json","ca4db693ee1fe5bac7ca06be5403dda9df3561e8","2025-02-26T05:23:38Z"),
 ("2024-25","OpenFootball","openfootball/football.json","2024-25/en.1.json","79f9a5bed8421ce312e2359f48cc12a756e79369","2025-05-13T05:28:25Z"),
 ("2025-26","OpenFootball","openfootball/football.json","2025-26/en.1.json","268e8237611c5fbc5854bda16c3206af49701beb","2025-11-12T05:20:03Z"),
 ("2025-26","OpenFootball","openfootball/football.json","2025-26/en.1.json","4a843cdd1008cd13498a7274501cfc16a37c76b4","2026-01-08T05:19:34Z"),
 ("2025-26","OpenFootball","openfootball/football.json","2025-26/en.1.json","25cfaf102954ebbcdc48f9c2984198b71d48610d","2026-03-13T05:43:14Z"),
 ("2025-26","OpenFootball","openfootball/football.json","2025-26/en.1.json","b4ceb69e8336bed220575fcb98928e7f54847894","2026-05-19T08:19:43Z"),
)
class HarvestError(ValueError):pass

def hour_label(ts):
    return utc(ts).strftime("%Y-%m-%d-%H")

def verify_old_raw(candidate,raw,push):
    season,provider,repo,path,commit,committer=candidate
    if not raw or len(raw)>3_000_000:
        raise HarvestError("PUBLIC_BLOB_SIZE_INVALID")
    if provider=="FPL":
        rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        if len(rows)!=380:raise HarvestError("OLD_FIXTURE_GRID_NOT_380")
        n=sum(r.get("finished")=="True" for r in rows)
        verify_raw_csv(raw,expected_finished=n,push_time_utc=push)
    else:
        doc=json.loads(raw)
        m=doc.get("matches")
        if not isinstance(m,list) or len(m)!=380:raise HarvestError("OLD_FIXTURE_GRID_NOT_380")
        n=sum(isinstance(x.get("score"),dict) and x["score"].get("ft") is not None for x in m)
        src={"season":season,"repo":repo,"path":path,"commit":commit,
            "sha":sha256(raw).hexdigest(),"push":push,
            "ft":n}
        parse_openfootball(raw,src)
    return n

def probe_one(candidate,read_hour=gharchive_one_hour,fetcher=fetch):
    season,provider,repo,path,commit,committer=candidate
    result={"season":season,"provider":provider,"repo":repo,"path":path,
        "commit":commit,"candidate_commit_time_ONLY_NOT_PUBLICATION":committer,
        "candidate_hour_NOT_PUBLICATION":hour_label(committer),
        "independent_publication_UTC":None,"independent_push_event_id":None,
        "source_sha256":None,"finished_matches_in_blob":None,
        "verified_publication":False,"no_training_or_target_scores_read":True}
    try:
        evidence=read_hour(hour_label(committer))
        result["gharchive_hour_status"]=evidence.get("status")
        matches=[e for e in evidence.get("events",[]) if
           commit in e.get("shas",[]) and e.get("repository")==repo
           and e.get("ref") in ("refs/heads/master","refs/heads/main")
           and e.get("event_id") and e.get("server_created_at_utc")
           and hour_label(e["server_created_at_utc"])==hour_label(committer)]
        if len(matches)!=1:
            result["state"]="NO_EXACT_INDEPENDENT_PUSH_IN_CANDIDATE_HOUR"
            return result
        m=matches[0];stamp=m["server_created_at_utc"]
        raw=fetcher(f"https://raw.githubusercontent.com/{repo}/{commit}/{path}",limit=3_000_001)
        finished=verify_old_raw(candidate,raw,stamp)
        result.update({"state":"HISTORIC_PUBLIC_PUSH_AND_SOURCE_BYTES_VERIFIED",
            "independent_publication_UTC":stamp,
            "independent_push_event_id":str(m["event_id"]),
            "source_sha256":sha256(raw).hexdigest(),
            "finished_matches_in_blob":finished,
            "verified_publication":True})
    except Exception as e:
        result["state"]="UNAVAILABLE_OR_INVALID_FAIL_CLOSED"
        result["safe_failure_type"]=type(e).__name__
    return result

def audit(probe=probe_one):
    with ThreadPoolExecutor(max_workers=5) as pool:
        future={pool.submit(probe,c):i for i,c in enumerate(CANDIDATES)}
        indexed=[None]*len(CANDIDATES)
        for job in as_completed(future):
            indexed[future[job]]=job.result()
    verified=[r for r in indexed if r["verified_publication"]]
    for r in verified:
        if r["independent_publication_UTC"] is None or r["source_sha256"] is None:
            raise HarvestError("UNATTESTED_SOURCE_MARKED_PUBLIC")
    return {"schema":SCHEMA,"candidate_commits_checked":len(CANDIDATES),
            "new_real_archived_public_snapshots":len(verified),
            "verified_by_season":dict(sorted(Counter(x["season"] for x in verified).items())),
            "failure_or_missing_event_count":len(CANDIDATES)-len(verified),
            "missing_gharchive_events_DO_NOT_MEAN_source_never_existed":True,
            "snapshot_observations":indexed,
            "original_PitchAPI_team_xg_first_published_proven":False,
            "historical_public_result_reconstruction_only":True,
            "original_full_121_plus_38_pit_complete":False,
            "official_M1_training_allowed":False,"gate14_pass":False,
            "test_rows_read":False,"sports_provider_api_calls":0}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);o=p.parse_args()
    d=Path(o.out);d.parent.mkdir(parents=True,exist_ok=True)
    if d.exists():raise HarvestError("APPEND_ONLY_OUTPUT_EXISTS")
    report=audit()
    d.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"verified_sources":report["new_real_archived_public_snapshots"],
       "verified_by_season":report["verified_by_season"],
       "cannot_retroactively_approve_original_M1":True},sort_keys=True))
if __name__=="__main__":main()
