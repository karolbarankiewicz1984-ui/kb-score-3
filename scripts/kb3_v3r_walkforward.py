"""KB Score V3-R: strictly isolated chronological retrospective research.

No API calls, no claim of historical PitchAPI first-publication proof,
no original 159-field M1 fit, no protected English TEST, no production writes.
The historical observations may be later provider revisions: results are
hypothesis-generating until genuinely forward-frozen evaluation is available.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import timedelta
import json
from pathlib import Path

from scripts.kb3_p1_historical_eligibility_split import (
    LEAGUES, SOURCE_DB, RECHECK_DB, hash_json, utc,
)
from scripts.kb3_p1_retro_catboost_1007_376 import (
    BASE, WITH_XG, CLASSES, PARAMS, load_sets, research_fit, execute,
)
from src.kb3_step14_m1_math_calibration import score_predictions

SCHEMA = "kb3-v3r-chronological-research-walkforward-v1"
EMBARGO_DAYS = 7
BOUNDARIES = (0.55, 0.75)
MIN_TRAIN = 100
MIN_VALIDATION = 20


class ResearchSafetyError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ResearchSafetyError(reason)


def chronological_folds(rows):
    """Two expanding-origin tests using ONLY original research TRAIN rows.

    The existing research VALIDATION is untouched until the final, separately
    scored historical check. This does not create a prospectively frozen test.
    Equal kickoff instants always stay in the same validation interval.
    """
    require(isinstance(rows, list) and len(rows) >= 2 * MIN_TRAIN,
            "INSUFFICIENT_RESEARCH_TRAIN")
    require(all(r.get("partition") == "TRAIN" and
                r.get("league") in LEAGUES and r.get("league") != "ENG"
                for r in rows), "PROTECTED_OR_VALIDATION_INPUT")
    keys = [(r["league"], str(r["fixture_id"])) for r in rows]
    require(len(keys) == len(set(keys)), "DUPLICATE_TRAIN_FIXTURE")
    ordered = sorted(rows, key=lambda r: (
        utc(r["kickoff_utc"]), r["league"], str(r["fixture_id"])))
    times = [utc(r["kickoff_utc"]) for r in ordered]
    boundaries = [times[int(len(times)*fraction)] for fraction in BOUNDARIES]
    require(boundaries[0] < boundaries[1], "NON_DISTINCT_FOLD_BOUNDARIES")
    embargo = timedelta(days=EMBARGO_DAYS)
    folds = []
    prior_validation_ids = set()
    for i, first in enumerate(boundaries):
        last = boundaries[i+1] if i+1 < len(boundaries) else None
        train = [r for r in ordered if utc(r["kickoff_utc"]) + embargo <= first]
        validation = [r for r in ordered
                      if first <= utc(r["kickoff_utc"]) and
                      (last is None or utc(r["kickoff_utc"]) < last)]
        require(len(train) >= MIN_TRAIN and len(validation) >= MIN_VALIDATION,
                "FOLD_TOO_SMALL")
        require(utc(train[-1]["kickoff_utc"]) + embargo <=
                utc(validation[0]["kickoff_utc"]), "EMBARGO_BROKEN")
        ids = {(r["league"], str(r["fixture_id"])) for r in validation}
        require(not (ids & prior_validation_ids), "FOLDS_OVERLAP")
        prior_validation_ids.update(ids)
        require(set(r["label"] for r in train) == set(CLASSES),
                "ALL_CLASSES_REQUIRED_IN_FOLD_TRAIN")
        folds.append((train, validation, {
            "fold": i+1,
            "training_n": len(train),
            "validation_n": len(validation),
            "last_train_kickoff_utc": train[-1]["kickoff_utc"],
            "first_validation_kickoff_utc": validation[0]["kickoff_utc"],
            "last_validation_kickoff_utc": validation[-1]["kickoff_utc"],
            "embargo_days": EMBARGO_DAYS,
            "training_identity_sha256": hash_json(keys_for(train)),
            "validation_identity_sha256": hash_json(keys_for(validation)),
        }))
    return folds


def keys_for(rows):
    return sorted([r["league"], str(r["fixture_id"])]
                  for r in rows)


def laplace_baseline(train, validation):
    freq = Counter(x["label"] for x in train)
    probs = {k: (freq[k]+1)/(len(train)+len(CLASSES)) for k in CLASSES}
    return [probs.copy() for _ in validation]


def run(outdir, *, db_path=SOURCE_DB, recheck_path=RECHECK_DB):
    """Read-only against source DB; write only a caller-chosen new temp dir."""
    root = Path(outdir)
    require(not root.exists(), "APPEND_ONLY_OUTPUT_PATH_REQUIRED")
    train, validation, source = load_sets(db_path, recheck_path)
    require(all(r["partition"] == "VALIDATION" for r in validation),
            "FINAL_VALIDATION_PARTITION_DRIFT")
    folds = chronological_folds(train)
    root.mkdir(parents=True, exist_ok=False)
    summaries = []
    for fold_train, fold_val, meta in folds:
        folder = root / ("fold_%d" % meta["fold"])
        folder.mkdir()
        y = [r["label"] for r in fold_val]
        outcome = {
            "TRAIN_ONLY_LAPLACE": score_predictions(
                laplace_baseline(fold_train,fold_val), y)}
        for name, features in (
            ("CATBOOST_NO_XG", BASE),
            ("CATBOOST_PLUS_RETROSPECTIVE_XG", WITH_XG)):
            predictions, _ = research_fit(
                fold_train, fold_val, features, folder/(name+".cbm"))
            outcome[name] = score_predictions(predictions, y)
        summaries.append({**meta, "variants": outcome,
            "retrospective_only": True, "no_model_promotion": True})
    # Existing full cohort comparison is run ONCE, without reusing fold
    # models, fitting on original VALIDATION, or reading protected TEST.
    final = execute(root / "original_validation",
                    db_path=db_path, recheck_path=recheck_path)
    require(final["train_n"] == len(train) and
            final["validation_n"] == len(validation) and
            final["official_fit_increment"] == 0 and
            final["model_champion_auto_promoted"] is False and
            final["original_historical_provider_first_published_certified"] is False,
            "FINAL_RESEARCH_GUARDS_FAILED")
    report = {
        "schema": SCHEMA,
        "experiment": "V3-R_CHRONOLOGICAL_RECONSTRUCTION_NOT_ORIGINAL_V3",
        "source_class": "RETROSPECTIVE_REVISIONS_FIRST_PUBLICATION_UNKNOWN",
        "feature_sets": {
            "NO_XG": list(BASE), "WITH_RETROSPECTIVE_XG": list(WITH_XG)},
        "fixed_classifier_params": PARAMS,
        "source_provenance": source,
        "original_research_train_n": len(train),
        "original_research_validation_n": len(validation),
        "folds_from_training_only": summaries,
        "final_original_validation_report_sha256": final["report_sha256"],
        "final_original_validation_metrics": {
            name: final["variants"][name]["metrics"] for name in (
                "TRAIN_ONLY_MARGINAL_LAPLACE", "CATBOOST_RESEARCH_NO_XG",
                "CATBOOST_RESEARCH_PLUS_XG_WITH_MISSING")},
        "historical_feature_cutoff": "hypothetical kickoff minus 2h",
        "predecessor_result_lag_enforced_by_source_builder": True,
        "fold_embargo_days": EMBARGO_DAYS,
        "future_holdout_evaluated": False,
        "actual_historic_provider_publication_certified": False,
        "original_V3_121_plus_38_gate14_modified": False,
        "original_V3_gate14_strict": "PENDING",
        "original_test_england_2026_27_accessed": False,
        "production_M0_modified": False,
        "champion_auto_promoted": False,
        "official_fit_increment": 0,
        "production_approved": False,
        "research_only": True,
    }
    report["report_sha256"] = hash_json(report)
    target = root/"V3R_WALKFORWARD_REPORT.json"
    with target.open("x", encoding="utf8") as f:
        json.dump(report, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
    print("V3R_WALKFORWARD_RESEARCH_ONLY",
          json.dumps({"folds": len(summaries),
            "train": len(train), "validation": len(validation),
            "report_sha256": report["report_sha256"],
            "original_gate14": "PENDING",
            "production_approved": False}, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    run(args.outdir)


if __name__ == "__main__":
    main()
