"""Step11 two completed Premier League seasons, ephemeral CI-only integration pilot.

Uses existing API-Football subscription: TWO fixture-list calls.
NEVER exports fixture rows, secrets, xG, database, or predictions.
No historical point-in-time certification. No training.
"""
from __future__ import annotations
import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3

from scripts.step09_import_history import (
    canonical_bytes,fetch_api,import_rows,parse_rows,sha256
)
from src.kb3_features import build_features,utc_dt,utc_str

YEARS=(2023,2024)
EXPECTED=380


def pilot(*, outdir, key):
    if not key:
        raise RuntimeError("API_FOOTBALL_KEY_REQUIRED")
    root=Path(outdir)
    root.mkdir(parents=True,exist_ok=True)
    db=root/"step11-pl-two-seasons-EPHEMERAL.sqlite3"
    source_hashes={}
    imports=[]
    for year in YEARS:
        payload=fetch_api(key,league_id=39,season=year)
        rows=parse_rows(payload,expected_count=EXPECTED,league_id=39,season=year)
        if any(r["status"]!="FINISHED" for r in rows):
            raise ValueError("HISTORICAL_SEASON_NOT_ALL_FINISHED")
        response_hash=sha256(canonical_bytes(payload))
        a=import_rows(db,rows,response_hash,league_id=39,season=year)
        b=import_rows(db,rows,response_hash,league_id=39,season=year)
        if a["inserted"]!=EXPECTED or b["inserted"]!=0 or b["reused"]!=EXPECTED:
            raise ValueError("SEASON_IMPORT_NOT_IDEMPOTENT")
        imports.append({"start_year":year,"imported":a["inserted"],"reused":b["reused"],
                        "retrospective_snapshot":True})
        source_hashes[str(year)]=response_hash
    with sqlite3.connect(db) as c:
        fixture_count=c.execute("SELECT count(*) FROM fixtures").fetchone()[0]
        by_season=c.execute("""
            SELECT s.start_year,count(*) FROM fixtures f
            JOIN seasons s ON s.season_id=f.season_id
            GROUP BY s.start_year ORDER BY s.start_year
        """).fetchall()
        teams=c.execute("SELECT count(*) FROM teams").fetchone()[0]
        if fixture_count!=760 or by_season!=[(2023,380),(2024,380)]:
            raise ValueError("TWO_SEASON_COUNT_MISMATCH")
        targets=c.execute("""
            SELECT f.fixture_id,f.kickoff_utc FROM fixtures f
            JOIN seasons s ON s.season_id=f.season_id
            WHERE s.start_year=2024
            ORDER BY f.kickoff_utc,f.fixture_id
        """).fetchall()
        samples=[targets[0],targets[len(targets)//2],targets[-1]]
        historical_counts=[]
        for fid,start in samples:
            cutoff=utc_str(utc_dt(start)-timedelta(hours=1))
            replay=build_features(c,fid,cutoff_utc=cutoff,mode="replay")
            strict=build_features(c,fid,cutoff_utc=cutoff,mode="verified")
            previous=(replay["features"]["home_prior_seasons_games_available"]
                      +replay["features"]["away_prior_seasons_games_available"])
            if strict["accepted_predecessor_count"]!=0 or strict["training_allowed"]:
                raise ValueError("INCORRECT_HISTORICAL_AVAILABILITY")
            if replay["training_allowed"] or replay["availability_class"]!="RETROSPECTIVE":
                raise ValueError("REPLAY_ACCIDENTALLY_CERTIFIED")
            historical_counts.append(previous)
        if not any(n>0 for n in historical_counts):
            raise ValueError("NO_CROSS_SEASON_ELO_HISTORY")
    return {
        "schema":"kb3-step11-two-season-ephemeral-v1",
        "source":"API-Football fixtures/league=39, Pro subscription",
        "source_payload_hashes":source_hashes,
        "season_imports":imports,"fixtures_total":fixture_count,
        "competition":"Premier League","distinct_teams_across_two_years":teams,
        "cross_season_prior_match_counts_sample":historical_counts,
        "replay_only":True,"historical_point_in_time_certified":False,
        "training_allowed":False,"trained_model":False,
        "archive_status":"EPHEMERAL_CI_ONLY_NO_DURABLE_BACKUP",
        "secrets_exported":False,"db_exported":False
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",default="audit/step11/two-season")
    a=ap.parse_args()
    out=Path(a.outdir)
    r=pilot(outdir=out,key=os.environ.get("API_FOOTBALL_KEY","").strip())
    (out/"STEP11_TWO_SEASON_AGGREGATE.json").write_text(
        json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("STEP11_TWO_SEASON_PILOT",json.dumps(r,sort_keys=True))


if __name__=="__main__":
    main()
