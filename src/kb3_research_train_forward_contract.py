"""Research-only versioned TRAIN/forward clock contract (no model or DB mutation).

The 48h historical reconstruction and 3h observed forward rule are NOT
interchangeable. Even records with timestamps are not certified without
independent source evidence. This module measures the gap; it does not
turn reconstructed history into original PIT or authorize a new model.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import json

SCHEMA = "kb3-train-forward-clock-parity-research-v1"
CLOCK_LEGACY = timedelta(hours=48)
CLOCK_FORWARD = timedelta(hours=3)
LEAD = timedelta(minutes=90)
ALLOWED = frozenset(("ESP", "ITA", "GER", "FRA", "NED", "BEL", "TUR", "POL"))


class ParityError(ValueError):
    pass


def ensure(ok, message):
    if not ok:
        raise ParityError(message)


def utc(value):
    ensure(isinstance(value, str) and value.endswith("Z"), "UTC_Z_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ParityError("INVALID_UTC") from exc
    ensure(parsed.utcoffset() == timedelta(0), "NOT_UTC")
    return parsed


def sha(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def age_days(reference, kickoff):
    return round((reference - kickoff).total_seconds() / 86400, 4)


def audit_target(row):
    """Compare identical predecessor IDs under two historical clock rules.

    Forward_clock_only is an upper bound, NOT attested provider history.
    Evidence-labelled rows are still only input claims; external host/provider
    byte verification is outside this read-only research module.
    """
    ensure(isinstance(row, dict), "TARGET_OBJECT_REQUIRED")
    ensure(row.get("league") in ALLOWED, "UNAPPROVED_OR_PROTECTED_LEAGUE")
    target_id = row.get("fixture_id")
    ensure(isinstance(target_id, str) and target_id, "TARGET_ID_REQUIRED")
    kickoff = utc(row["kickoff_utc"])
    cutoff = utc(row["capture_cutoff_utc"])
    ensure(cutoff <= kickoff - LEAD, "TARGET_NOT_BEFORE_90MIN_CUTOFF")
    predecessors = row.get("predecessors")
    ensure(isinstance(predecessors, list), "PREDECESSOR_LIST_REQUIRED")
    seen = set()
    legacy, forward_clock_only, evidence_claims = [], [], []
    reasons = {"AFTER_CUTOFF": 0, "LEGACY_48H_NOT_ELIGIBLE": 0,
               "FORWARD_3H_NOT_ELIGIBLE": 0, "PIT_EVIDENCE_NOT_SUPPLIED": 0}
    time_by_id = {}
    for p in predecessors:
        ensure(isinstance(p, dict), "PREDECESSOR_OBJECT_REQUIRED")
        pid = p.get("fixture_id")
        ensure(isinstance(pid, str) and pid and pid != target_id, "TARGET_OR_BAD_PREDECESSOR")
        ensure(pid not in seen, "DUPLICATE_PREDECESSOR_ID")
        seen.add(pid)
        prior = utc(p["kickoff_utc"])
        ensure(prior < kickoff, "FUTURE_PREDECESSOR")
        time_by_id[pid] = prior
        if prior >= cutoff:
            reasons["AFTER_CUTOFF"] += 1
            continue
        old_ok = prior + CLOCK_LEGACY <= kickoff
        new_ok = prior + CLOCK_FORWARD <= cutoff
        if old_ok:
            legacy.append(pid)
        else:
            reasons["LEGACY_48H_NOT_ELIGIBLE"] += 1
        if new_ok:
            forward_clock_only.append(pid)
        else:
            reasons["FORWARD_3H_NOT_ELIGIBLE"] += 1
        attested = False
        if new_ok and p.get("source_provenance") == "ORIGINAL_PREMATCH_ATTESTED":
            published = p.get("source_published_at_utc")
            observed = p.get("source_observed_at_utc")
            if published is not None and observed is not None:
                published_dt = utc(published)
                observed_dt = utc(observed)
                attested = prior + CLOCK_FORWARD <= published_dt <= observed_dt <= cutoff
        if attested:
            evidence_claims.append(pid)
        elif new_ok:
            reasons["PIT_EVIDENCE_NOT_SUPPLIED"] += 1
    order = lambda ident: (time_by_id[ident], ident)
    legacy.sort(key=order)
    forward_clock_only.sort(key=order)
    evidence_claims.sort(key=order)

    def last_age(ids, reference):
        return age_days(reference, time_by_id[ids[-1]]) if ids else None

    result = {
        "schema": SCHEMA, "league": row["league"], "fixture_id": target_id,
        "target_kickoff_utc": row["kickoff_utc"],
        "capture_cutoff_utc": row["capture_cutoff_utc"],
        "predecessors_checked": len(predecessors),
        "legacy48h_predecessor_ids": legacy,
        "forward3h_clock_only_predecessor_ids": forward_clock_only,
        "forward3h_unverified_evidence_claim_ids": evidence_claims,
        "only_legacy_ids": sorted(set(legacy) - set(forward_clock_only)),
        "only_forward_clock_ids": sorted(set(forward_clock_only) - set(legacy)),
        "legacy_days_since_last_kickoff_at_target": last_age(legacy, kickoff),
        "forward_days_since_last_kickoff_at_capture": last_age(forward_clock_only, cutoff),
        "reasons": reasons,
        "independent_source_evidence_verified": False,
        "original_historical_pit_certified": False,
        "training_allowed": False,
        "production_model_changed": False,
    }
    result["report_sha256"] = sha(result)
    return result


def audit_batch(rows):
    ensure(isinstance(rows, list), "BATCH_LIST_REQUIRED")
    reports = [audit_target(row) for row in rows]
    ensure(len({(r["league"], r["fixture_id"]) for r in reports}) == len(reports),
           "DUPLICATE_TARGET")
    return {
        "schema": SCHEMA, "target_count": len(reports),
        "predecessor_set_difference_targets": sum(
            bool(r["only_legacy_ids"] or r["only_forward_clock_ids"]) for r in reports),
        "days_since_last_difference_targets": sum(
            r["legacy_days_since_last_kickoff_at_target"] !=
            r["forward_days_since_last_kickoff_at_capture"] for r in reports),
        "research_only": True, "independent_pit_verified": False,
        "gate16": "PENDING", "gate17": "PENDING",
        "targets": reports,
    }
