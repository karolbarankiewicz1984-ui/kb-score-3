"""Read-only UEFA source evidence for KB3 GATE11.

Records original PitchAPI responses, true completed observation times and a
canonical hash chain. A sealed evidence bundle is NOT provider publish-time
proof or certification of historical prematch availability.
"""
from __future__ import annotations
import gzip
import hashlib
import io
import json
import os
from datetime import datetime,timezone,timedelta
from pathlib import Path

from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.kb3_pit_ledger import canonical,hexdigest,as_utc

SCHEMA="kb3-step11-pitch-uefa-evidence-v1"
MAGIC=b"KB3UE1\n"
AAD=b"KB3-STEP11-UEFA-NATIVE-XG-EVIDENCE-V1"
MAX_RAW=16*1024*1024


def add_observation(receipts,*,resource,payload,started,completed,origin="NETWORK_OBSERVED"):
    start,end=as_utc(started),as_utc(completed)
    if end<start or (end-start).total_seconds()>180:
        raise ValueError("UEFA_UNTRUSTWORTHY_CAPTURE_INTERVAL")
    if origin not in ("NETWORK_OBSERVED","SYNTHETIC_TEST"):
        raise ValueError("UEFA_CAPTURE_ORIGIN_UNKNOWN")
    if origin=="NETWORK_OBSERVED":
        now=datetime.now(timezone.utc)
        if (end-now).total_seconds()>10 or (now-end).total_seconds()>180:
            raise ValueError("UEFA_NETWORK_CAPTURE_CLOCK_INVALID")
    if not isinstance(resource,str) or not resource.startswith("pitchapi:"):
        raise ValueError("UEFA_RESOURCE_NOT_PITCH_NATIVE")
    if receipts and start<as_utc(receipts[-1]["completed_at_utc"]):
        raise ValueError("UEFA_NONMONOTONIC_RECEIPT")
    prior=receipts[-1]["chain_sha256"] if receipts else "0"*64
    receipt={"provider":"PitchAPI","resource":resource,
       "started_at_utc":started,"completed_at_utc":completed,"origin":origin,
       "original_published_at_utc":None,
       "payload_sha256":hexdigest(canonical(payload)),"payload":payload,
       "previous_sha256":prior}
    receipt["chain_sha256"]=hexdigest(canonical(receipt))
    receipts.append(receipt)
    return receipt["chain_sha256"]


def verify_receipts(receipts,*,allow_synthetic=False):
    previous="0"*64;previous_time=None
    allowed={"NETWORK_OBSERVED","SYNTHETIC_TEST"} if allow_synthetic else {"NETWORK_OBSERVED"}
    if not isinstance(receipts,list) or not receipts:
        raise ValueError("UEFA_EMPTY_SOURCE_RECEIPTS")
    resources=[]
    for entry in receipts:
        if not isinstance(entry,dict) or entry.get("origin") not in allowed:
            raise ValueError("UEFA_NON_REAL_EVIDENCE")
        item=dict(entry)
        chain=item.pop("chain_sha256",None)
        if (not chain or item.get("previous_sha256")!=previous or
            item.get("provider")!="PitchAPI" or
            item.get("original_published_at_utc") is not None):
            raise ValueError("UEFA_CHAIN_METADATA_MISMATCH")
        a,b=as_utc(item["started_at_utc"]),as_utc(item["completed_at_utc"])
        if a>b or (b-a).total_seconds()>180 or (previous_time and a<previous_time):
            raise ValueError("UEFA_CHAIN_TIME_INVALID")
        if hexdigest(canonical(item["payload"]))!=item["payload_sha256"]:
            raise ValueError("UEFA_TAMPERED_SOURCE_PAYLOAD")
        if hexdigest(canonical(item))!=chain:
            raise ValueError("UEFA_TAMPERED_CHAIN")
        previous,previous_time=chain,b
        resources.append(item["resource"])
    if len(resources)!=len(set(resources)):
        raise ValueError("UEFA_DUPLICATE_RESOURCE_RECEIPT")
    return {"sessions":len(receipts),"final_chain_sha256":previous,
            "resource_types":{prefix:sum(x.startswith(prefix) for x in resources)
             for prefix in ("pitchapi:catalog","pitchapi:uefa:","pitchapi:shots:")},
            "source_first_published_at_known":False,
            "training_allowed":False}


def seal(receipts,public_pem,out,manifest):
    proof=verify_receipts(receipts)
    public=serialization.load_pem_public_key(Path(public_pem).read_bytes())
    if not isinstance(public,rsa.RSAPublicKey) or public.key_size<3072:
        raise ValueError("UEFA_RECIPIENT_RSA_TOO_WEAK")
    raw=canonical({"schema":SCHEMA,"receipts":receipts})
    if len(raw)>MAX_RAW:
        raise ValueError("UEFA_RAW_TOO_LARGE")
    aes=os.urandom(32)
    nonce=os.urandom(12)
    keywrap=public.encrypt(aes,padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),label=None))
    cipher=MAGIC+len(keywrap).to_bytes(2,"big")+keywrap+nonce+AESGCM(aes).encrypt(
        nonce,gzip.compress(raw,mtime=0),AAD)
    fingerprint=hexdigest(public.public_bytes(
        serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo))
    meta={"schema":SCHEMA,"algorithms":"AES-256-GCM+RSA-OAEP-SHA256+gzip",
          "ciphertext_sha256":hexdigest(cipher),"ciphertext_bytes":len(cipher),
          "raw_sha256":hexdigest(raw),"raw_bytes":len(raw),
          "recipient_fingerprint_sha256":fingerprint,
          "proof":proof,"provider_publication_proven":False,
          "historical_prematch_pit_certified":False,
          "training_allowed":False,"offsite_restore_verified":False}
    dest,mp=Path(out),Path(manifest)
    if dest.exists() or mp.exists():
        raise FileExistsError("UEFA_ARCHIVE_DO_NOT_OVERWRITE")
    dest.parent.mkdir(parents=True,exist_ok=True)
    mp.parent.mkdir(parents=True,exist_ok=True)
    try:
        with dest.open("xb") as f:f.write(cipher)
        with mp.open("x",encoding="utf8") as f:
            json.dump(meta,f,sort_keys=True,indent=2);f.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True);mp.unlink(missing_ok=True);raise
    return meta


def restore(encrypted,manifest,private_key,*,allow_synthetic=False,
            include_receipts=False):
    meta=json.loads(Path(manifest).read_text("utf8"))
    if meta.get("schema")!=SCHEMA:
        raise ValueError("UEFA_ARCHIVE_SCHEMA_MISMATCH")
    blob=Path(encrypted).read_bytes()
    if len(blob)!=meta.get("ciphertext_bytes") or hexdigest(blob)!=meta.get("ciphertext_sha256"):
        raise ValueError("UEFA_ARCHIVE_CHECKSUM_MISMATCH")
    if not blob.startswith(MAGIC):
        raise ValueError("UEFA_ARCHIVE_MAGIC_INVALID")
    start=len(MAGIC);keysize=int.from_bytes(blob[start:start+2],"big")
    if not 256<=keysize<=1024:
        raise ValueError("UEFA_ARCHIVE_WRAP_SIZE_INVALID")
    private=serialization.load_pem_private_key(Path(private_key).read_bytes(),password=None)
    if not isinstance(private,rsa.RSAPrivateKey):
        raise ValueError("UEFA_INVALID_PRIVATE_KEY")
    fingerprint=hexdigest(private.public_key().public_bytes(
        serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo))
    if fingerprint!=meta.get("recipient_fingerprint_sha256"):
        raise ValueError("UEFA_WRONG_RECIPIENT_PRIVATE_KEY")
    start+=2
    aes=private.decrypt(blob[start:start+keysize],padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),label=None))
    pos=start+keysize
    compressed=AESGCM(aes).decrypt(blob[pos:pos+12],blob[pos+12:],AAD)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as f:
        raw=f.read(MAX_RAW+1)
    if len(raw)>MAX_RAW or len(raw)!=meta.get("raw_bytes") or hexdigest(raw)!=meta.get("raw_sha256"):
        raise ValueError("UEFA_DECRYPTED_HASH_INVALID")
    payload=json.loads(raw)
    if payload.get("schema")!=SCHEMA:
        raise ValueError("UEFA_PAYLOAD_SCHEMA_INVALID")
    proof=verify_receipts(payload["receipts"],allow_synthetic=allow_synthetic)
    if proof!=meta.get("proof"):
        raise ValueError("UEFA_PROVENANCE_CHECK_FAILED")
    result={"validated":True,"proof":proof,"training_allowed":False}
    if include_receipts:
        # Sensitive provider records: strictly caller-owned in-memory return,
        # never print or store in CI artifacts/public reports.
        result["receipts"]=payload["receipts"]
    return result
