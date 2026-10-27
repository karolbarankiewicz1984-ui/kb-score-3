"""Step14 full-scope native identity and historical per-field PIT evidence audit.

Exactly 760 TRAIN and 380 VALIDATION from the previously sealed PitchAPI
source. No TEST access. No results/odds/xG read or exported; original match
dicts are only projected onto native fixture/team IDs/names, kickoff and
source receipt capture timestamps. External public source audit is optional
evidence ONLY and never promotes historical fixture identity into model PIT.
The original October 2026 receipt must NOT be backdated to 2023-2026.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import re

from src.kb3_pitch_native import MATCH_ID,TEAM_ID
from src.kb3_pitch_uefa_evidence import verify_receipts
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step14_native_team_crosswalk import (
    SAFE_SHA,ARCHIVE_ZIP_SHA,ARCHIVE_CHAIN_SHA, canonical_team_name,
    OFFICIAL_FIXTURE_AMENDMENT,
)
from src.kb3_split import sha

SEASONS={"2023/2024":("2023-24","TRAIN"),"2024/2025":("2024-25","TRAIN"),
         "2025/2026":("2025-26","VALIDATION")}
SCHEMA="kb3-step14-full-1140-native-identity-pit-audit-v1"
PUBLIC_BLOB_SCHEMA="kb3-step14-historical-blob-clock-crosswalk-audit-v1"
PUBLIC_CLOCK_SCHEMA="kb3-step14-thirdparty-public-push-clock-v1"

class FullNativeAuditError(ValueError):pass

def _utc(value):
    if not isinstance(value,str):
        raise FullNativeAuditError("INVALID_CLOCK")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise FullNativeAuditError("INVALID_CLOCK") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds()!=0:
        raise FullNativeAuditError("NOT_EXACT_UTC")
    return dt.astimezone(timezone.utc)

def _validate_safe(safe):
    if (not isinstance(safe,dict) or safe.get("schema")!="kb3-step12-methodology-v1" or
        safe.get("projection_sha256")!=SAFE_SHA or
        sha({k:v for k,v in safe.items() if k!="projection_sha256"})!=SAFE_SHA or
        safe.get("training_allowed") is not False or
        safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380}):
        raise FullNativeAuditError("FROZEN_SAFE_VIEW_NOT_VERIFIED")
    idx={}
    for item in safe["fixtures"]:
        # No reading of holdout ID, kickoff or other TEST fields.
        if item.get("partition")=="TEST":
            continue
        if set(item)!={"fixture_id","kickoff_utc","partition"}:
            raise FullNativeAuditError("MODEL_VIEW_HAS_TARGET_FIELDS")
        fid=item["fixture_id"]
        if fid in idx or not MATCH_ID.fullmatch(str(fid)):
            raise FullNativeAuditError("DUPLICATE_SAFE_ID")
        if item["partition"] not in ("TRAIN","VALIDATION"):
            raise FullNativeAuditError("UNKNOWN_ROLE")
        idx[fid]=(item["kickoff_utc"],item["partition"])
    if len(idx)!=1140 or sum(x[1]=="TRAIN" for x in idx.values())!=760:
        raise FullNativeAuditError("FROZEN_TRAIN_VALIDATION_COUNT_CHANGED")
    return idx

def _validate_native(receipts,idx,*,zip_sha,chain_sha):
    if zip_sha!=ARCHIVE_ZIP_SHA or chain_sha!=ARCHIVE_CHAIN_SHA:
        raise FullNativeAuditError("PINNED_ARCHIVE_HASH_CHANGED")
    wanted={"pitchapi:catalog"}|{
        f"pitchapi:history:premier-league:{season}:matches:played" for season in SEASONS}
    if not isinstance(receipts,list) or len(receipts)!=4 or {r.get("resource") for r in receipts}!=wanted:
        raise FullNativeAuditError("ORIGINAL_RECEIPTS_INCOMPLETE")
    proof=verify_receipts(receipts)
    if proof.get("final_chain_sha256")!=ARCHIVE_CHAIN_SHA:
        raise FullNativeAuditError("RECEIPT_CHAIN_CHANGED")
    native={}
    per_season=Counter()
    team_name_by_id={}
    team_ids_by_season={}
    club_pairs_by_season={}
    for full_season,(short,role) in SEASONS.items():
        receipt=next(r for r in receipts if r["resource"]==
                     f"pitchapi:history:premier-league:{full_season}:matches:played")
        observed=_utc(receipt.get("completed_at_utc"))
        matches=receipt.get("payload",{}).get("matches")
        if not isinstance(matches,list) or len(matches)!=380:
            raise FullNativeAuditError("SEALED_SOURCE_SEASON_INCOMPLETE")
        clubs=set()
        directional_pairs=set()
        for row in matches:
            if not isinstance(row,dict):
                raise FullNativeAuditError("MATCH_NOT_OBJECT")
            mid=row.get("id")
            if not isinstance(mid,str) or not MATCH_ID.fullmatch(mid) or mid in native:
                raise FullNativeAuditError("DUPLICATE_NATIVE_ID")
            expected=idx.get(mid)
            if expected is None:
                raise FullNativeAuditError("NATIVE_ID_NOT_IN_TRAIN_VALIDATION")
            if expected[1]!=role or expected[0]!=row.get("time_utc"):
                raise FullNativeAuditError("NATIVE_ROLE_OR_KICKOFF_DISAGREES_WITH_FROZEN_SPLIT")
            kickoff=_utc(row["time_utc"])
            if not kickoff<observed:
                raise FullNativeAuditError("RETROSPECTIVE_SOURCE_CLOCK_INCONSISTENT")
            home,away=row.get("home_team"),row.get("away_team")
            if not isinstance(home,dict) or not isinstance(away,dict):
                raise FullNativeAuditError("MISSING_NATIVE_TEAM_PAIR")
            for team in (home,away):
                tid,name=team.get("id"),team.get("name")
                if not isinstance(tid,str) or not TEAM_ID.fullmatch(tid):
                    raise FullNativeAuditError("INVALID_NATIVE_TEAM_ID")
                fixed=canonical_team_name(name)
                if tid in team_name_by_id and team_name_by_id[tid]!=fixed:
                    raise FullNativeAuditError("SAME_NATIVE_ID_DIFFERENT_TEAM_NAME")
                team_name_by_id[tid]=fixed
                clubs.add(tid)
            h,a=home["id"],away["id"]
            if h==a or (h,a) in directional_pairs:
                raise FullNativeAuditError("DUPLICATE_TEAM_FIXTURE_OR_SELF")
            directional_pairs.add((h,a))
            # Explicit allowlist. Never copy score_home, score_away, status,
            # xG, odds, or any outcome-dependent hash into native audit.
            native[mid]={"kickoff_utc":row["time_utc"],"season":short,
                         "role":role,"home_id":h,"away_id":a,
                         "home_name":home["name"],"away_name":away["name"],
                         "observed_at_utc":receipt["completed_at_utc"]}
            per_season[short]+=1
        if len(clubs)!=20 or len(directional_pairs)!=380:
            raise FullNativeAuditError("LEAGUE_TEAM_GRAPH_INCOMPLETE")
        team_ids_by_season[short]=clubs
        club_pairs_by_season[short]=directional_pairs
    if len(native)!=1140 or set(native)!=set(idx) or per_season!={
       "2023-24":380,"2024-25":380,"2025-26":380}:
        raise FullNativeAuditError("NATIVE_ALL_1140_MISMATCH")
    return native,per_season,team_ids_by_season

def _feature_family(key):
    if "xg" in key or "xga" in key:
        return "historical_xG_xGA"
    if "elo" in key:
        return "Elo_and_opponent_Elo"
    if any(x in key for x in ("points_avg","gf_avg","ga_avg","history")):
        return "previous_match_form_and_goals"
    return "fixture_and_history_completeness"

def _public_sample(native,blob,clock):
    if blob is None or clock is None:
        return {"status":"NOT_RUN_NO_PINNED_PUBLIC_SOURCES",
                "sample_count":0,"counts":{}, "independent_public_push_not_full_feature_PIT":True}
    if (blob.get("schema")!=PUBLIC_BLOB_SCHEMA or
        blob.get("gate14_pass") is not False or
        clock.get("schema")!=PUBLIC_CLOCK_SCHEMA or
        clock.get("gate14_pass") is not False):
        raise FullNativeAuditError("PUBLIC_SOURCE_AUDIT_SCHEMA_INVALID")
    rows=blob.get("records")
    if not isinstance(rows,list) or len(rows)!=60 or len({r["pitch_fixture_id"] for r in rows})!=60:
        raise FullNativeAuditError("PUBLIC_SAMPLE_NOT_FROZEN_60")
    valid_pushes={r["candidate_source_commit_sha"]:r for r in clock.get("records",[])
        if r.get("independent_public_push_time_corroborated") is True and
           r.get("public_branch_ref")=="refs/heads/master"}
    tally=Counter()
    for item in rows:
        fid=item["pitch_fixture_id"]
        n=native.get(fid)
        if n is None:
            raise FullNativeAuditError("PUBLIC_PILOT_NOT_IN_ORIGINAL_TRAIN_VALIDATION")
        if n["kickoff_utc"]!=item["kickoff_utc"] or n["season"]!=item["season"] or n["role"]!=item["partition"]:
            raise FullNativeAuditError("PUBLIC_PILOT_KICKOFF_CHANGED")
        matches=item.get("match_by_exact_uk_local_to_utc_kickoff",[])
        if not isinstance(matches,list):
            raise FullNativeAuditError("INVALID_ARCHIVE_CANDIDATE_SHAPE")
        matched=[m for m in matches if
             canonical_team_name(n["home_name"])==canonical_team_name(m["home_name_openfootball"]) and
             canonical_team_name(n["away_name"])==canonical_team_name(m["away_name_openfootball"]) and
             m.get("score_present_in_prematch_candidate_blob") is False]
        # Do NOT change original stale July blob. The official Sep3 fixture
        # amendment corroborates native identity, not July's preamendment fixture.
        if fid==OFFICIAL_FIXTURE_AMENDMENT["fixture_id"]:
            amend=OFFICIAL_FIXTURE_AMENDMENT
            if (canonical_team_name(n["home_name"])!=canonical_team_name(amend["home"]) or
                canonical_team_name(n["away_name"])!=canonical_team_name(amend["away"]) or
                n["kickoff_utc"]!=amend["kickoff_utc"]):
                raise FullNativeAuditError("OFFICIAL_AMENDMENT_DISAGREES_WITH_NATIVE")
            if matched:
                raise FullNativeAuditError("STALE_PUBLIC_BLOB_SILENTLY_CORRECTED")
            tally["IDENTITY_ONLY_OFFICIAL_RESCHEDULE_NOT_OLD_BLOB"]=1
            continue
        if not item.get("candidate_commit_sha"):
            tally["NO_PREMATCH_PUBLIC_COMMIT"]=tally["NO_PREMATCH_PUBLIC_COMMIT"]+1
        elif len(matched)>1:
            raise FullNativeAuditError("DUPLICATE_EXACT_HOME_AWAY_PUBLIC_SOURCE")
        elif len(matched)==1:
            commit=item["candidate_commit_sha"]
            event=valid_pushes.get(commit)
            if (event and event.get("server_created_at_utc") and
                _utc(event["server_created_at_utc"])<_utc(n["kickoff_utc"])):
                tally["MATCH_EXACT_TEAMS_AND_SERVER_PUSH_BEFORE_KICKOFF"]+=1
            else:
                tally["MATCH_EXACT_TEAMS_GIT_COMMIT_DATE_ONLY"]+=1
        else:
            tally["NO_NATIVE_PAIR_MATCH_IN_OLD_PUBLIC_BLOB"]+=1
    if sum(tally.values())!=60:
        raise FullNativeAuditError("SAMPLE_STATUSES_INCOMPLETE")
    return {"status":"CHECKED_NATIVE_PAIR_AGAINST_PUBLIC_60_HISTORICAL_CANDIDATES",
            "sample_count":60,"counts":dict(sorted(tally.items())),
            "independent_public_push_not_full_feature_PIT":True,
            "source_commit_dates_only_never_promoted":True,
            "historical_reschedule_not_backdated":True}

def audit_1140(*,safe,receipts,zip_sha=ARCHIVE_ZIP_SHA,
               chain_sha=ARCHIVE_CHAIN_SHA,blob=None,clock=None):
    idx=_validate_safe(safe)
    native,per_season,team_sets=_validate_native(receipts,idx,
        zip_sha=zip_sha,chain_sha=chain_sha)
    public=_public_sample(native,blob,clock)
    ftypes=Counter(_feature_family(key) for key in EXPECTED_FEATURES)
    flags=Counter(_feature_family(key) for key in EXPECTED_MISSING)
    role_counts=Counter(row["role"] for row in native.values())
    post_match=sum(_utc(n["observed_at_utc"])>_utc(n["kickoff_utc"]) for n in native.values())
    if post_match!=1140 or role_counts!={"TRAIN":760,"VALIDATION":380}:
        raise FullNativeAuditError("NOT_UNIFORMLY_RETROSPECTIVE_SOURCE")
    return {
        "schema":SCHEMA,
        "evidence_class":"OWNER_LOCAL_AUTHENTIC_PITCHAPI_SOURCE_AND_SEPARATE_PUBLIC_AUDIT",
        "source_archive_zip_sha256":ARCHIVE_ZIP_SHA,
        "source_chain_sha256":ARCHIVE_CHAIN_SHA,
        "source_safe_projection_sha256":SAFE_SHA,
        "native_identity_fixture_ids_checked":len(native),
        "identity_checked_season_counts":dict(sorted(per_season.items())),
        "identity_checked_partition_counts":dict(sorted(role_counts.items())),
        "native_season_team_counts":{season:len(teams) for season,teams in sorted(team_sets.items())},
        "native_team_id_name_conflicts":0,
        "native_fixture_id_kickoff_role_mismatches":0,
        "native_home_away_duplicate_matches":0,
        "native_identity_within_pitchapi_sealed_source_verified":1140,
        "external_archive_crosswalk_sample":public,
        "original_retrospective_source_observed_after_target_kickoff":post_match,
        "actual_historical_first_publication_for_full_features_proven":0,
        "feature_contract_numeric_nullable_field_count":len(EXPECTED_FEATURES),
        "feature_contract_missing_flag_count":len(EXPECTED_MISSING),
        "feature_contract_total_lineage_proofs_expected":len(EXPECTED_FEATURES)+len(EXPECTED_MISSING),
        "field_family_counts":dict(sorted(ftypes.items())),
        "missing_flag_family_counts":dict(sorted(flags.items())),
        "prematch_proven_by_original_pitchapi_receipts_by_family":{
            k:{"certified_train":0,"certified_validation":0,
                "train_missing_asof_proof":760,"validation_missing_asof_proof":380,
                "original_source_status":"OBSERVED_2026_AFTER_HISTORIC_KICKOFF"}
            for k in sorted(ftypes)},
        "prematch_provider_result_history_asof_proven_rows":0,
        "prematch_provider_elo_asof_proven_rows":0,
        "prematch_provider_form_asof_proven_rows":0,
        "prematch_provider_xg_asof_proven_rows":0,
        "public_schedules_not_substitute_for_all_121_features":True,
        "real_training_prematch_proven_rows":0,
        "real_validation_prematch_proven_rows":0,
        "test_matches_inspected":0,"test_labels_read":0,
        "match_results_or_odds_exported":False,
        "native_fixture_ids_or_native_team_ids_exported":False,
        "private_rsa_key_exported":False,
        "sports_api_requests":0,
        "production_model_fitted":False,
        "training_allowed":False,
        "gate14_pass":False,
    }
