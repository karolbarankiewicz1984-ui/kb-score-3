"""Read-only, historically reconstructed, matched CatBoost research on real PitchAPI.

No provider API. No formal PIT claims. No modification of M0, pinned Shadow,
official FIT/HOLDOUT, production model or protected Premier League TEST.
Run: python -m scripts.kb3_core5_matched_experiment --out <report.json>
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/research/historical_multistat/observations.sqlite"
SCHEMA = "kb3-core5-xg-cards-matched-retrospective-research-v1"
LEAGUES = frozenset(("ESP", "ITA", "GER", "FRA", "NED", "BEL", "TUR", "POL"))
SEASONS = frozenset(("2023/2024", "2024/2025", "2025/2026"))
GOALS = ("goals_for", "goals_against", "points")
THREE = ("total_shots", "fouls", "corners")
CARD = ("yellow_cards",)
XG = ("xg_for", "xg_against")
LABELS = ("1", "X", "2")
PARAMS = dict(iterations=180, depth=3, learning_rate=.035, l2_leaf_reg=8.,
    loss_function="MultiClass", random_seed=20261104, thread_count=2,
    verbose=False, allow_writing_files=False, nan_mode="Min")

def utc(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1<<20), b""):
            h.update(block)
    return h.hexdigest()

def historic_rows(path):
    """No target results as features, strict five predecessors, copied readonly."""
    with sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall()==[]
        fixtures = {}
        team_history = defaultdict(list)
        for league, season, mid, ko, home, away, gh, ga in db.execute(
            "SELECT scope,season,match_id,kickoff_utc,home_team_id,away_team_id,"
            "goals_home_90,goals_away_90 FROM finished_fixture_index "
            "ORDER BY kickoff_utc,match_id"
        ):
            key=(league,mid)
            assert key not in fixtures and league!="ENG"
            fixtures[key]=(season,ko,home,away,gh,ga)
            for team in (home,away):
                team_history[(league,team)].append((utc(ko),mid))
        observed={(league,mid) for league,mid in db.execute(
            "SELECT scope,match_id FROM observations")}
        cached={}
        for league,mid,raw in db.execute(
            "SELECT scope,target_match_id,feature_json FROM rolling_feature_cache"
        ):
            key=(league,mid)
            assert key not in cached
            cached[key]=json.loads(raw)
        assert observed and observed==set(cached) and observed<=set(fixtures)
        assert db.execute("SELECT COUNT(*) FROM observations WHERE "
            "provider_first_published_at_utc IS NOT NULL").fetchone()[0]==0
    rows=[]
    strict_disagreements=0
    for key in sorted(observed):
        league,mid=key
        season,ko,home,away,gh,ga=fixtures[key]
        if league not in LEAGUES or season not in SEASONS:
            continue
        snapshot=cached[key]
        assert snapshot["training_approved"] is False
        assert snapshot["original_pit_certified"] is False
        target_ko=utc(ko)
        cutoff=target_ko-timedelta(hours=2)  # hypothetical, never a real PIT
        for team in (home,away):
            all_games=team_history[(league,team)]
            a=[m for kick,m in all_games if m!=mid and
               kick+timedelta(hours=3)<=target_ko][-5:]
            b=[m for kick,m in all_games if m!=mid and
               kick+timedelta(hours=3)<=cutoff][-5:]
            strict_disagreements+=int(a!=b)
        sides=snapshot["sides"]
        home5=sides["home"]["all"]["5"]
        away5=sides["away"]["all"]["5"]
        if not home5["history_complete"] or not away5["history_complete"]:
            continue
        data={}
        for side,roll in (("home",home5),("away",away5)):
            for field in GOALS+THREE+CARD+XG:
                item=roll["metrics"][field]
                if item["complete"]:
                    assert item["valid_n"]==5 and item["mean"] is not None
                    data[side+"_"+field]=float(item["mean"])
                else:
                    assert item["mean"] is None
                    data[side+"_"+field]=float("nan")
        def complete(fields):
            return all(math.isfinite(data[side+"_"+f])
                       for side in ("home","away") for f in fields)
        assert complete(GOALS)
        rows.append(dict(league=league, fixture=mid, kickoff=ko,
            label=("1" if gh>ga else "X" if gh==ga else "2"), data=data,
            three=complete(THREE), core=complete(THREE+CARD),
            xg=complete(XG)))
    assert strict_disagreements==0, "LAST5_CACHE_STRICT_ASOF_DRIFT"
    return sorted(rows,key=lambda r:(r["kickoff"],r["league"],r["fixture"])), {
        "finished_indexed":len(fixtures), "observed_historical":len(observed),
        "strict_asof_predecessor_differences":strict_disagreements}

def chronological_split(rows):
    """70/30 by fixture kickoff; grouped ties and seven-day embargo."""
    assert len(rows)>=20
    ordered=sorted(rows,key=lambda r:(r["kickoff"],r["league"],r["fixture"]))
    boundary=utc(ordered[int(len(ordered)*.7)]["kickoff"])
    train=[r for r in ordered if utc(r["kickoff"])<boundary]
    assert train
    earliest=max(boundary,utc(train[-1]["kickoff"])+timedelta(days=7))
    valid=[r for r in ordered if utc(r["kickoff"])>=earliest]
    assert valid
    assert utc(train[-1]["kickoff"])+timedelta(days=7)<=utc(valid[0]["kickoff"])
    assert not {(r["league"],r["fixture"]) for r in train} & {
        (r["league"],r["fixture"]) for r in valid}
    return train,valid,{"total":len(rows), "train":len(train),
        "validation":len(valid), "embargo_discarded":len(rows)-len(train)-len(valid),
        "last_train_utc":train[-1]["kickoff"], "first_validation_utc":valid[0]["kickoff"]}

def columns(cards=False, xg=False):
    fields=GOALS+THREE+(CARD if cards else ())+(XG if xg else ())
    return [side+"_"+key for side in ("home","away") for key in fields]

def fit(train, valid, fields):
    from catboost import CatBoostClassifier
    x=lambda rows:[[r["data"][name] for name in fields] for r in rows]
    model=CatBoostClassifier(**PARAMS)
    model.fit(x(train),[r["label"] for r in train])
    classes=[str(c) for c in model.classes_]
    assert set(classes)==set(LABELS)
    pred=[{y:float(p[classes.index(y)]) for y in LABELS}
          for p in model.predict_proba(x(valid))]
    assert all(all(0<=p[k]<=1 for k in LABELS) and
               abs(sum(p.values())-1)<1e-8 for p in pred)
    return pred

def scores(rows, predictions):
    assert rows and len(rows)==len(predictions)
    logloss=brier=hits=0.
    for row,p in zip(rows,predictions):
        y=row["label"]
        logloss-=math.log(max(p[y],1e-15))
        brier+=sum((p[k]-int(k==y))**2 for k in LABELS)
        hits+=int(max(LABELS,key=lambda k:p[k])==y)
    n=len(rows)
    return {"n":n, "log_loss":round(logloss/n,6),
            "brier_sum3":round(brier/n,6),
            "top1_accuracy":round(hits/n,6)}

def week_bootstrap(rows, a, b, replicates=600):
    """Paired match-by-match deltas, resampled in kickoff-week blocks."""
    weeks=defaultdict(list)
    for row,x,y in zip(rows,a,b):
        week=utc(row["kickoff"]).isocalendar()[:2]
        label=row["label"]
        dloss=math.log(max(x[label],1e-15))-math.log(max(y[label],1e-15))
        dbrier=sum((y[k]-int(k==label))**2-(x[k]-int(k==label))**2
                   for k in LABELS)
        weeks[week].append((dloss,dbrier))
    keys=sorted(weeks)
    if len(keys)<2:
        return {"weeks":len(keys),"status":"TOO_FEW_WEEKS"}
    rng=random.Random(20261105)
    losses=[];briers=[]
    for _ in range(replicates):
        draw=[item for key in (rng.choice(keys) for _ in keys)
              for item in weeks[key]]
        losses.append(sum(x for x,y in draw)/len(draw))
        briers.append(sum(y for x,y in draw)/len(draw))
    def ci(x):
        a=sorted(x)
        return [round(a[int(.025*len(a))],6),
                round(a[int(.975*len(a))-1],6)]
    return {"weeks":len(keys),"replicates":replicates,
        "delta_new_minus_base_log_loss_ci95":ci(losses),
        "delta_new_minus_base_brier_sum3_ci95":ci(briers),
        "cannot_prove_model_superiority":True}

def compare(rows, baseline, candidate):
    a=scores(rows,baseline);b=scores(rows,candidate)
    return {"baseline":a,"candidate":b,
        "delta_candidate_minus_baseline":{
            k:round(b[k]-a[k],6) for k in
            ("log_loss","brier_sum3","top1_accuracy")},
        "bootstrap":week_bootstrap(rows,baseline,candidate)}

def research(path=DB):
    rows,meta=historic_rows(path)
    core=[r for r in rows if r["core"]]
    xg=[r for r in rows if r["xg"]]
    complete=[r for r in core if r["xg"]]
    three=[r for r in rows if r["three"]]
    assert len(core)>=20 and len(complete)>=20
    train,valid,core_split=chronological_split(core)
    # Extended no-card training cannot use ANY matches later than base TRAIN.
    three_train=[r for r in three if utc(r["kickoff"])<=
                 utc(train[-1]["kickoff"])]
    assert len(three_train)>=len(train)
    assert all(utc(r["kickoff"])<=utc(valid[0]["kickoff"])-timedelta(days=7)
               for r in three_train)
    four=fit(train,valid,columns(cards=True))
    plus_xg=fit(train,valid,columns(cards=True,xg=True))
    three_equal=fit(train,valid,columns())
    three_more=fit(three_train,valid,columns())
    ctrain,cvalid,complete_split=chronological_split(complete)
    cbase=fit(ctrain,cvalid,columns(cards=True))
    cxg=fit(ctrain,cvalid,columns(cards=True,xg=True))
    selected=[i for i,row in enumerate(valid) if row["xg"]]
    return {"schema":SCHEMA, "historical_db_sha256":sha_file(path),
        "source_type":"RECONSTRUCTED_LATER_POSTMATCH_OBSERVATION",
        "source_original_first_publication_proven":False,
        "original_historical_pit_certified":False,
        "formal_fit_increment":0,"production_approved":False,
        "existing_m0_unchanged":True,"pinned_shadow_six_unchanged":True,
        "protected_english_test_untouched":True,
        "full_85_feature_m1r_parity":False,
        "historical_source_inventory":meta,
        "cohorts":{"history5":len(rows),"core5":len(core),"xg5":len(xg),
            "core5_plus_xg5":len(complete),
            "three_stats_without_yellow":len(three),
            "extra_three_stats_training_before_core_cutoff":
                len(three_train)-len(train)},
        "core5_split":core_split,"complete_core5_xg5_split":complete_split,
        "main_paired_validation":{
            "xg_optional_vs_no_xg_same_train":compare(valid,four,plus_xg),
            "remove_yellow_same_train":compare(valid,four,three_equal),
            "remove_yellow_expanded_early_train":compare(valid,four,three_more)},
        "complete_core5_xg5_paired_validation":compare(cvalid,cbase,cxg),
        "core5_validation_rows_with_complete_xg":len(selected),
        "optional_xg_complete_only_paired_check":compare(
            [valid[i] for i in selected],
            [four[i] for i in selected],
            [plus_xg[i] for i in selected]),
        "parameters":PARAMS,"embargo_days":7,
        "scope":"RESEARCH_ONLY_NOT_PROSPECTIVE_NOT_FORMAL_PIT"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=DB)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=research(args.db)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True,
                                  ensure_ascii=False)+"\n",encoding="utf8")
    print("KB3_CORE5_MATCHED_RESEARCH",json.dumps({
        "cohorts":result["cohorts"],
        "core5_split":result["core5_split"],
        "complete_split":result["complete_core5_xg5_split"],
        "optional_xg_delta":result["main_paired_validation"][
            "xg_optional_vs_no_xg_same_train"]["delta_candidate_minus_baseline"],
        "complete_xg_delta":result["complete_core5_xg5_paired_validation"][
            "delta_candidate_minus_baseline"],
        "no_cards_expanded_delta":result["main_paired_validation"][
            "remove_yellow_expanded_early_train"]["delta_candidate_minus_baseline"],
        "formal_pit":False},sort_keys=True))

if __name__=="__main__":
    main()
