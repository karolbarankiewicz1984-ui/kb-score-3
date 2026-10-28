"""Search old 2024-25 / 2025-26 xG publication with independent event clocks.

No Git commit timestamp is proof. Research-only discovery of exact original
FPL fixture and player match blobs. Older publisher snapshots may be absent.
No API-football/PitchAPI calls, no private RSA, TEST, odds or training.
"""
from __future__ import annotations
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
import argparse,csv,io,json

from src.kb3_step14_fpl_historic_clock_pilot import gharchive_one_hour
from src.kb3_step14_multiseason_pit import fetch,utc
from src.kb3_step14_xg_four_gates import extract_public_xg,XGFourGateError

REPO="vaastav/Fantasy-Premier-League"
SCHEMA="kb3-step14-2024-2025-fpl-xg-old-independent-push-discovery-v1"
WINDOWS=(
 {"season":"2024-25","name":"PRE_OCT05_PLAYER_GW","path":"data/2024-25/gws/gw6.csv",
  "since":"2024-09-28T00:00:00Z","until":"2024-10-04T20:00:00Z",
  "target_kickoff_after":"2024-10-05T11:00:00Z"},
 {"season":"2024-25","name":"PRE_OCT05_MERGED_XG","path":"data/2024-25/gws/merged_gw.csv",
  "since":"2024-09-28T00:00:00Z","until":"2024-10-04T20:00:00Z",
  "target_kickoff_after":"2024-10-05T11:00:00Z"},
 {"season":"2025-26","name":"EARLY_2025_PLAYER_GW","path":"data/2025-26/gws/gw6.csv",
  "since":"2025-09-27T00:00:00Z","until":"2025-10-10T23:59:00Z",
  "target_kickoff_after":"2025-10-11T12:00:00Z"},
)
class SourceClockError(ValueError):pass

def independent_exact_push(sha,committer_hint,archive_reader=gharchive_one_hour):
    stamp=utc(committer_hint)
    hour=stamp.strftime("%Y-%m-%d-%H")
    archive=archive_reader(hour)
    if archive.get("status")!="READ_OK":
        return {"status":"GHARCHIVE_HOUR_UNAVAILABLE",
                "confirmed":False,"server_publication_utc":None,
                "event_id":None,"archive_hour":hour}
    hits=[x for x in archive.get("events",[])
       if x.get("repository")==REPO and
       x.get("ref") in ("refs/heads/master","refs/heads/main") and
       sha in x.get("shas",[]) and x.get("event_id") and
       x.get("server_created_at_utc") and
       utc(x["server_created_at_utc"]).strftime("%Y-%m-%d-%H")==hour]
    if len(hits)>1:raise SourceClockError("AMBIGUOUS_PUBLIC_PUSH_EVENTS")
    if not hits:
        return {"status":"NO_EXACT_INDEPENDENT_SHA_PUSH_IN_ARCHIVE_HOUR",
                "confirmed":False,"server_publication_utc":None,
                "event_id":None,"archive_hour":hour}
    return {"status":"EXACT_SHA_PUBLIC_PUSH_CONFIRMED","confirmed":True,
            "server_publication_utc":hits[0]["server_created_at_utc"],
            "event_id":str(hits[0]["event_id"]),
            "archive_hour":hour}

def select_window_commits(data,window):
    if not isinstance(data,list):raise SourceClockError("INVALID_COMMITS_METADATA")
    selected=[]
    for item in data:
        sha=item.get("sha")
        dt=((item.get("commit") or {}).get("committer") or {}).get("date")
        if not isinstance(sha,str) or len(sha)!=40 or not isinstance(dt,str):continue
        try:stamp=utc(dt)
        except (ValueError,TypeError):continue
        if utc(window["since"])<=stamp<=utc(window["until"]):
            selected.append((stamp,sha))
    selected.sort(key=lambda r:(r[0],r[1]),reverse=True)
    # Two latest source revisions per window, to avoid unbounded archive traffic.
    return [{"commit":sha,"GIT_DATE_DISCOVERY_HINT_NOT_PUBLICATION":dt.isoformat().replace("+00:00","Z")}
             for dt,sha in selected[:2]]

def scan_one(window,fetcher=fetch,archive_reader=gharchive_one_hour):
    out={"season":window["season"],"probe_name":window["name"],
         "searched_path":window["path"],"before_target_min_utc":window["target_kickoff_after"],
         "snapshots":[],"pitchapi_original_team_xg_pit_proven":False}
    url=f"https://api.github.com/repos/{REPO}/commits?"+urlencode({
        "path":window["path"],"until":window["until"],"per_page":100})
    try:
        selection=select_window_commits(json.loads(fetcher(url)),window)
    except Exception as exc:
        out["status"]="GITHUB_SOURCE_DISCOVERY_UNAVAILABLE"
        out["error_type"]=type(exc).__name__
        return out
    if not selection:
        out["status"]="NO_OLD_FILE_COMMIT_IN_WINDOW"
        return out
    for candidate in selection:
        s=dict(candidate);s["status"]="UNVERIFIED";s["historical_publication_proven"]=False
        try:
            clock=independent_exact_push(
                candidate["commit"],candidate["GIT_DATE_DISCOVERY_HINT_NOT_PUBLICATION"],
                archive_reader)
            s["clock"]=clock
            if not clock["confirmed"]:
                s["status"]="OLD_COMMIT_EXISTED_BUT_NO_INDEPENDENT_PUB_CLOCK"
                out["snapshots"].append(s);continue
            pub=utc(clock["server_publication_utc"])
            if pub>=utc(window["target_kickoff_after"]):
                s["status"]="PUSH_AFTER_TEST_TARGET_CUTOFF"
                out["snapshots"].append(s);continue
            base=f"https://raw.githubusercontent.com/{REPO}/{candidate['commit']}/"
            fpl_fixture=fetcher(base+f"data/{window['season']}/fixtures.csv",limit=3_000_001)
            old_xg=fetcher(base+window["path"],limit=40_000_001)
            if len(old_xg)>=40_000_001:raise SourceClockError("SOURCE_OVER_40MB")
            s["fixtures_raw_sha256"]=sha256(fpl_fixture).hexdigest()
            s["player_xg_raw_sha256"]=sha256(old_xg).hexdigest()
            # No post-source target stats are valid even if visible in Git.
            xg=extract_public_xg(fpl_fixture,old_xg,
                published_at=clock["server_publication_utc"],
                pinned_fixture_sha=s["fixtures_raw_sha256"],
                pinned_player_sha=s["player_xg_raw_sha256"],
                require_full_grid=True)
            s["completed_public_fixtures"]=xg["finished_fixtures"]
            s["fixture_pairs_with_both_player_sides"]=xg["fixtures_with_both_sides_player_xg"]
            s["public_player_rows"]=xg["player_rows"]
            s["original_team_xg_semantics_equivalent"]=False
            s["status"]="OLD_PUBLIC_PLAYER_XG_EXACT_SIDE_ASOF_SOURCE_VERIFIED"
            s["historical_publication_proven"]=True
        except Exception as exc:
            s["status"]="SOURCE_CLOCK_OR_EXACT_XG_SIDE_FAIL_CLOSED"
            s["error_type"]=type(exc).__name__
        out["snapshots"].append(s)
    out["status"]="PUBLIC_SOURCE_WINDOW_SCANNED"
    return out

def run():
    reports=[scan_one(w) for w in WINDOWS]
    return {"schema":SCHEMA,"reports":reports,
        "candidate_xg_sources_with_verified_sha_push_and_fixture_side":sum(
            s["status"]=="OLD_PUBLIC_PLAYER_XG_EXACT_SIDE_ASOF_SOURCE_VERIFIED"
            for r in reports for s in r["snapshots"]),
        "provider_timestamp_not_git_commit_time":True,
        "native_original_PitchAPI_provider_team_xg_definition_matched":False,
        "original_121_plus_38_pit_eligible":0,
        "original_train_pit_eligible":0,
        "original_validation_pit_eligible":0,
        "training_allowed":False,"gate14_pass":False,
        "no_original_RSA_or_TEST":True,"paid_sports_provider_api_calls":0}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    dest=Path(p.parse_args().output);r=run()
    dest.parent.mkdir(parents=True,exist_ok=True)
    value=json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if dest.exists():
        if dest.read_text(encoding="utf8")!=value:raise SourceClockError("REPORT_IMMUTABLE")
    else:dest.write_text(value,encoding="utf8")
    print(json.dumps({
        "candidate_historical_xg_sources":r["candidate_xg_sources_with_verified_sha_push_and_fixture_side"],
        "windows":[{"name":x["probe_name"],"status":x["status"],
                    "sources":[{"status":z["status"],
                                "published_utc":z.get("clock",{}).get("server_publication_utc"),
                                "old_completed_fixtures":z.get("completed_public_fixtures")}
                        for z in x["snapshots"]]} for x in r["reports"]],
        "original_PitchAPI_team_xg_PIT":False,"gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
