"""Sealed PitchAPI-native ledger, distinct crypto context from API-Football PIT.

Never ship a private key to Actions; use the existing public recipient PEM.
An offsite manifest hash is only a claim until a separately stored copy has
been downloaded, decrypted and independently verified.
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
from src.kb3_pitch_native_ledger import verify

MAGIC=b"KB3PN1\n"
AAD=b"KB3-STEP11-PITCH-NATIVE-OBSERVATION-LEDGER-V1"
MAX_SIZE=100*1024*1024

def digest(blob):return hashlib.sha256(blob).hexdigest()

def seal(source,public_pem,dest,manifest,*,allow_synthetic=False):
    source,public_pem,dest,manifest=map(Path,(source,public_pem,dest,manifest))
    if dest.exists() or manifest.exists():
        raise FileExistsError("NATIVE_ARCHIVE_CANNOT_BE_OVERWRITTEN")
    public=serialization.load_pem_public_key(public_pem.read_bytes())
    if not isinstance(public,rsa.RSAPublicKey) or public.key_size<3072:
        raise ValueError("RECIPIENT_PUBLIC_KEY_INSUFFICIENT")
    with tempfile.TemporaryDirectory() as temp:
        clean=Path(temp)/"clean-native.sqlite3"
        with sqlite3.connect(source) as a,sqlite3.connect(clean) as b:
            a.backup(b)
        with sqlite3.connect(clean) as db:
            proof=verify(db)
            if proof["fixture_captures"]!=1 or proof["shot_captures"]<1:
                raise ValueError("NATIVE_CAPTURE_SCOPE_INCOMPLETE")
            origins=[x[0] for x in db.execute(
                "SELECT DISTINCT origin FROM pitch_captures")]
            if len(origins)!=1 or origins[0]!=(
                "SYNTHETIC_TEST" if allow_synthetic else "NETWORK_OBSERVED"):
                raise ValueError("UNVERIFIED_NATIVE_OBSERVATION")
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("NATIVE_SQLITE_INTEGRITY_FAILURE")
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("NATIVE_SQLITE_FOREIGN_KEY_FAILURE")
        if clean.stat().st_size>MAX_SIZE:
            raise ValueError("NATIVE_SOURCE_TOO_LARGE")
        raw=clean.read_bytes()
    aes=os.urandom(32);nonce=os.urandom(12)
    encrypted_aes=public.encrypt(aes,padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),label=None))
    ciphertext=MAGIC+len(encrypted_aes).to_bytes(2,"big")+encrypted_aes+nonce+AESGCM(aes).encrypt(
        nonce,gzip.compress(raw,mtime=0),AAD)
    manifest_data={
       "schema":"kb3-pitch-native-sealed-observation-v1",
       "created_at_utc":datetime.now(timezone.utc).isoformat(),
       "algorithm":"AES-256-GCM+RSA-OAEP-SHA256+gzip",
       "encrypted_sha256":digest(ciphertext),
       "encrypted_bytes":len(ciphertext),
       "sqlite_sha256":digest(raw),
       "sqlite_bytes":len(raw),
       "recipient_public_sha256":digest(public.public_bytes(
           serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)),
       "chain_evidence":proof,
       "provider":"PitchAPI",
       "original_publication_verified":False,
       "retrospective_pit_verified":False,
       "training_allowed":False,
       "production_switch_approved":False,
       "offsite_restore_verified":False,
       "origin":"SYNTHETIC_TEST" if allow_synthetic else "NETWORK_OBSERVED"}
    dest.parent.mkdir(parents=True,exist_ok=True)
    manifest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with dest.open("xb") as h:h.write(ciphertext)
        with manifest.open("x",encoding="utf8") as h:
            json.dump(manifest_data,h,sort_keys=True,indent=2);h.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True);manifest.unlink(missing_ok=True);raise
    return manifest_data

def restore(cipherpath,manifestpath,privatepath,targetpath):
    cipherpath,manifestpath,privatepath,targetpath=map(
        Path,(cipherpath,manifestpath,privatepath,targetpath))
    if targetpath.exists():
        raise FileExistsError("RESTORE_TARGET_ALREADY_EXISTS")
    meta=json.loads(manifestpath.read_text("utf8"))
    if meta.get("schema")!="kb3-pitch-native-sealed-observation-v1":
        raise ValueError("NATIVE_MANIFEST_SCHEMA_MISMATCH")
    ct=cipherpath.read_bytes()
    if len(ct)!=meta.get("encrypted_bytes") or digest(ct)!=meta.get("encrypted_sha256"):
        raise ValueError("NATIVE_CIPHERTEXT_SHA_MISMATCH")
    if not ct.startswith(MAGIC):
        raise ValueError("NATIVE_CIPHERTEXT_MAGIC_MISMATCH")
    start=len(MAGIC)
    n=int.from_bytes(ct[start:start+2],"big")
    if not 256<=n<=1024:
        raise ValueError("NATIVE_WRAPPED_KEY_SIZE_INVALID")
    private=serialization.load_pem_private_key(privatepath.read_bytes(),password=None)
    if not isinstance(private,rsa.RSAPrivateKey):
        raise ValueError("NATIVE_WRONG_PRIVATE_KEY")
    digest_pub=digest(private.public_key().public_bytes(
        serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo))
    if digest_pub!=meta.get("recipient_public_sha256"):
        raise ValueError("NATIVE_PUBLIC_KEY_SHA_MISMATCH")
    start+=2
    aes=private.decrypt(ct[start:start+n],padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),label=None))
    at=start+n
    plain=AESGCM(aes).decrypt(ct[at:at+12],ct[at+12:],AAD)
    with gzip.GzipFile(fileobj=io.BytesIO(plain)) as zipped:
        raw=zipped.read(MAX_SIZE+1)
    if len(raw)>MAX_SIZE or digest(raw)!=meta.get("sqlite_sha256"):
        raise ValueError("NATIVE_UNCOMPRESSED_SQLITE_MISMATCH")
    targetpath.parent.mkdir(parents=True,exist_ok=True)
    try:
        with targetpath.open("xb") as h:h.write(raw)
        with sqlite3.connect(targetpath) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("NATIVE_RESTORE_SQLITE_INVALID")
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("NATIVE_RESTORE_SQLITE_FOREIGN_KEY_INVALID")
            proof=verify(db)
            if proof!=meta["chain_evidence"]:
                raise ValueError("NATIVE_RESTORE_CHAIN_DIFFERS")
    except BaseException:
        targetpath.unlink(missing_ok=True);raise
    return {"restored":True,"evidence":proof,"training_allowed":False,
            "historical_pit_verified":False}
