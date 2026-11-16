"""True future-only V3-R CatBoost shadow, research-only and independent of M0.

On its FIRST approved main-branch run, fit once on retrospective TRAIN ONLY,
pin immutable model bytes and feature contract, then score genuine upcoming M0
fixtures using fresh PitchAPI fixture listings + source observations available
at the current capture time. Never backdate to the original M0 freeze. Missing
optional statistics remain NaN; no invented zeros or retro forecasts.

All source payloads are encrypted. GitHub-host timestamp verification is a
separate audit, so a local freeze is never called host-attested by this code.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,json,math,os,re,sqlite3

from scripts.kb3_p1_historical_eligibility_split import (
    SOURCE_DB,RECHECK_DB,hash_json,read_only_conn,utc,
)
from scripts.kb3_p1_retro_catboost_1007_376 import (
    BASE,PARAMS,CLASSES,load_sets,matrix,numeric,
    build_features_without_target_label,
)
from scripts.pitchapi_step06_audit import to_plain
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_pit_ledger import utc_now
from src.kb3_step16_m0_720_eight_forward import (
    ROOT,DB as M0_DB,LEAD,select_eight,validate_season,
    CURRENT,PREVIOUS,hashobj,
)

MODEL_VERSION="KB3_V3R_CATBOOST_NO_XG_14_FORWARD_RESEARCH_V1"
CONTRACT="kb3-v3r-catboost-prospective-shadow-v1"
MODEL_DIR=ROOT/"assets/research/kb3_v3r_forward"
MODEL_FILE=MODEL_DIR/"v3r_no_xg_14.cbm"
MANIFEST=MODEL_DIR/"manifest.json"
OUTPUT=ROOT/"data/v3r_shadow"
PUBLIC_KEY=ROOT/"config/step11_archive_recipient_public.pem"
MAX_CALLS=17
RESULT_LAG=timedelta(hours=3)
MAX_TARGETS=80
MODEL_VERSION_FIXED=True
SAFE_ID=re.compile(r"^m_[A-Za-z0-9_-]{2,100}$")
LEAGUES=frozenset(("ESP","ITA","GER","FRA","NED","BEL","TUR","POL"))


class V3RShadowSafety(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise V3RShadowSafety(reason)


def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def when(value):
    if isinstance(value,datetime):
        need(value.tzinfo is not None and value.utcoffset()==timedelta(0),
             "UTC_DATETIME_REQUIRED")
        return value
    return utc(value)


def stamp(value):
    return when(value).isoformat(timespec="microseconds").replace("+00:00","Z")


def verify_pinned(model_file=MODEL_FILE,manifest_file=MANIFEST):
    from catboost import CatBoostClassifier
    a,b=Path(model_file),Path(manifest_file)
    need(a.is_file() and b.is_file(),"PINNED_V3R_MODEL_OR_MANIFEST_MISSING")
    obj=json.loads(b.read_text(encoding="utf8"))
    need(obj.get("schema")=="kb3-v3r-trained-pinned-14-v1" and
         obj.get("model_version")==MODEL_VERSION and
         obj.get("feature_names")==list(BASE) and
         obj.get("fixed_training_parameters")==PARAMS and
         obj.get("train_only") is True and
         obj.get("trained_on_reconstructed_history") is True and
         obj.get("original_provider_historical_pit_certified") is False and
         obj.get("production_approved") is False and
         obj.get("official_fit_increment")==0 and
         obj.get("validation_never_used_for_training") is True and
         obj.get("original_eng_test_accessed") is False,
         "INVALID_PINNED_V3R_RESEARCH_MANIFEST")
    need(hash_json({k:v for k,v in obj.items() if k!="manifest_sha256"})==
         obj.get("manifest_sha256"),"MANIFEST_SHA_MISMATCH")
    need(sha_file(a)==obj.get("binary_sha256"),"MODEL_BINARY_SHA_MISMATCH")
    model=CatBoostClassifier()
    model.load_model(str(a))
    need(list(model.feature_names_)==list(BASE) and
         set(map(str,model.classes_))==set(CLASSES) and
         len(model.classes_)==3,
         "CATBOOST_BINARY_FEATURES_OR_LABELS_CHANGED")
    return model,obj


def train_or_load(*,source_db=SOURCE_DB,recheck_db=RECHECK_DB,
                  model_file=MODEL_FILE,manifest_file=MANIFEST):
    """One-time train-only CatBoost research model; never refit after pin."""
    a,b=Path(model_file),Path(manifest_file)
    need(a.exists()==b.exists(),"INCOMPLETE_PINNED_V3R_MODEL")
    if a.exists():
        model,manifest=verify_pinned(a,b)
        return model,manifest,False
    need(Path(source_db).is_file(),"RECONSTRUCTED_SOURCE_NOT_FOUND")
    train,valid,meta=load_sets(source_db,recheck_db)
    need(all(row["partition"]=="TRAIN" and row["league"]!="ENG"
             for row in train) and
         all(row["partition"]=="VALIDATION" for row in valid) and
         len(train)>=1000 and len(valid)>=300 and
         meta["formal_training_allowed"] is False,
         "RECONSTRUCTED_RESEARCH_TRAIN_PROVENANCE_FAIL")
    from catboost import CatBoostClassifier
    model=CatBoostClassifier(**PARAMS)
    model.fit(matrix(train,BASE),[r["label"] for r in train],
              feature_names=list(BASE))
    need(list(model.feature_names_)==list(BASE) and
         set(map(str,model.classes_))==set(CLASSES),
         "V3R_MODEL_FITTING_CONTRACT_DRIFT")
    a.parent.mkdir(parents=True,exist_ok=True)
    need(not a.exists() and not b.exists(),"MODEL_CREATED_CONCURRENTLY")
    model.save_model(str(a))
    obj={
        "schema":"kb3-v3r-trained-pinned-14-v1",
        "model_version":MODEL_VERSION,
        "binary_sha256":sha_file(a),
        "feature_names":list(BASE),
        "fixed_training_parameters":PARAMS,
        "source_snapshot_sha256":sha_file(source_db),
        "source_split_train_selector_sha256":meta["train_selector_sha256"],
        "source_research_gate_report_sha256":meta["original_gate_sha256"],
        "training_rows":len(train),
        "validation_rows_not_fitted":len(valid),
        "last_training_fixture_utc":max(r["kickoff_utc"] for r in train),
        "trained_at_utc":stamp(datetime.now(timezone.utc)),
        "train_only":True,
        "validation_never_used_for_training":True,
        "trained_on_reconstructed_history":True,
        "original_provider_historical_pit_certified":False,
        "original_eng_test_accessed":False,
        "official_fit_increment":0,
        "production_approved":False,
    }
    obj["manifest_sha256"]=hash_json(obj)
    with b.open("x",encoding="utf8") as fh:
        json.dump(obj,fh,sort_keys=True,indent=2,ensure_ascii=False)
        fh.write("\n")
    verify_pinned(a,b)
    return model,obj,True


def source_observations(*,source_db=SOURCE_DB,cutoff):
    """Only real observations captured by the source before THIS new run."""
    records={};late=0
    with read_only_conn(source_db) as cn:
        need(cn.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
             "SOURCE_DATABASE_INTEGRITY")
        for (scope,mid,ko,home,away,obsat,items,xgs,xgh,xga) in cn.execute(
                """SELECT scope,match_id,kickoff_utc,home_team_id,
                away_team_id,source_observed_at_utc,stat_items_json,
                xg_status,xg_home,xg_away FROM observations"""):
            if scope not in LEAGUES:
                continue
            key=(scope,mid)
            need(key not in records,"DUPLICATED_SOURCE_OBSERVATION_ID")
            if utc(obsat)>when(cutoff):
                late+=1
                continue
            records[key]={
                "home_team_id":home,"away_team_id":away,
                "kickoff_utc":ko,"items":json.loads(items),
                "xg_status":xgs,"xg_home":xgh,"xg_away":xga,
                "source_observed_at_utc":obsat,
            }
    return records,late


def verified_m0_candidates(*,db_path=M0_DB,now,out_root=OUTPUT):
    """Read-only M0 parent bytes; never mint a shadow for an ended fixture."""
    now=when(now)
    root=Path(out_root)/"forecasts"
    need(Path(db_path).is_file(),"M0_FROZEN_DATABASE_MISSING")
    out=[];skipped=Counter()
    with read_only_conn(db_path) as cn:
        need(cn.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
             "M0_DATABASE_INTEGRITY")
        for (id,league,mid,ko,at,home,away,blob) in cn.execute(
            """SELECT id,league,native_match_id,kickoff_utc,captured_at_utc,
            home_team_id,away_team_id,payload_json FROM forecasts
            ORDER BY kickoff_utc,league,native_match_id"""):
            need(league in LEAGUES,"PROTECTED_PARENT_LEAGUE")
            parent=json.loads(blob)
            need(id==parent.get("forecast_sha256") and
                 id==hashobj({k:v for k,v in parent.items()
                              if k!="forecast_sha256"}) and
                 parent.get("provider_match_id")==mid and
                 parent.get("league_country")==league and
                 parent.get("kickoff_utc")==ko and
                 parent.get("home_team_id")==home and
                 parent.get("away_team_id")==away and
                 utc(at)<utc(ko)-LEAD,
                 "M0_FROZEN_PARENT_HASH_OR_IDENTITY_DRIFT")
            need(SAFE_ID.fullmatch(mid) is not None,
                 "UNSAFE_TARGET_PROVIDER_NATIVE_ID")
            if (root/league/(mid+".json")).exists():
                skipped["already_shadowed"]+=1
                continue
            if utc(ko)<=now+timedelta(hours=3):
                skipped["not_sufficiently_future"]+=1
                continue
            if utc(ko)>now+timedelta(days=8):
                skipped["outside_8day_horizon"]+=1
                continue
            out.append({"id":id,"league":league,"mid":mid,"kickoff_utc":ko,
                "home_team_id":home,"away_team_id":away,"m0_at":at,
                "parent":parent})
    need(len(out)<=MAX_TARGETS,"UNSAFE_V3R_NEW_PARENT_VOLUME")
    return out,dict(skipped)


def current_listings(client,targets,*,now):
    """Fresh full native league fixtures, source-chain-sealed before scoring.

    Unavailable one-league listing is quarantined; valid other leagues can
    continue. The catalog and every successful source are archived encrypted.
    """
    receipts=[];calls=0;fail=Counter()
    def call(resource,fn,*args,**kwargs):
        nonlocal calls
        need(calls<MAX_CALLS,"LIVE_SOURCE_PROVIDER_CALL_CAP")
        calls+=1;started=utc_now()
        try:
            data=to_plain(fn(*args,**kwargs))
            if not isinstance(data,dict):
                raise V3RShadowSafety("SOURCE_NOT_DICTIONARY")
        except Exception as exc:
            fail[type(exc).__name__]+=1
            return None
        ended=utc_now()
        add_observation(receipts,resource=resource,payload=data,
                        started=started,completed=ended)
        return data
    catalog=call("pitchapi:v3r:catalog",client.leagues.list)
    need(catalog is not None,"PITCHAPI_LEAGUE_CATALOG_UNAVAILABLE")
    chosen=select_eight(catalog)
    requested={t["league"] for t in targets}
    histories={};live_targets={};scope_errors={}
    for league,_,lid in chosen:
        if league not in requested:
            continue
        sources=[]
        for season in (PREVIOUS,CURRENT):
            source=call("pitchapi:v3r:fixtures:"+league+":"+season,
                        client.leagues.matches,lid,season=season,
                        **({"status":"all"} if season==CURRENT else {}))
            if source is None:
                scope_errors[league]="PROVIDER_FIXTURE_LISTING_UNAVAILABLE"
                continue
            try:
                validate_season(source.get("matches"),current=(season==CURRENT))
                sources.append((season,source["matches"]))
            except Exception:
                scope_errors[league]="PROVIDER_FIXTURE_LIST_INTEGRITY"
        if len(sources)!=2 or league in scope_errors:
            continue
        history=[];unique=set()
        for season,items in sources:
            if season==CURRENT:
                live_targets[league]={m["id"]:m for m in items}
            for m in items:
                mid=m["id"]
                need(mid not in unique,"PROVIDER_DUPLICATE_BETWEEN_SEASONS")
                unique.add(mid)
                if m.get("status")!="finished":
                    continue
                finished=utc(m["time_utc"])+RESULT_LAG
                if finished>when(now):
                    continue
                history.append({
                    "scope":league,"season":season,"match_id":mid,
                    "kickoff_utc":m["time_utc"],
                    "home_team_id":m["home_team"]["id"],
                    "away_team_id":m["away_team"]["id"],
                    "goals_home_90":m["score_home"],
                    "goals_away_90":m["score_away"],
                })
        history.sort(key=lambda x:(utc(x["kickoff_utc"]),x["match_id"]))
        histories[league]=history
    need(receipts,"NO_REAL_SOURCE_OBSERVATIONS")
    return receipts,histories,live_targets,scope_errors,calls,dict(fail)


def record_for(target,*,history,listing,observations,model,manifest,at,
               source_chain_sha):
    """Score a new future M0 fixture using only completed SOURCE records."""
    now=when(at);ko=utc(target["kickoff_utc"])
    need(now<ko-LEAD,"PREGAME_PUBLICATION_DEADLINE")
    native=listing.get(target["mid"])
    if (not isinstance(native,dict) or
        native.get("time_utc")!=target["kickoff_utc"] or
        (native.get("home_team") or {}).get("id")!=target["home_team_id"] or
        (native.get("away_team") or {}).get("id")!=target["away_team_id"] or
        native.get("status") not in ("scheduled","not_started","upcoming") or
        native.get("score_home") is not None or
        native.get("score_away") is not None):
        return None,"PARENT_PROVIDER_TARGET_IDENTITY_DRIFT"
    selected={}
    drift=0
    for g in history:
        key=(g["scope"],g["match_id"])
        row=observations.get(key)
        if row is None:
            continue
        if (row["home_team_id"]!=g["home_team_id"] or
            row["away_team_id"]!=g["away_team_id"] or
            row["kickoff_utc"]!=g["kickoff_utc"]):
            drift+=1
            continue
        need(utc(row["source_observed_at_utc"])<=now,
             "POST_FORECAST_STATS_SOURCE_LEAK")
        selected[key]=row
    # Freeze the history as of this run (NOT as of future kickoff minus 2h).
    # The shared TRAIN feature builder still enforces the stricter per-target
    # predecessor eligibility bound. It cannot see a match not yet finished.
    past=[g for g in history if
          utc(g["kickoff_utc"])+RESULT_LAG<=now]
    past.sort(key=lambda x:(utc(x["kickoff_utc"]),x["match_id"]))
    features,flags=build_features_without_target_label(
        {"kickoff_utc":target["kickoff_utc"],
         "match_id":target["mid"],
         "home_team_id":target["home_team_id"],
         "away_team_id":target["away_team_id"]},
        past,selected,[utc(x["kickoff_utc"]) for x in past],
        allow_incomplete=True)
    need(set(features)==set(BASE)|{
        "home_xg_for","home_xg_against","away_xg_for","away_xg_against"},
        "TRAIN_FORWARD_14_PLUS_4_FEATURE_SCHEMA_DRIFT")
    missing=[key for key in BASE if features[key] is None]
    if not flags["history5"] or any(features[k] is None for k in
       ("home_goals_for","home_goals_against","home_points",
        "away_goals_for","away_goals_against","away_points")):
        return None,"M0_FALLBACK_MISSING_TRUE_HISTORY5"
    # CatBoost knows missing optional fields as floating NaNs; never 0.
    vector=[numeric(features[k]) for k in BASE]
    probs=model.predict_proba([vector])
    classes=[str(z) for z in model.classes_]
    p={key:float(probs[0][classes.index(key)]) for key in CLASSES}
    need(all(math.isfinite(v) and 0<=v<=1 for v in p.values())
         and abs(sum(p.values())-1)<1e-8,
         "INVALID_V3R_PROBABILITY")
    core={
        "schema":CONTRACT,"model_version":MODEL_VERSION,
        "research_only":True,"production_approved":False,
        "official_fit_increment":0,
        "original_historic_source_pit_proven":False,
        "independent_host_publication_proof_pending":True,
        "source_class":"REAL_NETWORK_FIXTURE_AT_NEW_FREEZE_PLUS_HISTORICAL_OBSERVATIONS_AS_OF_NOW",
        "model_binary_sha256":manifest["binary_sha256"],
        "model_manifest_sha256":manifest["manifest_sha256"],
        "source_m0_forecast_sha256":target["id"],
        "m0_original_capture_utc":target["m0_at"],
        "league":target["league"],
        "provider_match_id":target["mid"],
        "kickoff_utc":target["kickoff_utc"],
        "generated_at_utc":stamp(now),
        "source_capture_chain_sha256":source_chain_sha,
        "feature_names":list(BASE),
        "feature_vector_sha256":hash_json({
            "features":{k:features[k] for k in BASE}}),
        "feature_values":{k:features[k] for k in BASE},
        "missing_optional_features":missing,
        "missing_value_policy":"NAN_NOT_ZERO_AND_RETRY",
        "complete_lastfive_history":True,
        "full_14_feature_coverage":not bool(missing),
        "stats_source_identity_mismatches_not_used":drift,
        "target_result_used":False,
        "p_1x2":p,
    }
    core["forecast_sha256"]=hash_json(core)
    return core,None


def run_live(client,*,now=None,source_db=SOURCE_DB,m0_db=M0_DB,
             out_root=OUTPUT,model_file=MODEL_FILE,manifest_file=MANIFEST,
             public_key=PUBLIC_KEY,run_id=None):
    start=when(now or datetime.now(timezone.utc))
    model,manifest,model_created=train_or_load(source_db=source_db,
        model_file=model_file,manifest_file=manifest_file)
    targets,old=verified_m0_candidates(db_path=m0_db,now=start,out_root=out_root)
    status=Counter();forecasts=[];network_calls=0;failures={}
    if targets:
        receipts,histories,listing,scoped,network_calls,failures=(
            current_listings(client,targets,now=start))
        captured=datetime.now(timezone.utc)
        obs,late=source_observations(source_db=source_db,cutoff=captured)
        chain=receipts[-1]["chain_sha256"]
        for t in targets:
            if t["league"] in scoped:
                status["LEAGUE_LISTING_UNAVAILABLE"]+=1
                continue
            h=histories.get(t["league"])
            if h is None:
                status["NO_VERIFIED_NATIVE_LISTING"]+=1
                continue
            result,reason=record_for(t,history=h,
                listing=listing[t["league"]],observations=obs,
                model=model,manifest=manifest,
                at=datetime.now(timezone.utc),source_chain_sha=chain)
            if reason:
                status[reason]+=1
                continue
            forecasts.append(result)
        # Save RAW provider replies encrypted: no plaintext in git.
        token=(run_id or os.environ.get("GITHUB_RUN_ID","manual"))
        need(re.fullmatch(r"[A-Za-z0-9_-]{1,60}",token) is not None,
             "UNSAFE_REAL_RUN_TOKEN")
        run_dir=Path(out_root)/"sources"/start.date().isoformat()/("run-"+token)
        need(not run_dir.exists(),"IMMUTABLE_V3R_NETWORK_SESSION_ALREADY_EXISTS")
        run_dir.mkdir(parents=True,exist_ok=False)
        evidence=seal(receipts,public_key,run_dir/"SOURCE.enc",
                      run_dir/"SOURCE.manifest.json")
    else:
        late=0;scoped={};evidence=None;chain=None
    # Last guard before persisted independent forecasts. Old M0 remains byte
    # unchanged; never retrospectively create forecasts after this cutoff.
    accepted=[]
    for record in forecasts:
        if datetime.now(timezone.utc)>=utc(record["kickoff_utc"])-LEAD:
            status["LATE_BEFORE_LOCAL_FREEZE"]+=1
            continue
        p=Path(out_root)/"forecasts"/record["league"]/(record["provider_match_id"]+".json")
        need(not p.exists(),"DUPLICATED_V3R_FORECAST_PUBLICATION")
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("x",encoding="utf8") as f:
            json.dump(record,f,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)
            f.write("\n")
        accepted.append(record)
    result={
        "schema":"kb3-v3r-forward-shadow-actual-run-v1",
        "run_utc":stamp(start),
        "model_version":MODEL_VERSION,
        "new_pinned_model_built":model_created,
        "pinned_model_sha256":manifest["binary_sha256"],
        "historical_train_n":manifest["training_rows"],
        "model_research_only":True,
        "production_approved":False,
        "official_fit_increment":0,
        "new_future_frozen_forecasts":len(accepted),
        "new_m0_parent_candidates":len(targets),
        "already_scored_or_ineligible_m0":old,
        "unavailable_reasons":dict(sorted(status.items())),
        "source_missing_leagues":scoped,
        "provider_network_request_count":network_calls,
        "provider_request_cap":MAX_CALLS,
        "provider_errors_by_type":failures,
        "source_observation_after_capture_excluded":late,
        "source_cipher_sha256":evidence["ciphertext_sha256"] if evidence else None,
        "source_chain_sha256":chain,
        "existing_m0_not_modified":True,
        "protected_eng_test_not_accessed":True,
        "host_attestation_pending":True,
        "no_automatic_champion_promotion":True,
    }
    result["report_sha256"]=hash_json(result)
    path=Path(out_root)/"reports"/start.date().isoformat()
    path.mkdir(parents=True,exist_ok=True)
    token=(run_id or os.environ.get("GITHUB_RUN_ID","manual"))
    target=path/("run-"+token+".json")
    need(not target.exists(),"IMMUTABLE_REPORT_EXISTS")
    with target.open("x",encoding="utf8") as fh:
        json.dump(result,fh,sort_keys=True,indent=2,ensure_ascii=False)
        fh.write("\n")
    print("KB3_V3R_REAL_SHADOW_RUN",json.dumps({
        "new_pinned_model_built":model_created,
        "new_future_frozen_forecasts":len(accepted),
        "new_m0_parent_candidates":len(targets),
        "unavailable_reasons":result["unavailable_reasons"],
        "provider_network_request_count":network_calls,
        "production_approved":False,
        "report_sha256":result["report_sha256"]},sort_keys=True))
    return result


def main():
    key=os.getenv("PITCHAPI_API_KEY","")
    need(bool(key.strip()),"ORIGINAL_PITCHAPI_KEY_MISSING")
    from pitchapi import PitchAPI
    run_live(PitchAPI(api_key=key,max_retries=0))


if __name__=="__main__":
    main()
