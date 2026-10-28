"""Discover *additional* 2023/24, 2024/25, 2025/26 historic blobs.

GitHub commit dates are discovery hints, NEVER independent public clocks.
GH Archive matching exact PushEvent is mandatory; missing archive -> NO PIT.
No private PitchAPI, target scores, TEST, odds, training, or paid API.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
import argparse,csv,io,json

from src.kb3_step14_multiseason_pit import fetch,utc,per_openfootball,_score
from src.kb3_step14_fpl_form5_lineage import _candidate,parse_fixture_rows
from src.kb3_step14_fpl_historic_clock_pilot import gharchive_one_hour
from src.kb3_step14_gharchive_clock import read_hour

SCHEMA="kb3-step14-three-additional-historical-snapshots-discovery-v1"
CANDIDATES=(
 {"season":"2023-24","repo":"vaastav/Fantasy-Premier-League",
  "file":"data/2023-24/fixtures.csv",
  "after":"2023-11-01T00:00:00Z","until":"2023-12-05T23:59:59Z","type":"FPL"},
 {"season":"2024-25","repo":"openfootball/football.json",
  "file":"2024-25/en.1.json",
  "after":"2024-12-01T00:00:00Z","until":"2025-01-01T23:59:59Z","type":"OF"},
 {"season":"2025-26","repo":"openfootball/football.json",
  "file":"2025-26/en.1.json",
  "after":"2025-10-01T00:00:00Z","until":"2025-10-31T23:59:59Z","type":"OF"},
 {"season":"2024-25","repo":"vaastav/Fantasy-Premier-League",
  "file":"data/2024-25/fixtures.csv",
  "after":"2024-11-01T00:00:00Z","until":"2024-12-05T23:59:59Z","type":"FPL"},
 {"season":"2025-26","repo":"openfootball/football.json",
  "file":"2025-26/en.1.json",
  "after":"2026-01-01T00:00:00Z","until":"2026-02-01T23:59:59Z","type":"OF"},
)

class DiscoveryError(ValueError): pass

def pinned_selection(options,commits):
    """Only path-specific commit metadata, deterministic latest candidate in window."""
    chosen=[]
    for item in commits:
        sha=item.get("sha")
        dt=((item.get("commit") or {}).get("committer") or {}).get("date")
        if (not isinstance(sha,str) or len(sha)!=40
            or not isinstance(dt,str) or not dt.endswith("Z")):
            continue
        if utc(options["after"])<=utc(dt)<=utc(options["until"]):
            chosen.append((utc(dt),sha))
    if not chosen:return None
    chosen.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return {"commit_sha":chosen[0][1],
            "git_committer_date_DISCOVERY_ONLY":chosen[0][0].isoformat().replace("+00:00","Z")}

def probe_public_push(repo,sha,commit_hint,reader):
    """Never use git timestamps as publication evidence; hour is lookup hint."""
    hour=utc(commit_hint).strftime("%Y-%m-%d-%H")
    result=reader(hour)
    if repo.startswith("vaastav/"):
        events=result.get("events",[]) if result.get("status")=="READ_OK" else []
        filtered=[e for e in events
                  if e.get("repository")==repo
                  and e.get("ref") in ("refs/heads/master","refs/heads/main")
                  and sha in e.get("shas",[])]
    else:
        events=result.get("push_events_found",[]) if result.get("status")=="READ_OK" else []
        filtered=[e for e in events
                  if e.get("event_repo_name")==repo
                  and e.get("push_ref") in ("refs/heads/master","refs/heads/main")
                  and sha in e.get("included_commit_shas",[])]
    if len(filtered)!=1:
        return {"archive_hour":hour,"archive_read_status":result.get("status"),
                "independent_clock_verified":False,"published_at_utc":None,
                "independent_event_id":None}
    event=filtered[0]
    when=event.get("server_created_at_utc") if repo.startswith("vaastav/") else event.get("created_at_utc")
    event_id=event.get("event_id")
    try:stamp=utc(when)
    except (ValueError,TypeError,AttributeError) as exc:raise DiscoveryError("BAD_EXTERNAL_CLOCK") from exc
    if stamp.strftime("%Y-%m-%d-%H")!=hour or not event_id:
        raise DiscoveryError("GH_ARCHIVE_MISMATCH_OR_NOT_SERVER_TIME")
    return {"archive_hour":hour,"archive_read_status":"READ_OK",
            "independent_clock_verified":True,
            "published_at_utc":when,"independent_event_id":str(event_id)}

def audit_candidate(option,*,fetcher=fetch,fpl_reader=gharchive_one_hour,of_reader=read_hour):
    query=urlencode({"path":option["file"],"until":option["until"],"per_page":"100"})
    api=f"https://api.github.com/repos/{option['repo']}/commits?{query}"
    result={"season":option["season"],"public_repo":option["repo"],"path":option["file"],
            "search_window_start_NOT_PIT":option["after"],
            "search_window_end_NOT_PIT":option["until"],
            "trained_or_approved":False,"original_pitchapi_pit_certified":False}
    try:
        candidates=json.loads(fetcher(api))
        if not isinstance(candidates,list):raise DiscoveryError("GITHUB_COMMIT_API_INVALID")
        selected=pinned_selection(option,candidates)
        if selected is None:
            result["state"]="NO_COMMIT_IN_WINDOW";return result
        result.update(selected)
        raw=fetcher(f"https://raw.githubusercontent.com/{option['repo']}/{selected['commit_sha']}/{option['file']}")
        result["old_raw_sha256"]=sha256(raw).hexdigest()
        if option["type"]=="FPL":
            rows=parse_fixture_rows(raw)
            source_finished=sum(r["finished"]=="True" for r in rows)
        else:
            payload=json.loads(raw)
            if not isinstance(payload.get("matches"),list) or len(payload["matches"])!=380:
                raise DiscoveryError("GRID_NOT_380")
            source_finished=sum(_score(m) for m in payload["matches"])
        result["source_finished_score_records_in_old_blob"]=source_finished
        result["old_fixture_grid_size"]=380
        # Not a PIT proof unless archive independently corroborates this SHA.
        attested=probe_public_push(option["repo"],selected["commit_sha"],
                                  selected["git_committer_date_DISCOVERY_ONLY"],
                                  fpl_reader if option["type"]=="FPL" else of_reader)
        result.update(attested)
        if not attested["independent_clock_verified"]:
            result["state"]="RAW_HISTORIC_CONTENT_ONLY_PUBLIC_CLOCK_UNPROVEN"
            result["public_form5_prematch_certified_count"]=0
            return result
        stamp=utc(attested["published_at_utc"])
        if option["type"]=="FPL":
            known=0
            for row in rows:
                if row["finished"]=="True":
                    if not row["kickoff_time"] or utc(row["kickoff_time"]).date()>=stamp.date():
                        raise DiscoveryError("FUTURE_OR_SAME_DAY_FINISHED_SCORE")
                    known+=1
                elif row["team_h_score"] or row["team_a_score"]:
                    raise DiscoveryError("FUTURE_FPL_SCORE")
            valid=sum(1 for row in rows if row["finished"]=="False" and row["kickoff_time"] and
                      utc(row["kickoff_time"])>stamp and
                      _candidate(rows,row,stamp).get("state")=="PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE")
        else:
            source={"sha":sha256(raw).hexdigest(),"push":attested["published_at_utc"],
                    "ft":source_finished,"season":option["season"],
                    "repo":option["repo"],"commit":selected["commit_sha"],
                    "event":attested["independent_event_id"]}
            output=per_openfootball(source,raw)
            valid=output["states"].get("PUBLIC_5_PRIOR_RESULTS_ONLY",0)
        result["state"]="NEW_INDEPENDENT_PUSH_TIME_VERIFIED_PARTIAL_PUBLIC_FT"
        result["public_form5_prematch_certified_count"]=valid
        result["native_id_join_completed"]=False
        result["source_score_values_exported"]=False
        return result
    except Exception as exc:
        # Network and malformed archive do not confer PIT: classify, do not guess.
        result["state"]="UNAVAILABLE_OR_INVALID_FAIL_CLOSED"
        result["independent_clock_verified"]=False
        result["published_at_utc"]=None
        result["public_form5_prematch_certified_count"]=0
        result["error_type"]=type(exc).__name__
        return result

def run():
    records=[audit_candidate(a) for a in CANDIDATES]
    return {"schema":SCHEMA,"candidate_windows_scanned":len(records),
            "records":records,
            "new_source_snapshots_with_independent_clock":sum(r.get("independent_clock_verified") is True for r in records),
            "never_use_git_commit_timestamp_as_pubtime":True,
            "public_content_and_clock_not_equivalent_to_pitchapi_team_xg":True,
            "official_train_rows_pit_certified":0,
            "official_validation_rows_pit_certified":0,
            "gate14_pass":False,"training_allowed":False,
            "no_test_read":True,"paid_sports_api_calls":0}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",required=True)
    output=Path(a.parse_args().output)
    r=run()
    output.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(r,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if output.exists():
        if output.read_text(encoding="utf8")!=encoded:raise DiscoveryError("APPEND_ONLY_HISTORIC_AUDIT")
    else:output.write_text(encoded,encoding="utf8")
    print(json.dumps({"additional_blobs_scanned":len(r["records"]),
                      "independent_push_verified":r["new_source_snapshots_with_independent_clock"],
                      "states":[{"season":x["season"],"repo":x["public_repo"],"state":x["state"]} for x in r["records"]],
                      "public_additional_5match_candidates":[{"season":x["season"],"repo":x["public_repo"],"count":x.get("public_form5_prematch_certified_count",0)} for x in r["records"]],
                      "gate14_pass":False,"training_allowed":False},sort_keys=True))
if __name__=="__main__":main()
