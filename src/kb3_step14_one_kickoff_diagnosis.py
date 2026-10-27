"""Explain ONE owner-local native-vs-public Premier League kickoff disagreement.

- NEVER outputs native fixture IDs, team IDs, original match records or scores.
- Does NOT edit the source, infer which clock is correct or approve PIT TRAIN.
- The source is independently pinned by existing 1140 source validator.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

from src.kb3_step14_full_identity_pit_audit import (
    _independent_public_1140,_utc,FullNativeAuditError,
)
from src.kb3_step14_native_team_crosswalk import canonical_team_name


def diagnose_one(native,reference):
    """Require validated native map with exactly 1140 real or synthetic matches.

    Caller must first verify encrypted original archive receipts + source chain
    using _validate_native; this helper only reads allowlisted names and times.
    """
    if not isinstance(native,dict) or len(native)!=1140:
        raise FullNativeAuditError("NATIVE_SOURCE_NOT_FULL_1140")
    validated=_independent_public_1140(native,reference)
    counts=validated["counts"]
    if (validated["checked"]!=1140 or
        counts.get("EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF",0)!=1139 or
        counts.get("SAME_PUBLIC_TEAM_PAIR_DIFFERENT_UTC_KICKOFF",0)!=1 or
        sum(counts.values())!=1140):
        raise FullNativeAuditError("EXPECTED_ONE_KICKOFF_DISAGREEMENT_NOT_FOUND")
    public={}
    for season,data in reference["source_seasons"].items():
        for m in data["fixtures_target_free"]:
            key=(season,canonical_team_name(m["home_name"]),canonical_team_name(m["away_name"]))
            if key in public:
                raise FullNativeAuditError("DUPLICATE_PUBLIC_TEAM_PAIR")
            # Full pinned original public validation performed above.
            local=datetime.fromisoformat(m["date"]+"T"+m["time_london"])
            utc=local.replace(tzinfo=ZoneInfo("Europe/London")).astimezone(timezone.utc)
            public[key]={"utc":utc,"home":m["home_name"],"away":m["away_name"]}
    disagreements=[]
    for n in native.values():
        key=(n["season"],canonical_team_name(n["home_name"]),canonical_team_name(n["away_name"]))
        item=public.get(key)
        if item is None:raise FullNativeAuditError("PAIR_DIFFERENCE_NOT_KICKOFF")
        observed=_utc(n["kickoff_utc"])
        if observed==item["utc"]:
            continue
        diff=(observed-item["utc"]).total_seconds()/60
        if not diff.is_integer():
            raise FullNativeAuditError("NON_MINUTE_KICKOFF_DIFFERENCE")
        disagreements.append({
            "season":n["season"],"partition":n["role"],
            "home_name":n["home_name"],"away_name":n["away_name"],
            "pitchapi_kickoff_utc":observed.isoformat().replace("+00:00","Z"),
            "openfootball_kickoff_utc":item["utc"].isoformat().replace("+00:00","Z"),
            "openfootball_local_time_london":item["utc"].astimezone(
                 ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M %Z"),
            "difference_pitchapi_minus_public_minutes":int(diff),
        })
    if len(disagreements)!=1:
        raise FullNativeAuditError("ONE_DIFFERENCE_EXPECTED")
    return {
       "schema":"kb3-step14-one-owner-local-kickoff-discrepancy-v1",
       "scope":"owner_local_authenticated_pitchapi_vs_frozen_oct2026_public_schedule",
       "original_native_match_count_checked":1140,
       "fully_matching_both_teams_and_utc":1139,
       "time_disagreements":disagreements,
       "warning":"TWO_ARCHIVED_TIMES_DIFFER; NO PROOF WHICH ONE WAS OFFICIAL AT HISTORICAL PREDICTION CUTOFF",
       "local_names_and_times_only_no_private_ids":True,
       "native_team_ids_exported":False,
       "native_fixture_ids_exported":False,
       "scores_or_odds_read":False,
       "test_rows_read":0,
       "source_mutated":False,
       "full_historical_PIT_train_certified":0,
       "training_allowed":False,
       "gate14_pass":False,
    }
