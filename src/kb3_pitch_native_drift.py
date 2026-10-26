"""Compare two independently verified PitchAPI match snapshots (Step11).

Input ledgers must be decrypted separately, not combined. Only *observed*
provider-native data is compared; there is no fabricated published_at.
Redact team/fixture identifiers from the public summary.
"""
from __future__ import annotations
from collections import Counter
from datetime import timezone
import hashlib
import json
import sqlite3

from src.kb3_pit_ledger import as_utc,canonical
from src.kb3_pitch_native_ledger import verify,latest_asof
from src.kb3_pitch_native import check_season

def compare_records(previous,current):
    """Pure, offline and deterministic. Full-season native IDs required."""
    check_season(previous,"2026/2027",expected_count=380,require_upcoming=False)
    check_season(current,"2026/2027",expected_count=380,require_upcoming=False)
    old={m["id"]:m for m in previous};new={m["id"]:m for m in current}
    if set(old)!=set(new):
        raise ValueError("PITCH_FIXTURE_SET_CHANGED_REQUIRES_REVIEW")
    counts=Counter()
    statuses=Counter()
    for mid in sorted(old):
        a,b=old[mid],new[mid]
        if a["home_team"]["id"]!=b["home_team"]["id"] or a["away_team"]["id"]!=b["away_team"]["id"]:
            raise ValueError("PITCH_NATIVE_TEAM_ID_CHANGED_REQUIRES_REVIEW")
        if a["time_utc"]!=b["time_utc"]:
            counts["kickoff_changed"]+=1
        if a["status"]!=b["status"]:
            counts["status_changed"]+=1
            statuses[(a["status"],b["status"])]+=1
        if (a["score_home"],a["score_away"])!=(b["score_home"],b["score_away"]):
            counts["score_changed"]+=1
        if (a["home_team"]["name"],a["away_team"]["name"])!=(
            b["home_team"]["name"],b["away_team"]["name"]):
            counts["display_names_changed"]+=1
        if canonical(a)!=canonical(b):
            counts["full_source_row_changed"]+=1
    return {"league":"Premier League","season":"2026/2027",
       "provider":"PitchAPI","match_count":len(old),
       "changed_kickoffs":counts["kickoff_changed"],
       "changed_statuses":counts["status_changed"],
       "changed_scores":counts["score_changed"],
       "changed_team_display_names":counts["display_names_changed"],
       "changed_raw_match_payloads":counts["full_source_row_changed"],
       "status_transitions":[{"from":a,"to":b,"count":v}
          for (a,b),v in sorted(statuses.items())],
       "match_id_collision_or_team_reassignment":False,
       "same_native_match_ids":True,
       "training_allowed":False}

def _read_last_match_capture(db):
    p=verify(db)
    captures=db.execute("""SELECT capture_id,completed_at_utc,response_sha256,
       chain_sha256,response_json,origin FROM pitch_captures
       WHERE kind='matches' ORDER BY ordinal DESC""").fetchall()
    if not captures:
        raise ValueError("NATIVE_MATCH_CAPTURES_MISSING")
    cid,end,sha,chain,raw,origin=captures[0]
    if origin!="NETWORK_OBSERVED":
        raise ValueError("SYNTHETIC_CAPTURE_CANNOT_CERTIFY_REAL_DRIFT")
    items=json.loads(raw)
    check_season(items,"2026/2027",expected_count=380,require_upcoming=False)
    return items,{"capture_id":cid,"completed_at_utc":end,
                  "response_sha256":sha,"chain_sha256":chain,
                  "verified_receipt_count":p["captures"]}

def compare_independent_ledgers(old_path,new_path):
    """No merge, no writes, no queries, no secrets."""
    from pathlib import Path
    old_path,new_path=Path(old_path),Path(new_path)
    if old_path.resolve()==new_path.resolve():
        raise ValueError("SAME_ARCHIVE_CANNOT_ESTABLISH_TWO_OBSERVATIONS")
    with sqlite3.connect(f"file:{old_path.resolve()}?mode=ro",uri=True) as a,sqlite3.connect(
        f"file:{new_path.resolve()}?mode=ro",uri=True) as b:
        previous,old_meta=_read_last_match_capture(a)
        current,new_meta=_read_last_match_capture(b)
    past,now=as_utc(old_meta["completed_at_utc"]),as_utc(new_meta["completed_at_utc"])
    if now<=past:
        raise ValueError("NEW_OBSERVATION_NOT_LATER_THAN_PREVIOUS")
    diff=compare_records(previous,current)
    diff.update({"schema":"kb3-native-snapshot-drift-v1",
        "prior_observed_at_utc":old_meta["completed_at_utc"],
        "current_observed_at_utc":new_meta["completed_at_utc"],
        "prior_source_hash_sha256":old_meta["response_sha256"],
        "current_source_hash_sha256":new_meta["response_sha256"],
        "prior_receipt_chain_sha256":old_meta["chain_sha256"],
        "current_receipt_chain_sha256":new_meta["chain_sha256"],
        "prior_verified_receipt_count":old_meta["verified_receipt_count"],
        "current_verified_receipt_count":new_meta["verified_receipt_count"],
        "observations_on_distinct_utc_dates":past.date()!=now.date(),
        "actual_provider_published_at_known":False,
        "historical_pit_backtest_certified":False,
        "production_switch_approved":False})
    return diff
