#!/usr/bin/env python3
"""Step 05: bounded, read-only API-Football league/season coverage audit.

No sports predictions or model training here. Never prints credentials or raw
provider responses. Each absence is recorded as MISSING/NOT_AVAILABLE, not zero.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = "https://v3.football.api-sports.io"
LEAGUES = {
    39: ("Premier League", "England"),
    140: ("La Liga", "Spain"),
    135: ("Serie A", "Italy"),
    78: ("Bundesliga", "Germany"),
    61: ("Ligue 1", "France"),
}
SEASONS = list(range(2021, 2027))
FINISHED = {"FT", "AET", "PEN"}
FIELDS = {"Fouls", "Corner Kicks", "Yellow Cards", "Shots on Goal"}
MAX_CALLS = 125
STOP_WHEN_DAILY_REMAINING_BELOW = 125
USER_AGENT = "KB3-Coverage-Audit/1.0"


class AuditAPI:
    def __init__(self, token: str):
        if not token:
            raise RuntimeError("MISSING_SECRET")
        self.__token = token
        self.calls = 0
        self.failures = []
        self.daily_limit = None
        self.daily_remaining = None
        self.minute_limit = None
        self.minute_remaining = None
        self.plan = None
        self.active = None

    def get(self, endpoint: str, **params):
        if self.calls >= MAX_CALLS:
            raise RuntimeError("AUDIT_CALL_BUDGET_REACHED")
        if self.daily_remaining is not None and self.daily_remaining < STOP_WHEN_DAILY_REMAINING_BELOW:
            raise RuntimeError("DAILY_QUOTA_RESERVE_REACHED")
        uri = ROOT + "/" + endpoint
        if params:
            uri += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(uri, method="GET", headers={
            "x-apisports-key": self.__token,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        })
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=18) as response:
                status = response.status
                self.daily_limit = self._num(response.headers.get("x-ratelimit-requests-limit")) or self.daily_limit
                self.daily_remaining = self._num(response.headers.get("x-ratelimit-requests-remaining"))
                self.minute_limit = self._num(response.headers.get("x-ratelimit-limit")) or self.minute_limit
                self.minute_remaining = self._num(response.headers.get("x-ratelimit-remaining"))
                if status != 200:
                    raise RuntimeError("NON_200_HTTP_RESPONSE")
                data = json.loads(response.read(12_000_000))
            if not isinstance(data, dict) or data.get("errors"):
                raise RuntimeError("API_ERROR_RESPONSE")
            if endpoint == "status" and data.get("response"):
                value = data["response"]
                self.plan = value.get("subscription", {}).get("plan")
                self.active = value.get("subscription", {}).get("active")
                self.daily_limit = value.get("requests", {}).get("limit_day") or self.daily_limit
                current = value.get("requests", {}).get("current")
                if self.daily_remaining is None and isinstance(current, int):
                    self.daily_remaining = self.daily_limit - current
            return data
        except urllib.error.HTTPError as exc:
            self.failures.append({"endpoint": endpoint, "code": "HTTP_" + str(exc.code)})
        except urllib.error.URLError:
            self.failures.append({"endpoint": endpoint, "code": "NETWORK_ERROR"})
        except (ValueError, TypeError):
            self.failures.append({"endpoint": endpoint, "code": "JSON_OR_SCHEMA_ERROR"})
        except RuntimeError as exc:
            self.failures.append({"endpoint": endpoint, "code": str(exc)})
        return None

    @staticmethod
    def _num(s):
        try:
            return int(s)
        except (ValueError, TypeError):
            return None


def get_finished(fixtures):
    return sorted([
        f for f in fixtures
        if isinstance(f, dict)
        and (f.get("fixture") or {}).get("status", {}).get("short") in FINISHED
        and isinstance((f.get("fixture") or {}).get("id"), int)
    ], key=lambda x: ((x.get("fixture") or {}).get("date") or "",
                      (x.get("fixture") or {}).get("id") or 0))


def sample_deterministic(items, count=2):
    if not items:
        return []
    if count == 1:
        return [items[len(items) // 2]]
    indexes = sorted(set([len(items) // 4, (3 * len(items)) // 4]))
    return [items[i] for i in indexes]


def both_teams_stats(data):
    response = (data or {}).get("response")
    if not isinstance(response, list) or len(response) < 2:
        return {"state": "NOT_AVAILABLE", "complete_types": []}
    pair = response[:2]
    all_types = []
    for team in pair:
        values = {}
        for stat in team.get("statistics") or []:
            if isinstance(stat, dict):
                values[stat.get("type")] = stat.get("value")
        all_types.append({name for name in FIELDS if values.get(name) is not None})
    return {
        "state": "AVAILABLE" if any(all_types) else "EMPTY_STATISTICS",
        "complete_types": sorted(all_types[0].intersection(all_types[1])),
    }


def selected_fixture(rows, year):
    x = next((r for r in rows if r["season"] == year and r["n_finished"] > 0), None)
    if x:
        return x["_sample_fixture"]
    candidates = [r for r in rows if r["n_finished"] and r["_sample_fixture"]]
    return candidates[-1]["_sample_fixture"] if candidates else None


def run(output: Path):
    key = os.getenv("API_FOOTBALL_KEY", "").strip()
    api = AuditAPI(key)
    begun = dt.datetime.now(dt.timezone.utc)
    result = {
        "schema": "kb30-api-football-coverage-v1",
        "run_at_utc": begun.isoformat(),
        "leagues_requested": 5,
        "seasons_requested": SEASONS,
        "sampling": "Two deterministic finished fixtures per league-season, 25%/75% chronological index; five 2025 lineup, events, player examples",
        "rows": [],
        "special_probes": [],
        "limitations": [
            "League-season declared coverage is not per-fixture completeness.",
            "Per-fixture statistics are sampled; they are not an exhaustive count of statistical completeness.",
            "An absent provider field means NOT_AVAILABLE, never an actual zero.",
            "Historical odds older than the provider's retention window are not authenticated prematch snapshots.",
            "Fixture results retrieved now do not establish that earlier snapshots existed before kickoff.",
            "The project has not trained a model; this is only a read-only source audit.",
        ],
    }
    status = api.get("status")
    if status is None or api.active is False:
        result["outcome"] = "BLOCKED_STATUS"
        return finish(output, result, api)

    for league_id, (label, country) in LEAGUES.items():
        league_response = api.get("leagues", id=league_id)
        descriptions = (league_response or {}).get("response") or []
        seasons_meta = {}
        for entry in descriptions:
            if not isinstance(entry, dict):
                continue
            for s in entry.get("seasons", []):
                if isinstance(s, dict):
                    seasons_meta[s.get("year")] = s
        for season in SEASONS:
            coverage = (seasons_meta.get(season) or {}).get("coverage") or {}
            flags = (coverage.get("fixtures") or {})
            row = {
                "league_id": league_id, "league": label, "country": country,
                "season": season,
                "season_listed": season in seasons_meta,
                "coverage_declared": {
                    "events": flags.get("events"),
                    "lineups": flags.get("lineups"),
                    "statistics_fixtures": flags.get("statistics_fixtures"),
                    "statistics_players": flags.get("statistics_players"),
                    "injuries": coverage.get("injuries"),
                    "odds": coverage.get("odds"),
                },
                "fixture_fetch": "NOT_TESTED",
                "n_fixtures": None, "n_finished": None,
                "n_results_with_goals": None,
                "n_scheduled_other": None,
                "stats_sample_count": 0, "stats_available_count": 0,
                "stats_fields_both_teams": {k: 0 for k in sorted(FIELDS)},
                "_sample_fixture": None,
            }
            result["rows"].append(row)
            if season not in seasons_meta:
                row["fixture_fetch"] = "NOT_LISTED"
                continue
            data = api.get("fixtures", league=league_id, season=season)
            if data is None or not isinstance(data.get("response"), list):
                row["fixture_fetch"] = "ERROR_OR_UNAVAILABLE"
                continue
            fixtures = data["response"]
            finished = get_finished(fixtures)
            row["fixture_fetch"] = "OK"
            row["n_fixtures"] = len(fixtures)
            row["n_finished"] = len(finished)
            row["n_results_with_goals"] = sum(
                isinstance((x.get("goals") or {}).get("home"), int)
                and isinstance((x.get("goals") or {}).get("away"), int)
                for x in finished
            )
            row["n_scheduled_other"] = len(fixtures) - len(finished)
            selected = sample_deterministic(finished, 2)
            if selected:
                row["_sample_fixture"] = selected[0]["fixture"]["id"]
            for game in selected:
                fixture_id = game["fixture"]["id"]
                stat = api.get("fixtures/statistics", fixture=fixture_id)
                row["stats_sample_count"] += 1
                check = both_teams_stats(stat)
                if check["state"] == "AVAILABLE":
                    row["stats_available_count"] += 1
                for name in check["complete_types"]:
                    row["stats_fields_both_teams"][name] += 1

        # One historical 2025 match probe per league for deeper response types.
        subset = [x for x in result["rows"] if x["league_id"] == league_id]
        fixture_id = selected_fixture(subset, 2025)
        if fixture_id:
            for endpoint in ["fixtures/lineups", "fixtures/events", "fixtures/players"]:
                test = api.get(endpoint, fixture=fixture_id)
                response = (test or {}).get("response")
                state = "ERROR_OR_UNAVAILABLE"
                n_items = None
                if isinstance(response, list):
                    state = "RETURNED_LIST"
                    n_items = len(response)
                result["special_probes"].append({
                    "league_id": league_id, "league": label,
                    "season": 2025, "kind": endpoint,
                    "state": state, "items": n_items
                })

    # Odds probe is time-sensitive. Treat only as current capability evidence.
    odds = api.get("odds", league=39, season=2026, page=1)
    if isinstance((odds or {}).get("response"), list):
        result["odds_now"] = {
            "state": "CURRENT_SNAPSHOT_ONLY",
            "league_id": 39,
            "season": 2026,
            "n_page_items": len(odds["response"]),
            "paging": (odds.get("paging") or {}).get("total"),
        }
    else:
        result["odds_now"] = {"state": "ERROR_OR_UNAVAILABLE"}

    result["outcome"] = "DATA_COLLECTED"
    return finish(output, result, api)


def finish(output, result, api):
    # Provider metadata do not include private account information.
    result["account_status"] = {
        "plan": api.plan, "subscription_active": api.active,
        "daily_limit": api.daily_limit, "daily_remaining_after": api.daily_remaining,
        "minute_limit": api.minute_limit,
    }
    result["requests_used_by_this_audit"] = api.calls
    result["request_ceiling"] = MAX_CALLS
    result["provider_errors"] = api.failures
    rows = result["rows"]
    for row in rows:
        row.pop("_sample_fixture", None)
    result["rows_with_fixtures"] = sum(isinstance(r.get("n_fixtures"), int) and r["n_fixtures"] > 0 for r in rows)
    result["total_fixture_rows_reported"] = sum(r.get("n_fixtures") or 0 for r in rows)
    result["total_stats_samples"] = sum(r.get("stats_sample_count") or 0 for r in rows)
    result["total_stats_2teams_available"] = sum(r.get("stats_available_count") or 0 for r in rows)
    output.mkdir(parents=True, exist_ok=True)
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    json_path = output / ("API_FOOTBALL_STEP05_" + day + ".json")
    md_path = output / ("API_FOOTBALL_STEP05_" + day + ".md")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# KB Score 3.0 — Etap 05: audyt API-Football",
        "",
        "Wykonano: " + result["run_at_utc"],
        "**Stan:** " + result["outcome"] + " — samo wykonanie nie oznacza GATE PASS.",
        "",
        "## Limity i odczyt konta (bez danych osobowych)",
        "",
        "- Plan: " + str(api.plan) + ", active=" + str(api.active),
        "- Zapytania tego testu: " + str(api.calls) + "/" + str(MAX_CALLS),
        "- Dzienny limit / pozostałe po teście: " + str(api.daily_limit) + " / " + str(api.daily_remaining),
        "- Maksymalny limit na minutę: " + str(api.minute_limit),
        "- Błędy API: " + str(len(api.failures)),
        "- Przebadane kombinacje z terminarzem: " + str(result["rows_with_fixtures"]) + " / " + str(len(rows)),
        "- Liczba meczów na pobranych listach: " + str(result["total_fixture_rows_reported"]),
        "- Próbki statystyk (2 drużyny): " + str(result["total_stats_2teams_available"]) + " / " + str(result["total_stats_samples"]),
        "",
        "## Pokrycie liga × sezon (liczby z API, nie estymacje)",
        "",
        "| Liga | Sezon | Zgłoszono statystyki | Mecze | Zakończone | Wyniki | Próbki statystyk | Faule/rożne/kartki/strzały — obie drużyny |",
        "|---|---:|:---:|---:|---:|---:|:---:|---|",
    ]
    for row in rows:
        fmt = lambda x: "BRAK" if x is None else str(x)
        d = row["stats_fields_both_teams"]
        s = "/".join(str(d.get(k, 0)) for k in ["Fouls", "Corner Kicks", "Yellow Cards", "Shots on Goal"])
        c = row["coverage_declared"].get("statistics_fixtures")
        flag = "TAK" if c is True else ("NIE" if c is False else "BRAK")
        lines.append(
            f'| {row["league"]} | {row["season"]} | {flag} | '
            f'{fmt(row["n_fixtures"])} | {fmt(row["n_finished"])} | '
            f'{fmt(row["n_results_with_goals"])} | '
            f'{row["stats_available_count"]}/{row["stats_sample_count"]} | {s} |'
        )
    lines += [
        "", "## Kontrole szczegółowe — próbki 2025",
        "", "| Liga | Rodzaj | Odpowiedź | Rekordy |",
        "|---|---|---|---:|",
    ]
    for t in result["special_probes"]:
        lines.append(f'| {t["league"]} | {t["kind"]} | {t["state"]} | {t["items"] if t["items"] is not None else "BRAK"} |')
    odds = result.get("odds_now", {})
    lines += [
        "", "## Kursy — wyłącznie obecne",
        "",
        "Bieżący endpoint: " + odds.get("state", "NOT_TESTED")
        + "; wynik strony: " + str(odds.get("n_page_items", "BRAK"))
        + "; liczba stron: " + str(odds.get("paging", "BRAK")) + ".",
        "",
        "**NIE oznacza to dostępności historycznych kursów**. Dostawca opisuje historię kursów przedmeczowych około 7 dni.",
        "",
        "## Znane ograniczenia",
        "",
    ] + ["- " + item for item in result["limitations"]]
    if api.failures:
        lines += ["", "## Błędy zapytań (bez surowych odpowiedzi)"]
        lines += [f'- {x["endpoint"]}: {x["code"]}' for x in api.failures]
    lines += ["", "## Decyzja odbioru", "",
              "**GATE 05: DO ODBIORU / PENDING**, dopóki nie zweryfikowano liczebności, próbek i dowodów.",
              "Następny krok po PASS: 06 — audyt PitchAPI. Brak kodu modelu i brak treningu.",
              ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Coverage rows: {len(rows)}; fixture coverage rows: {result['rows_with_fixtures']}")
    print(f"Fixture records: {result['total_fixture_rows_reported']}; stats samples: {result['total_stats_2teams_available']}/{result['total_stats_samples']}")
    print(f"API audit requests: {api.calls}; errors: {len(api.failures)}; outcome: {result['outcome']}")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n".join(lines[:18]) + "\n")
    return 0 if result["outcome"] == "DATA_COLLECTED" and result["rows_with_fixtures"] >= 20 else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="step05-output")
    args = parser.parse_args()
    try:
        sys.exit(run(Path(args.out)))
    except Exception as exc:
        # Exception messages could include provider-sensitive text. Never log details.
        print("AUDIT_BLOCKED: " + type(exc).__name__)
        sys.exit(3)
