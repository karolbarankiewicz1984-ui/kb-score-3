"""Separate real retro CatBoost on a versioned chronological research cohort.

Historical reference was 1007/376; newer source captures may expand it.

This is NOT original as-of, production M0, or 85-feature legacy M1-R.
Archived postmatch source values may not have existed at each original kickoff.
No provider API; models and metrics remain only private CI artifacts.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import timedelta
from bisect import bisect_right
from pathlib import Path
import hashlib
import json
import math
import random

from scripts.kb3_p1_historical_eligibility_split import (
    SOURCE_DB,RECHECK_DB,assess,utc,read_only_conn,hash_json,MIN_LEAD,
    RESULT_MIN_LAG,LEAGUES,
)
from src.kb3_historical_feature_quality import _load_records,rolling_window
from src.kb3_step14_m1_math_calibration import score_predictions,score_one

SCHEMA="kb3-p1-retrospective-catboost-research-1007x376-v1"
CLASSES=("1","X","2")
GOALS=("goals_for","goals_against","points")
CORE=("total_shots","fouls","corners","yellow_cards")
XG=("xg_for","xg_against")
BASE=tuple(f"{side}_{key}" for side in ("home","away") for key in GOALS+CORE)
WITH_XG=BASE+tuple(f"{side}_{key}" for side in ("home","away") for key in XG)
PARAMS={
 "iterations":180,"depth":3,"learning_rate":.035,"l2_leaf_reg":8.,
 "loss_function":"MultiClass","random_seed":20261104,"thread_count":2,
 "verbose":False,"allow_writing_files":False,"nan_mode":"Min",
}
class RetroResearchError(ValueError): pass
def need(ok,msg):
    if not ok:raise RetroResearchError(msg)
def numeric(v):
    if v is None:return float("nan")
    need(type(v) in (int,float) and math.isfinite(v),"BAD_NUMERIC_FEATURE")
    return float(v)


def build_features_without_target_label(target,history,observed,clocks,*,allow_incomplete=False):
    """Same last-five feature contract; NaN means missing, never invented zero.

    Existing retrospective 4550/1864 validation remains strict by default.
    True new forward research may tolerate unavailable optional statistics.
    If a whole five-game history is absent, the caller must mark low coverage
    and use the existing M0 fallback, not pretend a reliable V3-R estimate.
    """
    ko=utc(target["kickoff_utc"])
    proxy=ko-timedelta(hours=2)
    need(proxy<=ko-MIN_LEAD,"CUTOFF_BEFORE_90MIN")
    predecessors=history[:bisect_right(clocks,proxy-RESULT_MIN_LAG)]
    need(all(utc(p["kickoff_utc"])+RESULT_MIN_LAG<=proxy and
             p["match_id"]!=target["match_id"] for p in predecessors),
         "POSTCUTOFF_OR_TARGET_LEAK")
    feats={}
    flags={"history5":True,"core5":True,"xg5":True}
    for side,team in (("home",target["home_team_id"]),
                      ("away",target["away_team_id"])):
        roll=rolling_window(predecessors,observed,team,5)
        flags["history5"] &=roll["history_complete"]
        flags["core5"] &=roll["core_stats_complete"]
        flags["xg5"] &=roll["xg_complete"]
        for key in GOALS+CORE+XG:
            metric=roll["metrics"][key]
            if key in GOALS and not allow_incomplete:
                need(metric["complete"] and metric["valid_n"]==5 and
                     metric["mean"] is not None,"GOALS_LAST5_INCOMPLETE")
            if not metric["complete"]:
                need(metric["mean"] is None,"PARTIAL_MEAN_LEAK")
            feats[f"{side}_{key}"]=metric["mean"]
    need(set(feats)==set(WITH_XG),"FEATURE_CONTRACT_MISSING")
    if not allow_incomplete:
        need(flags["history5"], "MISSING_REQUIRED_LAST5")
    return feats,flags


def load_sets(db_path=SOURCE_DB,recheck_path=RECHECK_DB):
    gate,train_sel,val_sel=assess(db_path,recheck_path)
    a=gate["research_reconstruction"]
    need(gate["official_v2_training_eligible"]==0 and
         gate["official_v2_validation_eligible"]==0 and
         gate["formal_catboost_85_retraining_authorized"] is False,
         "FALSE_ORIGINAL_PIT_CERTIFICATION")
    # The 1007 / 376 / 56 split belongs only to the prior source SHA
    # pinned in the original research report. Fresh historical observations
    # re-compute a new, separate research cohort; they MUST NOT be presented
    # as a replay or re-training of the pinned Shadow Six binary.
    need(gate["source_first_published_proven"] is False and
         gate["independent_historical_target_prematch_host_receipt_available"] is False
         and gate["official_fit_samples_added"]==0
         and gate["research_reconstruction"]["research_only"] is True
         and gate["research_reconstruction"]["historical_reconstruction_only"] is True
         and a["split"]["status"]=="RESEARCH_SPLIT_ONLY_NOT_FIT"
         and a["split"]["embargo_days"]==7
         and len(train_sel)>0 and len(val_sel)>0
         and len(train_sel)+len(val_sel)+a["embargo_discarded"]==
             a["potential_historical_no_xg_history5"],
         "RESEARCH_SPLIT_PROVENANCE_OR_ACCOUNTING_DRIFT")
    with read_only_conn(db_path) as db:
        fixt,obs,rechecks,buckets=_load_records(
            db,recheck_db_path=recheck_path)
    index={(f["scope"],f["match_id"]):f
           for games in fixt.values() for f in games}
    clocks={scope:[utc(f["kickoff_utc"]) for f in games]
            for scope,games in fixt.items()}
    rows=[]
    counted=Counter()
    for part,items in (("TRAIN",train_sel),("VALIDATION",val_sel)):
        for selector in items:
            key=(selector["league"],selector["fixture_id"])
            need(selector["league"] in LEAGUES and key in index and
                 selector["train_approved"] is False and
                 selector["historical_original_pit_certified"] is False,
                 "UNSAFE_SELECTOR")
            t=index[key]
            need(t["kickoff_utc"]==selector["kickoff_utc"] and
                 t["season"]==selector["season"],
                 "TARGET_IDENTITY_CHANGED")
            feat,fl=build_features_without_target_label(
                t,fixt[selector["league"]],obs,clocks[selector["league"]])
            need(fl["core5"]==selector["complete_core5"] and
                 fl["xg5"]==selector["complete_xg5"],
                 "RECONSTRUCTED_SELECTOR_FEATURE_DRIFT")
            # The actual postmatch 90min label is read ONLY after feature build.
            h,aw=t["goals_home_90"],t["goals_away_90"]
            need(type(h) is int and type(aw) is int and
                 0<=h<=30 and 0<=aw<=30,"INVALID_TARGET_LABEL")
            label="1" if h>aw else "X" if h==aw else "2"
            rows.append({"league":selector["league"],"fixture_id":t["match_id"],
                         "kickoff_utc":t["kickoff_utc"],"partition":part,
                         "features":feat,"label":label})
            counted[part+"_core5"]+=int(fl["core5"])
            counted[part+"_xg5"]+=int(fl["xg5"])
    tr=[r for r in rows if r["partition"]=="TRAIN"]
    va=[r for r in rows if r["partition"]=="VALIDATION"]
    need(len(tr)==len(train_sel) and len(va)==len(val_sel) and
         len(tr)>0 and len(va)>0,"TRAIN_VALIDATION_COUNT_DRIFT")
    need(len({(r["league"],r["fixture_id"]) for r in rows})==len(rows),
         "DUPLICATE_FIXTURE_IN_PARTITIONS")
    need(max(utc(x["kickoff_utc"]) for x in tr)+timedelta(days=7)
         <=min(utc(x["kickoff_utc"]) for x in va),"EMBARGO_VIOLATION")
    need(set(r["label"] for r in tr)==set(CLASSES),"MISSING_TRAIN_CLASS")
    meta={"historical_source_sha256":a["historical_source_sha256"],
          "original_gate_sha256":gate["report_sha256"],
          "train_selector_sha256":hash_json(train_sel),
          "validation_selector_sha256":hash_json(val_sel),
          "feature_count_no_xg":len(BASE),
          "feature_count_with_xg":len(WITH_XG),
          "cohort_train_n":len(tr),"cohort_validation_n":len(va),
          "cohort_embargo_discarded":a["embargo_discarded"],
          "original_shadow_six_reference_train_n":1007,
          "original_shadow_six_reference_validation_n":376,
          "original_shadow_six_immutable_binary_reused":False,
          "counts":dict(counted),
          "source_class":"HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT",
          "formal_training_allowed":False}
    return tr,va,meta


def matrix(rows,names):
    return [[numeric(r["features"][k]) for k in names] for r in rows]


def research_fit(train,valid,names,path):
    from catboost import CatBoostClassifier
    clf=CatBoostClassifier(**PARAMS)
    clf.fit(matrix(train,names),[r["label"] for r in train])
    cls=[str(v) for v in clf.classes_]
    need(set(cls)==set(CLASSES),"INVALID_CLASS_ORDER")
    scores=clf.predict_proba(matrix(valid,names))
    probs=[{key:float(z[cls.index(key)]) for key in CLASSES}
           for z in scores]
    need(all(all(math.isfinite(z) and 0<=z<=1 for z in p.values())
             and abs(sum(p.values())-1)<1e-8 for p in probs),
         "INVALID_PROBABILITY")
    clf.save_model(str(path))
    return probs,hashlib.sha256(Path(path).read_bytes()).hexdigest()


def by_league(valid,pred):
    grp=defaultdict(list)
    for row,p in zip(valid,pred):
        grp[row["league"]].append((p,row["label"]))
    return {lg:score_predictions([p for p,y in rows],[y for p,y in rows])
            for lg,rows in sorted(grp.items())}


def week_ci(valid,base,xg,replicates=600):
    weeks=defaultdict(list)
    for row,p,q in zip(valid,base,xg):
        iso=utc(row["kickoff_utc"]).isocalendar()
        a=score_one(p,row["label"])
        b=score_one(q,row["label"])
        weeks[(iso.year,iso.week)].append((b[0]-a[0],b[1]-a[1]))
    keys=sorted(weeks)
    need(len(keys)>=2,"INSUFFICIENT_WEEK_BLOCKS")
    rng=random.Random(20261104)
    samples=[[],[]]
    for _ in range(replicates):
        group=[v for k in (rng.choice(keys) for _ in keys) for v in weeks[k]]
        for i in (0,1):
            samples[i].append(sum(v[i] for v in group)/len(group))
    def ci(a):
        a=sorted(a)
        return [round(a[int(.025*len(a))],8),
                round(a[int(.975*len(a))-1],8)]
    return {"weeks":len(keys),"replicates":replicates,
            "delta_xg_minus_no_xg_logloss_ci95":ci(samples[0]),
            "delta_xg_minus_no_xg_brier_ci95":ci(samples[1]),
            "historical_replay_not_prospective":True}


def execute(outdir,db_path=SOURCE_DB,recheck_path=RECHECK_DB):
    outdir=Path(outdir)
    need(not outdir.exists(),"REPORT_PATH_MUST_BE_NEW")
    train,valid,meta=load_sets(db_path,recheck_path)
    outdir.mkdir(parents=True)
    outcomes={};preds={}
    freq=Counter(x["label"] for x in train)
    priors={label:(freq[label]+1)/(len(train)+3) for label in CLASSES}
    baseline=[priors for x in valid]
    outcomes["TRAIN_ONLY_MARGINAL_LAPLACE"]={
        "metrics":score_predictions(baseline,[x["label"] for x in valid]),
        "by_league":by_league(valid,baseline)}
    for variant,names in (
        ("CATBOOST_RESEARCH_NO_XG",BASE),
        ("CATBOOST_RESEARCH_PLUS_XG_WITH_MISSING",WITH_XG)):
        p,sha=research_fit(train,valid,names,outdir/(variant+".cbm"))
        preds[variant]=p
        outcomes[variant]={"features":list(names),
            "metrics":score_predictions(p,[r["label"] for r in valid]),
            "by_league":by_league(valid,p),
            "private_artifact_binary_sha256":sha}
    base=outcomes["CATBOOST_RESEARCH_NO_XG"]["metrics"]
    with_xg=outcomes["CATBOOST_RESEARCH_PLUS_XG_WITH_MISSING"]["metrics"]
    report={
        "schema":SCHEMA,"status":"EXECUTED_REAL_RETROSPECTIVE_RESEARCH_ONLY",
        "train_n":len(train),"validation_n":len(valid),
        "source_revision_class":"CURRENT_EXPANDING_HISTORICAL_RESEARCH_ONLY",
        "old_pinned_shadow_six_unchanged":True,
        "last_train_utc":max(x["kickoff_utc"] for x in train),
        "first_validation_utc":min(x["kickoff_utc"] for x in valid),
        "embargo_days":7,"source_provenance":meta,
        "training_class_counts":dict(sorted(freq.items())),
        "fixed_training_parameters":PARAMS,"variants":outcomes,
        "xg_minus_no_xg_delta":{key:round(with_xg[key]-base[key],9)
            for key in ("brier_sum3","log_loss","top1_accuracy")},
        "pairwise_week_block_bootstrap":week_ci(
            valid,preds["CATBOOST_RESEARCH_NO_XG"],
            preds["CATBOOST_RESEARCH_PLUS_XG_WITH_MISSING"]),
        "target_score_never_a_feature":True,
        "original_historical_provider_first_published_certified":False,
        "asof_v2_formal_training_or_validation":False,
        "forward_prospective_paired_comparison":False,
        "m0_production_comparison_authorized":False,
        "original_catboost_M1R_85_feature_weights_reused":False,
        "model_bins_archived_only_in_private_CI":True,
        "model_champion_auto_promoted":False,
        "official_fit_increment":0,
        "gate16":"PENDING","gate17":"PENDING"}
    report["report_sha256"]=hash_json(report)
    # The original 1007/376 report and Shadow Six binary are immutable
    # prior research. Name every new experiment by its actual cohort sizes.
    report_file=(outdir/("RETRO_CATBOOST_%d_%d_REPORT.json" %
                         (len(train),len(valid))))
    report_file.write_text(
        json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print("KB3_RETRO_RESEARCH_TRAIN_RESULT",json.dumps({
        "train":len(train),"validation":len(valid),
        "nonxg":base,"withxg":with_xg,
        "xg_delta":report["xg_minus_no_xg_delta"],
        "week_ci":report["pairwise_week_block_bootstrap"],
        "report_sha256":report["report_sha256"],
        "formal_pit":False},sort_keys=True))
    return report


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",type=Path,required=True)
    a=p.parse_args()
    execute(a.outdir)


if __name__=="__main__":
    main()
