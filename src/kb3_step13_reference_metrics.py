"""Step13: reference evaluation formulas ONLY; no historical scoring authority.

Historical backtests require source receipts proving pre-match prediction
freeze and correct result availability. This isolated module cannot read the
real archive, and only accepts explicitly declared SYNTHETIC_REFERENCE inputs.
"""
from __future__ import annotations
import math
from src.kb3_step13_baseline import BaselineSafetyError

LABEL_TO_PROBABILITY_KEY = {"H": "1", "D": "X", "A": "2"}


def score_synthetic_reference(rows, *, mode):
    """Evaluate artificially constructed unit-test examples only.

    Multiclass Brier uses sum over 3 outcomes (range 0..2), averaged across N.
    Top-class ECE: 5 fixed bins, [0,0.2), ..., [0.8,1].
    No real fixture ID, odds, or provider receipts are accepted here.
    """
    if mode != "SYNTHETIC_REFERENCE_ONLY":
        raise BaselineSafetyError("STEP13_HISTORICAL_EVAL_NOT_CERTIFIED")
    if not isinstance(rows, list) or not rows:
        raise BaselineSafetyError("STEP13_REFERENCE_ROWS_REQUIRED")
    total_log, total_brier = 0.0, 0.0
    bins = [{"n": 0, "confidence_sum": 0.0, "accuracy_sum": 0.0}
            for _ in range(5)]
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"probabilities", "label"}:
            raise BaselineSafetyError("STEP13_REFERENCE_SCHEMA_ONLY")
        ps = row["probabilities"]
        label = row["label"]
        if label not in LABEL_TO_PROBABILITY_KEY or not isinstance(ps, dict) or set(ps) != {"1", "X", "2"}:
            raise BaselineSafetyError("STEP13_REFERENCE_LABEL_OR_KEYS_INVALID")
        vals = list(ps.values())
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1
               for v in vals):
            raise BaselineSafetyError("STEP13_REFERENCE_PROB_INVALID")
        if abs(math.fsum(vals) - 1.0) > 1e-10:
            raise BaselineSafetyError("STEP13_REFERENCE_PROBS_NOT_NORMALIZED")
        truth = LABEL_TO_PROBABILITY_KEY[label]
        p_truth = ps[truth]
        total_log += -math.log(max(p_truth, 1e-15))
        total_brier += math.fsum(
            (ps[k] - (1.0 if k == truth else 0.0)) ** 2
            for k in ("1", "X", "2"))
        predicted = max(("1", "X", "2"), key=lambda k: ps[k])
        confidence = ps[predicted]
        slot = min(4, int(confidence * 5))
        bins[slot]["n"] += 1
        bins[slot]["confidence_sum"] += confidence
        bins[slot]["accuracy_sum"] += 1.0 if predicted == truth else 0.0
    n = len(rows)
    ece = sum(abs(x["accuracy_sum"] / x["n"] - x["confidence_sum"] / x["n"])
              * x["n"] / n for x in bins if x["n"])
    return {
        "reference_type": "SYNTHETIC_ONLY_NOT_HISTORICAL",
        "sample_size": n,
        "multiclass_log_loss": total_log / n,
        "multiclass_brier_sum3": total_brier / n,
        "top_class_ece_5bins": ece,
        "calibration_bins": [{
            "low_inclusive": i / 5,
            "high_exclusive_except_last": (i+1)/5,
            "sample_size": r["n"],
            "mean_confidence": r["confidence_sum"] / r["n"] if r["n"] else None,
            "observed_top_class_accuracy": r["accuracy_sum"] / r["n"] if r["n"] else None,
        } for i, r in enumerate(bins)],
        "empirical_historical_performance": False,
        "training_allowed": False,
    }
