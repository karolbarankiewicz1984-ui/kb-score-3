"""Reproduce actual four-season native PitchAPI Elo from TWO sealed archives.

Runs on the owner's trusted computer only. Private RSA key is never sent to
GitHub or persisted in artifacts; decrypted SQLite lives in TemporaryDirectory.
Only aggregate nonidentifying audit data leaves this command.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from src.kb3_features import utc_dt,digest
from src.kb3_pitch_native_archive import restore as restore_current
from src.kb3_pitch_uefa_evidence import restore as restore_history
from src.kb3_pitch_native_ledger import latest_asof
from src.kb3_pitch_native_observed_features import build_native_observed

def sha(blob):return hashlib.sha256(blob).hexdigest()

def audit(*,current_cipher,current_manifest,historical_cipher,
          historical_manifest,private_key,cutoff_utc,
          expected_historical_sha256,expected_current_sha256):
    for source,expected in ((historical_cipher,expected_historical_sha256),
                            (current_cipher,expected_current_sha256)):
        if not isinstance(expected,str) or len(expected)!=64 or sha(
            Path(source).read_bytes())!=expected.lower():
            raise ValueError("SEALED_SOURCE_NOT_PINNED_TO_APPROVED_CIPHERTEXT")
    source=restore_history(historical_cipher,historical_manifest,private_key,
                           include_receipts=True)
    if not source["validated"] or len(source["receipts"])!=4:
        raise ValueError("NATIVE_HISTORICAL_SEALED_SOURCE_INVALID")
    with tempfile.TemporaryDirectory(prefix="kb3_native_multiyear_") as tmp:
        sqlite=Path(tmp)/"verified-current.sqlite3"
        verified=restore_current(current_cipher,current_manifest,private_key,sqlite)
        if not verified["restored"]:
            raise ValueError("NATIVE_CURRENT_SEALED_SOURCE_INVALID")
        with sqlite3.connect(f"file:{sqlite.resolve()}?mode=ro",uri=True) as db:
            target_games=latest_asof(db,cutoff_utc)
            if not target_games or len(target_games)!=380:
                raise ValueError("NATIVE_CURRENT_SOURCE_UNAVAILABLE_ASOF")
            cutoff=utc_dt(cutoff_utc)
            upcoming=[g for g in target_games.values() if g["status"]!="finished"
                      and utc_dt(g["time_utc"])>cutoff]
            if not upcoming:
                raise ValueError("NO_FUTURE_NATIVE_TARGET_AT_CUTOFF")
            target=min(upcoming,key=lambda g:(g["time_utc"],g["id"]))
            first=build_native_observed(db,target["id"],cutoff_utc=cutoff_utc)
            combined=build_native_observed(db,target["id"],cutoff_utc=cutoff_utc,
                            historical_receipts=source["receipts"])
            assert combined["sha256"]==digest({
                k:v for k,v in combined.items() if k!="sha256"})
            assert not combined["training_allowed"]
            assert not combined["target_prematch_snapshot_certified"]
            if combined["accepted_predecessor_count"]-first["accepted_predecessor_count"]!=1140:
                raise ValueError("HISTORICAL_RESULTS_NOT_FULLY_INCLUDED")
            if any(utc_dt(p["latest_required_observed_at_utc"])>cutoff
                   for p in combined["feature_availability"].values()):
                raise ValueError("MULTISEASON_FIELD_AFTER_CUTOFF")
            return {"schema":"kb3-step11-native-4season-real-offsite-audit-v1",
                "provider":"PitchAPI","feature_schema":combined["schema"],
                "cutoff_utc":cutoff_utc,
                "target_kickoff_utc":combined["kickoff_utc"],
                "previous_completed_seasons":3,
                "prior_season_finished_results":1140,
                "current_season_finished_results":first["accepted_predecessor_count"],
                "combined_observed_results":combined["accepted_predecessor_count"],
                "home_prior_season_games":combined["features"]["home_prior_seasons_games_available"],
                "away_prior_season_games":combined["features"]["away_prior_seasons_games_available"],
                "field_count":len(combined["features"]),
                "field_availability_receipts":len(combined["feature_availability"]),
                "home_elo_current_only":first["features"]["home_elo"],
                "home_elo_combined":combined["features"]["home_elo"],
                "away_elo_current_only":first["features"]["away_elo"],
                "away_elo_combined":combined["features"]["away_elo"],
                "historical_sealed_sha256":sha(Path(historical_cipher).read_bytes()),
                "current_sealed_sha256":sha(Path(current_cipher).read_bytes()),
                "historical_full_chain_sha256":source["proof"]["final_chain_sha256"],
                "full_feature_lineage_sha256":combined["sha256"],
                "historical_original_provider_publication_known":False,
                "historical_prematch_pit_certified":False,
                "provisional_elo_params_only":True,
                "training_allowed":False,
                "production_forecasts_allowed":False}
def main():
    p=argparse.ArgumentParser()
    for name in ("current-cipher","current-manifest","historical-cipher",
                 "historical-manifest","private-key","cutoff-utc",
                 "expected-historical-sha256","expected-current-sha256","out"):
        p.add_argument("--"+name,required=True)
    args=vars(p.parse_args())
    out=args.pop("out")
    try:
        data=audit(**{k.replace("-","_"):v for k,v in args.items()})
        path=Path(out);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("x",encoding="utf8") as fd:
            json.dump(data,fd,sort_keys=True,indent=2);fd.write("\n")
        print("KB3_NATIVE_MULTISEASON_VERIFIED_NO_FIT",
              json.dumps({k:data[k] for k in (
                "prior_season_finished_results","combined_observed_results",
                "field_count","field_availability_receipts",
                "historical_prematch_pit_certified","training_allowed")},
              sort_keys=True))
    except Exception as exc:
        # Do not log provider record content or paths containing private secrets.
        print("KB3_NATIVE_MULTISEASON_REJECTED",type(exc).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
