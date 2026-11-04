"""Seal the current source SQLite with the existing owner RSA public key.

Only AES-GCM encrypted bytes and a SHA manifest may be persisted/uploaded.
The private key must NEVER be accessible to this workflow. Encrypted current
database is not historical provider publication proof or production approval.
"""
from __future__ import annotations
import hashlib
import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/forward_m0_720_eight/kb3_forward_eight.sqlite"
PUBLIC=ROOT/"config/step11_archive_recipient_public.pem"
OUTPUT=ROOT/"audit/step01_backup_encrypted"
MAGIC=b"KB3DB1\n"
AAD=b"KB3-STEP01-M0-REAL-SQLITE-BACKUP-2026-11-04"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def create(root=ROOT):
    root=Path(root)
    src=root/SOURCE.relative_to(ROOT)
    out=root/OUTPUT.relative_to(ROOT)
    public_path=root/PUBLIC.relative_to(ROOT)
    if out.exists():
        raise FileExistsError("ENCRYPTED_BACKUP_DIRECTORY_ALREADY_EXISTS")
    key=serialization.load_pem_public_key(public_path.read_bytes())
    if not isinstance(key,rsa.RSAPublicKey) or key.key_size<3072:
        raise ValueError("OWNER_RSA_KEY_TOO_WEAK")
    clear=src.read_bytes()
    if not clear.startswith(b"SQLite format 3\\x00".replace(b"\\x00", b"\x00")):
        raise ValueError("SQLITE_SOURCE_FORMAT_INVALID")
    aes=os.urandom(32)
    nonce=os.urandom(12)
    wrapped=key.encrypt(aes, padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=None))
    cipher=MAGIC+len(wrapped).to_bytes(2,"big")+wrapped+nonce+AESGCM(aes).encrypt(
        nonce,gzip.compress(clear,mtime=0),AAD)
    out.mkdir(parents=True,exist_ok=False)
    encrypted=out/"M0_REAL_SQLITE_2026-11-04.enc"
    manifest=out/"M0_REAL_SQLITE_2026-11-04.manifest.json"
    with encrypted.open("xb") as file:file.write(cipher)
    checks={
      "schema":"kb3-step01-current-m0-encrypted-sqlite-v1",
      "source_classification":"CURRENT_REAL_RESEARCH_SQLITE_NOT_PRODUCTION",
      "original_source_path":"data/forward_m0_720_eight/kb3_forward_eight.sqlite",
      "plaintext_sha256":sha(clear),
      "plaintext_bytes":len(clear),
      "encrypted_sha256":sha(cipher),
      "encrypted_bytes":len(cipher),
      "algorithms":"RSA-OAEP-SHA256+AES-256-GCM+gzip",
      "aad":AAD.decode(),
      "rsa_recipient_public_sha256":sha(key.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)),
      "rsa_private_key_stored":False,
      "encrypted_header_valid":cipher.startswith(MAGIC),
      "metadata_only_not_a_restore":True,
      "offsite_upload_verified":False,
      "owner_private_key_decrypt_test_pending":True,
      "source_revision":os.environ.get("GITHUB_SHA","UNSET"),
      "created_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    with manifest.open("x",encoding="utf8") as file:
        json.dump(checks,file,ensure_ascii=False,indent=2,sort_keys=True)
        file.write("\n")
    if encrypted.stat().st_size!=checks["encrypted_bytes"] or sha(encrypted.read_bytes())!=checks["encrypted_sha256"]:
        raise ValueError("ENCRYPTED_BACKUP_READBACK_MISMATCH")
    # No plaintext, private key, or source DB is written to the output directory.
    if sorted(x.name for x in out.iterdir())!=sorted([encrypted.name,manifest.name]):
        raise AssertionError("EXTRA_BACKUP_OUTPUT_UNSAFE")
    print(json.dumps({k:v for k,v in checks.items() if k in (
        "schema","source_classification","plaintext_sha256","plaintext_bytes","encrypted_sha256",
        "encrypted_bytes","rsa_private_key_stored","source_revision","owner_private_key_decrypt_test_pending"
    )},sort_keys=True))
    return checks

if __name__=="__main__":
    create()
