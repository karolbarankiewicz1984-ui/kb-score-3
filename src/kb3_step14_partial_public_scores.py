"""True *partial* historical source availability backed by GH Archive PushEvent.

Only completed predecessor score data from two archived OpenFootball blobs.
No target result consumed, no TEST and no original PitchAPI M1 gate release.
The 2025 July blob is prior to the season: it has zero completed results.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request,urlopen
import json

from src.kb3_split import sha
from src.kb3_step14_native_team_crosswalk import REQUIRED,OFFICIAL_FIXTURE_AMENDMENT
from src.kb3_step14_full_identity_pit_audit import _utc

ROOT=Path(__file__).resolve().parents[1]
BLOB=ROOT/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json"
CLOCK=ROOT/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json"
PUBLIC_2024=("2024-25","5f777dc6e2cd02cdafd1520e81b7e338284fb7a7",
            "6687e626fd7361ae771308920b289392229c36f6bdffee0b56b7e9235815e3de")
PUBLIC_2025=("2025-26","fdca227e6fc8284865254f009e987ce7a70935a0",
            "ba32190faf6aad0558d9e919344db6be6abe6e4ce733168b7efc40427771962b")
SOURCE_URL="https://raw.githubusercontent.com/openfootball/football.json/{sha}/{season}/en.1.json"

class PartialEvidenceError(ValueError):pass

def _scores_before_push(doc,push):
    results=[]
    for row in doc.get("matches",[]):
        if type(row) is not dict:raise PartialEvidenceError("BAD_MATCH_RECORD")
        ft=row.get("score",{}).get("ft") if type(row.get("score")) is dict else None
        if type(ft) is not list or len(ft)!=2 or not all(type(v) is int and 0<=v<=30 for v in ft):
            continue
        # Commit was pushed at a known time; a final score in that public blob
        # proves its availability no later than that push. Require game
        # calendar date strictly earlier than the push day; no same-day.
        if type(row.get("date")) is not str or row["date"]>=push[:10]:
            raise PartialEvidenceError("RESULT_DATE_AT_OR_AFTER_INDEPENDENT_PUSH")
        results.append((row["team1"],row["team2"],row["date"]))
    return results

def analyse(docs,blobs,clock):
    if len(blobs.get("records",[]))!=60 or clock.get("gate14_pass") is not False:
        raise PartialEvidenceError("ORIGINAL_ARCHIVE_REPORT_NOT_PINNED")
    look={r["pitch_fixture_id"]:r for r in blobs["records"]}
    pushes={r["candidate_source_commit_sha"]:r for r in clock["records"]
            if r.get("independent_public_push_time_corroborated") is True and
               r.get("public_branch_ref")=="refs/heads/master"}
    source_map={"2024-25":PUBLIC_2024,"2025-26":PUBLIC_2025}
    past_by_season={}
    count_by_season={}
    for season,(_,commit,_) in source_map.items():
        e=pushes.get(commit)
        if e is None or not e.get("server_created_at_utc"):
            raise PartialEvidenceError("GH_ARCHIVE_PUSH_PROOF_MISSING")
        doc=docs[season]
        if type(doc) is not dict or type(doc.get("matches")) is not list or len(doc["matches"])!=380:
            raise PartialEvidenceError("PUBLIC_RAW_SEASON_INVALID")
        prior=_scores_before_push(doc,e["server_created_at_utc"])
        past_by_season[season]=prior
        count_by_season[season]=len(prior)
    outcomes=[]
    for ident in ("m_3AMymS","m_4AseJ9","m_0lzfjT","m_0JJdwI"):
        req=REQUIRED[ident]
        if ident==OFFICIAL_FIXTURE_AMENDMENT["fixture_id"]:
            outcomes.append({
                "fixture_id":ident,
                "public_july_source_contains_actual_native_pair":False,
                "state":"WRONG_JULY_FIXTURE_SAME_KICKOFF_REVISED_IN_SEPTEMBER",
                "no_target_score_examined":True,
                "prematch_native_PitchAPI_form5_certified":False,
                "official_m1_training_allowed":False,
            })
            continue
        season=req["season"]; doc=docs[season]
        old=look.get(ident)
        if old is None or old["candidate_commit_sha"]!=req["commit"]:
            raise PartialEvidenceError("TARGET_HISTORIC_COMMIT_CHANGED")
        target=[g for g in doc["matches"] if
                g.get("team1")==req["home"] and g.get("team2")==req["away"]]
        if len(target)!=1 or (type(target[0].get("score")) is dict and
                               target[0]["score"].get("ft") is not None):
            raise PartialEvidenceError("TARGET_SCORE_ALREADY_IN_ARCHIVED_BLOB")
        proof=pushes[req["commit"]]
        if _utc(proof["server_created_at_utc"])>=_utc(req["kickoff_utc"]):
            raise PartialEvidenceError("PUSH_NOT_BEFORE_TARGET")
        prior=past_by_season[season]
        home_count=sum(req["home"] in (h,a) for h,a,_ in prior)
        away_count=sum(req["away"] in (h,a) for h,a,_ in prior)
        outcomes.append({
            "fixture_id":ident,"season":season,
            "public_july_source_contains_actual_native_pair":True,
            "independent_GH_push_before_kickoff":True,
            "public_push_time_utc":proof["server_created_at_utc"],
            "public_source_sha":req["commit"],
            "completed_predecessor_results_for_home_in_pushed_blob":home_count,
            "completed_predecessor_results_for_away_in_pushed_blob":away_count,
            "public_within_season_last5_goal_form_inputs_reconstructable":
                home_count>=5 and away_count>=5,
            "historic_result_values_exported":False,
            "prematch_native_PitchAPI_form5_certified":False,
            "official_m1_training_allowed":False,
        })
    return {
        "schema":"kb3-step14-historical-partial-public-score-evidence-v1",
        "source":"exact OpenFootball raw historical Git SHA + GH Archive independent public PushEvent",
        "historical_public_push_2024_10_02_fully_finished_results":count_by_season["2024-25"],
        "historical_public_push_2025_07_30_fully_finished_results":count_by_season["2025-26"],
        "public_availability_of_some_prior_ft_results_proven":True,
        "full_original_pitchapi_feature_vector_pit_certified":False,
        "source_is_same_as_pitchapi_original":False,
        "target_match_scores_exported_or_used":False,
        "no_test_result_read":True,
        "official_M1_train_eligible":0,"gate14_pass":False,
        "records":outcomes,
    }

def run(root=ROOT,fetcher=None):
    root=Path(root)
    if fetcher is None:
        def fetcher(url):
            req=Request(url,headers={"User-Agent":"KB3-step14-asof-public-score-audit"})
            with urlopen(req,timeout=25) as r:
                return r.read(2_000_001)
    docs={}
    for season,commit,expected_hash in (PUBLIC_2024,PUBLIC_2025):
        raw=fetcher(SOURCE_URL.format(season=season,sha=commit))
        if type(raw) is not bytes or sha256(raw).hexdigest()!=expected_hash:
            raise PartialEvidenceError("ARCHIVED_BLOB_SHA_CHANGED")
        docs[season]=json.loads(raw)
    blob=json.loads((root/"data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json").read_text())
    clock=json.loads((root/"data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json").read_text())
    result=analyse(docs,blob,clock)
    result["report_sha256"]=sha(result)
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    arg=p.parse_args()
    result=run()
    dest=Path(arg.output);dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        if json.loads(dest.read_text())!=result:
            raise PartialEvidenceError("REPORT_CHANGED_APPEND_ONLY")
    else:
        dest.write_text(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in (
        "historical_public_push_2024_10_02_fully_finished_results",
        "historical_public_push_2025_07_30_fully_finished_results",
        "full_original_pitchapi_feature_vector_pit_certified","gate14_pass")},sort_keys=True))
