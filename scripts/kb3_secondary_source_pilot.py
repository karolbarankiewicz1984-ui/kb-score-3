"""Read-only, fail-closed 30-fixture secondary-source pilot for NED/POL.

No scraping, paid API, automatic name fuzzy-match, data write, model fit,
or claim that an observed-after-match source is original pre-match PIT.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sqlite3

from scripts.kb3_history_gain_first import prepare_source, issue_priority_scores
from src.kb3_historical_feature_quality import effective_stat

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"data/research/historical_multistat/observations.sqlite"
RECHECK=ROOT/"data/research/historical_multistat/issue_rechecks.sqlite"
SCHEMA="kb3-secondary-yellow-pilot-strict-crosswalk-v1"
SCOPES=frozenset(("NED","POL"))
HIST_SEASONS=frozenset(("2023/2024","2024/2025","2025/2026"))
MAX_SAMPLES=30

def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def clock(s):
    if not isinstance(s,str) or not s.endswith("Z"):
        raise ValueError("PILOT_STRICT_UTC_REQUIRED")
    return datetime.fromisoformat(s.replace("Z","+00:00"))

def manifest(db_path=DB,recheck_db=RECHECK,limit=MAX_SAMPLES):
    if not 1<=limit<=MAX_SAMPLES:
        raise ValueError("PILOT_MAX_30")
    original_sha=sha_file(db_path)
    source=prepare_source(db_path,recheck_db)
    if source is None:
        raise ValueError("ORIGINAL_HISTORY_REQUIRED")
    fixtures,observed=source
    ranked,_=issue_priority_scores(db_path,recheck_db)
    ix={(s,x["match_id"]):x for s,games in fixtures.items() for x in games}
    with sqlite3.connect(Path(recheck_db).resolve().as_uri()+"?mode=ro",uri=True) as db:
        attempted={(s,mid):status for s,mid,status in db.execute(
            "SELECT scope,match_id,status FROM issue_rechecks "
            "WHERE issue_type='YELLOW_CARDS'")}
    rows=[]
    for (scope,mid),row in observed.items():
        if scope not in SCOPES or row["season"] not in HIST_SEASONS:
            continue
        fixture=ix[(scope,mid)]
        missing=[side for side in ("home","away")
                 if effective_stat(row,"yellow_cards",side) is None]
        if not missing:
            continue
        other=all(effective_stat(row,k,s) is not None
                  for s in ("home","away")
                  for k in ("total_shots","fouls","corners"))
        if not other:
            continue  # Second source of cards alone cannot complete this match's core stats.
        rows.append({
            "scope":scope,"season":row["season"],"pitchapi_match_id":str(mid),
            "kickoff_utc":fixture["kickoff_utc"],
            "home_team_id":str(fixture["home_team_id"]),
            "away_team_id":str(fixture["away_team_id"]),
            "fulltime_home_goals":fixture["goals_home_90"],
            "fulltime_away_goals":fixture["goals_away_90"],
            "missing_yellow_sides":missing,
            "prior_recheck_status":attempted.get((scope,mid),"NOT_ATTEMPTED"),
            "target_impact_weight":round(float(ranked.get((scope,mid),0)),7),
            "secondary_source_status":"NOT_YET_OBSERVED",
        })
    rows.sort(key=lambda x:(-x["target_impact_weight"],x["scope"],
                            x["kickoff_utc"],x["pitchapi_match_id"]))
    # Balanced NED/POL sampling; unused allocation flows to the other league.
    n=limit//2
    chosen=rows_for_scope(rows,"NED",n)+rows_for_scope(rows,"POL",n)
    already={(x["scope"],x["pitchapi_match_id"]) for x in chosen}
    for row in rows:
        if len(chosen)>=limit:break
        if (row["scope"],row["pitchapi_match_id"]) not in already:
            chosen.append(row)
            already.add((row["scope"],row["pitchapi_match_id"]))
    chosen.sort(key=lambda x:(x["scope"],-x["target_impact_weight"],
                             x["kickoff_utc"],x["pitchapi_match_id"]))
    assert sha_file(db_path)==original_sha,"IMMUTABLE_SOURCE_CHANGED"
    return {
        "schema":SCHEMA,"source_sha256":original_sha,
        "source_recheck_sha256":sha_file(recheck_db),
        "candidate_pool_n":len(rows),"pilot_n":len(chosen),
        "pilot_per_scope":dict(sorted(Counter(x["scope"] for x in chosen).items())),
        "unmatched_source_rows":len(chosen),
        "source_observed_match_count":0,"verified_crosswalk_count":0,
        "cards_recovered":0,"core5_increment":0,
        "formal_historical_pit_certified":False,
        "source_authorization_unverified":True,
        "model_fit_or_calibration_performed":False,
        "raw_observations_modified":False,
        "status":"RESEARCH_CANDIDATES_ONLY_SECONDARY_PROVENANCE_PENDING",
        "samples":chosen,
    }

def rows_for_scope(rows,scope,n):
    return [x for x in rows if x["scope"]==scope][:n]

def strict_match(primary,secondary,crosswalk):
    """Only independent verified source: match 2 team IDs, kickoff, score, season.

    Caller supplies a reviewed mapping with named source clubs (NOT generated
    by fuzzy string matching or inferred from matching the score alone).
    Return a validation decision, never mutate source/statistical tables.
    """
    needed=("source_name","source_uri","secondary_match_id",
            "home_team_name","away_team_name","scope","season","kickoff_utc",
            "fulltime_home_goals","fulltime_away_goals","yellow_home","yellow_away",
            "yellow_semantics","license_reviewed_for_intended_use")
    if any(k not in secondary for k in needed):
        return "REJECT_MISSING_REQUIRED_SOURCE_FIELDS"
    if secondary["license_reviewed_for_intended_use"] is not True:
        return "REJECT_SOURCE_RIGHTS_NOT_REVIEWED"
    if not all(isinstance(secondary[k],str) and secondary[k].strip()
               for k in ("source_name","source_uri","secondary_match_id",
                         "home_team_name","away_team_name")):
        return "REJECT_SECONDARY_IDENTITY"
    if secondary["scope"]!=primary["scope"] or secondary["season"]!=primary["season"]:
        return "REJECT_LEAGUE_SEASON"
    if secondary["fulltime_home_goals"]!=primary["fulltime_home_goals"] or \
       secondary["fulltime_away_goals"]!=primary["fulltime_away_goals"]:
        return "REJECT_SCORE_MISMATCH"
    if abs((clock(secondary["kickoff_utc"])-clock(primary["kickoff_utc"])).total_seconds())>15*60:
        return "REJECT_KICKOFF_CLOCK"
    for side in ("home","away"):
        name=secondary[side+"_team_name"]
        mapping=crosswalk.get((primary["scope"],primary["season"],
                               secondary["source_name"],name))
        if not isinstance(mapping,dict) or mapping.get("verified") is not True \
           or mapping.get("original_pitchapi_team_id")!=primary[side+"_team_id"] \
           or not mapping.get("evidence_uri"):
            return "REJECT_UNVERIFIED_TEAM_CROSSWALK"
    if secondary["home_team_name"]==secondary["away_team_name"] or \
       primary["home_team_id"]==primary["away_team_id"]:
        return "REJECT_SAME_TEAM"
    if secondary["yellow_semantics"]!="FULLTIME_YELLOW_EVENTS_INCLUDING_SECOND_YELLOW":
        return "REJECT_YELLOW_SEMANTICS_UNCERTAIN"
    for k in ("yellow_home","yellow_away"):
        v=secondary[k]
        if type(v) is not int or not 0<=v<=30:
            return "REJECT_INVALID_YELLOW"
    return "MATCHED_RESEARCH_ONLY_NOT_ORIGINAL_HISTORICAL_PIT"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=DB)
    p.add_argument("--recheck",type=Path,default=RECHECK)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--limit",type=int,default=MAX_SAMPLES)
    args=p.parse_args()
    result=manifest(args.db,args.recheck,args.limit)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("KB3_SECONDARY_NED_POL_PILOT",json.dumps({
        k:result[k] for k in
        ("pilot_n","pilot_per_scope","candidate_pool_n","cards_recovered",
         "core5_increment","status")},sort_keys=True))

if __name__=="__main__":
    main()
