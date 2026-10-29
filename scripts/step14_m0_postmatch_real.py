"""Read 4 REAL current PitchAPI network endpoints, postmatch settle, score,
and archive encrypted raw evidence + append-only SQLite. No new paid service.
NEVER backdate history or fit M1. Two scheduled checks daily.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from scripts.pitchapi_step06_audit import to_plain
from scripts.step14_three_league_pitchapi_actual_audit import (
    select_three,CURRENT)
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_pit_ledger import utc_now,canonical,as_utc
from src.kb3_m0_live_settlement_calibration import (
    settle,audit_and_prepare_calibration,ResultSafetyError)
from src.kb3_m0_shadow_1x2_live_freeze import VERSION as FORECAST_SCHEMA
from src.kb3_three_league_sqlite_forward_features import MODEL

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-real-network-postmatch-3league-M0-1x2-scoring-v1"
class PostmatchRunError(ValueError):pass

def verify_original_forecasts(db_path,report_root):
    """Cross-check immutable pre-existing Git JSON forecasts against SQLite.

    A SHA alone does not prove independent first publication, but cross-check
    with already committed pre-match report prevents silent feature rewriting.
    """
    manifest={}
    files=sorted(Path(report_root).glob("*/FROZEN_M0_SHADOW_1X2.json"))
    if not files:raise PostmatchRunError("NO_PREEXISTING_ARCHIVED_SHADOW_REPORT")
    for path in files:
        report=json.loads(path.read_text(encoding="utf8"))
        checksum=report.get("report_sha256")
        if checksum!=hashlib.sha256(canonical({k:v for k,v in report.items()
                                               if k!="report_sha256"})).hexdigest():
            raise PostmatchRunError("FORECAST_REPORT_HASH_TAMPERED")
        if (report.get("mode")!="M0_SHADOW_PROVISIONAL_UNFITTED"
                or report.get("original_2026_27_Premier_League_TEST_touched") is not False
                or report.get("original_M1_training_or_calibration") is not False):
            raise PostmatchRunError("UNSAFE_MODEL_STATUS_IN_EXISTING_FORECAST")
        for item in report["individual_forecasts"]:
            raw={k:v for k,v in item.items() if k!="forecast_sha256"}
            h=hashlib.sha256(canonical(raw)).hexdigest()
            if h!=item.get("forecast_sha256") or h in manifest:
                raise PostmatchRunError("FROZEN_FORECAST_CHANGED_OR_DUPLICATED")
            if (item["schema"]!=FORECAST_SCHEMA or item["engine"]!="KB3_ELO_POISSON_M0_V0_1"
                or item["parameter_status"]!="ILLUSTRATIVE_UNFITTED_NOT_FOR_BETTING"
                or as_utc(item["generated_at_utc"])>=as_utc(item["kickoff_utc"])):
                raise PostmatchRunError("INVALID_PREMATCH_MODEL_FROZEN_STATUS")
            manifest[h]=item
    with sqlite3.connect(db_path) as db:
        rows=db.execute("""SELECT forecast_id,prediction_payload_sha256,
            league_country,provider_match_id,kickoff_utc,p_1,p_x,p_2,
            feature_sha256,feature_snapshot_id,generated_at_utc
            FROM m0_shadow_1x2_forecasts""").fetchall()
    if len(rows)!=len(manifest):
        raise PostmatchRunError("SQLITE_AND_PRIOR_GITHUB_FROZEN_FORECAST_COUNT_DIFFER")
    for fid,h,country,mid,ko,p1,px,p2,fsha,fsid,generated in rows:
        item=manifest.get(h)
        if item is None or fid!=h or (item["league"],item["match_id"],
          item["kickoff_utc"],item["feature_sha256"],item["feature_snapshot_id"],
          item["generated_at_utc"])!=(country,mid,ko,fsha,fsid,generated):
            raise PostmatchRunError("SQLITE_FORECAST_NOT_PUBLISHED_IDENTICALLY")
        if any(abs(item["p_1x2"][k]-v)>1e-12
            for k,v in (("1",p1),("X",px),("2",p2))):
            raise PostmatchRunError("FORECAST_PROBABILITIES_DIVERGED")
    return {"independently_existing_repo_forecast_hashes":len(manifest),
            "match_hash_identical":True,
            "server_first_publication_utc_independently_proven":False}

def run(*,key,public_pem,db_path,report_root,evidence_root,now=None,
         client_factory=None):
    if not isinstance(key,str) or not key.strip():
        raise PostmatchRunError("EXISTING_PITCHAPI_SECRET_REQUIRED")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    now=now or datetime.now(timezone.utc)
    if now.utcoffset().total_seconds()!=0:raise PostmatchRunError("UTC_REQUIRED")
    root=Path(evidence_root)
    dest=root/now.strftime("%Y-%m-%d")/("run-"+now.strftime("%H%M%S%f"))
    if dest.exists():raise PostmatchRunError("EXISTING_UNIQUE_EVIDENCE_RUN")
    # First prove genuinely archived forecasts before consuming results.
    before=verify_original_forecasts(db_path,report_root)
    dest.mkdir(parents=True,exist_ok=False)
    try:
        cli=client_factory(api_key=key)
        original=[];calls=0
        def request(resource,method,*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls>4:raise PostmatchRunError("MAX_FOUR_NETWORK_CALLS")
            start=utc_now()
            result=to_plain(method(*args,**kwargs))
            end=utc_now()
            if not isinstance(result,dict):raise PostmatchRunError("NON_DICT_PITCH_API")
            add_observation(original,resource=resource,payload=result,
                            started=start,completed=end)
            return result
        cat=request("pitchapi:catalog",cli.leagues.list)
        chosen=select_three(cat)
        sources={}
        for title,country,expected,lid in chosen:
            fixtures=request("pitchapi:postmatch:"+country+":"+CURRENT,
                 cli.leagues.matches,lid,season=CURRENT,status="all")
            sources[country]=(original[-1],fixtures.get("matches"))
        if len(original)!=4:raise PostmatchRunError("WRONG_NETWORK_OBSERVATION_COUNT")
        sealed=seal(original,public_pem,
                    dest/"ORIGINAL_PITCHAPI_RESULTS.enc",
                    dest/"ORIGINAL_PITCHAPI_RESULTS.manifest.json")
        staging=dest/"STAGING_M0.sqlite"
        shutil.copy2(db_path,staging)
        settled=settle(staging,sources,now=utc_now())
        audit=audit_and_prepare_calibration(staging,now=utc_now())
        with sqlite3.connect(staging) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise PostmatchRunError("POSTMATCH_SQLITE_INTEGRITY")
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise PostmatchRunError("POSTMATCH_SQLITE_FK")
        receipt={"schema":SCHEMA,"captured_at_utc":original[-1]["completed_at_utc"],
         "network_call_count":calls,"processed_leagues":["ESP","ITA","GER"],
         "original_Premier_League_TEST_accessed":False,
         "no_new_provider_subscription":True,"original_source_encrypted":True,
         "original_source_chain_sha256":sealed["proof"]["final_chain_sha256"],
         "original_source_cipher_sha256":sealed["ciphertext_sha256"],
         "forecast_existing_preflight":before,"settlement":settled,"evaluation":audit,
         "persistent_sqlite_after_sha256":hashlib.sha256(staging.read_bytes()).hexdigest(),
         "calibration_auto_activated":False,
         "M1_training_or_original_gate14_pass":False}
        receipt["receipt_sha256"]=hashlib.sha256(canonical(receipt)).hexdigest()
        (dest/"M0_POSTMATCH_AND_CALIBRATION_REVIEW.json").write_text(
            json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf8")
        os.replace(staging,db_path)
        return receipt,dest
    except BaseException:
        shutil.rmtree(dest,ignore_errors=True)
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="data/forward_m0/kb3_forward_m0.sqlite")
    p.add_argument("--forecasts",default="data/forecasts/m0_shadow_1x2")
    p.add_argument("--evidence",default="data/pit_sidecar/m0_postmatch")
    p.add_argument("--public-key",default="config/step11_archive_recipient_public.pem")
    a=p.parse_args()
    try:
        r,dest=run(key=os.environ.get("PITCHAPI_API_KEY",""),public_pem=a.public_key,
            db_path=a.db,report_root=a.forecasts,evidence_root=a.evidence)
        print(json.dumps({"state":"REAL_M0_1X2_POSTMATCH_AUDITED",
          "newly_settled":r["settlement"]["newly_settled"],
          "total":r["settlement"]["total_settled"],
          "ll":r["evaluation"]["aggregate_score"]["log_loss"] if r["evaluation"]["aggregate_score"] else None,
          "brier_sum3":r["evaluation"]["aggregate_score"]["brier_sum3"] if r["evaluation"]["aggregate_score"] else None,
          "calibration_fit_reached":r["evaluation"]["candidate"] is not None,
          "auto_activated":False,"receipts":4,
          "evidence":str(dest)},sort_keys=True))
    except Exception as exc:
        print("M0_POSTMATCH_SAFE_FAIL",type(exc).__name__,
              str(exc) if isinstance(exc,(PostmatchRunError,ResultSafetyError)) else "opaque")
        raise SystemExit(3)
if __name__=="__main__":main()
