"""Validate evidence for independent, research-only non-goal count targets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import re

from src.kb3_pitch_native import MATCH_ID, TEAM_ID
from src.kb3_pit_ledger import as_utc, canonical, hexdigest

SCOPES = ("BEL", "ESP", "FRA", "GER", "ITA", "NED", "POL", "TUR")
PERIOD = "REGULAR_90_MINUTES"
SIDES = ("home", "away")
# Historical PitchAPI keys are candidates. No provider revision is approved here.
STAT_FIELDS = {
    "fouls_called": "fouls",
    "corners_taken": "corners",
    "total_shots": "total_shots",
    "shots_on_target": "ShotsOnTarget",
}
CARD_TARGETS = ("yellow_cards", "straight_red_cards", "second_yellow_dismissals", "card_units")
TARGETS = tuple(STAT_FIELDS) + CARD_TARGETS
COUNT_TEXT = re.compile(r"[0-9]{1,9}(?:\.0{1,9})?")
SHA256 = re.compile(r"[a-f0-9]{64}")


@dataclass(frozen=True)
class Fixture:
    """Expected identity and status from a separately checked fixture listing."""

    scope: str
    match_id: str
    home_id: str
    away_id: str
    kickoff_utc: str
    status: str


@dataclass(frozen=True)
class HostProof:
    """Inputs from an independently verified host record for these exact bytes."""

    reference: str
    created_at_utc: str
    payload_sha256: str


@dataclass(frozen=True)
class Source:
    payload: object
    observed_at_utc: str
    payload_sha256: str
    revision: str | None = None
    host: HostProof | None = None


@dataclass(frozen=True)
class StatRule:
    """A reviewed rule for one target in a particular provider revision.

    The evidence must establish that native_period means 2x45 plus stoppage
    time, and that native_field is complete per side with the target definition.
    """

    revision: str
    native_period: str
    native_field: str
    format_type: str
    definition_ref: str


@dataclass(frozen=True)
class CardRule:
    """Review of an adapter for ordered, complete, participant-aware events.

    The adapter must distinguish the second caution from a straight red and
    must preserve identity, periods and completeness from the original feed.
    """

    revision: str
    definition_ref: str
    include_half_time: bool


@dataclass(frozen=True)
class Count:
    status: str
    value: int | None
    reason: str


def blocked(reason, status="UNKNOWN"):
    return Count(status, None, reason)


def accepted(value):
    return Count("PASS", value, "VALIDATED_RESEARCH_COUNT")


def unavailable(count):
    return dict.fromkeys((*SIDES, "total"), count)


def aggregate(sides):
    if all(count.status == "PASS" for count in sides.values()):
        total = accepted(sum(count.value for count in sides.values()))
    elif sides["home"] == sides["away"]:
        total = sides["home"]
    else:
        status = "QUARANTINE" if any(count.status == "QUARANTINE" for count in sides.values()) else "UNKNOWN"
        total = blocked("TEAM_PAIR_UNAVAILABLE", status)
    return {**sides, "total": total}


def source_identity(payload, fixture):
    """Read the observed PitchAPI envelope and bind match and both team sides."""
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None, blocked("SOURCE_PAYLOAD_MISSING")
    if data.get("match_id") != fixture.match_id:
        return None, blocked("NATIVE_FIXTURE_ID_MISMATCH", "QUARANTINE")
    for side, expected_id in (("home", fixture.home_id), ("away", fixture.away_id)):
        team = data.get(side + "_team")
        if not isinstance(team, dict) or team.get("id") is None:
            return None, blocked("NATIVE_TEAM_ID_MISSING")
        if team["id"] != expected_id:
            return None, blocked("NATIVE_TEAM_SIDE_MISMATCH", "QUARANTINE")
    return data, None


def fixture_check(fixture):
    if fixture.scope not in SCOPES:
        return blocked("FIXTURE_SCOPE_EXCLUDED", "QUARANTINE")
    if (not isinstance(fixture.match_id, str) or not MATCH_ID.fullmatch(fixture.match_id)
            or any(not isinstance(team, str) or not TEAM_ID.fullmatch(team)
                   for team in (fixture.home_id, fixture.away_id))
            or fixture.home_id == fixture.away_id):
        return blocked("INVALID_EXPECTED_NATIVE_IDENTITY", "QUARANTINE")
    if fixture.status != "finished":
        return blocked("FIXTURE_NOT_FINISHED")
    return None


def source_check(source, fixture, target_kickoff_utc):
    if source is None or source.payload is None:
        return None, blocked("SOURCE_PAYLOAD_MISSING")
    try:
        same_payload = (SHA256.fullmatch(source.payload_sha256 or "")
                        and hexdigest(canonical(source.payload)) == source.payload_sha256)
    except (TypeError, ValueError):
        same_payload = False
    if not same_payload:
        return None, blocked("SOURCE_HASH_MISMATCH", "QUARANTINE")
    try:
        observed = as_utc(source.observed_at_utc)
        earliest_end = as_utc(fixture.kickoff_utc) + timedelta(minutes=90)
        cutoff = (as_utc(target_kickoff_utc) - timedelta(minutes=90)
                  if target_kickoff_utc is not None else None)
    except (ValueError, OverflowError):
        return None, blocked("INVALID_SOURCE_OR_FIXTURE_CLOCK", "QUARANTINE")
    if observed < earliest_end:
        return None, blocked("OBSERVED_BEFORE_REGULATION_END", "QUARANTINE")
    if cutoff is not None and observed >= cutoff:
        return None, blocked("SOURCE_OBSERVATION_AT_OR_AFTER_CUTOFF", "QUARANTINE")
    return source_identity(source.payload, fixture)


def host_check(source, target_kickoff_utc):
    proof = source.host
    if proof is None:
        return blocked("INDEPENDENT_HOST_PROOF_MISSING")
    if not proof.reference or proof.payload_sha256 != source.payload_sha256:
        return blocked("HOST_PROOF_NOT_BOUND_TO_PAYLOAD", "QUARANTINE")
    try:
        created = as_utc(proof.created_at_utc)
    except ValueError:
        return blocked("INVALID_HOST_CLOCK", "QUARANTINE")
    if created < as_utc(source.observed_at_utc):
        return blocked("HOST_PROOF_PREDATES_OBSERVATION", "QUARANTINE")
    if target_kickoff_utc is not None and created >= as_utc(target_kickoff_utc) - timedelta(minutes=90):
        return blocked("HOST_PROOF_AT_OR_AFTER_CUTOFF", "QUARANTINE")
    return None


def native_periods(data):
    periods = data.get("periods")
    if not isinstance(periods, list) or not periods:
        return None, blocked("NATIVE_PERIOD_MISSING")
    if any(not isinstance(p, dict) or not isinstance(p.get("period"), str)
           or not p["period"] for p in periods):
        return None, blocked("INVALID_NATIVE_PERIOD", "QUARANTINE")
    return periods, None


def select_period(periods, label):
    matches = [period for period in periods if period["period"] == label]
    if not matches:
        return None, blocked("REGULATION_PERIOD_MISSING")
    if len(matches) != 1:
        return None, blocked("DUPLICATE_REGULATION_PERIOD", "QUARANTINE")
    return matches[0], None


def period_items(period):
    groups = period.get("groups")
    if not isinstance(groups, list) or not groups:
        return None, blocked("NATIVE_STAT_GROUPS_MISSING")
    items = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("items"), list):
            return None, blocked("INVALID_NATIVE_STAT_GROUP", "QUARANTINE")
        if any(not isinstance(item, dict) for item in group["items"]):
            return None, blocked("INVALID_NATIVE_STAT_ITEM", "QUARANTINE")
        items.extend(group["items"])
    return items, None


def side_count(items, side):
    values = []
    for item in items:
        raw = item.get(side)
        if raw is None or raw == "":
            return blocked("TEAM_STAT_MISSING")
        if type(raw) is int and raw >= 0:
            values.append(raw)
        elif isinstance(raw, str) and COUNT_TEXT.fullmatch(raw.strip()):
            values.append(int(raw.split(".")[0]))
        else:
            return blocked("INVALID_TEAM_COUNT", "QUARANTINE")
    if len(set(values)) != 1:
        return blocked("CONFLICTING_STAT_DUPLICATES", "QUARANTINE")
    return accepted(values[0])


def validate_stat(periods, rule, source, target_kickoff_utc):
    if (rule is None or not rule.definition_ref or not source.revision
            or source.revision != rule.revision or not rule.native_period
            or not rule.native_field or not isinstance(rule.format_type, str)):
        return unavailable(blocked("NATIVE_STAT_SEMANTICS_UNVERIFIED"))
    period, error = select_period(periods, rule.native_period)
    if error:
        return unavailable(error)
    items, error = period_items(period)
    if error:
        return unavailable(error)
    items = [item for item in items if item.get("key") == rule.native_field]
    if not items:
        return unavailable(blocked("NATIVE_STAT_FIELD_MISSING"))
    if any(item.get("format_type") != rule.format_type for item in items):
        return unavailable(blocked("NATIVE_STAT_FORMAT_MISMATCH", "QUARANTINE"))
    error = host_check(source, target_kickoff_utc)
    if error:
        return unavailable(error)
    return aggregate({side: side_count(items, side) for side in SIDES})


def validate_stats(source, fixture, rules, target_kickoff_utc):
    data, error = source_check(source, fixture, target_kickoff_utc)
    if not error:
        periods, error = native_periods(data)
    if error:
        return {target: unavailable(error) for target in STAT_FIELDS}
    results = {
        target: validate_stat(periods, rules.get(target), source, target_kickoff_utc)
        for target in STAT_FIELDS
    }
    total, on_target = results["total_shots"], results["shots_on_target"]
    for side in SIDES:
        a, b = total[side].value, on_target[side].value
        if a is not None and b is not None and b > a:
            for item in (total, on_target):
                item[side] = blocked("SHOTS_ON_TARGET_EXCEED_TOTAL", "QUARANTINE")
    for target in ("total_shots", "shots_on_target"):
        results[target] = aggregate({side: results[target][side] for side in SIDES})
    return results


def card_counts(events, fixture, rule):
    teams = {fixture.home_id: "home", fixture.away_id: "away"}
    counts = {target: dict.fromkeys(SIDES, 0) for target in CARD_TARGETS}
    event_ids, cautioned, dismissed = set(), set(), set()
    player_teams = {}
    kinds = {"yellow": "yellow_cards", "straight_red": "straight_red_cards",
             "second_yellow": "second_yellow_dismissals"}
    for event in events:
        if not isinstance(event, dict):
            return None, "INVALID_CARD_EVENT"
        event_id, kind, period = (event.get(key) for key in ("id", "kind", "period"))
        if not isinstance(event_id, str) or not event_id or event_id in event_ids:
            return None, "DUPLICATE_OR_INVALID_EVENT_ID"
        event_ids.add(event_id)
        if kind not in ("yellow", "straight_red", "second_yellow", "non_card"):
            return None, "UNKNOWN_EVENT_KIND"
        if period not in (PERIOD, "HALF_TIME", "AFTER_MATCH", "EXTRA_TIME", "PENALTIES"):
            return None, "UNKNOWN_EVENT_PERIOD"
        if kind == "non_card" or period in ("AFTER_MATCH", "EXTRA_TIME", "PENALTIES"):
            continue
        if period == "HALF_TIME" and not rule.include_half_time:
            continue
        team, player, role = (event.get(key) for key in ("team_id", "player_id", "participant"))
        if not isinstance(team, str) or team not in teams or not isinstance(player, str) or not player:
            return None, "CARD_EVENT_IDENTITY_INVALID"
        if role not in ("active", "bench", "staff"):
            return None, "UNKNOWN_CARD_PARTICIPANT_STATUS"
        if role != "active":
            continue
        if player_teams.setdefault(player, team) != team:
            return None, "CARD_PLAYER_TEAM_CONFLICT"
        if player in dismissed or (kind == "yellow" and player in cautioned):
            return None, "CARD_DISMISSAL_OR_CAUTION_CONFLICT"
        if kind == "second_yellow" and player not in cautioned:
            return None, "SECOND_YELLOW_WITHOUT_FIRST_CAUTION"
        if kind == "yellow":
            cautioned.add(player)
        else:
            dismissed.add(player)
        counts[kinds[kind]][teams[team]] += 1
    for side in SIDES:
        # First caution has already contributed one unit; second dismissal adds two.
        counts["card_units"][side] = (counts["yellow_cards"][side]
                                      + 2 * counts["straight_red_cards"][side]
                                      + 2 * counts["second_yellow_dismissals"][side])
        counts["yellow_cards"][side] += counts["second_yellow_dismissals"][side]
    return counts, None


def validate_cards(source, fixture, rule, target_kickoff_utc):
    data, error = source_check(source, fixture, target_kickoff_utc)
    if not error:
        if (rule is None or not rule.definition_ref or not source.revision
                or source.revision != rule.revision):
            error = blocked("NATIVE_CARD_EVENT_SEMANTICS_UNVERIFIED")
        elif data.get("period") != PERIOD:
            error = blocked("REGULATION_CARD_PERIOD_UNPROVEN")
        elif data.get("complete") is not True or not isinstance(data.get("events"), list):
            error = blocked("COMPLETE_CARD_STREAM_UNPROVEN")
        else:
            error = host_check(source, target_kickoff_utc)
    if not error:
        counts, reason = card_counts(data["events"], fixture, rule)
        if reason:
            error = blocked(reason, "QUARANTINE")
    if error:
        return {target: unavailable(error) for target in CARD_TARGETS}
    return {target: aggregate({side: accepted(value) for side, value in sides.items()})
            for target, sides in counts.items()}


def validate(fixture, *, stats=None, cards=None, stat_rules=None, card_rule=None, target_kickoff_utc=None):
    """Check each target and side. Omit target kickoff for postmatch evidence.

    Treat rules and host proofs as trusted inputs after independent review.
    This interface performs no bookmaker matching, publishing or settlement.
    """
    error = fixture_check(fixture)
    if error:
        return {target: unavailable(error) for target in TARGETS}
    return {**validate_stats(stats, fixture, stat_rules or {}, target_kickoff_utc),
            **validate_cards(cards, fixture, card_rule, target_kickoff_utc)}
