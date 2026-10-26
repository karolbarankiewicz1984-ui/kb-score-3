"""Step13 M0: deterministic, event-time-correct SYNTHETIC fold replay.

The only accepted input is a tagged synthetic fixture set with SYN- IDs.
Predictions are computed at each simulated kickoff; labels update Elo ONLY
after their independently specified observation time. No bookmaker odds,
provider keys, real historical fixtures, PIT certifications or model fitting.

This exercises the future real-evaluation control flow, not historical skill.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import heapq
import math

from src.kb3_split import SplitSafetyError, timestamp, WINDOWS, WALK_FORWARD, sha
from src.kb3_step13_baseline import BaselineParameters, forecast, update_elo
from src.kb3_step13_reference_metrics import score_synthetic_reference


SCHEMA = "kb3-step13-synthetic-fold-replay-v0.2"
FIELDS = frozenset((
    "fixture_id", "home_team_id", "away_team_id", "kickoff_utc",
    "result_observed_at_utc", "label_90m", "partition",
))
METHODS = ("EXPANDING", "ROLLING_24_CALENDAR_MONTHS")
MINIMUM_RESULT_LAG = timedelta(hours=3)


def _validated_synthetic_rows(source):
    if not isinstance(source, dict) or set(source) != {"dataset_kind", "fixtures"}:
        raise SplitSafetyError("STEP13_REPLAY_SYNTHETIC_SCHEMA_REQUIRED")
    if source["dataset_kind"] != "SYNTHETIC_REFERENCE_ONLY":
        raise SplitSafetyError("STEP13_REPLAY_REAL_DATA_DENIED")
    rows = source["fixtures"]
    if not isinstance(rows, list) or len(rows) == 0:
        raise SplitSafetyError("STEP13_REPLAY_EMPTY_SYNTHETIC_SOURCE")
    found = set()
    checked = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise SplitSafetyError("STEP13_REPLAY_OUTCOME_OR_ODDS_TAINT")
        fid = row["fixture_id"]
        home, away = row["home_team_id"], row["away_team_id"]
        if not isinstance(fid, str) or not fid.startswith("SYN-MATCH-") or fid in found:
            raise SplitSafetyError("STEP13_REPLAY_NON_SYNTHETIC_OR_DUPLICATE_ID")
        if (not isinstance(home, str) or not isinstance(away, str)
                or not home.startswith("SYN-TEAM-")
                or not away.startswith("SYN-TEAM-") or home == away):
            raise SplitSafetyError("STEP13_REPLAY_TEAM_ID_INVALID")
        found.add(fid)
        ko = timestamp(row["kickoff_utc"])
        obs = timestamp(row["result_observed_at_utc"])
        if obs < ko + MINIMUM_RESULT_LAG:
            raise SplitSafetyError("STEP13_REPLAY_RESULT_EARLIER_THAN_POSSIBLE")
        if row["label_90m"] not in ("H", "D", "A"):
            raise SplitSafetyError("STEP13_REPLAY_LABEL_INVALID")
        role = next((part for part, start, stop in WINDOWS
                     if timestamp(start) <= ko < timestamp(stop)), None)
        if role != row["partition"] or role == "TEST":
            raise SplitSafetyError("STEP13_REPLAY_PARTITION_OR_TEST_DENIED")
        checked.append({
            "fixture_id": fid, "home_team_id": home, "away_team_id": away,
            "kickoff": ko, "result_observed_at": obs, "label": row["label_90m"],
            "partition": role,
        })
    return sorted(checked, key=lambda x: (x["kickoff"], x["fixture_id"]))


def run_synthetic_fold(source, *, fold, method, evaluation_asof_utc):
    """Replay EXACT earlier observations before every simulated kickoff.

    For a fold: TRAIN uses only eligible history available before fold start;
    subsequent VALIDATION matches update Elo after their result observation.
    For matches with delayed labels, update uses Elo rating at its own kickoff,
    then adds a zero-sum delta at receipt time. Future labels NEVER affect
    pre-receipt predictions.
    """
    if type(fold) is not int or not 1 <= fold <= 4:
        raise SplitSafetyError("STEP13_REPLAY_FOLD_INVALID")
    if method not in METHODS:
        raise SplitSafetyError("STEP13_REPLAY_METHOD_INVALID")
    rows = _validated_synthetic_rows(source)
    start_text, stop_text = WALK_FORWARD[fold - 1]
    start, stop = timestamp(start_text), timestamp(stop_text)
    observed_asof = timestamp(evaluation_asof_utc)
    if observed_asof <= stop:
        raise SplitSafetyError("STEP13_REPLAY_EVALUATION_BEFORE_FOLD_END")
    oldest = (timestamp(WINDOWS[0][1]) if method == "EXPANDING"
              else start.replace(year=start.year-2))

    history = [r for r in rows if
               oldest <= r["kickoff"] < start and
               r["result_observed_at"] < start]
    validation = [r for r in rows if
                  r["partition"] == "VALIDATION" and start <= r["kickoff"] < stop]
    if not validation:
        raise SplitSafetyError("STEP13_REPLAY_NO_VALIDATION_ROWS")
    if any(r["result_observed_at"] > observed_asof for r in validation):
        raise SplitSafetyError("STEP13_REPLAY_LABEL_NOT_OBSERVED_BY_EVALUATION")
    included = sorted(history + validation,
                      key=lambda x: (x["kickoff"], x["fixture_id"]))

    params = BaselineParameters()
    ratings = {}
    pending = []
    predictions = []
    updates = 0
    for game in included:
        ko = game["kickoff"]
        # Strict '< kickoff': an observation stamped at target kickoff itself
        # is still unavailable; equal-time kickoffs cannot learn each other.
        while pending and pending[0][0] < ko:
            _, _, h_id, a_id, d_home, d_away = heapq.heappop(pending)
            ratings[h_id] = ratings.get(h_id, params.initial_elo) + d_home
            ratings[a_id] = ratings.get(a_id, params.initial_elo) + d_away
            updates += 1
        h_id, a_id = game["home_team_id"], game["away_team_id"]
        pre_h = ratings.get(h_id, params.initial_elo)
        pre_a = ratings.get(a_id, params.initial_elo)
        if start <= ko < stop:
            outlook = forecast(pre_h, pre_a, params)
            predictions.append({
                "fixture_id": game["fixture_id"],
                "kickoff_utc": game["kickoff"].isoformat().replace("+00:00", "Z"),
                "p_1x2": outlook["p_1x2"],
                "label_90m": game["label"],
                "elo_home_before_kickoff": pre_h,
                "elo_away_before_kickoff": pre_a,
                "applied_prior_observations": updates,
            })
        updated_h, updated_a = update_elo(pre_h, pre_a, game["label"], params)
        heapq.heappush(pending, (
            game["result_observed_at"], game["fixture_id"], h_id, a_id,
            updated_h - pre_h, updated_a - pre_a,
        ))
    metric_input = [
        {"probabilities": row["p_1x2"], "label": row["label_90m"]}
        for row in predictions
    ]
    metrics = score_synthetic_reference(metric_input, mode="SYNTHETIC_REFERENCE_ONLY")
    outcome = {
        "schema": SCHEMA,
        "source_type": "SYNTHETIC_REFERENCE_ONLY",
        "source_content_sha256": sha(source),
        "method": method,
        "fold": fold,
        "validation_from_utc": start_text,
        "validation_to_exclusive_utc": stop_text,
        "evaluation_asof_utc": evaluation_asof_utc,
        "history_window_from_utc": oldest.isoformat().replace("+00:00", "Z"),
        "training_synthetic_candidate_count": len(history),
        "validation_synthetic_count": len(validation),
        "prediction_rows": predictions,
        "synthetic_score_reference": metrics,
        "model_fitted": False,
        "empirical_historical_performance": False,
        "real_pit_verified": False,
        "real_historical_training_allowed": False,
        "gate13_pass": False,
    }
    outcome["report_sha256"] = sha(outcome)
    return outcome


def compare_synthetic_fold(source, *, fold, evaluation_asof_utc):
    expanding = run_synthetic_fold(
        source, fold=fold, method="EXPANDING",
        evaluation_asof_utc=evaluation_asof_utc)
    rolling = run_synthetic_fold(
        source, fold=fold, method="ROLLING_24_CALENDAR_MONTHS",
        evaluation_asof_utc=evaluation_asof_utc)
    if [r["fixture_id"] for r in expanding["prediction_rows"]] != [
            r["fixture_id"] for r in rolling["prediction_rows"]]:
        raise SplitSafetyError("STEP13_REPLAY_VALIDATION_NOT_PAIRED")
    return {"fold": fold, "source_type": "SYNTHETIC_REFERENCE_ONLY",
            "expanding": expanding, "rolling": rolling,
            "validation_paired": True, "real_historical_test": False,
            "training_allowed": False}
