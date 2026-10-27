"""Read-only Step11 -> Step14 schema/provenance inspection, NEVER training.

No model features or labels are exported; no real data are fetched or fitted.
Accepting a Step11 schema NEVER overrides its training_allowed=False.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
import math


class Step14BridgeError(ValueError):
    pass


SCHEMA = "kb3-step11-v0.5"
SELECTED = ("elo_home_minus_away", "home_all_5_points_avg", "away_all_5_points_avg",
            "home_all_5_xg_avg", "away_all_5_xg_avg")
FLAGS = ("home_all_5_xg", "away_all_5_xg")


def _full_step11_keys():
    features = {"elo_home_minus_away"}
    missing = set()
    for side in ("home", "away"):
        for suffix in ("elo", "elo_games_available", "prior_seasons_games_available",
                       "games_available", "days_since_last_kickoff", "venue_games_available"):
            features.add(f"{side}_{suffix}")
        missing.add(f"{side}_days_since_last_kickoff")
        for category in ("all", "venue"):
            for window in (5, 10, 15):
                stem = f"{side}_{category}_{window}"
                features.add(stem + "_n")
                for suffix in ("points_avg", "gf_avg", "ga_avg", "opponent_elo_avg",
                               "xg_n", "xg_avg", "xga_n", "xga_avg"):
                    features.add(f"{stem}_{suffix}")
                for suffix in ("history", "xg", "xga"):
                    missing.add(f"{stem}_{suffix}")
    return frozenset(features), frozenset(missing)


EXPECTED_FEATURES, EXPECTED_MISSING = _full_step11_keys()
EXPECTED_PROOFS = EXPECTED_FEATURES | frozenset("missing:" + x for x in EXPECTED_MISSING)
PROOF_KEYS = frozenset(("latest_required_observed_at_utc", "evidence_class",
                        "kind", "included_games", "fixtures_sha256",
                        "provider_original_published_at_utc", "training_allowed"))
SOURCE_KEYS = frozenset(("provider", "native_ids_only", "source_capture_id", "source_chain_sha256",
                         "source_observed_at_utc", "hash_chain_verified",
                         "source_first_publication_time_known", "historical_pit_certified",
                         "training_allowed", "multiseason_elo_status", "historical_native_seasons"))
STEP11_OUTPUT_KEYS = frozenset(("schema", "fixture_id", "elo_parameters", "elo_parameter_status",
                                "result_evidence_policy", "row_payload_at_snapshot_proven",
                                "kickoff_utc", "feature_cutoff_utc", "mode", "availability_class",
                                "target_prematch_snapshot_certified", "training_allowed", "features",
                                "missing_flags", "lineage", "accepted_predecessor_count",
                                "excluded", "note", "source_evidence", "feature_availability", "sha256"))


def _hash(payload):
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _utc(value):
    if not isinstance(value, str):
        raise Step14BridgeError("MISSING_UTC")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Step14BridgeError("INVALID_UTC") from exc
    if d.tzinfo is None or d.utcoffset().total_seconds() != 0:
        raise Step14BridgeError("NOT_UTC")
    return d.astimezone(timezone.utc)


def inspect_step11_contract(snapshot):
    """Verify full native-observed Step11 evidence and export only hashes.

    Does NOT certify historical PIT or make the source training-eligible.
    """
    if type(snapshot) is not dict or set(snapshot) != STEP11_OUTPUT_KEYS:
        raise Step14BridgeError("STEP11_SCHEMA_OR_EXTRA_TARGET_FIELD")
    if snapshot.get("schema") != SCHEMA or snapshot.get("mode") != "observed":
        raise Step14BridgeError("STEP11_NOT_OBSERVED_SCHEMA")
    if (snapshot.get("training_allowed") is not False or
        snapshot.get("target_prematch_snapshot_certified") is not False or
        snapshot.get("availability_class") != "OBSERVED_AT_NOT_CERTIFIED" or
        snapshot.get("row_payload_at_snapshot_proven") is not True):
        raise Step14BridgeError("STEP11_UNAPPROVED_TRAINING_OR_PIT_FLAG")
    signature = snapshot["sha256"]
    if not isinstance(signature, str) or len(signature) != 64 or signature != _hash(
            {k: v for k, v in snapshot.items() if k != "sha256"}):
        raise Step14BridgeError("STEP11_SNAPSHOT_SHA_MISMATCH")
    if type(snapshot["fixture_id"]) not in (int, str) or not snapshot["fixture_id"]:
        raise Step14BridgeError("INVALID_FIXTURE_ID")
    cutoff, kickoff = _utc(snapshot["feature_cutoff_utc"]), _utc(snapshot["kickoff_utc"])
    if cutoff >= kickoff:
        raise Step14BridgeError("CUTOFF_NOT_BEFORE_KICKOFF")
    evidence = snapshot.get("source_evidence")
    if not isinstance(evidence, dict) or not set(evidence) <= SOURCE_KEYS:
        raise Step14BridgeError("UNKNOWN_SOURCE_PROVENANCE")
    if (evidence.get("provider") != "PitchAPI" or evidence.get("native_ids_only") is not True or
        evidence.get("hash_chain_verified") is not True or
        evidence.get("source_first_publication_time_known") is not False or
        evidence.get("historical_pit_certified") is not False or
        evidence.get("training_allowed") is not False):
        raise Step14BridgeError("UNVERIFIED_SOURCE_CONTRACT")
    if not isinstance(evidence.get("source_chain_sha256"), str) or len(evidence["source_chain_sha256"]) != 64:
        raise Step14BridgeError("INVALID_CHAIN_HASH")
    observed = _utc(evidence.get("source_observed_at_utc"))
    if observed > cutoff:
        raise Step14BridgeError("SOURCE_AFTER_CUTOFF")
    features, flags, proofs = snapshot["features"], snapshot["missing_flags"], snapshot["feature_availability"]
    if not isinstance(features, dict) or set(features) != EXPECTED_FEATURES:
        raise Step14BridgeError("STEP11_FEATURE_KEY_MISMATCH_OR_ODDS")
    if not isinstance(flags, dict) or set(flags) != EXPECTED_MISSING:
        raise Step14BridgeError("STEP11_MISSING_FLAG_MISMATCH")
    if not isinstance(proofs, dict) or set(proofs) != EXPECTED_PROOFS:
        raise Step14BridgeError("STEP11_PER_FIELD_PROOF_MISSING")
    for key, val in features.items():
        if val is not None and (type(val) not in (int, float) or not math.isfinite(val)):
            raise Step14BridgeError("INVALID_STEP11_FEATURE_VALUE")
    if any(type(v) is not bool for v in flags.values()):
        raise Step14BridgeError("STEP11_NON_BOOLEAN_MISSING_FLAG")
    for name in EXPECTED_PROOFS:
        obj = proofs[name]
        if not isinstance(obj, dict) or set(obj) != PROOF_KEYS:
            raise Step14BridgeError("INCOMPLETE_FEATURE_PROOF")
        if (obj["evidence_class"] != "OBSERVED_AT_NOT_PROVIDER_PUBLISHED" or
            obj["provider_original_published_at_utc"] is not None or
            obj["training_allowed"] is not False):
            raise Step14BridgeError("PROOF_MISREPRESENTS_PROVIDER_TIME")
        stamp = _utc(obj["latest_required_observed_at_utc"])
        if not observed <= stamp <= cutoff:
            raise Step14BridgeError("FEATURE_PROOF_OUTSIDE_ASOF")
        if (type(obj["included_games"]) is not int or obj["included_games"] < 0 or
            not isinstance(obj["kind"], str) or not obj["kind"] or
            not isinstance(obj["fixtures_sha256"], str) or len(obj["fixtures_sha256"]) != 64):
            raise Step14BridgeError("INVALID_FEATURE_LINEAGE")
    for side in ("home", "away"):
        for n in (5, 10, 15):
            for context in ("all", "venue"):
                prefix = f"{side}_{context}_{n}"
                games = features[prefix + "_n"]
                if type(games) is not int or not 0 <= games <= n:
                    raise Step14BridgeError("INVALID_HISTORY_WINDOW")
                for suffix in ("xg", "xga"):
                    covered = features[prefix + "_" + suffix + "_n"]
                    average = features[prefix + "_" + suffix + "_avg"]
                    missing = flags[prefix + "_" + suffix]
                    if (type(covered) is not int or not 0 <= covered <= games or
                        (covered == 0) != (average is None) or
                        missing is not (covered < games or games == 0)):
                        raise Step14BridgeError("INVALID_PARTIAL_XG_MISSINGNESS")
    selected_hash = _hash({"features": {k: features[k] for k in SELECTED},
                           "missing_flags": {k: flags[k] for k in FLAGS}})
    return {"contract": "KB3_STEP14_STEP11_READ_ONLY_BRIDGE_V1",
            "step11_schema": SCHEMA, "step11_snapshot_sha256": signature,
            "fixture_id_sha256": _hash(str(snapshot["fixture_id"])),
            "selected_feature_names": list(SELECTED), "missing_flag_names": list(FLAGS),
            "selected_feature_values_sha256": selected_hash,
            "full_feature_count": len(features), "full_missing_flag_count": len(flags),
            "full_provenance_count": len(proofs),
            "feature_values_exported": False, "target_label_exported": False,
            "source_observation_is_historical_pit": False,
            "step14_real_fit_permitted": False, "model_promoted": False,
            "gate14_pass": False}
