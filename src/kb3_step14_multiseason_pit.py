"""Step 14: independent three-season historic-public-asof audit (NO training).

Never infer publication from git author/committer time; use externally
corroborated GH Archive PushEvent and pinned immutable raw bytes.
Unverified old commits are inventoried only and CANNOT supply features.
No native archive, TEST, odds, paid API or target goals read/exported.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import argparse, csv, io, json

from src.kb3_step14_fpl_form5_lineage import build as fpl_build
from src.kb3_step14_native_team_crosswalk import REQUIRED, OFFICIAL_FIXTURE_AMENDMENT, canonical_team_name

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "kb3-step14-multiseason-public-pit-partial-v1"
FPL_REPO = "vaastav/Fantasy-Premier-League"
OF_REPO = "openfootball/football.json"
SOURCES = (
    dict(season="2023-24",provider="FPL",repo=FPL_REPO,
         commit="96fbc38ee6e36e3a7250081a787b65a1a27c944d",
         path="data/2023-24/fixtures.csv",
         sha="07b88250be0903a76b6334a7db56b9d9c148fc4a301c5e2338ce2c27dd01f367",
         push="2023-10-05T14:38:59Z",event="32344206544",ft=70),
    dict(season="2024-25",provider="OpenFootball",repo=OF_REPO,
         commit="5f777dc6e2cd02cdafd1520e81b7e338284fb7a7",
         path="2024-25/en.1.json",
         sha="6687e626fd7361ae771308920b289392229c36f6bdffee0b56b7e9235815e3de",
         push="2024-10-02T13:52:44Z",event="42475053178",ft=60),
    dict(season="2025-26",provider="OpenFootball",repo=OF_REPO,
         commit="fdca227e6fc8284865254f009e987ce7a70935a0",
         path="2025-26/en.1.json",
         sha="ba32190faf6aad0558d9e919344db6be6abe6e4ce733168b7efc40427771962b",
         push="2025-07-30T16:20:53Z",event="52743265113",ft=0),
)
# Historical content can be valid without historical publication proof.
# These NEVER contribute to any eligible or PIT count.
UNVERIFIED = (
    dict(season="2023-24",provider="FPL",repo=FPL_REPO,
         commit="be15e285f106d1becc6f24c0c470ec9ada8c935a",
         path="data/2023-24/fixtures.csv",expected_ft=10),
    dict(season="2023-24",provider="FPL",repo=FPL_REPO,
         commit="615da45c450fb13993b7e8da4c8388d7e2f57703",
         path="data/2023-24/fixtures.csv",expected_ft=90),
    dict(season="2024-25",provider="OpenFootball",repo=OF_REPO,
         commit="d0a780d5a22b34375f320a51e52e723814d59aff",
         path="2024-25/en.1.json",expected_ft=None),
    dict(season="2024-25",provider="OpenFootball",repo=OF_REPO,
         commit="831bb41621b99b7081f9942ff294fb3c91165448",
         path="2024-25/en.1.json",expected_ft=None),
)

class SourceAuditError(ValueError): pass

def utc(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise SourceAuditError("EXPLICIT_UTC_REQUIRED")
    try: result=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise SourceAuditError("INVALID_UTC") from exc
    if result.utcoffset().total_seconds()!=0:
        raise SourceAuditError("UTC_REQUIRED")
    return result.astimezone(timezone.utc)

def raw_url(s):
    return f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/{s['path']}"

def fetch(url,limit=3_000_001):
    with urlopen(Request(url,headers={"User-Agent":"KB3-step14-independent-asof-audit"}),timeout=40) as f:
        return f.read(limit)

def london(dt_day,clock):
    if not isinstance(dt_day,str) or not isinstance(clock,str):
        raise SourceAuditError("MISSING_SOURCE_CLOCK")
    try:
        local=datetime.fromisoformat(dt_day+"T"+clock).replace(tzinfo=ZoneInfo("Europe/London"))
        if local.strftime("%Y-%m-%dT%H:%M")!=dt_day+"T"+clock:
            raise SourceAuditError("UNSTABLE_UK_CLOCK")
        return local.astimezone(timezone.utc)
    except (ValueError,TypeError) as exc:
        raise SourceAuditError("BAD_SOURCE_CLOCK") from exc

def _score(m):
    obj=m.get("score")
    v=obj.get("ft") if isinstance(obj,dict) else None
    if v is None:return False
    if not (type(v) is list and len(v)==2 and all(type(z) is int and 0<=z<=30 for z in v)):
        raise SourceAuditError("INVALID_PUBLIC_FT")
    return True

def parse_openfootball(raw,source):
    if sha256(raw).hexdigest()!=source["sha"]:
        raise SourceAuditError("PINNED_RAW_SHA_CHANGED")
    document=json.loads(raw)
    rows=document.get("matches")
    if not isinstance(rows,list) or len(rows)!=380:
        raise SourceAuditError("SOURCE_GRID_NOT_380")
    push=utc(source["push"])
    counted=0
    seen=set()
    cleaned=[]
    for m in rows:
        if not isinstance(m,dict):
            raise SourceAuditError("INVALID_MATCH")
        pair=(canonical_team_name(m.get("team1")),canonical_team_name(m.get("team2")))
        if pair[0]==pair[1] or pair in seen:
            raise SourceAuditError("DUPLICATE_DIRECTIONAL_PAIR")
        seen.add(pair)
        kickoff=None
        if m.get("date") and m.get("time"):
            kickoff=london(m["date"],m["time"])
        exists=_score(m)
        if exists:
            # Source might contain same-day goals with uncertain game end time.
            # Only accept outcomes from earlier calendar days (strict).
            if kickoff is None or m["date"]>=source["push"][:10]:
                raise SourceAuditError("FUTURE_RESULT_IN_HISTORICAL_BLOB")
            counted+=1
        cleaned.append({"home":pair[0],"away":pair[1],
                        "day":m.get("date"),"kickoff":kickoff, "ft_published":exists})
    if counted!=source["ft"]:
        raise SourceAuditError("HISTORIC_FT_COUNT_CHANGED")
    return cleaned

def form5_openfootball(records,source,target):
    if target["ft_published"] or target["kickoff"] is None:
        return "TARGET_NOT_VERIFIABLY_UNPLAYED",None
    ko=target["kickoff"]
    if utc(source["push"])>=ko:
        return "SOURCE_NOT_BEFORE_TARGET",None
    ids={}
    for side,team in (("home",target["home"]),("away",target["away"])):
        matches=[r for r in records if team in (r["home"],r["away"]) and r is not target]
        # An undated TIME on a strictly *later calendar date* does not
        # invalidate a past-five reconstruction. Missing time on same/prior
        # dates does: such a fixture could have preceded this target.
        target_day=ko.astimezone(ZoneInfo("Europe/London")).date().isoformat()
        if any(r["kickoff"] is None and (not r.get("day") or r["day"]<=target_day)
               for r in matches):
            return "UNKNOWN_TEAM_SCHEDULE",None
        earlier=[r for r in matches if r["kickoff"] is not None and r["kickoff"]<ko]
        if any(not r["ft_published"] or r["kickoff"]>=utc(source["push"]) for r in earlier):
            return "INTERVENING_RESULT_NOT_IN_SNAPSHOT",None
        earlier.sort(key=lambda r:r["kickoff"],reverse=True)
        if len(earlier)<5:return "FEWER_THAN_FIVE_PREDECESSORS",None
        ids[side]=len(earlier[:5])
    return "PUBLIC_5_PRIOR_RESULTS_ONLY",ids

def per_openfootball(source,raw):
    records=parse_openfootball(raw,source)
    counts=Counter()
    count_candidate=0
    samples=[]
    for target in records:
        if target["ft_published"] or target["kickoff"] is None:
            continue
        if target["kickoff"]<=utc(source["push"]):
            continue
        state,proof=form5_openfootball(records,source,target)
        counts[state]+=1
        count_candidate+=1
        if state=="PUBLIC_5_PRIOR_RESULTS_ONLY":
            samples.append({"home":target["home"],"away":target["away"],
                            "kickoff_utc":target["kickoff"].isoformat().replace("+00:00","Z")})
    return {"season":source["season"],"source_repo":source["repo"],
            "verified_prematch_raw_sha256":source["sha"],
            "verified_source_commit":source["commit"],"push_utc":source["push"],
            "independent_push_event_id":source["event"],
            "finished_earlier_ft_in_blob":source["ft"],"old_unplayed_targets_evaluated":count_candidate,
            "states":dict(sorted(counts.items())),"public_form5_candidates":samples}

def strict_four_native_crosswalk(verified):
    """Only original four owner-local matched identities; no guess joins."""
    rows=[]
    for mid,item in REQUIRED.items():
        entry=verified[item["season"]]
        if item["season"]=="2025-26" and entry["finished_earlier_ft_in_blob"]!=0:
            raise SourceAuditError("PRESEASON_NO_PRIOR_FT_INVARIANT")
        old_name=(canonical_team_name(item["home"]),canonical_team_name(item["away"]))
        matches=[m for m in entry["public_form5_candidates"]
                 if (m["home"],m["away"])==old_name and m["kickoff_utc"]==item["kickoff_utc"]]
        is_amend=(mid==OFFICIAL_FIXTURE_AMENDMENT["fixture_id"])
        if len(matches)>1:raise SourceAuditError("AMBIGUOUS_EXACT_PUBLIC_CROSSWALK")
        rows.append({
            "known_original_native_fixture_id":mid,"season":item["season"],
            "original_partition":item["partition"],"original_native_pair_attested_owner_local":True,
            "archived_source_pair_time_exact_form5":bool(matches) and not is_amend,
            "old_public_schedule_revised_after_source_push":is_amend,
            "earlier_public_form5_proven":bool(matches) and not is_amend,
            "native_pitchapi_form5_values_equivalence_proven":False,
            "full_historical_pitchapi_pit_proven":False,
            "official_m1_training_allowed":False,
        })
    return rows

def verify_existing_clocks(root):
    clock=json.loads((root/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json").read_text(encoding="utf8"))
    fpl=json.loads((root/"data/audits/STEP14_FPL_2023_PREMATCH_PUBLIC_SNAPSHOT_PILOT_2026-10-27.json").read_text(encoding="utf8"))
    if clock.get("gate14_pass") is not False or fpl.get("gate14_pass") is not False:
        raise SourceAuditError("HISTORIC_CLOCK_ATTESTATION_CHANGED")
    for s in SOURCES:
        if s["provider"]=="FPL":
            matches=[x for x in fpl["records"] if x["historic_commit_sha"]==s["commit"]
                     and x["server_confirmed_public_push_utc"]==s["push"]
                     and str(x["server_event_id"])==s["event"]
                     and x["original_archived_csv_sha256"]==s["sha"]
                     and x["original_publication_timestamp_externally_corroborated"] is True]
        else:
            matches=[x for x in clock["records"] if
                     x["candidate_source_commit_sha"]==s["commit"]
                     and x["server_created_at_utc"]==s["push"]
                     and str(x["server_github_event_id"])==s["event"]
                     and x["independent_public_push_time_corroborated"] is True]
        if len(matches)!=1:raise SourceAuditError("INDEPENDENT_PUBLISHED_CLOCK_NOT_PINNED")

def audit(*,root=ROOT,fetcher=fetch):
    root=Path(root)
    verify_existing_clocks(root)
    reports={}
    for s in SOURCES:
        raw=fetcher(raw_url(s))
        if sha256(raw).hexdigest()!=s["sha"]:
            raise SourceAuditError("PINNED_PUBLIC_BLOB_CHANGED")
        if s["provider"]=="FPL":
            fpl_evidence=json.loads((root/"data/audits/STEP14_FPL_2023_PREMATCH_PUBLIC_SNAPSHOT_PILOT_2026-10-27.json").read_text(encoding="utf8"))
            x=fpl_build(raw,fpl_evidence)
            report={"season":s["season"],"source_repo":s["repo"],
                    "verified_prematch_raw_sha256":s["sha"],"verified_source_commit":s["commit"],
                    "push_utc":s["push"],"independent_push_event_id":s["event"],
                    "finished_earlier_ft_in_blob":70,
                    "old_unplayed_targets_evaluated":x["public_future_target_rows_evaluated"],
                    "states":x["counts"],
                    "public_form5_candidate_ids":[r["source_fixture_id"] for r in x["records"]
                         if r["state"]=="PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE"],
                    "public_form5_candidates":[]}
        else:
            report=per_openfootball(s,raw)
        reports[s["season"]]=report
    extra=[]
    # Unknown public clock MUST stay null, even if old SHA/raw content exists.
    for s in UNVERIFIED:
        row={"season":s["season"],"repo":s["repo"],"commit":s["commit"],
             "source_clock_verified":False,"independent_publication_utc":None,
             "may_supply_prematch_features":False,"status":"UNVERIFIED_ORIGINAL_PUBLICATION"}
        try:
            raw=fetcher(raw_url(s))
            row["raw_sha256_present_day_audit_only"]=sha256(raw).hexdigest()
            if s["provider"]=="FPL":
                import csv as _csv
                fixtures=list(_csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
                if len(fixtures)!=380:raise SourceAuditError("UNVERIFIED_GRID_CHANGED")
                row["finished_in_old_blob"]=sum(r.get("finished")=="True" for r in fixtures)
                if row["finished_in_old_blob"]!=s["expected_ft"]:
                    raise SourceAuditError("UNVERIFIED_CANDIDATE_CONTENT_CHANGED")
            else:
                document=json.loads(raw)
                if len(document.get("matches",[]))!=380:
                    raise SourceAuditError("UNVERIFIED_GRID_CHANGED")
                row["finished_in_old_blob"]=sum(_score(r) for r in document["matches"])
            row["status"]="OLD_CONTENT_RETRIEVED_CLOCK_UNVERIFIED"
        except (OSError,ValueError,KeyError,UnicodeError) as exc:
            row["status"]="SOURCE_UNAVAILABLE_OR_INVALID"
            row["error_class"]=type(exc).__name__
        extra.append(row)
    native=strict_four_native_crosswalk(reports)
    return {"schema":SCHEMA,"verified_three_season_public_sources":reports,
            "other_old_source_versions_not_pit":extra,
            "owner_local_four_fixture_source_join":native,
            "public_form5_input_candidates_by_season":{
                "2023-24":reports["2023-24"]["states"].get("PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE",0),
                "2024-25":reports["2024-25"]["states"].get("PUBLIC_5_PRIOR_RESULTS_ONLY",0),
                "2025-26":reports["2025-26"]["states"].get("PUBLIC_5_PRIOR_RESULTS_ONLY",0)},
            "public_source_does_not_equal_pitchapi_feature_values":True,
            "native_join_scope":"ONLY_FOUR_ALREADY_OWNER_AUTHENTICATED_NATIVE_FIXTURES",
            "full_prematch_elo_chain_proven_for_native_train":False,
            "historical_team_xg_proven":False,
            "official_original_train_pit_eligible":0,
            "official_original_validation_pit_eligible":0,
            "m1_fit_allowed":False,"gate14_pass":False,"test_examined":False,
            "no_results_goals_or_odds_exported":True,"paid_api_calls":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    a=p.parse_args()
    r=audit()
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    serialized=json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if out.exists():
        if out.read_text(encoding="utf8")!=serialized:
            raise SourceAuditError("APPEND_ONLY_REPORT_MISMATCH")
    else:
        out.write_text(serialized,encoding="utf8")
    print(json.dumps({"verified_three_season_public_sources":3,
            "source_form5_candidates_by_season":r["public_form5_input_candidates_by_season"],
            "known_native_partial_joins":sum(x["earlier_public_form5_proven"]
                                             for x in r["owner_local_four_fixture_source_join"]),
            "unverified_source_versions":len(r["other_old_source_versions_not_pit"]),
            "m1_fit_allowed":False,"gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
