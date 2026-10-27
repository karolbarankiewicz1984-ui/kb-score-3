"""KB Score 3.0 M1 independent 1/X/2 probability mathematics.

No implicit alphabetical class mapping, no odds. A forecast is never mutated.
For real future deployment, frozen records MUST be authenticated independently
at capture time; a later self-hash alone DOES NOT prove a prematch freeze.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math

CLASSES=("1","X","2")
EPS=1e-15

class M1MathError(ValueError):pass

def strict_utc(stamp):
    if type(stamp) is not str:
        raise M1MathError("UTC_REQUIRED")
    try:
        d=datetime.fromisoformat(stamp.replace("Z","+00:00"))
    except ValueError as exc:
        raise M1MathError("INVALID_UTC") from exc
    if d.tzinfo is None or d.utcoffset().total_seconds()!=0:
        raise M1MathError("UTC_REQUIRED")
    return d.astimezone(timezone.utc)

def order_probability(probability_by_class):
    if type(probability_by_class) is not dict or set(probability_by_class)!=set(CLASSES):
        raise M1MathError("CLASS_ORDER_OR_KEYS_CHANGED")
    result=[]
    for label in CLASSES:
        value=probability_by_class[label]
        if type(value) not in (float,int) or not math.isfinite(value) or value<0 or value>1:
            raise M1MathError("INVALID_PROBABILITY")
        result.append(float(value))
    if abs(sum(result)-1)>1e-8:
        raise M1MathError("NOT_A_PROBABILITY_SIMPLEX")
    return result

def stable_softmax(logits):
    if len(logits)!=3 or any(type(x) not in (float,int) or not math.isfinite(x) for x in logits):
        raise M1MathError("INVALID_LOGITS")
    shift=max(logits)
    weights=[math.exp(float(x)-shift) for x in logits]
    den=sum(weights)
    return [x/den for x in weights]

def temperature_probabilities(probability_by_class,temperature):
    p=order_probability(probability_by_class)
    if type(temperature) not in (float,int) or not math.isfinite(temperature) or not 0.1<=temperature<=10:
        raise M1MathError("INVALID_TEMPERATURE")
    return dict(zip(CLASSES,stable_softmax([math.log(max(q,EPS))/float(temperature) for q in p])))

def score_one(p,label):
    q=order_probability(p)
    if label not in CLASSES:raise M1MathError("INVALID_LABEL")
    ix=CLASSES.index(label)
    loss=-math.log(max(q[ix],EPS))
    br=sum((q[i]-(1.0 if i==ix else 0.0))**2 for i in range(3))
    # Multiclass Brier sum3 in [0,2] (we DO NOT divide by 3).
    return loss,br

def score_predictions(predictions,labels):
    if not predictions or len(predictions)!=len(labels):
        raise M1MathError("NO_PAIRED_PREDICTIONS")
    logs=[];briers=[];bins=[[0,0.0,0] for _ in range(10)]
    correct=0
    for p,y in zip(predictions,labels):
        ll,bs=score_one(p,y);logs.append(ll);briers.append(bs)
        q=order_probability(p)
        argmax=max(range(3),key=lambda i:q[i])
        won=int(CLASSES[argmax]==y)
        correct+=won
        confidence=q[argmax]
        b=bins[min(9,int(confidence*10))]
        b[0]+=1;b[1]+=confidence;b[2]+=won
    n=len(logs)
    table=[{"bin":j,"count":v[0],"mean_confidence":v[1]/v[0],
            "observed_top1_accuracy":v[2]/v[0]} for j,v in enumerate(bins) if v[0]]
    ece=sum(r["count"]/n*abs(r["mean_confidence"]-r["observed_top1_accuracy"]) for r in table)
    return {"n":n,"log_loss":sum(logs)/n,"brier_sum3":sum(briers)/n,
            "top1_accuracy":correct/n,"top1_ece_10bins":ece,"reliability_top1":table}

def fit_temperature(calibration_predictions,calibration_labels,*,min_rows=10,
                    temperatures=(0.7,0.85,1.0,1.15,1.4,1.8,2.2)):
    if not calibration_predictions or len(calibration_predictions)!=len(calibration_labels) or len(calibration_labels)<min_rows:
        raise M1MathError("NOT_ENOUGH_PAST_CALIBRATION_RESULTS")
    if 1.0 not in temperatures or any(t<=0 for t in temperatures):
        raise M1MathError("UNSAFE_TEMPERATURE_GRID")
    raw=score_predictions(calibration_predictions,calibration_labels)
    trials=[]
    for t in temperatures:
        m=score_predictions([temperature_probabilities(p,t) for p in calibration_predictions],calibration_labels)
        trials.append({"temperature":float(t),"log_loss":m["log_loss"]})
    # Prefer neutral 1.0 on exact ties; don't tune to later evaluation rows.
    best=min(trials,key=lambda r:(r["log_loss"],abs(r["temperature"]-1.0)))
    return {"temperature":best["temperature"],
            "calibration_rows":len(calibration_labels),"calibration_log_loss_raw":raw["log_loss"],
            "calibration_log_loss_fitted":best["log_loss"],
            "grid":trials,"frozen_before_evaluation":True,
            "production_approved":False}

def evaluate_calibrated_holdout(predictions,labels,fit):
    raw=score_predictions(predictions,labels)
    post=score_predictions([temperature_probabilities(p,fit["temperature"]) for p in predictions],labels)
    return {"raw":raw,"calibrated":post,"calibrated_minus_raw_log_loss":post["log_loss"]-raw["log_loss"],
            "calibrated_minus_raw_brier_sum3":post["brier_sum3"]-raw["brier_sum3"],
            "recommend_automatic_production_activation":False}

def freeze_forecast(*,forecast_id,kickoff_utc,frozen_at_utc,model_version,variant,probabilities):
    if (not isinstance(forecast_id,str) or not forecast_id or
        not isinstance(model_version,str) or not model_version or
        variant not in ("NO_XG","WITH_XG_MASKS")):
        raise M1MathError("INVALID_FREEZE_ID_OR_MODEL")
    if strict_utc(frozen_at_utc)>=strict_utc(kickoff_utc):
        raise M1MathError("FORECAST_NOT_BEFORE_KICKOFF")
    order_probability(probabilities)
    record={"schema":"kb3-m1-frozen-probabilities-v1","forecast_id":forecast_id,
            "kickoff_utc":kickoff_utc,"frozen_at_utc":frozen_at_utc,
            "model_version":model_version,"variant":variant,
            "probabilities":dict(probabilities)}
    record["sha256"]=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return record

def audit_frozen_settlements(forecasts,settlements,*,cutoff_utc):
    """Prepare strictly historic settlement pairs for FUTURE calibration.

    An append-only external ledger must attest genuine freeze/settlement times.
    This pure checker prevents mathematical lookahead but does NOT verify
    external ledger timestamps / identities cryptographically.
    """
    cutoff=strict_utc(cutoff_utc)
    if not isinstance(forecasts,list) or not isinstance(settlements,list):
        raise M1MathError("INVALID_LEDGER")
    byid={}
    for row in forecasts:
        if type(row) is not dict or set(row)!={"schema","forecast_id","kickoff_utc","frozen_at_utc","model_version","variant","probabilities","sha256"}:
            raise M1MathError("INVALID_FROZEN_RECORD")
        original={k:v for k,v in row.items() if k!="sha256"}
        if (row["schema"]!="kb3-m1-frozen-probabilities-v1" or
            row["sha256"]!=hashlib.sha256(json.dumps(original,sort_keys=True,separators=(",",":")).encode()).hexdigest()):
            raise M1MathError("FROZEN_RECORD_CHANGED")
        frozen=freeze_forecast(**{k:original[k] for k in ("forecast_id","kickoff_utc","frozen_at_utc","model_version","variant","probabilities")})
        if frozen!=row or row["forecast_id"] in byid:
            raise M1MathError("DUPLICATE_OR_INVALID_FROZEN_FORECAST")
        byid[row["forecast_id"]]=row
    seen=set();pairs=[]
    for item in settlements:
        if type(item) is not dict or set(item)!={"forecast_id","settled_at_utc","label_1x2"}:
            raise M1MathError("UNKNOWN_OR_MISSING_SETTLEMENT_FIELDS")
        key=item["forecast_id"]
        if key not in byid or key in seen or item["label_1x2"] not in CLASSES:
            raise M1MathError("UNKNOWN_DUPLICATE_OR_BAD_SETTLEMENT")
        seen.add(key)
        forecast=byid[key]
        kickoff=strict_utc(forecast["kickoff_utc"])
        if not kickoff<strict_utc(item["settled_at_utc"])<cutoff:
            raise M1MathError("FUTURE_OUTCOME_ENTERED_BEFORE_OR_AFTER_CUTOFF")
        if strict_utc(forecast["frozen_at_utc"])>=kickoff:
            raise M1MathError("PREDICTION_FROM_FUTURE")
        pairs.append((forecast,item))
    pairs.sort(key=lambda x:(x[0]["kickoff_utc"],x[0]["forecast_id"]))
    return pairs
