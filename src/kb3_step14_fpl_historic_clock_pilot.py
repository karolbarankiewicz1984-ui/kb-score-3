"""Strict research-only resurrection of 2023/24 public historical FPL match snapshots.

Independent GHArchive PushEvent proof is mandatory before an archived
seasonal result can be described as actually published before a later match.
Do NOT export FT scores, join PitchAPI native IDs, read 2026/27 TEST, use odds,
approve real TRAIN or substitute player xG for PitchAPI xG.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from urllib.request import Request,urlopen
from pathlib import Path
import csv,gzip,io,json

REPO="vaastav/Fantasy-Premier-League"
FILE="data/2023-24/fixtures.csv"
SCHEMA="kb3-step14-fpl-2023-24-historic-public-pit-source-pilot-v1"
SAMPLES=(
 ("2023-08-16-02","be15e285f106d1becc6f24c0c470ec9ada8c935a",10),
 ("2023-10-05-14","96fbc38ee6e36e3a7250081a787b65a1a27c944d",70),
 ("2023-10-27-08","615da45c450fb13993b7e8da4c8388d7e2f57703",90),
)
MAX_ARCHIVE_EVENTS=2_500_000

class FPLSourceError(ValueError): pass

def _utc(s):
    try:
        a=datetime.fromisoformat(s.replace("Z","+00:00"))
    except (AttributeError,ValueError) as exc:raise FPLSourceError("BAD_UTC") from exc
    if a.tzinfo is None or a.utcoffset().total_seconds()!=0:
        raise FPLSourceError("UTC_REQUIRED")
    return a.astimezone(timezone.utc)

def verify_raw_csv(raw,*,expected_finished,push_time_utc):
    if not isinstance(raw,bytes) or not 5000<len(raw)<3_000_000:
        raise FPLSourceError("BAD_BYTES")
    stream=io.StringIO(raw.decode("utf-8-sig"),newline="")
    reader=csv.DictReader(stream)
    names=set(reader.fieldnames or [])
    required={"id","team_h","team_a","kickoff_time","finished","team_h_score","team_a_score"}
    if not required<=names:
        raise FPLSourceError("MISSING_FIELDS")
    ids=set(); finished=0; empty=0; prior=0
    push=_utc(push_time_utc)
    for row in reader:
        fid=row["id"]
        if not fid or fid in ids:raise FPLSourceError("DUPLICATE_OR_BAD_ID")
        ids.add(fid)
        is_done=row["finished"]
        h,a=row["team_h_score"],row["team_a_score"]
        if is_done=="True":
            if not (h and a): raise FPLSourceError("FINISHED_MATCH_NO_FT")
            if any(float(v)!=int(float(v)) or int(float(v))<0 for v in (h,a)):
                raise FPLSourceError("BAD_FINAL_SCORE")
            when=_utc(row["kickoff_time"])
            if when>=push:raise FPLSourceError("FUTURE_SCORE_IN_HISTORIC_PUBLIC_BLOB")
            finished+=1
            prior+=1
        elif is_done=="False":
            if h or a:raise FPLSourceError("PREMATCH_ROW_HAS_SCORE")
            empty+=1
        else:raise FPLSourceError("UNKNOWN_FINISHED_VALUE")
    if len(ids)!=380 or finished!=expected_finished or empty!=380-finished:
        raise FPLSourceError("HISTORICAL_SNAPSHOT_COUNT_CHANGED")
    return {"season":"2023-24","fixture_rows_checked":len(ids),
            "finished_ft_records_available_at_historical_source_publication":prior,
            "unplayed_rows_have_null_scores":empty,
            "any_future_or_target_score_used":False}

def fetch_old_csv(commit):
    url=f"https://raw.githubusercontent.com/{REPO}/{commit}/{FILE}"
    with urlopen(Request(url,headers={"User-Agent":"KB3-step14-fpl-pit-proof"}),timeout=40) as f:
        return f.read(3_000_001)

def gharchive_one_hour(hour,*,opener=None):
    if opener is None:
        def opener(url):
            return urlopen(Request(url,headers={"User-Agent":"KB3-step14-fpl-pit-proof"}),timeout=65)
    url=f"https://data.gharchive.org/{hour}.json.gz"
    try:
        matches=[];total=0
        with opener(url) as stream,gzip.GzipFile(fileobj=stream,mode="rb") as compressed:
            for line in compressed:
                total+=1
                if total>MAX_ARCHIVE_EVENTS:
                    raise FPLSourceError("GHARCHIVE_TOO_LARGE")
                if b'"PushEvent"' not in line or b'Fantasy-Premier-League' not in line:
                    continue
                event=json.loads(line)
                if (event.get("type")!="PushEvent" or
                    event.get("repo",{}).get("name")!=REPO):
                    continue
                payload=event.get("payload",{})
                shas={payload.get("head")}
                shas.update(c.get("sha") for c in payload.get("commits",[]) if isinstance(c,dict))
                if payload.get("ref") not in ("refs/heads/master","refs/heads/main"):
                    continue
                matches.append({"event_id":event.get("id"),
                                "server_created_at_utc":event.get("created_at"),
                                "repository":REPO,
                                "ref":payload.get("ref"),
                                "shas":sorted(x for x in shas if isinstance(x,str))})
        return {"status":"READ_OK","hour":hour,"events_scanned":total,"events":matches}
    except (OSError,EOFError,TimeoutError) as exc:
        return {"status":"READ_UNAVAILABLE","hour":hour,"error_type":type(exc).__name__,
                "events":[]}

def audit(*,read_archived_csv=fetch_old_csv,read_hour=gharchive_one_hour):
    verified=[]
    for hour,commit,expected_count in SAMPLES:
        events=read_hour(hour)
        if events.get("status")!="READ_OK":
            raise FPLSourceError("INDEPENDENT_HISTORICAL_SERVER_CLOCK_UNAVAILABLE")
        matched=[e for e in events["events"] if commit in e["shas"] and
                 e.get("server_created_at_utc") and e.get("event_id")]
        if len(matched)!=1:
            raise FPLSourceError("EXACT_SHA_PUBLIC_GH_ARCHIVE_PUSH_NOT_CORROBORATED")
        proof=matched[0]
        push=proof["server_created_at_utc"]
        expected_hour=datetime.strptime(hour,"%Y-%m-%d-%H").replace(tzinfo=timezone.utc)
        if not expected_hour<=_utc(push)<expected_hour.replace(minute=59,second=59,microsecond=999999):
            raise FPLSourceError("GHARCHIVE_SERVER_TIME_NOT_IN_ARCHIVE_HOUR")
        raw=read_archived_csv(commit)
        checked=verify_raw_csv(raw,expected_finished=expected_count,push_time_utc=push)
        verified.append({
            "public_repo":REPO,"season":"2023-24",
            "server_confirmed_public_push_utc":push,
            "server_event_id":str(proof["event_id"]),
            "historic_commit_sha":commit,
            "historic_original_csv_sha256":sha256(raw).hexdigest(),
            **checked,
            "prematch_source_status":"PUBLIC_PUSH_VERIFIED_PARTIAL_HISTORIC_FT_ONLY",
        })
    return {
        "schema":SCHEMA,"source":"GH Archive hourly PushEvent + SHA-pinned old FPL 2023/24 CSV",
        "source_is_not_pitchapi":True,
        "proof_is_public_result_availability_not_complete_159_feature_pit":True,
        "verified_snapshots":len(verified),
        "records":verified,
        "original_PitchAPI_production_train_rows_certified":0,
        "official_M1_train_allowed":False,"gate14_pass":False,
        "xg_input_certified":False,
        "native_pitchapi_team_pair_joined":False,
        "test_rows_examined":0,"odds_used":False,"paid_sports_api_requests":0,
    }

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    dest=Path(p.parse_args().output)
    result=audit()
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        if json.loads(dest.read_text(encoding="utf8"))!=result:
            raise FPLSourceError("SIGNED_REPORT_CHANGED")
    else:
        with dest.open("x",encoding="utf8") as f:
            json.dump(result,f,sort_keys=True,ensure_ascii=False,indent=2);f.write("\n")
    print(json.dumps({"verified_snapshots":result["verified_snapshots"],
        "score_counts":[x["finished_ft_records_available_at_historical_source_publication"] for x in result["records"]],
        "gate14_pass":result["gate14_pass"]},sort_keys=True))
