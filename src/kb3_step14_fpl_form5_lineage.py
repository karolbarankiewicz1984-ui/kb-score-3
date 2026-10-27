"""Step14 research-only, fail-closed per-fixture FPL form-5 source lineage.

One externally timestamped 2023/24 public blob is used as an immutable
availability witness, NOT as PitchAPI provenance. No native PitchAPI ID join,
TEST, odds, xG, target scores, provider API or CatBoost training.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
import argparse
import csv
import io
import json

from src.kb3_step14_fpl_historic_clock_pilot import verify_raw_csv

REPO = "vaastav/Fantasy-Premier-League"
COMMIT = "96fbc38ee6e36e3a7250081a787b65a1a27c944d"
CSV_SHA256 = "07b88250be0903a76b6334a7db56b9d9c148fc4a301c5e2338ce2c27dd01f367"
PUBLIC_AT = "2023-10-05T14:38:59Z"
EVENT_ID = "32344206544"
SOURCE_AUDIT = "data/audits/STEP14_FPL_2023_PREMATCH_PUBLIC_SNAPSHOT_PILOT_2026-10-27.json"
URL = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/data/2023-24/fixtures.csv"
SCHEMA = "kb3-step14-fpl-source-form5-fixture-lineage-v1"

class LineageError(ValueError):
    pass


def utc(s):
    if not isinstance(s, str) or not s.endswith("Z"):
        raise LineageError("UTC_Z_REQUIRED")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LineageError("BAD_UTC") from exc
    if d.utcoffset().total_seconds() != 0:
        raise LineageError("NON_UTC")
    return d.astimezone(timezone.utc)


def verify_evidence(evidence, raw):
    """The source's Git author/committer date must never substitute for PushEvent."""
    if not isinstance(evidence, dict):
        raise LineageError("MISSING_FROZEN_EVIDENCE")
    records = evidence.get("records", [])
    chosen = [r for r in records if r.get("historic_commit_sha") == COMMIT]
    if len(chosen) != 1:
        raise LineageError("AMBIGUOUS_SOURCE_EVIDENCE")
    r = chosen[0]
    if (evidence.get("gate14_pass") is not False
        or evidence.get("official_M1_train_allowed") is not False
        or r.get("original_publication_timestamp_externally_corroborated") is not True
        or r.get("prematch_source_status") != "PUBLIC_PUSH_VERIFIED_PARTIAL_FT_ONLY"
        or r.get("independent_gharchive_hour_status") != "READ_OK"
        or r.get("public_repo") != REPO
        or r.get("server_confirmed_public_push_utc") != PUBLIC_AT
        or str(r.get("server_event_id")) != EVENT_ID
        or r.get("original_archived_csv_sha256") != CSV_SHA256
        or r.get("finished_ft_records_available_at_historical_source_publication") != 70
        or r.get("unplayed_rows_have_null_scores") != 310
        or sha256(raw).hexdigest() != CSV_SHA256):
        raise LineageError("SOURCE_CLOCK_OR_CONTENT_NOT_PINNED")
    verify_raw_csv(raw, expected_finished=70, push_time_utc=PUBLIC_AT)
    return r


def parse_fixture_rows(raw):
    try:
        items = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    except (UnicodeError, csv.Error) as exc:
        raise LineageError("INVALID_CSV") from exc
    required = {"id", "team_h", "team_a", "kickoff_time", "finished",
                "team_h_score", "team_a_score"}
    if len(items) != 380 or any(not required.issubset(x) for x in items):
        raise LineageError("INVALID_FIXTURE_GRID")
    ids = [x["id"] for x in items]
    if len(set(ids)) != 380 or any(not x for x in ids):
        raise LineageError("DUPLICATE_FIXTURE")
    for r in items:
        if not r["team_h"] or not r["team_a"] or r["team_h"] == r["team_a"]:
            raise LineageError("INVALID_TEAM_PAIR")
        if r["finished"] not in ("True", "False"):
            raise LineageError("BAD_FINISHED")
        if r["kickoff_time"]:
            utc(r["kickoff_time"])
    return items


def _candidate(rows, target, stamp):
    """Prove ALL within-season preceding fixtures for both teams are in blob.

    Unknown kickoff, same-time conflict and intervening matches block rather
    than silently treating 5 old scores as the latest 5 at target time.
    """
    if target["finished"] != "False" or not target["kickoff_time"]:
        return {"state": "NO_PREMATCH_TARGET_CLOCK"}
    kickoff = utc(target["kickoff_time"])
    if kickoff <= stamp:
        return {"state": "NOT_AFTER_VERIFIED_PUBLICATION"}
    sides = {}
    for name, tid in (("home", target["team_h"]), ("away", target["team_a"])):
        matches = [r for r in rows if r["id"] != target["id"]
                   and tid in (r["team_h"], r["team_a"])]
        if any(not r["kickoff_time"] for r in matches):
            return {"state": "TEAM_SCHEDULE_TIME_UNKNOWN"}
        if any(utc(r["kickoff_time"]) == kickoff for r in matches):
            return {"state": "SAME_TEAM_SAME_KICKOFF"}
        prior = [r for r in matches if utc(r["kickoff_time"]) < kickoff]
        # A single unplayed/potentially postponed earlier fixture prevents
        # claiming completeness of the set of five immediately prior games.
        if any(r["finished"] != "True"
               or utc(r["kickoff_time"]) >= stamp for r in prior):
            return {"state": "INTERVENING_UNVERIFIED_FIXTURE"}
        prior.sort(key=lambda r: (utc(r["kickoff_time"]), r["id"]), reverse=True)
        if len(prior) < 5:
            return {"state": "FEWER_THAN_FIVE_PROVEN_PREDECESSORS"}
        sides[name] = [r["id"] for r in prior[:5]]
    return {"state": "PUBLIC_FORM5_INPUTS_CONDITIONALLY_RECONSTRUCTABLE",
            "home_last5_public_fixture_ids": sides["home"],
            "away_last5_public_fixture_ids": sides["away"]}


def build(raw, evidence):
    verify_evidence(evidence, raw)
    rows = parse_fixture_rows(raw)
    stamp = utc(PUBLIC_AT)
    report_rows = []
    for target in rows:
        # Only future, unplayed source rows are considered as possible target
        # fixtures. Original TRAIN/VALIDATION native IDs never enter here.
        if target["finished"] != "False" or not target["kickoff_time"]:
            continue
        if utc(target["kickoff_time"]) <= stamp:
            continue
        result = _candidate(rows, target, stamp)
        result.update({
            "source_fixture_id": target["id"],
            "target_kickoff_in_old_public_schedule_utc": target["kickoff_time"],
            "source_commit_sha": COMMIT,
            "public_push_utc": PUBLIC_AT,
            "independent_event_id": EVENT_ID,
            "native_pitchapi_match_join_certified": False,
            "pitchapi_original_form5_certified": False,
            "elo_complete_chain_certified": False,
            "xg_certified": False,
            "official_M1_training_allowed": False,
        })
        report_rows.append(result)
    counts = dict(sorted(Counter(r["state"] for r in report_rows).items()))
    return {
        "schema": SCHEMA,
        "audit_scope": "FPL_2023_24_PUBLIC_SOURCE_ONLY_NOT_NATIVE_PITCHAPI",
        "verified_public_push_utc": PUBLIC_AT,
        "public_source_commit_sha": COMMIT,
        "csv_sha256": CSV_SHA256,
        "server_event_id": EVENT_ID,
        "public_old_blob_completed_results": 70,
        "public_future_target_rows_evaluated": len(report_rows),
        "counts": counts,
        "records": sorted(report_rows, key=lambda r: (r["target_kickoff_in_old_public_schedule_utc"], r["source_fixture_id"])),
        "result_values_exported": False,
        "native_pitchapi_team_ids_or_scores_examined": False,
        "test_2026_27_examined": False,
        "pitchapi_complete_121_plus_38_feature_pit_certified": False,
        "official_original_train_rows_certified": 0,
        "official_original_validation_rows_certified": 0,
        "official_M1_training_allowed": False,
        "gate14_pass": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / SOURCE_AUDIT).read_text(encoding="utf8"))
    req = Request(URL, headers={"User-Agent": "KB3-step14-historic-lineage"})
    with urlopen(req, timeout=45) as f:
        raw = f.read(3_000_001)
    report = build(raw, evidence)
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if dest.exists():
        if dest.read_text(encoding="utf8") != encoded:
            raise LineageError("IMMUTABLE_REPORT_REPLACEMENT_REFUSED")
    else:
        with dest.open("x", encoding="utf8") as f:
            f.write(encoded)
    # Public counts only: no private native IDs, target scores or goal values.
    print(json.dumps({"public_future_target_rows_evaluated": report["public_future_target_rows_evaluated"],
                      "counts": report["counts"], "official_M1_training_allowed": False,
                      "gate14_pass": False}, sort_keys=True))


if __name__ == "__main__":
    main()
