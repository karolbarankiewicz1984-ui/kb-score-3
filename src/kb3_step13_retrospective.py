"""KB3 Step13: explicitly RETROSPECTIVE event-time research, never PIT evidence.

Pure offline math: predicts before reading each target outcome, updating Elo
from a *hypothetical* kickoff+48h delay. This is not observed_at: PitchAPI
was actually retrieved in October 2026. Never train on or inspect TEST.

Full research must be called by the separate trusted-local archive runner:
cryptographically verified encrypted input with pinned real source receipts.
There is no network, odds, xG, user secrets or mutation in this module.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, replace
from datetime import timedelta
import heapq
import math

from src.kb3_split import WALK_FORWARD, WINDOWS, timestamp, sha, SplitSafetyError
from src.kb3_step13_baseline import (
    BaselineParameters, BaselineSafetyError, update_elo, forecast,
)
from src.kb3_step13_poisson_train import FIXED_GRID

POLICY = "RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT"
LAG = timedelta(hours=48)
MIN_FIT_ROWS = 8
KEYS = frozenset(("fixture_id","home_team_id","away_team_id",
                  "kickoff_utc","goals_home_90","goals_away_90"))


def _validate(rows):
    if not isinstance(rows,list) or not rows:
        raise BaselineSafetyError("STEP13_RESEARCH_ROWS_MISSING")
    seen=set()
    accepted=[]
    for r in rows:
        if not isinstance(r,dict) or set(r)!=KEYS:
            raise BaselineSafetyError("STEP13_RESEARCH_SCHEMA_OR_ODDS_TAINT")
        ident=r["fixture_id"]
        h,a=r["home_team_id"],r["away_team_id"]
        if (not isinstance(ident,str) or not ident or ident in seen
                or not isinstance(h,str) or not h
                or not isinstance(a,str) or not a or h==a):
            raise BaselineSafetyError("STEP13_RESEARCH_IDS_INVALID")
        seen.add(ident)
        ko=timestamp(r["kickoff_utc"])
        role=next((name for name,start,stop in WINDOWS
                   if timestamp(start)<=ko<timestamp(stop)),"OUT")
        if role not in ("TRAIN","VALIDATION"):
            raise BaselineSafetyError("STEP13_RESEARCH_TEST_AND_OUT_OF_SCOPE_DENIED")
        gh,ga=r["goals_home_90"],r["goals_away_90"]
        if any(type(n) is not int or not 0<=n<=30 for n in (gh,ga)):
            raise BaselineSafetyError("STEP13_RESEARCH_GOALS_INVALID")
        accepted.append({**r,"_date":ko,"_role":role})
    return sorted(accepted,key=lambda r:(r["_date"],r["fixture_id"]))


def _historical_states(checked, *, boundary, lower):
    """Fixed fold-start input: outcome of each earlier game only if 48h elapsed.

    Delayed receipts are simulated for event-time replay, NOT presented as
    actual provenance. Each match is assigned Elo from available prior events.
    """
    p=BaselineParameters()
    pending=[]
    ratings={}
    train=[]
    for match in checked:
        ko=match["_date"]
        if ko>=boundary:
            break
        if ko<lower:
            # Rolling must exclude older matches for Elo too, not just fit.
            continue
        while pending and pending[0][0]<ko:
            _,_,hid,aid,dh,da=heapq.heappop(pending)
            ratings[hid]=ratings.get(hid,p.initial_elo)+dh
            ratings[aid]=ratings.get(aid,p.initial_elo)+da
        hid,aid=match["home_team_id"],match["away_team_id"]
        pre_h=ratings.get(hid,p.initial_elo)
        pre_a=ratings.get(aid,p.initial_elo)
        gh,ga=match["goals_home_90"],match["goals_away_90"]
        lab="H" if gh>ga else "A" if gh<ga else "D"
        after_h,after_a=update_elo(pre_h,pre_a,lab,p)
        heapq.heappush(pending,(ko+LAG,match["fixture_id"],hid,aid,
                                after_h-pre_h,after_a-pre_a))
        # Targets may be fitted if BOTH event time and conservative lag
        # have elapsed strictly before this quarter starts.
        if lower<=ko and ko+LAG<boundary:
            train.append(((pre_h-pre_a)/p.elo_scale,gh,ga))
    while pending and pending[0][0]<boundary:
        _,_,hid,aid,dh,da=heapq.heappop(pending)
        ratings[hid]=ratings.get(hid,p.initial_elo)+dh
        ratings[aid]=ratings.get(aid,p.initial_elo)+da
    return ratings,train


def _train_poisson(train):
    """Profile MLE over a prefixed TRAIN-only Elo elasticity grid."""
    if len(train)<MIN_FIT_ROWS:
        raise BaselineSafetyError("STEP13_RESEARCH_INSUFFICIENT_TRAIN")
    total_h=sum(gh for _,gh,_ in train)
    total_a=sum(ga for _,_,ga in train)
    if total_h==0 or total_a==0:
        raise BaselineSafetyError("STEP13_RESEARCH_DEGENERATE_GOALS")
    fits=[]
    for elasticity in FIXED_GRID:
        exposures_h=[math.exp(elasticity*d) for d,_,_ in train]
        exposures_a=[math.exp(-elasticity*d) for d,_,_ in train]
        home_rate=total_h/math.fsum(exposures_h)
        away_rate=total_a/math.fsum(exposures_a)
        if not (0.01<=home_rate<=5.0 and 0.01<=away_rate<=5.0):
            continue
        nll=0.0
        for (delta,gh,ga),eh,ea in zip(train,exposures_h,exposures_a):
            lh,la=home_rate*eh,away_rate*ea
            if not (1e-6<=lh<=8 and 1e-6<=la<=8):
                nll=math.inf
                break
            nll+=lh-gh*math.log(lh)+math.lgamma(gh+1)
            nll+=la-ga*math.log(la)+math.lgamma(ga+1)
        if math.isfinite(nll):
            fits.append((nll,elasticity,home_rate,away_rate))
    if not fits:
        raise BaselineSafetyError("STEP13_RESEARCH_NO_FINITE_FIT")
    best=min(fits)
    return replace(BaselineParameters(),
                   elo_goal_elasticity=best[1],
                   base_home_goals=best[2],base_away_goals=best[3])


def _eval(predictions, labels):
    if len(predictions)!=len(labels) or not predictions:
        raise BaselineSafetyError("STEP13_RESEARCH_INCOMPLETE_TARGETS")
    sum_ll=sum_brier=0.0
    bins=[{"n":0,"confidence_sum":0.0,"hits":0} for _ in range(5)]
    for prob,lab in zip(predictions,labels):
        selected={"H":"1","D":"X","A":"2"}[lab]
        sum_ll += -math.log(max(prob[selected],1e-15))
        sum_brier += math.fsum(
            (prob[k]-(1.0 if k==selected else 0.0))**2
            for k in ("1","X","2"))
        top=max(("1","X","2"),key=lambda k:prob[k])
        c=prob[top]
        bin_=bins[min(4,int(c*5))]
        bin_["n"]+=1
        bin_["confidence_sum"]+=c
        bin_["hits"]+=int(top==selected)
    n=len(labels)
    ece=sum(abs(b["hits"]/b["n"]-b["confidence_sum"]/b["n"])*b["n"]/n
            for b in bins if b["n"])
    return {"n":n,"multiclass_logloss":sum_ll/n,
            "multiclass_brier_sum3":sum_brier/n,
            "top_class_ece_5bin":ece,
            "calibration_bins":[{"n":b["n"],"confidence":b["confidence_sum"]/b["n"] if b["n"] else None,
                                 "accuracy":b["hits"]/b["n"] if b["n"] else None}
                                for b in bins]}


def retrospective_research(rows, *, policy):
    if policy!=POLICY:
        raise BaselineSafetyError("STEP13_RESEARCH_EXPLICIT_POLICY_REQUIRED")
    checked=_validate(rows)
    by_role=Counter(r["_role"] for r in checked)
    if by_role["TRAIN"]<MIN_FIT_ROWS or by_role["VALIDATION"]==0:
        raise BaselineSafetyError("STEP13_RESEARCH_MISSING_PARTITIONS")
    # No result from held-out TEST enters the function, even as an unused row.
    folds=[]
    for i,(start_text,end_text) in enumerate(WALK_FORWARD,1):
        start,end=timestamp(start_text),timestamp(end_text)
        targets=[r for r in checked if start<=r["_date"]<end]
        if not targets:
            continue
        per_method={}
        for method in ("EXPANDING","ROLLING_24_CALENDAR_MONTHS"):
            lower=(timestamp(WINDOWS[0][1]) if method=="EXPANDING"
                   else start.replace(year=start.year-2))
            ratings,train=_historical_states(checked,boundary=start,lower=lower)
            p=_train_poisson(train)
            # Predictions are frozen for entire quarter using only TRAIN.
            frozen=[]
            for t in targets:
                h=ratings.get(t["home_team_id"],p.initial_elo)
                a=ratings.get(t["away_team_id"],p.initial_elo)
                probabilities=forecast(h,a,p)["p_1x2"]
                frozen.append(probabilities)
            # Outcomes read only once ALL predictions have been made.
            labels=["H" if t["goals_home_90"]>t["goals_away_90"] else
                    "A" if t["goals_home_90"]<t["goals_away_90"] else "D"
                    for t in targets]
            metric=_eval(frozen,labels)
            per_method[method]={
                "training_rows":len(train),
                "fitted_parameters":asdict(p),
                "metrics":metric,
                "validation_fixture_ids_sha256":sha([t["fixture_id"] for t in targets]),
                "parameters_frozen_before_validation":True,
                "validation_labels_used_for_fitting":False,
            }
        folds.append({"fold":i,"validation_from_utc":start_text,
                      "validation_to_exclusive_utc":end_text,
                      "validation_count":len(targets),"methods":per_method})
    if not folds:
        raise BaselineSafetyError("STEP13_RESEARCH_NO_VALIDATION_FOLDS")
    # Aggregate weighted metrics, never choose champion from synthetic or
    # unverified history and never touch the held-out TEST.
    overall={}
    for method in ("EXPANDING","ROLLING_24_CALENDAR_MONTHS"):
        n=sum(f["validation_count"] for f in folds)
        overall[method]={"validation_n":n}
        for name in ("multiclass_logloss","multiclass_brier_sum3","top_class_ece_5bin"):
            # Fold-weighted ECE is descriptive; global ECE requires pooled bins.
            overall[method][name+"_fold_weighted"]=sum(
                f["methods"][method]["metrics"][name]*f["validation_count"]
                for f in folds)/n
    return {
        "schema":"kb3-step13-retrospective-event-time-research-v0.4",
        "research_policy":POLICY,
        "event_time_lag_assumption_hours":48,
        "actual_historical_prematch_receipts_certified":False,
        "original_provider_publication_at_matchtime_known":False,
        "training_data_origin":"ARCHIVE_RETRIEVED_AFTER_ALL_TRAIN_AND_VALIDATION_MATCHES",
        "train_partition_rows":by_role["TRAIN"],
        "validation_partition_rows":by_role["VALIDATION"],
        "test_rows_processed":0,
        "match_data_sha256":sha(rows),
        "folds":folds,"overall":overall,
        "produced_real_historical_research_metrics":True,
        "historical_pit_backtest_performed":False,
        "holdout_test_untouched":True,
        "model_production_eligible":False,
        "training_allowed":False,
        "gate13_pass":False,
    }
