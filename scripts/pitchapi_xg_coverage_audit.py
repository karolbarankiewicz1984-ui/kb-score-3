#!/usr/bin/env python3
"""KB3 gate 06: bounded read-only PitchAPI xG coverage audit; no ML training."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LEAGUES = {
  39: ("Premier League", "ENG", ("premier league",)),
  140: ("La Liga", "ESP", ("la liga", "laliga", "primera division")),
  135: ("Serie A", "ITA", ("serie a",)),
  78: ("Bundesliga", "GER", ("bundesliga",)),
  61: ("Ligue 1", "FRA", ("ligue 1",)),
}
START_YEARS = (2022, 2023, 2024, 2025, 2026)
PITCH_MAX = 115
FOOTBALL_MAX = 30
TOKEN_PATTERN = re.compile(r"^(?:m_|l_)")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129.0.0.0 Safari/537.36"


def norm(x):
    s = unicodedata.normalize("NFKD", x or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(w for w in s.split() if w not in {"fc", "cf", "ac", "sc", "the", "football", "club", "de"})


def picked(items, n=3):
    if not items:
        return []
    return [items[i] for i in sorted(set(round((len(items)-1)*q/(n+1)) for q in range(1, n+1)))]


def shots_summary(payload, home_id, away_id):
    if not isinstance(payload, dict) or not isinstance(payload.get("periods"), list):
        return {"state": "MISSING", "shots": None, "with_xg": None, "invalid": None,
                "xg_home": None, "xg_away": None}
    shots = [s for part in payload["periods"] if isinstance(part,dict)
             for s in (part.get("shots") or []) if isinstance(s, dict)]
    counts = Counter()
    xgs = Counter()
    bad = 0
    with_xg = 0
    for s in shots:
        value = s.get("expected_goals")
        team = s.get("team_id")
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            continue
        if value < 0 or value > 1 or team not in (home_id, away_id):
            bad += 1
            continue
        with_xg += 1
        counts[team] += 1
        xgs[team] += float(value)
    state = "COMPLETE_WITH_XG" if shots and len(shots) == with_xg and counts[home_id] and counts[away_id] else (
        "PARTIAL_XG" if with_xg else ("NO_SHOTS" if not shots else "NO_NUMERIC_XG"))
    return {"state": state, "shots": len(shots), "with_xg": with_xg,
            "invalid": bad, "xg_home": round(xgs[home_id], 4) if counts[home_id] else None,
            "xg_away": round(xgs[away_id], 4) if counts[away_id] else None}


def matching_pitch_to_football(pitch, football_games):
    try:
        when = datetime.fromisoformat(pitch["time_utc"].replace("Z", "+00:00"))
    except (ValueError, KeyError, AttributeError):
        return {"state": "MISSING_KICKOFF", "fixture_id": None}
    options = []
    for game in football_games:
        if not isinstance(game, dict):
            continue
        fixture, teams = game.get("fixture") or {}, game.get("teams") or {}
        try:
            t2 = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if abs((when-t2).total_seconds()) > 4*3600:
            continue
        pg = (pitch.get("home_team") or {}).get("name", "")
        pa = (pitch.get("away_team") or {}).get("name", "")
        ag = (teams.get("home") or {}).get("name", "")
        aa = (teams.get("away") or {}).get("name", "")
        sim_h = SequenceMatcher(None,norm(pg),norm(ag)).ratio()
        sim_a = SequenceMatcher(None,norm(pa),norm(aa)).ratio()
        score = (game.get("goals") or {})
        goal_ok = score.get("home") == pitch.get("score_home") and score.get("away") == pitch.get("score_away")
        options.append((sim_h+sim_a, sim_h, sim_a, goal_ok, fixture.get("id")))
    if not options:
        return {"state":"NO_TIME_MATCH","fixture_id":None}
    options.sort(reverse=True)
    best=options[0]
    if best[1] >= .68 and best[2] >= .68 and best[3] and (len(options)==1 or best[0]-options[1][0]>.12):
        return {"state":"MATCHED","fixture_id":best[4]}
    return {"state":"AMBIGUOUS_OR_MISMATCH","fixture_id":None}


class Client:
    def __init__(self, name, base, key, ceiling, header):
        self.name,self.base,self.key,self.ceiling,self.header=name,base,key,ceiling,header
        self.calls=0
        self.failures=[]
    def get(self, path, params=None):
        if self.calls >= self.ceiling:
            raise RuntimeError(self.name+"_HARD_REQUEST_BUDGET")
        self.calls+=1
        url=self.base+path+("?"+urlencode(params) if params else "")
        request=Request(url, headers={self.header:self.key,"Accept":"application/json","User-Agent":UA}, method="GET")
        try:
            with urlopen(request,timeout=20) as res:
                if res.status != 200:
                    self.failures.append({"kind":"HTTP","status":res.status})
                    return None
                data=json.loads(res.read(14_000_000))
            if not isinstance(data,dict) or data.get("errors") or data.get("error"):
                self.failures.append({"kind":"API_ERROR","endpoint":path.split("/")[1]})
                return None
            return data.get("data") if self.name=="pitchapi" else data.get("response")
        except HTTPError as e:
            self.failures.append({"kind":"HTTP","status":e.code,"endpoint":path.split("/")[1]})
        except (URLError,TimeoutError):
            self.failures.append({"kind":"NETWORK","endpoint":path.split("/")[1]})
        except (ValueError, TypeError):
            self.failures.append({"kind":"JSON","endpoint":path.split("/")[1]})
        return None


def league_lookup(catalog, country, aliases):
    leagues=(catalog or {}).get("leagues")
    if not isinstance(leagues,list):
        return None
    scores=[]
    for lg in leagues:
        if not isinstance(lg,dict) or (lg.get("country_code") or "").upper()!=country:
            continue
        title=norm(lg.get("name"))
        grade=max(SequenceMatcher(None,title,norm(alias)).ratio() for alias in aliases)
        if grade>.76:
            scores.append((grade,lg))
    return max(scores,key=lambda x:x[0])[1] if scores else None


def build_report(target):
    key=os.environ.get("PITCHAPI_API_KEY","").strip()
    fk=os.environ.get("API_FOOTBALL_KEY","").strip()
    if not key or not fk:
        print("BLOCKED: missing configured secret; no values printed")
        return 3
    pitch=Client("pitchapi","https://api.pitchapi.dev","",PITCH_MAX,"X-API-KEY")
    pitch.key=key
    football=Client("football","https://v3.football.api-sports.io","",FOOTBALL_MAX,"x-apisports-key")
    football.key=fk
    snapshot={"schema":"kb3-step06-xg-audit-v1","generated_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"Five European top leagues, season starts 2022–2026",
        "leagues":[],"rows":[],"examples":[],"assumptions":[
          "PitchAPI catalog seasons are declarations, NOT proof all matches have xG",
          "PitchAPI historical post-match shots are inputs ONLY to reconstruct pre-match rolling features of subsequent matches",
          "API-Football fixture and PitchAPI fixture IDs differ; this audit stores only confident sampled matches",
          "No match/shot sample is a full-coverage guarantee; historical xG must never be used for the same game's prematch prediction",
          "Null xG is missing, not zero. xG range 0–1 per shot is validated.",
          "Predicted lineups before kickoff are not confirmed XI; no historical time provenance is assumed",
          "No new expenses; manual read-only audit; provider terms and fair-use should be respected",
        ]}
    catalog=pitch.get("/v1/leagues")
    if not isinstance((catalog or {}).get("leagues"),list):
        snapshot["outcome"]="BLOCKED_CATALOG"
        return output(target,snapshot,pitch,football)
    snapshot["catalog_leagues"]=len(catalog["leagues"])
    for lid,(label,country,aliases) in LEAGUES.items():
        lg=league_lookup(catalog,country,aliases)
        snap={"api_football_id":lid,"league":label,"pitch_id":lg.get("id") if lg else None,
              "pitch_label":lg.get("name") if lg else None,
              "advertised_seasons":lg.get("seasons",[]) if lg else [],
              "found":lg is not None}
        snapshot["leagues"].append(snap)
        if not lg:
            for season in START_YEARS:
                snapshot["rows"].append({"league":label,"year":season,"state":"LEAGUE_MISSING"})
            continue
        declared=lg.get("seasons") or []
        for year in START_YEARS:
            season=f"{year}/{year+1}"
            row={"league":label,"year":year,"pitch_season":season,
                 "catalog_listed":season in declared,"pitch_matches":None,
                 "pitch_finished":None,"api_football_fixtures":None,
                 "samples_selected":0,"samples_with_both_xg":0,"samples_crossmatched":0,
                 "sample_states":[],"error":None}
            snapshot["rows"].append(row)
            if season not in declared:
                row["error"]="SEASON_NOT_LISTED";continue
            pdata=pitch.get("/v1/leagues/"+lg["id"]+"/matches",{"season":season,"status":"played"})
            if not isinstance(pdata,dict) or not isinstance(pdata.get("matches"),list):
                row["error"]="PITCH_FIXTURE_LIST_UNAVAILABLE";continue
            games=pdata["matches"]
            finished=[g for g in games if isinstance(g,dict) and g.get("status")=="finished"
                      and isinstance(g.get("score_home"),int) and isinstance(g.get("score_away"),int)]
            finished.sort(key=lambda g:(g.get("time_utc") or "",g.get("id") or ""))
            row["pitch_matches"]=len(games);row["pitch_finished"]=len(finished)
            fa=football.get("/fixtures",{"league":lid,"season":year})
            fixtures=fa if isinstance(fa,list) else []
            row["api_football_fixtures"]=len(fixtures) if isinstance(fa,list) else None
            if not isinstance(fa,list):
                row["error"]="FOOTBALL_FIXTURE_LIST_UNAVAILABLE"
            for match in picked(finished):
                mid=match.get("id")
                if not isinstance(mid,str) or not mid.startswith("m_"):
                    row["error"]="BAD_MATCH_ID";continue
                resp=pitch.get("/v1/matches/"+mid+"/shots")
                hs=(match.get("home_team") or {}).get("id")
                aws=(match.get("away_team") or {}).get("id")
                xc=shots_summary(resp,hs,aws)
                linked=matching_pitch_to_football(match,fixtures) if fixtures else {"state":"NO_FOOTBALL_FIXTURES","fixture_id":None}
                row["samples_selected"]+=1
                row["sample_states"].append(xc["state"])
                row["samples_with_both_xg"]+=int(xc["state"]=="COMPLETE_WITH_XG")
                row["samples_crossmatched"]+=int(linked["state"]=="MATCHED")
                snapshot["examples"].append({
                  "league":label,"season":season,"pitch_id":mid,
                  "api_football_id":linked["fixture_id"],"match_link_state":linked["state"],
                  "kickoff_utc":match.get("time_utc"),
                  "home":(match.get("home_team") or {}).get("name"),
                  "away":(match.get("away_team") or {}).get("name"),
                  "score_home":match.get("score_home"),"score_away":match.get("score_away"),
                  "xg":xc
                })
                time.sleep(0.09)
    snapshot["outcome"]="COLLECTED"
    return output(target,snapshot,pitch,football)


def output(folder,s,p,f):
    s["requests_pitchapi"]=p.calls;s["requests_football"]=f.calls
    s["budget_pitchapi"]=PITCH_MAX;s["budget_football"]=FOOTBALL_MAX
    s["errors_pitchapi"]=p.failures;s["errors_football"]=f.failures
    rows=s["rows"];samples=s["examples"]
    s["summary"]={"row_count":len(rows),"listed_rows":sum(r.get("catalog_listed",False) for r in rows),
        "samples":len(samples),"both_xg":sum(x["xg"]["state"]=="COMPLETE_WITH_XG" for x in samples),
        "matched":sum(x["match_link_state"]=="MATCHED" for x in samples),
        "invalid_shots":sum(x["xg"].get("invalid") or 0 for x in samples)}
    folder.mkdir(parents=True,exist_ok=True)
    today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    js=folder/("PITCHAPI_STEP06_"+today+".json")
    md=folder/("PITCHAPI_STEP06_"+today+".md")
    js.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# KB Score 3.0 — PitchAPI xG audit","",
        "Data UTC: "+s["generated_utc"],"Stan: "+s["outcome"]+" (nie oznacza automatycznie PASS)",
        "","## Liczby",
        f'- Katalog: {s.get("catalog_leagues","BRAK")} lig',
        f'- Wiersze liga–sezon: {len(rows)}; sezony katalogowe: {s["summary"]["listed_rows"]}',
        f'- Próbki strzałów: {s["summary"]["samples"]}; xG obu zespołów: {s["summary"]["both_xg"]}; zgodne pary API-Football: {s["summary"]["matched"]}',
        f'- Błędne wartości strzałów: {s["summary"]["invalid_shots"]}',
        f'- Zapytania PitchAPI: {p.calls}/{PITCH_MAX}; API-Football: {f.calls}/{FOOTBALL_MAX}',
        f'- Błędy usług: {len(p.failures)} / {len(f.failures)}',
        "","## Pokrycie katalogowe i próbki","",
        "| Liga | Sezon | W katalogu | W PitchAPI ukończone | Mecze w API-Football | xG obu drużyn w próbkach | Dopasowane próbki |",
        "|---|---|:---:|---:|---:|---:|---:|"]
    for r in rows:
        val=lambda x: "BRAK" if x is None else str(x)
        lines.append(f'| {r["league"]} | {r["pitch_season"] if "pitch_season" in r else r["year"]} | {"TAK" if r.get("catalog_listed") else "NIE"} | {val(r.get("pitch_finished"))} | {val(r.get("api_football_fixtures"))} | {r.get("samples_with_both_xg",0)}/{r.get("samples_selected",0)} | {r.get("samples_crossmatched",0)}/{r.get("samples_selected",0)} |')
    lines.extend(["","## Przykłady (identyfikatory i rzeczywiste wartości, nie prognozy)","","| Data UTC | Liga | Mecz | Pitch ID | API-F ID | Status połączenia | Strzały/xG |","|---|---|---|---|---|---|---|"])
    for x in samples:
        sg=x["xg"]
        vals="BRAK" if sg["xg_home"] is None or sg["xg_away"] is None else f'{sg["xg_home"]}/{sg["xg_away"]}'
        lines.append(f'| {x["kickoff_utc"]} | {x["league"]} | {x["home"]} – {x["away"]} | {x["pitch_id"]} | {x["api_football_id"] or "BRAK"} | {x["match_link_state"]} | {sg["state"]}: {sg["shots"]} strzałów; H/A {vals} |')
    lines+=["","## Ograniczenia i zasady chronologii",""]
    lines+=["- "+z for z in s["assumptions"]]
    lines+=["","**BRAMKA 06: DO ODBIORU**, aż do osobnej weryfikacji niezależnej. Braki i niedopasowania nie są zerami."]
    md.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f'PITCHAPI_AUDIT {s["outcome"]} rows={len(rows)} samples={len(samples)} both_xg={s["summary"]["both_xg"]} crossmatched={s["summary"]["matched"]}')
    print(f'CALLS PitchAPI={p.calls}/{PITCH_MAX} API-Football={f.calls}/{FOOTBALL_MAX}, errors={len(p.failures)}+{len(f.failures)}')
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as out:
            out.write("\n".join(lines[:14])+"\n")
    return 0 if s["outcome"]=="COLLECTED" and len(rows)==25 and len(samples)>=15 else 2


if __name__=="__main__":
    try:
        sys.exit(build_report(Path("step06-output")))
    except Exception as exc:
        # Do not emit provider exception messages, URL headers, tokens, or response bodies.
        print("PITCHAPI_AUDIT_BLOCKED:",type(exc).__name__)
        sys.exit(3)
