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
from pathlib import Path
from src.kb3_research_train_forward_contract import audit_batch, sha

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


def run(fixtures=None):
    a = inspect_source(FORWARD.read_text(), LEGACY.read_text())
    if fixtures is None:
        a["same_fixture_deltas"] = None
        a["same_fixture_sample_status"] = "NO_REAL_ID_INPUT_SUPPLIED"
    else:
        a["same_fixture_deltas"] = audit_batch(fixtures)
        a["same_fixture_sample_status"] = "RESEARCH_INPUT_NOT_CERTIFICATION"
    a["report_sha256"] = sha(a)
    return a


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", type=Path, help="JSON list of same-fixture targets")
    args = p.parse_args()
    fixtures = None if args.fixtures is None else json.loads(args.fixtures.read_text())
    print(json.dumps(run(fixtures), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
