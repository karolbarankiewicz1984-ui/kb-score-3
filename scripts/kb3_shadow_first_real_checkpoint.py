"""Read-only checkpoint of first actual same-fixture M0 + Shadow Six records.

NO provider API, training, mutation, or synthetic data injection.
An M0/Shadow row's local clock is NOT a host-created artifact proof. Report
separately: new M0, new Shadow, actual GitHub host proof, and settled pairs.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from src.kb3_pit_ledger import as_utc,canonical

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"data/forward_m0_720_eight/kb3_forward_eight.sqlite"
ACTIVATION_UTC="2026-11-04T23:18:24Z"
MODEL="KB3_CATBOOST_SHADOW_LAST5_GOALS_6_RESEARCH_V1"
PIN_SHA="58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5"
SCHEMA="kb3-first-real-shadow-six-checkpoint-v1"


class CheckpointError(ValueError):
    pass


def need(condition,message):
    if not condition:
        raise CheckpointError(message)


def hash_obj(item):
    return hashlib.sha256(canonical(item)).hexdigest()


def _has_table(db,name):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def _count(db,table,where="",params=()):
    if not _has_table(db,table):
        return 0
    need(table in {
       "forecasts","settlements","kb3_p1_shadow_six_new_only",
       "kb3_p1_shadow_six_host_proofs","m0720_github_push_proofs"},
       "UNEXPECTED_TABLE")
    return int(db.execute("SELECT COUNT(*) FROM "+table+" "+where,params).fetchone()[0])


def audit(db_path=DB,activation_utc=ACTIVATION_UTC):
    path=Path(db_path)
    activated=as_utc(activation_utc)
    result={
      "schema":SCHEMA,
      "activation_from_utc":activation_utc,
      "source_db":str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else
                  path.name,
      "official_fit_increment":0,
      "model_promotion":False,
      "historical_model_pit_certified":False,
      "real_pre_match_pair_confirmed":False,
      "github_host_artifact_proof_confirmed":False,
      "settled_attested_pair_confirmed":False,
      "m0_total":0,"m0_new_since_activation":0,
      "shadow_total":0,"shadow_new_since_activation":0,
      "m0_shadow_pair_same_source_count":0,
      "github_host_verified_shadow_pairs":0,
      "settled_github_host_verified_pairs":0,
    }
    if not path.is_file():
        result["state"]="NO_PERSISTED_M0_SQLITE_FOUND"
        result["explanation"]="No immutable DB to inspect; do not infer a new forecast."
        return result
    with sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        need(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
             "PERSISTED_M0_DB_INTEGRITY_FAILURE")
        need(_has_table(db,"forecasts") and _has_table(db,"settlements"),
             "PERSISTED_M0_SCHEMA_MISSING")
        result["m0_total"]=_count(db,"forecasts")
        result["m0_new_since_activation"]=_count(
             db,"forecasts","WHERE captured_at_utc >= ?",(activation_utc,))
        result["shadow_total"]=_count(db,"kb3_p1_shadow_six_new_only")
        result["shadow_new_since_activation"]=_count(
             db,"kb3_p1_shadow_six_new_only",
             "WHERE shadow_generated_at_utc >= ?",(activation_utc,))
        result["settlement_total"]=_count(db,"settlements")
        # Classify every real Shadow Six fixture by kickoff and settlement.
        # This is a read-only snapshot, not proof that PitchAPI has a result.
        now=datetime.now(timezone.utc)
        diagnostic={"checked_at_utc":now.isoformat(),
                    "shadow_fixture_count":0,"settled":0,
                    "kickoff_future":0,"kickoff_less_than_3h_ago":0,
                    "mature_over_3h_unsettled":0,
                    "mature_unsettled_fixtures":[]}
        if _has_table(db,"kb3_p1_shadow_six_new_only"):
            for fid,league,mid,kick,settled in db.execute("""
                SELECT f.id,f.league,f.native_match_id,f.kickoff_utc,
                       EXISTS(SELECT 1 FROM settlements t WHERE t.forecast_id=f.id)
                FROM kb3_p1_shadow_six_new_only s
                JOIN forecasts f ON f.id=s.source_m0_forecast_sha256
                WHERE s.shadow_generated_at_utc >= ?
                ORDER BY f.kickoff_utc,f.id
            """,(activation_utc,)):
                diagnostic["shadow_fixture_count"]+=1
                kickoff=as_utc(kick)
                if settled:
                    diagnostic["settled"]+=1
                elif now<kickoff:
                    diagnostic["kickoff_future"]+=1
                elif now<kickoff+timedelta(hours=3):
                    diagnostic["kickoff_less_than_3h_ago"]+=1
                else:
                    diagnostic["mature_over_3h_unsettled"]+=1
                    diagnostic["mature_unsettled_fixtures"].append({
                        "league":league,"native_match_id":mid,
                        "kickoff_utc":kick,"forecast_id":fid,
                        "cause":"NEEDS_PROVIDER_SETTLEMENT_REASON_AUDIT"})
        result["shadow_settlement_diagnostic"]=diagnostic
        result["existing_m0_host_proofs"]=_count(db,"m0720_github_push_proofs")
        result["existing_shadow_host_proofs"]=_count(
            db,"kb3_p1_shadow_six_host_proofs")
        if result["shadow_total"] and not _has_table(db,"kb3_p1_shadow_six_host_proofs"):
            result["explanation"]="Shadow exists, but host proof table is absent or not audited."
        valid=[]
        if result["shadow_total"]:
            rows=db.execute("""
                SELECT s.id,s.payload_json,s.source_m0_forecast_sha256,
                       s.model_bytes_sha256,s.kickoff_utc,
                       s.shadow_generated_at_utc,
                       f.id,f.payload_json,f.captured_at_utc,
                       f.kickoff_utc,f.league,f.native_match_id
                FROM kb3_p1_shadow_six_new_only s
                JOIN forecasts f ON f.id=s.source_m0_forecast_sha256
                WHERE s.shadow_generated_at_utc>=?
                ORDER BY s.shadow_generated_at_utc,s.id
                """,(activation_utc,)).fetchall()
            need(len(rows)==result["shadow_new_since_activation"],
                 "ORPHAN_OR_TAMPERED_SHADOW_NOT_PAIRED_WITH_M0")
            for (s_id,s_json,parent_id,sha,kick,shadow_at,
                 f_id,f_json,f_at,f_kick,league,mid) in rows:
                child=json.loads(s_json)
                parent=json.loads(f_json)
                need(parent_id==f_id
                     and parent.get("forecast_sha256")==f_id
                     and child.get("shadow_sha256")==s_id
                     and hash_obj({k:v for k,v in parent.items()
                                   if k!="forecast_sha256"})==f_id
                     and hash_obj({k:v for k,v in child.items()
                                   if k!="shadow_sha256"})==s_id,
                     "PARENT_OR_SHADOW_IMMUTABLE_HASH_MISMATCH")
                need(sha==PIN_SHA
                     and child.get("model_bytes_sha256")==PIN_SHA
                     and child.get("model_version")==MODEL
                     and child.get("production_approved") is False
                     and child.get("official_fit_eligible") is False
                     and child.get("research_only") is True,
                     "NEW_SHADOW_RESEARCH_VERSION_OR_APPROVAL_DRIFT")
                need(kick==f_kick==parent["kickoff_utc"]
                     and child["league_country"]==league
                     and child["provider_match_id"]==mid
                     and child["feature_sha256"]==parent["feature_sha256"]
                     and child["source_chain_sha256"]==parent["source_chain_sha256"]
                     and child["original_feature_cutoff_utc"]==
                         parent["feature_cutoff_utc"]
                     and parent["feature_cutoff_utc"]==f_at,
                     "SHADOW_PARENT_OR_CUTOFF_DRIFT")
                lead=timedelta(minutes=90)
                need(activated <= as_utc(shadow_at)
                     and as_utc(f_at)<=as_utc(shadow_at)
                     and as_utc(shadow_at)<as_utc(kick)-lead
                     and as_utc(f_at)<as_utc(kick)-lead,
                     "NEW_SHADOW_NOT_REAL_EARLY_CAPTURE")
                valid.append(s_id)
        result["m0_shadow_pair_same_source_count"]=len(valid)
        result["real_pre_match_pair_confirmed"]=len(valid)>0
        if valid and _has_table(db,"kb3_p1_shadow_six_host_proofs"):
            proof_rows=db.execute("""
                SELECT p.proof_sha256,p.shadow_sha256,
                       p.source_m0_forecast_sha256,
                       p.github_artifact_id,
                       p.github_server_artifact_created_utc,
                       p.attestation_source,p.audited_at_utc,
                       s.shadow_generated_at_utc,s.kickoff_utc,
                       s.source_m0_forecast_sha256
                FROM kb3_p1_shadow_six_host_proofs p
                JOIN kb3_p1_shadow_six_new_only s
                  ON s.id=p.shadow_sha256
                WHERE s.shadow_generated_at_utc >= ?
                """,(activation_utc,)).fetchall()
            ids=set(valid)
            passed=set()
            for proofsha,cid,proofparent,art,server,source,audited,created,kick,parent in proof_rows:
                need(cid in ids and cid not in passed and proofparent==parent,
                     "DUPLICATE_OR_OLD_SHADOW_HOST_PROOF")
                proof={
                    "shadow_sha256":cid,
                    "source_m0_forecast_sha256":proofparent,
                    "github_artifact_id":art,
                    "github_server_artifact_created_utc":server,
                    "attestation_source":source,
                    "audited_at_utc":audited}
                need(hash_obj(proof)==proofsha and
                     source=="GITHUB_HOST_ARCHIVED_ORIGINAL_SHADOW_SIX_SQLITE_BYTES",
                     "SHADOW_HOST_PROOF_IMMUTABLE_SHA_OR_SOURCE_INVALID")
                need(str(art).isdigit()
                     and as_utc(created)<=as_utc(server)
                     and as_utc(server)<=as_utc(kick)-timedelta(minutes=90)
                     and as_utc(server)<=as_utc(audited),
                     "HOST_PROOF_CLOCK_INVALID")
                passed.add(cid)
            result["github_host_verified_shadow_pairs"]=len(passed)
            result["github_host_artifact_proof_confirmed"]=bool(passed)
            if passed:
                marks=",".join("?" for _ in passed)
                n=db.execute(
                   "SELECT COUNT(*) FROM kb3_p1_shadow_six_host_proofs h "
                   "JOIN kb3_p1_shadow_six_new_only s ON s.id=h.shadow_sha256 "
                   "JOIN settlements t ON t.forecast_id=s.source_m0_forecast_sha256 "
                   "WHERE h.shadow_sha256 IN ("+marks+")",tuple(passed)).fetchone()[0]
                result["settled_github_host_verified_pairs"]=int(n)
                result["settled_attested_pair_confirmed"]=n>0
        if result["settled_attested_pair_confirmed"]:
            result["state"]="FIRST_GENUINE_HOST_ATTESTED_SETTLED_PAIR"
        elif result["github_host_artifact_proof_confirmed"]:
            result["state"]="GENUINE_HOST_ATTESTED_PREMATCH_PAIRS_NOT_SETTLED"
        elif result["real_pre_match_pair_confirmed"]:
            result["state"]="REAL_CAPTURED_PAIRS_PENDING_INDEPENDENT_GITHUB_HOST_PROOF"
        elif result["m0_new_since_activation"]>0:
            result["state"]="NEW_M0_CAPTURE_WITHOUT_ELIGIBLE_SHADOW_PAIRS"
        else:
            result["state"]="NOT_YET_FIRST_REAL_FORECAST"
    return result


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--db",type=Path,default=DB)
    ns=args.parse_args()
    result=audit(ns.db)
    print("KB3_FIRST_REAL_SHADOW_CHECKPOINT "+json.dumps(
        result,sort_keys=True,ensure_ascii=False))
    # Never silently approve a model or fill missing snapshots.
    need(result["official_fit_increment"]==0 and result["model_promotion"] is False,
         "RESEARCH_FIT_PROMOTION_FORBIDDEN")


if __name__=="__main__":
    main()
