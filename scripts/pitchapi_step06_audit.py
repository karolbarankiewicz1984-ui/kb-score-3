#!/usr/bin/env python3
"""KB Score 3.0 Step 06: bounded read-only PitchAPI historical xG coverage.

Audit data source ONLY. Realized xG from shots AFTER the match is NOT a
pre-match fixture feature. Never infer missing xG as zero or expose API keys.
"""
from __future__ import annotations
import datetime as dt
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PITCH = "https://api.pitchapi.dev"
FOOTBALL = "https://v3.football.api-sports.io"
MAX_PITCH = 110
MAX_FOOTBALL = 45
TOP5 = [
    ("Premier League", "ENG", 39),
    ("La Liga", "ESP", 140),
    ("Serie A", "ITA", 135),
    ("Bundesliga", "GER", 78),
    ("Ligue 1", "FRA", 61),
]
SEASONS = tuple(range(2021, 2027))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
VALID_ID = re.compile(r"^[a-z]_[A-Za-z0-9]{6}$")

class Client:
    def __init__(self, base, env_name, header, cap):
        self.base = base
        self.key = os.environ.get(env_name, "").strip()
        self.header = header
        self.cap = cap
        self.calls = 0
        self.errors = []
        if not self.key:
            raise RuntimeError("MISSING_SECRET_" + env_name)

    def get(self, route, **params):
        if self.calls >= self.cap:
            raise RuntimeError("CALL_BUDGET_EXHAUSTED")
        self.calls += 1
        url = self.base + route
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET", headers={
            self.header: self.key, "Accept": "application/json", "User-Agent": UA
        })
        try:
            with urllib.request.urlopen(req, timeout=16) as response:
                if response.status != 200:
                    raise RuntimeError("BAD_HTTP_STATUS")
                data = json.loads(response.read(12_000_000))
            if not isinstance(data, dict) or data.get("error") or data.get("errors"):
                self.errors.append({"endpoint": route.split("?")[0], "type": "API_ERROR"})
                return None
            return data
        except urllib.error.HTTPError as e:
            self.errors.append({"endpoint": route, "type": "HTTP_" + str(e.code)})
        except (urllib.error.URLError, TimeoutError):
            self.errors.append({"endpoint": route, "type": "NETWORK_OR_TIMEOUT"})
        except (ValueError, TypeError):
            self.errors.append({"endpoint": route, "type": "JSON_ERROR"})
        except RuntimeError:
            self.errors.append({"endpoint": route, "type": "RESPONSE_ERROR"})
        return None

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return re.sub(r"\s+", " ", s)

def select_two(games):
    good = sorted(
        (g for g in games if isinstance(g, dict) and g.get("status") == "finished"
         and VALID_ID.fullmatch(str(g.get("id", ""))) and g.get("time_utc")),
        key=lambda g: (g["time_utc"], g["id"])
    )
    if not good:
        return [], 0
    return [good[i] for i in sorted(set((len(good)//4, (3*len(good))//4)))], len(good)

def parse_shots(payload, home_id, away_id):
    """A legitimate 0 xG total is possible ONLY with a complete, valid shot feed."""
    data = (payload or {}).get("data")
    if not isinstance(data, dict):
        return {"state": "INVALID_RESPONSE", "shots": None}
    periods = data.get("periods")
    if not isinstance(periods, list):
        return {"state": "NO_PERIOD_LIST", "shots": None}
    sums = {home_id: 0.0, away_id: 0.0}
    count = {home_id: 0, away_id: 0}
    missing = unknown_team = invalid = 0
    for period in periods:
        shots = period.get("shots") if isinstance(period, dict) else None
        if not isinstance(shots, list):
            return {"state": "INCOMPLETE_PERIOD", "shots": None}
        for shot in shots:
            if not isinstance(shot, dict):
                invalid += 1
                continue
            team = shot.get("team_id")
            xg = shot.get("expected_goals")
            if team not in sums:
                unknown_team += 1
                continue
            if not isinstance(xg, (int, float)) or isinstance(xg, bool):
                missing += 1
                continue
            if not 0 <= xg <= 1:
                invalid += 1
                continue
            sums[team] += float(xg)
            count[team] += 1
    total = sum(count.values())
    state = ("COMPLETE_SHOT_XG" if not missing and not invalid and not unknown_team and total > 0
             else "NO_SHOTS" if total == 0 and not missing and not invalid and not unknown_team
             else "PARTIAL_SHOT_XG")
    return {"state": state, "shots": total, "missing_xg": missing,
            "invalid_xg": invalid, "unknown_team": unknown_team,
            "home_shots": count[home_id], "away_shots": count[away_id],
            "home_xg_sum": round(sums[home_id], 4) if state == "COMPLETE_SHOT_XG" else None,
            "away_xg_sum": round(sums[away_id], 4) if state == "COMPLETE_SHOT_XG" else None}

def find_af_match(pitch, fixtures):
    """Strict pair; ambiguous and alias suggestions remain NON-VERIFIED."""
    dt_s = str(pitch.get("time_utc", ""))[:10]
    p_home = norm((pitch.get("home_team") or {}).get("name"))
    p_away = norm((pitch.get("away_team") or {}).get("name"))
    home_score, away_score = pitch.get("score_home"), pitch.get("score_away")
    same_day = []
    for f in fixtures:
        if str((f.get("fixture") or {}).get("date") or "")[:10] != dt_s:
            continue
        if (f.get("goals") or {}).get("home") != home_score or (f.get("goals") or {}).get("away") != away_score:
            continue
        names = f.get("teams") or {}
        h, a = norm((names.get("home") or {}).get("name")), norm((names.get("away") or {}).get("name"))
        same_day.append((f,h,a))
    exact = [(f,h,a) for f,h,a in same_day if h==p_home and a==p_away]
    if len(exact)==1:
        return {"state": "EXACT_NAMES_DATE_SCORE", "api_football_fixture_id": exact[0][0]["fixture"]["id"]}
    # Score/date only or alias similarity must not silently authenticate a pair.
    close = [(f,h,a) for f,h,a in same_day if min(
        difflib.SequenceMatcher(None,p_home,h).ratio(),
        difflib.SequenceMatcher(None,p_away,a).ratio())>=0.70]
    if len(close)==1:
        return {"state": "ALIAS_CANDIDATE_UNVERIFIED", "api_football_fixture_id": close[0][0]["fixture"]["id"]}
    return {"state": "AMBIGUOUS_OR_UNMATCHED", "api_football_fixture_id": None}

def analyze(outdir: Path):
    pitch = Client(PITCH,"PITCHAPI_API_KEY","X-API-KEY",MAX_PITCH)
    football = Client(FOOTBALL,"API_FOOTBALL_KEY","x-apisports-key",MAX_FOOTBALL)
    result = {"schema":"kb30-pitchapi-audit-v1",
              "run_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
              "source":"PitchAPI", "sample_policy":"two deterministic finished matches (25%, 75%) per available league-season",
              "rows":[], "samples":[], "league_catalog":[],"limitations":[
                 "League catalog seasons and played match counts do not prove shot-xG availability for every fixture.",
                 "Shot xG is a post-match label/history input for LATER matches only, not a prematch snapshot.",
                 "Missing/null shot xG is never a legitimate numeric zero.",
                 "Score/date and fuzzy team matches are suggestions, not verified one-to-one linkage.",
                 "Historical fixture lists queried today do not prove data was available prematch.",
                 "This is source audit, NOT a trained predictive model."],
              "provider_errors":{}}
    catalog=pitch.get("/v1/leagues")
    leagues=(catalog or {}).get("data",{}).get("leagues")
    if not isinstance(leagues,list):
        result["outcome"]="BLOCKED_CATALOG"
        return finish(outdir,result,pitch,football)
    result["catalog_league_count"]=len(leagues)
    for label,country,af_id in TOP5:
        matches=[l for l in leagues if norm(l.get("name"))==norm(label) and
                 str(l.get("country_code") or "").upper()==country]
        if len(matches)!=1:
            matches=[l for l in leagues if norm(l.get("name"))==norm(label)]
        selected=matches[0] if len(matches)==1 else None
        result["league_catalog"].append({
            "expected_league":label,"expected_country":country,
            "found":selected is not None, "pitch_id": selected.get("id") if selected else None,
            "declared_seasons": selected.get("seasons",[]) if selected else []
        })
        for year in SEASONS:
            season=f"{year}/{year+1}"
            row={"league":label,"pitch_league_id":selected.get("id") if selected else None,
                 "api_football_league_id":af_id,"season":season,
                 "in_catalog":bool(selected and season in selected.get("seasons",[])),
                 "list_state":"NOT_TESTED","played_count":None,
                 "sample_count":0,"complete_xg_count":0,"partial_xg_count":0,
                 "strict_pair_count":0,"alias_candidates":0,"unmatched_pair_count":0}
            result["rows"].append(row)
            if not selected or season not in selected.get("seasons",[]):
                row["list_state"]="NOT_IN_CATALOG";continue
            listing=pitch.get(f"/v1/leagues/{selected['id']}/matches",season=season)
            games=(listing or {}).get("data",{}).get("matches")
            if not isinstance(games,list):
                row["list_state"]="NO_MATCH_LIST";continue
            row["list_state"]="OK"
            chosen,finished_count=select_two(games)
            row["played_count"]=finished_count
            for m in chosen:
                mid=m["id"]; row["sample_count"]+=1
                h=(m.get("home_team") or {}).get("id")
                a=(m.get("away_team") or {}).get("id")
                metric={"state":"INVALID_TEAM_IDS","shots":None}
                if h and a and h!=a:
                    metric=parse_shots(pitch.get(f"/v1/matches/{mid}/shots"),h,a)
                if metric["state"]=="COMPLETE_SHOT_XG":row["complete_xg_count"]+=1
                elif metric["state"]!="NO_SHOTS":row["partial_xg_count"]+=1
                api_match={"state":"NOT_CHECKED","api_football_fixture_id":None}
                # On representative first sample per season, fetch API-Football
                # same-day fixture list to verify country/team/date/score.
                if row["sample_count"]==1:
                    day=str(m.get("time_utc") or "")[:10]
                    af=football.get("/fixtures",league=af_id,season=year,date=day)
                    af_fixtures=(af or {}).get("response")
                    if isinstance(af_fixtures,list):
                        api_match=find_af_match(m,af_fixtures)
                    else:api_match={"state":"API_FOOTBALL_LIST_UNAVAILABLE","api_football_fixture_id":None}
                    if api_match["state"]=="EXACT_NAMES_DATE_SCORE":row["strict_pair_count"]+=1
                    elif api_match["state"]=="ALIAS_CANDIDATE_UNVERIFIED":row["alias_candidates"]+=1
                    else:row["unmatched_pair_count"]+=1
                result["samples"].append({"league":label,"season":season,
                    "pitch_match_id":mid,"kickoff_utc":m.get("time_utc"),
                    "home_team":(m.get("home_team") or {}).get("name"),
                    "away_team":(m.get("away_team") or {}).get("name"),
                    "score_home":m.get("score_home"),"score_away":m.get("score_away"),
                    "shot_xg":metric,"api_football_pair":api_match})
    result["outcome"]="AUDIT_COLLECTED"
    return finish(outdir,result,pitch,football)

def finish(folder,result,pitch,football):
    result["requests"]={"pitchapi":pitch.calls,"api_football":football.calls,
                        "pitch_limit":pitch.cap,"football_limit":football.cap}
    result["provider_errors"]={"pitchapi":pitch.errors,"api_football":football.errors}
    rows=result["rows"];samples=result["samples"]
    result["summary"]={
        "target_rows":len(rows),
        "listed_rows":sum(r["list_state"]=="OK" for r in rows),
        "played_matches_sum":sum(r["played_count"] or 0 for r in rows),
        "shots_examined":len(samples),
        "complete_xg_samples":sum(s["shot_xg"]["state"]=="COMPLETE_SHOT_XG" for s in samples),
        "partial_or_missing_xg_samples":sum(s["shot_xg"]["state"]!="COMPLETE_SHOT_XG" for s in samples),
        "strict_verified_api_football_matches":sum(s["api_football_pair"]["state"]=="EXACT_NAMES_DATE_SCORE" for s in samples),
        "candidate_alias_matches":sum(s["api_football_pair"]["state"]=="ALIAS_CANDIDATE_UNVERIFIED" for s in samples),
        "provider_errors_total":len(pitch.errors)+len(football.errors)
    }
    folder.mkdir(parents=True,exist_ok=True)
    day=dt.datetime.now(dt.timezone.utc).date().isoformat()
    json_path=folder/f"PITCHAPI_STEP06_{day}.json"
    md_path=folder/f"PITCHAPI_STEP06_{day}.md"
    json_path.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    s=result["summary"]
    lines=["# KB Score 3.0 — Audyt PitchAPI, krok 06","",
           "Odczyt UTC: "+result["run_utc"],"Stan testu: "+result["outcome"]+"; odbiór GATE 06 wymaga kontroli raportu.","",
           "## Wyniki zbiorcze","",
           "| Pozycja | Wynik |","|---|---:|"]
    for k,v in s.items():lines.append(f"| {k} | {v} |")
    lines+=["| PitchAPI calls | "+str(pitch.calls)+" / "+str(pitch.cap)+" |",
           "| API-Football crosscheck calls | "+str(football.calls)+" / "+str(football.cap)+" |",
           "","## Liga × sezon — historia i xG próbek","",
           "| Liga | Sezon | W katalogu | Mecze rozegrane | Sprawdzono xG | Pełne xG | Sparowane dokładnie |",
           "|---|---|:---:|---:|---:|---:|---:|"]
    for r in rows:
        val=lambda x:"BRAK" if x is None else str(x)
        lines.append(f"| {r['league']} | {r['season']} | {'TAK' if r['in_catalog'] else 'NIE'} | {val(r['played_count'])} | {r['sample_count']} | {r['complete_xg_count']} | {r['strict_pair_count']} |")
    lines+=["","## Przykłady konkretnych meczów i mapowania","",
            "| Liga | Sezon | Pitch ID | Mecz | xG | Strzały | API-Football ID | Pairing |",
            "|---|---|---|---|---|---:|---|---|"]
    for m in samples:
        d=m["shot_xg"]; q=m["api_football_pair"]
        xg=(f"{d['home_xg_sum']}/{d['away_xg_sum']}" if d["state"]=="COMPLETE_SHOT_XG" else d["state"])
        lines.append(f"| {m['league']} | {m['season']} | {m['pitch_match_id']} | {m['home_team']} – {m['away_team']} | {xg} | {d['shots'] if d['shots'] is not None else 'BRAK'} | {q.get('api_football_fixture_id') or 'BRAK'} | {q['state']} |")
    lines+=["","## Zastrzeżenia",""]+["- "+k for k in result["limitations"]]
    if pitch.errors or football.errors:
        lines+=["","## Diagnostyka HTTP i błędy bez sekretów",""]
        lines+=["- PitchAPI "+str(x["endpoint"])+": "+x["type"] for x in pitch.errors]
        lines+=["- API-Football "+str(x["endpoint"])+": "+x["type"] for x in football.errors]
    lines+=["","**Brak danych to nie zero.** xG dotyczy zakończonych historycznych spotkań, do budowy cech dla późniejszych spotkań używać tylko wcześniejszej historii.","",
            "**GATE 06: DO ODBIORU / PENDING** do czasu niezależnego potwierdzenia wyników.",""]
    md_path.write_text("\n".join(lines),encoding="utf-8")
    print("PITCHAPI_STEP06_SAFESUMMARY "+json.dumps({**s,"pitch_calls":pitch.calls,"football_calls":football.calls,"outcome":result["outcome"]}))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as fh:
            fh.write("\n".join(lines[:26])+"\n")
    return 0 if result["outcome"]=="AUDIT_COLLECTED" and s["listed_rows"]>=10 and s["shots_examined"]>=15 else 2

if __name__=="__main__":
    try:
        sys.exit(analyze(Path("step06-output")))
    except Exception as e:
        print("STEP06_BLOCKED_"+type(e).__name__)
        sys.exit(3)
