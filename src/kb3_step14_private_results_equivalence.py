"""Step14 owner-local true old FT vs original native PitchAPI score equivalence.

This is a strict read-only research audit, executed with the owner's RSA
private key only in the local runner. Public source snapshots are SHA/push
pinned and all private values are transient. No target scores, private match
IDs, native team IDs, ratings, xG, source receipts or labels exported.
Public pre-match evidence DOES NOT prove original PitchAPI publication.
"""
from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
import csv,io,json,math

from src.kb3_features import EloParameters,elo_probability
from src.kb3_step14_multiseason_pit import SOURCES,utc,london,parse_openfootball
from src.kb3_step14_fpl_form5_lineage import _candidate,parse_fixture_rows
from src.kb3_step14_fpl_historic_clock_pilot import verify_raw_csv
from src.kb3_step14_native_team_crosswalk import canonical_team_name
from scripts.step14_multiseason_owner_native_join_local import (
    ADDITIONAL_2023,map_fpl_team_ids_by_finished_clock
)

SCHEMA="kb3-step14-private-original-native-old-public-score-equivalence-v1"
class NativeFTError(ValueError):pass

def integer_goal(x):
    if type(x) is int and 0<=x<=30:return x
    if type(x) is str and x and x.strip()==x:
        try:v=float(x)
        except ValueError as exc:raise NativeFTError("BAD_FT_SCORE") from exc
        if math.isfinite(v) and 0<=v<=30 and v.is_integer():
            return int(v)
    raise NativeFTError("BAD_FT_SCORE")

def collect_prior_native_ids(native,raws):
    """Build an allowlist only from scores present in the old public blobs.

    Never require, inspect or export an original TRAIN target label or
    any original VALIDATION label.
    """
    allowed=set()
    for source in (SOURCES[0],ADDITIONAL_2023):
        raw=raws[source["commit"]]
        pinned_raw(source,raw)
        verify_raw_csv(raw,expected_finished=source["ft"],push_time_utc=source["push"])
        rows=parse_fixture_rows(raw)
        mapping=map_fpl_team_ids_by_finished_clock(
            rows,native,season="2023-24",published_at=source["push"],
            expected_finished=source["ft"])
        idx=index_native(native,{},"2023-24")
        old=0
        for r in rows:
            if r["finished"]!="True":continue
            key=(mapping[r["team_h"]],mapping[r["team_a"]],r["kickoff_time"])
            item=idx.get(key)
            if item is None:raise NativeFTError("PUBLIC_FINISHED_NOT_IN_ORIGINAL_NATIVE")
            allowed.add(item[0]);old+=1
        if old!=source["ft"]:raise NativeFTError("PUBLIC_OLD_PRIOR_COUNT_CHANGED")
    source=SOURCES[1]
    raw=raws[source["commit"]]
    pinned_raw(source,raw)
    entries=parse_openfootball(raw,source)
    index={}
    for mid,n in native.items():
        if n["season"]!="2024-25":continue
        key=(canonical_team_name(n["home_name"]),canonical_team_name(n["away_name"]),n["kickoff_utc"])
        if key in index:raise NativeFTError("DUPLICATE_NATIVE_PAIR")
        index[key]=mid
    found=0
    for e in entries:
        if not e["ft_published"]:continue
        if e["kickoff"] is None:raise NativeFTError("OLD_PUBLIC_KICKOFF_MISSING")
        stamp=e["kickoff"].isoformat().replace("+00:00","Z")
        mid=index.get((e["home"],e["away"],stamp))
        if mid is None:raise NativeFTError("PUBLIC_EARLIER_FT_NOT_IN_NATIVE")
        allowed.add(mid);found+=1
    if found!=60:raise NativeFTError("OLD_PUBLIC_60_CHANGED")
    if not all(native[mid]["role"]=="TRAIN" for mid in allowed):
        raise NativeFTError("VALIDATION_LABEL_ALLOWLIST_FORBIDDEN")
    return allowed

def native_scores(receipts,native,allowlist):
    """Only read original labels for explicitly published historical PREDECESSORS.

    The other original matches, including all 380 VALIDATION, have their
    scores neither accessed nor serialized.
    """
    if not allowlist or not all(mid in native and native[mid]["role"]=="TRAIN" for mid in allowlist):
        raise NativeFTError("PREDECESSOR_ALLOWLIST_INVALID")
    expected={"2023/2024":"2023-24","2024/2025":"2024-25"}
    scores={}
    for long,short in expected.items():
        src=[r for r in receipts if r.get("resource")==
             f"pitchapi:history:premier-league:{long}:matches:played"]
        if len(src)!=1 or len(src[0].get("payload",{}).get("matches",[]))!=380:
            raise NativeFTError("ORIGINAL_SCORE_RECEIPT_INCOMPLETE")
        for row in src[0]["payload"]["matches"]:
            mid=row.get("id")
            if mid not in allowlist:
                continue
            n=native.get(mid)
            if n is None or n["season"]!=short or mid in scores:
                raise NativeFTError("PRIVATE_SCORE_NATIVE_ID_DISAGREES")
            if (row.get("time_utc")!=n["kickoff_utc"] or
                row.get("home_team",{}).get("id")!=n["home_id"] or
                row.get("away_team",{}).get("id")!=n["away_id"]):
                raise NativeFTError("PRIVATE_SCORE_IDENTITY_CHANGED")
            scores[mid]=(integer_goal(row.get("score_home")),
                         integer_goal(row.get("score_away")))
    if set(scores)!=set(allowlist):
        raise NativeFTError("PRIVATE_PREDECESSOR_SCORE_GRID_INCOMPLETE")
    return scores

def index_native(native,scores,season):
    ix={}
    for mid,n in native.items():
        if n["season"]!=season:continue
        key=(n["home_id"],n["away_id"],n["kickoff_utc"])
        if key in ix:raise NativeFTError("AMBIGUOUS_PRIVATE_MATCH_CLOCK")
        ix[key]=(mid,n,scores.get(mid))
    if len(ix)!=380:raise NativeFTError("PRIVATE_SEASON_NOT_380")
    return ix

def pinned_raw(source,raw):
    if (source not in (SOURCES[0],SOURCES[1],ADDITIONAL_2023) or
        sha256(raw).hexdigest()!=source["sha"]):
        raise NativeFTError("RAW_SHA_NOT_SOURCE_PINNED")

def replay_elo_batched(public_prior,params=None):
    """Pure replay with Step11's simultaneous-kickoff independent updates.

    public_prior: [(kickoff, public_id, private_home, private_away, gh,ga)]
    Returned ratings must NEVER be serialized in aggregate.
    """
    p=params or EloParameters()
    if (type(p) is not EloParameters or
        (p.initial,p.k,p.home_advantage,p.scale,p.season_retention)
           !=(1500.0,20.0,65.0,400.0,0.85)):
        raise NativeFTError("STEP11_ELO_PARAMS_NOT_ORIGINAL")
    seen=set()
    for when,pub,h,a,gh,ga in public_prior:
        if h==a or pub in seen or gh<0 or ga<0:
            raise NativeFTError("DUPLICATE_OR_INVALID_PUBLIC_PRIOR")
        seen.add(pub)
    rows=sorted(public_prior,key=lambda x:(x[0],x[1]))
    ratings=defaultdict(lambda:p.initial)
    i=0;matches=0
    while i<len(rows):
        j=i
        while j<len(rows) and rows[j][0]==rows[i][0]:j+=1
        involved=set();deltas=defaultdict(float)
        for _,_,home,away,gh,ga in rows[i:j]:
            if home in involved or away in involved:
                raise NativeFTError("SAME_TEAM_SIMULTANEOUS_KICKOFF")
            involved.update((home,away))
            ex=elo_probability(ratings[home],ratings[away],p)
            actual=1.0 if gh>ga else 0.0 if gh<ga else .5
            delta=p.k*(actual-ex)
            deltas[home]+=delta;deltas[away]-=delta
        for tid,delta in deltas.items():ratings[tid]+=delta
        matches+=j-i;i=j
    if matches!=len(public_prior):
        raise NativeFTError("ELO_REPLAY_DROPPED_A_MATCH")
    return ratings

def audit_fpl(source,raw,native,scores):
    pinned_raw(source,raw)
    verify_raw_csv(raw,expected_finished=source["ft"],push_time_utc=source["push"])
    rows=parse_fixture_rows(raw)
    mapping=map_fpl_team_ids_by_finished_clock(
        rows,native,season="2023-24",published_at=source["push"],
        expected_finished=source["ft"])
    index=index_native(native,scores,"2023-24")
    prior=[];different=0;matched=set()
    for row in rows:
        if row["finished"]!="True":continue
        key=(mapping[row["team_h"]],mapping[row["team_a"]],row["kickoff_time"])
        hit=index.get(key)
        if hit is None:raise NativeFTError("OLD_FPL_MATCH_NOT_IN_PRIVATE_NATIVE")
        mid,_,score=hit
        if score is None:raise NativeFTError("PRIOR_NATIVE_SCORE_NOT_IN_ALLOWLIST")
        if mid in matched:raise NativeFTError("PUBLIC_MATCH_REPEATED")
        matched.add(mid)
        pubscore=(integer_goal(row["team_h_score"]),integer_goal(row["team_a_score"]))
        different+=int(pubscore!=score)
        prior.append((utc(row["kickoff_time"]),row["id"],key[0],key[1],*pubscore))
    if len(prior)!=source["ft"]:raise NativeFTError("SOURCE_COMPLETED_COUNT_CHANGED")
    if different:
        # Never show which score differed, or derive any Elo from mismatch.
        return {"season":"2023-24","source_commit":source["commit"],
                "old_completed_FT":source["ft"],"exact_original_native_score_matches":len(prior)-different,
                "score_disagreements":different,"status":"BLOCKED_NATIVE_SCORE_DISAGREEMENTS",
                "source_form5_target_native_elo_evidence":0,
                "original_pitchapi_published_at_proven":False}
    ratings=replay_elo_batched(prior)
    cond=0;native_target_missing=0
    pubdone_ids=set(matched)
    for target in rows:
        if (target["finished"]!="False" or not target["kickoff_time"]
            or utc(target["kickoff_time"])<=utc(source["push"])):
            continue
        if _candidate(rows,target,utc(source["push"]))["state"]!="PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE":
            continue
        key=(mapping[target["team_h"]],mapping[target["team_a"]],target["kickoff_time"])
        hit=index.get(key)
        if hit is None:
            native_target_missing+=1
            continue
        # A target's within-season Elo must not be contaminated by a newly
        # completed target-team event not yet present in the old snapshot.
        _,n,_=hit
        for tid in (n["home_id"],n["away_id"]):
            source_prior=[r for r in prior if tid in (r[2],r[3])]
            native_prior=[(mid,z) for mid,z in native.items() if
                 z["season"]=="2023-24"
                 and tid in (z["home_id"],z["away_id"])
                 and utc(z["kickoff_utc"])<utc(n["kickoff_utc"])]
            if len(source_prior)!=len(native_prior) or any(mid not in pubdone_ids for mid,_ in native_prior):
                raise NativeFTError("TARGET_TEAM_HAS_UNPUBLISHED_PREDECESSOR")
            if tid not in ratings:raise NativeFTError("TARGET_TEAM_ELO_NOT_INITIALIZED")
        cond+=1
    return {"season":"2023-24","source_commit":source["commit"],
            "independent_publication_utc":source["push"],
            "old_completed_FT":source["ft"],
            "exact_original_native_score_matches":len(prior),
            "score_disagreements":0,
            "status":"PREVIOUS_FT_SCORES_EXACT_AND_LOCAL_ELO_MATH_REPLAY",
            "earlier_native_public_elo_updates_replayed":len(prior),
            "source_form5_target_native_elo_evidence":cond,
            "form5_targets_native_identity_missing":native_target_missing,
            "original_pitchapi_published_at_proven":False}

def index_native_public_names(native,scores,season):
    """Index all sealed fixture identities, but only allowlisted prior scores.

    Scores for future TRAIN targets and all VALIDATION rows are intentionally
    absent. Never request a score just to build the name-and-kickoff index.
    """
    index={}
    for mid,n in native.items():
        if n["season"]!=season:continue
        key=(canonical_team_name(n["home_name"]),
             canonical_team_name(n["away_name"]),n["kickoff_utc"])
        if key in index:raise NativeFTError("AMBIGUOUS_NATIVE_PUBLIC_NAMES")
        index[key]=scores.get(mid)  # Missing by design: no label read.
    if len(index)!=380:raise NativeFTError("NATIVE_SEASON_INDEX_INCOMPLETE")
    return index

def audit_of(source,raw,native,scores):
    pinned_raw(source,raw)
    entries=parse_openfootball(raw,source)
    rawmatches=json.loads(raw)["matches"]
    if len(entries)!=len(rawmatches):raise NativeFTError("OPENFOOTBALL_GRID_CHANGED")
    index=index_native_public_names(native,scores,"2024-25")
    checked=0;different=0
    for m,e in zip(rawmatches,entries):
        if not e["ft_published"]:continue
        if e["kickoff"] is None:raise NativeFTError("PUBLIC_COMPLETED_KICKOFF_MISSING")
        key=(e["home"],e["away"],e["kickoff"].isoformat().replace("+00:00","Z"))
        private=index.get(key)
        if key not in index:raise NativeFTError("PRIOR_PUBLIC_TEAM_CLOCK_NOT_IN_NATIVE")
        if private is None:raise NativeFTError("PUBLIC_PREDECESSOR_SCORE_NOT_IN_ALLOWLIST")
        pair=m["score"]["ft"]
        pubscore=(integer_goal(pair[0]),integer_goal(pair[1]))
        different+=int(private!=pubscore)
        checked+=1
    if checked!=60:raise NativeFTError("OPENFOOTBALL_60_CHANGED")
    return {"season":"2024-25","source_commit":source["commit"],
            "independent_publication_utc":source["push"],
            "old_completed_FT":60,
            "exact_original_native_score_matches":checked-different,
            "score_disagreements":different,
            "status":("PREVIOUS_FT_SCORES_EXACT" if different==0 else "BLOCKED_NATIVE_SCORE_DISAGREEMENTS"),
            "original_prior_season_2023_24_full_380_public_asof_proven":False,
            "full_multiseason_native_elo_chain_certified":False,
            "original_pitchapi_published_at_proven":False}

def audit(native,scores,raws):
    if len(native)!=1140 or not scores or not all(mid in native and native[mid]["role"]=="TRAIN" for mid in scores):
        raise NativeFTError("REQUIRES_ORIGINAL_AUTHENTICATED_PRIOR_ONLY")
    proof=[]
    for source in (SOURCES[0],ADDITIONAL_2023):
        proof.append(audit_fpl(source,raws[source["commit"]],native,scores))
    proof.append(audit_of(SOURCES[1],raws[SOURCES[1]["commit"]],native,scores))
    return {"schema":SCHEMA,"historical_pinned_public_sources_vs_RSA_PitchAPI":proof,
            "score_matches_sum_across_snapshots_includes_repeat_public_results":True,
            "source_target_pairs_not_unique_training_rows":True,
            "historical_xg_published_at_certified":False,
            "original_pitchapi_121_plus_38_pit_certified":False,
            "official_train_pit_certified":0,
            "official_validation_pit_certified":0,
            "test_examined":False,"outcome_values_or_native_ids_exported":False,
            "private_key_exported":False,"training_allowed":False,
            "gate14_pass":False}
