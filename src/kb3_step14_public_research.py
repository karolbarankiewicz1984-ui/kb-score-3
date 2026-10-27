"""KB3 Step14 isolated retrospective *research*, NOT PIT certified or production.

Only CC0 OpenFootball Premier League 2023-24, 2024-25 (TRAIN) and
2025-26 (VALIDATION); do not read or download the official 2026-27 TEST.
The independent external dataset does not resolve PitchAPI fixture IDs.
Historical feature availability is HYPOTHETICAL (3 calendar day embargo),
not proof of provider pre-match publication. No xG, odds, bookmaker or API.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import heapq
import json
import math
import tempfile
import urllib.request

SOURCE="https://raw.githubusercontent.com/openfootball/football.json/master/{season}/en.1.json"
TRAIN_SEASONS=("2023-24","2024-25")
VALID_SEASON="2025-26"
SEASONS=TRAIN_SEASONS+(VALID_SEASON,)
FEATURES=("elo_diff_plus_home","home_form5","away_form5","home_form_n","away_form_n")
POLICY="RETROSPECTIVE_RESEARCH_NOT_PIT"
SEED=141027


class ResearchSafetyError(ValueError): pass


def read_public_seasons(fetcher=None):
    if fetcher is None:
        def fetcher(url):
            with urllib.request.urlopen(url,timeout=25) as f:
                return f.read(2_000_000+1)
    data={}
    hashes={}
    for season in SEASONS:
        raw=fetcher(SOURCE.format(season=season))
        if not isinstance(raw,bytes) or not 1000<len(raw)<2_000_000:
            raise ResearchSafetyError("INVALID_SOURCE_BYTES")
        hashes[season]=sha256(raw).hexdigest()
        data[season]=json.loads(raw)
    return data,hashes


def _score(record):
    s=record.get("score")
    if isinstance(s,dict):
        s=s.get("ft")
    if type(s) is not list or len(s)!=2 or any(type(v) is not int or not 0<=v<=30 for v in s):
        raise ResearchSafetyError("INCOMPLETE_INVALID_FT_SCORE")
    return tuple(s)


def load_results(sources):
    if set(sources)!=set(SEASONS):
        raise ResearchSafetyError("SOURCE_SEASONS_CHANGED_TEST_DENIED")
    rows=[]
    for season in SEASONS:
        document=sources[season]
        if type(document) is not dict or type(document.get("matches")) is not list or len(document["matches"])!=380:
            raise ResearchSafetyError("NOT_380_COMPLETED_FIXTURES")
        seen=set()
        for game in document["matches"]:
            if type(game) is not dict or not {"date","team1","team2","score"}<=set(game):
                raise ResearchSafetyError("UNRECOGNIZED_MATCH")
            day=date.fromisoformat(game["date"])
            if not season.startswith(str(day.year)) and day.year!=int(season[:4])+1:
                raise ResearchSafetyError("MATCH_DATE_WRONG_SEASON")
            home,away=game["team1"],game["team2"]
            if any(not isinstance(v,str) or not v or len(v)>100 for v in (home,away)) or home==away:
                raise ResearchSafetyError("BAD_TEAMS")
            key=(season,home,away)
            if key in seen:
                raise ResearchSafetyError("DUPLICATE_FIXTURE")
            seen.add(key)
            gh,ga=_score(game)
            rows.append((day,season,home,away,gh,ga))
    rows.sort(key=lambda r:(r[0],r[2],r[3]))
    if len(rows)!=1140:
        raise ResearchSafetyError("RESEARCH_COUNTS_CHANGED")
    return rows


def lagged_features(rows):
    """Updates only once day+3 <= next match day; avoids same-day leakage.

    This is intentionally a conservative event-time reconstruction; NOT a
    receipt, not provider publication time. Score of target cannot reach
    features, since its update is enqueued after feature computation.
    """
    elo=defaultdict(lambda:1500.0)
    prev=defaultdict(list)
    pending=[]
    outputs=[]
    for day,season,home,away,gh,ga in rows:
        while pending and pending[0][0]<day:
            _,_,h,a,sh,sa=heapq.heappop(pending)
            eh,ea=elo[h],elo[a]
            expected_h=1/(1+10**((ea-eh)/400))
            observed=1.0 if sh>sa else .5 if sh==sa else 0.
            change=20*(observed-expected_h)
            elo[h]+=change
            elo[a]-=change
            prev[h].append(3 if sh>sa else 1 if sh==sa else 0)
            prev[a].append(3 if sa>sh else 1 if sh==sa else 0)
        hform,aform=prev[home][-5:],prev[away][-5:]
        features=[
            float(elo[home]-elo[away]+60),
            float(sum(hform)/max(len(hform),1)),
            float(sum(aform)/max(len(aform),1)),
            float(len(hform)),
            float(len(aform)),
        ]
        label="1" if gh>ga else "X" if gh==ga else "2"
        outputs.append({"date":day.isoformat(),"season":season,
                        "feature_vector":features,"label":label})
        # Actual event time (date only) + 3 days, strict inequality below.
        # All score changes on date D are hidden until date D+4.
        seq=len(outputs)
        heapq.heappush(pending,(day+timedelta(days=3),seq,home,away,gh,ga))
    return outputs


def _prob_metrics(probs,targets):
    if len(probs)!=len(targets) or not probs:
        raise ResearchSafetyError("EMPTY_VALIDATION")
    ll=br=acc=0.0
    bins=[[0,0.0,0.0] for _ in range(10)]
    for p,y in zip(probs,targets):
        if len(p)!=3 or any(not math.isfinite(float(a)) or float(a)<0 for a in p) or abs(sum(p)-1)>1e-7:
            raise ResearchSafetyError("INVALID_P_1X2")
        idx=("1","X","2").index(y)
        ll-=math.log(max(float(p[idx]),1e-15))
        br+=sum((float(v)-(i==idx))**2 for i,v in enumerate(p))
        predicted=max(range(3),key=lambda i:p[i])
        success=int(predicted==idx)
        acc+=success
        confidence=float(p[predicted])
        b=bins[min(9,int(confidence*10))]
        b[0]+=1;b[1]+=confidence;b[2]+=success
    n=len(targets)
    ece=sum(q[0]/n*abs(q[1]/q[0]-q[2]/q[0]) for q in bins if q[0])
    return {"log_loss":round(ll/n,8),"brier_sum3":round(br/n,8),
            "accuracy":round(acc/n,8),"ece_top1_10bin":round(ece,8)}


def run_research(sources,source_sha256,model_path=None):
    from catboost import CatBoostClassifier,Pool
    records=lagged_features(load_results(sources))
    train=[r for r in records if r["season"] in TRAIN_SEASONS]
    valid=[r for r in records if r["season"]==VALID_SEASON]
    if len(train)!=760 or len(valid)!=380 or max(r["date"] for r in train)>=min(r["date"] for r in valid):
        raise ResearchSafetyError("CHRONOLOGY_OR_SPLIT_CHANGED")
    labels=[r["label"] for r in train]
    if set(labels)!={"1","X","2"}:
        raise ResearchSafetyError("TRAIN_CLASSES_MISSING")
    cfg={"iterations":150,"depth":4,"learning_rate":0.045,"loss_function":"MultiClass",
         "random_seed":SEED,"thread_count":1,"allow_writing_files":False,"verbose":False}
    model=CatBoostClassifier(**cfg)
    model.fit(Pool([r["feature_vector"] for r in train],labels,feature_names=list(FEATURES)))
    probabilities=model.predict_proba(Pool([r["feature_vector"] for r in valid],feature_names=list(FEATURES)))
    order=[str(x) for x in model.classes_]
    if set(order)!={"1","X","2"}:
        raise ResearchSafetyError("CLASS_ORDER_UNSAFE")
    aligned=[[float(p[order.index(c)]) for c in ("1","X","2")] for p in probabilities]
    freq=Counter(labels)
    empirical=[freq[c]/len(train) for c in ("1","X","2")]
    if model_path is None:
        with tempfile.TemporaryDirectory(prefix="kb3_step14_research_") as t:
            cbm=Path(t)/"M1_RESEARCH_ONLY_NOT_PIT.cbm"
            model.save_model(str(cbm))
            model_sha=sha256(cbm.read_bytes()).hexdigest()
    else:
        dest=Path(model_path)
        if dest.name!="M1_RESEARCH_ONLY_NOT_PIT.cbm":
            raise ResearchSafetyError("MODEL_DESTINATION_RESEARCH_LABEL_REQUIRED")
        dest.parent.mkdir(parents=True,exist_ok=True)
        model.save_model(str(dest))
        model_sha=sha256(dest.read_bytes()).hexdigest()
    result={
        "schema":"kb3-step14-public-research-catboost-v1",
        "research_only_policy":POLICY,
        "source":"openfootball/football.json",
        "source_urls":{s:SOURCE.format(season=s) for s in SEASONS},
        "source_sha256":source_sha256,
        "official_step12_train_eligibility_changed":False,
        "official_pitchapi_ids_joined":False,
        "real_historical_pit_proven":False,
        "actual_historical_observed_at_known":False,
        "feature_source_data_is_asof_certified":False,
        "synthetic_data":False,
        "research_real_match_results":True,
        "train_rows":len(train),
        "validation_rows":len(valid),
        "test_season_requested":False,
        "test_rows_read":0,
        "odds_read":False,
        "xg_read":False,
        "lag_rule":"event_date + 3 days; update only strictly earlier than next target calendar date; hypothetical not actual publication",
        "feature_names":list(FEATURES),
        "fixed_seed":SEED,
        "fixed_config":cfg,
        "model_sha256":model_sha,
        "valid_class_counts":dict(Counter(r["label"] for r in valid)),
        "catboost_research_validation":_prob_metrics(aligned,[r["label"] for r in valid]),
        "train_frequency_reference":_prob_metrics([empirical]*len(valid),[r["label"] for r in valid]),
        "gate14_pass":False,
        "production_approved":False,
        "model_champion_selected":False,
    }
    return result


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--model",default=None)
    args=p.parse_args()
    docs,hashes=read_public_seasons()
    out=run_research(docs,hashes,model_path=args.model)
    dest=Path(args.report)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("train_rows","validation_rows","catboost_research_validation","train_frequency_reference","source_sha256","model_sha256","gate14_pass","production_approved")},sort_keys=True))
