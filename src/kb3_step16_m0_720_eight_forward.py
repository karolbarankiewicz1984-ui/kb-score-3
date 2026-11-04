"""Separate real forward 8-league M0-720-TRAIN research collector and immutable scorer.

Never touch the original three-league SQLite or protected Premier League TEST.
One research forecast per native fixture; results can only arrive after kickoff.
Historical original first-published PIT and external GitHub publication proof are
NOT assumed. No odds, production promotion, calibrator fit, or API purchase.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,json,os,shutil,sqlite3
from scripts.pitchapi_step06_audit import to_plain
from src.kb3_features import _compose_features,EloParameters
from src.kb3_pit_ledger import as_utc,canonical,utc_now
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_step13_baseline import BaselineParameters,forecast
from src.kb3_step14_m1_math_calibration import score_one,score_predictions
from scripts.step14_three_league_pitchapi_actual_audit import CURRENT,PREVIOUS,LEAGUES
from scripts.step16_additional_leagues_audit import CANDIDATES,norm

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"data/forward_m0_720_eight/kb3_forward_eight.sqlite"
FORECASTS=ROOT/"data/forecasts/m0_720_eight"
SOURCES=ROOT/"data/pit_sidecar/m0_720_eight"
MODEL="M0_ELO_POISSON_RESEARCH_720TRAIN_V1"
MANIFEST=ROOT/"models/research/M0_720_TRAIN_STABLE_CANDIDATE_20261029.json"
PARAMETERS=asdict(BaselineParameters())
EIGHT=(("ESP","LaLiga",LEAGUES[0][1]),("ITA","Serie A",LEAGUES[1][1]),
       ("GER","Bundesliga",LEAGUES[2][1]))+tuple(
       (country,title,aliases) for country,title,aliases in CANDIDATES
       if country in ("FRA","NED","BEL","TUR","POL"))
EIGHT_COUNTRIES=frozenset(x[0] for x in EIGHT)
LEAD=timedelta(minutes=90)
HORIZON=timedelta(hours=96)
FORECAST_LIMIT=10
CALL_CAP_CAPTURE=17  # one catalogue + 2 seasons per each of eight
CALL_CAP_SETTLE=9    # one catalogue + current season per each of eight

class Research720Error(ValueError): pass

def stamp(t):
    d=t if isinstance(t,datetime) else as_utc(t)
    require(d.tzinfo is not None and d.utcoffset()==timedelta(0),"UTC_CLOCK_REQUIRED")
    return d.isoformat(timespec="microseconds").replace("+00:00","Z")
def hashobj(x):
    return hashlib.sha256(canonical(x)).hexdigest()
def require(condition,reason):
    if not condition:raise Research720Error(reason)

def trained_params(root=ROOT):
    m=json.loads((Path(root)/"models/research/M0_720_TRAIN_STABLE_CANDIDATE_20261029.json").read_text())
    require(m.get("candidate_id")==MODEL and m.get("trained_on_real_historical_matches")==720
            and m.get("validation_matches")==374
            and m.get("production_approved") is False
            and m.get("season_2026_27_original_premier_league_test_opened") is False
            and m.get("candidate_parameters_active_in_daily_pipeline") is False,
            "RESEARCH_720_MANIFEST_NOT_FROZEN")
    p=BaselineParameters(**m["fitted_parameters"])
    require(asdict(p)==m["fitted_parameters"] and
        abs(p.base_home_goals-1.6447363878515198)<1e-13 and
        abs(p.base_away_goals-1.4381853609496382)<1e-13 and
        p.elo_goal_elasticity==0.6,"720_TRAIN_PARAMS_CHANGED")
    require(m["historical_input_class"].startswith("B_RECONSTRUCTED_"),
            "FALSE_PIT_PROOF")
    return p,hashobj(asdict(p)),hashobj(m)

def select_eight(catalog):
    require(isinstance(catalog,dict) and isinstance(catalog.get("leagues"),list),
            "SOURCE_CATALOG_INVALID")
    chosen=[]
    for country,title,aliases in EIGHT:
        found=[x for x in catalog["leagues"] if isinstance(x,dict)
               and x.get("country_code","").upper()==country
               and norm(x.get("name","")) in aliases
               and CURRENT in (x.get("seasons") or [])
               and PREVIOUS in (x.get("seasons") or [])]
        require(len(found)==1 and isinstance(found[0].get("id"),str)
                and found[0]["id"].startswith("l_"),"CANDIDATE_LEAGUE_UNAVAILABLE_"+country)
        require(found[0].get("is_free") is True,
                "PROVIDER_FREE_ENTITLEMENT_NOT_CONFIRMED_"+country)
        chosen.append((country,title,found[0]["id"]))
    require(len({x[2] for x in chosen})==8
            and all(x[0]!="ENG" for x in chosen),"PROTECTED_LEAGUE_OR_ALIAS")
    return chosen

def validate_season(games,*,current):
    require(isinstance(games,list) and len(games)>=250,
            "SEASON_INCOMPLETE_OR_NOT_RETURNED")
    ids=set();teams=set();past=0;future=0
    for m in games:
        require(isinstance(m,dict) and isinstance(m.get("id"),str)
                and m["id"].startswith("m_") and m["id"] not in ids,
                "BAD_OR_DUPLICATE_PROVIDER_MATCH")
        ids.add(m["id"])
        try:
            t=as_utc(m["time_utc"]);home=m["home_team"]["id"];away=m["away_team"]["id"]
        except (KeyError,TypeError,ValueError):
            raise Research720Error("BAD_NATIVE_FIXTURE_IDENTITIES") from None
        require(isinstance(home,str) and isinstance(away,str) and home!=away,
                "BAD_TEAM_IDENTITIES")
        teams.update((home,away))
        if m["status"]=="finished":
            require(all(type(m.get(k)) is int and 0<=m[k]<=30
                        for k in ("score_home","score_away")),
                    "BAD_NATIVE_FINAL_90_MIN_RESULT")
            past+=1
        elif current and m["status"] in ("scheduled","not_started","upcoming"):
            require(m.get("score_home") is None and m.get("score_away") is None,
                    "FUTURE_TARGET_CONTAINS_RESULT")
            future+=1
        elif not current:
            # Provider sometimes includes past-season postponed/playoff entries.
            require(m["status"] in ("cancelled","postponed","abandoned","awarded"),
                    "PREVIOUS_SEASON_STATE_UNKNOWN")
    require(len(teams)>=16 and past>=30 and (not current or future>=1),
            "SEASON_NOT_READY")
    return {"all":len(games),"finished":past,"not_started":future,
            "teams":len(teams),"id_sha256":hashobj(sorted(ids))}

def historical_phase_id_inventory(receipts):
    """Exact provider IDs for NED/BEL preliminary phase adjudication.

    Stage labels are source-observed only; unknown labels remain NULL, never
    inferred from chronological order or duplicate matchups. No new API.
    """
    out={}
    for country in ("NED","BEL"):
        key="pitchapi:m0720:fixtures:"+country+":"+PREVIOUS
        selected=[r for r in receipts if r.get("resource")==key]
        require(len(selected)==1,"HISTORIC_PHASE_FIXTURES_NOT_UNIQUE_"+country)
        games=selected[0]["payload"]["matches"]
        require(len({m["id"] for m in games})==len(games),"HISTORIC_PHASE_DUPLICATE_ID")
        items=[]
        for m in games:
            labels={f:m.get(f) if isinstance(m.get(f),(str,int)) else None
                    for f in ("round","stage","phase","competition_phase")}
            items.append({"fixture_id":m["id"],"kickoff_utc":m["time_utc"],
                          "home_team_id":m["home_team"]["id"],
                          "away_team_id":m["away_team"]["id"],
                          "provider_stage_hints":labels,
                          "formal_phase_reviewed":False})
        out[country]={"native_fixture_rows":len(items),
             "phase_labels_are_only_source_hints":True,
             "any_phase_pass_or_training_approval":False,
             "fixture_rows":items}
    return out

def make_forecasts(receipts,*,cutoff,params,param_sha,manifest_sha,challenger_engine=None,challenger_sink=None,
                   known_fixtures=(),diagnostics=None,wall_clock=None,
                   shadow_engine=None,shadow_sink=None):
    require((challenger_engine is None)==(challenger_sink is None),"CHALLENGER_SINK_PAIR_REQUIRED")
    require((shadow_engine is None)==(shadow_sink is None),"SHADOW_SINK_PAIR_REQUIRED")
    grouped={}
    for rec in receipts:
        part=rec["resource"].split(":")
        if len(part)==5 and part[:2]==["pitchapi","m0720"] and part[2]=="fixtures":
            country,season=part[3],part[4]
            require(country in EIGHT_COUNTRIES and season in (PREVIOUS,CURRENT)
                    and (country,season) not in grouped,"UNEXPECTED_SOURCE_SCOPE")
            require(as_utc(rec["completed_at_utc"])<=cutoff
                    and rec.get("origin")=="NETWORK_OBSERVED","SOURCE_AFTER_CUTOFF")
            grouped[(country,season)]=rec
    require(len(grouped)==16,"ALL_EIGHT_LEAGUE_SOURCES_REQUIRED")
    rows=[];by_league=Counter();verified={};known_fixtures=set(known_fixtures)
    reasons=defaultdict(Counter);decisions=[]
    shadow_unavailable=[]
    def decision(country,m,reason):
        reasons[country][reason]+=1
        if m.get('status') in ('scheduled','not_started','upcoming'):
            decisions.append({'league':country,'native_match_id':m['id'],
                'kickoff_utc':m['time_utc'],'reason':reason})
    for country,title,_ in EIGHT:
        src_old=grouped[(country,PREVIOUS)]
        src_now=grouped[(country,CURRENT)]
        old=src_old["payload"].get("matches");current=src_now["payload"].get("matches")
        verified[(country,PREVIOUS)]=validate_season(old,current=False)
        verified[(country,CURRENT)]=validate_season(current,current=True)
        require(not ({m["id"] for m in old}&{m["id"] for m in current}),
                "CROSS_SEASON_DUPLICATE_GAME_ID")
        future=[]
        for m in current:
            if m['status'] not in ('scheduled','not_started','upcoming'):
                decision(country,m,'STATUS_NOT_UPCOMING')
            elif as_utc(m['time_utc'])<=cutoff+LEAD:decision(country,m,'INSIDE_90MIN_OR_PAST')
            elif as_utc(m['time_utc'])>cutoff+HORIZON:decision(country,m,'OUTSIDE_96H')
            elif (country,m['id']) in known_fixtures:decision(country,m,'ALREADY_FROZEN')
            else:future.append(m)
        future.sort(key=lambda m:(m['time_utc'],m['id']))
        # Apply quota AFTER minimum historical completeness, so unavailable teams
        # do not starve subsequent valid upcoming fixtures in the 96h window.
        history=[]
        for season,seq,source in ((PREVIOUS,old,src_old),(CURRENT,current,src_now)):
            for m in seq:
                ko=as_utc(m["time_utc"])
                if m["status"]!="finished" or ko+timedelta(hours=3)>as_utc(source["completed_at_utc"]):
                    continue
                history.append({"fixture_id":m["id"],
                  "season_start_year":int(season[:4]),
                  "home_team_id":m["home_team"]["id"],"away_team_id":m["away_team"]["id"],
                  "kickoff_utc":m["time_utc"],"date":ko,
                  "status":"FINISHED","goals_home_90":m["score_home"],
                  "goals_away_90":m["score_away"],
                  "snapshot_id":source["chain_sha256"],"result_provider_name":"PitchAPI",
                  "result_record_updated_at_utc":None,
                  "captured_at_utc":source["completed_at_utc"],"published_at_utc":None,
                  "xgh":None,"xga":None,"xgh_source":None,"xga_source":None})
        source_latest=max(as_utc(src_old["completed_at_utc"]),as_utc(src_now["completed_at_utc"]))
        for m in future:
            if wall_clock is not None and wall_clock()>=as_utc(m['time_utc'])-LEAD:
                decision(country,m,'TOO_LATE_DURING_BUILD');continue
            target={"fixture_id":m["id"],"home_team_id":m["home_team"]["id"],
                    "away_team_id":m["away_team"]["id"],"season_start_year":2026}
            features=_compose_features(target,list(history),cutoff=cutoff,
                kickoff=as_utc(m["time_utc"]),target_id=m["id"],
                mode="observed",params=EloParameters(),
                excluded=defaultdict(int),source_evidence={
                "provider":"PitchAPI","source_observed_at_utc":stamp(source_latest),
                "country":country,"current_receipt_chain_sha256":src_now["chain_sha256"],
                "previous_receipt_chain_sha256":src_old["chain_sha256"],
                "original_provider_first_published_at_known":False})
            v=features["features"]
            require(len(v)==121 and len(features["missing_flags"])==38
                    and len(features["feature_availability"])==159
                    and features["training_allowed"] is False
                    and features["availability_class"]=="OBSERVED_AT_NOT_CERTIFIED",
                    "UNSAFE_FEATURE_INPUT_OR_UNPROVEN_PIT")
            if v["home_all_5_n"]<5 or v["away_all_5_n"]<5:
                reason=('BOTH_HISTORY5_SHORT' if v['home_all_5_n']<5 and v['away_all_5_n']<5
                        else 'HOME_HISTORY5_SHORT' if v['home_all_5_n']<5 else 'AWAY_HISTORY5_SHORT')
                decision(country,m,reason)
                continue
            if by_league[country]>=FORECAST_LIMIT:
                decision(country,m,'NEW_ELIGIBLE_OVER_QUOTA');continue
            if wall_clock is not None and wall_clock()>=as_utc(m['time_utc'])-LEAD:
                decision(country,m,'TOO_LATE_DURING_BUILD');continue
            fx=forecast(v["home_elo"],v["away_elo"],params)
            item={"model_version":MODEL,"params_sha256":param_sha,
                  "manifest_sha256":manifest_sha,
                  "league_country":country,"league_name":title,
                  "provider_match_id":m["id"],"home_team_id":m["home_team"]["id"],
                  "away_team_id":m["away_team"]["id"],
                  "kickoff_utc":m["time_utc"],"feature_cutoff_utc":stamp(cutoff),
                  "generated_at_utc":stamp(cutoff),
                  "feature_sha256":features["sha256"],
                  "source_chain_sha256":src_now["chain_sha256"],
                  "elo_home":v["home_elo"],"elo_away":v["away_elo"],
                  "p_1x2":fx["p_1x2"],
                  "p_over":fx["p_over"],"p_btts_yes":fx["p_btts_yes"],
                  "expected_goals":fx["expected_goals"],
                  "phase":"EARLY","status":"RESEARCH_TRAIN720_UNCALIBRATED",
                  "original_provider_first_published_at_proven":False,
                  "independent_repo_first_published_utc_proven":False,
                  "training_allowed":False,"production_approved":False}
            item["forecast_sha256"]=hashobj(item)
            require(abs(sum(item["p_1x2"].values())-1)<1e-10,
                    "INVALID_FORECAST_PROBABILITY")
            if challenger_engine is not None:
                challenger_sink.extend(challenger_engine.records(features,item))
            if shadow_engine is not None:
                # An optional challenger must never suppress a valid M0
                # forecast simply because its six-feature vector is absent.
                # Source integrity, bad model SHA, clocks and unexpected errors
                # remain strict NO-GO and are NOT caught here.
                from src.kb3_p1_prospective_shadow_six_v1 import ShadowSafetyError
                try:
                    shadow_sink.extend(shadow_engine.records(features,item))
                except ShadowSafetyError as exc:
                    error=str(exc)
                    if (error=="MISSING_LAST5_HISTORY" or
                            error.startswith("SIX_FORWARD_REAL_GOAL_FORM_FEATURE_UNAVAILABLE:")):
                        shadow_unavailable.append({
                            "league":country,"native_match_id":m["id"],
                            "source_m0_forecast_sha256":item["forecast_sha256"],
                            "reason":error})
                    else:
                        raise
            rows.append(item);by_league[country]+=1
            decision(country,m,'NEW_FORECAST_SELECTED')
    require(len(rows)<=80 and len({(f["league_country"],f["provider_match_id"])
            for f in rows})==len(rows),"DUPLICATE_TARGET_OR_OVER_CAP")
    if diagnostics is not None:
        diagnostics.update({'reason_counts':{s:dict(c) for s,c in sorted(reasons.items())},
            'upcoming_decisions':decisions,
            **({'optional_shadow_unavailable':shadow_unavailable} if shadow_engine is not None else {}),
            'known_fixtures_excluded_before_quota':True,
            'max_new_forecasts_per_league':FORECAST_LIMIT,'source_cutoff_utc':stamp(cutoff)})
    return rows,dict(by_league),{f"{a}/{b}":v for (a,b),v in verified.items()}

def known_forecast_fixtures(path):
    if not Path(path).exists():return set()
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as db:
        return set(db.execute('SELECT league,native_match_id FROM forecasts'))

SCHEMA="""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS model_meta (
 model TEXT PRIMARY KEY,
 parameters_sha256 TEXT NOT NULL,
 manifest_sha256 TEXT NOT NULL,
 start_utc TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status='RESEARCH_ONLY_NOT_APPROVED')
);
CREATE TABLE IF NOT EXISTS forecasts (
 id TEXT PRIMARY KEY,
 model TEXT NOT NULL REFERENCES model_meta(model),
 league TEXT NOT NULL CHECK(league IN ('ESP','ITA','GER','FRA','NED','BEL','TUR','POL')),
 native_match_id TEXT NOT NULL,
 home_team_id TEXT NOT NULL,away_team_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL, captured_at_utc TEXT NOT NULL,
 params_sha256 TEXT NOT NULL,source_chain_sha256 TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 UNIQUE(league,native_match_id),
 CHECK(julianday(captured_at_utc)<julianday(kickoff_utc)-90.0/1440.0)
);
CREATE TABLE IF NOT EXISTS settlements (
 settlement_sha256 TEXT PRIMARY KEY,
 forecast_id TEXT NOT NULL UNIQUE REFERENCES forecasts(id),
 league TEXT NOT NULL,
 native_match_id TEXT NOT NULL,
 score_home INTEGER NOT NULL CHECK(score_home BETWEEN 0 AND 30),
 score_away INTEGER NOT NULL CHECK(score_away BETWEEN 0 AND 30),
 outcome TEXT NOT NULL CHECK(outcome IN ('1','X','2')),
 observed_utc TEXT NOT NULL,settled_utc TEXT NOT NULL,
 provider_source_chain_sha256 TEXT NOT NULL,
 log_loss REAL NOT NULL CHECK(log_loss>=0),
 brier_sum3 REAL NOT NULL CHECK(brier_sum3>=0 AND brier_sum3<=2),
 CHECK(julianday(observed_utc)>=julianday(settled_utc))
);
CREATE TRIGGER IF NOT EXISTS research_forecast_no_update BEFORE UPDATE ON forecasts
 BEGIN SELECT RAISE(ABORT,'RESEARCH_FORECAST_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS research_forecast_no_delete BEFORE DELETE ON forecasts
 BEGIN SELECT RAISE(ABORT,'RESEARCH_FORECAST_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS research_settlement_no_update BEFORE UPDATE ON settlements
 BEGIN SELECT RAISE(ABORT,'RESEARCH_SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS research_settlement_no_delete BEFORE DELETE ON settlements
 BEGIN SELECT RAISE(ABORT,'RESEARCH_SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS research_model_no_update BEFORE UPDATE ON model_meta
 BEGIN SELECT RAISE(ABORT,'RESEARCH_MODEL_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS research_model_no_delete BEFORE DELETE ON model_meta
 BEGIN SELECT RAISE(ABORT,'RESEARCH_MODEL_IMMUTABLE'); END;
"""
def connect_db(db_path=DB):
    Path(db_path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
            "RESEARCH_SQLITE_CORRUPTION")
    return db

def freeze_sqlite(db_path,items,*,param_sha,manifest_sha,now,new_frozen_ids=None):
    with connect_db(db_path) as db:
        meta=db.execute("SELECT model,parameters_sha256,manifest_sha256 FROM model_meta").fetchall()
        if not meta:
            db.execute("INSERT INTO model_meta VALUES(?,?,?,?,'RESEARCH_ONLY_NOT_APPROVED')",
                (MODEL,param_sha,manifest_sha,stamp(now)))
        else:
            require(meta==[(MODEL,param_sha,manifest_sha)],
                "VERSION_OR_PARAMS_CHANGED_MUST_NEW_DATABASE")
        added=0
        for item in items:
            require(item["model_version"]==MODEL and
                    item["params_sha256"]==param_sha and
                    item["manifest_sha256"]==manifest_sha and
                    item["forecast_sha256"]==hashobj({k:v for k,v in item.items()
                        if k!="forecast_sha256"}),"INVALID_FROZEN_CANDIDATE")
            found=db.execute("SELECT id FROM forecasts WHERE league=? AND native_match_id=?",
                             (item["league_country"],item["provider_match_id"])).fetchone()
            if found:continue
            db.execute("""INSERT INTO forecasts(id,model,league,native_match_id,
                 home_team_id,away_team_id,kickoff_utc,captured_at_utc,
                 params_sha256,source_chain_sha256,payload_json)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                 (item["forecast_sha256"],MODEL,item["league_country"],
                  item["provider_match_id"],item["home_team_id"],item["away_team_id"],
                  item["kickoff_utc"],item["generated_at_utc"],param_sha,
                  item["source_chain_sha256"],json.dumps(item,sort_keys=True,allow_nan=False)))
            added+=1
            if new_frozen_ids is not None:
                new_frozen_ids.add(item["forecast_sha256"])
        db.commit()
        require(db.execute("PRAGMA foreign_key_check").fetchall()==[],
                "RESEARCH_FOREIGN_KEY_FAULT")
        total=db.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
    return added,total

def settle_sqlite(db_path,real_results,*,observed_at,source_chain_sha):
    """real_results keyed by (country,match_id), from independently observed 8 leagues."""
    with connect_db(db_path) as db:
        pending=db.execute("""SELECT id,league,native_match_id,home_team_id,
                      away_team_id,kickoff_utc,captured_at_utc,payload_json
                FROM forecasts WHERE id NOT IN
                  (SELECT forecast_id FROM settlements) ORDER BY kickoff_utc,id""").fetchall()
        settled=0;unready=0;reasons=Counter();decisions=[]
        for fid,league,mid,h,a,kick,captured,payload in pending:
            item=json.loads(payload)
            require(item["forecast_sha256"]==hashobj({k:v for k,v in item.items()
                        if k!="forecast_sha256"}) and item["forecast_sha256"]==fid,
                    "ORIGINAL_FORECAST_PAYLOAD_TAMPERED")
            require(item["model_version"]==MODEL and
                    item["params_sha256"]==db.execute("SELECT parameters_sha256 FROM model_meta").fetchone()[0]
                    and as_utc(captured)<as_utc(kick)-LEAD,
                    "ORIGINAL_FROZEN_VERSION_OR_TIME_DRIFT")
            m=real_results.get((league,mid))
            reason=None
            if as_utc(kick)+timedelta(hours=3)>observed_at:reason='RESULT_MATURITY_3H_NOT_REACHED'
            elif m is None:reason='PROVIDER_RESULT_MISSING'
            elif m.get('id')!=mid:reason='RESULT_NATIVE_MATCH_ID_MISMATCH'
            else:
                try:source_kick=as_utc(m.get('time_utc'))
                except (TypeError,ValueError):reason='RESULT_KICKOFF_INVALID'
                else:
                    if source_kick!=as_utc(kick):reason='KICKOFF_CHANGED_REVIEW_REQUIRED'
            if reason is None:
                if m.get('home_team',{}).get('id')!=h or m.get('away_team',{}).get('id')!=a:reason='RESULT_TEAM_SIDE_MISMATCH'
                elif m.get('status')!='finished':reason='RESULT_NOT_FINISHED'
                elif any(type(m.get(x)) is not int or not 0<=m[x]<=30 for x in ('score_home','score_away')):reason='RESULT_SCORE_INVALID'
            if reason:
                unready+=1;reasons[reason]+=1
                decisions.append({'forecast_id':fid,'league':league,'native_match_id':mid,'reason':reason})
                continue
            gh,ga=m["score_home"],m["score_away"]
            label="1" if gh>ga else "2" if gh<ga else "X"
            ll,bs=score_one(item["p_1x2"],label)
            rec={"forecast_id":fid,"league":league,"native_match_id":mid,
                 "score_home":gh,"score_away":ga,"outcome":label,
                 "observed_utc":stamp(observed_at),"source_chain_sha256":source_chain_sha,
                 "log_loss":ll,"brier_sum3":bs}
            hrec=hashobj(rec)
            db.execute("""INSERT INTO settlements
              (settlement_sha256,forecast_id,league,native_match_id,
               score_home,score_away,outcome,observed_utc,settled_utc,
               provider_source_chain_sha256,log_loss,brier_sum3)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
              (hrec,fid,league,mid,gh,ga,label,stamp(observed_at),
               stamp(observed_at),source_chain_sha,ll,bs))
            settled+=1
            reasons['SETTLED_NEW']+=1
            decisions.append({'forecast_id':fid,'league':league,'native_match_id':mid,'reason':'SETTLED_NEW'})
        db.commit()
        total=db.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
        all_scores=db.execute("""SELECT f.payload_json,s.outcome FROM settlements s
                        JOIN forecasts f ON f.id=s.forecast_id ORDER BY f.kickoff_utc,f.id""").fetchall()
        metrics=(score_predictions([json.loads(x)["p_1x2"] for x,y in all_scores],
                [y for x,y in all_scores]) if all_scores else None)
    return {"new_settlements":settled,"total_settlements":total,
            "not_yet_settled":unready,"metrics":metrics,
            'settlement_reason_counts':dict(reasons),'settlement_decisions':decisions,
            "100_fit_threshold_reached":total>=100,
            "50_future_after_fit_verified":False,
            "calibration_fitted":False,"production_approved":False}

def collect_receipts(client,*,mode,now):
    require(mode in ("forecast","settle"),"INVALID_RESEARCH_RUN_MODE")
    calls=0;receipts=[]
    def call(resource,method,*args,**kwargs):
        nonlocal calls
        require(calls<(CALL_CAP_CAPTURE if mode=="forecast" else CALL_CAP_SETTLE),
                "PROVIDER_REQUEST_BUDGET_EXCEEDED")
        calls+=1;start=utc_now()
        try:data=to_plain(method(*args,**kwargs))
        except Exception as exc:
            failure=Research720Error('PROVIDER_CAPTURE_FAILED')
            failure.capture_detail={'resource':resource,'network_calls':calls,'error_type':type(exc).__name__}
            failure.partial_receipts=receipts
            raise failure from None
        end=utc_now()
        if not isinstance(data,dict):
            failure=Research720Error('PROVIDER_INVALID_RESPONSE')
            failure.capture_detail={'resource':resource,'network_calls':calls,'error_type':'NON_OBJECT_RESPONSE'}
            failure.partial_receipts=receipts
            raise failure
        add_observation(receipts,resource=resource,payload=data,
                        started=start,completed=end)
        return data
    catalog=call("pitchapi:m0720:catalog",client.leagues.list)
    chosen=select_eight(catalog)
    for c,title,lid in chosen:
        seasons=(PREVIOUS,CURRENT) if mode=="forecast" else (CURRENT,)
        for season in seasons:
            call("pitchapi:m0720:fixtures:"+c+":"+season,
                 client.leagues.matches,lid,season=season,
                 **({"status":"all"} if season==CURRENT else {}))
    require(calls==(CALL_CAP_CAPTURE if mode=="forecast" else CALL_CAP_SETTLE),
            "ACTUAL_PROVIDER_CALL_COUNT_MISMATCH")
    return receipts,chosen,calls

def run(*,mode,client,now=None,db_path=DB,root=SOURCES,public_key=None,
        forecast_root=FORECASTS,clock=None):
    now=now or datetime.now(timezone.utc)
    require(isinstance(now,datetime) and now.utcoffset()==timedelta(0),"SERVER_UTC_REQUIRED")
    require(mode in ('forecast','settle'),'INVALID_RESEARCH_RUN_MODE')
    require(getattr(client,'_max_retries',0)==0,'SDK_RETRIES_MUST_BE_ZERO_FOR_REQUEST_CAP')
    clock=clock or (lambda:datetime.now(timezone.utc))
    if mode=='forecast':
        from src.kb3_step16_run_policy import forecast_due
        due,reason=forecast_due(root,forecast_root,now)
        require(due,'FORECAST_NOT_DUE:'+reason)
    p,param_sha,manifest_sha=trained_params()
    # Preflight the actual pinned research model BEFORE any new provider API.
    # OFF by default; this is not production promotion or historical PIT.
    shadow_engine=None
    if mode=="forecast":
        from src.kb3_p1_shadow_live_gate import load_opted_shadow
        shadow_engine=load_opted_shadow(clock=clock)
    day=now.date().isoformat()
    run_name=mode+'-'+now.strftime('%H%M%S%f')
    folder=Path(root)/day/run_name
    require(not folder.exists(),"IMMUTABLE_SOURCE_RUN_ALREADY_EXISTS")
    folder.mkdir(parents=True,exist_ok=False)
    attempt={'model_version':MODEL,'mode':mode,'run_utc':stamp(now),
             'status':'ATTEMPT_STARTED_NOT_A_FORECAST','provider_call_cap':CALL_CAP_CAPTURE if mode=='forecast' else CALL_CAP_SETTLE}
    attempt['attempt_sha256']=hashobj(attempt)
    with (folder/'ATTEMPT.json').open('x') as f:json.dump(attempt,f,sort_keys=True)
    dbp=Path(db_path);staging=folder/"STAGED_M0720.sqlite"
    reportdir=None;mirror_created=False;receipts=[]
    try:
        receipts,chosen,calls=collect_receipts(client,mode=mode,now=now)
        cutoff=clock()
        require(cutoff>=now,'SERVER_CLOCK_MOVED_BACKWARDS')
        rawmeta=seal(receipts,public_key or ROOT/"config/step11_archive_recipient_public.pem",
            folder/"SOURCE.enc",folder/"SOURCE.manifest.json")
        if dbp.exists():shutil.copy2(dbp,staging)
        if mode=="forecast":
            from src.kb3_step17_forward_challengers import (
                Challengers,freeze_new_challengers)
            candidate_engine=Challengers()
            candidates=[]
            shadow_candidates=[] if shadow_engine is not None else None
            diagnostics={}
            forecasts,coverage,season_shapes=make_forecasts(receipts,cutoff=cutoff,
                params=p,param_sha=param_sha,manifest_sha=manifest_sha,
                challenger_engine=candidate_engine,challenger_sink=candidates,
                shadow_engine=shadow_engine,shadow_sink=shadow_candidates,
                known_fixtures=known_forecast_fixtures(staging),diagnostics=diagnostics,
                wall_clock=clock)
            freeze_at=clock()
            late=[f for f in forecasts if freeze_at>=as_utc(f['kickoff_utc'])-LEAD]
            forecasts=[f for f in forecasts if freeze_at<as_utc(f['kickoff_utc'])-LEAD]
            diagnostics['too_late_before_sqlite_publish']=[{'league':f['league_country'],'native_match_id':f['provider_match_id']} for f in late]
            coverage=dict(Counter(f['league_country'] for f in forecasts))
            new_ids=set()
            new,total=freeze_sqlite(staging,forecasts,param_sha=param_sha,
                                    manifest_sha=manifest_sha,now=cutoff,
                                    new_frozen_ids=new_ids)
            challenger_state=freeze_new_challengers(staging,candidates,new_m0_ids=new_ids)
            require(challenger_state["new_challengers"]==2*new
                    and challenger_state["new_common_fixture_pairs"]==new,
                    "NOT_ALL_NEW_M0_MATCHES_HAVE_TWO_CHALLENGERS")
            if shadow_engine is not None:
                from src.kb3_p1_prospective_shadow_six_v1 import freeze_only_new_m0
                shadow_state=freeze_only_new_m0(
                    staging,shadow_candidates,new_m0_ids=new_ids)
                shadow_missing_new=[
                    row for row in diagnostics.get("optional_shadow_unavailable",[])
                    if row["source_m0_forecast_sha256"] in new_ids]
                require(
                    shadow_state["added"]+len(shadow_missing_new)==new and
                    shadow_state["official_fit_increment"]==0,
                    "SHADOW_NEW_M0_COVERAGE_ACCOUNTING_OR_INTEGRITY_DRIFT")
                shadow_state["missing_features_new_m0"]=len(shadow_missing_new)
                shadow_state["enabled"]=True
            extra={"new_forecasts":new,"total_forecasts":total,"coverage":coverage,
                   'forecast_selection_diagnostics':diagnostics,
                   "season_shapes":season_shapes,
                   "ned_bel_historical_phase_native_id_review":historical_phase_id_inventory(receipts),
                   "step17_challenger_research":challenger_state,
                   "step17_challengers_are_independent_unfitted_research":True,
                   "step17_challenger_host_artifact_proof_pending":True,
                   "step17_gate":"PENDING_STEP16_AND_FULL_FAIR_BENCHMARK"}
            if shadow_engine is not None:
                extra["catboost_shadow_six_research"]=shadow_state
                extra["shadow_research_not_production"]=True
            reportdir=Path(forecast_root)/day/run_name
            require(not reportdir.exists(),'IMMUTABLE_FORECAST_RUN_ALREADY_ARCHIVED')
        else:
            results={}
            for entry in receipts:
                x=entry["resource"].split(":")
                if len(x)==5 and x[2]=="fixtures" and x[4]==CURRENT:
                    for m in entry["payload"]["matches"]:
                        require((x[3],m['id']) not in results,'DUPLICATE_RESULT_NATIVE_MATCH_ID')
                        results[(x[3],m["id"])]=m
            extra=settle_sqlite(staging,results,observed_at=cutoff,
                                source_chain_sha=rawmeta["proof"]["final_chain_sha256"])
            # Host-side PushEvent creation time + immutable bytes at its historical
            # commit, NOT a user-controlled commit timestamp or self-declared clock.
            # Missing repo event => no proof, no calibration; settlement still
            # persists independently and can be audited on a later run.
            from src.kb3_step16_m0_720_calibration import (
                github_events,inspect_event_proofs,append_proofs,calibrate_if_eligible,
                github_actions_artifact_proofs)
            token=os.environ.get("GH_TOKEN","")
            events,provider_state=github_events(token)
            proposed,proof_audit=inspect_event_proofs(
                staging,events,now=cutoff,repo_root=ROOT)
            push_verified=append_proofs(staging,proposed,now=cutoff)
            # GitHub bot pushes often do NOT surface through /events.
            # Use GitHub-owned immutable Actions artifact created_at combined
            # with the actual original ZIP-ed SQLite bytes as second proof.
            artifact_proofs,artifact_audit=github_actions_artifact_proofs(
                staging,token=token,now=cutoff)
            verified_count=append_proofs(staging,artifact_proofs,now=cutoff)
            ready=calibrate_if_eligible(staging,now=cutoff)
            from src.kb3_step17_challenger_provenance import (
                audit_challengers,paired_settled_report)
            challenger_audit=audit_challengers(staging,token=token,now=cutoff)
            paired_results=paired_settled_report(staging)
            from src.kb3_p1_shadow_host_provenance import (
                audit_shadow,paired_settled_shadow)
            shadow_host_audit=audit_shadow(staging,token=token,now=cutoff)
            shadow_pairs=paired_settled_shadow(staging)
            extra.update({
                "publication_proof_audit":{
                   "push_event_provider_state":provider_state,
                   "audited_push_event_count":proof_audit["events_considered"],
                   "push_source_revisions_verified":proof_audit["historic_versions_verified"],
                   "push_verified_rows_added":len(proposed),
                   "actions_artifact_audit":artifact_audit,
                   "actions_artifact_verified_rows_added":len(artifact_proofs),
                   "verified_forecast_rows_total":verified_count,
                   "github_commit_author_date_used_as_proof":False,
                   "missing_host_evidence_never_assumed_pre_match":True},
                "calibration_readiness":ready,
                "step17_challenger_proof_audit":challenger_audit,
                "step17_paired_same_fixture_readiness":paired_results})
            if shadow_host_audit.get("state")!="SHADOW_DISABLED_OR_NO_NEW_ROWS":
                extra["catboost_shadow_six_host_audit"]=shadow_host_audit
                extra["catboost_shadow_six_paired_results"]=shadow_pairs
        report={"schema":"kb3-step16-8league-M0-720-TRAIN-forward-v1",
            "mode":mode,"model_version":MODEL,"params_sha256":param_sha,
            "manifest_sha256":manifest_sha,"run_utc":stamp(cutoff),
            "network_calls":calls,"league_count":len(chosen),
            "countries":[x[0] for x in chosen],"source_cipher_sha256":rawmeta["ciphertext_sha256"],
            "source_chain_sha256":rawmeta["proof"]["final_chain_sha256"],
            "source_first_published_by_provider_proven":False,
            "independent_first_repo_publication_before_kickoff_proven":False,
            "historic_native_PIT_proven":False,
            "production_approved":False,"original_2026_27_Premier_League_TEST_accessed":False,
            "existing_three_league_shadow_database_modified":False,
            "calibrator_auto_fitted":bool(extra.get('calibration_readiness',{}).get('calibrator_first_fit_just_written')),
            'attempt_started_utc':stamp(now),'gate16':'PENDING',**extra}
        report["report_sha256"]=hashobj(report)
        with (folder/"RECEIPT.json").open("x",encoding="utf8") as f:
            json.dump(report,f,indent=2,sort_keys=True,ensure_ascii=False);f.write("\n")
        if mode=="forecast":
            reportdir.mkdir(parents=True,exist_ok=False)
            mirror_created=True
            with (reportdir/"FROZEN_M0_720_EIGHT.json").open("x",encoding="utf8") as f:
                json.dump(report,f,sort_keys=True,indent=2,ensure_ascii=False);f.write("\n")
        # Publish the DB last: evidence and mirror write failures cannot leave
        # forecast rows without their archive. Old daily files are never changed.
        if mode=='forecast':
            require(all(clock()<as_utc(f['kickoff_utc'])-LEAD for f in forecasts),
                    'PUBLICATION_DEADLINE_ELAPSED')
        dbp.parent.mkdir(parents=True,exist_ok=True)
        os.replace(staging,dbp)
        return report
    except BaseException as exc:
        partial=getattr(exc,'partial_receipts',receipts)
        if partial and not (folder/'SOURCE.enc').exists():
            try:seal(partial,public_key or ROOT/'config/step11_archive_recipient_public.pem',folder/'SOURCE.enc',folder/'SOURCE.manifest.json')
            except Exception:pass  # Never write partial raw in plaintext.
        (folder/'RECEIPT.json').unlink(missing_ok=True)
        staging.unlink(missing_ok=True)
        if mirror_created:shutil.rmtree(reportdir,ignore_errors=True)
        failure={'model_version':MODEL,'mode':mode,'run_utc':stamp(now),
                 'status':'FAILED_NO_DATABASE_PUBLICATION','error_type':type(exc).__name__,
                 'source_encrypted':(folder/'SOURCE.enc').exists(),
                 'capture_detail':getattr(exc,'capture_detail',None)}
        try:
            with (folder/'FAILURE.json').open('x') as f:json.dump(failure,f,sort_keys=True)
        except OSError:pass
        raise
