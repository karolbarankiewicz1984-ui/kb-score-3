"""Step13 / task4: prospective result collector, STRICT original ten native IDs.

NOT AUTOMATICALLY INVOKED. UTC >= final kickoff +3h and every match must
actually be finished. Calls exactly ten SDK matches.get native endpoints;
never calls a season-level played/all listing. Raw payload is sealed
under the owner's existing RSA public key with a NEW unique Step13 AES AAD;
only encrypted evidence, public manifest and aggregate evaluation leave CI.
Private key never accessed; a locally verified hash chain alone cannot
certify provider time of first publication or an independent offsite restore.
"""
from __future__ import annotations
from datetime import datetime,timezone
import argparse,gzip,hashlib,json,os
from pathlib import Path
from src.kb3_pit_ledger import canonical,as_utc,utc_now
from src.kb3_pitch_uefa_evidence import add_observation,verify_receipts
from src.kb3_step13_forward_score import _check_snapshot,score_locked_first_ten,SOURCE_FILE,MIN_FINAL_LAG,SOURCE_HASH
from src.kb3_split import sha,timestamp,freeze_manifest
from src.kb3_step13_baseline import BaselineSafetyError
from scripts.pitchapi_step06_audit import to_plain

AAD=b"KB3-STEP13-EXACT-TEN-PITCHAPI-RESULT-RECEIPTS-V1"
MAGIC=b"KB3S13R1\n"
OUTPUT_PREFIX="audit/step13/forward-ten-evidence"

def check_earliest_frozen(snapshot,now_utc):
    indexed=_check_snapshot(snapshot)
    moment=timestamp(now_utc)
    if moment<max(timestamp(x["kickoff_utc"])+MIN_FINAL_LAG for x in indexed.values()):
        raise BaselineSafetyError("STEP13_FINAL_NO_ACCESS_BEFORE_ALL_FINAL_LAG")
    return indexed

def validate_captured_receipts(snapshot,observations,*,evaluation_time,allow_synthetic=False):
    indexed=check_earliest_frozen(snapshot,evaluation_time)
    if (not isinstance(observations,list) or len(observations)!=10):
        raise BaselineSafetyError("STEP13_FINAL_EXACTLY_10_RECEIPTS")
    origin="SYNTHETIC_TEST" if allow_synthetic else "NETWORK_OBSERVED"
    if any(x.get("origin")!=origin for x in observations):
        raise BaselineSafetyError("STEP13_FINAL_WRONG_OBSERVATION_ORIGIN")
    proof=verify_receipts(observations,allow_synthetic=allow_synthetic)
    if proof["sessions"]!=10:
        raise BaselineSafetyError("STEP13_FINAL_INCOMPLETE_CHAIN")
    raw_receipts=[]
    observed_ids=set()
    for item in observations:
        body=item["payload"]
        payload=body.get("data",body)
        if not isinstance(payload,dict):
            raise BaselineSafetyError("STEP13_FINAL_INVALID_PROVIDER_BODY")
        mid=payload.get("id")
        if mid not in indexed or mid in observed_ids or item["resource"]!=f"pitchapi:step13:final:{mid}":
            raise BaselineSafetyError("STEP13_FINAL_NON_TARGET_OR_DUPLICATE")
        observed_ids.add(mid)
        expected=indexed[mid]
        home=payload.get("home_team") or {}
        away=payload.get("away_team") or {}
        if (home.get("id")!=expected["home_team_id"] or
            away.get("id")!=expected["away_team_id"] or
            timestamp(payload.get("time_utc"))!=timestamp(expected["kickoff_utc"]) or
            payload.get("status")!="finished"):
            raise BaselineSafetyError("STEP13_FINAL_SOURCE_IDENTITY_OR_STATUS")
        a,b=payload.get("score_home"),payload.get("score_away")
        if (type(a) is not int or type(b) is not int or
             not 0<=a<=30 or not 0<=b<=30):
            raise BaselineSafetyError("STEP13_FINAL_90MIN_RESULT_INVALID")
        raw_receipts.append({
            "fixture_id":mid,"home_team_id":home["id"],
            "away_team_id":away["id"],"kickoff_utc":payload["time_utc"],
            "status":"finished","goals_home_90":a,"goals_away_90":b,
            "observed_at_utc":item["completed_at_utc"],
            "source":"PitchAPI","capture_sha256":item["payload_sha256"],
        })
    result=score_locked_first_ten(snapshot,raw_receipts,
                       scoring_observed_at_utc=evaluation_time)
    if allow_synthetic:
        result["source_evidence_kind"]="SYNTHETIC_TEST_ONLY"
    else:
        result["source_evidence_kind"]="NETWORK_OBSERVED_MATCH_GET"
    result["capture_chain_locally_verified"]=True
    result["capture_chain_final_sha256"]=proof["final_chain_sha256"]
    result["exactly_ten_individual_provider_calls"]=10
    result["other_test_results_requested"]=0
    result["original_provider_publication_clock_proven"]=False
    result["independent_restore_of_sealed_evidence_pending"]=True
    result["gate13_pass"]=False
    result["training_allowed"]=False
    result["report_sha256"]=sha({k:v for k,v in result.items() if k!="report_sha256"})
    return result,proof

def seal_evidence(observations,proof,*,recipient,encrypted_path,manifest_path):
    """New cryptographic context: AES-256-GCM + RSA-OAEP SHA256."""
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import padding,rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    public=serialization.load_pem_public_key(Path(recipient).read_bytes())
    if not isinstance(public,rsa.RSAPublicKey) or public.key_size<3072:
        raise BaselineSafetyError("STEP13_FINAL_WEAK_RSA_PUBLIC_KEY")
    raw=canonical({"schema":"kb3-step13-exact-ten-results-receipts-v1",
                   "observations":observations,"proof":proof})
    if len(raw)>2*1024*1024:
        raise BaselineSafetyError("STEP13_FINAL_RAW_EVIDENCE_TOO_LARGE")
    key=os.urandom(32)
    wrapped=public.encrypt(key,padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),label=None))
    nonce=os.urandom(12)
    ciphertext=MAGIC+len(wrapped).to_bytes(2,"big")+wrapped+nonce+AESGCM(key).encrypt(
        nonce,gzip.compress(raw,mtime=0),AAD)
    dest=Path(encrypted_path);manifest=Path(manifest_path)
    if dest.exists() or manifest.exists():
        raise FileExistsError("STEP13_FINAL_EVIDENCE_IMMUTABLE_DO_NOT_OVERWRITE")
    meta={"schema":"kb3-step13-exact-ten-aes-gcm-rsa-evidence-v1",
       "encrypted_sha256":hashlib.sha256(ciphertext).hexdigest(),
       "encrypted_bytes":len(ciphertext),
       "raw_sha256":hashlib.sha256(raw).hexdigest(),
       "raw_bytes":len(raw),
       "source_chain_sha256":proof["final_chain_sha256"],
       "resource_count":10,
       "algorithm":"AES-256-GCM_RSA-OAEP-SHA256_DISTINCT_STEP13_AAD",
       "recipient_public_sha256":hashlib.sha256(public.public_bytes(
           serialization.Encoding.DER,
           serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest(),
       "independent_decryption_verified":False,
       "source_first_pubtime_known":False,
       "historical_prematch_pit_certified":False,
       "training_allowed":False}
    dest.parent.mkdir(parents=True,exist_ok=True)
    manifest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as out:out.write(ciphertext)
    with manifest.open("x",encoding="utf8") as out:
        json.dump(meta,out,sort_keys=True,indent=2);out.write("\n")
    return meta

def collect_once(*,output_prefix=OUTPUT_PREFIX,recipient="config/step11_archive_recipient_public.pem"):
    # Must check original hash and all kickoff time gates BEFORE any networking.
    snapshot=json.loads(Path(SOURCE_FILE).read_text(encoding="utf8"))
    indexed=check_earliest_frozen(snapshot,utc_now())
    key=os.getenv("PITCHAPI_API_KEY","").strip()
    if not key:raise BaselineSafetyError("STEP13_FINAL_PITCH_KEY_MISSING")
    if any(Path(output_prefix+s).exists() for s in (".enc",".manifest.json",".aggregate.json")):
        raise FileExistsError("STEP13_FINAL_OUTPUT_ALREADY_EXISTS")
    from pitchapi import PitchAPI
    client=PitchAPI(api_key=key)
    evidence=[]
    # Ten individual match reads only: no leagues.matches(status=played/all)
    # no date endpoint, no other TEST labels, no retries in this script.
    for mid in sorted(indexed):
        t0=utc_now()
        m=to_plain(client.matches.get(mid))
        t1=utc_now()
        add_observation(evidence,resource=f"pitchapi:step13:final:{mid}",
                        payload=m,started=t0,completed=t1)
    evaluated=utc_now()
    report,proof=validate_captured_receipts(snapshot,evidence,evaluation_time=evaluated)
    paths={s:output_prefix+s for s in (".enc",".manifest.json",".aggregate.json")}
    crypt=seal_evidence(evidence,proof,recipient=recipient,
         encrypted_path=paths[".enc"],manifest_path=paths[".manifest.json"])
    report["encrypted_source_sha256"]=crypt["encrypted_sha256"]
    report["encrypted_source_manifest_sha256"]=sha(crypt)
    report["report_sha256"]=sha({k:v for k,v in report.items() if k!="report_sha256"})
    freeze_manifest(report,paths[".aggregate.json"])
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-prefix",default=OUTPUT_PREFIX)
    p.add_argument("--recipient",default="config/step11_archive_recipient_public.pem")
    z=p.parse_args()
    try:
        r=collect_once(output_prefix=z.output_prefix,recipient=z.recipient)
        print("STEP13_TEN_PROSPECTIVE_AGGREGATE_ONLY",
              "n",r["prospective_evaluation_target_count"],
              "accuracy",r["top1_1x2_accuracy"],
              "logloss",r["multiclass_1x2_logloss"],
              "brier",r["multiclass_1x2_brier_sum3"],
              "test_other_results_requested",r["other_test_results_requested"],
              "GATE13",r["gate13_pass"],"SHA",r["report_sha256"])
    except Exception as e:
        print("STEP13_TEN_PROSPECTIVE_COLLECTOR_BLOCKED",type(e).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
