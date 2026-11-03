"""Independent current-main repair: strict native shots + All stats evidence.

This is not a reconstruction of the unavailable Codex R1–R5 source package.
Observed-at clocks never establish original historical publication.
"""
from datetime import datetime, timezone, timedelta
import re
from src.kb3_pit_ledger import as_utc, canonical, hexdigest
from src.kb3_step14_pitchapi_xg_semantics import (
    SemanticAuditError, source_data, parse_native_shots, parse_native_team_stats,
)

MAX_PAIR_SECONDS = 360

def total_shots_pair(payload, match_id, home_id, away_id):
    # Also authenticates exact fixture/sides and the single All period.
    parse_native_team_stats(payload, match_id, home_id, away_id)
    periods = source_data(payload)["periods"]
    full = next(p for p in periods if isinstance(p, dict) and p.get("period") == "All")
    found = []
    for group in full.get("groups", []):
        for item in group["items"]:
            if isinstance(item, dict) and item.get("key") == "total_shots":
                found.append(item)
    if len(found) != 1:
        raise SemanticAuditError("TOTAL_SHOTS_MISSING_OR_NOT_UNIQUE")
    def count(value):
        # SDK MatchStatItem.home/away are strings; booleans and fractions fail.
        if type(value) is int and value >= 0:
            return value
        if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
            return int(value)
        raise SemanticAuditError("TOTAL_SHOTS_INVALID_COUNT")
    return count(found[0].get("home")), count(found[0].get("away"))

def validate_pair(shots, stats, match_id, home_id, away_id):
    h, a = parse_native_team_stats(stats, match_id, home_id, away_id)
    nh, na = total_shots_pair(stats, match_id, home_id, away_id)
    sh, sa, ch, ca = parse_native_shots(shots, match_id, home_id, away_id, allow_empty=True)
    if (nh, na) != (ch, ca):
        raise SemanticAuditError("SHOT_COUNT_DISAGREEMENT")
    if abs(sh-h) > .15 or abs(sa-a) > .15:
        raise SemanticAuditError("NATIVE_SHOT_VS_FULL_MATCH_XG_DISAGREE")
    # Tolerance must not certify positive xG for an independently empty side.
    if (nh == 0 and h != 0) or (na == 0 and a != 0):
        raise SemanticAuditError("EMPTY_SIDE_NONZERO_XG")
    return sh, sa, ch, ca, h, a

def validate_receipts(shots, stats, match, shot_receipt, stat_receipt, *, allow_synthetic=False):
    clocks=[]
    allowed={"NETWORK_OBSERVED","SYNTHETIC_TEST"} if allow_synthetic else {"NETWORK_OBSERVED"}
    for payload, receipt in ((shots, shot_receipt), (stats, stat_receipt)):
        if (not isinstance(receipt, dict) or receipt.get("origin") not in allowed
                or receipt.get("provider")!="PitchAPI"
                or receipt.get("original_published_at_utc") is not None):
            raise SemanticAuditError("PAIR_CAPTURE_ORIGIN_INVALID")
        if receipt.get("payload_sha256") != hexdigest(canonical(payload)) or receipt.get("payload") != payload:
            raise SemanticAuditError("PAIR_CAPTURE_PAYLOAD_MISMATCH")
        signed={k:v for k,v in receipt.items() if k!="chain_sha256"}
        if receipt.get("chain_sha256") != hexdigest(canonical(signed)):
            raise SemanticAuditError("PAIR_CAPTURE_CHAIN_INVALID")
        start, end=as_utc(receipt["started_at_utc"]), as_utc(receipt["completed_at_utc"])
        if start>end or (end-start).total_seconds()>180:
            raise SemanticAuditError("PAIR_CAPTURE_INTERVAL_INVALID")
        if receipt["origin"]=="NETWORK_OBSERVED" and end>datetime.now(timezone.utc)+timedelta(seconds=10):
            raise SemanticAuditError("PAIR_CAPTURE_IN_FUTURE")
        if start < as_utc(match["time_utc"])+timedelta(hours=3):
            raise SemanticAuditError("PAIR_CAPTURE_BEFORE_RESULT_LAG")
        clocks.append((start,end,receipt))
    if match.get("status")!="finished":
        raise SemanticAuditError("PAIR_REQUIRES_FINISHED_MATCH")
    if shot_receipt["origin"]!=stat_receipt["origin"]:
        raise SemanticAuditError("PAIR_CAPTURE_ORIGIN_MISMATCH")
    first,last=sorted(clocks,key=lambda c:c[0])
    if first[1]>last[0] or last[2].get("previous_sha256")!=first[2]["chain_sha256"]:
        raise SemanticAuditError("PAIR_CAPTURES_NOT_ADJACENT")
    if (last[1]-first[0]).total_seconds()>MAX_PAIR_SECONDS:
        raise SemanticAuditError("PAIR_CAPTURE_WINDOW_EXCEEDED")
    return last[1]
