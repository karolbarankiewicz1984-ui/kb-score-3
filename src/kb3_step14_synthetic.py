"""KB3 step14: fail-closed feature contract and SYNTHETIC CatBoost CPU smoke test.

No API, no archive access, no real fitting, no TEST, no odds, no production.
Generated in-code examples are not evidence of real PIT or predictive quality.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory


class Step14SafetyError(ValueError):
    pass


LABELS = ("1", "X", "2")
BASE = ("elo_home_minus_away", "home_all_5_points_avg", "away_all_5_points_avg")
XG = ("home_all_5_xg_avg", "away_all_5_xg_avg")
MASK = ("home_all_5_xg_missing", "away_all_5_xg_missing")
FEATURES = BASE + XG + MASK
ROW_KEYS = frozenset(("fixture_id", "kickoff_utc", "feature_cutoff_utc",
                      "source_observed_at_utc", "partition", "evidence_class",
                      "features", "feature_availability", "label_1x2"))
SEED = 141027


def _dt(value):
    if not isinstance(value, str):
        raise Step14SafetyError("INVALID_UTC_TIMESTAMP")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Step14SafetyError("INVALID_UTC_TIMESTAMP") from exc
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise Step14SafetyError("TIMESTAMP_MUST_BE_UTC")
    return result


def _number(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in (int, float) or not math.isfinite(value):
        raise Step14SafetyError("INVALID_NUMERIC_FEATURE")


def validate_row(row):
    """Strict synthetic-only schema; this does NOT authorize real training."""
    if not isinstance(row, dict) or set(row) != ROW_KEYS:
        raise Step14SafetyError("UNKNOWN_OR_MISSING_FIELDS_POSSIBLE_LEAK")
    if row["evidence_class"] != "SYNTHETIC_CODE_GENERATED_ONLY":
        raise Step14SafetyError("REAL_FIT_BLOCKED_NO_PIT_CERTIFICATE")
    if row["partition"] not in ("SYNTH_TRAIN", "SYNTH_VALIDATION"):
        raise Step14SafetyError("VALIDATION_OR_TEST_NOT_FOR_TRAINING")
    if row["label_1x2"] not in LABELS:
        raise Step14SafetyError("INVALID_SYNTHETIC_LABEL")
    if not isinstance(row["fixture_id"], str) or not row["fixture_id"].startswith("SYNTH14_"):
        raise Step14SafetyError("INVALID_SYNTHETIC_FIXTURE")
    observed = _dt(row["source_observed_at_utc"])
    cutoff = _dt(row["feature_cutoff_utc"])
    kickoff = _dt(row["kickoff_utc"])
    if not observed <= cutoff < kickoff:
        raise Step14SafetyError("FEATURE_FROM_FUTURE_OR_LATE_SOURCE")
    feats, times = row["features"], row["feature_availability"]
    if not isinstance(feats, dict) or set(feats) != set(FEATURES):
        raise Step14SafetyError("UNKNOWN_FEATURE_OR_ODDS")
    if not isinstance(times, dict) or set(times) != set(FEATURES):
        raise Step14SafetyError("FEATURE_TIME_MISSING")
    for name in FEATURES:
        if not observed <= _dt(times[name]) <= cutoff:
            raise Step14SafetyError("FEATURE_FROM_FUTURE_OR_LATE_SOURCE")
        if name in MASK:
            if type(feats[name]) is not bool:
                raise Step14SafetyError("INVALID_MISSING_MASK")
        else:
            _number(feats[name], nullable=name in XG)
    for value_name, mask_name in zip(XG, MASK):
        if (feats[value_name] is None) is not feats[mask_name]:
            raise Step14SafetyError("MISSING_XG_MUST_REMAIN_NULL")
    return True


def synthetic_rows():
    """Only internal fabricated examples; cannot be overridden by external rows."""
    rows = []
    for partition, count, start in (("SYNTH_TRAIN", 90, datetime(2024, 1, 1, tzinfo=timezone.utc)),
                                    ("SYNTH_VALIDATION", 30, datetime(2025, 1, 1, tzinfo=timezone.utc))):
        for i in range(count):
            kickoff = start + timedelta(days=i)
            observed = kickoff - timedelta(days=3)
            cutoff = kickoff - timedelta(days=2)
            edge = ((i * 7) % 31 - 15) * 9.0
            missing_home, missing_away = i % 5 == 0, i % 7 == 0
            features = {
                "elo_home_minus_away": edge,
                "home_all_5_points_avg": ((i * 3) % 14) / 5,
                "away_all_5_points_avg": ((i * 5) % 14) / 5,
                "home_all_5_xg_avg": None if missing_home else 0.7 + (i % 11) / 10,
                "away_all_5_xg_avg": None if missing_away else 0.6 + (i % 9) / 10,
                "home_all_5_xg_missing": missing_home,
                "away_all_5_xg_missing": missing_away,
            }
            stamp = observed.isoformat().replace("+00:00", "Z")
            rows.append({
                "fixture_id": f"SYNTH14_{partition}_{i:03d}",
                "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                "feature_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
                "source_observed_at_utc": stamp,
                "partition": partition,
                "evidence_class": "SYNTHETIC_CODE_GENERATED_ONLY",
                "features": features,
                "feature_availability": {k: stamp for k in FEATURES},
                "label_1x2": LABELS[(i + (i // 5)) % 3],
            })
    validate_dataset(rows)
    return rows


def validate_dataset(rows):
    if not isinstance(rows, list) or len(rows) != 120:
        raise Step14SafetyError("SYNTHETIC_DATASET_SIZE_CHANGED")
    seen = set()
    for row in rows:
        validate_row(row)
        if row["fixture_id"] in seen:
            raise Step14SafetyError("DUPLICATE_FIXTURE")
        seen.add(row["fixture_id"])
    train = [r for r in rows if r["partition"] == "SYNTH_TRAIN"]
    valid = [r for r in rows if r["partition"] == "SYNTH_VALIDATION"]
    if len(train) != 90 or len(valid) != 30:
        raise Step14SafetyError("WRONG_SPLIT")
    if max(_dt(r["kickoff_utc"]) for r in train) >= min(_dt(r["kickoff_utc"]) for r in valid):
        raise Step14SafetyError("CHRONOLOGY_LEAK")
    if set(r["label_1x2"] for r in train) != set(LABELS):
        raise Step14SafetyError("MISSING_CLASS")
    return train, valid


def _matrix(rows, use_xg):
    names = FEATURES if use_xg else BASE
    return [[float("nan") if r["features"][k] is None else float(r["features"][k])
             for k in names] for r in rows], names


def run_synthetic_catboost(*, use_xg=False):
    """Real CPU engine, fake generated records. Never accepts real data paths."""
    try:
        from catboost import CatBoostClassifier, Pool
    except ImportError as exc:
        raise Step14SafetyError("CATBOOST_NOT_INSTALLED") from exc
    rows = synthetic_rows()
    train, valid = validate_dataset(rows)
    x_train, names = _matrix(train, use_xg)
    x_valid, _ = _matrix(valid, use_xg)
    config = dict(iterations=36, depth=3, learning_rate=0.08,
                  loss_function="MultiClass", random_seed=SEED, thread_count=1,
                  allow_writing_files=False, verbose=False)
    model = CatBoostClassifier(**config)
    model.fit(Pool(x_train, [r["label_1x2"] for r in train], feature_names=list(names)))
    raw = model.predict_proba(x_valid)
    classes = [str(v) for v in model.classes_]
    if set(classes) != set(LABELS):
        raise Step14SafetyError("MODEL_CLASSES_CHANGED")
    logloss, brier = 0.0, 0.0
    for probabilities, row in zip(raw, valid):
        p = {label: float(probabilities[classes.index(label)]) for label in LABELS}
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in p.values()) or abs(sum(p.values()) - 1) > 1e-9:
            raise Step14SafetyError("PROBABILITIES_NOT_NORMALIZED")
        logloss -= math.log(max(p[row["label_1x2"]], 1e-15)) / len(valid)
        brier += sum((p[label] - (label == row["label_1x2"])) ** 2 for label in LABELS) / len(valid)
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False)
    # Check that .cbm can be reloaded and returns the *same* class probabilities.
    # This does not validate real forecasting performance.
    with TemporaryDirectory(prefix="kb3_step14_synthetic_") as work:
        destination = Path(work) / "NOT_FOR_PRODUCTION.cbm"
        model.save_model(str(destination))
        model_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        restored = CatBoostClassifier()
        restored.load_model(str(destination))
        restored_classes = [str(v) for v in restored.classes_]
        if restored_classes != classes:
            raise Step14SafetyError("CBM_RELOAD_CLASS_ORDER_CHANGED")
        roundtrip = restored.predict_proba(Pool(x_valid, feature_names=list(names)))
        max_roundtrip_error = max(
            abs(float(a) - float(b))
            for original, reloaded in zip(raw, roundtrip)
            for a, b in zip(original, reloaded)
        )
        if max_roundtrip_error > 1e-12:
            raise Step14SafetyError("CBM_RELOAD_PROBABILITIES_DIFFER")
    return {
        "experiment": "KB3_STEP14_CPU_SYNTHETIC_ONLY",
        "feature_variant": "WITH_XG_MASKS" if use_xg else "NO_XG",
        "feature_names": list(names), "seed": SEED, "config": config,
        "synthetic_data_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "ephemeral_synthetic_model_sha256": model_hash,
        "cbm_reload_checked": True,
        "cbm_reload_max_absolute_probability_difference": max_roundtrip_error,
        "synthetic_train_count": len(train), "synthetic_validation_count": len(valid),
        "synthetic_log_loss": logloss, "synthetic_brier_sum3": brier,
        "synthetic_pipeline_ready": True,
        "real_data_training_eligible": False, "historical_pit_certified": False,
        "production_approved": False, "real_data_read": False,
        "test_labels_read": 0, "odds_fields_used": 0, "network_requests": 0,
        "gate14_pass": False,
    }


if __name__ == "__main__":
    print(json.dumps([run_synthetic_catboost(use_xg=False),
                      run_synthetic_catboost(use_xg=True)], sort_keys=True, indent=2))
