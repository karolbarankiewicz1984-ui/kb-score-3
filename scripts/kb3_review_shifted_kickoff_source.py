"""Locally reopen the owner-sealed PitchAPI evidence for one quarantined fixture."""

import argparse
import json
from pathlib import Path
import sqlite3

from scripts.kb3_review_postfit_readonly import ROOT, latest_receipt, need, pending_settlement_review, utc
from src.kb3_pitch_uefa_evidence import restore


def verified_fixture(receipts, case, expected_kickoff, *, frozen):
    resource = f"pitchapi:m0720:fixtures:{case['league']}:2026/2027"
    source = [item for item in receipts if item["resource"] == resource]
    need(len(source) == 1, "SHIFTED_KICKOFF_SOURCE_RESOURCE_NOT_UNIQUE")
    source = source[0]
    if frozen:
        need(source["chain_sha256"] == case["frozen_source_chain_sha256"]
             and utc(source["completed_at_utc"]) <= utc(case["frozen_capture_utc"]),
             "SHIFTED_KICKOFF_ORIGINAL_SOURCE_CHAIN_OR_CLOCK_MISMATCH")
    matches = [m for m in source["payload"]["matches"] if m["id"] == case["native_match_id"]]
    need(len(matches) == 1, "SHIFTED_KICKOFF_NATIVE_MATCH_NOT_UNIQUE")
    match = matches[0]
    need(utc(match["time_utc"]) == utc(expected_kickoff), "SHIFTED_KICKOFF_PROVIDER_CLOCK_MISMATCH")
    teams = {}
    for side in ("home", "away"):
        team = match.get(f"{side}_team")
        need(isinstance(team, dict) and team.get("id") == case[f"frozen_{side}_team_id"],
             "SHIFTED_KICKOFF_PROVIDER_TEAM_ID_MISMATCH")
        name = team.get("name")
        need(isinstance(name, str) and bool(name.strip()), "SHIFTED_KICKOFF_PROVIDER_TEAM_NAME_MISSING")
        teams[side] = {"id": team["id"], "name": name.strip()}
    return teams, source["chain_sha256"]


def read_bundle(folder, owner_key):
    return restore(folder / "SOURCE.enc", folder / "SOURCE.manifest.json", owner_key,
                   include_receipts=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_match_id")
    parser.add_argument("--frozen-source", required=True, type=Path)
    parser.add_argument("--owner-key", required=True, type=Path,
                        help="Path to the private recipient key on the owner's machine")
    args = parser.parse_args()

    receipt_path, receipt = latest_receipt(ROOT)
    ledger = ROOT / "data/forward_m0_720_eight/kb3_forward_eight.sqlite"
    with sqlite3.connect(ledger.as_uri()+"?mode=ro", uri=True) as db:
        pending = pending_settlement_review(db, receipt)
    cases = [c for c in pending["kickoff_changed_review_cases"]
             if c["native_match_id"] == args.native_match_id]
    need(len(cases) == 1, "SHIFTED_KICKOFF_PENDING_CASE_NOT_UNIQUE")
    case = cases[0]
    need(case["provider_source_identity_and_cutoff_checks_pass"], "SHIFTED_KICKOFF_SOURCE_REVIEW_FAILED")

    original = read_bundle(args.frozen_source, args.owner_key)
    revised = read_bundle(receipt_path.parent, args.owner_key)
    need(revised["proof"]["final_chain_sha256"] == receipt["source_chain_sha256"],
         "SHIFTED_KICKOFF_SETTLEMENT_SOURCE_CHAIN_MISMATCH")
    original_teams, original_chain = verified_fixture(
        original["receipts"], case, case["original_frozen_kickoff_utc"], frozen=True)
    revised_teams, revised_chain = verified_fixture(
        revised["receipts"], case, case["provider_revised_kickoff_utc"], frozen=False)
    need(original_teams == revised_teams, "SHIFTED_KICKOFF_PROVIDER_TEAM_NAMES_CHANGED")
    print(json.dumps({
        "league": case["league"], "native_match_id": case["native_match_id"],
        "provider_team_names_by_side": original_teams,
        "frozen_source_chain_sha256": original_chain, "revised_source_chain_sha256": revised_chain,
        "automatic_settlement_permitted": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
