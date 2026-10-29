"""Real PitchAPI 3-league -> SQLite M0 121+38 pre-kickoff snapshots.

Works ONLY on true live network-observed PitchAPI receipts captured by the
existing 3-league daily job. Reuses Step11 shared ELO/form/xG/lineage maths.
No synthetic training, test, M0 forecasts, retrospective first-published dates,
raw provider source redistribution or incomplete xG imputation.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from hashlib import sha256
import json,sqlite3
from src.kb3_features import _compose_features,EloParameters,utc_dt,FeatureSafetyError,digest
from src.kb3_pitch_native import check_season
from src.kb3_pit_ledger import as_utc,canonical,utc_now
from src.kb3_step14_pitchapi_xg_semantics import parse_native_team_stats,parse_native_shots
from scripts.step14_three_league_pitchapi_actual_audit import CURRENT,PREVIOUS,LEAGUES
ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-true-network-three-league-sqlite-m0-121-38-pit-observed-freeze-v1"
MODEL="M0_ELO_POISSON_UNFITTED_SHADOW_FEATURES_V1"
MIN_PREMATCH=timedelta(minutes=90)
# Step16 acceleration changes fixture COVERAGE only, never model inputs/parameters.
ACCEL_MAX_TARGETS_PER_LEAGUE=10
ACCEL_HORIZON_HOURS=96
class M0FreezeError(ValueError):pass

def opaque_sql_id(kind,orig):
    if not isinstance(orig,str) or not orig:raise M0FreezeError("INVALID_NATIVE_KEY")
    return int.from_bytes(sha256((kind+"|"+orig).encode()).digest()[:7],"big")

def matches_receipts(receipts):
    found={}; xg={}
    for r in receipts:
        if r.get("origin")!="NETWORK_OBSERVED":
            raise M0FreezeError("SOURCE_NOT_REAL")
        label=r.get("resource","")
        if not isinstance(label,str) or not label.startswith("pitchapi:"):
            raise M0FreezeError("NOT_PITCH_SOURCE")
        ended=as_utc(r["completed_at_utc"])
        if ended>datetime.now(timezone.utc)+timedelta(seconds=10):
            raise M0FreezeError("SOURCE_CLOCK_IN_FUTURE")
        if label.startswith("pitchapi:pilot_daily:"):
            parts=label.split(":")
            if len(parts)!=4:raise M0FreezeError("INVALID_SEASON_LABEL")
            _,_,country,season=parts
            if country not in {"ESP","ITA","GER"} or season not in (CURRENT,PREVIOUS):
                raise M0FreezeError("UNEXPECTED_SOURCE_LEAGUE_OR_YEAR")
            if (country,season) in found:
                raise M0FreezeError("DUPLICATE_FIXTURE_SOURCE")
            rows=r["payload"].get("matches")
            if not isinstance(rows,list):raise M0FreezeError("MATCHES_SOURCE_INVALID")
            found[(country,season)]=(r,rows)
        elif label.startswith("pitchapi:stats:") or label.startswith("pitchapi:shots:"):
            typ="stats" if label.startswith("pitchapi:stats:") else "shots"
            mid=label.split(":")[-1]
            key=(typ,mid)
            if key in xg:raise M0FreezeError("DUPLICATE_XG_SOURCE")
            xg[key]=r
    if set(found)!={(country,season) for country,_,_,_ in LEAGUES
                   for season in (CURRENT,PREVIOUS)}:
        raise M0FreezeError("THREE_LEAGUES_TWO_SEASONS_REQUIRED")
    return found,xg

def observed_three_league_snapshots(receipts,*,cutoff_utc=None,
                                    target_limit=4,horizon_hours=None):
    if (type(target_limit) is not int or not 1<=target_limit<=10 or
            (horizon_hours is not None and
             (type(horizon_hours) is not int or not 2<=horizon_hours<=168))):
        raise M0FreezeError("UNSAFE_TARGET_COVERAGE_SETTINGS")
    found,xg=matches_receipts(receipts)
    cutoff=utc_dt(cutoff_utc or utc_now())
    snapshots=[];sources=[];per_league=Counter()
    for country,aliases,expected,title in LEAGUES:
        r_now,games=found[(country,CURRENT)]
        r_old,previous=found[(country,PREVIOUS)]
        check_season(games,CURRENT,expected_count=expected)
        check_season(previous,PREVIOUS,expected_count=expected)
        if any(m["status"]!="finished" for m in previous):
            raise M0FreezeError("PREVIOUS_SEASON_INCOMPLETE")
        if len({m["id"] for m in previous+games})!=2*expected:
            raise M0FreezeError("DUPLICATE_PROVIDER_ID_ACROSS_YEARS")
        source_completed=max(as_utc(r_now["completed_at_utc"]),
                             as_utc(r_old["completed_at_utc"]))
        if source_completed>cutoff:
            raise M0FreezeError("LEAGUE_SOURCE_OBSERVED_AFTER_FEATURE_FREEZE")
        sources.extend([(country,CURRENT,r_now),(country,PREVIOUS,r_old)])
        eligible=sorted((m for m in games
            if m["status"] in ("upcoming","not_started","scheduled")
               and as_utc(m["time_utc"])>cutoff+MIN_PREMATCH
               and m.get("score_home") is None and m.get("score_away") is None
               and (horizon_hours is None or
                    as_utc(m["time_utc"])<=cutoff+timedelta(hours=horizon_hours))),
            key=lambda m:(m["time_utc"],m["id"]))[:target_limit]
        # A kickoff less than 90m away is not silently frozen.
        if not eligible:continue
        predecessor_games=[]
        for season,rows in ((PREVIOUS,previous),(CURRENT,games)):
            for m in rows:
                ko=as_utc(m["time_utc"])
                if (m["status"]!="finished"
                    or ko+timedelta(hours=3)>source_completed or ko>=cutoff):
                    continue
                predecessor_games.append((season,m))
        for target in eligible:
            tko=as_utc(target["time_utc"])
            if cutoff>=tko-MIN_PREMATCH:
                raise M0FreezeError("TOO_CLOSE_TO_KICKOFF")
            target_id=target["id"]
            historical=[]
            for season,m in predecessor_games:
                ko=as_utc(m["time_utc"])
                if m["id"]==target_id or ko>=tko:continue
                mid=m["id"];h=m["home_team"]["id"];a=m["away_team"]["id"]
                hxg=axg=None;origin=None
                sr=xg.get(("stats",mid));sh=xg.get(("shots",mid))
                if sr and sh:
                    stats_end=as_utc(sr["completed_at_utc"])
                    shots_end=as_utc(sh["completed_at_utc"])
                    if stats_end>cutoff or shots_end>cutoff:
                        raise M0FreezeError("XG_CAPTURE_AFTER_FREEZE")
                    if min(stats_end,shots_end)<ko+timedelta(hours=3):
                        raise M0FreezeError("SHOT_BEFORE_FINISHED")
                    parse_native_shots(sh["payload"],mid,h,a)
                    hxg,axg=parse_native_team_stats(sr["payload"],mid,h,a)
                    origin={"shot_observed_at_utc":sr["completed_at_utc"],
                            "provider_original_published_at_utc":None}
                historical.append({
                    "fixture_id":mid,"season_start_year":int(season[:4]),
                    "home_team_id":h,"away_team_id":a,
                    "kickoff_utc":m["time_utc"],"date":ko,
                    "status":"FINISHED","goals_home_90":m["score_home"],
                    "goals_away_90":m["score_away"],
                    "snapshot_id":r_old["chain_sha256"] if season==PREVIOUS else r_now["chain_sha256"],
                    "result_provider_name":"PitchAPI",
                    "result_record_updated_at_utc":None,
                    "captured_at_utc":r_old["completed_at_utc"] if season==PREVIOUS else r_now["completed_at_utc"],
                    "published_at_utc":None,
                    "xgh":hxg,"xga":axg,
                    "xgh_source":origin,"xga_source":origin})
            target_row={"fixture_id":target_id,
                        "home_team_id":target["home_team"]["id"],
                        "away_team_id":target["away_team"]["id"],
                        "season_start_year":2026}
            evidence={"provider":"PitchAPI","source_observed_at_utc":
                source_completed.isoformat().replace("+00:00","Z"),
                "country":country,"current_receipt_chain_sha256":r_now["chain_sha256"],
                "previous_receipt_chain_sha256":r_old["chain_sha256"],
                "original_provider_first_published_at_known":False}
            snapshot=_compose_features(target_row,historical,cutoff=cutoff,
                kickoff=tko,target_id=target_id,
                mode="observed",params=EloParameters(),
                excluded=defaultdict(int),source_evidence=evidence)
            if (len(snapshot["features"]),len(snapshot["missing_flags"]))!=(121,38):
                raise M0FreezeError("ORIGINAL_121_PLUS_38_FEATURE_COUNT_MISMATCH")
            if (set(snapshot["feature_availability"])!=
                 set(snapshot["features"])|{"missing:"+k for k in snapshot["missing_flags"]}):
                raise M0FreezeError("NOT_ALL_159_FIELDS_HAVE_ACTUAL_RECEIPT_CLOCK")
            if any(as_utc(x["latest_required_observed_at_utc"])>cutoff for
                   x in snapshot["feature_availability"].values()):
                raise M0FreezeError("FEATURE_OBSERVED_AFTER_CUTOFF")
            if (snapshot["training_allowed"] is not False
                or snapshot["target_prematch_snapshot_certified"] is not False
                or snapshot["availability_class"]!="OBSERVED_AT_NOT_CERTIFIED"):
                raise M0FreezeError("ORIGINAL_PIT_GATE_OVERRIDDEN")
            snapshots.append((country,title,target,snapshot))
            per_league[title]+=1
    if target_limit==4 and horizon_hours is None:
        if len(snapshots)!=12 or dict(per_league)!={"LaLiga":4,"Serie A":4,"Bundesliga":4}:
            raise M0FreezeError("THREE_TIMES_FOUR_PREMATCH_SNAPSHOTS_REQUIRED")
    elif (len(snapshots)>3*target_limit or
          any(x>target_limit for x in per_league.values())):
        raise M0FreezeError("ACCELERATED_TARGET_COUNT_INVALID")
    if any(as_utc(x[2]["time_utc"])<=cutoff+MIN_PREMATCH for x in snapshots):
        raise M0FreezeError("FROZEN_TARGET_ALREADY_STARTED")
    return snapshots,sources,cutoff

def commit_sqlite(db_path,receipts,*,cutoff_utc,raw_cipher_sha,raw_chain_sha,
                  target_limit=4,horizon_hours=None):
    snapshots,sources,cutoff=observed_three_league_snapshots(
        receipts,cutoff_utc=cutoff_utc,target_limit=target_limit,
        horizon_hours=horizon_hours)
    path=Path(db_path);path.parent.mkdir(parents=True,exist_ok=True)
    create=not path.exists()
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        if create:
            db.executescript((ROOT/"migrations/001_initial_schema.sql").read_text())
        db.executescript((ROOT/"migrations/002_forward_m0_observed_freeze.sql").read_text())
        now=cutoff.isoformat().replace("+00:00","Z")
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("""INSERT OR IGNORE INTO providers(provider_id,name,terms_review_status,created_utc)
                       VALUES(1,'PitchAPI','PENDING',?)""",(now,))
            db.execute("""INSERT OR IGNORE INTO model_versions(model_version_id,family,code_sha,created_at_utc,approval_status)
                        VALUES(?,?,?,?,?)""",(MODEL,"M0_ELO_POISSON","UNFITTED_STEP13_MATH_PROTOTYPE",now,"EXPERIMENT"))
            country_index={c:i+1 for i,(c,*_) in enumerate(LEAGUES)}
            for country,season,r in sources:
                sid=r["chain_sha256"];pid=r["payload_sha256"]
                db.execute("""INSERT OR IGNORE INTO source_snapshots
                    (snapshot_id,provider_id,endpoint_label,captured_at_utc,
                     published_at_utc,source_data_hash,availability_class)
                    VALUES(?,1,?,?,NULL,?,'NOT_VERIFIED')""",
                    (sid,r["resource"],r["completed_at_utc"],pid))
                db.execute("""INSERT OR IGNORE INTO m0_forward_sources
                  (source_id,country,season,actual_completed_utc,network_response_sha256,
                   raw_provider_first_published_at_utc) VALUES(?,?,?,?,?,NULL)""",
                  (sid,country,season,r["completed_at_utc"],pid))
            for country,title,target,snapshot in snapshots:
                competition=country_index[country]
                db.execute("""INSERT OR IGNORE INTO competitions(competition_id,name,country,type)
                           VALUES(?,?,?,'LEAGUE')""",(competition,title,country))
                season_id=competition*10000+2026
                db.execute("""INSERT OR IGNORE INTO seasons(season_id,competition_id,start_year,season_label)
                           VALUES(?,?,2026,'2026/2027')""",(season_id,competition))
                h=target["home_team"];a=target["away_team"]
                for t in (h,a):
                    tid=opaque_sql_id("team",t["id"])
                    db.execute("""INSERT OR IGNORE INTO teams(team_id,canonical_name,country)
                               VALUES(?,?,?)""",(tid,t["name"],country))
                    db.execute("""INSERT OR IGNORE INTO team_provider_map
                       (provider_id,external_team_id,team_id,valid_from_utc)
                       VALUES(1,?,?,'2026-01-01T00:00:00Z')""",(t["id"],tid))
                fid=opaque_sql_id("fixture",target["id"])
                db.execute("""INSERT OR IGNORE INTO fixtures
                  (fixture_id,season_id,home_team_id,away_team_id,kickoff_utc,status,
                   created_utc,updated_utc)
                  VALUES(?,?,?,?,?,'SCHEDULED',?,?)""",
                  (fid,season_id,opaque_sql_id("team",h["id"]),
                   opaque_sql_id("team",a["id"]),target["time_utc"],now,now))
                existing=db.execute("SELECT kickoff_utc,home_team_id,away_team_id FROM fixtures WHERE fixture_id=?",
                    (fid,)).fetchone()
                if existing!=(target["time_utc"],opaque_sql_id("team",h["id"]),
                              opaque_sql_id("team",a["id"])):
                    # Never silently amend already frozen old fixture identity.
                    raise M0FreezeError("SCHEDULE_CHANGED_REQUIRES_EXPLICIT_REVISION")
                payload=json.dumps(snapshot,sort_keys=True,separators=(",",":"),
                                   ensure_ascii=False,allow_nan=False)
                record_id=digest({"country":country,"fixture":target["id"],
                   "day":cutoff.date().isoformat(),"cutoff":now,
                   "feature_hash":snapshot["sha256"]})
                countxg=sum(1 for k,v in snapshot["features"].items()
                            if k.endswith("_xg_avg") and v is not None)
                db.execute("""INSERT INTO feature_snapshots
                  (feature_snapshot_id,fixture_id,model_version_id,observed_cutoff_utc,
                   generated_at_utc,feature_hash,missing_flags_json,availability_class)
                  VALUES(?,?,?,?,?,?,?,'NOT_VERIFIED')""",
                  (record_id,fid,MODEL,now,now,snapshot["sha256"],
                   json.dumps(snapshot["missing_flags"],sort_keys=True)))
                db.execute("""INSERT INTO m0_forward_feature_records
                  (record_id,feature_snapshot_id,league_country,provider_match_id,
                   provider_home_team_id,provider_away_team_id,snapshot_day_utc,
                   kickoff_original_utc,captured_before_kickoff_utc,signed_source_chain_sha256,
                   source_ciphertext_sha256,feature_payload_json,numeric_fields,
                   missing_flag_fields,source_xg_count,eligible_for_original_M1)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,121,?,?,0)""",
                  (record_id,record_id,country,target["id"],h["id"],a["id"],
                   cutoff.date().isoformat(),target["time_utc"],now,
                   raw_chain_sha,raw_cipher_sha,payload,38,countxg))
            db.commit()
        except BaseException:
            db.rollback();raise
        rows=db.execute("""SELECT COUNT(*) FROM m0_forward_feature_records""").fetchone()[0]
        daily=db.execute("""SELECT league_country,COUNT(*)
             FROM m0_forward_feature_records WHERE snapshot_day_utc=?
             GROUP BY league_country""",(cutoff.date().isoformat(),)).fetchall()
        expected=dict(Counter(c for c,_,_,_ in snapshots))
        if dict(daily)!=expected or any(v>target_limit for v in expected.values()):
            raise M0FreezeError("SQLITE_FROZEN_COUNTS_MISMATCH")
        fk=db.execute("PRAGMA foreign_key_check").fetchall()
        if fk:raise M0FreezeError("SQLITE_REFERENTIAL_INTEGRITY_FAIL")
        if db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] !=0:
            raise M0FreezeError("NO_AUTOMATIC_FORECAST_ALLOWED")
    return {"schema":SCHEMA,"frozen_feature_snapshots_today":len(snapshots),
      "target_limit_per_league":target_limit,
      "target_horizon_hours":horizon_hours,
      "total_immutable_snapshots_in_db":rows,
      "by_country":dict(daily),
      "numeric_fields_per_snapshot":121,"missing_flags_per_snapshot":38,
      "fully_verified_PitchAPI_xG_15_per_side":False,
      "observed_on_live_UTC":now,"target_results_accessed":False,
      "source_original_published_at_known":False,
      "original_TEST_Premier_League_2026_27_accessed":False,
      "original_Gate14_pass":False,"model_fit_or_forecast_generated":False,
      "real_SQLite_persisted":True}
