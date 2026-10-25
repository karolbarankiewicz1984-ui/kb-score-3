"""Gate 07 — conservative, auditable PitchAPI ↔ API-Football fixture crosswalk.

Reads frozen Gate 06 sample (60 matches), queries API-Football once per
league-season, and outputs only deterministic, carefully verified mappings.
No fuzzy automatic merges, no raw API response persistence, no ML training.
"""
from __future__ import annotations
from collections import Counter, defaultdict
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

INPUT = Path("data/audits/PITCHAPI_STEP06_2026-10-25.json")
OUTPUT = Path("data/audits/STEP07_MATCH_CROSSWALK_2026-10-25.json")
REPORT = Path("docs/audits/STEP07_MATCH_CROSSWALK_2026-10-25.md")
FOOTBALL_URL = "https://v3.football.api-sports.io/fixtures"
LEAGUE_IDS = {"Premier League": 39, "La Liga": 140, "Serie A": 135,
              "Bundesliga": 78, "Ligue 1": 61}
MAX_REQUESTS = 32
MIN_REMAINING = 250
STRICT_SECONDS = 20 * 60
NEAR_SECONDS = 72 * 3600
FINISHED = {"FT", "AET", "PEN"}
# Intentional: no broad synonyms or automatic aliases; doubtful candidates
# are explicitly sent to the review queue instead of silently approved.

def norm(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c)).casefold()
    value = value.replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", value))

def as_utc(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo is not None else None
    except ValueError:
        return None

def same_result(pitch, football):
    goals = football.get("goals") or {}
    h, a = pitch.get("score_home"), pitch.get("score_away")
    return (type(h) is int and type(a) is int and
            type(goals.get("home")) is int and type(goals.get("away")) is int and
            h == goals.get("home") and a == goals.get("away"))

def flattened_game(f):
    fx, teams, goals = f.get("fixture") or {}, f.get("teams") or {}, f.get("goals") or {}
    h, a = teams.get("home") or {}, teams.get("away") or {}
    return {"football_id": fx.get("id"), "kickoff_utc": fx.get("date"),
            "status": (fx.get("status") or {}).get("short"),
            "home_team": h.get("name"), "away_team": a.get("name"),
            "home_team_id": h.get("id"), "away_team_id": a.get("id"),
            "score_home": goals.get("home"), "score_away": goals.get("away")}

def classify(pitch, full_fixtures):
    """STRICT only: same league-season, UTC within 20m, both exact names, score.

    Not even near-duplicates get auto-joined. Review queue always has evidence.
    """
    when = as_utc(pitch.get("kickoff_utc"))
    if not when:
        return {"state": "REVIEW_INVALID_KICKOFF", "football_id": None, "candidates": []}
    if not pitch.get("home_team") or not pitch.get("away_team"):
        return {"state": "REVIEW_MISSING_TEAM", "football_id": None, "candidates": []}
    strict = []
    nearby = []
    for f in full_fixtures:
        fx = f.get("fixture") or {}
        dt = as_utc(fx.get("date"))
        if not dt or not isinstance(fx.get("id"), int):
            continue
        delta = abs((dt-when).total_seconds())
        if delta > NEAR_SECONDS:
            continue
        teams = f.get("teams") or {}
        home = (teams.get("home") or {}).get("name")
        away = (teams.get("away") or {}).get("name")
        exact_names = norm(home) == norm(pitch["home_team"]) and norm(away) == norm(pitch["away_team"])
        goal_ok = same_result(pitch, f)
        status_ok = ((fx.get("status") or {}).get("short") in FINISHED)
        if delta <= STRICT_SECONDS and exact_names and goal_ok and status_ok:
            strict.append(flattened_game(f))
        else:
            a = SequenceMatcher(None, norm(home), norm(pitch["home_team"])).ratio()
            b = SequenceMatcher(None, norm(away), norm(pitch["away_team"])).ratio()
            if (a >= .55 and b >= .55) or exact_names:
                candidate = flattened_game(f)
                candidate.update({"time_delta_minutes": int(round(delta/60)),
                                  "name_similarity_home": round(a, 3),
                                  "name_similarity_away": round(b, 3),
                                  "same_score": goal_ok, "finished": status_ok,
                                  "home_away_swapped": (
                                      norm(home)==norm(pitch["away_team"]) and
                                      norm(away)==norm(pitch["home_team"]))})
                nearby.append(candidate)
    if len(strict) == 1:
        return {"state": "STRICT", "football_id": strict[0]["football_id"],
                "matched": strict[0], "candidates": []}
    if len(strict) > 1:
        return {"state": "REVIEW_MULTIPLE_EXACT", "football_id": None,
                "candidates": strict}
    nearby.sort(key=lambda c: (c["time_delta_minutes"],
                 -(c["name_similarity_home"]+c["name_similarity_away"]),
                 c["football_id"]))
    return {"state": "REVIEW_CANDIDATE" if nearby else "UNMATCHED",
            "football_id": None, "candidates": nearby[:3]}

def no_duplicate_mapping(entries):
    """Any key collision invalidates ALL involved auto-pairs, never pick a winner."""
    pitch_counts = Counter(e["pitch_match_id"] for e in entries)
    id_to_rows = defaultdict(list)
    for e in entries:
        if e["state"] == "STRICT":
            id_to_rows[e["football_id"]].append(e)
    for e in entries:
        if pitch_counts[e["pitch_match_id"]] > 1:
            e.update({"state": "REVIEW_DUPLICATE_PITCH_ID", "football_id": None,
                      "matched": None})
    for rows in id_to_rows.values():
        if len(rows) > 1:
            for e in rows:
                e.update({"state": "REVIEW_DUPLICATE_FOOTBALL_ID",
                          "football_id": None, "matched": None})

def evaluate(pitch_samples, football_by_season):
    output = []
    for s in pitch_samples:
        year = int(str(s.get("season") or "0")[:4])
        group = (s.get("league"), year)
        if group not in football_by_season:
            state = {"state": "REVIEW_SOURCE_NOT_LOADED",
                     "football_id": None, "candidates": []}
        else:
            state = classify(s, football_by_season[group])
        record = {"pitch_match_id": s["pitch_match_id"], "league": s["league"],
                  "season": s["season"], "kickoff_utc": s["kickoff_utc"],
                  "pitch_home": s["home_team"], "pitch_away": s["away_team"],
                  "pitch_score": [s["score_home"], s["score_away"]],
                  "previous_gate06_pair": s.get("api_football_pair"),
                  **state}
        output.append(record)
    no_duplicate_mapping(output)
    for r in output:
        historical = r.get("previous_gate06_pair") or {}
        if historical.get("state") == "EXACT_NAMES_DATE_SCORE":
            r["independent_crosscheck"] = (
                "CONSISTENT" if r["state"] == "STRICT" and
                r["football_id"] == historical.get("api_football_fixture_id")
                else "CONFLICT")
        elif historical.get("api_football_fixture_id"):
            r["independent_crosscheck"] = (
                "SAME_CANDIDATE" if r["football_id"] == historical.get("api_football_fixture_id")
                else "REQUIRES_REVIEW")
        else:
            r["independent_crosscheck"] = "NOT_PREVIOUSLY_VERIFIED"
    return output

def verify_fixture_uniqueness(fixtures):
    ids = [x.get("fixture", {}).get("id") for x in fixtures]
    ids = [x for x in ids if x is not None]
    return len(ids) == len(set(ids))

def call_fixture_list(key, league, year, observed):
    if observed["calls"] >= MAX_REQUESTS:
        raise RuntimeError("REQUEST_LIMIT_STOP")
    if observed["calls"]:
        time.sleep(.55)
    url = FOOTBALL_URL + "?" + urlencode({"league": league, "season": year})
    request = Request(url, headers={"x-apisports-key": key, "Accept": "application/json",
                                   "User-Agent": "KBScore3-IdentityAudit/1.0"}, method="GET")
    observed["calls"] += 1
    try:
        with urlopen(request,timeout=18) as r:
            raw = r.read(15_000_000)
            limit = r.headers.get("x-ratelimit-requests-limit")
            rem = r.headers.get("x-ratelimit-requests-remaining")
            if limit and limit.isdigit(): observed["daily_limit"] = int(limit)
            if rem and rem.isdigit(): observed["daily_remaining"] = int(rem)
    except HTTPError as e:
        raise RuntimeError("FOOTBALL_HTTP_"+str(e.code)) from None
    except (URLError,TimeoutError):
        raise RuntimeError("FOOTBALL_TRANSPORT_ERROR") from None
    result = json.loads(raw)
    if not isinstance(result, dict) or result.get("errors") or not isinstance(result.get("response"), list):
        raise RuntimeError("FOOTBALL_INVALID_RESPONSE")
    if result.get("paging",{}).get("total",1) != 1:
        raise RuntimeError("FOOTBALL_FIXTURES_PAGING_UNEXPECTED")
    if (observed["daily_remaining"] is not None and
        observed["daily_remaining"] < MIN_REMAINING):
        raise RuntimeError("FOOTBALL_DAILY_QUOTA_SAFETY_STOP")
    return result["response"]

def main():
    key = os.environ.get("API_FOOTBALL_KEY","").strip()
    if not key:
        raise SystemExit("MISSING_SECRET_API_FOOTBALL_KEY")
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    samples = source.get("samples")
    if not isinstance(samples,list) or len(samples) != 60:
        raise RuntimeError("EXPECTED_60_GATE06_SAMPLES")
    groups = sorted({(s["league"],int(s["season"][:4])) for s in samples})
    if len(groups) != 30:
        raise RuntimeError("EXPECTED_30_GROUPS")
    observed = {"calls":0, "daily_limit":None, "daily_remaining":None}
    fixture_lists,duplicates = {},[]
    for league,year in groups:
        fixture_lists[(league,year)]=call_fixture_list(key,LEAGUE_IDS[league],year,observed)
        if not verify_fixture_uniqueness(fixture_lists[(league,year)]):
            duplicates.append({"league":league,"season_start":year})
    matches=evaluate(samples,fixture_lists)
    counts=dict(sorted(Counter(r["state"] for r in matches).items()))
    conflicts=[r["pitch_match_id"] for r in matches if r["independent_crosscheck"]=="CONFLICT"]
    dup_result=[r["pitch_match_id"] for r in matches if "DUPLICATE" in r["state"]]
    verified=[r for r in matches if r["state"]=="STRICT"]
    reviews=[r for r in matches if r["state"]!="STRICT"]
    payload={"schema":"kb30-cross-provider-identity-v1","run_utc":datetime.now(timezone.utc).isoformat(),
       "source_pitchapi":"data/audits/PITCHAPI_STEP06_2026-10-25.json",
       "validation_policy":"league+season, same home and away after conservative normalization, same score, kickoff <=20 min UTC, finished, unique IDs; no fuzzy auto-match",
       "outcome":"AUDIT_COLLECTED_NOT_GATE_ACCEPTED",
       "samples":len(matches),"groups":len(groups),"status_counts":counts,
       "strict_count":len(verified),"review_count":len(reviews),"crosscheck_conflicts":conflicts,
       "duplicates_input":duplicates,"duplicate_mapping":dup_result,
       "api_football_calls":observed["calls"],"api_daily_limit":observed["daily_limit"],
       "api_daily_remaining":observed["daily_remaining"],
       "fixtures_checked":sum(map(len,fixture_lists.values())),
       "mapping":matches,
       "review_queue":reviews,
       "limitations":["60 deterministic sample matches; not a full 9297 fixture migration.",
          "Alias-like or ambiguous names never auto-map; they stay queued for review.",
          "Postmatch score used for historical ID confirmation only, NEVER as a pregame predictive feature.",
          "Temporal delta UTC; local display may differ by daylight saving rules.",
          "Fixtures can be rescheduled; same teams on new date require renewed confirmation."]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Gate 07 — API-Football ↔ PitchAPI identity audit","",
      f"UTC: {payload['run_utc']}",
      f"Samples: {len(matches)} in {len(groups)} league-seasons; calls: {observed['calls']}; fixtures scanned: {payload['fixtures_checked']}",
      f"STRICT: {len(verified)}; REVIEW/UNMATCHED: {len(reviews)}; crosscheck conflicts: {len(conflicts)}; duplicates: {len(dup_result)}",
      "", "**Only STRICT rows can be auto-used. Others are NOT linked.**",
      "", "| Pitch ID | Competition | Fixture | API-F ID | State | Detail |",
      "|---|---|---|---|---|---|"]
    for r in matches:
        c=r["candidates"][:1] if r.get("candidates") else []
        hint=(f"Candidate {c[0]['football_id']} / {c[0]['home_team']} – {c[0]['away_team']} / {c[0]['time_delta_minutes']}min / score={c[0]['same_score']}" if c else "—")
        lines.append(f"| {r['pitch_match_id']} | {r['league']} {r['season']} | {r['pitch_home']} – {r['pitch_away']} | {r.get('football_id') or '—'} | {r['state']} | {hint} |")
    lines+=["","## Reviews and quality controls",
            "- Check original team names, scores and UTC kickoff before any manual alias approval.",
            "- Ambiguous, swapped home/away, score conflict and postponed matches cannot auto-merge.",
            "- One-to-one mapping is mandatory; duplicates are quarantined.",
            "- xG is postmatch context for later games, never used as prematch data for its own game.",
            "- Sample is not historical full coverage; the complete crosswalk will grow in the dedicated import stages."]
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    summ={"samples":len(matches),"strict":len(verified),"review":len(reviews),
          "previous_strict_conflicts":len(conflicts),"duplicate_mapping":len(dup_result),
          "duplicate_input":len(duplicates),"api_calls":observed["calls"],"fixtures_checked":payload["fixtures_checked"]}
    print("GATE07_SUMMARY "+json.dumps(summ,sort_keys=True))
    with open(os.getenv("GITHUB_STEP_SUMMARY","/dev/null"),"a",encoding="utf-8") as f:
        f.write("\n".join(lines[:8])+"\n")
    # Some review entries are EXPECTED and explicitly isolated, not an audit failure.
    if conflicts or duplicates or dup_result or len(verified)==0:
        raise SystemExit("GATE07_VALIDATION_FAILED")
if __name__=="__main__":
    main()
