"""KB3 Step18: independent research-only Champion readiness gate.

Strictly consumes audited Step17 same-fixture host-attested comparison.
It cannot approve, replace, fit, or deploy any model. No TEST/odds/API.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SOURCE_SCHEMA="kb3-step17-offline-three-engine-readonly-v1"
SCHEMA="kb3-step18-research-evidence-gate-v1"
MIN_PAIRED=100
MIN_WEEK_BLOCKS=8
PAIRS={
 "ELO_ONLY":("ELO_ONLY__vs__M0_ELO_POISSON_720TRAIN",-1),
 "CATBOOST_NO_XG":("M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG",1),
}

class Gate18Error(ValueError):
    pass

def require(ok,reason):
    if not ok: raise Gate18Error(reason)

def evaluate(report):
    require(type(report) is dict and report.get("schema")==SOURCE_SCHEMA,
            "WRONG_OR_MISSING_STEP17_REPORT")
    require(report.get("source_db_unchanged") is True and
            report.get("no_provider_calls") is True and
            report.get("no_new_forecasts_or_backfill") is True and
            report.get("protected_test_accessed") is False and
            report.get("winner_auto_selected") is False and
            report.get("gate17")=="PENDING",
            "RESEARCH_SOURCE_OR_PROTECTED_TEST_DRIFT")
    require(report.get("performance_claim_allowed") is False and
            isinstance(report.get("source_m0_sha256"),str) and
            len(report["source_m0_sha256"])==64,
            "UNTRUSTED_PERFORMANCE_REPORT")
    pairs=report.get("pairwise_evaluation")
    counts=report.get("pairwise_common_n")
    require(isinstance(pairs,dict) and isinstance(counts,dict),
            "MISSING_SAME_GAME_COMPARISON")
    result={}
    for engine,(key,sign) in PAIRS.items():
        x=pairs.get(key)
        require(isinstance(x,dict) and type(x.get("common_n")) is int
                and x["common_n"]>=0 and x["common_n"]==counts.get(key),
                "PAIRWISE_COUNT_DRIFT_"+engine)
        n=x["common_n"]
        intervals={}
        blocked=[]
        if n<MIN_PAIRED:blocked.append("NOT_ENOUGH_PAIRED_GAMES")
        # P1-01: M1-R TRAIN reconstructs feature availability at kickoff
        # after 48h result maturation; live challengers use a source
        # snapshot cutoff and 3h maturity. Identical column names do NOT
        # prove point-in-time semantic parity. No Champion evidence until
        # independent before-kickoff parity audit accepts a NEW version.
        if engine=="CATBOOST_NO_XG":
            blocked.append("P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS")

        for metric in ("brier_sum3","log_loss"):
            ci=(x.get("deltas") or {}).get(metric)
            if not isinstance(ci,dict):
                blocked.append("MISSING_PAIRED_"+metric.upper()+"_CI")
                intervals[metric]=None
                continue
            require(ci.get("n")==n and type(ci.get("week_blocks")) is int,
                    "PAIRED_CI_SAMPLE_DRIFT_"+metric)
            bounds=ci.get("ci95")
            if ci["week_blocks"]<MIN_WEEK_BLOCKS:
                blocked.append("TOO_FEW_INDEPENDENT_WEEKS")
                intervals[metric]=None
                continue
            require(isinstance(bounds,list) and len(bounds)==2 and
                    all(type(q) in (int,float) and -10<q<10 for q in bounds)
                    and bounds[0]<=bounds[1],"INVALID_CI_"+metric)
            intervals[metric]=bounds
            # sign=-1: left challenger must beat right M0 -> interval upper <0
            # sign=+1: right challenger must beat left M0 -> interval lower >0
            beats=(bounds[1]<0 if sign==-1 else bounds[0]>0)
            if not beats: blocked.append("NO_CLEAR_"+metric.upper()+"_IMPROVEMENT")
        result[engine]={
          "same_fixture_settled_n":n,
          "paired_ci95":intervals,
          "research_statistical_signal_only":not blocked,
          "blocked_reasons":sorted(set(blocked)),
          "requires_later_out_of_sample_confirmatory_test":True,
          "eligible_for_champion_automatic_promotion":False,
        }
    return {
      "schema":SCHEMA,
      "model_family":"KB_SCORE_3_0",
      "source_m0_sha256":report["source_m0_sha256"],
      "minimum_same_fixture_paired_n":MIN_PAIRED,
      "minimum_independent_ISO_weeks":MIN_WEEK_BLOCKS,
      "gate16_finished_and_independently_accepted":False,
      "gate17_finished_and_independently_accepted":False,
      "candidate_diagnostics":result,
      "ready_for_human_champion_decision":False,
      "candidate_deployment_authorized":False,
      "new_model_fit_or_calibration":False,
      "winner_chosen":False,
      "protected_english_test_opened":False,
      "formal_step18":"PENDING_16_17_AND_OWNER_APPROVAL",
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    p=Path(args.out)
    require(not p.exists(),"RESEARCH_GATE_REPORT_ALREADY_EXISTS")
    source=json.loads(Path(args.input).read_text(encoding="utf-8"))
    report=evaluate(source)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"schema":SCHEMA,"gate":report["formal_step18"],
      "candidates":{k:v["blocked_reasons"] for k,v in report["candidate_diagnostics"].items()}},
      sort_keys=True))

if __name__=="__main__":
    main()
