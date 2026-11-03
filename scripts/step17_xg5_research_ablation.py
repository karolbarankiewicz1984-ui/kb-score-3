"""Step17: a real, research-only, paired xG5 feature ablation on archived fixtures.

This is NOT the production M0 comparison, not formal GATE17, not provider
historical point-in-time evidence, not official recalibration or selection.
Both versions fit only on earlier finished fixtures and score the same later
fixtures. No Premier League TEST (or ENG at all), no external API calls.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.kb3_historical_feature_quality import FEATURE_VERSION

ROOT=Path(__file__).resolve().parents[1]
SOURCE_DB=ROOT/"data/research/historical_multistat/observations.sqlite"
REPORT_SCHEMA="kb3-step17-real-xg5-chronological-ablation-v1"
ALLOWED_SCOPES=frozenset(("ESP","ITA","GER","FRA","NED","BEL","TUR","POL"))
CLASSES=("1","X","2")
MIN_TRAIN=80
MIN_VAL=25
MIN_TOTAL=MIN_TRAIN+MIN_VAL
GOAL_FEATURES=("goals_for","goals_against","points")
EXTRAS=("total_shots","fouls","corners","yellow_cards")
XG_FEATURES=("xg_for","xg_against")

class ResearchSafetyError(ValueError):
    pass

def require(ok,code):
    if not ok: raise ResearchSafetyError(code)

def iso(s):
    require(isinstance(s,str) and s.endswith("Z"),"UTC_TIMESTAMP_REQUIRED")
    try:
        v=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc:
        raise ResearchSafetyError("INVALID_TIMESTAMP") from exc
    require(v.utcoffset()==timedelta(0),"NON_UTC_TIMESTAMP")
    return v

def only_numeric(value):
    if value is None: return float("nan")
    require(type(value) in (int,float) and math.isfinite(value),"BAD_NUMERIC_FEATURE")
    return float(value)

def build_example(feature,fixture):
    """Join research features with eventual 90-minute label *after* feature read.

    The label is never passed through the feature matrix. Each rolling statistic
    was computed from actual predecessor fixture IDs by the upstream auditor.
    """
    require(feature["schema"]==FEATURE_VERSION,"FEATURE_VERSION_MISMATCH")
    require(feature["source"]=="PitchAPI","WRONG_PROVIDER")
    require(feature["availability_class"]=="HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
            "UNEXPECTED_SOURCE_PROVENANCE")
    require(feature["original_pit_certified"] is False
            and feature["training_approved"] is False
            and feature["actual_source_first_published_at_known"] is False,
            "HISTORICAL_PIT_CANNOT_BE_CERTIFIED")
    require(feature["target_match_id"]==fixture["match_id"]
            and feature["scope"]==fixture["scope"]
            and feature["target_kickoff_utc"]==fixture["kickoff_utc"],
            "TARGET_IDENTITY_MISMATCH")
    require(feature["scope"] in ALLOWED_SCOPES,"PROTECTED_OR_UNAPPROVED_SCOPE")
    require(set(feature["sides"])=={"home","away"},"UNEXPECTED_SIDE")
    require(iso(feature["target_kickoff_utc"]) < datetime.now(timezone.utc)-timedelta(hours=3),
            "TARGET_NOT_SETTLED")
    base=[];with_xg=[]
    for team in ("home","away"):
        summary=feature["sides"][team]["all"]["5"]
        require(summary["requested_n"]==5 and summary["history_complete"]
                and summary["xg_complete"] and summary["actual_predecessors"]==5,
                "TRUE_LAST5_XG_INCOMPLETE")
        for key in GOAL_FEATURES+EXTRAS:
            field=summary["metrics"][key]
            if key in GOAL_FEATURES:
                require(field["complete"] and field["valid_n"]==5
                        and field["mean"] is not None,"FORM5_INCOMPLETE")
            base.append(only_numeric(field["mean"]))
        xg=[]
        for key in XG_FEATURES:
            field=summary["metrics"][key]
            require(field["complete"] and field["valid_n"]==5
                    and field["mean"] is not None,"XG5_MISSING_IN_WINDOW")
            xg.append(only_numeric(field["mean"]))
        with_xg.extend(xg)
    gh,ga=fixture["goals_home_90"],fixture["goals_away_90"]
    require(type(gh) is int and type(ga) is int and 0<=gh<50 and 0<=ga<50,
            "INVALID_TARGET_SCORE")
    label="1" if gh>ga else "X" if gh==ga else "2"
    return {"scope":fixture["scope"],"season":fixture["season"],
            "match_id":fixture["match_id"],"kickoff_utc":fixture["kickoff_utc"],
            "y":label,"base":base,"with_xg":base+with_xg}

def load_examples(path=SOURCE_DB):
    path=Path(path)
    require(path.is_file(),"SOURCE_SQLITE_MISSING")
    with sqlite3.connect("file:"+str(path.resolve())+"?mode=ro",uri=True) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                "SOURCE_SQLITE_INTEGRITY_FAIL")
        tables={x[0] for x in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        require({"finished_fixture_index","observations","rolling_feature_cache"}<=tables,
                "SOURCE_SCHEMA_MISSING")
        count=db.execute("SELECT COUNT(*) FROM rolling_feature_cache").fetchone()[0]
        total=db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        require(count==total,"SOURCE_ROLLING_CACHE_INCOMPLETE")
        require(db.execute("""SELECT COUNT(*) FROM rolling_feature_cache
                      WHERE research_only!=1 OR provider_original_pit_certified!=0
                      OR feature_version!=?""",(FEATURE_VERSION,)).fetchone()[0]==0,
                "UNSAFE_RESEARCH_CACHE")
        require(db.execute("SELECT COUNT(*) FROM observations WHERE scope='ENG'").fetchone()[0]==0,
                "PROTECTED_ENGLISH_TEST_OBSERVED")
        query="""SELECT c.scope,c.target_match_id,c.target_kickoff_utc,c.feature_json,
                        f.season,f.goals_home_90,f.goals_away_90,
                        o.match_id AS observed_target
                 FROM rolling_feature_cache c
                 JOIN finished_fixture_index f
                 ON f.scope=c.scope AND f.match_id=c.target_match_id
                 JOIN observations o
                 ON o.scope=c.scope AND o.match_id=c.target_match_id
                 ORDER BY c.target_kickoff_utc,c.scope,c.target_match_id"""
        all_rows=db.execute(query).fetchall()
    require(len(all_rows)==count,"UNJOINED_FEATURE_ROWS")
    examples=[]; missing=Counter();by_scope=Counter();ids=set()
    for scope,mid,ko,payload,season,gh,ga,observed_target in all_rows:
        require(scope in ALLOWED_SCOPES or scope=="UCL","FORBIDDEN_SOURCE_SCOPE")
        if scope=="UCL":
            missing["ucl_mapping_not_certified"]+=1;continue
        f=json.loads(payload)
        sides=f["sides"]
        if not (sides["home"]["all"]["5"]["xg_complete"] and
                sides["away"]["all"]["5"]["xg_complete"]):
            missing["true_last5_xg_incomplete"]+=1;continue
        if (scope,mid) in ids: raise ResearchSafetyError("DUPLICATE_SOURCE_FIXTURE")
        ids.add((scope,mid))
        row=build_example(f,{"scope":scope,"match_id":mid,"kickoff_utc":ko,
                             "season":season,"goals_home_90":gh,"goals_away_90":ga})
        examples.append(row);by_scope[scope]+=1
    examples.sort(key=lambda x:(x["kickoff_utc"],x["scope"],x["match_id"]))
    return examples,{"source_observations":total,"research_targets":count,
                     "full_xg5_targets":len(examples),
                     "full_xg5_by_scope":dict(sorted(by_scope.items())),
                     "excluded_reasons":dict(sorted(missing.items())),
                     "source_sqlite_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}

def chronological_split(examples):
    require(all(examples[i]["kickoff_utc"]<=examples[i+1]["kickoff_utc"]
                for i in range(len(examples)-1)),"NOT_CHRONOLOGICAL")
    if len(examples)<MIN_TOTAL:
        return None,"TOO_FEW_COMPLETE_XG5"
    ix=int(len(examples)*0.70)
    while ix<len(examples) and ix>0 and examples[ix-1]["kickoff_utc"]==examples[ix]["kickoff_utc"]:
        ix+=1
    if ix>=len(examples) or ix<MIN_TRAIN or len(examples)-ix<MIN_VAL:
        return None,"INSUFFICIENT_CHRONOLOGICAL_PARTITIONS"
    train,test=examples[:ix],examples[ix:]
    require(iso(train[-1]["kickoff_utc"])<iso(test[0]["kickoff_utc"]),
            "NON_STRICT_SPLIT")
    require(len({(r["scope"],r["match_id"]) for r in examples})==len(examples),
            "DUPLICATE_MATCH_IDS")
    return (train,test),None

def score(pairs):
    require(len(pairs)>0,"NO_SCORED_GAMES")
    brier=0.;ll=0.;correct=0; bins=[[] for _ in range(5)]
    for pred,y in pairs:
        require(y in CLASSES and set(pred)==set(CLASSES),"INVALID_CLASSES")
        require(all(type(pred[k]) in (int,float) and math.isfinite(pred[k]) and
                    0<pred[k]<1 for k in CLASSES),"INVALID_PREDICTION")
        require(abs(sum(pred.values())-1)<1e-8,"NON_NORMALIZED_P")
        brier+=sum((pred[k]-int(k==y))**2 for k in CLASSES)
        ll-=math.log(pred[y]); top=max(CLASSES,key=lambda k:pred[k])
        correct+=int(top==y)
        idx=min(4,int(max(pred.values())*5))
        bins[idx].append((max(pred.values()),int(top==y)))
    n=len(pairs)
    ece=sum(len(g)/n*abs(sum(x[0] for x in g)/len(g)-
                         sum(x[1] for x in g)/len(g)) for g in bins if g)
    return {"n":n,"brier_sum3":brier/n,"log_loss":ll/n,
            "top1_accuracy":correct/n,"top1_ece5":ece}

def fit_compare(split):
    from catboost import CatBoostClassifier
    train,test=split
    require(set(x["y"] for x in train)==set(CLASSES),
            "TRAIN_MISSING_ONE_OUTCOME_CLASS")
    all_results={}
    for name,field in (("NO_XG_FORM_AND_CORE5","base"),
                       ("WITH_NATIVE_XG5_FORM_AND_CORE5","with_xg")):
        # Fixed parameters: absolutely no tuning on the later evaluation rows.
        model=CatBoostClassifier(iterations=175,depth=3,learning_rate=.035,
            l2_leaf_reg=8.0,loss_function="MultiClass",random_seed=20261103,
            thread_count=2,verbose=False,allow_writing_files=False)
        model.fit([r[field] for r in train],[r["y"] for r in train])
        classes=[str(c) for c in model.classes_]
        require(set(classes)==set(CLASSES),"CATBOOST_UNEXPECTED_LABELS")
        predictions=model.predict_proba([r[field] for r in test])
        evaluated=[]
        for prob,y in zip(predictions,(r["y"] for r in test)):
            evaluated.append(({k:float(prob[classes.index(k)]) for k in CLASSES},y))
        all_results[name]={"metrics":score(evaluated),
                           "feature_count":len(train[0][field]),
                           "fit_only_earlier_records":True}
    diff={k:all_results["WITH_NATIVE_XG5_FORM_AND_CORE5"]["metrics"][k]-
          all_results["NO_XG_FORM_AND_CORE5"]["metrics"][k]
          for k in ("brier_sum3","log_loss","top1_accuracy")}
    return all_results,diff

def run(path=SOURCE_DB,fit=True):
    examples,audit=load_examples(path)
    split,why=chronological_split(examples)
    out={"schema":REPORT_SCHEMA,"status":"RESEARCH_NOT_PRODUCTION",
         "source":audit,"historical_original_pit_certified":False,
         "train_only_before_validation":True,
         "protected_2026_27_premier_league_test_accessed":False,
         "model_m0_unchanged":True,"calibration_100_fit_50_holdout_unchanged":True,
         "gates_16_17":"PENDING","champion_promotion_authorized":False,
         "same_games_and_fixed_parameters":True,
         "is_this_the_existing_M0_comparison":False,
         "why":"paired CatBoost no-xG vs xG5 feature ablation only"}
    if split is None:
        out["research_fit_status"]="NO_GO"
        out["research_fit_reason"]=why
        out["train_n"]=out["validation_n"]=0
    else:
        train,test=split
        out["train_n"]=len(train);out["validation_n"]=len(test)
        out["train_last_kickoff_utc"]=train[-1]["kickoff_utc"]
        out["validation_first_kickoff_utc"]=test[0]["kickoff_utc"]
        out["train_league_counts"]=dict(sorted(Counter(x["scope"] for x in train).items()))
        out["validation_league_counts"]=dict(sorted(Counter(x["scope"] for x in test).items()))
        out["validation_unique_iso_weeks"]=len(set(
            (iso(x["kickoff_utc"]).isocalendar().year,
             iso(x["kickoff_utc"]).isocalendar().week) for x in test))
        out["split_fixture_ids_sha256"]=hashlib.sha256(json.dumps(
            [(x["scope"],x["match_id"],"TRAIN" if i<len(train) else "VALIDATION")
             for i,x in enumerate(examples)],separators=(",",":")).encode()).hexdigest()
        if fit:
            result,diff=fit_compare(split)
            out["research_fit_status"]="EXECUTED_RESEARCH_ABLATION"
            out["paired_results"]=result
            out["with_xg_minus_without_xg"]=diff
        else:
            out["research_fit_status"]="ELIGIBLE_UNFITTED_PREFLIGHT"
    out["independent_generalization_evidence"]=False
    out["formal_g17_ready"]=False
    out["report_sha256"]=hashlib.sha256(json.dumps(
        out,sort_keys=True,allow_nan=False,separators=(",",":")).encode()).hexdigest()
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=SOURCE_DB)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    args=p.parse_args()
    require(not args.out.exists(),"APPEND_ONLY_RESULT_EXISTS")
    report=run(args.db,fit=not args.preflight_only)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("KB3_STEP17_XG5_RESEARCH",json.dumps({
        k:report.get(k) for k in ("research_fit_status","train_n","validation_n",
                                 "validation_unique_iso_weeks","paired_results",
                                 "with_xg_minus_without_xg","gates_16_17")},
        sort_keys=True))
if __name__=="__main__":main()
