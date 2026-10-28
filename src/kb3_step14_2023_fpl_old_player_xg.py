"""Prove historic FPL/Opta player-xG rows were in an old May-2024 blob.

No private PitchAPI, no xP expected points, no original target outcomes.
Values and player names are never exported. FPL player per-fixture xG is
not equivalent by default to PitchAPI team-match xG.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import argparse,csv,io,json,math

from src.kb3_step14_multiseason_pit import fetch
from src.kb3_step14_owner_elo_2023_to_2024 import FULL_2023,check_pinned_public_evidence

ROOT=Path(__file__).resolve().parents[1]
MERGED_PATH="data/2023-24/gws/merged_gw.csv"
SCHEMA="kb3-step14-2023-fpl-old-player-fixture-xg-coverage-v1"
class PlayerXGError(ValueError):pass

def inspect(fpl_fixture_csv,fpl_merged_csv):
    fixtures=list(csv.DictReader(io.StringIO(fpl_fixture_csv.decode("utf-8-sig"))))
    if len(fixtures)!=380 or len({str(x["id"]) for x in fixtures})!=380:
        raise PlayerXGError("OLD_PUBLIC_FT_FIXTURE_GRID_CHANGED")
    expected={str(x["id"]) for x in fixtures}
    reader=csv.DictReader(io.StringIO(fpl_merged_csv.decode("utf-8-sig")))
    fields=set(reader.fieldnames or [])
    if not {"fixture","expected_goals","team"}.issubset(fields):
        raise PlayerXGError("NOT_PLAYER_FIXTURE_XG_SCHEMA")
    counts={};has_xg=set();missing_xg=0;invalid_fixture=0;total=0
    for row in reader:
        total+=1
        fixture=str(row.get("fixture") or "").strip()
        if fixture not in expected:
            invalid_fixture+=1
            continue
        counts[fixture]=counts.get(fixture,0)+1
        value=row.get("expected_goals")
        if value is None or value.strip()=="":
            missing_xg+=1
            continue
        try:v=float(value)
        except ValueError as e:raise PlayerXGError("INVALID_PLAYER_XG") from e
        if not math.isfinite(v) or v<0:
            raise PlayerXGError("INVALID_PLAYER_XG")
        has_xg.add(fixture)
    if total<380:raise PlayerXGError("NOT_ENOUGH_PLAYER_ROWS")
    return {
       "source_scope":"FPL_OPTA_PLAYER_FIXTURE_ROWS_NOT_TEAM_PITCHAPI_XG",
       "source_old_commit":FULL_2023["commit"],
       "original_old_fixture_grid":380,
       "public_player_row_count":total,
       "public_player_rows_with_unmatched_fixture":invalid_fixture,
       "distinct_FPL_fixture_ids_represented_by_player_rows":len(counts),
       "distinct_FPL_fixture_ids_with_numeric_player_xg":len(has_xg),
       "player_rows_with_missing_xg":missing_xg,
       "independently_published_full_source_commit_UTC":FULL_2023["push"],
       "independent_push_event_id":FULL_2023["event_id"],
       "player_xg_historically_available_before_2024_25_opening":bool(has_xg),
       "player_xg_each_2023_24_target_prematch_available":False,
       "original_pitchapi_team_match_xg_equivalent":False,
       "no_player_names_values_shots_or_fixture_ids_exported":True,
       "original_train_xg_PIT_certified":False,
       "test_examined":False,"training_allowed":False,"gate14_pass":False}

def run():
    proof=json.loads((ROOT/"data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json").read_text(encoding="utf8"))
    check_pinned_public_evidence(proof)
    base=f"https://raw.githubusercontent.com/{FULL_2023['repo']}/{FULL_2023['commit']}/"
    ft=fetch(base+FULL_2023["path"],limit=4_000_001)
    if sha256(ft).hexdigest()!=FULL_2023["sha"]:
        raise PlayerXGError("HISTORIC_FT_SHA_CHANGED")
    raw=fetch(base+MERGED_PATH,limit=40_000_001)
    if len(raw)>=40_000_001:
        raise PlayerXGError("OLD_MERGED_GW_TOO_LARGE")
    out=inspect(ft,raw)
    out["old_2023_24_merged_player_csv_sha256"]=sha256(raw).hexdigest()
    return {"schema":SCHEMA,"research":out,
            "native_team_xg_pit_proven":False,
            "official_m1_training_allowed":False,"gate14_pass":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    dst=Path(p.parse_args().output)
    r=run()
    dst.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(r,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if dst.exists():
        if dst.read_text(encoding="utf8")!=text:raise PlayerXGError("IMMUTABLE_REPORT_MISMATCH")
    else:dst.write_text(text,encoding="utf8")
    a=r["research"]
    print(json.dumps({
       "old_2023_24_player_rows":a["public_player_row_count"],
       "public_fixture_ids_with_old_numeric_xg":a["distinct_FPL_fixture_ids_with_numeric_player_xg"],
       "old_publication_utc":FULL_2023["push"],
       "full_PitchAPI_team_xg_PIT":False,"gate14_pass":False
    },sort_keys=True))
if __name__=="__main__":main()
