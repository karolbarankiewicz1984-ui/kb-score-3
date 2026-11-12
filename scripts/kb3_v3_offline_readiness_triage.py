"""Offline-only V3 readiness triage; no network, database writes or provider calls."""
from datetime import datetime, timedelta, timezone


def assess_readiness(fixtures_in_window, selected_targets, kickoff_utc=None,
                     hosted_source_utc=None, builder_verified_87=False):
    if fixtures_in_window < 0 or selected_targets < 0:
        raise ValueError("INVALID_COUNTS")
    if selected_targets > fixtures_in_window:
        return "SELECTOR_COUNT_INCONSISTENT"
    if fixtures_in_window == 0:
        return "NO_FIXTURES_IN_WINDOW"
    if selected_targets == 0:
        return "SELECTOR_MISMATCH_REQUIRES_OFFLINE_REPLAY"
    if not kickoff_utc or not hosted_source_utc:
        return "MISSING_INDEPENDENT_HOST_TIME"
    if kickoff_utc.tzinfo is None or hosted_source_utc.tzinfo is None:
        return "INVALID_TIMEZONE"
    cutoff = kickoff_utc.astimezone(timezone.utc) - timedelta(minutes=90)
    if hosted_source_utc.astimezone(timezone.utc) >= cutoff:
        return "SOURCE_NOT_BEFORE_EXACT_CUTOFF"
    if not builder_verified_87:
        return "ORIGINAL_BUILDER_87_NOT_VERIFIED"
    return "RESEARCH_FORWARD_87_VERIFIED_NOT_PIT_TRAIN"
