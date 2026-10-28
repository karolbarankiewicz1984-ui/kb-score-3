"""2024/25 independently public, in-season-only Elo input prefix (60 FT).

This public-only calculation follows the owner's real, separately observed
60/60 exact score equivalence against original PitchAPI. The 2023/24 FULL
380-game final team Elo ratings and original historic result publication
receipts remain unproven: DO NOT treat this 2024 reset-1500 replay as the
model's multi-season Elo feature, or TRAIN as PIT eligible.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from urllib.request import Request,urlopen
import argparse,json

from src.kb3_step14_multiseason_pit import (
    SOURCES,parse_openfootball,per_openfootball,verify_existing_clocks,
    _score,utc,form5_openfootball
)
from src.kb3_step14_private_results_equivalence import replay_elo_batched

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-2024-public-only-within-season-elo-prefix-v1"

class PublicEloError(ValueError):pass

def analyze(raw,source=None):
    source=source or SOURCES[1]
    if source!=SOURCES[1]:
        raise PublicEloError("UNVERIFIED_PUBLIC_SOURCE")
    if sha256(raw).hexdigest()!=source["sha"]:
        raise PublicEloError("OLD_PUBLIC_BLOB_HASH_CHANGED")
    records=parse_openfootball(raw,source)
    doc=json.loads(raw)
    if len(records)!=len(doc.get("matches",[])):
        raise PublicEloError("PUBLIC_RECORD_COUNT_CHANGED")
    old=[]
    for index,(rec,match) in enumerate(zip(records,doc["matches"])):
        if not rec["ft_published"]:
            # No target or future labels are read.
            continue
        if rec["kickoff"] is None or rec["kickoff"]>=utc(source["push"]):
            raise PublicEloError("NOT_EARLIER_THAN_PUBLICATION")
        goals=match["score"]["ft"]
        if not _score(match):
            raise PublicEloError("INVALID_PRIOR_FT")
        old.append((rec["kickoff"],str(index),rec["home"],rec["away"],goals[0],goals[1]))
    if len(old)!=60:
        raise PublicEloError("EXACTLY_60_PUBLIC_PREDECESSORS_REQUIRED")
    ratings=replay_elo_batched(old)
    candidates=per_openfootball(source,raw)["public_form5_candidates"]
    if len(candidates)!=10:
        raise PublicEloError("HISTORICAL_SOURCE_10_FORM5_TARGETS_CHANGED")
    indexed={(r["home"],r["away"],
        r["kickoff"].isoformat().replace("+00:00","Z") if r["kickoff"] else None):r
        for r in records}
    if len(indexed)!=380:raise PublicEloError("SOURCE_DUPLICATE_FIXTURE")
    for target in candidates:
        key=(target["home"],target["away"],target["kickoff_utc"])
        rec=indexed.get(key)
        if rec is None:
            raise PublicEloError("CANDIDATE_NOT_IN_AUTHENTIC_OLD_SOURCE")
        status,_=form5_openfootball(records,source,rec)
        if status!="PUBLIC_5_PRIOR_RESULTS_ONLY":
            raise PublicEloError("HISTORICAL_LAST_FIVE_NO_LONGER_COMPLETE")
        # Each team must have a deterministic finite, in-season rating.
        if not all(t in ratings and 0<ratings[t]<4000 for t in (rec["home"],rec["away"])):
            raise PublicEloError("CANDIDATE_INSEASON_ELO_CHAIN_INCOMPLETE")
    return {
        "schema":SCHEMA,
        "old_public_commit":source["commit"],
        "old_public_raw_sha256":source["sha"],
        "independently_archived_push_utc":source["push"],
        "independent_gh_archive_event_id":source["event"],
        "old_published_prior_FT_events_used_for_isolated_inseason_elo":len(old),
        "public_targets_with_source_level_complete_form5_and_isolated_inseason_elo":len(candidates),
        "source_comparison_with_original_pitchapi_FT_60_of_60_from_owner_screen":True,
        "source_comparison_screen_record":"data/audits/STEP14_OWNER_LOCAL_PRIOR_FT_270_OF_270_SCREEN_2026-10-28.json",
        "proof_is_2024_25_isolated_reset_1500_NOT_original_crossseason_elo":True,
        "original_2023_24_380_game_end_elo_asof_published":False,
        "original_2024_25_full_elo_feature_pit_certified":False,
        "original_pitchapi_team_xg_historical_pit_certified":False,
        "rated_team_ids_or_numeric_elo_values_exported":False,
        "match_outcomes_or_private_ids_exported":False,
        "original_train_rows_pit_certified":0,
        "original_validation_rows_pit_certified":0,
        "test_examined":False,
        "sports_api_paid_calls":0,
        "training_allowed":False,
        "gate14_pass":False,
    }

def run():
    verify_existing_clocks(ROOT)
    source=SOURCES[1]
    url=f"https://raw.githubusercontent.com/{source['repo']}/{source['commit']}/{source['path']}"
    with urlopen(Request(url,headers={"User-Agent":"KB3-Step14-2024-inseason-research"}),timeout=35) as f:
        raw=f.read(3_000_001)
    return analyze(raw)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    out=Path(parser.parse_args().output)
    report=run()
    out.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n"
    if out.exists():
        if out.read_text(encoding="utf8")!=payload:
            raise PublicEloError("AUDIT_OUTPUT_APPEND_ONLY_CONFLICT")
    else:
        out.write_text(payload,encoding="utf8")
    print(json.dumps({"2024_25_public_prior_elo_replay":60,
                      "public_2024_25_form5_targets_with_isolated_inseason_elo":report["public_targets_with_source_level_complete_form5_and_isolated_inseason_elo"],
                      "full_native_multiseason_elo_pit":False,
                      "train_pit_certified":0,"gate14_pass":False},sort_keys=True))

if __name__=="__main__":main()
