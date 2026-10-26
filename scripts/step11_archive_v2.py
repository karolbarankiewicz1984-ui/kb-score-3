"""KB3 Step11: hybrid encrypted SQLite archive; recipient secret is NEVER in CI.

AES-256-GCM sealed with a fresh per-archive random content key, then the
content key is wrapped by RSA-3072 OAEP-SHA256 to an offline public key.
Only ciphertext and safe aggregate manifest may leave the CI runner.
Historical data remain RETROSPECTIVE, never certified historical prematch.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"KB3ENC2\n"
AAD = b"KB3-STEP11-REPLAY-ARCHIVE-V2"
MAX_DB_BYTES = 64 * 1024 * 1024

def sha(b):
    return hashlib.sha256(b).hexdigest()

def require_counts(db, *, expected_fixtures, expected_by_year):
    with sqlite3.connect(db) as c:
        c.execute("PRAGMA foreign_keys=ON")
        integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
        violations = c.execute("PRAGMA foreign_key_check").fetchall()
        version = c.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        count = c.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]
        finished = c.execute("SELECT COUNT(*) FROM fixtures WHERE status='FINISHED' AND goals_home_90 IS NOT NULL AND goals_away_90 IS NOT NULL").fetchone()[0]
        maps = c.execute("SELECT COUNT(*) FROM fixture_provider_map WHERE match_quality='STRICT' AND review_status='APPROVED'").fetchone()[0]
        by_year = {str(y):n for y,n in c.execute("""
          SELECT s.start_year,COUNT(*) FROM fixtures f
          JOIN seasons s ON s.season_id=f.season_id GROUP BY s.start_year
        """)}
        classes = sorted(set(v for (v,) in c.execute("SELECT availability_class FROM source_snapshots")))
        if (integrity!="ok" or violations or version!=1 or count!=expected_fixtures
            or finished!=expected_fixtures or maps!=expected_fixtures or by_year!=expected_by_year
            or classes!=["RETROSPECTIVE"]):
            raise ValueError("ARCHIVE_SOURCE_NOT_APPROVED_REPLAY")
        return {"fixtures":count,"approved_provider_maps":maps,
                "by_year":by_year,"schema_version":version,
                "integrity_check":integrity,"foreign_key_violations":len(violations),
                "source_availability_classes":classes,
                "historical_point_in_time_certified":False,
                "training_allowed":False}

def encrypt(source, recipient_public_key, output, manifest, *,
            expected_fixtures=760, expected_by_year=None):
    source,output,manifest=Path(source),Path(output),Path(manifest)
    if expected_by_year is None:
        expected_by_year={"2023":380,"2024":380}
    if output.exists() or manifest.exists():
        raise FileExistsError("ARCHIVE_OUTPUT_EXISTS")
    public=serialization.load_pem_public_key(Path(recipient_public_key).read_bytes())
    if not isinstance(public,rsa.RSAPublicKey) or public.key_size<3072:
        raise ValueError("RECIPIENT_PUBLIC_KEY_TOO_WEAK")
    with tempfile.TemporaryDirectory() as tmp:
        clean=Path(tmp)/"consistent.sqlite3"
        with sqlite3.connect(source) as src,sqlite3.connect(clean) as dst:
            src.execute("PRAGMA foreign_keys=ON")
            src.backup(dst)
        evidence=require_counts(clean,expected_fixtures=expected_fixtures,
                                expected_by_year=expected_by_year)
        if clean.stat().st_size>MAX_DB_BYTES:
            raise ValueError("DB_TOO_LARGE_FOR_V2_ARCHIVE")
        raw=clean.read_bytes()
    wrapped_key=os.urandom(32)
    nonce=os.urandom(12)
    encrypted_key=public.encrypt(wrapped_key,padding.OAEP(
       mgf=padding.MGF1(algorithm=hashes.SHA256()),
       algorithm=hashes.SHA256(),label=None))
    ciphertext=AESGCM(wrapped_key).encrypt(nonce,gzip.compress(raw,mtime=0),AAD)
    blob=MAGIC+len(encrypted_key).to_bytes(2,"big")+encrypted_key+nonce+ciphertext
    if len(blob)>MAX_DB_BYTES:raise ValueError("ARCHIVE_ENCRYPTED_TOO_LARGE")
    metadata={"schema":"kb3-step11-encrypted-archive-v2",
              "created_utc":datetime.now(timezone.utc).isoformat(),
              "algorithm":"RSA-OAEP-SHA256+AES-256-GCM+gzip",
              "encryption_recipient_public_sha256":sha(
                  public.public_bytes(serialization.Encoding.DER,
                                      serialization.PublicFormat.SubjectPublicKeyInfo)),
              "encrypted_sha256":sha(blob),"encrypted_bytes":len(blob),
              "plaintext_sqlite_sha256":sha(raw),"sqlite_bytes":len(raw),
              "evidence":evidence,"archive_classification":"RETROSPECTIVE_ONLY",
              "historical_point_in_time_certified":False,
              "training_allowed":False,"trained_model":False,
              "source_fixture_payloads_exported":False,
              "recovery_private_key_stored_in_archive":False}
    output.parent.mkdir(parents=True,exist_ok=True)
    manifest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with output.open("xb") as stream:stream.write(blob)
        with manifest.open("x",encoding="utf8") as stream:
            json.dump(metadata,stream,sort_keys=True,indent=2)
            stream.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise
    return metadata

def restore(archive, manifest, private_key, destination):
    archive,manifest,destination=Path(archive),Path(manifest),Path(destination)
    if destination.exists():
        raise FileExistsError("RESTORE_TARGET_EXISTS")
    metadata=json.loads(manifest.read_text(encoding="utf8"))
    if metadata.get("schema")!="kb3-step11-encrypted-archive-v2":
        raise ValueError("INVALID_ARCHIVE_MANIFEST")
    blob=archive.read_bytes()
    if len(blob)!=metadata.get("encrypted_bytes") or sha(blob)!=metadata.get("encrypted_sha256"):
        raise ValueError("CIPHERTEXT_CHECKSUM_MISMATCH")
    if not blob.startswith(MAGIC):raise ValueError("INVALID_ARCHIVE_MAGIC")
    size=int.from_bytes(blob[len(MAGIC):len(MAGIC)+2],"big")
    if size<256 or size>1024:raise ValueError("INVALID_KEY_WRAP_SIZE")
    at=len(MAGIC)+2
    wrapped,nonce,ct=blob[at:at+size],blob[at+size:at+size+12],blob[at+size+12:]
    private=serialization.load_pem_private_key(Path(private_key).read_bytes(),password=None)
    if not isinstance(private,rsa.RSAPrivateKey):
        raise ValueError("WRONG_PRIVATE_KEY_TYPE")
    public_der=private.public_key().public_bytes(serialization.Encoding.DER,
                                                serialization.PublicFormat.SubjectPublicKeyInfo)
    if sha(public_der)!=metadata.get("encryption_recipient_public_sha256"):
        raise ValueError("RECIPIENT_KEY_MISMATCH")
    key=private.decrypt(wrapped,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                            algorithm=hashes.SHA256(),label=None))
    # Don't decompress outside a bounded validated ciphertext.
    compressed=AESGCM(key).decrypt(nonce,ct,AAD)
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as gz:
        raw=gz.read(MAX_DB_BYTES+1)
    if len(raw)>MAX_DB_BYTES or sha(raw)!=metadata.get("plaintext_sqlite_sha256"):
        raise ValueError("PLAINTEXT_CHECKSUM_MISMATCH")
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:
        with destination.open("xb") as stream:stream.write(raw)
        evidence=metadata["evidence"]
        actual=require_counts(destination,
             expected_fixtures=evidence["fixtures"],
             expected_by_year=evidence["by_year"])
        if actual!=evidence:raise ValueError("RESTORED_EVIDENCE_MISMATCH")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return {"status":"RESTORE_PASS","fixtures":evidence["fixtures"],
            "by_year":evidence["by_year"],"integrity":"ok",
            "historical_point_in_time_certified":False,"training_allowed":False}

def main():
    p=argparse.ArgumentParser()
    sp=p.add_subparsers(dest="operation",required=True)
    a=sp.add_parser("encrypt")
    a.add_argument("--db",required=True)
    a.add_argument("--public-key",required=True)
    a.add_argument("--out",required=True)
    a.add_argument("--manifest",required=True)
    b=sp.add_parser("restore")
    b.add_argument("--archive",required=True)
    b.add_argument("--manifest",required=True)
    b.add_argument("--private-key",required=True)
    b.add_argument("--target",required=True)
    x=p.parse_args()
    if x.operation=="encrypt":
        meta=encrypt(x.db,x.public_key,x.out,x.manifest)
        print(json.dumps({"status":"ENCRYPTED","fixtures":meta["evidence"]["fixtures"],
                          "ciphertext_sha256":meta["encrypted_sha256"],
                          "historical_point_in_time_certified":False},sort_keys=True))
    else:
        print(json.dumps(restore(x.archive,x.manifest,x.private_key,x.target),
                         sort_keys=True))

if __name__=="__main__":
    main()
