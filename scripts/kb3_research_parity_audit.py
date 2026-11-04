"""Read-only reproducible clock policy inspection and optional per-fixture delta.

No provider calls, training, encrypted source decryption or modifications.
Usage:
  python -m scripts.kb3_research_parity_audit
  python -m scripts.kb3_research_parity_audit --fixtures /tmp/fixture_inputs.json
The optional fixtures input requires genuine provenance review before use.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
from datetime import timedelta
from pathlib import Path
from src.kb3_research_train_forward_contract import audit_batch, sha, utc, ALLOWED

ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "src/kb3_features.py"
LEGACY = ROOT / "scripts/step14_m1r_recompute_1140_relaxed_48h.py"


def inspect_source(forward_text, legacy_text):
    f = re.sub(r"\s+", "", forward_text)
    h = re.sub(r"\s+", "", legacy_text)
    checks = {
        "forward_result_lag_3h": "RESULT_LAG=timedelta(hours=3)" in f,
        "legacy_train_lag_48h": "LAG=timedelta(hours=48)" in h,
        "forward_age_uses_capture_cutoff":
            '(cutoff-utc_dt(all_games[-1]["kickoff_utc"])).total_seconds()' in f,
        "legacy_age_uses_target_kickoff":
            '(ko-previous[-1]["ko"]).total_seconds()' in h,
        "forward_requires_original_publication":
            "start+RESULT_LAG<=published<=captured<=cutoff" in f,
        "legacy_source_explicitly_reconstructed":
            "B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT" in h,
    }
    if not all(checks.values()):
        raise ValueError("SOURCE_POLICY_DRIFT_REQUIRES_MANUAL_REVIEW")
    return {"schema": "kb3-p1-01-research-source-clock-audit-v1",
            "checks": checks,
            "forward_code_sha256": hashlib.sha256(forward_text.encode()).hexdigest(),
            "legacy_code_sha256": hashlib.sha256(legacy_text.encode()).hexdigest(),
            "lag_disagreement": "CONFIRMED_48H_VS_3H",
            "age_reference_disagreement": "CONFIRMED_KICKOFF_VS_CUTOFF",
            "remediation_status": "OPEN_NOT_FIXED",
            "source_evidence_certified": False, "model_unchanged": True,
            "gate16": "PENDING", "gate17": "PENDING"}



def real_fixture_clock_case_study(db_path, *, max_targets=128):
    """True historic fixture IDs but hypothetical target-2h capture, never PIT.

    This studies CLOCK POLICY differences over the existing chronological
    fixture index, not the historical provider first-published timestamps.
    Score labels and target results are never read. The real forward snapshot
    clock may be different, so this cannot clear P1-01.
    """
    db_path = Path(db_path)
    if not db_path.is_file():
        raise ValueError("HISTORICAL_SOURCE_DB_NOT_FOUND")
    if type(max_targets) is not int or not 1 <= max_targets <= 2000:
        raise ValueError("INVALID_TARGET_LIMIT")
    with sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("HISTORICAL_DB_INTEGRITY_ERROR")
        events = [dict(zip(("scope", "match_id", "kickoff_utc",
                            "home_team_id", "away_team_id"), r))
                  for r in db.execute(
                   "SELECT scope,match_id,kickoff_utc,home_team_id,away_team_id "
                   "FROM finished_fixture_index ORDER BY kickoff_utc,match_id")]
        observation_ids = set(db.execute(
            "SELECT scope,match_id FROM observations"))
    if any(e["scope"]=="ENG" for e in events):
        raise ValueError("PROTECTED_ENG_HISTORY_PRESENT")
    targets = [e for e in events if e["scope"] in ALLOWED
               and (e["scope"], e["match_id"]) in observation_ids]
    targets = targets[-max_targets:]
    cases = []
    for target in targets:
        ko = utc(target["kickoff_utc"])
        capture = (ko - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        predecessors = [
            {"fixture_id": p["match_id"], "kickoff_utc": p["kickoff_utc"]}
            for p in events if p["scope"]==target["scope"]
            and p["match_id"] != target["match_id"]
            and utc(p["kickoff_utc"]) < ko
            and (p["home_team_id"] in (target["home_team_id"],target["away_team_id"])
                 or p["away_team_id"] in (
                     target["home_team_id"],target["away_team_id"]))
        ]
        cases.append({"league":target["scope"],"fixture_id":target["match_id"],
                      "kickoff_utc":target["kickoff_utc"],
                      "capture_cutoff_utc":capture,
                      "predecessors":predecessors})
    audited = audit_batch(cases)
    examples = [r for r in audited["targets"] if
                r["only_legacy_ids"] or r["only_forward_clock_ids"]
                or r["legacy_days_since_last_kickoff_at_target"] !=
                r["forward_days_since_last_kickoff_at_capture"]][:5]
    return {
        "schema": "kb3-real-historical-fixture-id-clock-case-study-v1",
        "real_fixture_ids_from_existing_sqlite": True,
        "input_sqlite_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest(),
        "sample_targets_checked": audited["target_count"],
        "predecessor_set_difference_targets":
            audited["predecessor_set_difference_targets"],
        "days_since_last_difference_targets":
            audited["days_since_last_difference_targets"],
        "examples": examples,
        "assumed_capture_clock": "HYPOTHETICAL_TARGET_KICKOFF_MINUS_2H",
        "provider_first_publication_certified": False,
        "original_capture_cutoff_recovered": False,
        "source_class": "HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
        "training_allowed": False, "no_model_or_data_mutation": True,
    }


def run(fixtures=None, historical_db=None, max_targets=128):
    a = inspect_source(FORWARD.read_text(), LEGACY.read_text())
    if fixtures is None:
        a["same_fixture_deltas"] = None
        a["same_fixture_sample_status"] = "NO_REAL_ID_INPUT_SUPPLIED"
    else:
        a["same_fixture_deltas"] = audit_batch(fixtures)
        a["same_fixture_sample_status"] = "RESEARCH_INPUT_NOT_CERTIFICATION"
    if historical_db is not None:
        a["real_historical_clock_case_study"] = real_fixture_clock_case_study(
            historical_db, max_targets=max_targets)
    a["report_sha256"] = sha(a)
    return a


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", type=Path, help="JSON list of same-fixture targets")
    p.add_argument("--historical-db", type=Path, help="Existing real historical sqlite (read-only)")
    p.add_argument("--max-targets", type=int, default=128)
    args = p.parse_args()
    fixtures = None if args.fixtures is None else json.loads(args.fixtures.read_text())
    print(json.dumps(run(fixtures, historical_db=args.historical_db,
                         max_targets=args.max_targets),
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
