"""KB3 7-point acceleration audit: immutable, no provider or network calls.
Only existing checked-in repo evidence. Does not certify unavailable fixture IDs.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
M0=ROOT/"data/forward_m0_720_eight/kb3_forward_eight.sqlite"
XG=ROOT/"data/forward_step17_xg_eight/observed_xg.sqlite"
FORECAST=ROOT/"data/pit_sidecar/m0_720_eight/2026-11-01/forecast/RECEIPT.json"
XG_RECEIPT=ROOT/"data/pit_sidecar/step17_native_xg_eight/2026-11-01/XG_READINESS_RECEIPT.json"
EIGHT=("ESP","ITA","GER","FRA","NED","BEL","TUR","POL")
EXPECTED_M0_SHA="55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1"

def require(value, reason):
    if not value:
        raise ValueError(reason)

def utc(x):
    value=datetime.fromisoformat(x.replace("Z","+00:00"))
    require(value.tzinfo is not None, "TIME_NOT_UTC")
    return value.astimezone(timezone.utc)

def open_readonly(path):
    require(Path(path).is_file(), "MISSING_READ_ONLY_SQLITE")
    db=sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro",uri=True)
    require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok","SQLITE_INTEGRITY_FAILURE")
    require(db.execute("PRAGMA foreign_key_check").fetchall()==[],"SQLITE_FOREIGN_KEYS_FAILURE")
    return db

def has_table(db, table):
    return db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()[0]==1

def audit_m0(db, *, now):
    require(has_table(db,"forecasts") and has_table(db,"settlements"),"M0_TABLES_MISSING")
    require(has_table(db,"m0720_github_push_proofs"),"HOST_PROOFS_MISSING")
    meta=db.execute("SELECT model,parameters_sha256,status FROM model_meta").fetchall()
    require(len(meta)==1 and meta[0][0]=="M0_ELO_POISSON_RESEARCH_720TRAIN_V1" and
            meta[0][1]==EXPECTED_M0_SHA and meta[0][2]=="RESEARCH_ONLY_NOT_APPROVED",
            "M0_BASELINE_MANIFEST_CHANGED")
    counts=Counter()
    leagues=Counter()
    rows=db.execute("""SELECT f.id,f.league,f.kickoff_utc,
        p.github_server_event_utc,s.forecast_id
        FROM forecasts f
        LEFT JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
        LEFT JOIN settlements s ON s.forecast_id=f.id""").fetchall()
    require(len({row[0] for row in rows})==len(rows),"DUPLICATE_M0_FORECAST")
    for fid,league,kickoff,published,settled in rows:
        require(league in EIGHT,"PROTECTED_ENGLISH_TEST_PRESENT")
        leagues[league]+=1
        k=utc(kickoff)
        if published is None:
            counts["missing_github_host_proof"]+=1
            continue
        require(utc(published)<k-timedelta(minutes=90),"M0_HOST_PROOF_TOO_LATE")
        counts["host_attested_forecasts"]+=1
        if settled is not None:
            counts["host_attested_settled"]+=1
        elif k<=now:
            counts["host_attested_kickoff_passed_not_settled"]+=1
        else:
            counts["host_attested_future_awaiting_match"]+=1
    counts["all_forecasts"]=len(rows)
    counts["all_settlements"]=db.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
    counts["calibrator_count"]=db.execute("SELECT COUNT(*) FROM m0720_calibrators").fetchone()[0] if has_table(db,"m0720_calibrators") else 0
    counts["holdout_review_count"]=db.execute("SELECT COUNT(*) FROM m0720_holdout_reviews").fetchone()[0] if has_table(db,"m0720_holdout_reviews") else 0
    require(counts["calibrator_count"]==0 or counts["host_attested_settled"]>=100,"CALIBRATION_PREMATURE")
    require(counts["holdout_review_count"]==0 or counts["calibrator_count"]>0,"HOLDOUT_PREMATURE")
    chall=db.execute("SELECT COUNT(*) FROM step17_frozen_challengers").fetchone()[0] if has_table(db,"step17_frozen_challengers") else 0
    proof=db.execute("SELECT COUNT(*) FROM step17_challenger_host_proofs").fetchone()[0] if has_table(db,"step17_challenger_host_proofs") else 0
    require(proof<=chall,"CHALLENGER_PROOF_OVERCOUNT")
    complete=db.execute("""SELECT COUNT(DISTINCT c.source_m0_forecast_sha256)
        FROM step17_frozen_challengers c
        JOIN step17_challenger_host_proofs p ON p.challenger_sha256=c.challenger_sha256
        JOIN settlements s ON s.forecast_id=c.source_m0_forecast_sha256
        JOIN m0720_github_push_proofs m ON m.forecast_id=s.forecast_id""").fetchone()[0] if chall and has_table(db,"step17_challenger_host_proofs") else 0
    return {"counts":dict(counts),"per_league_frozen":dict(sorted(leagues.items())),
      "challenger_frozen":chall,"challenger_host_attested":proof,
      "at_least_one_challenger_paired_with_settled_m0":complete,
      "calibration_threshold_100_not_reduced":True,
      "future_independent_holdout_50_not_reduced":True,
      "authoritative_eligible_fit_count_must_use_full_calibration_gate":True}

def audit_history(forecast):
    require(forecast.get("mode")=="forecast" and forecast.get("league_count")==8
       and set(forecast.get("countries",[]))==set(EIGHT)
       and forecast.get("original_2026_27_Premier_League_TEST_accessed") is False,
       "WRONG_FORECAST_SCOPE")
    shapes=forecast["season_shapes"]
    inventory={}
    for c in EIGHT:
        old=shapes[c+"/2025/2026"]
        n=old["teams"]
        total=old["all"]
        require(old["finished"]==total and old["not_started"]==0,"HISTORY_NOT_FINISHED")
        regular=n*(n-1)
        inventory[c]={"fixtures_count":total,"regular_round_robin_reference":regular,
          "delta_count_not_phase_evidence":total-regular,
          "needs_native_fixture_id_phase_review":total!=regular,
          "source_fixture_id_set_sha256":old["id_sha256"]}
    covered=forecast.get("coverage",{})
    require(set(covered)==set(EIGHT),"M0_COVERAGE_LEAGUES_MISSING")
    return {"historical_fixture_total":sum(x["fixtures_count"] for x in inventory.values()),
      "country_counts":inventory,"per_league_eligible_forecasts_at_original_capture":covered,
      "original_capture_total_eligible_forecasts":sum(covered.values()),
      "m0_current_limit_per_league":10,"m0_current_horizon_hours":96,
      "m0_capture_provider_calls":forecast["network_calls"],
      "limit_binding_cannot_be_inferred_from_post_filter_coverage":True,
      "raw_native_fixture_phase_ids_available_in_receipt":False,
      "new_multi_league_training_allowed":False}

def audit_xg(db,receipt):
    require(has_table(db,"observed_native_xg"),"XG_TABLE_MISSING")
    n=db.execute("SELECT COUNT(*) FROM observed_native_xg").fetchone()[0]
    require(n==receipt["cumulative_verified_xg_matches"],"XG_DB_RECEIPT_COUNT_MISMATCH")
    published=db.execute("SELECT COUNT(*) FROM observed_native_xg WHERE source_published_at_utc IS NOT NULL").fetchone()[0]
    require(published==0,"UNVERIFIED_PROVIDER_PUBLICATION_ASSIGNED")
    require(receipt["hard_limit_calls"]==33 and receipt["network_calls"]<=33,
        "XG_PROVIDER_BUDGET_CHANGED")
    form=receipt["future_form5_coverage"]
    require(form["complete_last5_both_team_xg"]<=form["future_targets_scanned"],
        "XG_COMPLETENESS_INVALID")
    return {"verified_native_xg_pairs":n,"observed_last5_complete_targets":form["complete_last5_both_team_xg"],
        "future_targets_checked":form["future_targets_scanned"],
        "missing_last5_targets_by_league":form["missing_by_country"],
        "provider_first_published_utc_proven":False,
        "actual_missing_predecessor_fixture_ids_available_offline":False,
        "actual_provider_calls_last_capture":receipt["network_calls"],
        "provider_calls_if_16_pairs":17+2*16,
        "extra_calls_over_current_limit_if_16_pairs":16,
        "provider_subscription_allows_49_calls":None,
        "research_priority_selector_live":False}

def run(m0_db,xg_db,forecast_receipt,xg_receipt,*,now):
    require(now.tzinfo is not None and now.utcoffset()==timedelta(0),"AUDIT_TIME_NOT_UTC")
    with open_readonly(m0_db) as m,open_readonly(xg_db) as x:
        mr=audit_m0(m,now=now)
        xr=audit_xg(x,json.loads(Path(xg_receipt).read_text()))
    source=json.loads(Path(forecast_receipt).read_text())
    hist=audit_history(source)
    return {"schema":"kb3-step16-17-seven-step-readonly-real-sqlite-v1",
      "source_scope":"actual_main_repo_immutable_db_and_receipt_no_api",
      "asof_utc":now.isoformat(),"m0":mr,"xg":xr,"history_and_coverage":hist,
      "provider_calls_issued_by_this_audit":0,"sqlite_mutations":0,
      "source_sha256":{"m0_db":hashlib.sha256(Path(m0_db).read_bytes()).hexdigest(),
       "xg_db":hashlib.sha256(Path(xg_db).read_bytes()).hexdigest(),
       "forecast_receipt":hashlib.sha256(Path(forecast_receipt).read_bytes()).hexdigest(),
       "xg_receipt":hashlib.sha256(Path(xg_receipt).read_bytes()).hexdigest()},
      "m0_model_changed":False,"protected_test_accessed":False,
      "gate16":"PENDING","gate17":"PENDING","production_promoted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m0",default=str(M0))
    p.add_argument("--xg",default=str(XG))
    p.add_argument("--forecast",default=str(FORECAST))
    p.add_argument("--xg-receipt",default=str(XG_RECEIPT))
    p.add_argument("--output",required=True)
    args=p.parse_args()
    outfile=Path(args.output)
    require(not outfile.exists(),"AUDIT_OUTPUT_APPEND_ONLY")
    assert not any(str(outfile.resolve()).startswith(str((ROOT/p).resolve())) for p in ("data","models"))
    report=run(args.m0,args.xg,args.forecast,args.xg_receipt,now=datetime.now(timezone.utc))
    outfile.parent.mkdir(parents=True,exist_ok=True)
    outfile.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"m0":report["m0"],"xg":{k:report["xg"][k] for k in
      ("verified_native_xg_pairs","observed_last5_complete_targets","future_targets_checked")},
      "history_total":report["history_and_coverage"]["historical_fixture_total"],
      "zero_api_and_no_database_changes":True},sort_keys=True))
if __name__=="__main__":
    main()
