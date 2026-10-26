"""KB Score 3.0 — Step 11: strictly timed prematch features.

Replay is retrospective only, NEVER proof of historical prematch knowledge.
No training, predictions, odds, API requests, or database mutation.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3

FEATURE_VERSION = "kb3-step11-v0.1"
ELO_INITIAL = 1500.0  # provisional prior; estimate parameters only on future TRAIN
ELO_K = 20.0
HOME_ADVANTAGE = 65.0
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


def elo_probability(home, away):
    return 1.0 / (1.0 + 10 ** ((away-home-HOME_ADVANTAGE)/400.0))


def load_fixtures(db, target_id):
    db.row_factory = sqlite3.Row
    target = db.execute("""
      SELECT fixture_id, season_id, home_team_id, away_team_id, kickoff_utc
      FROM fixtures WHERE fixture_id=?""", (target_id,)).fetchone()
    if target is None:
        raise FeatureSafetyError("TARGET_NOT_FOUND")
    history = db.execute("""
      SELECT f.fixture_id,f.season_id,f.home_team_id,f.away_team_id,
             f.kickoff_utc,f.status,f.goals_home_90,f.goals_away_90,
             m.match_quality,m.review_status,
             s.snapshot_id,s.availability_class,s.captured_at_utc,s.published_at_utc
      FROM fixtures f
      LEFT JOIN fixture_provider_map m ON f.fixture_id=m.fixture_id
      LEFT JOIN source_snapshots s ON s.snapshot_id=m.source_snapshot_id
      WHERE f.season_id=? AND f.fixture_id<>?
      ORDER BY f.kickoff_utc,f.fixture_id
    """, (target["season_id"], target_id)).fetchall()
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
    captured = utc_dt(row["captured_at_utc"])
    published = utc_dt(row["published_at_utc"])
    return start + RESULT_LAG <= published <= captured <= cutoff


def fetch_xg(db, fixture, team, kickoff, cutoff, mode):
    rows = db.execute("""
        SELECT o.numeric_value,o.observed_at_utc,s.captured_at_utc,
               s.published_at_utc,s.availability_class,s.snapshot_id
        FROM match_stat_observations o
        JOIN source_snapshots s ON s.snapshot_id=o.snapshot_id
        WHERE o.fixture_id=? AND o.team_id=?
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


def build_features(db, target_id, *, cutoff_utc, mode="verified"):
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
    ratings = defaultdict(lambda:ELO_INITIAL)
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
            pre_h,pre_a = ratings[home],ratings[away]
            score = (1 if row["goals_home_90"] > row["goals_away_90"] else
                     0 if row["goals_home_90"] < row["goals_away_90"] else .5)
            change = ELO_K*(score-elo_probability(pre_h,pre_a))
            deltas[home] += change
            deltas[away] -= change
            for tid,oid,venue,gf,ga,xg_for,xg_against,opp_elo in (
                (home,away,True,row["goals_home_90"],row["goals_away_90"],
                 row["xgh"],row["xga"],pre_a),
                (away,home,False,row["goals_away_90"],row["goals_home_90"],
                 row["xga"],row["xgh"],pre_h)):
                team_history[tid].append({
                    "fixture_id":row["fixture_id"],"kickoff_utc":row["kickoff_utc"],
                    "home":venue,"opponent":oid,"opponent_elo":opp_elo,
                    "gf":gf,"ga":ga,"points":3 if gf>ga else 1 if gf==ga else 0,
                    "xg":xg_for,"xga":xg_against})
            lineage.append({
                "fixture_id":row["fixture_id"],"kickoff_utc":row["kickoff_utc"],
                "result_snapshot":row["snapshot_id"],
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
        values[side+"_elo"] = round(ratings[tid],5)
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
        ratings[target["home_team_id"]]-ratings[target["away_team_id"]],5)
    out = {
        "schema":FEATURE_VERSION,"fixture_id":target_id,
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
