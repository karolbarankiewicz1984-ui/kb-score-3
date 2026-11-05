"""Recover and classify existing historical public source evidence, read-only.

Do not confuse older public English FPL/OpenFootball source witnesses with
native PitchAPI 8-league as-of. No web/network, secret, RSA key, or original
protected 2026/27 Premier League TEST. This audits the evidence ALREADY saved.
"""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import hashlib

from scripts.kb3_p1_historical_eligibility_split import (
    SOURCE_DB, ALLOWED_SCOPES, LEAGUES, read_only_conn, hash_json,
)

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_1140=ROOT/"data/audits/STEP14_ORIGINAL_1140_PUBLIC_PREMATCH_RECONSTRUCTION_2026-10-28.json"
PUBLIC_2025=ROOT/"data/audits/STEP14_2025_FPLCORE_DENSE_25_INDEPENDENT_ASOF_2026-10-29.json"
PROVIDER=ROOT/"data/audits/STEP14_PITCHAPI_ORIGINAL_XG_FIRST_PUBLICATION_AND_SEMANTICS_STATUS_2026-10-28.json"


class ArchiveSafety(ValueError):
    pass


def require(condition,reason):
    if not condition:
        raise ArchiveSafety(reason)


def run(*, db_path=SOURCE_DB, old_public_path=PUBLIC_1140,
        public_2025_path=PUBLIC_2025, provider_path=PROVIDER):
    public=json.loads(Path(old_public_path).read_text())
    newer=json.loads(Path(public_2025_path).read_text())
    native=json.loads(Path(provider_path).read_text())
    require(public["native_original_fixture_ids_and_utc_matched"]==1140 and
            public["independently_dated_public_old_fixture_snapshots_total"]==13 and
            public["source_result_based_prematch_form5_exact_native_fixtures"]==106,
            "OLD_PUBLIC_WITNESS_BASELINE_DRIFT")
    require(public["original_pitchapi_historical_121_plus_38_PIT_qualified_TRAIN"]==0
            and public["original_pitchapi_historical_121_plus_38_PIT_qualified_VALIDATION"]==0,
            "OLD_PUBLIC_RECONSTRUCTION_FALSELY_ADMITTED")
    require(newer["independent_GitHub_server_witnessed_old_versions"]==25
            and newer["historically_public_source_FORM5_targets"]==109
            and newer["historically_public_source_xg5_complete_targets"]==107
            and newer["source_provider_first_published_time_PitchAPI_is_unverified"] is True
            and newer["provider_original_121_plus_38_PIT_certified"]==0,
            "LATEST_PUBLIC_WITNESS_BASELINE_DRIFT")
    require(native["historical_team_xg_original_provider_version_history_recovered"] is False
            and native["historical_team_xg_first_value_published_at_field_in_public_docs"] is False
            and native["train_rows_original_full_121_plus_38_pit_certified"]==0
            and native["validation_rows_original_full_121_plus_38_pit_certified"]==0,
            "ORIGINAL_PITCHAPI_FIRST_PUBLICATION_DRIFT")
    with read_only_conn(db_path) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                "SOURCE_DB_INTEGRITY_FAIL")
        scopes={x[0] for x in db.execute(
            "SELECT DISTINCT scope FROM observations")}
        require(scopes<=ALLOWED_SCOPES and "ENG" not in scopes,
                "PROTECTED_ENG_SOURCE_INCLUDED")
        stats={}
        for name,sql in (
            ("observed_stats_rows","SELECT COUNT(*) FROM observations"),
            ("native_eight_stats_rows",
             "SELECT COUNT(*) FROM observations WHERE scope!='UCL'"),
            ("provider_first_published_present",
             "SELECT COUNT(*) FROM observations WHERE provider_first_published_at_utc IS NOT NULL"),
            ("observed_stats_before_target_minus90min",
             """SELECT COUNT(*) FROM observations
                WHERE julianday(source_observed_at_utc)
                  <= julianday(kickoff_utc)-90.0/1440.0"""),
            ("fixture_first_published_present",
             "SELECT COUNT(*) FROM finished_fixture_index WHERE original_provider_first_published_utc IS NOT NULL"),
            ("fixture_listed_before_target_minus90min",
             """SELECT COUNT(*) FROM finished_fixture_index
                WHERE julianday(listing_observed_at_utc)
                  <= julianday(kickoff_utc)-90.0/1440.0"""),
            ("distinct_history_target_receipts",
             """SELECT COUNT(*) FROM rolling_feature_cache
                WHERE provider_original_pit_certified=1 OR research_only!=1"""),
        ):
            stats[name]=db.execute(sql).fetchone()[0]
    # 1525 / 1520 describe the *archived* 04.11 experiment, not a
    # maximum size of a continuously growing research SQLite. Never remove
    # the independent first-publication and actual-time protection gates.
    old_total, old_eight = 1525, 1520
    require(stats["observed_stats_rows"]>=old_total and
            stats["native_eight_stats_rows"]>=old_eight and
            stats["observed_stats_rows"]>=stats["native_eight_stats_rows"] and
            stats["provider_first_published_present"]==0 and
            stats["fixture_first_published_present"]==0 and
            stats["observed_stats_before_target_minus90min"]==0 and
            stats["fixture_listed_before_target_minus90min"]==0 and
            stats["distinct_history_target_receipts"]==0,
            "HISTORICAL_PIT_PROVENANCE_OR_INVENTORY_DRIFT")
    result={
        "schema":"kb3-existing-public-archive-vs-native-eight-pit-audit-v1",
        "audit_scope":"CHECKED_IN_HISTORICAL_SQLITE_AND_PREVIOUS_PUBLIC_AUDITS",
        "existing_earlier_public_witnesses_reused_not_newly_recovered":True,
        "existing_public_witness_scope":"ENGLISH_FPL_OPENFOOTBALL_DIFFERENT_PROVIDER",
        "old_1140_native_ENG_public_witnessed_snapshots":13,
        "old_1140_native_ENG_prematch_result_form5_candidates":106,
        "newer_2025_ENG_public_witnessed_old_source_versions":25,
        "newer_2025_ENG_public_form5_targets":109,
        "newer_2025_ENG_public_xg5_targets_alternative_definition":107,
        "do_not_sum_overlapping_public_snapshot_sets":True,
        "do_not_transfer_public_fpl_xg_to_native_pitchapi":True,
        "eight_league_source_observations":stats,
        "archived_experiment_20261104_observations":old_total,
        "archived_experiment_20261104_eight_league_observations":old_eight,
        "current_inventory_delta_from_archived_experiment":
            stats["observed_stats_rows"]-old_total,
        "current_eight_league_delta_from_archived_experiment":
            stats["native_eight_stats_rows"]-old_eight,
        "original_experiment_replayed_on_current_source":False,
        "independent_old_eight_league_provider_publication_recovered_from_checked_sources":0,
        "verified_eight_league_historical_prematch_v2_training_targets":0,
        "new_external_sources_downloaded":0,
        "provider_api_calls":0,
        "historical_other_provider_eng_witnesses_not_access_to_protected_test":True,
        "formal_training_approved":False,
        "next_recovery_need":(
            "PRE_TARGET_NATIVE_EIGHT_LEAGUE_SOURCE_BYTES_WITH_INDEPENDENT_PUBLICATION"
            "_AND_ID_CROSSWALK_OR_TRUE_FUTURE_CAPTURE"),
        "original_M0_unchanged":True,
        "gate16":"PENDING","gate17":"PENDING",
    }
    result["report_sha256"]=hash_json(result)
    return result


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        raise ArchiveSafety("REPORT_OUTPUT_ALREADY_EXISTS")
    result=run()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("KB3_ARCHIVE_RECOVERY_EVIDENCE",json.dumps({
        "saved_public_sources_2025":result["newer_2025_ENG_public_witnessed_old_source_versions"],
        "saved_public_targets_2025":result["newer_2025_ENG_public_form5_targets"],
        "native_eight_old_pit":result[
            "verified_eight_league_historical_prematch_v2_training_targets"],
        "source_timing":result["eight_league_source_observations"],
        "new_external_sources_downloaded":0,
        "report_sha256":result["report_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
