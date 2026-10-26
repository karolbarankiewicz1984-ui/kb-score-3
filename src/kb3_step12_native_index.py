"""KB Score 3.0 step12: historical PitchAPI source receipts to split metadata.

Pure processing only: does not access networks, keys, files or credentials.
"""
from collections import Counter
from datetime import timedelta

from src.kb3_features import utc_dt
from src.kb3_pitch_native import check_season
from src.kb3_pitch_uefa_evidence import verify_receipts
from src.kb3_split import build_manifest, sha, SplitSafetyError

SEASONS = ("2023/2024", "2024/2025", "2025/2026", "2026/2027")
RES = "pitchapi:step12:premier-league:{season}:matches:all"


def index_receipts(receipts, *, allow_synthetic=False):
    if not isinstance(receipts, list) or len(receipts) != 5:
        raise SplitSafetyError("STEP12_NEEDS_FIVE_RECEIPTS")
    proof = verify_receipts(receipts, allow_synthetic=allow_synthetic)
    expected = {"pitchapi:catalog"} | {RES.format(season=s) for s in SEASONS}
    if {r["resource"] for r in receipts} != expected:
        raise SplitSafetyError("STEP12_SOURCE_RESOURCE_MISMATCH")
    by_resource = {r["resource"]: r for r in receipts}
    catalogue = by_resource["pitchapi:catalog"].get("payload")
    leagues = catalogue.get("leagues") if isinstance(catalogue, dict) else None
    candidates = [l for l in (leagues or [])
                  if isinstance(l, dict)
                  and str(l.get("name", "")).strip().casefold() == "premier league"
                  and str(l.get("country_code", "")).upper() == "ENG"
                  and all(season in (l.get("seasons") or [])
                          for season in SEASONS)]
    if len(candidates) != 1:
        raise SplitSafetyError("STEP12_CATALOGUE_SEASON_IDENTITY_MISMATCH")
    rows, counts, seen = [], {}, set()
    previous_teams = None
    for season in SEASONS:
        receipt = by_resource[RES.format(season=season)]
        matches = receipt["payload"].get("matches")
        checked = check_season(matches, season, expected_count=380,
                               require_upcoming=(season == SEASONS[-1]))
        if season != SEASONS[-1] and checked["status_counts"] != {"finished": 380}:
            raise SplitSafetyError("STEP12_HISTORICAL_NOT_FINISHED")
        obs = utc_dt(receipt["completed_at_utc"])
        team_ids = {t["id"] for m in matches for t in
                    (m["home_team"], m["away_team"])}
        if previous_teams is not None and len(previous_teams & team_ids) < 14:
            raise SplitSafetyError("STEP12_TEAM_IDS_UNSTABLE")
        previous_teams = team_ids
        counts[season] = {
            "fixtures": len(matches), "statuses": checked["status_counts"],
            "source_payload_sha256": receipt["payload_sha256"],
            "source_observed_at_utc": receipt["completed_at_utc"]}
        for m in matches:
            mid = m["id"]
            if mid in seen:
                raise SplitSafetyError("STEP12_DUPLICATE_FIXTURE")
            seen.add(mid)
            ko = utc_dt(m["time_utc"])
            done = m["status"] == "finished"
            if done and obs < ko + timedelta(hours=3):
                raise SplitSafetyError("STEP12_FINAL_SCORE_NOT_YET_OBSERVED")
            prospect = not done and ko > obs
            row = {
                "fixture_id": mid, "kickoff_utc": m["time_utc"],
                "evidence_class": "PROSPECTIVE_OBSERVED_AT" if prospect else "RETROSPECTIVE",
                "label_90m": ("H" if m["score_home"] > m["score_away"]
                              else "A" if m["score_home"] < m["score_away"] else "D")
                             if done else None,
                "label_observed_at_utc": receipt["completed_at_utc"] if done else None,
                "native_match_sha256": sha(m),
                "source_payload_sha256": receipt["payload_sha256"],
                "source_observed_at_utc": receipt["completed_at_utc"],
            }
            if prospect:
                row["feature_cutoff_utc"] = receipt["completed_at_utc"]
                row["feature_availability"] = {
                    "schedule_only": {"latest_required_observed_at_utc":
                        receipt["completed_at_utc"], "training_allowed": False}}
            rows.append(row)
    at = max(utc_dt(r["completed_at_utc"]) for r in receipts)
    manifest = build_manifest(rows, exported_at_utc=at.isoformat(),
                              dataset_version="kb3-pitch-native-pl-2023-2027-v1")
    partition_counts = dict(Counter(x["partition"] for x in manifest["rows"]))
    if partition_counts != {"TRAIN": 760, "VALIDATION": 380, "TEST": 380}:
        raise SplitSafetyError("STEP12_PARTITION_COUNTS_INVALID")
    if (len(rows) != 1520 or manifest["quarantined_count"] != 1520
            or any(manifest["eligible_counts"].values())
            or manifest["training_allowed"] or manifest["gate12_pass"]):
        raise SplitSafetyError("STEP12_FALSE_TRAINING_READINESS")
    return manifest, {
        "provider": "PitchAPI", "seasons": counts,
        "source_chain_sha256": proof["final_chain_sha256"],
        "partition_counts": partition_counts,
        "real_network_receipts": not allow_synthetic,
        "historical_prematch_pit_certified": False,
        "training_allowed": False}
