"""KB3 GATE10: deterministic 30 league-season schedule audit.

Reads *current* authorized API-Football fixture lists and compares them with
the archived 2026-10-25 coverage catalog; writes aggregated evidence only.
Does not import stats or promote ambiguous matches into training.
"""
import argparse
from collections import Counter
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request

from scripts.step10_quality_audit import parse_time

URL="https://v3.football.api-sports.io/fixtures"
FINISHED={"FT","AET","PEN"}
OPEN={"NS","TBD","1H","HT","2H","ET","BT","P","SUSP","INT"}
OTHER={"PST","CANC","ABD","AWD","WO"}
ALL=FINISHED|OPEN|OTHER

def verify_payload(row, payload):
    failures=[]
    caution=[]
    if not isinstance(payload,dict) or payload.get("errors") or not isinstance(payload.get("response"),list):
        return {"critical":["INVALID_API_PAYLOAD"],"warnings":[],"status_counts":{},"count":0,"review":[]}
    if (payload.get("paging") or {}).get("total",1)!=1:
        return {"critical":["INCOMPLETE_PAGINATION"],"warnings":[],"status_counts":{},"count":0,"review":[]}
    seen=set()
    team_games=Counter()
    pairs={}
    fixture_ids=[]
    status_counts=Counter()
    valid_finished=0
    bad_score=0
    date_violations=0
    missing_team=0
    duplicate_external=0
    same_team_day=Counter()
    competition_mismatch=0
    for item in payload["response"]:
        f=item.get("fixture") or {}
        league=item.get("league") or {}
        teams=item.get("teams") or {}
        home=teams.get("home") or {}
        away=teams.get("away") or {}
        fid=f.get("id")
        if not isinstance(fid,int) or isinstance(fid,bool) or fid<=0 or fid in seen:
            duplicate_external+=1
        else:
            seen.add(fid)
            fixture_ids.append(fid)
        if league.get("id")!=row["league_id"] or league.get("season")!=row["season"]:
            competition_mismatch+=1
        ids=(home.get("id"),away.get("id"))
        if not all(isinstance(v,int) and not isinstance(v,bool) and v>0 for v in ids) or ids[0]==ids[1]:
            missing_team+=1
        else:
            team_games[ids[0]]+=1
            team_games[ids[1]]+=1
            pairs.setdefault(ids,[]).append((fid,(f.get("status") or {}).get("short")))
        status=(f.get("status") or {}).get("short") or "NONE"
        status_counts[status]+=1
        if status not in ALL: caution.append("UNKNOWN_STATUS_"+status)
        try:
            kickoff=parse_time(f.get("date"))
            start=dt.datetime(row["season"],7,1,tzinfo=dt.timezone.utc)
            stop=dt.datetime(row["season"]+1,8,1,tzinfo=dt.timezone.utc)
            if not start<=kickoff<stop:date_violations+=1
            if ids[0] != ids[1] and all(isinstance(v,int) for v in ids):
                same_team_day[(ids[0],kickoff.date().isoformat())]+=1
                same_team_day[(ids[1],kickoff.date().isoformat())]+=1
        except (ValueError,TypeError):
            date_violations+=1
        if status in FINISHED:
            score=(item.get("score") or {}).get("fulltime") or {}
            if status=="FT" and (score.get("home") is None or score.get("away") is None):
                score=item.get("goals") or {}
            scores=(score.get("home"),score.get("away"))
            if all(isinstance(v,int) and not isinstance(v,bool) and 0<=v<=20 for v in scores):
                valid_finished+=1
            else:bad_score+=1
    count=len(payload["response"])
    archived=int(row.get("n_fixtures") or 0)
    if count!=archived: caution.append("COUNT_CHANGED_SINCE_SOURCE_AUDIT")
    if duplicate_external:failures.append("INVALID_OR_DUPLICATE_PROVIDER_IDS")
    if competition_mismatch:failures.append("WRONG_LEAGUE_OR_SEASON")
    if missing_team:failures.append("MISSING_OR_CONFLICTING_TEAMS")
    if date_violations:failures.append("IMPOSSIBLE_OR_OUT_OF_SEASON_DATE")
    if bad_score:failures.append("FINISHED_WITH_MISSING_90MIN_RESULT")
    # Goal fields are output labels, not predicitive features for that fixture.
    repeated=[{"home_team_api_id":home,"away_team_api_id":away,"matches":details}
              for (home,away),details in pairs.items() if len(details)>1]
    if repeated:caution.append("DUPLICATE_HOME_AWAY_PAIR_REVIEW_REQUIRED")
    if any(n>1 for n in same_team_day.values()):
        caution.append("TEAM_PLAYS_TWICE_SAME_UTC_DATE_REVIEW_REQUIRED")
    if row["season"]<=2025 and any(s in OPEN for s in status_counts):
        caution.append("HISTORICAL_OPEN_FIXTURE_REVIEW_REQUIRED")
    if row["season"]<=2025 and any(s in OTHER for s in status_counts):
        caution.append("HISTORICAL_EXCEPTION_STATUS_REVIEW_REQUIRED")
    team_counts=Counter(team_games.values())
    if len(team_games) not in (18,20):caution.append("UNEXPECTED_TEAM_COUNT_REVIEW_REQUIRED")
    if count>0 and len(team_games)>0 and max(team_games.values())-min(team_games.values())>4 and row["season"]<=2025:
        caution.append("TEAM_SCHEDULE_IMBALANCE_REVIEW_REQUIRED")
    if row["season"]==2026:
        caution.append("IN_PROGRESS_SEASON_NOT_TRAINING_LABEL_COMPLETE")
    if (valid_finished!=row["n_finished"] and row["season"]<=2025):
        caution.append("FINISHED_COUNT_CHANGED_SINCE_SOURCE_AUDIT")
    return {
        "league_id":row["league_id"],"league":row["league"],"season":row["season"],
        "count":count,"archived_reference_count":archived,
        "finished":sum(status_counts[s] for s in FINISHED),
        "valid_regulation_scores":valid_finished,
        "teams":len(team_games),
        "status_counts":dict(sorted(status_counts.items())),
        "critical":sorted(set(failures)),
        "warnings":sorted(set(caution)),
        "review_duplicate_home_away_pairs":repeated[:20],
        "duplicate_external_ids":duplicate_external,
        "out_of_season_dates":date_violations,
        "invalid_finished_scores":bad_score,
        "team_game_count_distribution":dict(sorted(team_counts.items())),
        "eligibility":"QUARANTINE" if failures or caution and row["season"]<=2025 else "HISTORICAL_LABELS_ONLY" if row["season"]<=2025 else "IN_PROGRESS",
    }

def get(key,league,season):
    if not key:raise RuntimeError("API_FOOTBALL_KEY_REQUIRED")
    qs=urllib.parse.urlencode({"league":league,"season":season})
    req=urllib.request.Request(URL+"?"+qs,headers={
        "x-apisports-key":key,"Accept":"application/json",
        "User-Agent":"KBScore3-GATE10-Crossleague/1.0"})
    with urllib.request.urlopen(req,timeout=40) as resp:
        buf=resp.read(8_000_001)
        if len(buf)>8_000_000:raise RuntimeError("OVERSIZED_RESPONSE")
        return json.loads(buf)

def execute(catalog,key,sleep=0.3):
    if len(catalog["rows"])!=30:raise ValueError("EXPECTED_30_SOURCE_CATALOG_ROWS")
    out=[]
    for row in sorted(catalog["rows"],key=lambda r:(r["league_id"],r["season"])):
        p=get(key,row["league_id"],row["season"])
        out.append(verify_payload(row,p))
        if sleep:time.sleep(sleep)
    reviewed=[r for r in out if r["warnings"] or r["critical"]]
    problems=[r for r in out if r["critical"]]
    finished=[r for r in out if r["season"]<=2025]
    return {
      "schema":"kb3-gate10-multileague-qa-v1",
      "source_catalog":"data/audits/API_FOOTBALL_STEP05_2026-10-25.json",
      "leagues":len(set(r["league_id"] for r in out)),
      "league_seasons":len(out),
      "completed_season_combinations":len(finished),
      "in_progress_season_combinations":len(out)-len(finished),
      "rows_examined":sum(r["count"] for r in out),
      "critical_season_combinations":len(problems),
      "review_season_combinations":len(reviewed),
      "historical_completed_seasons_with_review":sum(bool(r["warnings"] or r["critical"]) for r in finished),
      "labels_approved_without_manual_review":sum(1 for r in finished if not r["warnings"] and not r["critical"]),
      "no_auto_training":True,
      "results":out,
      "summary":"PASS_RAW_VALIDATION_WITH_REVIEW_QUEUE" if not problems else "FAIL_BLOCKING_ERRORS",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--catalog",default="data/audits/API_FOOTBALL_STEP05_2026-10-25.json")
    ap.add_argument("--outdir",default="audit/step10")
    args=ap.parse_args()
    catalog=json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    result=execute(catalog,os.environ.get("API_FOOTBALL_KEY","").strip())
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    (out/"STEP10_ALL_LEAGUES.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("STEP10_CROSSLEAGUE "+json.dumps({k:result[k] for k in (
      "leagues","league_seasons","rows_examined","critical_season_combinations",
      "review_season_combinations","historical_completed_seasons_with_review","summary"
    )},sort_keys=True))
    for r in result["results"]:
        if r["warnings"] or r["critical"]:
            print("STEP10_REVIEW "+json.dumps({k:r[k] for k in ("league","season","count","status_counts","warnings","critical","review_duplicate_home_away_pairs")},ensure_ascii=False))
    if result["critical_season_combinations"]:
        raise SystemExit(3)

if __name__=="__main__":main()
