"""P1-01: shared as-of feature builder v2 for TRAIN and FORWARD research.

Same source-selection/feature semantics at the SAME target cutoff. This is a
new research version; it never rewrites the original M1-R (48h), Step11, M0,
or protected Premier League TEST. A later observation is not old PIT evidence.
All reported features remain non-training-approved until separate independent
source/host attestation and model governance.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import hashlib
import json
import re

from src.kb3_features import _compose_features, EloParameters, utc_dt, utc_str, digest

SCHEMA = "kb3-p1-shared-train-forward-asof-v2"
RESULT_MIN_LAG = timedelta(hours=3)
MIN_LEAD = timedelta(minutes=90)
LEAGUES = frozenset(("ESP", "ITA", "GER", "FRA", "NED", "BEL", "TUR", "POL"))
SHA = re.compile(r"^[a-f0-9]{64}$")
PURPOSES = frozenset(("TRAIN", "FORWARD"))


class SharedAsOfError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise SharedAsOfError(reason)


def when(value):
    need(type(value) is str and bool(re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value)),
         "CANONICAL_UTC_Z_REQUIRED")
    try:
        dt = utc_dt(value)
    except ValueError as exc:
        raise SharedAsOfError("INVALID_SOURCE_UTC") from exc
    need(utc_str(dt) == value.replace(".000000Z", "Z").replace(".000Z", "Z")
         or utc_str(dt).startswith(value[:-1].split(".")[0]),
         "SOURCE_UTC_NORMALIZATION_DRIFT")
    return dt


def digest_required(value):
    need(type(value) is str and bool(SHA.fullmatch(value)),
         "REAL_RECEIPT_SHA256_REQUIRED")
    return value


def clock_of(source, key):
    need(isinstance(source, dict), "SOURCE_RECEIPT_REQUIRED")
    return when(source.get(key))


def _target(target, cutoff):
    need(isinstance(target, dict), "TARGET_REQUIRED")
    need(target.get("league") in LEAGUES, "PROTECTED_OR_UNKNOWN_LEAGUE")
    need(type(target.get("fixture_id")) in (str, int) and
         str(target["fixture_id"]) != "", "TARGET_ID_REQUIRED")
    for key in ("home_team_id", "away_team_id"):
        need(type(target.get(key)) in (str, int) and str(target[key]),
             "TARGET_TEAM_ID_REQUIRED")
    need(str(target.get("home_team_id")) != str(target.get("away_team_id")),
         "TARGET_TEAMS_IDENTICAL")
    need(type(target.get("season_start_year")) is int and
         1900 <= target["season_start_year"] <= 2200,
         "TARGET_SEASON_INVALID")
    for key in ("goals_home_90", "goals_away_90", "score_home", "score_away",
                "outcome_1x2", "label", "result_1x2"):
        need(target.get(key) is None, "TARGET_LABEL_IN_FEATURE_SOURCE")
    ko = when(target.get("kickoff_utc"))
    need(cutoff <= ko - MIN_LEAD, "TARGET_EARLY_90MIN_REQUIRED")
    return ko


def _target_receipt(receipt, cutoff):
    need(isinstance(receipt, dict), "TARGET_CAPTURE_RECEIPT_REQUIRED")
    need(receipt.get("source_class") == "NETWORK_OBSERVED",
         "TARGET_RECONSTRUCTED_OR_UNOBSERVED")
    stamp = clock_of(receipt, "observed_completed_at_utc")
    need(stamp <= cutoff, "TARGET_CAPTURE_AFTER_CUTOFF")
    if receipt.get("captured_at_utc") is not None:
        need(stamp <= when(receipt["captured_at_utc"]) <= cutoff,
             "TARGET_CAPTURE_AFTER_CUTOFF")
    if receipt.get("published_at_utc") is not None:
        need(when(receipt["published_at_utc"]) <= stamp,
             "TARGET_PUBLICATION_AFTER_OBSERVATION")
    digest_required(receipt.get("source_sha256"))
    # A declared hash and clock DO NOT demonstrate independent GitHub receipt
    # or the provider's first historical publication time.
    completed = when(receipt.get("captured_at_utc", receipt["observed_completed_at_utc"]))
    return {"source_observed_at_utc": utc_str(completed),
            "source_sha256": receipt["source_sha256"],
            "source_class": "NETWORK_OBSERVED"}


def _xg_side(value, proof, predecessor_ko, cutoff, reasons):
    if value is None and proof is None:
        return None, None
    need(value is not None and proof is not None,
         "XG_VALUE_SOURCE_MISMATCH")
    need(type(value) in (float, int) and
         __import__("math").isfinite(value) and 0 <= value <= 30,
         "INVALID_XG")
    need(isinstance(proof, dict) and
         proof.get("source_class") == "NETWORK_OBSERVED",
         "XG_RECONSTRUCTED_OR_UNOBSERVED")
    observed = clock_of(proof, "observed_completed_at_utc")
    captured = clock_of(proof, "captured_at_utc")
    digest_required(proof.get("source_sha256"))
    need(observed <= captured, "XG_OBSERVED_AFTER_CAPTURE")
    published = proof.get("published_at_utc")
    if published is not None:
        pub = when(published)
        need(pub <= observed, "XG_PUBLICATION_AFTER_OBSERVATION")
    else:
        pub = None
    if (predecessor_ko + RESULT_MIN_LAG > observed or captured > cutoff or
        (pub is not None and pub > cutoff)):
        reasons["XG_SOURCE_NOT_AVAILABLE_AT_CUTOFF"] += 1
        return None, None
    # The shared Step11 aggregation takes the real observed clock; it does
    # NOT certify first provider publication, even if a timestamp is present.
    return float(value), {
        "observed_at_utc": utc_str(captured),
        "source_sha256": proof["source_sha256"]}


def _predecessor(row, target, cutoff, target_ko, reasons):
    need(isinstance(row, dict), "PREDECESSOR_ROW_REQUIRED")
    need(row.get("league") == target["league"], "CROSS_LEAGUE_HISTORY")
    need(str(row.get("fixture_id")) != str(target["fixture_id"]),
         "TARGET_RESULT_LEAK")
    for key in ("home_team_id", "away_team_id"):
        need(type(row.get(key)) in (str, int) and str(row[key]),
             "PREDECESSOR_TEAM_ID_REQUIRED")
    need(str(row.get("home_team_id")) != str(row.get("away_team_id")),
         "PREDECESSOR_TEAMS_IDENTICAL")
    need(type(row.get("season_start_year")) is int and
         row["season_start_year"] <= target["season_start_year"],
         "FUTURE_SEASON_IN_HISTORY")
    ko = when(row.get("kickoff_utc"))
    need(ko < target_ko, "FUTURE_OR_TIED_HISTORY")
    if ko >= cutoff:
        reasons["PREDECESSOR_AFTER_CUTOFF"] += 1
        return None
    if row.get("status") != "FINISHED":
        reasons["NOT_FINISHED_AT_SOURCE"] += 1
        return None
    if any(type(row.get(key)) is not int or
           not 0 <= row[key] <= 30
           for key in ("goals_home_90", "goals_away_90")):
        reasons["INVALID_90MIN_SCORE"] += 1
        return None
    receipt = row.get("result_receipt")
    need(isinstance(receipt, dict), "PREDECESSOR_RESULT_RECEIPT_REQUIRED")
    need(receipt.get("source_class") == "NETWORK_OBSERVED",
         "HISTORICAL_LATER_RECONSTRUCTION_NOT_PIT")
    observed = clock_of(receipt, "observed_completed_at_utc")
    captured = clock_of(receipt, "captured_at_utc")
    digest_required(receipt.get("source_sha256"))
    published = receipt.get("published_at_utc")
    pub = when(published) if published is not None else None
    need(observed <= captured, "RESULT_OBSERVED_AFTER_CAPTURE")
    if pub is not None:
        need(pub <= observed, "RESULT_PUBLICATION_AFTER_OBSERVATION")
    # A mutable provider result row updated AFTER the recorded snapshot
    # cannot substantiate an old score. If unknown, the attested source must
    # contain the actual result payload; separate byte audit still required.
    update = receipt.get("result_record_updated_at_utc")
    if update is not None:
        need(when(update) <= observed, "RESULT_ROW_MUTATED_AFTER_CAPTURE")
    if (ko + RESULT_MIN_LAG > observed or captured > cutoff or
        (pub is not None and pub > cutoff)):
        reasons["RESULT_NOT_AVAILABLE_AT_CUTOFF"] += 1
        return None

    xgh, xgh_source = _xg_side(
        row.get("xgh"), row.get("xgh_receipt"), ko, cutoff, reasons)
    xga, xga_source = _xg_side(
        row.get("xga"), row.get("xga_receipt"), ko, cutoff, reasons)
    return {
        "fixture_id": row["fixture_id"],
        "home_team_id": row["home_team_id"],
        "away_team_id": row["away_team_id"],
        "season_start_year": row["season_start_year"],
        "kickoff_utc": row["kickoff_utc"],
        "date": ko,
        "status": "FINISHED",
        "goals_home_90": row["goals_home_90"],
        "goals_away_90": row["goals_away_90"],
        "captured_at_utc": utc_str(captured),
        "published_at_utc": utc_str(pub) if pub else None,
        "snapshot_id": receipt["source_sha256"],
        "result_provider_name": row.get("result_provider_name"),
        "result_record_updated_at_utc": (update if update is not None
                                          else utc_str(observed)),
        "xgh": xgh, "xga": xga,
        "xgh_source": xgh_source, "xga_source": xga_source,
    }


def build_shared_features(*, purpose, target, cutoff_utc,
                          target_receipt, predecessor_rows,
                          elo_params=None):
    """Build SAME feature vector from SAME clocks in TRAIN and FORWARD.

    Missing or late verified provider receipt removes the predecessor rather
    than using 48h heuristic or silently claiming original source PIT.
    This function does NOT ingest target match label, fit models, call APIs,
    or admit a sample for formal training. It only builds candidate vectors
    subject to future independent source review.
    """
    need(purpose in PURPOSES, "PURPOSE_TRAIN_OR_FORWARD_REQUIRED")
    cutoff = when(cutoff_utc)
    target_ko = _target(target, cutoff)
    source = _target_receipt(target_receipt, cutoff)
    # Provider IDs have one canonical representation inside aggregation. In
    # particular team 123 and team "123" cannot silently become two ratings.
    target = {**target, **{key:str(target[key]) for key in
              ("fixture_id", "home_team_id", "away_team_id")}}
    need(isinstance(predecessor_rows, list), "PREDECESSORS_LIST_REQUIRED")
    params = EloParameters() if elo_params is None else elo_params
    need(isinstance(params, EloParameters), "ELO_PARAMETER_TYPE_INVALID")
    reasons = Counter()
    history = []
    seen = set()
    for row in predecessor_rows:
        need(isinstance(row, dict), "PREDECESSOR_OBJECT_REQUIRED")
        ident = row.get("fixture_id")
        need(type(ident) in (int, str) and str(ident), "BAD_PREDECESSOR_ID")
        need(str(ident) not in seen, "DUPLICATE_PREDECESSOR_ID")
        seen.add(str(ident))
        accepted = _predecessor(row, target, cutoff, target_ko, reasons)
        if accepted is not None:
            for key in ("fixture_id", "home_team_id", "away_team_id"):
                accepted[key] = str(accepted[key])
            history.append(accepted)
    view = _compose_features(
        {"home_team_id": target["home_team_id"],
         "away_team_id": target["away_team_id"],
         "season_start_year": target["season_start_year"]},
        history, cutoff=cutoff, kickoff=target_ko,
        target_id=target["fixture_id"], mode="observed",
        params=params, excluded=reasons,
        source_evidence=source)
    # Elo has transitive opponent dependencies. A team's earlier rating can
    # depend on games it never played itself. Conservatively bind Elo fields
    # to ALL accepted result receipts, without changing the M0 clock mapper.
    if history:
        latest = max(when(r["captured_at_utc"]) for r in history)
        ids_sha = digest(sorted(str(r["fixture_id"]) for r in history))
        for key, clock in view["feature_availability"].items():
            if "elo" in key:
                clock["latest_required_observed_at_utc"] = utc_str(max(
                    when(clock["latest_required_observed_at_utc"]), latest))
                clock["fixtures_sha256"] = ids_sha
                clock["included_games"] = len(history)
                clock["kind"] = "ELO_TRANSITIVE_ALL_ACCEPTED_RESULTS"
    for key in view["missing_flags"]:
        if key.endswith(("_xg", "_xga")):
            value_clock = view["feature_availability"][key+"_avg"]
            view["feature_availability"]["missing:"+key][
                "latest_required_observed_at_utc"] = value_clock[
                    "latest_required_observed_at_utc"]
    # Purpose not in the feature hash: changing only TRAIN <-> FORWARD must
    # never create a different prediction feature vector at an identical as-of.
    canonical = {
        "schema": SCHEMA,
        "target_fixture_id": target["fixture_id"],
        "league": target["league"],
        "target_kickoff_utc": utc_str(target_ko),
        "feature_cutoff_utc": utc_str(cutoff),
        "elo_parameters": view["elo_parameters"],
        "features": view["features"],
        "missing_flags": view["missing_flags"],
        "lineage": view["lineage"],
        "feature_availability": view["feature_availability"],
        "accepted_predecessor_count": view["accepted_predecessor_count"],
        "excluded": view["excluded"],
        "target_receipt": source,
        "original_provider_first_published_at_certified": False,
        "independent_receipt_bytes_verified": False,
        "training_allowed": False,
        "production_approved": False,
        "feature_contract_equal_for_train_and_forward": True,
    }
    canonical_sha = digest(canonical)
    return {**canonical, "purpose": purpose, "canonical_features_sha256": canonical_sha,
            "research_only": True,
            "note": ("Real as-of capture clocks; not independently attested "
                     "source byte availability or original historical PIT.")}


def compare_same_asof(train, forward):
    """Fail closed if v2 candidate TRAIN and FORWARD differ in any canonical byte."""
    need(isinstance(train, dict) and isinstance(forward, dict),
         "PAIR_OBJECTS_REQUIRED")
    need(train.get("purpose") == "TRAIN" and forward.get("purpose") == "FORWARD",
         "WRONG_PAIR_PURPOSE")
    for sample in (train, forward):
        need(sample.get("schema") == SCHEMA, "CONTRACT_VERSION_MISMATCH")
        need(sample.get("training_allowed") is False and
             sample.get("production_approved") is False,
             "UNAUTHORIZED_MODEL_APPROVAL")
    left = {k:v for k,v in train.items()
            if k not in ("purpose","canonical_features_sha256","research_only","note")}
    right = {k:v for k,v in forward.items()
             if k not in ("purpose","canonical_features_sha256","research_only","note")}
    need(left == right, "TRAIN_FORWARD_FEATURE_CONTRACT_DRIFT")
    need(digest(left) == train.get("canonical_features_sha256") ==
         forward.get("canonical_features_sha256"), "FEATURE_HASH_MISMATCH")
    return {"contract": SCHEMA, "canonical_features_sha256": digest(left),
            "same_asof_feature_parity": True, "training_allowed": False,
            "gate16": "PENDING", "gate17": "PENDING"}


def candidate_m1r_85_schema_bridge(view, frozen_audit):
    """Read-only SHAPE comparison with old M1-R 85 names, NOT old-model parity.

    Existing M1-R was trained with +48h historical semantics, therefore a
    85-column shape match NEVER authorizes passing these v2 values to its
    frozen trained weights or declaring calibrated prediction quality.
    Missing numbers are JSON null, never invented zero; a later independent
    training adapter can decide a model-specific NaN representation.
    """
    need(isinstance(view, dict) and view.get("schema") == SCHEMA,
         "ASOF_V2_SOURCE_REQUIRED")
    need(view.get("training_allowed") is False and
         view.get("production_approved") is False,
         "UNAUTHORIZED_SOURCE_APPROVAL")
    need(isinstance(frozen_audit, dict) and
         frozen_audit.get("frozen_feature_count") == 85 and
         frozen_audit.get("training") == 720 and
         frozen_audit.get("validation") == 374,
         "ORIGINAL_M1R_AUDIT_MISMATCH")
    names = frozen_audit.get("frozen_feature_names")
    need(isinstance(names, list) and len(names) == 85 and
         len(set(names)) == 85, "ORIGINAL_85_FEATURE_SCHEMA_INVALID")
    need(frozen_audit.get("original_TEST_2026_27_never_requested") is True,
         "ORIGINAL_TEST_PROTECTION_MISSING")
    need(frozen_audit.get("future_actual_PIT_certified") is False,
         "FALSE_OLD_PIT_CERTIFICATION")
    typed = []
    for name in names:
        need(type(name) is str and name.count(":") == 1,
             "MODEL_FEATURE_NAME_INVALID")
        kind, key = name.split(":")
        need(kind in ("num","miss"), "MODEL_FEATURE_KIND_UNKNOWN")
        source = view["features"] if kind == "num" else view["missing_flags"]
        need(key in source, "MODEL_REQUIRED_FEATURE_NOT_IN_V2_" + key)
        value = source[key]
        if kind == "miss":
            need(type(value) is bool, "INVALID_V2_MISSING_MASK_" + key)
            typed.append(int(value))
        elif value is None:
            typed.append(None)
        else:
            import math
            need(type(value) in (int, float) and math.isfinite(value),
                 "INVALID_V2_NUMERIC_" + key)
            typed.append(float(value))
    columns = {"schema": "kb3-p1-shared-asof-v2-m1r85-shape-bridge",
               "contract_sha256": view["canonical_features_sha256"],
               "fixture_id": view["target_fixture_id"],
               "purpose": view["purpose"],
               "feature_names": names, "candidate_values": typed,
               "feature_count": len(names),
               "missing_numeric": sum(
                   kind.startswith("num:") and value is None
                   for kind, value in zip(names,typed)),
               "same_names_not_same_old_training_semantics": True,
               "safe_to_score_with_frozen_original_m1r": False,
               "new_model_retrain_required": True,
               "training_allowed": False, "production_approved": False}
    columns["sha256"] = digest(columns)
    return columns


def require_paired_catboost_85_contract(train_view, forward_view, frozen_audit):
    """Research-only strict 85-column TRAIN/FORWARD parity gate.

    Rejects mixed historical 48h M1-R and forward 3h semantics: both views
    must come from this same as-of v2 builder at an identical cutoff.
    Shape parity is NOT permission to reuse original fitted M1-R weights.
    """
    parity = compare_same_asof(train_view, forward_view)
    train = candidate_m1r_85_schema_bridge(train_view, frozen_audit)
    forward = candidate_m1r_85_schema_bridge(forward_view, frozen_audit)
    need(train["feature_names"] == forward["feature_names"],
         "CATBOOST_FEATURE_ORDER_DRIFT")
    need(train["candidate_values"] == forward["candidate_values"],
         "CATBOOST_TRAIN_FORWARD_VALUES_DRIFT")
    need(train["contract_sha256"] == forward["contract_sha256"] ==
         parity["canonical_features_sha256"], "CATBOOST_ASOF_HASH_DRIFT")
    return {"schema":"kb3-catboost-asof-v2-85-parity-gate-v1",
            "feature_count":85,"contract_sha256":parity["canonical_features_sha256"],
            "same_asof_train_forward":True,"feature_names_and_order_equal":True,
            "feature_values_equal":True,"original_m1r_48h_weights_reusable":False,
            "new_model_retrain_required":True,"training_allowed":False,
            "production_approved":False}
