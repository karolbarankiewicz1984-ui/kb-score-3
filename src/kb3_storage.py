"""KB Score 3.0 — step 08 SQLite and verified backups (standard library).

No external API, ML, financial decisions or real personal data.
Actual production backups MUST be encrypted before external storage.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "001_initial_schema.sql"
SCHEMA_VERSION = 1

def connect(path):
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection

def initialize(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(MIGRATION.read_text(encoding="utf-8"))
        verify_database(conn)
    return path

def verify_database(conn):
    r = conn.execute("PRAGMA integrity_check").fetchone()
    if not r or r[0] != "ok":
        raise ValueError("DATABASE_INTEGRITY_FAILURE")
    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("DATABASE_FOREIGN_KEY_FAILURE")
    ver = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    if ver != SCHEMA_VERSION:
        raise ValueError("SCHEMA_VERSION_MISMATCH")
    return {"integrity": "ok", "foreign_keys": "ok", "schema_version": ver}

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def backup_database(source, output_dir):
    """SQLite atomic online backup to separate .sqlite3; SHA256 external manifest.

    IMPORTANT: resulting files are unencrypted. Only upload fully synthetic
    test backups or use dedicated encrypted storage in later production steps.
    """
    source = Path(source)
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    backup_id = (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                 + "-" + uuid.uuid4().hex[:10])
    target = dest / ("kb3-backup-" + backup_id + ".sqlite3")
    manifest_path = dest / ("kb3-backup-" + backup_id + ".manifest.json")
    with connect(source) as src, connect(target) as dst:
        verify_database(src)
        src.backup(dst, pages=100, sleep=0.01)
        summary = verify_database(dst)
        table_rows = {
            row[0]: dst.execute('SELECT COUNT(*) FROM "' + row[0] + '"').fetchone()[0]
            for row in dst.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        }
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {
        "schema": "kb3-backup-manifest-v1",
        "backup_id": backup_id,
        "created_utc": now,
        "snapshot_file": target.name,
        "sha256": file_hash(target),
        "size_bytes": target.stat().st_size,
        "integrity": summary,
        "row_counts": table_rows,
        "storage_classification": "SYNTHETIC_TEST_ONLY",
        "production_encryption_required": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path, target

def restore_database(manifest_path, source_dir, restored_path):
    """Validate checksum, restore to a *new* file and verify integrity/row counts."""
    manifest_path = Path(manifest_path)
    source_dir = Path(source_dir)
    restored_path = Path(restored_path)
    meta = json.loads(manifest_path.read_text(encoding="utf-8"))
    if meta.get("schema") != "kb3-backup-manifest-v1":
        raise ValueError("INVALID_BACKUP_MANIFEST")
    snapshot = meta.get("snapshot_file")
    if (not isinstance(snapshot, str) or not snapshot.startswith("kb3-backup-")
        or Path(snapshot).name != snapshot or not snapshot.endswith(".sqlite3")):
        raise ValueError("UNSAFE_BACKUP_FILENAME")
    backup = source_dir / snapshot
    if backup.stat().st_size != meta.get("size_bytes") or file_hash(backup) != meta.get("sha256"):
        raise ValueError("BACKUP_CHECKSUM_MISMATCH")
    if restored_path.exists():
        raise FileExistsError("RESTORE_TARGET_ALREADY_EXISTS")
    restored_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with connect(backup) as src, connect(restored_path) as dst:
            src.backup(dst, pages=100, sleep=0.01)
            check = verify_database(dst)
            if check != meta["integrity"]:
                raise ValueError("RESTORED_INTEGRITY_DIFFERS")
            for name, expected in meta["row_counts"].items():
                if name not in {
                    v[0] for v in dst.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }:
                    raise ValueError("RESTORE_MISSING_TABLE")
                got = dst.execute('SELECT COUNT(*) FROM "' + name.replace('"','""') + '"').fetchone()[0]
                if got != expected:
                    raise ValueError("RESTORE_ROW_COUNT_DIFFERS")
        return {"restored": True, "backup_id": meta["backup_id"],
                "source_sha256": meta["sha256"], "integrity": check,
                "tables": len(meta["row_counts"])}
    except BaseException:
        restored_path.unlink(missing_ok=True)
        raise

def main():
    parser = argparse.ArgumentParser(description="KB3 step 08 storage tools")
    parser.add_argument("operation", choices=["init", "backup", "restore", "verify"])
    parser.add_argument("--db", type=Path)
    parser.add_argument("--folder", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    if args.operation == "init":
        print(json.dumps({"initialized": str(initialize(args.db))}))
    elif args.operation == "verify":
        with connect(args.db) as conn:
            print(json.dumps(verify_database(conn)))
    elif args.operation == "backup":
        mf, db = backup_database(args.db, args.folder)
        meta = json.loads(mf.read_text())
        print(json.dumps({"backup_id": meta["backup_id"], "db": str(db),
                          "manifest": str(mf), "sha256": meta["sha256"]}))
    elif args.operation == "restore":
        print(json.dumps(restore_database(args.manifest, args.folder, args.target)))

if __name__ == "__main__":
    main()
