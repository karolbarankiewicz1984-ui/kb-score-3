"""One bounded PitchAPI capture for a real Step12 native index.

Only the existing account is used. Exactly 5 provider calls; no fitting.
Raw responses leave the runner only in RSA+AES encrypted evidence.
"""
import argparse
import json
import os
from pathlib import Path

from scripts.pitchapi_step06_audit import to_plain, norm
from src.kb3_pit_ledger import utc_now
from src.kb3_pitch_uefa_evidence import add_observation, seal
from src.kb3_step12_native_index import index_receipts, SEASONS, RES
from src.kb3_split import freeze_manifest, sha


def run(outdir, public_key):
    from pitchapi import PitchAPI
    credential = os.environ.get("PITCHAPI_API_KEY")
    if not credential:
        raise RuntimeError("MISSING_PROVIDER_SECRET")
    folder = Path(outdir)
    folder.mkdir(parents=True, exist_ok=True)
    sdk = PitchAPI(api_key=credential)
    observations = []
    first = utc_now()
    catalogue = to_plain(sdk.leagues.list())
    last = utc_now()
    add_observation(observations, resource="pitchapi:catalog",
                    payload=catalogue, started=first, completed=last)
    leagues = catalogue.get("leagues", [])
    matching = [l for l in leagues
                if norm(l.get("name")) == "premier league"
                and str(l.get("country_code") or "").upper() == "ENG"
                and all(s in (l.get("seasons") or []) for s in SEASONS)]
    if len(matching) != 1:
        raise RuntimeError("AMBIGUOUS_PREMIER_LEAGUE_SOURCE")
    for season in SEASONS:
        first = utc_now()
        source = to_plain(sdk.leagues.matches(matching[0]["id"],
                          season=season, status="all"))
        last = utc_now()
        add_observation(observations, resource=RES.format(season=season),
                        payload=source, started=first, completed=last)
    manifest, audit = index_receipts(observations)
    enc = folder / "STEP12_REAL_SOURCE.enc"
    source_manifest = folder / "STEP12_REAL_SOURCE.manifest.json"
    protected = seal(observations, public_key, enc, source_manifest)
    if protected["proof"]["final_chain_sha256"] != audit["source_chain_sha256"]:
        raise RuntimeError("SOURCE_HASH_CHAIN_MISMATCH")
    manifest["sealed_source_sha256"] = protected["ciphertext_sha256"]
    manifest["source_chain_sha256"] = audit["source_chain_sha256"]
    manifest["manifest_sha256"] = sha(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"})
    index_path = folder / "STEP12_NATIVE_SPLIT.json"
    freeze_manifest(manifest, index_path)
    if freeze_manifest(manifest, index_path) != "VERIFIED_UNCHANGED":
        raise RuntimeError("SPLIT_FREEZE_FAILED")
    report = {
        "schema": "kb3-step12-real-native-index-v1",
        "source": "PitchAPI", "calls": 5, "fixture_count": 1520,
        "season_details": audit["seasons"],
        "partition_counts": audit["partition_counts"],
        "quarantined": manifest["quarantined_count"],
        "eligible_counts": manifest["eligible_counts"],
        "source_chain_sha256": audit["source_chain_sha256"],
        "encrypted_source_sha256": protected["ciphertext_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "offsite_restore_verified": False, "gate12_pass": False,
        "training_allowed": False,
    }
    with (folder / "STEP12_NATIVE_AUDIT.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, sort_keys=True, indent=2)
        file.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="audit/step12/real")
    parser.add_argument("--recipient",
                        default="config/step11_archive_recipient_public.pem")
    args = parser.parse_args()
    try:
        report = run(args.out, args.recipient)
    except Exception as exc:
        print("STEP12_INDEX_BLOCKED", type(exc).__name__)
        raise SystemExit(3)
    print("STEP12_INDEX_CAPTURE_SUCCESS", json.dumps({
        key: report[key] for key in
        ("calls", "fixture_count", "partition_counts", "quarantined",
         "eligible_counts", "manifest_sha256", "gate12_pass")
    }, sort_keys=True))


if __name__ == "__main__":
    main()
