"""Decrypt and independently validate a KB3 Step09 offsite SQLite archive.

Requires: pip install cryptography
Key stays outside GitHub and Google Drive. Restore ALWAYS creates a new file.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC=b"KB3ENC1\n"
AAD=b"KB3_STEP09_PL_2024_V1"

def digest(b):
    return hashlib.sha256(b).hexdigest()

def read_key(file_path):
    txt=Path(file_path).read_text(encoding="utf-8")
    lines=[l[8:].strip() for l in txt.splitlines() if l.startswith("KEY_HEX=")]
    if len(lines)!=1:
        raise ValueError("INVALID_RECOVERY_KEY_FILE")
    key=bytes.fromhex(lines[0])
    if len(key)!=32:
        raise ValueError("AES256_KEY_REQUIRED")
    return key

def restore(archive,keyfile,manifest,target):
    archive=Path(archive)
    target=Path(target)
    if target.exists():
        raise FileExistsError("TARGET_EXISTS_NO_OVERWRITE")
    meta=json.loads(Path(manifest).read_text(encoding="utf-8"))
    if meta.get("schema")!="kb3-step09-offsite-archive-v1":
        raise ValueError("INVALID_MANIFEST")
    data=archive.read_bytes()
    if digest(data)!=meta["encrypted_sha256"] or len(data)!=meta["encrypted_size_bytes"]:
        raise ValueError("ENCRYPTED_CHECKSUM_FAILURE")
    if not data.startswith(MAGIC) or len(data)<36:
        raise ValueError("INVALID_ARCHIVE_FORMAT")
    raw=gzip.decompress(AESGCM(read_key(keyfile)).decrypt(
        data[len(MAGIC):len(MAGIC)+12],data[len(MAGIC)+12:],AAD))
    if digest(raw)!=meta["plaintext_sqlite_sha256"]:
        raise ValueError("SQLITE_CHECKSUM_FAILURE")
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        target.write_bytes(raw)
        with sqlite3.connect(target) as c:
            integrity=c.execute("PRAGMA integrity_check").fetchone()[0]
            violations=c.execute("PRAGMA foreign_key_check").fetchall()
            fixtures=c.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]
            maps=c.execute("SELECT COUNT(*) FROM fixture_provider_map").fetchone()[0]
            finished=c.execute("SELECT COUNT(*) FROM fixtures WHERE status='FINISHED'").fetchone()[0]
            if integrity!="ok" or violations or (fixtures,maps,finished)!=(380,380,380):
                raise ValueError("RESTORED_DATABASE_INTEGRITY_FAILURE")
        return {"status":"PASS","fixtures":fixtures,"map_count":maps,
                "sha256":digest(raw),"integrity":integrity}
    except BaseException:
        target.unlink(missing_ok=True)
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--key-file",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--target",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(restore(a.archive,a.key_file,a.manifest,a.target)))
if __name__=="__main__":
    main()
