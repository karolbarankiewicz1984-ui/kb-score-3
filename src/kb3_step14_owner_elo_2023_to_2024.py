"""Owner-local proof of original native Elo 2023/24 -> 2024/25 rollover.

All 2023/24 FT in one independently-public May-2024 snapshot precede the
first 2024/25 kickoff. 2024/25 preceding FT also independently archived.
Original targets/validation/test labels are NEVER read: 380 2023 and 60
2024 labels are PREDECESSORS for Oct-2024 targets, not target outcomes.
Only aggregate lineage proof leaves memory, no native IDs, goals, ratings.
This DOES NOT certify PitchAPI's original provider publication timestamps,
xG, all 121+38 model features, M1 training, or earlier 2023 target PIT.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import csv,io,json,math

from src.kb3_features import EloParameters,elo_probability
from src.kb3_step14_multiseason_pit import SOURCES,utc,parse_openfootball,per_openfootball
from src.kb3_step14_fpl_historic_clock_pilot import verify_raw_csv
from src.kb3_step14_fpl_form5_lineage import parse_fixture_rows
from src.kb3_step14_native_team_crosswalk import canonical_team_name
from src.kb3_step14_private_results_equivalence import (
    NativeFTError,integer_goal,index_native,index_native_public_names,
    native_scores,replay_elo_batched
)
from scripts.step14_multiseason_owner_native_join_local import (
    map_fpl_team_ids_by_finished_clock
)

FULL_2023={
    "repo":"vaastav/Fantasy-Premier-League",
    "path":"data/2023-24/fixtures.csv",
    "commit":"204c134d8e90e2b6e69ec252aa3ef6f10f21e73c",
    "sha":"d8521bdbb80edb5141bc17df71bf6026275f2e56fd6a6dc6041b3ae23a39ce6a",
    "push":"2024-05-27T18:05:12Z",
    "event_id":"38750359648",
    "ft":380,
}
SCHEMA="kb3-step14-owner-native-380-plus-60-asof-elo-rollover-research-v1"
class RolloverError(ValueError):pass

def check_pinned_public_evidence(full_report):
    evidence=full_report.get("full_season_EPL_2023_24",{})
    if (full_report.get("schema")!="kb3-step14-full-public-2023-24-elo-cutoff-and-fpl-player-xg-v1"
        or full_report.get("GATE14")!="PENDING"
        or evidence.get("commit")!=FULL_2023["commit"]
        or evidence.get("raw_sha256")!=FULL_2023["sha"]
        or evidence.get("event_server_UTC")!=FULL_2023["push"]
        or str(evidence.get("independent_GHArchive_event_id"))!=FULL_2023["event_id"]
        or evidence.get("old_380_fixtures_finished")!=380
        or evidence.get("publication_before_2024_25_opening") is not True):
        raise RolloverError("FROZEN_PUBLICATION_PROOF_NOT_VERIFIED")
    if utc(FULL_2023["push"])>=utc("2024-08-16T19:00:00Z"):
        raise RolloverError("FULL_RESULTS_NOT_PUBLISHED_BEFORE_NEW_SEASON")

def public_complete_2023_rows(raw):
    if sha256(raw).hexdigest()!=FULL_2023["sha"]:
        raise RolloverError("FULL_2023_PUBLIC_RAW_SHA_CHANGED")
    verify_raw_csv(raw,expected_finished=380,push_time_utc=FULL_2023["push"])
    rows=parse_fixture_rows(raw)
    if len(rows)!=380 or any(r["finished"]!="True" for r in rows):
        raise RolloverError("FULL_2023_380_PUBLIC_FT_NOT_PRESENT")
    return rows

def allowlist_only_before_2024_targets(native,old_2023,old_2024):
    rows=public_complete_2023_rows(old_2023)
    team_map=map_fpl_team_ids_by_finished_clock(
        rows,native,season="2023-24",published_at=FULL_2023["push"],expected_finished=380)
    old_2024_src=SOURCES[1]
    if sha256(old_2024).hexdigest()!=old_2024_src["sha"]:
        raise RolloverError("PUBLIC_2024_SHA_CHANGED")
    records=parse_openfootball(old_2024,old_2024_src)
    index_23=index_native(native,{},"2023-24")
    allow=set()
    for r in rows:
        key=(team_map[r["team_h"]],team_map[r["team_a"]],r["kickoff_time"])
        match=index_23.get(key)
        if match is None:raise RolloverError("2023_PUBLIC_MATCH_NOT_NATIVE_EXACT")
        allow.add(match[0])
    if len(allow)!=380:
        raise RolloverError("FULL_380_PRIVATE_2023_SOURCE_NOT_BIJECTIVE")
    ix24={}
    for mid,n in native.items():
        if n["season"]!="2024-25":continue
        k=(canonical_team_name(n["home_name"]),canonical_team_name(n["away_name"]),n["kickoff_utc"])
        if k in ix24:raise RolloverError("DUPLICATE_NATIVE_2024_FIXTURE")
        ix24[k]=mid
    if len(ix24)!=380:raise RolloverError("NATIVE_2024_NOT_380")
    earlier=0
    for r in records:
        if not r["ft_published"]:continue
        if r["kickoff"] is None:raise RolloverError("OLD_2024_SCORE_NO_CLOCK")
        key=(r["home"],r["away"],r["kickoff"].isoformat().replace("+00:00","Z"))
        mid=ix24.get(key)
        if mid is None:raise RolloverError("2024_PUBLIC_PRIOR_NOT_NATIVE_EXACT")
        allow.add(mid);earlier+=1
    if earlier!=60 or len(allow)!=440:
        raise RolloverError("PRIVATE_PREDECESSOR_ALLOWLIST_380_PLUS_60_CHANGED")
    if not all(native[mid]["role"]=="TRAIN" for mid in allow):
        raise RolloverError("NEVER_WHITELIST_VALIDATION_OR_TEST")
    return allow,team_map,records

def crossseason_replay_and_compare(native,raw_2023,raw_2024,scores,team_map,public_2024):
    rows=public_complete_2023_rows(raw_2023)
    idx23=index_native(native,scores,"2023-24")
    prior23=[]
    for r in rows:
        key=(team_map[r["team_h"]],team_map[r["team_a"]],r["kickoff_time"])
        match=idx23.get(key)
        if match is None or match[2] is None:
            raise RolloverError("MISSING_2023_PINNED_FT_NATIVE")
        pubscore=(integer_goal(r["team_h_score"]),integer_goal(r["team_a_score"]))
        if match[2]!=pubscore:raise RolloverError("2023_ORIGINAL_VS_PUBLIC_SCORE_MISMATCH")
        prior23.append((utc(r["kickoff_time"]),r["id"],key[0],key[1],*pubscore))
    if len(prior23)!=380:raise RolloverError("FULL_2023_HISTORY_NOT_380")
    elo23=replay_elo_batched(prior23)
    native23={tid for n in native.values() if n["season"]=="2023-24"
              for tid in (n["home_id"],n["away_id"])}
    native24={tid for n in native.values() if n["season"]=="2024-25"
              for tid in (n["home_id"],n["away_id"])}
    if len(native23)!=20 or len(native24)!=20 or set(elo23)!=native23:
        raise RolloverError("NATIVE_TEAM_ID_GRAPH_NOT_STABLE")
    stable=native23 & native24
    if len(stable)!=17:
        raise RolloverError("EXPECTED_17_STABLE_NATIVE_TEAM_IDS")
    p=EloParameters()
    ratings={tid:(p.initial+(elo23[tid]-p.initial)*p.season_retention
                  if tid in stable else p.initial) for tid in native24}
    if len(ratings)!=20:raise RolloverError("NO_FULL_2024_START_RATINGS")
    idx24=index_native_public_names(native,scores,"2024-25")
    idx24_id={}
    for mid,n in native.items():
        if n["season"]=="2024-25":
            ix=(canonical_team_name(n["home_name"]),canonical_team_name(n["away_name"]),n["kickoff_utc"])
            idx24_id[ix]=(mid,n)
    old=json.loads(raw_2024)["matches"]
    updates=[];completed=set()
    for rec,m in zip(public_2024,old):
        if not rec["ft_published"]:continue
        stamp=rec["kickoff"].isoformat().replace("+00:00","Z")
        key=(rec["home"],rec["away"],stamp)
        pair=idx24_id.get(key)
        if pair is None:raise RolloverError("OLD_2024_PUBLIC_SCORE_NOT_NATIVE")
        mid,n=pair
        if mid in completed:raise RolloverError("DUPLICATE_2024_MATCH")
        completed.add(mid)
        private=idx24.get(key)
        pub=(integer_goal(m["score"]["ft"][0]),integer_goal(m["score"]["ft"][1]))
        if private is None or private!=pub:
            raise RolloverError("2024_ORIGINAL_VS_PUBLIC_SCORE_MISMATCH")
        updates.append((utc(stamp),mid,n["home_id"],n["away_id"],*pub))
    if len(updates)!=60:raise RolloverError("PRIOR_2024_NOT_60")
    updates.sort(key=lambda x:(x[0],x[1]))
    i=0
    while i<len(updates):
        j=i
        while j<len(updates) and updates[j][0]==updates[i][0]:j+=1
        participants=set();deltas={}
        for _,_,h,a,gh,ga in updates[i:j]:
            if h in participants or a in participants:
                raise RolloverError("DUPLICATE_SIMULTANEOUS_TEAM")
            participants.update((h,a))
            expected=elo_probability(ratings[h],ratings[a],p)
            actual=1.0 if gh>ga else 0 if gh<ga else 0.5
            delta=p.k*(actual-expected)
            deltas[h]=deltas.get(h,0)+delta
            deltas[a]=deltas.get(a,0)-delta
        for tid,delta in deltas.items():ratings[tid]+=delta
        i=j
    ten=per_openfootball(SOURCES[1],raw_2024)["public_form5_candidates"]
    if len(ten)!=10:raise RolloverError("2024_TARGET_10_NOT_IN_OLD_SOURCE")
    passed=0;blocked=Counter()
    for t in ten:
        key=(t["home"],t["away"],t["kickoff_utc"])
        hit=idx24_id.get(key)
        if hit is None:
            blocked["TARGET_NOT_EXACT_ORIGINAL_NATIVE_PAIR"]+=1;continue
        _,n=hit
        cutoff=utc(SOURCES[1]["push"])
        target=utc(t["kickoff_utc"])
        if not cutoff<target:
            raise RolloverError("SOURCE_NOT_BEFORE_2024_TARGET")
        relevant={n["home_id"],n["away_id"]}
        native_prior={mid for mid,z in native.items()
            if z["season"]=="2024-25" and
            (z["home_id"] in relevant or z["away_id"] in relevant)
            and utc(z["kickoff_utc"])<target}
        if not native_prior.issubset(completed):
            blocked["PREVIOUS_2024_MATCH_NOT_IN_60_PREMATCH_SNAPSHOT"]+=1
            continue
        if not relevant.issubset(ratings):
            raise RolloverError("2024_NATIVE_RATING_MISSING")
        passed+=1
    return {
       "2023_full_380_prior_FT_RSA_PitchAPI_exact":380,
       "2024_publicly_prior_60_FT_RSA_PitchAPI_exact":60,
       "2023_end_public_elo_replay_count":380,
       "2024_start_stable_native_team_ids":17,
       "2024_promoted_native_team_ids_started_at_1500":3,
       "2024_elo_rollover_decay":0.85,
       "2024_prior_elo_updates_replayed":60,
       "2024_pinned_public_form5_target_pairs":10,
       "2024_exact_native_target_pairs_with_crossseason_elo_proof":passed,
       "2024_target_elo_blocker_categories":dict(blocked),
       "rating_values_or_source_scores_or_private_ids_exported":False}

def audit(native,receipts,old_2023,old_2024,public_evidence):
    if len(native)!=1140:
        raise RolloverError("OWNER_RSA_NATIVE_1140_REQUIRED")
    check_pinned_public_evidence(public_evidence)
    allow,team_map,old_24_records=allowlist_only_before_2024_targets(
        native,old_2023,old_2024)
    prior_scores=native_scores(receipts,native,allow)
    result=crossseason_replay_and_compare(
        native,old_2023,old_2024,prior_scores,team_map,old_24_records)
    return {"schema":SCHEMA,**result,
        "only_original_RSA_2023_prior_380_and_2024_prior_60_outcomes_read":True,
        "original_2023_target_prematch_PIT_proven":False,
        "original_2024_native_PitchAPI_published_at_proven":False,
        "native_2024_crossseason_Elo_math_with_independent_public_clock_verified":result[
            "2024_exact_native_target_pairs_with_crossseason_elo_proof"]==10,
        "historical_original_team_xg_PIT_proven":False,
        "original_121_plus_38_feature_PIT_proven":False,
        "train_eligible":0,"validation_eligible":0,
        "test_examined":False,"original_model_or_split_changed":False,
        "training_allowed":False,"gate14_pass":False}
