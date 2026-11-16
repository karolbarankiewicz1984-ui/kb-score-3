"""Prioritise genuine upcoming KB3 M0 last-five source gaps for PitchAPI.

Selection only: does not query APIs, invent missing values, modify sources,
train models, or pretend historic provider-publication evidence was recovered.
A missing stat remains in the next source-acquisition queue.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from scripts.kb3_p1_historical_eligibility_split import LEAGUES, utc

CURRENT = "2026/2027"
MAX_HORIZON = timedelta(days=8)
MIN_LEAD = timedelta(minutes=90)
RESULT_LAG = timedelta(hours=3)
SOURCE_DB = Path(__file__).resolve().parents[1] / "data/forward_m0_720_eight/kb3_forward_eight.sqlite"


class LastFiveSelectionError(ValueError):
    pass


def future_m0_targets(db_path, now):
    """Read existing immutable M0 forecasts; no retro or invented targets."""
    now = now.astimezone(timezone.utc)
    db_path = Path(db_path)
    if not db_path.is_file():
        return [], "NO_M0_DB"
    with sqlite3.connect(db_path.resolve().as_uri()+"?mode=ro",uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise LastFiveSelectionError("M0_READONLY_DB_INTEGRITY")
        rows = db.execute("""SELECT league,native_match_id,kickoff_utc,
                     home_team_id,away_team_id,captured_at_utc
                     FROM forecasts ORDER BY kickoff_utc,native_match_id""").fetchall()
    output = []
    for league,mid,ko,home,away,at in rows:
        if league not in LEAGUES:
            raise LastFiveSelectionError("PROTECTED_M0_LEAGUE")
        if (now+MIN_LEAD < utc(ko) <= now+MAX_HORIZON and
                utc(at)<utc(ko)-MIN_LEAD):
            output.append({"league":league,"native_match_id":mid,
                "kickoff_utc":ko,"home_team_id":home,
                "away_team_id":away,"captured_at_utc":at})
    return output, "EXISTING_REAL_M0_ONLY"


def prioritize_live_last5(groups, raw_current, known, *, db_path=SOURCE_DB,
                          now=None, limit=24):
    """True last-five native IDs from actual finished provider listings.

    Raw CURRENT listing verifies the existing M0 target still has exact
    provider match, kickoff and both native team IDs. No English sources.
    Missing stats are ranked for fetch. Previously fetched-but-incomplete
    observations are logged for recheck rather than backdated/overwritten.
    """
    if not 0 <= limit <= 48:
        raise LastFiveSelectionError("UNSAFE_FUTURE_PRIORITY_LIMIT")
    now = now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):
        raise LastFiveSelectionError("UTC_REQUIRED")
    targets, source_state = future_m0_targets(db_path,now)
    history = defaultdict(list)
    for (league,season),rows in groups.items():
        if league not in LEAGUES:
            continue  # UEFA data are unrelated; protected ENG never fetched
        for row in rows:
            if (row.get("status")!="finished" or
                utc(row["time_utc"])+RESULT_LAG>now):
                continue
            history[league].append((season,row))
    for games in history.values():
        games.sort(key=lambda pair:(pair[1]["time_utc"],pair[1]["id"]))
    real_targets=0
    quarantine=Counter()
    scores=Counter()
    already_observed=set()
    histories_short=0
    for target in targets:
        league = target["league"]
        catalogue = raw_current.get(league)
        if not isinstance(catalogue,dict) or not isinstance(catalogue.get("matches"),list):
            quarantine["NO_CURRENT_LIVE_LISTING"]+=1
            continue
        same = [x for x in catalogue["matches"] if x.get("id")==target["native_match_id"]]
        if len(same)!=1:
            quarantine["M0_TARGET_MISSING_OR_DUPLICATED_IN_CURRENT_LISTING"]+=1
            continue
        m = same[0]
        if not (m.get("time_utc")==target["kickoff_utc"] and
                (m.get("home_team") or {}).get("id")==target["home_team_id"] and
                (m.get("away_team") or {}).get("id")==target["away_team_id"] and
                m.get("status") in ("scheduled","not_started","upcoming")):
            quarantine["LIVE_TARGET_IDENTITY_OR_STATUS_CHANGED"]+=1
            continue
        real_targets += 1
        ko=utc(target["kickoff_utc"])
        priority_by_age=max(1,9-int((ko-now).total_seconds()//86400))
        for team in (target["home_team_id"],target["away_team_id"]):
            predecessors=[(season,p) for season,p in history[league]
                if team in ((p.get("home_team") or {}).get("id"),
                            (p.get("away_team") or {}).get("id"))
                and utc(p["time_utc"])+RESULT_LAG<=now]
            last_five=predecessors[-5:]
            if len(last_five)<5:
                histories_short+=1
            for distance,(season,p) in enumerate(reversed(last_five)):
                key=(league,p["id"])
                if key in known:
                    already_observed.add(key)
                else:
                    # Every missing last-five predecessor remains a request
                    # candidate; time proximity and true last-five order win.
                    scores[(league,season,p["id"])] += (
                        priority_by_age*(6-distance))
    lookup={(scope,season,m["id"]):m
            for (scope,season),rows in groups.items() if scope in LEAGUES
            for m in rows}
    ordered=sorted(scores,key=lambda x:(-scores[x],x[0],x[1],x[2]))
    chosen=[(scope,season,lookup[(scope,season,mid)])
            for scope,season,mid in ordered[:limit]]
    report={
        "schema":"kb3-v3r-upcoming-lastfive-source-priority-v1",
        "state":"PRIORITIZED_NOT_YET_FETCHED",
        "m0_source_state":source_state,
        "real_future_m0_candidates":len(targets),
        "native_live_verified_future_targets":real_targets,
        "target_identity_quarantine":dict(quarantine),
        "teams_below_lastfive_count":histories_short,
        "missing_lastfive_unique_fixture_stat_candidates":len(scores),
        "selected_for_real_provider_fetch":len(chosen),
        "missing_after_selection_remains_queued":max(0,len(scores)-len(chosen)),
        "already_observed_lastfive_fixture_stat_rows":len(already_observed),
        "no_private_ids_in_report":True,
        "source_first_published_certified":False,
        "allow_partial_optional_stats":True,
        "no_missing_values_filled_with_zero":True,
        "original_M0_changed":False,
    }
    return chosen, report
