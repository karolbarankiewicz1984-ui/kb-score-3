"""Step14 PitchAPI-native team-xG semantics vs exact historic FPL/Opta fixture sides.

Uses transient authentic source values in memory only. This is a
RETROSPECTIVE semantic-distance experiment, NEVER 2023-25 PitchAPI PIT.
The current 2026 capture clock is NOT a provider original first-published
clock. No provider values, IDs, or team names leave in output.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from math import isfinite
import statistics
from src.kb3_pitch_native import MATCH_ID,TEAM_ID

SCHEMA="kb3-step14-pitchapi-fpl-matched-team-xg-semantics-no-historical-clock-v1"
class SemanticAuditError(ValueError):pass

def source_data(payload):
    if not isinstance(payload,dict):
        raise SemanticAuditError("PITCHAPI_RESPONSE_NOT_OBJECT")
    data=payload.get("data",payload)
    if not isinstance(data,dict):raise SemanticAuditError("PITCHAPI_RESPONSE_DATA_NOT_OBJECT")
    return data

def num(value,*,maximum=30):
    if isinstance(value,bool) or value is None:
        raise SemanticAuditError("MISSING_OR_INVALID_XG")
    if not isinstance(value,(float,int,str)):
        raise SemanticAuditError("MISSING_OR_INVALID_XG")
    if isinstance(value,str):
        if not value.strip() or value.strip()!=value:
            raise SemanticAuditError("MISSING_OR_INVALID_XG")
    try:result=float(value)
    except (ValueError,TypeError) as e:
        raise SemanticAuditError("INVALID_XG_NUMBER") from e
    if not isfinite(result) or not 0<=result<=maximum:
        raise SemanticAuditError("NONFINITE_OR_NEGATIVE_XG")
    return result

def parse_native_team_stats(payload,match_id,home_id,away_id):
    """Only Period=All, item.key=expected_goals. Never xGOT, npxG or 1H."""
    d=source_data(payload)
    if d.get("match_id")!=match_id:
        raise SemanticAuditError("TEAM_STATS_NATIVE_FIXTURE_MISMATCH")
    home=d.get("home_team");away=d.get("away_team")
    if not isinstance(home,dict) or not isinstance(away,dict) or (
        home.get("id"),away.get("id"))!=(home_id,away_id):
        raise SemanticAuditError("TEAM_STATS_NATIVE_SIDE_ID_MISMATCH")
    periods=d.get("periods")
    if not isinstance(periods,list):
        raise SemanticAuditError("TEAM_STATS_PERIODS_MISSING")
    all_periods=[p for p in periods if isinstance(p,dict) and p.get("period")=="All"]
    if len(all_periods)!=1:
        raise SemanticAuditError("TEAM_STATS_FULL_MATCH_PERIOD_NOT_UNIQUE")
    items=[]
    for group in all_periods[0].get("groups",[]):
        if not isinstance(group,dict) or not isinstance(group.get("items"),list):
            raise SemanticAuditError("TEAM_STATS_INVALID_GROUP")
        items.extend(x for x in group["items"]
                     if isinstance(x,dict) and x.get("key")=="expected_goals")
    if len(items)!=1:
        raise SemanticAuditError("TEAM_STATS_XG_FIELD_NOT_UNIQUE")
    item=items[0]
    if item.get("format_type") not in ("double",""):
        raise SemanticAuditError("TEAM_STATS_XG_FORMAT_NOT_NUMERIC")
    return num(item.get("home")),num(item.get("away"))

def parse_native_shots(payload,match_id,home_id,away_id):
    """Validate exact shot fixture and each shot's original team ID.

    Ignore xGOT entirely: expected_goals in [0,1] is distinct from
    post-shot expected_goals_on_target.
    """
    d=source_data(payload)
    if d.get("match_id")!=match_id:
        raise SemanticAuditError("SHOTS_NATIVE_FIXTURE_MISMATCH")
    periods=d.get("periods")
    if not isinstance(periods,list) or not periods:
        raise SemanticAuditError("SHOTS_PERIODS_MISSING")
    out={home_id:0.0,away_id:0.0}
    counts=Counter();seen=set()
    for period in periods:
        if not isinstance(period,dict) or not isinstance(period.get("shots"),list):
            raise SemanticAuditError("SHOTS_PERIOD_INCOMPLETE")
        for s in period["shots"]:
            if not isinstance(s,dict) or s.get("team_id") not in out:
                raise SemanticAuditError("SHOT_WRONG_TEAM_OR_MALFORMED")
            shot_id=s.get("id")
            if shot_id is not None:
                if not isinstance(shot_id,str) or (match_id,shot_id) in seen:
                    raise SemanticAuditError("DUPLICATE_OR_INVALID_NATIVE_SHOT")
                seen.add((match_id,shot_id))
            v=num(s.get("expected_goals"),maximum=1)
            t=s["team_id"]
            out[t]+=v
            counts[t]+=1
    if not sum(counts.values()):
        raise SemanticAuditError("SHOTS_EMPTY_CANNOT_CERTIFY_0_XG")
    return out[home_id],out[away_id],counts[home_id],counts[away_id]

def side_comparison(*,match_id,home_id,away_id,source_shots,source_stats,
                    fpl_side_values,public_fixture_id,fpl_home_id,fpl_away_id):
    """One strict, already-joined native fixture with two FPL team sides.

    Caller must prove FPL <-> native via complete 380-match historical
    fingerprints before this function; identical names aren't accepted.
    """
    if not MATCH_ID.fullmatch(match_id) or not all(
         isinstance(t,str) and TEAM_ID.fullmatch(t) for t in (home_id,away_id)):
        raise SemanticAuditError("ORIGINAL_NATIVE_ID_SHAPE_INVALID")
    if home_id==away_id or fpl_home_id==fpl_away_id:
        raise SemanticAuditError("MATCH_SIDES_NOT_DISTINCT")
    for key in ((public_fixture_id,fpl_home_id),(public_fixture_id,fpl_away_id)):
        if key not in fpl_side_values:
            raise SemanticAuditError("NO_FPL_PLAYER_XG_FOR_EXACT_TEAM_AND_FIXTURE")
    totalh,totala=parse_native_team_stats(source_stats,match_id,home_id,away_id)
    sh,sa,nh,na=parse_native_shots(source_shots,match_id,home_id,away_id)
    return [
        {"pitch_shot_xg":sh,"pitch_fullmatch_team_stats_xg":totalh,
         "fpl_player_aggregate_xg":num(fpl_side_values[(public_fixture_id,fpl_home_id)]),
         "shots":nh},
        {"pitch_shot_xg":sa,"pitch_fullmatch_team_stats_xg":totala,
         "fpl_player_aggregate_xg":num(fpl_side_values[(public_fixture_id,fpl_away_id)]),
         "shots":na},
    ]

def aggregate(records):
    """Output ONLY non-identifying scalar aggregate errors (no values/IDs)."""
    if not records:raise SemanticAuditError("NO_EXACT_NATIVE_SIDE_COMPARISONS")
    for r in records:
        if set(r)!={"pitch_shot_xg","pitch_fullmatch_team_stats_xg",
                   "fpl_player_aggregate_xg","shots"}:
            raise SemanticAuditError("SEMANTIC_INPUT_UNTRUSTED")
    internal=[abs(r["pitch_shot_xg"]-r["pitch_fullmatch_team_stats_xg"]) for r in records]
    external=[abs(r["fpl_player_aggregate_xg"]-r["pitch_fullmatch_team_stats_xg"]) for r in records]
    for diff in internal+external:
        if not isfinite(diff):raise SemanticAuditError("NONFINITE_COMPARISON")
    def summarize(err):
        return {"count":len(err),
                "mean_absolute_difference":round(statistics.fmean(err),4),
                "median_absolute_difference":round(statistics.median(err),4),
                "max_absolute_difference":round(max(err),4),
                "within_0_02":sum(e<=.020000001 for e in err),
                "within_0_10":sum(e<=.100000001 for e in err),
                "over_0_25":sum(e>.250000001 for e in err)}
    return {
       "schema":SCHEMA,
       "exact_matched_team_sides":len(records),
       "exact_matched_fixtures":len(records)//2,
       "PITCH_SHOTS_XG_vs_PITCH_FULL_MATCH_STATS_XG":summarize(internal),
       "FPL_OPTA_PLAYER_SUM_XG_vs_PITCH_FULL_MATCH_STATS_XG":summarize(external),
       "comparison_values_in_memory_only":True,
       "source_last_observed_is_NOT_original_first_published":True,
       "historical_PitchAPI_first_publication_proven":False,
       "equivalence_of_provider_xg_definitions_proven":False,
       "eligible_original_train_PIT":0,"eligible_original_validation_PIT":0,
       "training_allowed":False,"gate14_pass":False,
       "test_examined":False,
    }

def classify_historical_publication(record,*,target_cutoff_utc):
    """No retrospective API response may establish its own historical clock."""
    # Even server Date or response retrieval time cannot prove the exact
    # stat value's first publication before any old target.
    if not isinstance(record,dict):raise SemanticAuditError("NO_SOURCE_EVIDENCE")
    if record.get("provider_original_publication_evidence_verified") is not True:
        return {"status":"BLOCKED_NO_PROVIDER_ORIGINAL_XG_PUBLICATION_RECEIPT",
                "pit_eligible":False}
    # This audit deliberately does not implement an approval path: external
    # provider attestations need a SEPARATE documented independent validator.
    return {"status":"HOLD_FOR_INDEPENDENT_PROVIDER_RECEIPT_REVIEW",
            "pit_eligible":False}
