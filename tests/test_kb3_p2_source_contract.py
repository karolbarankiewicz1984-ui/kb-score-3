import copy
from dataclasses import replace
import unittest

from src.kb3_p2_source_contract import (
    CARD_TARGETS, PERIOD, STAT_FIELDS, TARGETS, CardRule, Fixture, HostProof, Source,
    StatRule, validate,
)
from src.kb3_pit_ledger import canonical, hexdigest

FIXTURE = Fixture("POL", "m_000001", "t_000001", "t_000002", "2026-11-01T16:00:00Z", "finished")
REVISION = "synthetic-schema-rev"
PERIOD_LABEL = "SyntheticRegulation"
TARGET_KICKOFF = "2026-11-02T20:30:00Z"
RULES = {target: StatRule(REVISION, PERIOD_LABEL, field, "integer", "synthetic-definition")
         for target, field in STAT_FIELDS.items()}
CARD_RULE = CardRule(REVISION, "synthetic-card-definition", True)


def source(payload, observed="2026-11-01T18:30:00Z", created="2026-11-01T18:31:00Z"):
    digest = hexdigest(canonical(payload))
    return Source(payload, observed, digest, REVISION, HostProof("synthetic-host", created, digest))


def identity():
    return {"match_id": FIXTURE.match_id, "home_team": {"id": FIXTURE.home_id},
            "away_team": {"id": FIXTURE.away_id}}


def stats():
    items = [
        {"key": field, "home": str(home), "away": str(away), "format_type": "integer"}
        for field, home, away in zip(STAT_FIELDS.values(), (12, 5, 14, 6), (13, 0, 10, 4))
    ]
    return {"data": {**identity(), "periods": [{"period": PERIOD_LABEL, "groups": [{"items": items}]}]}}


def card(kind, player="p1", event_id="e1", team=FIXTURE.home_id, period=PERIOD, participant="active"):
    return {"id": event_id, "kind": kind, "team_id": team, "player_id": player,
            "period": period, "participant": participant}


def cards(events, complete=True):
    return {**identity(), "period": PERIOD, "complete": complete, "events": events}


class StatContractTests(unittest.TestCase):
    def validate_stats(self, payload, **kwargs):
        return validate(FIXTURE, stats=source(payload), stat_rules=RULES, **kwargs)

    def test_regulation_attested_under_each_reviewed_rule_including_explicit_zero(self):
        result = self.validate_stats(stats(), target_kickoff_utc=TARGET_KICKOFF)
        self.assertEqual(set(result), set(TARGETS))
        for target, pair in zip(STAT_FIELDS, ((12, 13), (5, 0), (14, 10), (6, 4))):
            self.assertEqual([result[target][side].value for side in ("home", "away", "total")],
                             [*pair, sum(pair)])
            self.assertEqual(result[target]["total"].status, "PASS")

    def test_extra_time_full_match_and_unknown_periods_are_never_substituted(self):
        for period in ("ExtraTime", "All", "1stHalf", "Penalties"):
            with self.subTest(period=period):
                payload = stats()
                payload["data"]["periods"][0]["period"] = period
                count = self.validate_stats(payload)["fouls_called"]["total"]
                self.assertEqual((count.value, count.reason), (None, "REGULATION_PERIOD_MISSING"))

    def test_missing_period_and_duplicate_period(self):
        for shape, reason in (([], "NATIVE_PERIOD_MISSING"), ([{}, {}], "INVALID_NATIVE_PERIOD")):
            payload = stats()
            payload["data"]["periods"] = shape
            self.assertEqual(self.validate_stats(payload)["fouls_called"]["total"].reason, reason)
        payload = stats()
        payload["data"]["periods"] *= 2
        self.assertEqual(self.validate_stats(payload)["fouls_called"]["total"].reason,
                         "DUPLICATE_REGULATION_PERIOD")

    def test_missing_one_side_is_not_zero_and_other_targets_remain_available(self):
        payload = stats()
        del payload["data"]["periods"][0]["groups"][0]["items"][1]["away"]
        result = self.validate_stats(payload)
        self.assertEqual(result["corners_taken"]["home"].value, 5)
        self.assertIsNone(result["corners_taken"]["away"].value)
        self.assertEqual(result["corners_taken"]["away"].reason, "TEAM_STAT_MISSING")
        self.assertIsNone(result["corners_taken"]["total"].value)
        self.assertEqual(result["fouls_called"]["total"].status, "PASS")

    def test_invalid_count_or_false_zero_is_quarantined(self):
        for raw in (False, True, -1, "0%", {"value": 0}, "0.2"):
            with self.subTest(raw=raw):
                payload = stats()
                payload["data"]["periods"][0]["groups"][0]["items"][0]["home"] = raw
                count = self.validate_stats(payload)["fouls_called"]["home"]
                self.assertEqual((count.status, count.value, count.reason),
                                 ("QUARANTINE", None, "INVALID_TEAM_COUNT"))

    def test_wrong_native_fixture_and_reversed_or_missing_native_team_ids(self):
        for edits, reason in (
            ({"match_id": "m_999999"}, "NATIVE_FIXTURE_ID_MISMATCH"),
            ({"home_team": {"id": FIXTURE.away_id}, "away_team": {"id": FIXTURE.home_id}},
             "NATIVE_TEAM_SIDE_MISMATCH"),
            ({"away_team": {}}, "NATIVE_TEAM_ID_MISSING"),
        ):
            with self.subTest(reason=reason):
                payload = stats()
                payload["data"].update(edits)
                self.assertEqual(self.validate_stats(payload)["corners_taken"]["total"].reason, reason)

    def test_rejects_incomplete_fixture_and_protected_or_cup_scope(self):
        for fixture, reason in (
            (replace(FIXTURE, status="in_progress"), "FIXTURE_NOT_FINISHED"),
            (replace(FIXTURE, status="abandoned"), "FIXTURE_NOT_FINISHED"),
            (replace(FIXTURE, scope="ENG"), "FIXTURE_SCOPE_EXCLUDED"),
            (replace(FIXTURE, scope="UCL"), "FIXTURE_SCOPE_EXCLUDED"),
        ):
            result = validate(fixture, stats=source(stats()), stat_rules=RULES)
            self.assertEqual({counts["total"].reason for counts in result.values()}, {reason})

    def test_source_needs_matching_revision_and_review_per_target(self):
        payload = stats()
        results = validate(FIXTURE, stats=source(payload),
                           stat_rules={"fouls_called": replace(RULES["fouls_called"], revision="other"),
                                       "corners_taken": RULES["corners_taken"]})
        self.assertEqual(results["fouls_called"]["home"].reason, "NATIVE_STAT_SEMANTICS_UNVERIFIED")
        self.assertEqual(results["corners_taken"]["total"].value, 5)
        self.assertIsNone(results["shots_on_target"]["total"].value)

    def test_missing_total_shots_is_not_imputed_from_other_categories(self):
        payload = stats()
        items = payload["data"]["periods"][0]["groups"][0]["items"]
        items.pop(2)
        items.append({"key": "ShotsOffTarget", "format_type": "integer", "home": 4, "away": 6})
        result = self.validate_stats(payload)
        self.assertEqual(result["total_shots"]["total"].reason, "NATIVE_STAT_FIELD_MISSING")
        self.assertEqual(result["shots_on_target"]["total"].value, 10)

    def test_conflicting_duplicates_and_shot_relationship(self):
        payload = stats()
        items = payload["data"]["periods"][0]["groups"][0]["items"]
        items.append({**items[0], "away": "99"})
        items[3]["home"] = "19"
        counts = self.validate_stats(payload)
        self.assertEqual(counts["fouls_called"]["away"].reason, "CONFLICTING_STAT_DUPLICATES")
        for target in ("total_shots", "shots_on_target"):
            self.assertEqual(counts[target]["home"].reason, "SHOTS_ON_TARGET_EXCEED_TOTAL")
            self.assertEqual(counts[target]["total"].status, "QUARANTINE")

    def test_late_source_or_late_host_cannot_be_used_before_forecast_cutoff(self):
        for observed, created, reason in (
            ("2026-11-02T19:00:00Z", "2026-11-02T19:01:00Z", "SOURCE_OBSERVATION_AT_OR_AFTER_CUTOFF"),
            ("2026-11-02T18:59:00Z", "2026-11-02T19:00:00Z", "HOST_PROOF_AT_OR_AFTER_CUTOFF"),
            ("2026-11-01T17:10:00Z", "2026-11-01T17:20:00Z", "OBSERVED_BEFORE_REGULATION_END"),
        ):
            with self.subTest(reason=reason):
                counts = validate(FIXTURE, stats=source(stats(), observed, created), stat_rules=RULES,
                                  target_kickoff_utc=TARGET_KICKOFF)
                self.assertEqual(counts["fouls_called"]["total"].reason, reason)

    def test_captured_bytes_and_host_proof_must_bind_and_be_chronological(self):
        captured = source(stats())
        changed = copy.deepcopy(captured.payload)
        changed["data"]["periods"].append({"period": "different"})
        for evidence, reason in (
            (replace(captured, payload=changed), "SOURCE_HASH_MISMATCH"),
            (replace(captured, host=None), "INDEPENDENT_HOST_PROOF_MISSING"),
            (replace(captured, host=replace(captured.host, payload_sha256="b" * 64)),
             "HOST_PROOF_NOT_BOUND_TO_PAYLOAD"),
            (replace(captured, host=replace(captured.host, created_at_utc="2026-11-01T18:29:00Z")),
             "HOST_PROOF_PREDATES_OBSERVATION"),
        ):
            with self.subTest(reason=reason):
                counts = validate(FIXTURE, stats=evidence, stat_rules=RULES)
                self.assertEqual(counts["fouls_called"]["total"].reason, reason)


class CardContractTests(unittest.TestCase):
    def test_counts_second_caution_once_and_only_active_players_in_scope(self):
        events = [
            card("yellow"),
            card("second_yellow", event_id="e2"),
            card("straight_red", player="p2", event_id="e3", team=FIXTURE.away_id),
            card("yellow", player="p3", event_id="e4", participant="bench"),
            card("straight_red", player="p4", event_id="e5", period="AFTER_MATCH"),
            card("yellow", player="p5", event_id="e6", period="HALF_TIME"),
            card("yellow", player="p6", event_id="e7", period="EXTRA_TIME"),
        ]
        counts = validate(FIXTURE, cards=source(cards(events)), card_rule=CARD_RULE)
        self.assertEqual([counts[target]["total"].value for target in CARD_TARGETS], [3, 1, 1, 6])
        self.assertEqual([counts["card_units"][side].value for side in ("home", "away")], [4, 2])
        counts = validate(FIXTURE, cards=source(cards(events)),
                          card_rule=replace(CARD_RULE, include_half_time=False))
        self.assertEqual(counts["card_units"]["total"].value, 5)

    def test_conflicting_events_or_unknown_semantics_quarantine_only_card_targets(self):
        for events, reason in (
            ([card("second_yellow")], "SECOND_YELLOW_WITHOUT_FIRST_CAUTION"),
            ([card("yellow"), card("second_yellow", event_id="e2"), card("straight_red", event_id="e3")],
             "CARD_DISMISSAL_OR_CAUTION_CONFLICT"),
            ([card("yellow"), card("yellow", event_id="e2")], "CARD_DISMISSAL_OR_CAUTION_CONFLICT"),
            ([card("yellow"), card("yellow", player="p2")], "DUPLICATE_OR_INVALID_EVENT_ID"),
            ([card("redcard")], "UNKNOWN_EVENT_KIND"),
            ([card("yellow", period="unknown")], "UNKNOWN_EVENT_PERIOD"),
            ([card("yellow", team="t_999999")], "CARD_EVENT_IDENTITY_INVALID"),
            ([card("yellow", participant="unknown")], "UNKNOWN_CARD_PARTICIPANT_STATUS"),
        ):
            with self.subTest(reason=reason):
                counts = validate(FIXTURE, cards=source(cards(events)), card_rule=CARD_RULE,
                                  stats=source(stats()), stat_rules=RULES)
                for target in CARD_TARGETS:
                    total = counts[target]["total"]
                    self.assertEqual((total.status, total.value, total.reason), ("QUARANTINE", None, reason))
                self.assertEqual(counts["fouls_called"]["total"].value, 25)

    def test_empty_stream_is_zero_only_when_completeness_and_semantics_are_proven(self):
        counts = validate(FIXTURE, cards=source(cards([], complete=False)), card_rule=CARD_RULE)
        self.assertEqual(counts["card_units"]["total"].reason, "COMPLETE_CARD_STREAM_UNPROVEN")
        counts = validate(FIXTURE, cards=source(cards([])))
        self.assertEqual(counts["card_units"]["total"].reason, "NATIVE_CARD_EVENT_SEMANTICS_UNVERIFIED")
        counts = validate(FIXTURE, cards=source(cards([])), card_rule=CARD_RULE)
        self.assertEqual(counts["card_units"]["total"].value, 0)
