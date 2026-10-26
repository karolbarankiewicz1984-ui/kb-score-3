"""KB Score 3.0 — Step 11: strictly timed prematch features.

Replay is retrospective only, NEVER proof of historical prematch knowledge.
No training, predictions, odds, API requests, or database mutation.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3

FEATURE_VERSION = "kb3-step11-v0.3"
# Defaults are provisional, not fitted. Tune only after Step12 chronological split.
@dataclass(frozen=True)
class EloParameters:
    initial: float = 1500.0
    k: float = 20.0
    home_advantage: float = 65.0
    scale: float = 400.0
    season_retention: float = 0.85

    def __post_init__(self):
        for value in (self.initial, self.k, self.home_advantage, self.scale, self.season_retention):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise FeatureSafetyError("INVALID_ELO_PARAMETERS")
        if self.k <= 0 or self.scale <= 0 or not (0 <= self.season_retention <= 1):
            raise FeatureSafetyError("INVALID_ELO_PARAMETERS")

WINDOWS = (5, 10, 15)
RESULT_LAG = timedelta(hours=3)
REPLAY_LAG = timedelta(hours=48)


class FeatureSafetyError(ValueError):
    pass


def utc_dt(value):
    if not isinstance(value, str):
        raise FeatureSafetyError("MISSING_TIMESTAMP")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeatureSafetyError("INVALID_TIMESTAMP") from exc
    if date.utcoffset() is None:
        raise FeatureSafetyError("NAIVE_TIMESTAMP")
    return date.astimezone(timezone.utc)


def utc_str(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf8")).hexdigest()


def elo_probability(home, away, params=None):
    params = params or EloParameters()
    return 1.0 / (1.0 + 10 ** ((away-home-params.home_advantage)/params.scale))


def load_fixtures(db, target_id):
    """Read only the same competition and earlier/current seasons.

    Stable team IDs are required for cross-season continuity. Missing games
    in another league cannot silently count as observed history.
    """
    db.row_factory = sqlite3.Row
    target = db.execute("""
      SELECT f.fixture_id,f.season_id,f.home_team_id,f.away_team_id,f.kickoff_utc,
             se.competition_id,se.start_year AS season_start_year
      FROM fixtures f JOIN seasons se ON se.season_id=f.season_id
      WHERE f.fixture_id=?""", (target_id,)).fetchone()
    if target is None:
        raise FeatureSafetyError("TARGET_NOT_FOUND")
    history = db.execute("""
      SELECT f.fixture_id,f.season_id,se.start_year AS season_start_year,
             f.home_team_id,f.away_team_id,f.kickoff_utc,
             f.status,f.goals_home_90,f.goals_away_90,
             f.updated_utc AS result_record_updated_at_utc,
             f.result_source AS result_provider_name,
             m.match_quality,m.review_status,
             ss.snapshot_id,ss.availability_class,
             ss.captured_at_utc,ss.published_at_utc
      FROM fixtures f
      JOIN seasons se ON se.season_id=f.season_id
      LEFT JOIN providers rp ON rp.name=f.result_source
      LEFT JOIN fixture_provider_map m
          ON m.fixture_id=f.fixture_id AND m.provider_id=rp.provider_id
      LEFT JOIN source_snapshots ss
          ON ss.snapshot_id=m.source_snapshot_id AND ss.provider_id=m.provider_id
      WHERE se.competition_id=? AND se.start_year<=? AND f.fixture_id<>?
      ORDER BY f.kickoff_utc,f.fixture_id
    """, (target["competition_id"], target["season_start_year"],target_id)).fetchall()
    return dict(target), [dict(x) for x in history]

def result_eligible(row, cutoff, mode):
    start = utc_dt(row["kickoff_utc"])
    if start >= cutoff or row["status"] != "FINISHED":
        return False
    goals = (row["goals_home_90"],row["goals_away_90"])
    if not all(type(v) is int and v >= 0 for v in goals):
        return False
    if row["match_quality"] != "STRICT" or row["review_status"] != "APPROVED":
        return False
    if mode == "replay":
        return start + REPLAY_LAG < cutoff
    if row["availability_class"] != "VERIFIED_PREMATCH":
        return False
    if not row["captured_at_utc"] or not row["published_at_utc"]:
        return False
    if not row["result_record_updated_at_utc"]:
        return False
    captured = utc_dt(row["captured_at_utc"])
    published = utc_dt(row["published_at_utc"])
    row_updated = utc_dt(row["result_record_updated_at_utc"])
    # A current mutable fixture row edited after the claimed snapshot cannot
    # stand in for that older snapshot's actual result payload.
    return start + RESULT_LAG <= published <= captured <= cutoff and row_updated <= captured


def fetch_xg(db, fixture, team, kickoff, cutoff, mode):
    rows = db.execute("""
        SELECT o.numeric_value,o.observed_at_utc,s.captured_at_utc,
               s.published_at_utc,s.availability_class,s.snapshot_id
        FROM match_stat_observations o
        JOIN source_snapshots s ON s.snapshot_id=o.snapshot_id
                                   AND s.provider_id=o.provider_id
        JOIN fixture_provider_map pm ON pm.fixture_id=o.fixture_id
                                     AND pm.provider_id=o.provider_id
        WHERE o.fixture_id=? AND o.team_id=?
          AND pm.match_quality='STRICT' AND pm.review_status='APPROVED'
          AND lower(o.metric) IN ('xg','expected_goals')
    """, (fixture, team)).fetchall()
    accepted = []
    for value,observed,captured,published,classification,snapshot in rows:
        if value is None:
            continue
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
            raise FeatureSafetyError("INVALID_XG")
        if mode == "verified":
            if classification != "VERIFIED_PREMATCH" or not published:
                continue
            if not (kickoff + RESULT_LAG <= utc_dt(published)
                    <= utc_dt(observed) <= utc_dt(captured) <= cutoff):
                continue
        elif not (kickoff + REPLAY_LAG < cutoff):
            continue
        accepted.append((float(value), {
            "snapshot_id": snapshot, "observed_at_utc": observed,
            "captured_at_utc": captured, "published_at_utc": published}))
    if len({round(x[0],9) for x in accepted}) > 1:
        raise FeatureSafetyError("CONFLICTING_XG")
    accepted.sort(key=lambda x: x[1]["snapshot_id"])
    return accepted[0] if accepted else (None,None)


def build_features(db, target_id, *, cutoff_utc, mode="verified", elo_params=None):
    params = EloParameters() if elo_params is None else elo_params
    if not isinstance(params, EloParameters):
        raise FeatureSafetyError("INVALID_ELO_PARAMETERS")
    if mode not in ("verified","replay"):
        raise FeatureSafetyError("INVALID_MODE")
    target, rows = load_fixtures(db,target_id)
    cutoff = utc_dt(cutoff_utc)
    kickoff = utc_dt(target["kickoff_utc"])
    if cutoff >= kickoff:
        raise FeatureSafetyError("FEATURE_CUTOFF_NOT_BEFORE_KICKOFF")
    if target["home_team_id"] == target["away_team_id"]:
        raise FeatureSafetyError("HOME_EQUALS_AWAY")
    history = []
    excluded = defaultdict(int)
    seen = set()
    for row in rows:
        if row["fixture_id"] in seen:
            raise FeatureSafetyError("AMBIGUOUS_FIXTURE_MAPPING")
        seen.add(row["fixture_id"])
        source_start = utc_dt(row["kickoff_utc"])
        if source_start >= cutoff or source_start >= kickoff:
            excluded["not_before_cutoff"] += 1
            continue
        if row["status"] == "AWARDED":
            excluded["awarded"] += 1
            continue
        if not result_eligible(row,cutoff,mode):
            excluded["no_qualified_result"] += 1
            continue
        xgh,src_h = fetch_xg(db,row["fixture_id"],row["home_team_id"],
                             source_start,cutoff,mode)
        xga,src_a = fetch_xg(db,row["fixture_id"],row["away_team_id"],
                             source_start,cutoff,mode)
        history.append({**row,"date":source_start,"xgh":xgh,"xga":xga,
                        "xgh_source":src_h,"xga_source":src_a})
    history.sort(key=lambda r:(r["date"],r["fixture_id"]))
    ratings = {}
    last_elo_season = {}
    elo_match_counts = defaultdict(int)

    def rating_for(tid, year):
        """Decay per elapsed season, even after relegation or a missing season."""
        prior_year = last_elo_season.get(tid)
        if prior_year is not None and year < prior_year:
            raise FeatureSafetyError("NONMONOTONIC_TEAM_SEASON")
        rating = ratings.get(tid, params.initial)
        if prior_year is not None and year > prior_year:
            rating = params.initial + (rating - params.initial) * (
                params.season_retention ** (year - prior_year))
        ratings[tid] = rating
        last_elo_season[tid] = year
        return rating

    team_history = defaultdict(list)
    lineage = []
    offset = 0
    while offset < len(history):
        end = offset
        while end < len(history) and history[end]["date"] == history[offset]["date"]:
            end += 1
        batch = history[offset:end]
        participants = set()
        for row in batch:
            a,b = row["home_team_id"],row["away_team_id"]
            if a in participants or b in participants:
                raise FeatureSafetyError("SAME_TEAM_SIMULTANEOUSLY")
            participants.update((a,b))
        deltas = defaultdict(float)
        for row in batch:
            home,away = row["home_team_id"],row["away_team_id"]
            season_year = row["season_start_year"]
            pre_h,pre_a = rating_for(home,season_year),rating_for(away,season_year)
            score = (1 if row["goals_home_90"] > row["goals_away_90"] else
                     0 if row["goals_home_90"] < row["goals_away_90"] else .5)
            change = params.k*(score-elo_probability(pre_h,pre_a,params))
            elo_match_counts[home] += 1
            elo_match_counts[away] += 1
            deltas[home] += change
            deltas[away] -= change
            for tid,oid,venue,gf,ga,xg_for,xg_against,opp_elo in (
                (home,away,True,row["goals_home_90"],row["goals_away_90"],
                 row["xgh"],row["xga"],pre_a),
                (away,home,False,row["goals_away_90"],row["goals_home_90"],
                 row["xga"],row["xgh"],pre_h)):
                team_history[tid].append({
                    "fixture_id":row["fixture_id"],"kickoff_utc":row["kickoff_utc"],
                    "season_start_year":season_year,
                    "home":venue,"opponent":oid,"opponent_elo":opp_elo,
                    "gf":gf,"ga":ga,"points":3 if gf>ga else 1 if gf==ga else 0,
                    "xg":xg_for,"xga":xg_against})
            lineage.append({
                "fixture_id":row["fixture_id"],"kickoff_utc":row["kickoff_utc"],
                "season_start_year":season_year,
                "result_snapshot":row["snapshot_id"],
                "result_provider_name":row["result_provider_name"],
                "result_record_updated_at_utc":row["result_record_updated_at_utc"],
                "result_captured_at_utc":row["captured_at_utc"],
                "result_published_at_utc":row["published_at_utc"],
                "xg_home":row["xgh_source"],"xg_away":row["xga_source"]})
        for team,delta in deltas.items():
            ratings[team] += delta
        offset = end
    values = {}
    missing = {}
    for side,tid,home_venue in (
        ("home",target["home_team_id"],True),
        ("away",target["away_team_id"],False)):
        all_games = team_history[tid]
        values[side+"_elo"] = round(rating_for(tid,target["season_start_year"]),5)
        values[side+"_elo_games_available"] = elo_match_counts[tid]
        values[side+"_prior_seasons_games_available"] = sum(
            r["season_start_year"] < target["season_start_year"] for r in all_games)
        values[side+"_games_available"] = len(all_games)
        values[side+"_days_since_last_kickoff"] = (
            round((cutoff-utc_dt(all_games[-1]["kickoff_utc"])).total_seconds()/86400,4)
            if all_games else None)
        missing[side+"_days_since_last_kickoff"] = not bool(all_games)
        venue_games = [r for r in all_games if r["home"]==home_venue]
        values[side+"_venue_games_available"] = len(venue_games)
        for category,seq in (("all",all_games),("venue",venue_games)):
            for n in WINDOWS:
                group = seq[-n:]
                stem = f"{side}_{category}_{n}"
                count = len(group)
                values[stem+"_n"] = count
                for field in ("points","gf","ga","opponent_elo"):
                    values[stem+"_"+field+"_avg"] = (
                        round(sum(r[field] for r in group)/count,6) if count else None)
                for field in ("xg","xga"):
                    real = [r[field] for r in group if r[field] is not None]
                    values[stem+"_"+field+"_n"] = len(real)
                    values[stem+"_"+field+"_avg"] = (
                        round(sum(real)/len(real),6) if real else None)
                    missing[stem+"_"+field] = len(real)<count or count==0
                missing[stem+"_history"] = count<n
    values["elo_home_minus_away"] = round(
        values["home_elo"]-values["away_elo"],5)
    out = {
        "schema":FEATURE_VERSION,"fixture_id":target_id,
        "elo_parameters":asdict(params),
        "elo_parameter_status":"PROVISIONAL_NOT_FITTED",
        "result_evidence_policy":"PROVIDER_SCOPED_AND_MUTABLE_ROW_TIME_CHECKED",
        "row_payload_at_snapshot_proven":False,
        "kickoff_utc":utc_str(kickoff),"feature_cutoff_utc":utc_str(cutoff),
        "mode":mode,
        "availability_class":"RETROSPECTIVE" if mode=="replay" else "NOT_VERIFIED",
        "target_prematch_snapshot_certified":False,"training_allowed":False,
        "features":values,"missing_flags":missing,"lineage":lineage,
        "accepted_predecessor_count":len(history),
        "excluded":dict(excluded),
        "note":"Replay is NOT proof of historic availability." if mode=="replay"
               else "Only timestamp-qualified predecessor history; target unverified."}
    out["sha256"] = digest(out)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--fixture-id",type=int,required=True)
    p.add_argument("--cutoff",required=True)
    p.add_argument("--mode",choices=("verified","replay"),default="verified")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    with sqlite3.connect(a.db) as db:
        data=build_features(db,a.fixture_id,cutoff_utc=a.cutoff,mode=a.mode)
    target=Path(a.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("STEP11_FEATURES",data["sha256"],data["accepted_predecessor_count"],
          data["availability_class"])


if __name__=="__main__":
    main()
