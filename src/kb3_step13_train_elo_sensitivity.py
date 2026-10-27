"""Step13 research diagnostic. Poisson goal profile on TRAIN only, not PIT or 1X2 validation.

No API calls, no odds, no TEST, no production parameter updates.
The wider grid is exploratory; the original 0.0..0.6 model is unchanged.
"""
import math
from src.kb3_split import sha, timestamp
from src.kb3_step13_retrospective import _validate, _historical_states

ORIGINAL_GRID=tuple(i/10 for i in range(7))
DIAGNOSTIC_GRID=tuple(i/10 for i in range(13))
START="2023-07-01T00:00:00Z"
MIDDLE="2024-07-01T00:00:00Z"
END="2025-07-01T00:00:00Z"
SAFE_SHA="3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7"


def profile(samples, grid=DIAGNOSTIC_GRID):
    if not isinstance(samples,list) or len(samples)<8:
        raise ValueError("STEP13_INSUFFICIENT_TRAIN")
    if grid!=DIAGNOSTIC_GRID:
        raise ValueError("STEP13_GRID_LOCKED")
    if any(type(d) not in (float,int) or not math.isfinite(d) or
           type(h) is not int or type(a) is not int or
           not(0<=h<=30 and 0<=a<=30) for d,h,a in samples):
        raise ValueError("STEP13_BAD_TRAIN_GOAL_OR_ELO")
    nh=sum(h for _,h,_ in samples); na=sum(a for _,_,a in samples)
    if nh<=0 or na<=0:
        raise ValueError("STEP13_DEGENERATE_TRAIN")
    result=[]
    for e in grid:
        eh=[math.exp(e*d) for d,_,_ in samples]
        ea=[math.exp(-e*d) for d,_,_ in samples]
        bh=nh/math.fsum(eh); ba=na/math.fsum(ea)
        if not (0.01<=bh<=5 and 0.01<=ba<=5):
            raise ValueError("STEP13_BAD_MLE_INTERCEPT")
        terms=[]
        for (d,h,a),sh,sa in zip(samples,eh,ea):
            lh=bh*sh; la=ba*sa
            if not (1e-6<=lh<=8 and 1e-6<=la<=8):
                raise ValueError("STEP13_BAD_MLE_EXPOSURE")
            terms.append(lh-h*math.log(lh)+math.lgamma(h+1)
                         +la-a*math.log(la)+math.lgamma(a+1))
        nll=math.fsum(terms)
        result.append({"elasticity":round(e,1),"train_goal_nll":nll,
                       "train_goal_nll_mean":nll/len(samples),
                       "train_base_home_goals":bh,"train_base_away_goals":ba})
    return result


def diagnose(rows, safe, retrieval_time):
    if timestamp(retrieval_time)<=timestamp(END):
        raise ValueError("STEP13_RETROSPECTIVE_RETRIEVAL_INVALID")
    if (safe.get("projection_sha256")!=SAFE_SHA or
        safe.get("training_allowed") is not False or
        safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380}):
        raise ValueError("STEP13_FROZEN_SPLIT_CHANGED")
    fixtures=safe["fixtures"]
    if len(fixtures)!=1520:
        raise ValueError("STEP13_SPLIT_LENGTH_CHANGED")
    train={f["fixture_id"]:f for f in fixtures if f["partition"]=="TRAIN"}
    if len(train)!=760 or not isinstance(rows,list) or len(rows)!=760:
        raise ValueError("STEP13_TRAIN_ONLY_REQUIRED")
    checked=_validate(rows)
    if any(r["_role"]!="TRAIN" or
           r["fixture_id"] not in train or
           timestamp(r["kickoff_utc"])!=timestamp(train[r["fixture_id"]]["kickoff_utc"])
           for r in checked):
        raise ValueError("STEP13_VALIDATION_OR_TEST_FORBIDDEN")
    if {r["fixture_id"] for r in checked}!=set(train):
        raise ValueError("STEP13_TRAIN_IDS_NOT_COMPLETE")
    _,first=_historical_states(checked,boundary=timestamp(MIDDLE),lower=timestamp(START))
    _,all_train=_historical_states(checked,boundary=timestamp(END),lower=timestamp(START))
    if len(first)!=380 or len(all_train)!=760 or all_train[:380]!=first:
        raise ValueError("STEP13_TRAIN_TIME_GUARD_FAILED")
    profiles={"TRAIN_760":profile(all_train),"TRAIN_2023_24":profile(first),
              "TRAIN_2024_25":profile(all_train[380:])}
    def best(values):
        return min(values,key=lambda row:(row["train_goal_nll"],row["elasticity"]))
    original=best(profiles["TRAIN_760"][:7])
    widened=best(profiles["TRAIN_760"])
    out={"schema":"kb3-step13-real-train-only-elo-sensitivity-v0.7",
         "source_type":"RETROSPECTIVE_TRAIN_RESEARCH_NOT_PIT",
         "source_observed_at_utc":retrieval_time,
         "simulated_lag_hours":48,
         "input_digest_sha256":sha(rows),
         "safe_view_sha256":SAFE_SHA,
         "train_rows":760,"validation_rows_read":0,"test_rows_read":0,
         "original_model_grid":list(ORIGINAL_GRID),
         "exploratory_train_only_grid":list(DIAGNOSTIC_GRID),
         "profile_metric":"POISSON_TWO_GOAL_TRAIN_NLL_NOT_1X2_LOGLOSS",
         "profiles":profiles,
         "original_grid_best_train_elasticity":original["elasticity"],
         "diagnostic_grid_best_train_elasticity":widened["elasticity"],
         "train_nll_difference_original_minus_diagnostic":
             original["train_goal_nll"]-widened["train_goal_nll"],
         "no_validation_in_grid_choice":True,
         "existing_model_parameters_unchanged":True,
         "retrospective_not_observed_asof":True,
         "training_allowed":False,"gate13_pass":False,
         "production_model_promoted":False}
    out["report_sha256"]=sha(out)
    return out
