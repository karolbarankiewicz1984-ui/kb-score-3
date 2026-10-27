"""One explicitly sourced 2024-10-19 Ipswich–Everton scheduled/actual kickoff distinction.

An event-day kickoff delay is NOT evidence any original PitchAPI M1
feature existed ahead of the originally scheduled match time. Do not
rewrite the sealed native source or the original public reference.

This read-only reviewer classifies an authenticated owner-local diagnostic
without exposing native team or match IDs, outcome labels, TEST or odds.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from src.kb3_step14_native_team_crosswalk import canonical_team_name
from src.kb3_step14_full_identity_pit_audit import PUBLIC_REFERENCE_SHA

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"data/audits/STEP14_IPSWICH_EVERTON_VERIFIED_KICKOFF_DELAY_2026-10-28.json"
EXPECTED_SCHEDULED="2024-10-19T14:00:00Z"
EXPECTED_ACTUAL="2024-10-19T14:15:00Z"
EXPECTED_SOURCE_URLS={
 "https://www.itfc.co.uk/news/2024/october/19/everton-kick-off-delayed/",
 "https://www.premierleague.com/en/news/4149676/ipswich-town-fc-v-everton-fc-premier-league",
 "https://www.premierleague.com/en/news/4076999",
 "https://www.reuters.com/sports/soccer/ipswich-v-everton-delayed-due-turnstile-issue-2024-10-19/",
}

class ExceptionEvidenceError(ValueError):pass

def _require_original_evidence(evidence):
    if (not isinstance(evidence,dict) or
        evidence.get("schema")!="kb3-step14-verified-single-kickoff-delay-exception-v1" or
        evidence.get("season")!="2024-25" or
        evidence.get("partition")!="TRAIN" or
        canonical_team_name(evidence.get("home_name"))!=canonical_team_name("Ipswich Town") or
        canonical_team_name(evidence.get("away_name"))!=canonical_team_name("Everton") or
        evidence.get("originally_scheduled_kickoff_utc")!=EXPECTED_SCHEDULED or
        evidence.get("actual_kickoff_utc")!=EXPECTED_ACTUAL or
        evidence.get("actual_minus_scheduled_minutes")!=15 or
        evidence.get("matching_public_reference_sha256")!=PUBLIC_REFERENCE_SHA or
        {r.get("url") for r in evidence.get("independent_sources",[]) if type(r) is dict}
            !=EXPECTED_SOURCE_URLS or
        evidence.get("historical_publication_clock_of_match_features_proven") is not False or
        evidence.get("training_allowed") is not False or
        evidence.get("gate14_pass") is not False or
        evidence.get("original_training_rows_pit_certified")!=0):
        raise ExceptionEvidenceError("OFFICIAL_KICKOFF_DELAY_EVIDENCE_NOT_PINNED")

def classify_owner_diagnostic(result,evidence):
    """Accept ONLY screenshot's real 1139+1 case, without upgrading its PIT."""
    _require_original_evidence(evidence)
    if (type(result) is not dict or
        result.get("schema")!="kb3-step14-one-owner-local-kickoff-discrepancy-v1" or
        result.get("original_native_match_count_checked")!=1140 or
        result.get("fully_matching_both_teams_and_utc")!=1139 or
        result.get("training_allowed") is not False or
        result.get("gate14_pass") is not False or
        result.get("test_rows_read")!=0 or
        result.get("native_fixture_ids_exported") is not False or
        result.get("native_team_ids_exported") is not False or
        not isinstance(result.get("time_disagreements"),list) or
        len(result["time_disagreements"])!=1):
        raise ExceptionEvidenceError("OWNER_DIAGNOSTIC_IS_NOT_EXACT_1139_PLUS_ONE")
    m=result["time_disagreements"][0]
    if (m.get("season")!="2024-25" or m.get("partition")!="TRAIN" or
        canonical_team_name(m.get("home_name"))!=canonical_team_name("Ipswich Town") or
        canonical_team_name(m.get("away_name"))!=canonical_team_name("Everton") or
        m.get("pitchapi_kickoff_utc")!=EXPECTED_ACTUAL or
        m.get("openfootball_kickoff_utc")!=EXPECTED_SCHEDULED or
        m.get("difference_pitchapi_minus_public_minutes")!=15):
        raise ExceptionEvidenceError("DISAGREEMENT_NOT_THE_VERIFIED_IPSWICH_DELAY")
    return {
        "schema":"kb3-step14-documentation-only-identity-exception-v1",
        "matched_external_identity":1140,
        "identical_source_kickoffs":1139,
        "explicitly_documented_scheduled_vs_actual_delay":1,
        "home_name":"Ipswich Town","away_name":"Everton",
        "scheduled_kickoff_utc":EXPECTED_SCHEDULED,
        "actual_kickoff_utc":EXPECTED_ACTUAL,
        "source_correction_needed":False,
        "original_historical_training_pit_certified":0,
        "training_allowed":False,"gate14_pass":False,
        "test_rows_read":0,"native_ids_exported":False,
    }

def eligible_before_original_schedule(feature_observed_at_utc,evidence):
    """A strict hard cap for any FUTURE experimental feature-PIT study.

    This is only a deadline check, not a proof that a feature was truly
    published or available; independent provenance remains mandatory.
    """
    _require_original_evidence(evidence)
    try:
        observed=datetime.fromisoformat(feature_observed_at_utc.replace("Z","+00:00"))
        cutoff=datetime.fromisoformat(EXPECTED_SCHEDULED.replace("Z","+00:00"))
    except (AttributeError,ValueError) as exc:
        raise ExceptionEvidenceError("INVALID_FEATURE_TIME") from exc
    if observed.tzinfo is None or observed.utcoffset().total_seconds()!=0:
        raise ExceptionEvidenceError("NOT_UTC")
    return observed<cutoff

def read_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))
