"""Research-only historic 2025/26 public PREMATCH match-stat reconstruction.

Use immutable old FPL-Core-Insights blobs AND independent GitHub server-timed
Actions run on the default branch. Never replace original PitchAPI native xG,
reuse target labels, or upgrade original 121+38 CatBoost M1 eligibility.

This script makes NO sports provider API calls and needs NO encryption.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from src.kb3_step14_native_team_crosswalk import canonical_team_name
from src.kb3_split import sha

REPO = "olbauday/FPL-Core-Insights"
REF_SOURCE = "data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json"
REF_SHA = "fa924730da71e3ba24e89a3095f7d4d92de5e71dd252b893bd86cc2e4db53678"
SCHEMA = "kb3-step14-fpl-core-2025-26-independent-actions-witness-partial-stat-reconstruction-v1"
SOURCES = (
    ("35932486961bb9a7eb8fbb710ad33ec21a28b1da", 17822709032, 4,
     "2025-09-18T08:24:28Z"),
    ("173bd03f01a9808dbbcf9c42e8ad1112b63429ac", 19175468717, 10,
     "2025-11-07T17:03:33Z"),
    ("59a4cd678579a38b5937bd07afe5635ed3be9e29", 20642294092, 19,
     "2026-01-01T17:04:13Z"),
    ("326b639b21979961dc2a6e1b06db388f8b7431e6", 22965280628, 28,
     "2026-03-11T17:18:18Z"),
)
ALIASES = {
    "man city": "manchester city",
    "man utd": "manchester united",
    "nott m forest": "nottingham forest",
    "spurs": "tottenham hotspur",
    "brighton": "brighton and hove albion",
    "wolves": "wolverhampton wanderers",
    "bournemouth": "bournemouth",
}
class CandidateError(ValueError):
    pass

def _get(url, *, limit=1_500_000):
    with urlopen(Request(url, headers={"User-Agent": "KB3-independent-prematch-source-recovery",
                                      "Accept": "application/vnd.github+json"}),
                 timeout=40) as stream:
        content = stream.read(limit + 1)
    if not content or len(content) > limit:
        raise CandidateError("EMPTY_OR_OVERSIZED_REMOTE_SOURCE")
    return content

def _utc(s):
    if not isinstance(s, str) or not s:
        raise CandidateError("MISSING_TIME")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CandidateError("INVALID_TIME") from exc
    if d.tzinfo is None:  # Source 'kickoff_time' stores UTC but lacks an explicit suffix.
        d = d.replace(tzinfo=timezone.utc)
    if d.utcoffset().total_seconds() != 0:
        raise CandidateError("NON_UTC_TIME")
    return d.astimezone(timezone.utc)

def _name(s):
    k = canonical_team_name(s).replace(" and ", " and ")
    return ALIASES.get(k, k)

def _csv(raw):
    try:
        parsed = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise CandidateError("INVALID_SOURCE_CSV") from exc
    if not parsed:
        raise CandidateError("EMPTY_CSV")
    return parsed

def _float(v):
    if v is None or v == "":
        return None
    try:
        num = float(v)
    except (ValueError, TypeError) as exc:
        raise CandidateError("INVALID_SOURCE_VALUE") from exc
    if not math.isfinite(num):
        raise CandidateError("NONFINITE_SOURCE_VALUE")
    return num

def _integer(v):
    n = _float(v)
    if n is None or int(n) != n or n < 0 or n > 30:
        raise CandidateError("INVALID_MATCH_SCORE")
    return int(n)

def _code(v):
    n = _float(v)
    if n is None or int(n) != n:
        raise CandidateError("INVALID_FPL_TEAM_CODE")
    return int(n)

def _fetch_raw(commit, path, fetcher=_get):
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}"
    raw = fetcher(url)
    return raw, sha256(raw).hexdigest()

def actions_witness(commit, expected_run, expected_time, get_json):
    data = get_json(f"https://api.github.com/repos/{REPO}/actions/runs?"
                    f"head_sha={commit}&per_page=30")
    if not isinstance(data, dict):
        raise CandidateError("MISSING_INDEPENDENT_GITHUB_SERVER_WITNESS")
    candidates = [r for r in data.get("workflow_runs", [])
                  if r.get("id") == expected_run
                  and r.get("head_sha") == commit
                  and r.get("head_branch") == "main"
                  and r.get("event") in ("schedule", "push", "workflow_dispatch")
                  and r.get("created_at") == expected_time
                  and r.get("conclusion") == "success"]
    if len(candidates) != 1:
        raise CandidateError("GITHUB_ACTIONS_WITNESS_NOT_VERIFIED")
    # A server-created Actions run with this head SHA on public main is
    # an independent existence-by clock for the commit's historical bytes;
    # it does NOT prove first upstream xG publication.
    return {"repo": REPO, "commit": commit, "server_created_at_utc": expected_time,
            "github_run_id": expected_run,
            "run_url": candidates[0].get("html_url")
                or f"https://github.com/{REPO}/actions/runs/{expected_run}",
            "proof": "GITHUB_SERVER_ACTIONS_MAIN_HEAD_SHA_EXISTED_BY",
            "provider_original_xg_first_published_verified": False}

def _get_json(url):
    return json.loads(_get(url, limit=3_000_000))

def _read_teams(raw):
    rows = _csv(raw)
    mapping = {}
    for x in rows:
        code = _code(x["code"])
        team = _name(x.get("fotmob_name") or x.get("name"))
        if code in mapping or team in mapping.values():
            raise CandidateError("TEAM_CODE_AMBIGUOUS")
        mapping[code] = team
    if len(mapping) != 20:
        raise CandidateError("NOT_PREMIER_LEAGUE_20_TEAMS")
    return mapping

def _read_matches(raw, *, witness, teams):
    published = _utc(witness)
    result = {}
    for row in _csv(raw):
        if not row.get("match_id", "").startswith("25-26-prem-"):
            continue  # Explicitly exclude EFL/European/other competitions.
        completed = row.get("finished")
        if completed not in ("True", "False"):
            raise CandidateError("UNKNOWN_FINISHED_STATE")
        if completed == "False":
            if row.get("home_score") or row.get("away_score"):
                raise CandidateError("FUTURE_MATCH_ALREADY_HAS_TARGET_RESULT")
            continue
        try:
            when = _utc(row["kickoff_time"])
            home = teams[_code(row["home_team"])]
            away = teams[_code(row["away_team"])]
        except KeyError as exc:
            raise CandidateError("UNKNOWN_SOURCE_TEAM") from exc
        if home == away:
            raise CandidateError("SELF_PLAY")
        # Conservative: source GitHub Actions witness >= 3h after kickoff.
        if (published - when).total_seconds() < 3 * 3600:
            raise CandidateError("FUTURE_OR_RECENT_FT_IN_OLD_SNAPSHOT")
        h, a = _integer(row["home_score"]), _integer(row["away_score"])
        hxg, axg = _float(row.get("home_expected_goals_xg")), _float(row.get("away_expected_goals_xg"))
        if hxg is not None and (hxg < 0 or hxg > 15):
            raise CandidateError("INVALID_XG")
        if axg is not None and (axg < 0 or axg > 15):
            raise CandidateError("INVALID_XG")
        key = (home, away, when.isoformat())
        if key in result:
            raise CandidateError("DUPLICATE_PUBLISHED_PREVIOUS_MATCH")
        result[key] = {"home": home, "away": away, "kickoff": when,
                       "home_goals": h, "away_goals": a, "home_xg": hxg, "away_xg": axg}
    return result

def _reference(path):
    j = json.loads(Path(path).read_text(encoding="utf8"))
    if (j.get("projection_sha256") != REF_SHA
        or sha({k: v for k, v in j.items() if k != "projection_sha256"}) != REF_SHA
        or j.get("schema") != "kb3-step14-public-historical-1140-targetfree-identity-reference-v1"
        or j.get("result_labels_in_projection") is not False
        or j.get("odds_in_projection") is not False
        or j.get("full_coverage_historical_season_fixtures") != 1140):
        raise CandidateError("UNTRUSTED_OR_LABELLED_RETROSPECTIVE_REFERENCE")
    src = j["source_seasons"]["2025-26"]["fixtures_target_free"]
    all_matches = []
    seen = set()
    for item in src:
        day = item["date"]
        clock = item["time_london"]
        london = datetime.fromisoformat(day + "T" + clock).replace(tzinfo=ZoneInfo("Europe/London"))
        ko = london.astimezone(timezone.utc)
        home, away = _name(item["home_name"]), _name(item["away_name"])
        key = (home, away, ko.isoformat())
        if key in seen:
            raise CandidateError("DUPLICATE_PUBLIC_REFERENCE")
        seen.add(key)
        all_matches.append({"key": key, "ko": ko, "home": home, "away": away})
    if len(all_matches) != 380:
        raise CandidateError("PUBLIC_REFERENCE_NOT_380")
    return all_matches

def _qualify_target(target, published, past, season_reference):
    if target["ko"] <= published:
        return None
    before = [x for x in season_reference if x["ko"] < target["ko"]]
    record = {"target_public_home": target["home"], "target_public_away": target["away"],
              "target_kickoff_utc": target["ko"].isoformat().replace("+00:00", "Z"),
              "source_publication_witness_utc": published.isoformat().replace("+00:00", "Z"),
              "source_is_not_native_PitchAPI": True,
              "native_pitchapi_fixture_id_join_proven": False,
              "original_121_plus_38_eligible": False}
    combined = {}
    for side in ("home", "away"):
        team = target[side]
        predecessors = sorted((x for x in before if team in (x["home"], x["away"])),
                              key=lambda x: x["ko"], reverse=True)[:5]
        if len(predecessors) < 5 or any(x["key"] not in past for x in predecessors):
            return None
        sums = {"points": 0, "gf": 0, "ga": 0, "xg": 0.0, "xga": 0.0}
        have_xg = True
        for previous in predecessors:
            m = past[previous["key"]]
            home = previous["home"] == team
            gf = m["home_goals"] if home else m["away_goals"]
            ga = m["away_goals"] if home else m["home_goals"]
            sums["points"] += 3 if gf > ga else 1 if gf == ga else 0
            sums["gf"] += gf
            sums["ga"] += ga
            own_xg = m["home_xg"] if home else m["away_xg"]
            opp_xg = m["away_xg"] if home else m["home_xg"]
            if own_xg is None or opp_xg is None:
                have_xg = False
            else:
                sums["xg"] += own_xg
                sums["xga"] += opp_xg
        combined[side] = {"previous_prematch_5_source_rows_found": 5,
                          "points_avg": sums["points"]/5,
                          "gf_avg": sums["gf"]/5, "ga_avg": sums["ga"]/5,
                          "alternative_xg_avg": sums["xg"]/5 if have_xg else None,
                          "alternative_xga_avg": sums["xga"]/5 if have_xg else None,
                          "alternative_xg_missing": not have_xg}
    record["prematch_public_FORM5"] = combined
    record["alternative_xg_is_not_PitchAPI_original_48_features"] = True
    return record

def audit(root, *, fetcher=_get, get_json=_get_json):
    targets = _reference(Path(root)/REF_SOURCE)
    reports = []
    dedup = {}
    for commit, run_id, max_gw, asof in SOURCES:
        witness = actions_witness(commit, run_id, asof, get_json)
        t = _utc(asof)
        base = "data/2025-2026/By Gameweek"
        teams_raw, teams_hash = _fetch_raw(commit, f"{base}/GW10/teams.csv", fetcher)
        teams = _read_teams(teams_raw)
        def load(gw):
            raw, hashvalue = _fetch_raw(commit, f"{base}/GW{gw}/matches.csv", fetcher)
            return gw, hashvalue, _read_matches(raw, witness=asof, teams=teams)
        old = {}
        sources = {}
        with ThreadPoolExecutor(max_workers=6) as pool:
            tasks = [pool.submit(load, gw) for gw in range(1, max_gw + 1)]
            for job in as_completed(tasks):
                gw, checksum, rows = job.result()
                sources[str(gw)] = checksum
                for key, m in rows.items():
                    if key in old:
                        raise CandidateError("SAME_MATCH_IN_MULTIPLE_GAMEWEEKS")
                    old[key] = m
        # Require strong corroboration against distinct retrospective schedule,
        # but never read results from it.
        target_keys = {x["key"] for x in targets}
        matched = {k:v for k,v in old.items() if k in target_keys}
        report = {"commit": commit, "witness": witness, "teams_sha256": teams_hash,
                  "source_match_file_sha256_by_gw": dict(sorted(sources.items(), key=lambda z:int(z[0]))),
                  "completed_old_Premier_League_matches": len(old),
                  "previous_matches_matched_to_public_targetfree_reference": len(matched),
                  "matched_public_FORM5_future_targets": 0,
                  "matched_alternative_xg_FORM5_future_targets": 0}
        for target in targets:
            record = _qualify_target(target, t, matched, targets)
            if record is None:
                continue
            report["matched_public_FORM5_future_targets"] += 1
            if all(not record["prematch_public_FORM5"][side]["alternative_xg_missing"]
                   for side in ("home","away")):
                report["matched_alternative_xg_FORM5_future_targets"] += 1
            # Latest witnessed source before target becomes its fixed research
            # snapshot; across source versions the same target is ONE match.
            key = target["key"]
            if key not in dedup or t > _utc(dedup[key]["source_publication_witness_utc"]):
                record["evidence_source_commit"] = commit
                record["evidence_github_run_id"] = run_id
                dedup[key] = record
        reports.append(report)
    candidates = sorted(dedup.values(), key=lambda z:(z["target_kickoff_utc"],
                                                       z["target_public_home"],
                                                       z["target_public_away"]))
    result = {"schema": SCHEMA,
      "source": REPO, "research_only": True,
      "real_historical_default_branch_server_witnesses": len(reports),
      "historical_source_versions": reports,
      "target_free_2025_26_reference_rows": 380,
      "new_distinct_published_public_FORM5_candidates": len(candidates),
      "new_distinct_published_public_alternative_xg_FORM5_candidates":
          sum(all(not v["prematch_public_FORM5"][s]["alternative_xg_missing"]
                  for s in ("home","away")) for v in candidates),
      "different_source_semantics_from_original_PitchAPI_team_xg": True,
      "original_121_plus_38_eligible_train": 0,
      "original_121_plus_38_eligible_validation": 0,
      "original_CatBoost_M1_fitted": False,
      "TRAIN_or_TEST_labels_or_odds_read": False,
      "original_model_split_or_GATES_modified": False,
      "gate14": "PENDING",
      "candidates": candidates}
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = audit(Path(__file__).resolve().parents[1])
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise CandidateError("APPEND_ONLY_NO_OVERWRITE")
    dest.write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf8")
    print(json.dumps({"independent_historic_github_server_witnesses": doc["real_historical_default_branch_server_witnesses"],
      "distinct_public_FORM5_candidates": doc["new_distinct_published_public_FORM5_candidates"],
      "alternative_source_xg_FORM5_candidates": doc["new_distinct_published_public_alternative_xg_FORM5_candidates"],
      "official_M1_fit": False, "gate14": "PENDING"}, sort_keys=True))

if __name__ == "__main__":
    main()
