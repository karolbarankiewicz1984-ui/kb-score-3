"""KB Score 3.0 Step17: fair, paired, cluster-uncertainty engine comparison.

Research only. Never retrain or choose a Champion on historical 374 VAL.
Inputs must be independently attested or explicitly labelled reconstructed.
The scorer does NOT certify evidence flags; the source auditor must do that.
No external imports, paid APIs, protected Premier League TEST or model fitting.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime, timezone, timedelta
import hashlib,json,math,random

ENGINES=("ELO_ONLY","M0_ELO_POISSON_720TRAIN","CATBOOST_NO_XG",
         "CATBOOST_WITH_XG","ENSEMBLE")
LABELS=("1","X","2")
MIN_FUTURE_PAIRED=100
MIN_BLOCKS=8
class Step17Error(ValueError): pass
def check(ok,msg):
    if not ok:raise Step17Error(msg)
def utc(t):
    check(isinstance(t,str),"UTC_STRING_REQUIRED")
    check(t.endswith("Z"),"UTC_Z_REQUIRED")
    try: dt=datetime.fromisoformat(t.replace("Z","+00:00"))
    except ValueError as e:raise Step17Error("INVALID_UTC_TIME") from e
    check(dt.utcoffset()==timedelta(0),"UTC_OFFSET_NOT_ALLOWED")
    return dt
def hash_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
        separators=(",",":"),allow_nan=False).encode()).hexdigest()
def prob(p):
    check(isinstance(p,dict) and set(p)==set(LABELS),"INVALID_1X2_LABELS")
    check(all(type(p[k]) in (int,float) and math.isfinite(p[k])
              and 0<p[k]<1 for k in LABELS),"INVALID_1X2_VALUES")
    check(abs(sum(p.values())-1)<1e-9,"NON_NORMALIZED_PROBABILITY")
    return p
def loss(p,label):
    prob(p)
    check(label in LABELS,"UNKNOWN_RESULT")
    return (-math.log(p[label]),sum(
      (p[c]-(1.0 if c==label else 0.0))**2 for c in LABELS),
      int(max(LABELS,key=lambda c:p[c])==label))
def metric(rows,engine):
    if not rows:return None
    items=[(row["predictions"][engine]["p_1x2"],row["outcome_1x2"]) for row in rows]
    scores=[loss(p,y) for p,y in items]
    conf=[max(p.values()) for p,y in items]
    bins=defaultdict(list)
    for (p,y),c in zip(items,conf):
        b=min(4,int(c*5))
        bins[b].append((c,int(max(p,key=p.get)==y)))
    return {"n":len(items),
        "log_loss":sum(t[0] for t in scores)/len(items),
        "brier_sum3":sum(t[1] for t in scores)/len(items),
        "top1_accuracy":sum(t[2] for t in scores)/len(items),
        "top1_ece_5_bins":sum(len(vals)/len(items)*
            abs(sum(v[0] for v in vals)/len(vals)
              -sum(v[1] for v in vals)/len(vals))
            for vals in bins.values())}

def check_payload(payload):
    check(isinstance(payload,dict) and set(payload)>={
        "schema","evaluation_domain","market","horizon","games","candidate_versions"},
        "MISSING_REQUIRED_BENCHMARK_FIELDS")
    check(payload["schema"]=="kb3-step17-paired-engine-input-v1","INPUT_SCHEMA_WRONG")
    check(payload["evaluation_domain"] in (
        "HISTORICAL_RECONSTRUCTED_RESEARCH","FORWARD_GITHUB_HOST_ATTESTED"),
        "MIXED_OR_UNKNOWN_EVALUATION_DOMAIN")
    check(payload["market"]=="1X2_90MIN","MIXED_MARKETS")
    check(payload["horizon"]=="EARLY_90MIN_OR_MORE","MIXED_HORIZONS")
    versions=payload["candidate_versions"]
    check(isinstance(versions,dict) and set(versions)==set(ENGINES),
          "FIVE_ENGINE_REGISTRY_REQUIRED")
    for e,v in versions.items():
        if v is not None:
            check(isinstance(v,str) and len(v)>=8,
                  "UNVERSIONED_PREDICTOR_"+e)
    games=payload["games"]
    check(isinstance(games,list),"GAMES_LIST_REQUIRED")
    check(not payload.get("protected_test_opened",False),
          "PROTECTED_TEST_CANNOT_BE_EVALUATED")
    seen=set();excluded=Counter();validated=[]
    for row in games:
        check(isinstance(row,dict) and set(row)>={
            "fixture_id","league","kickoff_utc","outcome_1x2",
            "result_observed_utc","predictions"},"GAME_FIELDS_MISSING")
        ident=(row["league"],row["fixture_id"])
        check(ident not in seen,"DUPLICATE_FIXTURE")
        seen.add(ident)
        check(row["league"] in ("ESP","ITA","GER","FRA","NED",
                                "BEL","TUR","POL","ENG_HISTORICAL"),
              "UNAPPROVED_LEAGUE")
        if payload["evaluation_domain"]=="FORWARD_GITHUB_HOST_ATTESTED":
            check(row["league"]!="ENG_HISTORICAL","PROTECTED_ENGLISH_TEST")
        check(isinstance(row["fixture_id"],str) and row["fixture_id"],
              "INVALID_FIXTURE_ID")
        check(row["outcome_1x2"] in LABELS,"INVALID_GAME_LABEL")
        k=utc(row["kickoff_utc"])
        observed=utc(row["result_observed_utc"])
        check(observed>=k+timedelta(hours=3),
              "RESULT_NOT_POSTMATCH")
        preds=row["predictions"]
        check(isinstance(preds,dict) and set(preds)<=set(ENGINES),
              "UNKNOWN_ENGINE_PREDICTION")
        for e,p in preds.items():
            check(versions[e] is not None,"UNREGISTERED_MODEL_VERSION")
            check(isinstance(p,dict) and set(p)>={
                "p_1x2","frozen_at_utc","model_version","horizon"},
                "FORECAST_RECORD_INCOMPLETE")
            check(p["model_version"]==versions[e],
                  "MIXED_MODEL_VERSIONS")
            check(p["horizon"]==payload["horizon"],
                  "MISMATCHED_PREMATCH_HORIZON")
            check(utc(p["frozen_at_utc"])<=k-timedelta(minutes=90),
                  "LATE_PREDICTION")
            prob(p["p_1x2"])
            if payload["evaluation_domain"]=="FORWARD_GITHUB_HOST_ATTESTED":
                check(p.get("github_server_artifact_verified") is True
                      and p.get("forecast_hash_verified") is True,
                      "FORWARD_WITHOUT_EXTERNAL_ATTESTATION")
            else:
                check(p.get("source_class")=="B_RECONSTRUCTED",
                      "HISTORICAL_SOURCE_NOT_DISCLOSED")
        validated.append(row)
    return validated

def paired_ci(rows,left,right,metric_name,*,replicates=1200,seed=20261029):
    """Same-game paired bootstrap, resampling whole ISO weeks, not outcomes independently."""
    check(metric_name in ("log_loss","brier_sum3","top1_accuracy"),
          "UNKNOWN_METRIC")
    check(type(replicates) is int and 100<=replicates<=10000,"BOOTSTRAP_REPS")
    values=defaultdict(list)
    for g in rows:
        week=utc(g["kickoff_utc"]).isocalendar()
        key=f"{week.year}-W{week.week:02d}"
        p=g["predictions"]
        a=loss(p[left]["p_1x2"],g["outcome_1x2"])
        b=loss(p[right]["p_1x2"],g["outcome_1x2"])
        idx={"log_loss":0,"brier_sum3":1,"top1_accuracy":2}[metric_name]
        values[key].append(a[idx]-b[idx])
    blocks=sorted(values)
    if len(blocks)<MIN_BLOCKS:
        return {"n":len(rows),"week_blocks":len(blocks),"ci95":None,
                "status":"INSUFFICIENT_INDEPENDENT_WEEKS"}
    d=sum(sum(v) for v in values.values())/len(rows)
    rng=random.Random(seed)
    simulated=[]
    for _ in range(replicates):
        picked=[values[rng.choice(blocks)] for i in blocks]
        simulated.append(sum(sum(v) for v in picked)/
                         sum(len(v) for v in picked))
    simulated.sort()
    lo=simulated[int((replicates-1)*0.025)]
    hi=simulated[int((replicates-1)*0.975)]
    return {"n":len(rows),"week_blocks":len(blocks),
            "delta_left_minus_right":d,"ci95":[lo,hi],
            "negative_favors_left_for_loss":metric_name!="top1_accuracy",
            "interval_excludes_zero":lo>0 or hi<0,
            "status":"PAIRED_ISO_WEEK_BOOTSTRAP"}

def compare(payload,*,replicates=1200):
    games=check_payload(payload)
    count=len(games)
    supported={e:[g for g in games if e in g["predictions"]] for e in ENGINES}
    missing={}
    for e in ENGINES:
        byleague=Counter(g["league"] for g in supported[e])
        missing[e]={"available_unique":len(supported[e]),
                    "missing_unique":count-len(supported[e]),
                    "coverage":(len(supported[e])/count if count else 0.),
                    "per_league":dict(sorted(byleague.items())),
                    "why_unavailable":("NO_FROZEN_PREDICTIONS" if not supported[e]
                                       else "SOME_GAMES_WITHOUT_PREDICTIONS" if len(supported[e])<count
                                       else None)}
    rows=[g for g in games if all(e in g["predictions"]
                                  for e in ENGINES if payload["candidate_versions"][e] is not None)]
    # Strict all-five fairness is a GATE17 condition; pairwise diagnostic can
    # still be computed when just two models are ready.
    complete_five=[g for g in games if all(e in g["predictions"] for e in ENGINES)]
    pairwise={}
    for i,left in enumerate(ENGINES):
        for right in ENGINES[i+1:]:
            pair=[g for g in games if left in g["predictions"] and
                                       right in g["predictions"]]
            k=left+"__vs__"+right
            pairwise[k]={"common_n":len(pair),
                "left":metric(pair,left),"right":metric(pair,right),
                "deltas":{metric_name:paired_ci(pair,left,right,metric_name,
                           replicates=replicates)
                           for metric_name in ("log_loss","brier_sum3","top1_accuracy")}
                           if pair else {}}
    # Exact three-engine intersection, never marginal pairwise counts.
    trio=("ELO_ONLY","M0_ELO_POISSON_720TRAIN","CATBOOST_NO_XG")
    triplets=[g for g in games if all(e in g["predictions"] for e in trio)]
    triplet_leagues={}
    for league in sorted({g["league"] for g in triplets}):
        group=[g for g in triplets if g["league"]==league]
        triplet_leagues[league]={"common_n":len(group),
            "scores":{e:metric(group,e) for e in trio}}
    triplet_pairs={}
    for i,left in enumerate(trio):
        for right in trio[i+1:]:
            triplet_pairs[left+"__vs__"+right]={
                "common_n":len(triplets),
                "deltas":{m:paired_ci(triplets,left,right,m,replicates=replicates)
                          for m in ("log_loss","brier_sum3","top1_accuracy")}
                          if triplets else {}}
    triplet_summary={"common_n":len(triplets),
        "scores":{e:metric(triplets,e) for e in trio},
        "per_league":triplet_leagues,
        "paired_deltas":triplet_pairs,
        "scope":"SAME_EXACT_THREE_ENGINE_FIXTURES_ONLY",
        "research_only":True,"winner_auto_selected":False}
    return {"schema":"kb3-step17-engine-comparison-readiness-v1",
            "evaluation_domain":payload["evaluation_domain"],
            "market":payload["market"],"horizon":payload["horizon"],
            "candidate_versions":payload["candidate_versions"],
            "unique_fixtures":count,"full_five_common_fixtures":len(complete_five),
            "exact_three_engine_comparison":triplet_summary,
            "missing_data_cost":missing,
            "fair_same_game_pairwise":pairwise,
            "all_five_common_scores":{e:metric(complete_five,e) for e in ENGINES},
            "research_historical_not_forward_certified":
                payload["evaluation_domain"]=="HISTORICAL_RECONSTRUCTED_RESEARCH",
            "production_model_changed":False,"sealed_test_accessed":False,
            "winner_auto_selected":False,
            "enough_for_formal_step17":False, # requires GATE16 and separate forward windows
            "gate16_completed_evidence_supplied":False,
            "gate17":"PENDING_STEP16_AND_FULL_FAIR_BENCHMARK",
            "input_sha256":hash_json(payload)}
