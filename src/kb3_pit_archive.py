"""Step11 PIT: RSA-OAEP+AES-GCM sealed append-only observation-ledger backup.

Hash chain is tamper-evident when its terminal digest is anchored offsite.
Recorded observed_at is the CI system's clock, not provider publication time.
"""
from __future__ import annotations
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import padding,rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.kb3_pit_ledger import verify_chain
from src.kb3_xg_pit import verify_xg

MAGIC=b"KB3PIT1\n"
AAD=b"KB3-STEP11-PIT-OBSERVATION-LEDGER-V1"
MAX_SIZE=100*1024*1024

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def seal(source,recipient_public_key,dest,manifest,*,allow_synthetic=False):
    source,dest,manifest=Path(source),Path(dest),Path(manifest)
    if dest.exists() or manifest.exists():
        raise FileExistsError("DO_NOT_OVERWRITE_BACKUP")
    public=serialization.load_pem_public_key(Path(recipient_public_key).read_bytes())
    if not isinstance(public,rsa.RSAPublicKey) or public.key_size<3072:
        raise ValueError("RECIPIENT_PUBLIC_KEY_TOO_WEAK")
    with tempfile.TemporaryDirectory() as tmp:
        clean=Path(tmp)/"ledger.sqlite3"
        with sqlite3.connect(source) as original,sqlite3.connect(clean) as backup:
            original.backup(backup)
        with sqlite3.connect(clean) as check:
            evidence=verify_chain(check)
            has_xg=check.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pit_xg_observations'").fetchone() is not None
            xg_evidence=verify_xg(check) if has_xg else None
            origins=[r[0] for r in check.execute("SELECT DISTINCT origin FROM captures")]
            if not origins or (not allow_synthetic and origins!=["NETWORK_OBSERVED"]):
                raise ValueError("NON_REAL_CAPTURE_CANNOT_BE_PUBLISHED")
            if check.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("SQLITE_INTEGRITY_ERROR")
        if clean.stat().st_size>MAX_SIZE:
            raise ValueError("LEDGER_TOO_LARGE")
        raw=clean.read_bytes()
    aes=os.urandom(32)
    nonce=os.urandom(12)
    wrapped=public.encrypt(aes,padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    blob=MAGIC+len(wrapped).to_bytes(2,"big")+wrapped+nonce+AESGCM(aes).encrypt(
        nonce,gzip.compress(raw,mtime=0),AAD)
    meta={"schema":"kb3-pit-sealed-observation-v1",
          "created_at_utc":datetime.now(timezone.utc).isoformat(),
          "algorithms":"AES-256-GCM+RSA-OAEP-SHA256+gzip",
          "recipient_public_sha256":digest(public.public_bytes(
              serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)),
          "encrypted_sha256":digest(blob),"encrypted_bytes":len(blob),
          "sqlite_sha256":digest(raw),"sqlite_bytes":len(raw),
          "ledger_evidence":evidence,
          "xg_evidence":xg_evidence,
          "provider_publication_certified":False,
          "historical_before_observation_certified":False,
          "training_allowed":False,"prediction_enabled":False,
          "origin":"SYNTHETIC_TEST" if allow_synthetic else "NETWORK_OBSERVED",
          "offsite_verified":False}
    dest.parent.mkdir(parents=True,exist_ok=True)
    manifest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with dest.open("xb") as f:f.write(blob)
        with manifest.open("x",encoding="utf8") as f:
            json.dump(meta,f,sort_keys=True,indent=2)
            f.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise
    return meta

def restore(source,manifest,private_key,target):
    source,manifest,private_key,target=map(Path,(source,manifest,private_key,target))
    if target.exists():raise FileExistsError("RESTORE_MUST_CREATE_NEW_FILE")
    meta=json.loads(manifest.read_text("utf8"))
    if meta.get("schema")!="kb3-pit-sealed-observation-v1":
        raise ValueError("WRONG_MANIFEST_SCHEMA")
    blob=source.read_bytes()
    if digest(blob)!=meta.get("encrypted_sha256") or len(blob)!=meta.get("encrypted_bytes"):
        raise ValueError("ENCRYPTED_CHECKSUM_INVALID")
    if not blob.startswith(MAGIC):
        raise ValueError("INVALID_ARCHIVE_MAGIC")
    n=int.from_bytes(blob[len(MAGIC):len(MAGIC)+2],"big")
    if n<256 or n>1024:raise ValueError("INVALID_WRAPPED_KEY_SIZE")
    i=len(MAGIC)+2
    private=serialization.load_pem_private_key(private_key.read_bytes(),password=None)
    if not isinstance(private,rsa.RSAPrivateKey):
        raise ValueError("INVALID_PRIVATE_KEY")
    public_digest=digest(private.public_key().public_bytes(
        serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo))
    if public_digest!=meta.get("recipient_public_sha256"):
        raise ValueError("WRONG_RECIPIENT_KEY")
    aes=private.decrypt(blob[i:i+n],padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    compressed=AESGCM(aes).decrypt(blob[i+n:i+n+12],blob[i+n+12:],AAD)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as f:
        raw=f.read(MAX_SIZE+1)
    if len(raw)>MAX_SIZE or digest(raw)!=meta.get("sqlite_sha256"):
        raise ValueError("RESTORED_SQLITE_INVALID")
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with target.open("xb") as f:f.write(raw)
        with sqlite3.connect(target) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("RESTORE_SQLITE_INTEGRITY_FAILURE")
            found=verify_chain(db)
            if found!=meta["ledger_evidence"]:
                raise ValueError("RESTORE_CHAIN_MISMATCH")
            if meta.get("xg_evidence") is not None:
                xg=verify_xg(db)
                if xg!=meta["xg_evidence"]:
                    raise ValueError("RESTORE_XG_EVIDENCE_MISMATCH")
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {"restored":True,"evidence":found,
            "training_allowed":False,"historical_before_observation_certified":False}
