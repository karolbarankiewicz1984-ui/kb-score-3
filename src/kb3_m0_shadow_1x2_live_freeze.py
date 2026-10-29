"""Generate real pre-match 1/X/2 M0 shadow predictions from immutable SQLite.

Only original Step13 Elo + independent Poisson math, illustrative UNFITTED
parameters. Input is 121+38 Step11 real observed-before-target feature freeze.
No use of fixture target results, odds, PL 2026/27 TEST, no historic original
M1 PIT promotion. Each future fixture has one irreversible EARLY forecast.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,shutil,sqlite3
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_features import digest
from src.kb3_pit_ledger import as_utc,canonical,utc_now
from src.kb3_step13_baseline import BaselineParameters,forecast
from src.kb3_three_league_sqlite_forward_features import MODEL,opaque_sql_id

ROOT=Path(__file__).resolve().parents[1]
VERSION="kb3-real-forward-M0-Elo-Poisson-shadow-1x2-v1"
MIN_MARGIN=timedelta(minutes=90)
MODEL_ENGINE="KB3_ELO_POISSON_M0_V0_1"
class ForecastFreezeError(ValueError):pass

def utc_string(x):
    return x.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def _verify_snapshot(row,*,now):
    (sid,fid,version,cutoff_db,feature_sha,source_sha,league,match_id,
     kick_db,h_id,a_id,stored_json,flags_db,hname,aname,fixture_status,
     fs_availability,approval_status,source_chain)=row
    if (league not in ("ESP","ITA","GER") or version!=MODEL
            or fs_availability!="NOT_VERIFIED" or approval_status!="EXPERIMENT"
            or fixture_status!="SCHEDULED" or not match_id.startswith("m_")):
        raise ForecastFreezeError("NOT_THE_ISOLATED_M0_SHADOW_FEATURE_INPUT")
    if source_sha!=feature_sha or not source_chain or len(source_chain)!=64:
        raise ForecastFreezeError("SOURCE_FEATURE_SHA_OR_CHAIN_MISMATCH")
    payload=json.loads(stored_json)
    if (payload.get("sha256")!=feature_sha or
        digest({k:v for k,v in payload.items() if k!="sha256"})!=feature_sha):
        raise ForecastFreezeError("FROZEN_FEATURE_PAYLOAD_TAMPERED")
    if payload.get("fixture_id")!=match_id or payload.get("kickoff_utc")!=kick_db:
        raise ForecastFreezeError("TARGET_FIXTURE_ID_OR_KICKOFF_CHANGED")
    if (payload.get("availability_class")!="OBSERVED_AT_NOT_CERTIFIED"
        or payload.get("training_allowed") is not False
        or payload.get("target_prematch_snapshot_certified") is not False
        or payload.get("mode")!="observed"):
        raise ForecastFreezeError("FALSE_TRAINING_ORIGINAL_PIT_CLAIM")
    v=payload.get("features");missing=payload.get("missing_flags")
    if not isinstance(v,dict) or len(v)!=121 or not isinstance(missing,dict) or len(missing)!=38:
        raise ForecastFreezeError("EXPECTED_121_NUMERIC_38_FLAGS")
    if any(type(x) is not bool for x in missing.values()):
        raise ForecastFreezeError("MISSING_FLAGS_NOT_BOOLEAN")
    if json.loads(flags_db)!=missing:
        raise ForecastFreezeError("SQLITE_VS_FULL_FEATURE_FLAGS_DIFFER")
    clocks=payload.get("feature_availability")
    if not isinstance(clocks,dict) or set(clocks)!=(set(v)|{"missing:"+k for k in missing}):
        raise ForecastFreezeError("159_FEATURE_SOURCE_CLOCKS_MISSING")
    kickoff=as_utc(kick_db);cutoff=as_utc(cutoff_db)
    if payload.get("feature_cutoff_utc")!=utc_string(cutoff).replace(".000000",""):
        # Source serializer uses second or microsecond precision, compare UTC instant.
        if as_utc(payload.get("feature_cutoff_utc"))!=cutoff:
            raise ForecastFreezeError("FROZEN_FEATURE_CUTOFF_CHANGED")
    if not cutoff<now<kickoff-MIN_MARGIN:
        return None
    if any(as_utc(item["latest_required_observed_at_utc"])>cutoff for item in clocks.values()):
        raise ForecastFreezeError("HISTORIC_OBSERVATION_AFTER_INPUT_CUTOFF")
    if any(item.get("provider_original_published_at_utc") is not None for item in clocks.values()):
        raise ForecastFreezeError("UNPROVEN_ORIGINAL_PUBLISH_TIME_MISLABELLED")
    for x in ("home_elo","away_elo"):
        if type(v.get(x)) not in (int,float) or not math.isfinite(v[x]) or not 100<=v[x]<=4000:
            raise ForecastFreezeError("INVALID_ELO_VALUE")
    for x in ("home_all_5_n","away_all_5_n"):
        if type(v.get(x)) is not int or v[x]<5:
            # True early-stage cold starts are not mislabeled as full form.
            return None
    if (not isinstance(hname,str) or not hname.strip()
            or not isinstance(aname,str) or not aname.strip()):
        raise ForecastFreezeError("TEAM_NAMES_IN_RELATIONAL_SOURCE_MISSING")
    return payload,v,kickoff,cutoff

def freeze(db_path,*,report_path=None,now=None,strict_initial_count=False):
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):
        raise ForecastFreezeError("SERVER_UTC_CLOCK_REQUIRED")
    path=Path(db_path)
    if not path.is_file():raise ForecastFreezeError("ACTUAL_PERSISTED_SQLITE_MISSING")
    params=BaselineParameters()
    params_sha=hashlib.sha256(canonical(asdict(params))).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript((ROOT/"migrations/003_m0_1x2_shadow_freeze.sql").read_text())
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ForecastFreezeError("SQLITE_INTEGRITY_CHECK_FAILED")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ForecastFreezeError("SQLITE_FOREIGN_KEYS_FAILED")
        # Latest source snapshot per target only (one earlier snapshot per fixture
        # can be frozen); no later observations may edit the original prediction.
        rows=db.execute("""SELECT fs.feature_snapshot_id,fs.fixture_id,fs.model_version_id,
           fs.observed_cutoff_utc,fs.feature_hash,mr.feature_sha256_dummy,
           mr.league_country,mr.provider_match_id,mr.kickoff_original_utc,
           mr.provider_home_team_id,mr.provider_away_team_id,mr.feature_payload_json,
           fs.missing_flags_json,home.canonical_name,away.canonical_name,
           f.status,fs.availability_class,mv.approval_status,
           mr.signed_source_chain_sha256
          FROM m0_forward_feature_records mr
          JOIN feature_snapshots fs ON fs.feature_snapshot_id=mr.feature_snapshot_id
          JOIN fixtures f ON f.fixture_id=fs.fixture_id
          JOIN model_versions mv ON mv.model_version_id=fs.model_version_id
          JOIN teams home ON home.team_id=f.home_team_id
          JOIN teams away ON away.team_id=f.away_team_id
          WHERE NOT EXISTS(SELECT 1 FROM m0_shadow_1x2_forecasts pr
            WHERE pr.league_country=mr.league_country
              AND pr.provider_match_id=mr.provider_match_id
              AND pr.phase='EARLY')
          ORDER BY mr.league_country,mr.provider_match_id,
                   fs.observed_cutoff_utc DESC""".replace("mr.feature_sha256_dummy","fs.feature_hash")).fetchall()
        chosen={}
        for row in rows:
            key=(row[6],row[7])
            if key not in chosen:chosen[key]=row
        scored=[];not_eligible=0
        for row in chosen.values():
            checked=_verify_snapshot(row,now=now)
            if checked is None:
                not_eligible+=1
                continue
            payload,features,kickoff,cutoff=checked
            forecast_data=forecast(features["home_elo"],features["away_elo"],params)
            if forecast_data["parameters_status"]!="ILLUSTRATIVE_UNFITTED_NOT_FOR_BETTING":
                raise ForecastFreezeError("UNEXPECTED_M0_ENGINE_FIT")
            probabilities=forecast_data["p_1x2"]
            if not math.isclose(sum(probabilities.values()),1.0,abs_tol=1e-12):
                raise ForecastFreezeError("INVALID_THREE_WAY_PROBABILITY_MASS")
            league,mid=row[6],row[7];sid=row[0];feature_sha=row[4]
            generated=utc_string(now)
            item={"schema":VERSION,"league":league,"match_id":mid,
                  "home":row[13],"away":row[14],"kickoff_utc":row[8],
                  "feature_snapshot_id":sid,"feature_sha256":feature_sha,
                  "feature_cutoff_utc":row[3],"generated_at_utc":generated,
                  "engine":MODEL_ENGINE,
                  "parameter_status":"ILLUSTRATIVE_UNFITTED_NOT_FOR_BETTING",
                  "params_sha256":params_sha,
                  "elo_pre_match":{"home":features["home_elo"],"away":features["away_elo"]},
                  "p_1x2":probabilities,
                  "expected_goals":forecast_data["expected_goals"],
                  "phase":"EARLY","evidence_state":"OBSERVED_BEFORE_KICKOFF_NOT_ORIGINAL_HISTORIC_PIT",
                  "calibrated":False,"training_allowed":False}
            fhash=hashlib.sha256(canonical(item)).hexdigest()
            scored.append((row,item,fhash))
        if strict_initial_count and (len(scored)!=12 or
            {country:sum(s[1]["league"]==country for s in scored)
             for country in ("ESP","ITA","GER")}!={"ESP":4,"ITA":4,"GER":4}):
            raise ForecastFreezeError("INITIAL_TWELVE_STRICT_SHADOW_ELIGIBILITY_BLOCKED")
        if not scored:return {"schema":VERSION,"state":"NO_NEW_ELIGIBLE_PREMATCH_TARGETS",
                   "fresh_forecasts":0,"not_eligible":not_eligible,
                   "total_frozen":db.execute("SELECT COUNT(*) FROM m0_shadow_1x2_forecasts").fetchone()[0]}
        db.execute("BEGIN IMMEDIATE")
        try:
            for row,item,h in scored:
                p=item["p_1x2"];e=item["expected_goals"]
                db.execute("""INSERT INTO m0_shadow_1x2_forecasts
                  (forecast_id,feature_snapshot_id,fixture_id,model_version_id,
                   league_country,provider_match_id,kickoff_utc,feature_cutoff_utc,
                   generated_at_utc,p_1,p_x,p_2,expected_home_goals,
                   expected_away_goals,feature_sha256,parameter_sha256,
                   prediction_payload_sha256,source_chain_sha256)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (h,row[0],row[1],MODEL,item["league"],item["match_id"],
                   item["kickoff_utc"],item["feature_cutoff_utc"],item["generated_at_utc"],
                   p["1"],p["X"],p["2"],e["home"],e["away"],
                   item["feature_sha256"],params_sha,h,row[18]))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ForecastFreezeError("INTEGRITY_FAULT_AFTER_SHADOW_FREEZE")
        if db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]!=0:
            raise ForecastFreezeError("ORIGINAL_PREMIER_LEAGUE_TEST_MODEL_TOUCHED")
        total=db.execute("SELECT COUNT(*) FROM m0_shadow_1x2_forecasts").fetchone()[0]
    reports=[item|{"forecast_sha256":h} for _,item,h in scored]
    report={"schema":VERSION,"mode":"M0_SHADOW_PROVISIONAL_UNFITTED",
       "actual_generated_utc":utc_string(now),
       "actual_derived_forecasts":len(reports),"total_immutable_forecasts":total,
       "source":"REAL_PITCHAPI_OBSERVED_BEFORE_TARGET_FROM_SQLITE",
       "calibration_status":"NOT_STARTED",
       "historic_provider_original_PIT_verified":False,
       "original_2026_27_Premier_League_TEST_touched":False,
       "original_M1_training_or_calibration":False,
       "eligible_for_betting_claims":False,
       "individual_forecasts":sorted(reports,
         key=lambda x:(x["kickoff_utc"],x["league"],x["match_id"]))}
    report["report_sha256"]=hashlib.sha256(canonical(report)).hexdigest()
    if report_path is not None:
        dest=Path(report_path)
        if dest.exists():raise ForecastFreezeError("APPEND_ONLY_FORECAST_REPORT_EXISTS")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("x",encoding="utf8") as f:
            json.dump(report,f,ensure_ascii=False,sort_keys=True,indent=2)
            f.write("\n")
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",default="data/forward_m0/kb3_forward_m0.sqlite")
    parser.add_argument("--out-root",default="data/forecasts/m0_shadow_1x2")
    parser.add_argument("--strict-initial",action="store_true")
    a=parser.parse_args()
    now=datetime.now(timezone.utc)
    out=Path(a.out_root)/now.date().isoformat()/"FROZEN_M0_SHADOW_1X2.json"
    if out.exists():
        print("M0_SHADOW_FORECAST_ALREADY_FROZEN_ON_THIS_DAY",out.as_posix())
        return
    result=freeze(a.db,report_path=out,now=now,
                  strict_initial_count=a.strict_initial)
    if result["fresh_forecasts"] if "fresh_forecasts" in result else False:
        print("M0_SHADOW_NO_NEW_ELIGIBLE",result)
    else:
        print(json.dumps({"status":"M0_GENUINE_1X2_PREMATCH_SHADOW_FROZEN",
            "created":result["actual_derived_forecasts"],
            "total":result["total_immutable_forecasts"],
            "report_sha256":result["report_sha256"],
            "sample_prognosis":result["individual_forecasts"][:2],
            "original_M1_gate14_pass":False},sort_keys=True))
if __name__=="__main__":main()
