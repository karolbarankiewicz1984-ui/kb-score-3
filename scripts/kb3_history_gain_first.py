"""Prioritize missing historical PitchAPI data by *potential* last-five cohort gain.

Read-only: no provider API, no training, no claims of original historic PIT.
All completions are conditional on future real provider observations being valid.
Never substitute a convenient older match for one of the true last five.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

from src.kb3_historical_feature_quality import (
    _load_records, _feature_for_match,
)

SEASONS = frozenset(("2023/2024", "2024/2025", "2025/2026"))
LEAGUES = frozenset(("ESP", "ITA", "GER", "FRA", "NED", "BEL", "TUR", "POL"))
UNDERSERVED = frozenset(("NED", "POL", "TUR"))
CORE = ("total_shots", "fouls", "corners", "yellow_cards")
NON_CARD = ("total_shots", "fouls", "corners")
XG = ("xg_for", "xg_against")
SCHEMA = "kb3-history-gain-first-research-priority-v1"
LEAD = timedelta(hours=2)
RESULT_LAG = timedelta(hours=3)


def when(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("HISTORY_PRIORITY_CANONICAL_UTC_REQUIRED")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def scope_boost(scope):
    return 2 if scope in UNDERSERVED else 1


def prepare_source(db_path, recheck_db=None):
    """Read original immutable observations with existing vetted card overlays."""
    path = Path(db_path)
    if not path.exists():
        return None
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("HISTORY_PRIORITY_CORRUPT_SOURCE")
        tables = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"finished_fixture_index", "observations"} <= tables:
            return None  # Small legacy/test fixture; original safe selector remains.
        ix, obs, _, _ = _load_records(
            db, recheck_db_path=(recheck_db if recheck_db is not None and
                                 Path(recheck_db).exists() else None))
    return ix, obs


def build_needs(fixtures, observed):
    """Only known finished historical *targets*, never a target score feature."""
    team_history = defaultdict(list)
    for league, games in fixtures.items():
        if league == "ENG":
            raise ValueError("PROTECTED_PREMIER_LEAGUE_TEST_IN_PRIORITY")
        for game in games:
            dt = when(game["kickoff_utc"])
            for team in (game["home_team_id"], game["away_team_id"]):
                team_history[(league, team)].append((dt, game))
    for games in team_history.values():
        games.sort(key=lambda z:(z[0],z[1]["match_id"]))

    closure_tasks = []
    core_card_tasks = []
    xg_repair_tasks = []
    target_count = 0
    for (league,mid), target_obs in sorted(observed.items()):
        if league not in LEAGUES or target_obs["season"] not in SEASONS:
            continue
        indexed = next((v for v in fixtures[league]
                        if v["match_id"] == mid), None)
        if indexed is None:
            raise ValueError("HISTORICAL_PRIORITY_UNINDEXED_TARGET")
        cutoff = when(indexed["kickoff_utc"]) - LEAD
        predecessors = []
        for side in ("home_team_id", "away_team_id"):
            team = indexed[side]
            recent = [(game, team) for dt, game in team_history[(league, team)]
                      if game["match_id"] != mid and dt + RESULT_LAG <= cutoff][-5:]
            if len(recent) != 5:
                break
            predecessors.extend(recent)
        if len(predecessors) != 10:
            continue
        target_count += 1
        missing = set()
        blocked_core = False
        blocked_joint = False
        missing_card = set()
        missing_xg = set()
        non_card_block = False
        for pred, team in predecessors:
            key = (league, pred["match_id"])
            row = observed.get(key)
            if row is None:
                missing.add(key)
                continue
            values = _feature_for_match(pred,row,team)
            card = values["yellow_cards"] is not None
            other = all(values[k] is not None for k in NON_CARD)
            xg = all(values[k] is not None for k in XG)
            if not other:
                non_card_block = True
            if not (other and card):
                blocked_core = True
            if not card:
                missing_card.add(key)
            if not xg:
                blocked_joint = True
                missing_xg.add(key)
        bonus = scope_boost(league)
        if missing:
            # A newly fetched missing fixture can only finish a Core5
            # if every *already observed* predecessor has a complete Core.
            if not blocked_core:
                closure_tasks.append(("core",league,frozenset(missing),5*bonus))
            if not blocked_core and not blocked_joint:
                closure_tasks.append(("joint",league,frozenset(missing),8*bonus))
            # Still useful to complete history5, even with existing stat gaps.
            closure_tasks.append(("history",league,frozenset(missing),1*bonus))
        else:
            # Existing observations can only be repaired by separate event
            # rechecks; never pretend that fetching new matches fixes them.
            if missing_card and not non_card_block:
                core_card_tasks.append((league,frozenset(missing_card),bonus))
            if missing_xg:
                xg_repair_tasks.append(
                    (league,frozenset(missing_xg),
                     bonus*(3 if not blocked_core else 1)))
    return {
        "closure_tasks":closure_tasks,
        "card_tasks":core_card_tasks,
        "xg_repair_tasks":xg_repair_tasks,
        "targets_with_full_last5":target_count,
    }


def greedy_rank(tasks, available, limit):
    """Each selection updates remaining deficits; deterministic and bounded."""
    selected=[]
    available=set(available)
    while len(selected) < limit:
        score=defaultdict(float)
        for typ,league,required,weight in tasks:
            remaining = required.difference(selected)
            if not remaining:
                continue
            # Strongly favor closing the final one or two real missing
            # predecessors; allow linked multi-fetch windows to mature.
            value = weight / len(remaining)**2
            for key in remaining.intersection(available):
                score[key] += value
        if not score:
            break
        best = min(score, key=lambda k:(-score[k],k[0],k[1]))
        selected.append(best)
        available.remove(best)
    return selected


def potential_unlocks(tasks, selected):
    planned=set(selected)
    by_kind=Counter()
    by_scope=Counter()
    for kind,league,missing,weight in tasks:
        if missing.issubset(planned):
            by_kind[kind]+=1
            by_scope[league+":"+kind]+=1
    return dict(sorted(by_kind.items())),dict(sorted(by_scope.items()))


def plan_missing_fixtures(groups, known, db_path, limit=36):
    """Rank *only* not-yet-seen authentic listed fixtures; no provider calls."""
    if not 0<=limit<=48:
        raise ValueError("HISTORY_PRIORITY_UNSAFE_BATCH_LIMIT")
    source=prepare_source(db_path)
    if source is None:
        return [],{"state":"NO_COMPATIBLE_ORIGINAL_HISTORY_DB","schema":SCHEMA,
                   "estimated_not_observed":True}
    fixtures,obs=source
    if set(obs)!=set(known):
        raise ValueError("HISTORY_PRIORITY_KNOWN_DB_ID_DRIFT")
    available={}
    for (league,season), matches in groups.items():
        if league not in LEAGUES:
            continue
        for item in matches:
            key=(league,item["id"])
            if key not in known:
                if key in available:
                    raise ValueError("HISTORY_PRIORITY_DUPLICATE_PROVIDER_ID")
                available[key]=(league,season,item)
    needs=build_needs(fixtures,obs)
    ids=greedy_rank(needs["closure_tasks"],available,limit)
    selected=[available[k] for k in ids]
    gains,scopes=potential_unlocks(needs["closure_tasks"],ids)
    report={"schema":SCHEMA,"state":"SOURCE_RANKED_NOT_FETCHED",
        "historical_targets_last5":needs["targets_with_full_last5"],
        "candidate_listed_missing_fixture_count":len(available),
        "gain_ranked_selected":len(ids),
        "potential_history5_unlocks_if_new_fixtures_complete":gains.get("history",0),
        "potential_core5_unlocks_if_new_fixtures_complete":gains.get("core",0),
        "potential_core5_xg5_unlocks_if_new_fixtures_complete":gains.get("joint",0),
        "potential_unlocks_by_scope_if_all_new_stats_valid":scopes,
        "assumed_new_stats_and_xg_available":True,
        "estimated_not_observed":True,
        "formal_pit_eligible":False,
        "model_or_test_modified":False}
    return selected,report


def issue_priority_scores(db_path, recheck_db=None):
    """Rank NEW unresolved existing cards/xG by affected last-five targets."""
    source=prepare_source(db_path,recheck_db)
    if source is None:
        return {},{}
    fixt,obs=source
    tasks=build_needs(fixt,obs)
    card=Counter();xg=Counter()
    for league,remaining,weight in tasks["card_tasks"]:
        for key in remaining:
            card[key]+=weight/len(remaining)**2
    for league,remaining,weight in tasks["xg_repair_tasks"]:
        for key in remaining:
            xg[key]+=weight/len(remaining)**2
    return dict(card),dict(xg)
