"""KB3 step16: prequential temperature SHADOW for settled host-attested M0-720.

This is diagnostic online evaluation, NOT production calibration or retraining.
For each already settled match, fit T using ONLY matches whose settlement was
observable strictly before that match's kickoff. Never read protected PL TEST.
No writes to SQLite or changes to original 100+50 rule.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
import argparse
import json
import sqlite3

from src.kb3_pit_ledger import canonical, as_utc
from src.kb3_step14_m1_math_calibration import (
    fit_temperature, score_one, score_predictions, temperature_probabilities,
    order_probability,
)

MODEL = "M0_ELO_POISSON_RESEARCH_720TRAIN_V1"
SOURCE_TYPES = frozenset((
    "GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES",
    "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES",
))
TRAIN_MIN_DIAGNOSTIC = 30
FIT_MIN_FORMAL = 100
HOLDOUT_MIN_FORMAL = 50

class ShadowAuditError(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise ShadowAuditError(message)

def verified_rows(db_path):
    """Read-only existing immutable records; trust upstream host proof audit,
    while validating identities/time rules again. Never derive proof from SHA.
    """
    path = Path(db_path).resolve()
    need(path.is_file(), "M0_EIGHT_SQLITE_NOT_FOUND")
    uri = path.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        need(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
             "SQLITE_INTEGRITY_FAIL")
        need(not db.execute("PRAGMA foreign_key_check").fetchall(),
             "FOREIGN_KEY_FAIL")
        models = db.execute("SELECT model FROM model_meta").fetchall()
        need(models == [(MODEL,)], "MODEL_META_DRIFT")
        # Required tables must exist: no fake proof when schema is missing.
        tables = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        need({"forecasts", "settlements", "m0720_github_push_proofs"} <= tables,
             "HOST_PROOF_TABLE_MISSING")
        records = db.execute("""SELECT f.id,f.model,f.league,f.native_match_id,
                   f.kickoff_utc,f.captured_at_utc,f.payload_json,
                   s.outcome,s.settled_utc,p.github_server_event_utc,p.source
                FROM forecasts f JOIN settlements s ON s.forecast_id=f.id
                JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
                ORDER BY f.kickoff_utc,f.id""").fetchall()
    out = []
    seen = set()
    for fid, model, league, native_id, kickoff, captured, payload, label, settled, proof_time, proof_source in records:
        need(model == MODEL and league in ("ESP","ITA","GER","FRA","NED","BEL","TUR","POL"),
             "UNEXPECTED_MODEL_OR_PROTECTED_LEAGUE")
        need((league,native_id) not in seen and fid not in seen,
             "DUPLICATE_FIXTURE_OR_FORECAST")
        seen.add((league,native_id)); seen.add(fid)
        p = json.loads(payload)
        need(p.get("forecast_sha256") == fid and
             sha256(canonical({k:v for k,v in p.items() if k != "forecast_sha256"})).hexdigest() == fid
             and p.get("model_version") == MODEL and p.get("phase") == "EARLY"
             and p.get("provider_match_id") == native_id
             and p.get("league_country") == league, "FROZEN_FORECAST_IDENTITY_MISMATCH")
        need(proof_source in SOURCE_TYPES, "UNSUPPORTED_HOST_PROOF_SOURCE")
        ko, ca, pr, se = (as_utc(t) for t in (kickoff,captured,proof_time,settled))
        need(ca <= pr <= ko-timedelta(minutes=90) and
             se > ko + timedelta(hours=3), "TIME_OR_HOST_PROOF_VIOLATION")
        need(label in ("1","X","2"), "INVALID_FT_LABEL")
        order_probability(p["p_1x2"])
        out.append({"id":fid,"league":league,"kickoff":ko,"settled":se,
                    "p":p["p_1x2"],"label":label})
    return out

def assess(rows, *, min_prior=TRAIN_MIN_DIAGNOSTIC):
    """Each evaluated match uses a freshly fitted T from strictly older,
    *already settled* independent matches. Diagnostics only; no persistent fit.
    """
    need(type(min_prior) is int and min_prior >= 20,
         "INVALID_DIAGNOSTIC_MINIMUM")
    seen = set()
    ordered = sorted(rows, key=lambda x:(x["kickoff"],x["id"]))
    for r in ordered:
        need(r["id"] not in seen and r["label"] in ("1","X","2")
             and isinstance(r["kickoff"],datetime) and isinstance(r["settled"],datetime)
             and r["kickoff"].tzinfo is not None and r["settled"].tzinfo is not None
             and r["kickoff"] < r["settled"], "DUPLICATE_OR_INVALID_SHADOW_ROW")
        seen.add(r["id"])
        order_probability(r["p"])
    evaluated=[]; temperatures=Counter(); raw=[]; adjusted=[]; labels=[]
    for r in ordered:
        train = [s for s in ordered if s["id"]!=r["id"] and
                 s["settled"] < r["kickoff"]]
        if len(train) < min_prior:
            continue
        fitted = fit_temperature([s["p"] for s in train],
                                 [s["label"] for s in train], min_rows=min_prior)
        t = fitted["temperature"]
        raw.append(r["p"]);adjusted.append(temperature_probabilities(r["p"],t))
        labels.append(r["label"]);temperatures[str(t)] += 1
        evaluated.append({"forecast_id":r["id"],"league":r["league"],
                          "prior_settled_n":len(train),"temperature":t,
                          "evaluated_kickoff_utc":r["kickoff"].isoformat()})
    result = {
        "schema":"kb3-step16-progressive-prequential-shadow-v1",
        "model":MODEL,
        "source_scope":"HOST_ATTESTED_SETTLED_ONLY",
        "upstream_proof_rechecked_locally_but_not_reauthenticated_against_GitHub":True,
        "settled_input_rows":len(ordered),
        "minimum_prior_settled_for_diagnostic":min_prior,
        "diagnostic_evaluated_rows":len(evaluated),
        "status":"SHADOW_DIAGNOSTIC_ONLY" if evaluated else "COLLECTING_NO_EVALUATION",
        "raw_metrics":score_predictions(raw,labels) if raw else None,
        "progressive_temperature_metrics":score_predictions(adjusted,labels) if adjusted else None,
        "temperature_choices":dict(temperatures),
        "sample_evaluation_provenance":evaluated,
        "formal_fit_min":FIT_MIN_FORMAL,
        "formal_prospective_holdout_min":HOLDOUT_MIN_FORMAL,
        "does_not_substitute_formal_100_plus_new_50":True,
        "catboost_retrained":False,
        "production_calibrator_changed":False,
        "champion_auto_selected":False,
        "protected_english_test_opened":False,
        "read_only":True,
        "formal_gate16_pass":False,
    }
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db",default="data/forward_m0_720_eight/kb3_forward_eight.sqlite")
    p.add_argument("--out",default="")
    args=p.parse_args()
    report=assess(verified_rows(args.db))
    body=json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        target=Path(args.out)
        need(not target.exists(),"SHADOW_REPORT_ALREADY_EXISTS")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(body,encoding="utf-8")
    print(body)

if __name__ == "__main__":
    main()
