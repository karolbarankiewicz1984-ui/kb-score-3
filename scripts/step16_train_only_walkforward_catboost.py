"""TRAIN-only 3-fold research; never tune on historical 374 validation or 2026/27 TEST."""
import argparse,gzip,hashlib,json,math,os
from collections import Counter
from pathlib import Path
from scripts.step14_m1r_train_real_catboost_720_evaluate_374 import SOURCE_MATRIX,SOURCE_SUMMARY,PARAMS,ROOT,_as_label,_score,M1RFitSafetyError
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import _valid_safe
from scripts.step14_full_1140_native_public_pit_lineage import norm,check_season,to_plain
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step13_baseline import forecast
from src.kb3_step13_retrospective import _train_poisson

SEASONS=("2023/2024","2024/2025")
VARIANTS={"BASE_FIXED":dict(PARAMS),
          "SHALLOW_FIXED":dict(PARAMS,iterations=250,depth=3,learning_rate=.045,l2_leaf_reg=10.0),
          "ELO_FORM5_FIXED":dict(PARAMS,iterations=300,depth=3,learning_rate=.04,l2_leaf_reg=10.0)}
SCORES=("n","log_loss","brier_multiclass_sum3","top1_accuracy","top1_ece_5_bins")
def require(ok,code):
    if not ok:raise M1RFitSafetyError(code)
def train_source(root):
    root=Path(root);meta=json.loads((root/SOURCE_SUMMARY).read_text())
    raw=(root/SOURCE_MATRIX).read_bytes()
    require(meta["matrix_gzip_sha256"]==hashlib.sha256(raw).hexdigest() and
        meta["matrix_rows"]==1140 and
        meta["m1r_BASE_eligible_by_partition"]=={"TRAIN":720,"VALIDATION":374} and
        meta["original_M1_Gate14"]=="PENDING" and
        meta["original_2026_27_TEST_examined"] is False,"SOURCE_GATE_CHANGED")
    counts=Counter();selected=[]
    with gzip.open(root/SOURCE_MATRIX,"rt",encoding="utf8") as f:
        for line in f:
            if not line.strip():continue
            row=json.loads(line);part=row["partition"]
            require(part in ("TRAIN","VALIDATION"),"TEST_IN_SOURCE")
            counts[part]+=1
            if part!="TRAIN":continue
            require(row["source_class"]=="B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT" and
                row["original_M1_159_PIT_certified"] is False and
                set(row["m1r_BASE_121_numeric_features"])==EXPECTED_FEATURES and
                set(row["m1r_BASE_38_missing_flags"])==EXPECTED_MISSING,"UNTRUSTED_TRAIN_FEATURES")
            if row["m1r_base_eligible"]:selected.append(row)
    require(counts=={"TRAIN":760,"VALIDATION":380} and len(selected)==720 and
        len({r["fixture_id"] for r in selected})==720,"NOT_ORIGINAL_720_TRAIN")
    selected.sort(key=lambda r:(r["kickoff_utc"],r["fixture_id"]))
    return selected,meta["matrix_gzip_sha256"]
def obtain_train_labels(key,root,client_factory=None):
    require(bool(key),"TRAIN_KEY_MISSING")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    cli=client_factory(api_key=key);calls=0
    def call(fn,*args,**kwargs):
        nonlocal calls
        require(calls<3,"MORE_THAN_THREE_PITCH_CALLS")
        calls+=1
        return to_plain(fn(*args,**kwargs))
    catalog=call(cli.leagues.list)
    found=[l for l in catalog["leagues"] if
        norm(l.get("name")).replace(" ","")=="premierleague" and
        str(l.get("country_code","")).upper()=="ENG" and
        all(s in (l.get("seasons") or []) for s in SEASONS)]
    require(len(found)==1,"ORIGINAL_ENGLISH_LEAGUE_ID_AMBIGUOUS")
    allowed={k:v[0] for k,v in _valid_safe(root).items() if v[1]=="TRAIN"}
    require(len(allowed)==760,"ORIGINAL_TRAIN_760_DRIFT")
    labels={}
    for season in SEASONS:
        source=call(cli.leagues.matches,found[0]["id"],season=season)
        matches=source["matches"];check_season(matches,season,expected_count=380)
        for m in matches:
            mid=m["id"]
            require(m["status"]=="finished" and mid in allowed and
                m["time_utc"]==allowed[mid] and mid not in labels and
                m["home_team"]["id"]!=m["away_team"]["id"],"TRAIN_MATCH_OR_TIME_CHANGED")
            labels[mid]={"outcome":_as_label(m["score_home"],m["score_away"]),
                         "home_goals":m["score_home"],"away_goals":m["score_away"]}
    require(set(labels)==set(allowed),"LABEL_SET_NOT_TRAIN_ONLY")
    return labels,calls
def folds(rows):
    require(len(rows)==720,"EXPECTED_ONLY_720")
    result=[]
    for cut in (360,480,600):
        while cut<720 and rows[cut]["kickoff_utc"]==rows[cut-1]["kickoff_utc"]:cut+=1
        end=min(720,cut+100)
        while end<720 and rows[end]["kickoff_utc"]==rows[end-1]["kickoff_utc"]:end+=1
        require(end>cut and end<=720 and end-cut>=90 and
                rows[cut-1]["kickoff_utc"]<rows[cut]["kickoff_utc"],"LEAKING_FOLD_BOUNDARY")
        result.append((rows[:cut],rows[cut:end]))
    return result
def value(row,name):
    typ,key=name.split(":",1)
    v=(row["m1r_BASE_121_numeric_features"][key] if typ=="num"
       else row["m1r_BASE_38_missing_flags"][key])
    if v is None:return float("nan")
    require(type(v) in (float,int,bool) and math.isfinite(v),"BAD_FEATURE_VALUE")
    return float(v)
def columns(train,variant):
    pool=sorted(["num:"+k for k in EXPECTED_FEATURES]+["miss:"+k for k in EXPECTED_MISSING])
    pool=[n for n in pool if "xg" not in n.lower()]
    if variant=="ELO_FORM5_FIXED":
        pool=[n for n in pool if
            n in ("num:home_elo","num:away_elo","num:elo_home_minus_away",
                  "num:home_days_since_last_kickoff","num:away_days_since_last_kickoff")
            or "_all_5_" in n or "_venue_5_" in n]
    chosen=[]
    for name in pool:
        distinct=set()
        for r in train:
            f=value(r,name);distinct.add("NULL" if math.isnan(f) else f)
            if len(distinct)>1:break
        if len(distinct)>1:chosen.append(name)
    require(len(chosen)>=5,"FOLD_FEATURES_TOO_FEW")
    return chosen
def scores(items):
    obj=_score([p for p,y in items],[y for p,y in items])
    return {k:obj[k] for k in SCORES}
def run(root=ROOT,labels_override=None,client_factory=None):
    root=Path(root);rows,source_sha=train_source(root)
    if labels_override is None:
        labels,calls=obtain_train_labels(os.environ.get("PITCHAPI_API_KEY",""),root,client_factory)
    else:labels,calls=labels_override,0
    require(set(r["fixture_id"] for r in rows)<=set(labels),"MISSING_TRAIN_LABELS")
    from catboost import CatBoostClassifier,Pool
    output=[];pooled={x:[] for x in (*VARIANTS,"M0_INNER_FOLD_TRAIN_ONLY")}
    for i,(train,test) in enumerate(folds(rows),1):
        ytrain=[labels[r["fixture_id"]]["outcome"] for r in train]
        ytest=[labels[r["fixture_id"]]["outcome"] for r in test]
        require(set(ytrain)=={"1","X","2"},"FOLD_NOT_THREE_CLASSES")
        variants={}
        for name,config in VARIANTS.items():
            names=columns(train,name)
            model=CatBoostClassifier(**config)
            model.fit(Pool([[value(r,k) for k in names] for r in train],
                           label=ytrain,feature_names=names))
            probs=model.predict_proba([[value(r,k) for k in names] for r in test])
            actual_classes=[str(c) for c in model.classes_]
            require(set(actual_classes)=={"1","X","2"},"BAD_CATBOOST_CLASSES")
            pairs=[({c:float(v[actual_classes.index(c)]) for c in ("1","X","2")},y)
                   for v,y in zip(probs,ytest)]
            pooled[name].extend(pairs)
            variants[name]={"metrics":scores(pairs),"feature_count":len(names),
                           "feature_names_sha256":hashlib.sha256(
                              json.dumps(names).encode()).hexdigest()}
        # Fair M0: refit only on preceding TRAIN records and goals for this fold.
        poisson_training=[(
          r["m1r_BASE_121_numeric_features"]["elo_home_minus_away"]/400.0,
          labels[r["fixture_id"]]["home_goals"],labels[r["fixture_id"]]["away_goals"])
          for r in train]
        m0_params=_train_poisson(poisson_training)
        m0_pairs=[(
          forecast(r["m1r_BASE_121_numeric_features"]["home_elo"],
                   r["m1r_BASE_121_numeric_features"]["away_elo"],
                   m0_params)["p_1x2"],labels[r["fixture_id"]]["outcome"])
          for r in test]
        pooled["M0_INNER_FOLD_TRAIN_ONLY"].extend(m0_pairs)
        variants["M0_INNER_FOLD_TRAIN_ONLY"]={
          "metrics":scores(m0_pairs),"poisson_fit_only_prior_inner_train":True}
        output.append({"fold":i,"train_n":len(train),"inner_eval_n":len(test),
                       "train_last_utc":train[-1]["kickoff_utc"],
                       "eval_first_utc":test[0]["kickoff_utc"],
                       "eval_last_utc":test[-1]["kickoff_utc"],
                       "variants":variants})
    agg={name:scores(pooled[name]) for name in (*VARIANTS,"M0_INNER_FOLD_TRAIN_ONLY")}
    result={"schema":"kb3-m1r-train-only-chronological-three-fold-research-v1",
            "status":"TRAIN_ONLY_RESEARCH_NO_CHAMPION",
            "training_population":720,"native_training_only_api_requests":calls,
            "validation_374_labels_requested":False,"test_2026_27_requested":False,
            "original_M0_or_M1_modified":False,
            "source_class":"B_RECONSTRUCTED_PREDECESSORS_NOT_HISTORIC_PROVIDER_PIT",
            "fixed_variants":list(VARIANTS),"source_sha256":source_sha,
            "m0_comparator_fit_only_each_earlier_inner_training_fold":True,
            "folds":output,"aggregate":agg,
            "research_order_only":sorted(VARIANTS,key=lambda n:agg[n]["log_loss"])}
    result["receipt_sha256"]=hashlib.sha256(
        json.dumps(result,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    output=Path(p.parse_args().out)
    require(not output.exists(),"RESEARCH_REPORT_APPEND_ONLY")
    result=run();output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print(json.dumps({"status":result["status"],"aggregate":result["aggregate"],
                      "calls":result["native_training_only_api_requests"]},sort_keys=True))
if __name__=="__main__":main()
