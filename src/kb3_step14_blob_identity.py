"""Step14 A continuation: inspect actual historical blob content, not just commit dates.

Pull only 2023-24/2024-25 TRAIN and 2025-26 VALIDATION from CC0 source.
Match original PitchAPI opaque fixture IDs by *kickoff timestamp alone* at
most as hypotheses. Require a second independent identity source with
both provider team IDs to call a crosswalk verified. No odds/test source.
Git committer.date alone is NOT proof of public publication time.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from zoneinfo import ZoneInfo

from src.kb3_step14_archive_probe import (
    SEASONS, PILOT, _utc, validate_roster, commits_for_season,
    ArchiveProbeError,
)

ROOT=Path(__file__).resolve().parents[1]
SAFE="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
SCHEMA="kb3-step14-historical-blob-clock-crosswalk-audit-v1"


def _download_json(url, *, max_bytes=1_500_000, downloader=None):
    if downloader is None:
        def downloader(url):
            req=Request(url,headers={"User-Agent":"KB3-step14-public-historical-blob-audit"})
            with urlopen(req,timeout=20) as r:
                return r.read(max_bytes+1)
    raw=downloader(url)
    if not isinstance(raw,bytes) or not 10 < len(raw) <= max_bytes:
        raise ArchiveProbeError("PUBLIC_HISTORICAL_SOURCE_BYTES_INVALID")
    return json.loads(raw),sha256(raw).hexdigest()


def _public_kickoff(record):
    """OpenFootball en.1.json time uses England local clock; UTC conversion via DST."""
    if not isinstance(record,dict):
        raise ArchiveProbeError("PUBLIC_GAME_INVALID")
    day=record.get("date")
    time=record.get("time")
    if not isinstance(day,str) or not isinstance(time,str):
        return None
    try:
        d=datetime.strptime(day+" "+time,"%Y-%m-%d %H:%M")
        localized=d.replace(tzinfo=ZoneInfo("Europe/London"))
        return localized.astimezone(timezone.utc)
    except ValueError:
        return None


def _target_candidates(doc,*,kickoff):
    games=doc.get("matches")
    if type(games) is not list or len(games)!=380:
        raise ArchiveProbeError("HISTORICAL_BLOB_NOT_380_FIXTURES")
    matches=[]
    for g in games:
        if _public_kickoff(g)==kickoff:
            if type(g.get("team1")) is not str or type(g.get("team2")) is not str:
                raise ArchiveProbeError("NO_PUBLIC_TEAMS")
            score=g.get("score")
            ft=score.get("ft") if type(score) is dict else score
            has_final=(type(ft) is list and len(ft)==2 and all(type(v) is int for v in ft))
            matches.append({"home_name_openfootball":g["team1"],
                            "away_name_openfootball":g["team2"],
                            "score_present_in_prematch_candidate_blob":has_final})
    return matches


def inspect_pinned_blob_pilot(roster,safe,*,commits,fetch_blob,
                               independently_verified_publication=None,
                               official_pitch_team_id_pair=None):
    """Strictly evidence-conservative. Publication and native identity remain blocked.

    A trusted independent mapping, if added later, must itself prove home/away
    PitchAPI IDs and the matching OpenFootball teams; bare flags cannot grant
    entry to the production TRAIN. Do not accept an ad-hoc caller-supplied bool.
    """
    rows=validate_roster(roster,safe)
    if set(commits)!=set(SEASONS):
        raise ArchiveProbeError("BAD_COMMIT_CATALOG")
    cache={}
    output=[]
    for row in rows:
        ko=_utc(row["kickoff_utc"])
        cutoff=ko-timedelta(hours=48)
        applicable=[(d,sha) for d,sha in commits[row["season"]] if d<cutoff]
        if not applicable:
            output.append({"pitch_fixture_id":row["fixture_id"],"kickoff_utc":row["kickoff_utc"],
                           "partition":row["partition"],"season":row["season"],
                           "status":"NO_COMMIT_BEFORE_CUTOFF","public_file_sha256":None,
                           "candidate_commit_sha":None,"candidate_time_not_independent":None,
                           "match_by_exact_uk_local_to_utc_kickoff":[],
                           "independently_verified_first_publication":False,
                           "native_pitchapi_team_pair_verified":False,
                           "official_train_eligible":False})
            continue
        commit_dt,commit_sha=max(applicable)
        key=(row["season"],commit_sha)
        if key not in cache:
            blob,raw_sha=fetch_blob(row["season"],commit_sha)
            if not isinstance(blob,dict):
                raise ArchiveProbeError("HISTORICAL_BLOB_NOT_OBJECT")
            cache[key]=(blob,raw_sha)
        blob,raw_sha=cache[key]
        matches=_target_candidates(blob,kickoff=ko)
        if len(matches)==1 and matches[0]["score_present_in_prematch_candidate_blob"]:
            status="SUSPECT_SCORE_ALREADY_PRESENT_BEFORE_TARGET_KICKOFF"
        elif len(matches)==1:
            status="ONE_PUBLIC_SCHEDULE_MATCH_BY_KICKOFF_ONLY"
        elif len(matches)==0:
            status="NO_EXACT_SCHEDULE_MATCH_AT_COMMIT"
        else:
            status="AMBIGUOUS_SAME_KICKOFF_PUBLIC_FIXTURES"
        # Neither of these inputs can be flipped to true by a caller. A separate
        # signed, trusted cross-provider receipt must be added and reviewed.
        output.append({"pitch_fixture_id":row["fixture_id"],"kickoff_utc":row["kickoff_utc"],
                       "partition":row["partition"],"season":row["season"],
                       "candidate_commit_sha":commit_sha,
                       "candidate_commit_timestamp_utc_not_publication_proof":commit_dt.isoformat().replace("+00:00","Z"),
                       "public_file_sha256":raw_sha,"status":status,
                       "match_by_exact_uk_local_to_utc_kickoff":matches,
                       "independently_verified_first_publication":False,
                       "native_pitchapi_team_pair_verified":False,
                       "official_train_eligible":False})
    tally=Counter(x["status"] for x in output)
    by_season={s:dict(Counter(x["status"] for x in output if x["season"]==s)) for s in SEASONS}
    return {
        "schema":SCHEMA,
        "source":"openfootball/football.json",
        "historical_source_blob_unique_commits_downloaded":len(cache),
        "historical_source_blob_sha256_recorded":True,
        "sampled_train":40,"sampled_validation":20,"sampled_test":0,
        "public_candidate_commit_dates_inspected":sum(x["candidate_commit_sha"] is not None for x in output),
        "status_totals":dict(tally),"by_season":by_season,
        "public_blob_content_inspected":True,
        "git_committer_timestamp_proves_publication":False,
        "historical_publication_time_independently_verified":False,
        "official_pitchapi_native_team_pair_identity_verified":False,
        "official_pitchapi_training_records_certified":0,
        "test_match_result_labels_read":0,"paid_pitchapi_calls":0,
        "production_train_allowed":False,"gate14_pass":False,
        "records":output,
    }


def run(root=ROOT):
    root=Path(root)
    roster=json.loads((root/PILOT).read_text(encoding="utf8"))
    safe=json.loads((root/SAFE).read_text(encoding="utf8"))
    commit_index={s:commits_for_season(s) for s in SEASONS}
    def fetch(season,commit_sha):
        if season not in SEASONS or len(commit_sha)!=40 or any(ch not in "abcdef0123456789" for ch in commit_sha):
            raise ArchiveProbeError("COMMIT_REF_UNSAFE")
        url=f"https://raw.githubusercontent.com/openfootball/football.json/{commit_sha}/{season}/en.1.json"
        return _download_json(url)
    return inspect_pinned_blob_pilot(roster,safe,commits=commit_index,fetch_blob=fetch)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    record=run()
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(record,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:record[k] for k in (
      "historical_source_blob_unique_commits_downloaded","public_candidate_commit_dates_inspected",
      "status_totals","by_season","official_pitchapi_training_records_certified","gate14_pass"
    )},sort_keys=True))
