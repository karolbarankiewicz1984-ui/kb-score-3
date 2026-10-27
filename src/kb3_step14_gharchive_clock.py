"""Third-party GH Archive PushEvent clock probe for four historical blob SHAs.

Raw Git committer timestamps are user-controlled and NOT public availability
proof. GH Archive created_at is an external archived copy of GitHub events,
which can corroborate a concrete push of the exact SHA to public repository.
Does not contain PitchAPI results or test labels; never grants model approval.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
import gzip
import json

REPO="openfootball/football.json"
SAMPLES=(
 ("2024-10-02-13","5f777dc6e2cd02cdafd1520e81b7e338284fb7a7","m_3AMymS","2024-10-05T16:30:00Z"),
 ("2024-11-05-05","d0a780d5a22b34375f320a51e52e723814d59aff","m_2IJhgL","2024-11-09T17:30:00Z"),
 ("2025-01-29-05","831bb41621b99b7081f9942ff294fb3c91165448","m_2g5x00","2025-02-02T16:30:00Z"),
 ("2025-07-30-16","fdca227e6fc8284865254f009e987ce7a70935a0","SEASON_2025_26_FIRST","2025-08-18T19:00:00Z"),
)
MAX_RECORDS_PER_ARCHIVE=1_500_000


def read_hour(archive_hour,*,open_stream=None):
    if open_stream is None:
        def open_stream(url):
            req=Request(url,headers={"User-Agent":"KB3-historical-PIT-audit"})
            return urlopen(req,timeout=50)
    url=f"https://data.gharchive.org/{archive_hour}.json.gz"
    try:
        f=open_stream(url)
        detected=[]
        n=0
        with f:
            with gzip.GzipFile(fileobj=f,mode="rb") as raw:
                for line in raw:
                    n+=1
                    if n>MAX_RECORDS_PER_ARCHIVE:
                        raise ValueError("GHARCHIVE_HOUR_TOO_LARGE")
                    if b'"PushEvent"' not in line or b'football.json' not in line:
                        continue
                    obj=json.loads(line)
                    if obj.get("type")!="PushEvent" or obj.get("repo",{}).get("name")!=REPO:
                        continue
                    payload=obj.get("payload",{})
                    all_sha=[payload.get("head")]
                    all_sha.extend(x.get("sha") for x in payload.get("commits",[]) if type(x) is dict)
                    detected.append({
                        "created_at_utc":obj.get("created_at"),
                        "event_id":obj.get("id"),
                        "event_repo_name":REPO,
                        "push_ref":payload.get("ref"),
                        "head_sha":payload.get("head"),
                        "included_commit_shas":sorted({s for s in all_sha if type(s) is str}),
                    })
        return {"status":"READ_OK","records_scanned":n,"push_events_found":detected,"archive_url":url}
    except Exception as exc:
        return {"status":"READ_UNAVAILABLE","error_type":type(exc).__name__,
                "archive_url":url,"records_scanned":None,"push_events_found":[]}


def audit_push_clock(fetch_hour=read_hour):
    hours=sorted({s[0] for s in SAMPLES})
    captured={h:fetch_hour(h) for h in hours}
    records=[]
    for hour,sha,fixture,kickoff in SAMPLES:
        source=captured[hour]
        same=[e for e in source.get("push_events_found",[])
              if sha in e.get("included_commit_shas",()) and
              e.get("push_ref") in ("refs/heads/master","refs/heads/main")]
        earlier=[]
        for event in same:
            try:
                push=datetime.fromisoformat(event["created_at_utc"].replace("Z","+00:00"))
                ko=datetime.fromisoformat(kickoff.replace("Z","+00:00"))
            except Exception:
                continue
            if push.tzinfo is not None and push<ko:
                earlier.append(event)
        records.append({
            "candidate_source_commit_sha":sha,
            "pitch_fixture_id_or_source_season":fixture,
            "kickoff_utc":kickoff,
            "source_archive_hour":hour,
            "gharchive_hour_read_status":source["status"],
            "matching_public_push_events":len(same),
            "push_events_before_kickoff":len(earlier),
            "server_created_at_utc":earlier[0]["created_at_utc"] if earlier else None,
            "server_github_event_id":earlier[0]["event_id"] if earlier else None,
            "public_branch_ref":earlier[0]["push_ref"] if earlier else None,
            "public_branch_head_sha":earlier[0]["head_sha"] if earlier else None,
            "independent_public_push_time_corroborated":bool(earlier),
            "historical_blob_content_inspected_in_separate_audit":True,
            "native_pitchapi_team_pair_crosswalk_verified":False,
            "eligible_for_official_m1":False,
        })
    return {
        "schema":"kb3-step14-thirdparty-public-push-clock-v1",
        "source":"GH Archive hourly public GitHub event stream",
        "archive_hours_scanned":hours,
        "hour_states":{h:{"status":v["status"],"n_events":len(v.get("push_events_found",[])),
                           "archive_url":v["archive_url"],
                           "error_type":v.get("error_type")} for h,v in captured.items()},
        "independent_push_sha_samples_corroborated":sum(x["independent_public_push_time_corroborated"] for x in records),
        "native_pitchapi_team_pairs_verified":0,
        "official_train_eligible":0,
        "test_labels_read":0,
        "paid_sports_provider_requests":0,
        "gate14_pass":False,
        "records":records,
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    args=p.parse_args()
    r=audit_push_clock()
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:r[k] for k in ("hour_states","independent_push_sha_samples_corroborated",
                         "native_pitchapi_team_pairs_verified","official_train_eligible","gate14_pass")},sort_keys=True))
