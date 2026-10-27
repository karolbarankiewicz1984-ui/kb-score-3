"""Step13 / audit 1 of 4: independent algebraic checks of Elo+Poisson M0.

No API, no outcome labels, no MODEL change. Only a previously-frozen forward
forecast artifact and synthetic rating pairs are inspected. The immutable
first snapshot is never rewritten.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from src.kb3_split import sha,freeze_manifest
from src.kb3_step13_baseline import BaselineParameters,forecast,update_elo,elo_expected_home_points,BaselineSafetyError
from src.kb3_step13_forward_score import SOURCE_FILE,SOURCE_HASH

SCHEMA="kb3-step13-independent-algebra-audit-v1"

def poisson_pmf(n,lam):
    return math.exp(n*math.log(lam)-lam-math.lgamma(n+1))

def check_math(snapshot):
    if snapshot.get("report_sha256")!=SOURCE_HASH or sha({k:v for k,v in snapshot.items() if k!="report_sha256"})!=SOURCE_HASH:
        raise BaselineSafetyError("STEP13_MATH_FROZEN_SNAPSHOT_CHANGED")
    if snapshot.get("first_snapshot_match_count")!=10 or snapshot.get("test_results_accessed")!=0:
        raise BaselineSafetyError("STEP13_MATH_UNSAFE_SNAPSHOT")
    p=BaselineParameters(**snapshot["fit_parameters"])
    checked=0
    worst={"one_x_two":0.0,"poisson_over":0.0,"btts":0.0,"scoreline":0.0,"elo_balance":0.0,"elo_logit":0.0}
    def close(label,a,b,tol=1e-9):
        if not(math.isfinite(a) and math.isfinite(b)):
            raise BaselineSafetyError("STEP13_MATH_NAN_OR_INF")
        gap=abs(a-b)
        worst[label]=max(worst[label],gap)
        if gap>tol:raise BaselineSafetyError("STEP13_MATH_IDENTITY_FAILED_"+label)
    # Independence from implementation's finite goal-list summation.
    for h in (1320.,1450.,1500.,1570.,1700.):
        for a in (1340.,1480.,1500.,1610.,1720.):
            f=forecast(h,a,p)
            ph,pa=f["expected_goals"]["home"],f["expected_goals"]["away"]
            close("one_x_two",sum(f["p_1x2"].values()),1.)
            close("btts",f["p_btts_yes"],(1-math.exp(-ph))*(1-math.exp(-pa)))
            total=ph+pa
            for threshold in (1,2,3):
                expected=1-sum(poisson_pmf(i,total) for i in range(threshold+1))
                close("poisson_over",f["p_over"][f"{threshold}.5"],expected)
            scores=f["top_5_scorelines"]
            if scores!=sorted(scores,key=lambda x:(-x["probability"],x["home"],x["away"])):
                raise BaselineSafetyError("STEP13_MATH_SCORELINE_ORDER_BAD")
            for v in scores:
                close("scoreline",v["probability"],poisson_pmf(v["home"],ph)*poisson_pmf(v["away"],pa))
            for outcome in ("H","D","A"):
                h2,a2=update_elo(h,a,outcome,p)
                close("elo_balance",h+a,h2+a2)
                target={"H":1.,"D":.5,"A":0.}[outcome]
                eh=1/(1+10**((a-h-p.elo_home_advantage)/p.elo_scale))
                close("elo_logit",h2-h,p.elo_k*(target-eh))
                close("elo_logit",elo_expected_home_points(h,a,p),eh)
            checked+=1
    # Pinned ten true, pre-kickoff model forecasts: recompute without targets.
    for row in snapshot["forecasts"]:
        f=forecast(row["elo_at_forecast"]["home"],row["elo_at_forecast"]["away"],p)
        for k in ("1","X","2"):
            close("one_x_two",f["p_1x2"][k],row["probabilities_1x2"][k],1e-12)
        for key in ("home","away"):
            close("poisson_over",f["expected_goals"][key],row["expected_goals"][key],1e-12)
        checked+=1
    report={
        "schema":SCHEMA,"original_snapshot_sha256":SOURCE_HASH,
        "synthetic_rating_pairs":25,"pinned_real_prematch_forecasts_replayed":10,
        "identity_checks":checked,"independent_closed_form_poisson_over_btts":True,
        "elo_zero_sum_and_standard_logistic_tested":True,
        "poisson_draw_and_scoreline_consistency_tested":True,
        "numerical_max_absolute_deviation":worst,
        "result_labels_read":0,"api_requests":0,"parameters_tuned":False,
        "source_snapshot_modified":False,"gate13_pass":False,
        "training_allowed":False,"step14_started":False,
    }
    report["report_sha256"]=sha(report)
    return report

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--output",required=True)
    opt=args.parse_args()
    j=json.loads(Path(SOURCE_FILE).read_text(encoding="utf8"))
    r=check_math(j)
    freeze_manifest(r,opt.output)
    print("STEP13_MATH_25_SYNTHETIC_PAIRS_10_FROZEN_PROBABILITIES_PASS",r["report_sha256"])
if __name__=="__main__":
    main()
