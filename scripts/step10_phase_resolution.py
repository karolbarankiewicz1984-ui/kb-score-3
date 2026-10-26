"""KB3 Step10: adjudicate historical exceptional 10 league-seasons by *round*.

Any extra fixture from playoffs/relegation tie-break is archived as an explicit
exclusion from standard double-round-robin training labels. Never delete it.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time
from scripts.step10_crossleague_qa import get, FINISHED

EXCEPTIONS={
    78:[2021,2022,2023,2024,2025], # Bundesliga +2 play-offs
    61:[2021,2023,2024,2025],      # Ligue 1 +/- relegation playoffs
    135:[2022],                     # Serie A one extra tiebreaker
}
NAMES={78:"Bundesliga",61:"Ligue 1",135:"Serie A"}

def classify(fixtures, *, league, year):
    seasons=Counter()
    regular=[]
    excluded=[]
    quarantined_regular=[]
    errs=[]
    teams=set()
    home=Counter()
    away=Counter()
    regular_pairs=Counter()
    for x in fixtures:
        lg=x.get("league") or {}
        fx=x.get("fixture") or {}
        t=x.get("teams") or {}
        h=(t.get("home") or {}).get("id")
        a=(t.get("away") or {}).get("id")
        round_label=str(lg.get("round") or "MISSING").strip()
        seasons[round_label]+=1
        if lg.get("id")!=league or lg.get("season")!=year:
            errs.append("WRONG_SEASON_OR_LEAGUE")
        if round_label.casefold().startswith("regular season"):
            regular.append(x)
            teams.update((h,a))
            home[h]+=1
            away[a]+=1
            regular_pairs[(h,a)]+=1
            raw_status=(fx.get("status") or {}).get("short")
            if raw_status in ("AWD","WO"):
                quarantined_regular.append({
                    "api_fixture_id":fx.get("id"),
                    "round":round_label,
                    "status":raw_status,
                    "reason":"AWARDED_GAME_NOT_ORDINARY_90MIN_LABEL",
                    "home_provider_team_id":h,
                    "away_provider_team_id":a,
                })
            elif raw_status not in FINISHED:
                errs.append("UNFINISHED_DOMESTIC_REGULAR_SEASON_MATCH")
        else:
            excluded.append({
              "api_fixture_id":fx.get("id"),
              "round":round_label,
              "status":(fx.get("status") or {}).get("short"),
              "home_provider_team_id":h,
              "away_provider_team_id":a,
            })
            if not any(term in round_label.casefold() for term in
                       ("relegation","play-off","playoff","qualification","final")):
                errs.append("UNKNOWN_NONREGULAR_PHASE_MUST_REVIEW")
    n=len(teams)
    expected=n*(n-1)
    if n not in (18,20):errs.append("INVALID_DOMESTIC_TEAM_COUNT")
    if len(regular)!=expected:errs.append("DOMESTIC_SCHEDULE_INCOMPLETE")
    if any(v!=1 for v in regular_pairs.values()):
        errs.append("DUPLICATE_DIRECTED_DOMESTIC_FIXTURE")
    if any(home[t]!=n-1 or away[t]!=n-1 for t in teams):
        errs.append("HOME_AWAY_IMBALANCE")
    if not excluded:errs.append("EXPECTED_EXCEPTION_PHASE_NOT_FOUND")
    return {
       "league_id":league,"league":NAMES.get(league),"season":year,
       "total_fixture_rows":len(fixtures),
       "domestic_regular_fixtures":len(regular),
       "domestic_teams":n,"expected_regular_fixtures":expected,
       "extra_phases_excluded_from_domestic_training":excluded,
       "quarantined_domestic_fixture_results":quarantined_regular,
       "normal_played_regular_label_count":len(regular)-len(quarantined_regular),
       "phase_names_counts":dict(sorted(seasons.items())),
       "errors":sorted(set(errs)),
       "approval":"DOMESTIC_REGULAR_LABELS_PASS_WITH_AWARDED_QUARANTINE" if not errs and quarantined_regular else "DOMESTIC_REGULAR_LABELS_PASS_EXTRAS_EXCLUDED" if not errs else "QUARANTINE",
    }

def run(key):
    results=[]
    for league,years in EXCEPTIONS.items():
        for year in years:
            payload=get(key,league,year)
            if payload.get("errors") or not isinstance(payload.get("response"),list):
                raise RuntimeError("INVALID_RESPONSE_%s_%s"%(league,year))
            results.append(classify(payload["response"],league=league,year=year))
            time.sleep(0.15)
    return {
      "schema":"kb3-gate10-phase-resolution-v1",
      "scenarios":len(results),
      "approved_regular_seasons":sum(r["approval"].startswith("DOMESTIC_REGULAR_LABELS_PASS") for r in results),
      "quarantined":sum(r["approval"]=="QUARANTINE" for r in results),
      "extra_fixtures_excluded":sum(len(r["extra_phases_excluded_from_domestic_training"]) for r in results),
      "awarded_regular_results_quarantined":sum(len(r["quarantined_domestic_fixture_results"]) for r in results),
      "critical_training_fail_closed":True,
      "scope":"10 exceptional historical season combinations; regular labels only",
      "results":results,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",default="audit/step10")
    args=ap.parse_args()
    d=run(os.getenv("API_FOOTBALL_KEY","").strip())
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    (out/"STEP10_PHASE_RESOLUTION.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("KB3_STEP10_PHASE_RESOLUTION "+json.dumps({
       "scenarios":d["scenarios"],
       "approved_regular_seasons":d["approved_regular_seasons"],
       "quarantined":d["quarantined"],
       "extra_fixtures_excluded":d["extra_fixtures_excluded"],
       "awarded_regular_results_quarantined":d["awarded_regular_results_quarantined"],
    },sort_keys=True))
    for r in d["results"]:
        print("KB3_PHASE_DETAIL "+json.dumps({
          k:r[k] for k in ("league","season","total_fixture_rows",
             "domestic_regular_fixtures","domestic_teams","expected_regular_fixtures",
             "extra_phases_excluded_from_domestic_training",
             "quarantined_domestic_fixture_results","errors")
        },ensure_ascii=False))
    if d["quarantined"]:raise SystemExit(4)

if __name__=="__main__":main()
