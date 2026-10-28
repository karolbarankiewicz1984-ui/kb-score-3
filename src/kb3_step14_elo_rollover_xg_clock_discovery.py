"""Step14 discover 2023/24 full-season public FT and independent xG clocks.

Research only; no original RSA, target results, odds, training, TEST, or
sports provider APIs. Git committer time is a SEARCH HINT only.
For Elo season rollover, source must be complete 380 FT AND independently
published before first 2024/25 PL kickoff 2024-08-16 19:00 UTC.
For xG, an authentic FPL player GW header does not establish team xG
equivalence to the original PitchAPI definition.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
import argparse,csv,io,json

from src.kb3_step14_fpl_historic_clock_pilot import gharchive_one_hour,verify_raw_csv
from src.kb3_step14_multiseason_pit import fetch,utc
from src.kb3_features import EloParameters,elo_probability

SCHEMA="kb3-step14-2023-full-elo-and-xg-independent-clock-search-v1"
REPO="vaastav/Fantasy-Premier-League"
ELO_CUTOFF="2024-08-16T19:00:00Z"
SEASON_END="2024-05-19T00:00:00Z"
SEARCHES=(
 {"kind":"ELO_FULL_FT","season":"2023-24","path":"data/2023-24/fixtures.csv",
  "after":"2024-05-19T00:00:00Z","until":"2024-08-15T23:59:59Z"},
 {"kind":"XG_FPL_PLAYER_GW38","season":"2023-24","path":"data/2023-24/gws/gw38.csv",
  "after":"2024-05-19T00:00:00Z","until":"2024-08-15T23:59:59Z"},
 {"kind":"XG_FPL_PLAYER_GW06","season":"2024-25","path":"data/2024-25/gws/gw6.csv",
  "after":"2024-09-28T00:00:00Z","until":"2024-10-31T23:59:59Z"},
 {"kind":"XG_FPL_PLAYER_GW06","season":"2025-26","path":"data/2025-26/gws/gw6.csv",
  "after":"2025-09-25T00:00:00Z","until":"2025-10-31T23:59:59Z"},
)
class DiscoveryError(ValueError):pass

def git_candidates(rows,option):
    """Return up to 2 boundary-old SHAs, not Git publication proofs."""
    if not isinstance(rows,list):
        raise DiscoveryError("COMMIT_API_NOT_A_LIST")
    eligible=[]
    for x in rows:
        if not isinstance(x,dict):continue
        sha=x.get("sha")
        date=((x.get("commit") or {}).get("committer") or {}).get("date")
        if not isinstance(sha,str) or len(sha)!=40 or not isinstance(date,str):
            continue
        try:dt=utc(date)
        except ValueError:continue
        if utc(option["after"])<=dt<=utc(option["until"]):
            eligible.append((dt,sha))
    if not eligible:return []
    eligible.sort(key=lambda x:(x[0],x[1]))
    selected=([eligible[0]] if len(eligible)==1 else [eligible[0],eligible[-1]])
    return [{"sha":sha,"git_committer_search_hint_only":
             date.isoformat().replace("+00:00","Z")}
             for date,sha in selected]

def matched_push(source_sha,commit_hint,clock_reader=gharchive_one_hour):
    """Only GH Archive independent PushEvent exact SHA is acceptable."""
    hour=utc(commit_hint).strftime("%Y-%m-%d-%H")
    event=clock_reader(hour)
    if event.get("status")!="READ_OK":
        return {"hour":hour,"gharchive_status":event.get("status","UNKNOWN"),
                "independent_source_publication_utc":None,
                "independent_push_event_id":None,
                "exact_sha_published_confirmed":False}
    candidates=[r for r in event.get("events",[])
        if (r.get("repository")==REPO and
            r.get("ref") in ("refs/heads/main","refs/heads/master") and
            source_sha in r.get("shas",[]) and r.get("event_id") and
            r.get("server_created_at_utc"))]
    if len(candidates)>1:raise DiscoveryError("DUPLICATE_PUBLIC_PUSH_CLOCK")
    if not candidates:
        return {"hour":hour,"gharchive_status":"READ_OK",
                "independent_source_publication_utc":None,
                "independent_push_event_id":None,
                "exact_sha_published_confirmed":False}
    candidate=candidates[0]
    dt=utc(candidate["server_created_at_utc"])
    if dt.strftime("%Y-%m-%d-%H")!=hour:
        raise DiscoveryError("GHARCHIVE_HOUR_TIME_CONFLICT")
    return {"hour":hour,"gharchive_status":"READ_OK",
            "independent_source_publication_utc":candidate["server_created_at_utc"],
            "independent_push_event_id":str(candidate["event_id"]),
            "exact_sha_published_confirmed":True}

def inspect_ft(raw,publication_utc):
    """Old FPL file is a full FT candidate only if all 380 already finished.

    Without independent publication clock, the exact source FT content can
    be inventoried, but may not enter an Elo as-of proof.
    """
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(rows)!=380 or len({r.get("id") for r in rows})!=380:
        raise DiscoveryError("FPL_FIXTURE_GRID_CHANGED")
    finished=[r for r in rows if r.get("finished")=="True"]
    result={"old_fpl_fixture_total":380,"old_completed_FT":len(finished),
            "all_380_ended":len(finished)==380}
    if publication_utc is None:
        result["full_380_FT_public_asof_2024_25_opening"]=False
        return result
    if utc(publication_utc)>=utc(ELO_CUTOFF):
        raise DiscoveryError("SOURCE_PUBLISHED_NOT_BEFORE_2024_OPENING")
    verify_raw_csv(raw,expected_finished=len(finished),push_time_utc=publication_utc)
    result["full_380_FT_public_asof_2024_25_opening"]=(len(finished)==380)
    return result

def inspect_xg(raw,publication_utc):
    """Never equate per-player FPL xG with original PitchAPI team-match xG."""
    # Bounded schema-only scan; do not leak athlete names or xG values.
    first=next(csv.reader(io.StringIO(raw[:20000].decode("utf-8-sig",errors="replace"))),[])
    fields=set(first)
    has="expected_goals" in fields
    return {
       "old_fpl_row_has_player_expected_goals_column":has,
       "old_csv_has_fixture_column":"fixture" in fields,
       "old_csv_has_team_column":"team" in fields,
       "data_scope":"FPL_PER_PLAYER_PER_GAMEWEEK_NOT_NATIVE_TEAM_MATCH",
       "source_old_publication_independently_verified":publication_utc is not None,
       "native_pitchapi_team_match_xg_values_equivalence_proven":False,
       "historical_native_pitchapi_xg_pit_eligible":False,
       "xg_values_or_player_rows_exported":False}

def scan(option,fetcher=fetch,clock_reader=gharchive_one_hour):
    out={"kind":option["kind"],"season":option["season"],
         "repo":REPO,"path":option["path"],
         "date_window_search_hint_only":[option["after"],option["until"]],
         "old_blob_publication_verified":False,
         "original_pitchapi_elo_or_xg_certified":False}
    url=(f"https://api.github.com/repos/{REPO}/commits?"
         +urlencode({"path":option["path"],"until":option["until"],"per_page":100}))
    try:
        candidates=git_candidates(json.loads(fetcher(url)),option)
    except (OSError,ValueError,KeyError,UnicodeError) as exc:
        out["state"]="GITHUB_DISCOVERY_UNAVAILABLE"
        out["failure_class"]=type(exc).__name__
        return out
    out["git_candidate_commit_count_selected"]=len(candidates)
    if not candidates:
        out["state"]="NO_HISTORICAL_FILE_COMMIT_IN_SEARCH_WINDOW"
        return out
    samples=[]
    for c in candidates:
        s={"source_git_sha":c["sha"],
           "git_committer_date_DISCOVERY_ONLY":c["git_committer_search_hint_only"]}
        try:
            raw=fetcher(f"https://raw.githubusercontent.com/{REPO}/{c['sha']}/{option['path']}")
            s["old_raw_sha256"]=sha256(raw).hexdigest()
            push=matched_push(c["sha"],c["git_committer_search_hint_only"],clock_reader)
            s.update(push)
            proven=push["independent_source_publication_utc"]
            if option["kind"]=="ELO_FULL_FT":
                s.update(inspect_ft(raw,proven))
                s["state"]=(
                    "FULL_380_FT_BEFORE_2024_OPENING_VERIFIED"
                    if s["full_380_FT_public_asof_2024_25_opening"]
                    else "RAW_FT_CONTENT_ONLY_OR_INCOMPLETE")
            else:
                s.update(inspect_xg(raw,proven))
                s["state"]=(
                    "HISTORICAL_FPL_PLAYER_XG_SCHEMATICALLY_DATED"
                    if proven and s["old_fpl_row_has_player_expected_goals_column"]
                    else "FPL_PLAYER_XG_PUBLICATION_OR_SCHEMA_UNPROVEN")
            s["training_allowed"]=False
        except (OSError,ValueError,KeyError,UnicodeError) as exc:
            s["state"]="OLD_BLOB_OR_EXTERNAL_CLOCK_UNAVAILABLE"
            s["failure_class"]=type(exc).__name__
            s["independent_source_publication_utc"]=None
            s["exact_sha_published_confirmed"]=False
        samples.append(s)
    out["source_candidates"]=samples
    out["old_blob_publication_verified"]=any(
       s.get("exact_sha_published_confirmed") is True for s in samples)
    out["state"]="CANDIDATES_CHECKED"
    return out

def audit(fetcher=fetch,clock_reader=gharchive_one_hour):
    sources=[scan(o,fetcher,clock_reader) for o in SEARCHES]
    full=[s for item in sources if item["kind"]=="ELO_FULL_FT"
          for s in item.get("source_candidates",[])
          if s.get("full_380_FT_public_asof_2024_25_opening") is True]
    xg=[s for item in sources if item["kind"].startswith("XG_")
        for s in item.get("source_candidates",[])
        if s.get("source_old_publication_independently_verified") is True
           and s.get("old_fpl_row_has_player_expected_goals_column") is True]
    return {"schema":SCHEMA,"historical_source_searches":sources,
            "fully_380_prematch_public_2023_24_blobs_verified_count":len(full),
            "2024_first_pl_kickoff_utc":ELO_CUTOFF,
            "full_380_ft_available_before_2024_opening":
                bool(full),
            "old_fpl_player_xg_sources_independently_clocked":len(xg),
            "player_xg_not_equivalent_to_native_pitchapi_team_xg":True,
            "full_2023_24_native_elo_final_ratings_proven":False,
            "2024_25_original_native_crossseason_elo_proven":False,
            "original_2023_2026_pitchapi_team_xg_pit_proven":False,
            "full_121_plus_38_features_pit_proven":False,
            "official_train_eligible":0,
            "official_validation_eligible":0,
            "original_2026_27_test_read":False,
            "sports_provider_paid_api_calls":0,
            "training_allowed":False,"gate14_pass":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    r=audit()
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(r,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    if dest.exists():
        if dest.read_text(encoding="utf8")!=raw:raise DiscoveryError("APPEND_ONLY_REPORT_CONFLICT")
    else:dest.write_text(raw,encoding="utf8")
    print(json.dumps({
        "full_380_old_ft_public_asof":r["full_380_ft_available_before_2024_opening"],
        "verified_old_fpl_player_xg_schemas":r["old_fpl_player_xg_sources_independently_clocked"],
        "source_scan_states":[x["state"] for x in r["historical_source_searches"]],
        "full_original_native_elo_or_xg_pit":False,
        "gate14_pass":False},sort_keys=True))

if __name__=="__main__": main()
