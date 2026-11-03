"""KB3 retrospective rolling 5/10/15 history and source-completeness audit.

A fixture ledger lists *every* finished predecessor, not merely matches
with observed statistics. No missing match is silently skipped. All historic
features are RESEARCH_RECONSTRUCTED, never certified original provider PIT.
This module does not read/modify live forecasts, calibrators or the protected TEST.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

WINDOWS = (5, 10, 15)
METRICS = (
    "total_shots", "ShotsOnTarget", "ShotsOffTarget", "fouls", "corners",
    "yellow_cards", "red_cards", "Offsides", "passes", "accurate_passes",
    "interceptions", "clearances", "keeper_saves", "big_chance",
    "shots_inside_box", "shots_outside_box", "touches_opp_box",
    "expected_goals_non_penalty", "expected_goals_open_play",
    "expected_goals_set_play", "expected_goals_on_target",
)
CORE = ("total_shots", "fouls", "corners", "yellow_cards")
FEATURE_VERSION = "kb3-historical-rolling-source-v1-research-not-pit"
NUMERIC = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")

FIXTURE_SQL = """
CREATE TABLE IF NOT EXISTS finished_fixture_index (
 scope TEXT NOT NULL, season TEXT NOT NULL, match_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL, home_team_id TEXT NOT NULL, away_team_id TEXT NOT NULL,
 goals_home_90 INTEGER NOT NULL, goals_away_90 INTEGER NOT NULL,
 listing_observed_at_utc TEXT NOT NULL, source_listing_sha256 TEXT NOT NULL,
 original_provider_first_published_utc TEXT CHECK(original_provider_first_published_utc IS NULL),
 PRIMARY KEY(scope,match_id)
);
CREATE TRIGGER IF NOT EXISTS finished_fixture_index_no_update
 BEFORE UPDATE ON finished_fixture_index
 BEGIN SELECT RAISE(ABORT,'FIXTURE_HISTORY_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS finished_fixture_index_no_delete
 BEFORE DELETE ON finished_fixture_index
 BEGIN SELECT RAISE(ABORT,'FIXTURE_HISTORY_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS rolling_feature_cache (
 scope TEXT NOT NULL, target_match_id TEXT NOT NULL,
 target_kickoff_utc TEXT NOT NULL, feature_version TEXT NOT NULL,
 research_only INTEGER NOT NULL CHECK(research_only=1),
 provider_original_pit_certified INTEGER NOT NULL CHECK(provider_original_pit_certified=0),
 feature_json TEXT NOT NULL, source_index_sha256 TEXT NOT NULL,
 PRIMARY KEY(scope,target_match_id)
);
"""


def _utc(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("INVALID_DATETIME")
    if dt.tzinfo is None:
        raise ValueError("NAIVE_DATETIME")
    return dt.astimezone(timezone.utc)


def ensure_tables(db):
    db.executescript(FIXTURE_SQL)


def add_fixture_rows(db_path, indexed):
    """Append full chronological fixture ledger, fail closed on changed identities.

    indexed entries: (scope,season,valid_finished_match,completed_utc,payload_sha).
    Existing observations are not modified. All fixture entries are already
    checked by the main collector's validate_match_rows.
    """
    with sqlite3.connect(db_path) as db:
        ensure_tables(db)
        inserted = 0
        for scope, season, m, captured, sha in indexed:
            if scope == "ENG" or m.get("status") != "finished":
                raise ValueError("FORBIDDEN_OR_UNFINISHED_FIXTURE")
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError("INVALID_SOURCE_HASH")
            if _utc(m["time_utc"]) + timedelta(hours=3) > _utc(captured):
                raise ValueError("RESULT_TOO_FRESH_FOR_INDEX")
            if any(type(m[k]) is not int or m[k] < 0 for k in ("score_home","score_away")):
                raise ValueError("BAD_FINISHED_GOALS")
            data=(scope,season,m["id"],m["time_utc"],
                  m["home_team"]["id"],m["away_team"]["id"],
                  m["score_home"],m["score_away"],captured,sha,None)
            present=db.execute("""SELECT season,kickoff_utc,home_team_id,away_team_id,
                                  goals_home_90,goals_away_90
                                  FROM finished_fixture_index WHERE scope=? AND match_id=?""",
                               (scope,m["id"])).fetchone()
            if present:
                if present != data[1:8][:1]+data[3:8]:
                    raise ValueError("PROVIDER_FINISHED_FIXTURE_REVISION_QUARANTINE")
                continue
            db.execute("""INSERT INTO finished_fixture_index (
                         scope,season,match_id,kickoff_utc,home_team_id,away_team_id,
                         goals_home_90,goals_away_90,listing_observed_at_utc,
                         source_listing_sha256,original_provider_first_published_utc)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)""",data)
            inserted += 1
        n=db.execute("SELECT COUNT(*) FROM finished_fixture_index").fetchone()[0]
        db.commit()
    return inserted,n


def _metric_number(value):
    if isinstance(value,(bool,int,float)) and (not isinstance(value,bool)):
        v=float(value)
        return v if math.isfinite(v) else None
    if not isinstance(value,str) or not NUMERIC.fullmatch(value.strip()):
        return None
    v=float(value.strip())
    return v if math.isfinite(v) else None


def raw_stat(row,metric,side):
    """Duplicate keys may agree, but conflicting group values are unavailable."""
    values=[_metric_number(item.get(side)) for item in row.get("items",[])
            if item.get("key")==metric]
    if not values or any(x is None for x in values):
        return None
    if max(values)-min(values)>1e-7:
        return None
    return values[0]


def _signed_side(fixture,team_id):
    if team_id==fixture["home_team_id"]:
        return "home"
    if team_id==fixture["away_team_id"]:
        return "away"
    raise ValueError("FIXTURE_TEAM_ID_MISMATCH")


def _feature_for_match(f,obs,team):
    side=_signed_side(f,team)
    home=side=="home"
    gf=f["goals_home_90"] if home else f["goals_away_90"]
    ga=f["goals_away_90"] if home else f["goals_home_90"]
    values={"goals_for":float(gf),"goals_against":float(ga),
            "points":float(3 if gf>ga else 1 if gf==ga else 0)}
    if obs:
        for key in METRICS:
            values[key]=raw_stat(obs,key,side)
        if obs["xg_status"]=="VERIFIED":
            values["xg_for"]=obs["xg_home"] if home else obs["xg_away"]
            values["xg_against"]=obs["xg_away"] if home else obs["xg_home"]
        else:
            values["xg_for"]=values["xg_against"]=None
    else:
        for key in METRICS+("xg_for","xg_against"):
            values[key]=None
    return values


def rolling_window(all_history, observed,team_id,n,venue=None):
    """Choose true chronological last N *fixtures* before considering stats.

    venue: None for all matches, "home" or "away" for same-venue history.
    Missing xG in a required fixture may NEVER be swapped for an older one.
    """
    if venue not in (None,"home","away") or n not in WINDOWS:
        raise ValueError("INVALID_ROLLING_SCOPE")
    seq=[f for f in all_history if team_id in (f["home_team_id"],f["away_team_id"])
         and (venue is None or _signed_side(f,team_id)==venue)]
    recent=seq[-n:]
    values=[_feature_for_match(f,observed.get((f["scope"],f["match_id"])),team_id)
            for f in recent]
    keys=("goals_for","goals_against","points","xg_for","xg_against")+METRICS
    summary={}
    for key in keys:
        valid=[row[key] for row in values if row.get(key) is not None]
        # Partial mean is intentionally NOT a model feature: null until true N/N.
        summary[key]={"valid_n":len(valid),
                      "complete":len(valid)==n,
                      "mean":(round(sum(valid)/n,6) if len(valid)==n else None)}
    stats_n=sum((f["scope"],f["match_id"]) in observed for f in recent)
    return {"requested_n":n,"actual_predecessors":len(recent),
            "history_complete":len(recent)==n,
            "stats_match_n":stats_n,
            "stats_complete":stats_n==n,
            "xg_complete":summary["xg_for"]["complete"] and summary["xg_against"]["complete"],
            "core_stats_complete":len(recent)==n and all(summary[k]["complete"] for k in CORE),
            "metrics":summary}


def _load_records(db):
    fixt=defaultdict(list)
    for r in db.execute("""SELECT scope,season,match_id,kickoff_utc,home_team_id,
                    away_team_id,goals_home_90,goals_away_90
                    FROM finished_fixture_index ORDER BY kickoff_utc,match_id"""):
        f=dict(zip(("scope","season","match_id","kickoff_utc","home_team_id",
                    "away_team_id","goals_home_90","goals_away_90"),r))
        fixt[f["scope"]].append(f)
    obs={}
    for r in db.execute("""SELECT scope,match_id,kickoff_utc,home_team_id,away_team_id,
                     stat_items_json,xg_status,xg_home,xg_away
                     FROM observations"""):
        scope,mid,ko,home,away,items,status,xgh,xga=r
        obs[(scope,mid)]={"kickoff_utc":ko,"home_team_id":home,
            "away_team_id":away,"items":json.loads(items),"xg_status":status,
            "xg_home":xgh,"xg_away":xga}
    return fixt,obs


def assess_and_cache(db_path,report_path):
    """Recompute research-only rolling features and aggregate source gaps.

    Cached derived values may be refreshed; original observations/index cannot.
    Feature rows target recorded finished games, never in-play/future fixtures.
    """
    path=Path(db_path)
    source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    totals=Counter()
    by_scope=defaultdict(Counter)
    with sqlite3.connect(path) as db:
        ensure_tables(db)
        fixt,obs=_load_records(db)
        if any(scope=="ENG" for scope in fixt):
            raise ValueError("PROTECTED_PREMIER_LEAGUE_TEST_IN_HISTORY")
        index={(f["scope"],f["match_id"]):f for arr in fixt.values() for f in arr}
        # Incomplete legacy data can be inspected but must never be assumed complete.
        db.execute("DELETE FROM rolling_feature_cache")
        for (scope,mid),data in sorted(obs.items()):
            target=index.get((scope,mid))
            if target is None:
                totals["target_missing_from_fixture_index"]+=1
                by_scope[scope]["target_missing_from_fixture_index"]+=1
                continue
            if (target["kickoff_utc"]!=data["kickoff_utc"] or
                target["home_team_id"]!=data["home_team_id"] or
                target["away_team_id"]!=data["away_team_id"]):
                raise ValueError("TARGET_FIXTURE_OBSERVATION_IDENTITY_MISMATCH")
            # Exclude target and any games played <3h before its kickoff.
            kickoff=_utc(target["kickoff_utc"])
            history=[f for f in fixt[scope] if f["match_id"]!=mid and
                     _utc(f["kickoff_utc"])+timedelta(hours=3)<=kickoff]
            side={}
            for name,tid,venue in (("home",target["home_team_id"],"home"),
                                   ("away",target["away_team_id"],"away")):
                side[name]={}
                for kind,place in (("all",None),("venue",venue)):
                    side[name][kind]={str(n):rolling_window(history,obs,tid,n,place)
                                      for n in WINDOWS}
            row={"schema":FEATURE_VERSION,"source":"PitchAPI",
                "scope":scope,"target_match_id":mid,
                "target_kickoff_utc":target["kickoff_utc"],
                "availability_class":"HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
                "actual_source_first_published_at_known":False,
                "original_pit_certified":False,"training_approved":False,
                "inter_competition_team_mapping_certified":False,
                "sides":side}
            jsonblob=json.dumps(row,sort_keys=True,separators=(",",":"))
            db.execute("""INSERT INTO rolling_feature_cache
              (scope,target_match_id,target_kickoff_utc,feature_version,
               research_only,provider_original_pit_certified,feature_json,
               source_index_sha256)
              VALUES(?,?,?,?,1,0,?,?)""",
              (scope,mid,target["kickoff_utc"],FEATURE_VERSION,jsonblob,source_hash))
            totals["targets_checked"]+=1
            by_scope[scope]["targets_checked"]+=1
            for n in WINDOWS:
                home,away=(side[s]["all"][str(n)] for s in ("home","away"))
                for name,field in (("history","history_complete"),("stats","stats_complete"),
                                   ("xg","xg_complete"),("core","core_stats_complete")):
                    if home[field] and away[field]:
                        totals[f"pair_{name}_{n}_complete"]+=1
                        by_scope[scope][f"pair_{name}_{n}_complete"]+=1
                    else:
                        totals[f"pair_{name}_{n}_incomplete"]+=1
                        by_scope[scope][f"pair_{name}_{n}_incomplete"]+=1
        total_fixtures=sum(len(x) for x in fixt.values())
        totals["indexed_finished_fixtures"]=total_fixtures
        totals["total_observed_stats_matches"]=len(obs)
        totals["xg_verified_matches"]=sum(v["xg_status"]=="VERIFIED" for v in obs.values())
        totals["xg_unverified_matches"]=len(obs)-totals["xg_verified_matches"]
        totals["missing_stat_match_count"]=total_fixtures-len(obs)
        cached=db.execute("SELECT COUNT(*) FROM rolling_feature_cache").fetchone()[0]
        assert cached==totals["targets_checked"]
        assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        db.commit()
    report={"schema":FEATURE_VERSION,
            "quality":"REAL_SOURCE_COUNTS_RETROSPECTIVE_RESEARCH_ONLY",
            "source_db_sha256_before_feature_cache":source_hash,
            "totals":dict(sorted(totals.items())),
            "by_scope":{k:dict(sorted(v.items())) for k,v in sorted(by_scope.items())},
            "missing_season_notice":"POL_2023_24_AND_2024_25_UNAVAILABLE_IN_PITCHAPI_CATALOG_AS_OF_2026_11_03",
            "history_n_definition":"ACTUAL_LAST_N_FINISHED_FIXTURES_NOT_LAST_N_WITH_STATS",
            "rolling_windows":list(WINDOWS),
            "venue_specific":True,
            "stat_keys":list(METRICS),
            "no_missing_as_zero":True,
            "never_use_target_result_as_its_own_feature":True,
            "retrospective_provider_original_publication_proven":False,
            "full_feature_training_approved":False,
            "official_calibration_changed":False,
            "existing_m0_modified":False,
            "protected_test_touched":False,
            "gate16_gate17":"PENDING"}
    report_path=Path(report_path)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    with report_path.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,sort_keys=True)
        f.write("\n")
    return report
