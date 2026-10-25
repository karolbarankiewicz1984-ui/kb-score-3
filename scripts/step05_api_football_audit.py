#!/usr/bin/env python3
"""KB3 step 05: bounded, read-only API-Football coverage audit.

No training, no odds persistence, no credential output. Standard library only.
Run only in the explicitly approved private GitHub repository.
"""
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://v3.football.api-sports.io"
LEAGUES = (
    (39, "Premier League"),
    (140, "La Liga"),
    (78, "Bundesliga"),
    (135, "Serie A"),
    (61, "Ligue 1"),
)
SEASONS = (2022, 2023, 2024, 2025, 2026)
FINAL_STATUSES = {"FT", "AET", "PEN"}
MAX_CALLS = 145
MIN_DAILY_REMAINING = 350
TIMEOUT_SECONDS = 18
OUTPUT = Path("audit/step05")
STAT_TYPES = ("Fouls", "Corner Kicks", "Yellow Cards", "Red Cards",
              "Shots on Goal", "Total Shots", "Ball Possession")

def choose_samples(fixtures, n=2):
    """Deterministic chronological sample from finished fixtures."""
    eligible = []
    for item in fixtures:
        fixture = item.get("fixture") or {}
        state = ((fixture.get("status") or {}).get("short"))
        if state in FINAL_STATUSES and fixture.get("id") and fixture.get("date"):
            eligible.append((fixture["date"], int(fixture["id"])))
    eligible.sort()
    if not eligible:
        return []
    indices = sorted({min(len(eligible)-1, (len(eligible)*(i+1))//(n+1))
                      for i in range(n)})
    return [eligible[i][1] for i in indices]

def stats_flags(reply):
    """Count separately both teams having non-null values for required types."""
    if not isinstance(reply, list):
        return {"teams_present": 0, "both_any": False,
                "both_by_type": {t: False for t in STAT_TYPES}}
    sides = []
    for side in reply:
        d = {}
        for entry in side.get("statistics") or []:
            label = entry.get("type")
            d[label] = entry.get("value")
        sides.append(d)
    sides = sides[:2]
    both_any = len(sides) == 2 and all(any(v is not None for v in side.values()) for side in sides)
    return {
        "teams_present": len(sides), "both_any": both_any,
        "both_by_type": {
            t: len(sides) == 2 and all(side.get(t) is not None for side in sides)
            for t in STAT_TYPES
        },
    }

def lineup_flag(reply):
    if not isinstance(reply, list) or len(reply) != 2:
        return False
    return all(len((side or {}).get("startXI") or []) >= 11 for side in reply)

class Api:
    def __init__(self, key):
        self.key = key
        self.calls = 0
        self.daily_limit = None
        self.first_remaining = None
        self.last_remaining = None
        self.minute_limit = None
        self.error_count = 0

    def get(self, path, params=None):
        if self.calls >= MAX_CALLS:
            raise RuntimeError("MAX_CALLS_REACHED")
        query = "?" + urllib.parse.urlencode(params) if params else ""
        req = urllib.request.Request(
            BASE + "/" + path + query,
            headers={"x-apisports-key": self.key, "Accept": "application/json",
                     "User-Agent": "KBScore3-CoverageAudit/1.0"},
            method="GET",
        )
        # Rate control: no more than 2 requests/second in this audit.
        if self.calls:
            time.sleep(0.55)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read(15_000_000)
                remaining = response.headers.get("x-ratelimit-requests-remaining")
                daily = response.headers.get("x-ratelimit-requests-limit")
                minute = response.headers.get("x-ratelimit-limit")
                if remaining and remaining.isdigit():
                    self.last_remaining = int(remaining)
                    if self.first_remaining is None:
                        self.first_remaining = self.last_remaining
                if daily and daily.isdigit():
                    self.daily_limit = int(daily)
                if minute and minute.isdigit():
                    self.minute_limit = int(minute)
        except urllib.error.HTTPError as exc:
            self.calls += 1
            self.error_count += 1
            return {"error": "HTTP_" + str(exc.code), "response": [],
                    "results": 0, "paging": {}}
        except Exception as exc:
            self.calls += 1
            self.error_count += 1
            return {"error": type(exc).__name__, "response": [],
                    "results": 0, "paging": {}}
        self.calls += 1
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("INVALID_PAYLOAD_TYPE")
        except (ValueError, UnicodeError):
            self.error_count += 1
            return {"error": "INVALID_JSON", "response": [], "results": 0, "paging": {}}
        api_errors = payload.get("errors")
        if api_errors:
            self.error_count += 1
            # Never print an API error body: it may include billing data.
            return {"error": "API_ERROR", "response": [],
                    "results": 0, "paging": {}}
        if self.last_remaining is not None and self.last_remaining < MIN_DAILY_REMAINING:
            raise RuntimeError("DAILY_QUOTA_SAFETY_STOP")
        return payload

def main():
    key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not key:
        print("AUDIT_FAIL: MISSING_SECRET", flush=True)
        raise SystemExit(2)
    api = Api(key)
    start = dt.datetime.now(dt.timezone.utc).isoformat()
    status = api.get("status")
    if status.get("error") or not status.get("response"):
        print("AUDIT_FAIL: STATUS_UNAVAILABLE", flush=True)
        raise SystemExit(3)
    rows = []
    failure_rows = 0
    for league_id, league_name in LEAGUES:
        for year in SEASONS:
            league_reply = api.get("leagues", {"id": league_id, "season": year})
            fixture_reply = api.get("fixtures", {"league": league_id, "season": year})
            fixtures = fixture_reply.get("response") or []
            errors = []
            if league_reply.get("error"): errors.append("LEAGUES_" + league_reply["error"])
            if fixture_reply.get("error"): errors.append("FIXTURES_" + fixture_reply["error"])
            matching = []
            for lg in league_reply.get("response") or []:
                if int((lg.get("league") or {}).get("id") or -1) == league_id:
                    matching.extend([s for s in lg.get("seasons") or [] if s.get("year") == year])
            coverage = (matching[0].get("coverage") or {}) if matching else {}
            cov_fixture = coverage.get("fixtures") or {}
            sample_ids = choose_samples(fixtures)
            stats = []
            for fixture_id in sample_ids:
                stats_reply = api.get("fixtures/statistics", {"fixture": fixture_id})
                if stats_reply.get("error"):
                    errors.append("STATS_" + stats_reply["error"])
                stats.append(stats_flags(stats_reply.get("response")))
            lineup_check = None
            if sample_ids:
                lineup_reply = api.get("fixtures/lineups", {"fixture": sample_ids[0]})
                if lineup_reply.get("error"):
                    errors.append("LINEUPS_" + lineup_reply["error"])
                lineup_check = lineup_flag(lineup_reply.get("response"))
            def cnt(t):
                return sum(1 for item in stats if item["both_by_type"].get(t))
            status_counts = {}
            for item in fixtures:
                state = (((item.get("fixture") or {}).get("status") or {}).get("short") or "UNKNOWN")
                status_counts[state] = status_counts.get(state, 0) + 1
            finished = sum(status_counts.get(s, 0) for s in FINAL_STATUSES)
            row = {
                "league_id": league_id, "league": league_name, "season_start": year,
                "league_season_exists": bool(matching), "fixtures_count": len(fixtures),
                "fixtures_results_field": fixture_reply.get("results"),
                "fixture_paging_total": (fixture_reply.get("paging") or {}).get("total", 1),
                "finished_90_et_pen": finished, "statuses": status_counts,
                "coverage_events": cov_fixture.get("events"),
                "coverage_lineups": cov_fixture.get("lineups"),
                "coverage_fixture_stats": cov_fixture.get("statistics_fixtures"),
                "coverage_players": cov_fixture.get("statistics_players"),
                "coverage_injuries": coverage.get("injuries"),
                "coverage_odds": coverage.get("odds"),
                "stat_sample_n": len(stats),
                "stats_both_nonnull": sum(s["both_any"] for s in stats),
                "stats_fouls_both": cnt("Fouls"),
                "stats_corners_both": cnt("Corner Kicks"),
                "stats_yellow_both": cnt("Yellow Cards"),
                "stats_red_both": cnt("Red Cards"),
                "stats_shots_on_goal_both": cnt("Shots on Goal"),
                "stats_total_shots_both": cnt("Total Shots"),
                "stats_possession_both": cnt("Ball Possession"),
                "lineup_sample_n": 1 if sample_ids else 0,
                "lineup_both_startXI": lineup_check,
                "errors": errors,
            }
            if errors or (not matching and year < 2026) or not fixtures:
                failure_rows += 1
            rows.append(row)
            print("AUDIT_ROW " + json.dumps(row, ensure_ascii=False, sort_keys=True),
                  flush=True)
    # Odds is a current snapshot only. NOT a historical odds coverage estimate.
    odds_probe = []
    for league_id, league_name in LEAGUES:
        o = api.get("odds", {"league": league_id, "season": 2026, "page": 1})
        odds_probe.append({"league_id": league_id, "league": league_name,
                           "season": 2026, "rows_on_page_1": len(o.get("response") or []),
                           "paging_total": (o.get("paging") or {}).get("total", 0),
                           "error": o.get("error")})
    # One isolated feature check: whether date-cutoff team stats endpoint accepts a past date.
    # We do not use the endpoint as proof of original past publication timing.
    result = {
        "schema": "kb3-api-football-coverage-audit-v1",
        "start_utc": start,
        "end_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "read-only-aggregated",
        "season_years": list(SEASONS),
        "leagues": [dict(id=i, name=n) for i, n in LEAGUES],
        "row_count": len(rows),
        "row_error_count": failure_rows,
        "call_count": api.calls,
        "daily_limit_header": api.daily_limit,
        "remaining_first_header": api.first_remaining,
        "remaining_last_header": api.last_remaining,
        "per_minute_limit_header": api.minute_limit,
        "request_errors": api.error_count,
        "odds_note": "Only current first page; do not infer historical odds coverage",
        "odds_current": odds_probe,
        "stats_sample_note": "Two deterministic finished fixture samples/season; a sample is not season-wide completeness",
        "lineups_sample_note": "One finished match lineup/season; historical lineup availability != true prematch publication",
        "rows": rows,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "coverage.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    def label(x):
        return "?" if x is None else ("YES" if x is True else "NO" if x is False else str(x))
    lines = [
        "# KB Score 3.0 — API-Football coverage audit",
        "",
        f"UTC: {start} through {result['end_utc']}",
        f"Calls: {api.calls} / max {MAX_CALLS}; error responses: {api.error_count}; rows with gaps/errors: {failure_rows}",
        f"Daily limit header: {api.daily_limit}; remaining at first / last response: {api.first_remaining} / {api.last_remaining}",
        "",
        "**Method:** one full fixture list + one league-coverage read per league/season; 2 deterministic finished fixtures for individual statistics, 1 for lineups. Sample results are NOT full-season measured completeness.",
        "",
        "| League | Start | Fixtures | Finished | Declared stats | Stats (sample) | Fouls (sample) | Corners (sample) | Lineups (sample) | Errors |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['league']} | {row['season_start']} | {row['fixtures_count']} | "
            f"{row['finished_90_et_pen']} | {label(row['coverage_fixture_stats'])} | "
            f"{row['stats_both_nonnull']}/{row['stat_sample_n']} | "
            f"{row['stats_fouls_both']}/{row['stat_sample_n']} | "
            f"{row['stats_corners_both']}/{row['stat_sample_n']} | "
            f"{label(row['lineup_both_startXI'])} | {', '.join(row['errors']) or '—'} |"
        )
    lines += ["", "## Current odds (NOT historical odds completeness)",
              "| League | Current sample: odds page 1 | Pages declared | Error |",
              "|---|---:|---:|---|"]
    for row in odds_probe:
        lines.append(f"| {row['league']} | {row['rows_on_page_1']} | {row['paging_total']} | {row['error'] or '—'} |")
    lines += [
        "",
        "## Interpretation",
        "- Coverage flags returned by the provider are declarative and **do not guarantee every fixture has these data**.",
        "- Null or absent stats remain missing, not zero.",
        "- Final score and stats retrieved now may not have been available before the match; this audit is **not** a point-in-time feature history.",
        "- Odds /odds has a short retention window: today's first page is not an archive of past prices.",
        "- No raw provider responses, secrets or individual identifiable access data are included in this report.",
        "- If a row has an error or missing coverage, flag it for the next-stage audit rather than inventing numbers.",
        "",
    ]
    report = "\n".join(lines)
    (OUTPUT / "coverage.md").write_text(report, encoding="utf-8")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"), "a", encoding="utf-8") as fh:
        fh.write(report)
    print("AUDIT_FINAL " + json.dumps({k: result[k] for k in (
        "row_count", "row_error_count", "call_count", "daily_limit_header",
        "remaining_first_header", "remaining_last_header", "request_errors"
    )}, sort_keys=True), flush=True)
    # Genuine API failures or absent fixtures in archived seasons invalidate full-pass.
    if api.error_count or failure_rows:
        print("AUDIT_INCOMPLETE: inspect the recorded gaps; this is not GATE PASS.", flush=True)
        raise SystemExit(4)

if __name__ == "__main__":
    main()
