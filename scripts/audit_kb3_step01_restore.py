"""Read-only pre-merge snapshot/restore preflight for KB Score 3.0 M0.

This verifies the repository SQLite and a restored, independent local copy.
It does NOT establish existence of a fresh OFF-SITE copy; see status field.
No provider calls, fit, archive rewriting or protected TEST access.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/forward_m0_720_eight/kb3_forward_eight.sqlite"
MANIFEST = ROOT / "models/research/M0_720_TRAIN_STABLE_CANDIDATE_20261029.json"
FORECAST = ROOT / "data/forecasts/m0_720_eight/2026-11-04/FROZEN_M0_720_EIGHT.json"
MODEL = "M0_ELO_POISSON_RESEARCH_720TRAIN_V1"
IMMUTABLE = (
    "research_forecast_no_update", "research_forecast_no_delete",
    "research_settlement_no_update", "research_settlement_no_delete",
    "research_model_no_update", "research_model_no_delete",
)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

def require(ok, reason):
    if not ok:
        raise AssertionError(reason)

def ro(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)

def snapshot(conn):
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLITE_INTEGRITY_FAILURE")
    require(conn.execute("PRAGMA foreign_key_check").fetchall() == [], "SQLITE_FOREIGN_KEY_FAILURE")
    tables = sorted(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    signature = {}
    for name in tables:
        require('"' not in name, "UNSAFE_TABLE_NAME")
        vals = [list(row) for row in conn.execute(f'SELECT * FROM "{name}"')]
        signature[name] = {
            "rows": len(vals),
            "sha256": hashlib.sha256(canon(sorted(vals, key=lambda x: repr(x)))).hexdigest(),
        }
    triggers = set(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'"))
    require(set(IMMUTABLE).issubset(triggers), "IMMUTABILITY_TRIGGER_MISSING")
    return signature

def verify(root=ROOT):
    root = Path(root)
    db = root / SOURCE.relative_to(ROOT)
    manifest = root / MANIFEST.relative_to(ROOT)
    archive = root / FORECAST.relative_to(ROOT)
    for file in (db, manifest, archive):
        require(file.is_file() and file.stat().st_size > 0, "REQUIRED_ARCHIVE_MISSING:" + str(file))
    m = json.loads(manifest.read_text(encoding="utf-8"))
    require(m["candidate_id"] == MODEL and m["production_approved"] is False, "MODEL_NOT_RESEARCH")
    param_hash = hashlib.sha256(canon(m["fitted_parameters"])).hexdigest()
    manifest_hash = hashlib.sha256(canon(m)).hexdigest()
    with ro(db) as original:
        start = snapshot(original)
        require({"model_meta", "forecasts", "settlements"}.issubset(start), "M0_TABLE_MISSING")
        meta = original.execute(
            "SELECT model,parameters_sha256,manifest_sha256,status FROM model_meta").fetchall()
        require(meta == [(MODEL, param_hash, manifest_hash, "RESEARCH_ONLY_NOT_APPROVED")],
                "MODEL_SHA_OR_VERSION_CHANGED")
        fcount = original.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
        scount = original.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
        require(fcount >= scount and fcount > 0, "M0_COUNTS_INVALID")
        require(original.execute("SELECT COUNT(*) FROM forecasts WHERE league='ENG'").fetchone()[0] == 0,
                "PROTECTED_TEST_IN_RESEARCH_FORECASTS")
        require(original.execute("SELECT COUNT(DISTINCT league || '/' || native_match_id) FROM forecasts").fetchone()[0] == fcount,
                "DUPLICATE_NATIVE_FORECAST")
        for payload, id_, kickoff, captured in original.execute(
            "SELECT payload_json,id,kickoff_utc,captured_at_utc FROM forecasts"):
            forecast = json.loads(payload)
            require(forecast.get("forecast_sha256") == id_ and
                    hashlib.sha256(canon({k: v for k, v in forecast.items()
                          if k != "forecast_sha256"})).hexdigest() == id_,
                    "FORECAST_BYTE_INTEGRITY")
            def utc(v):
                d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                require(d.tzinfo is not None, "FORECAST_TIME_NAIVE")
                return d.astimezone(timezone.utc)
            require(utc(captured) < utc(kickoff)-timedelta(minutes=90),
                    "FORECAST_NOT_90MIN_PREMATCH")
        with tempfile.TemporaryDirectory(prefix="kb3-step01-restore-") as tmp:
            tmpdir = Path(tmp)
            exact = tmpdir/"exact-copy.sqlite"
            exact.write_bytes(db.read_bytes())
            require(sha(exact) == sha(db), "REPOSITORY_FILE_COPY_MISMATCH")
            with ro(exact) as replica:
                require(snapshot(replica) == start, "EXACT_REPLICA_SEMANTIC_DRIFT")
            recovered = tmpdir/"online-backup-restored.sqlite"
            with sqlite3.connect(recovered) as target:
                original.backup(target)
            with ro(recovered) as recovered_db:
                require(snapshot(recovered_db) == start, "SQLITE_BACKUP_RESTORE_DRIFT")
            # Run a trigger mutation test on a disposable restored copy only.
            with sqlite3.connect(recovered) as target:
                target.execute("PRAGMA foreign_keys=ON")
                first = target.execute("SELECT id FROM forecasts LIMIT 1").fetchone()[0]
                try:
                    target.execute("UPDATE forecasts SET id=id WHERE id=?", (first,))
                except sqlite3.DatabaseError:
                    target.rollback()
                else:
                    raise AssertionError("FORECAST_IMMUTABILITY_NOT_ENFORCED")
            with ro(db) as after:
                require(snapshot(after) == start, "ORIGINAL_DATABASE_MUTATED")
    frozen = json.loads(archive.read_text(encoding="utf-8"))
    require(frozen.get("model_version") == MODEL and frozen.get("mode") == "forecast",
            "LAST_FORECAST_ARCHIVE_VERSION_INVALID")
    return {
        "status": "LOCAL_REPOSITORY_RESTORE_PASS_OFFSITE_NOT_VERIFIED",
        "repository_snapshot_sha256": sha(db),
        "forecast_archive_sha256": sha(archive),
        "model_params_sha256": param_hash,
        "model_manifest_sha256": manifest_hash,
        "tables": len(start),
        "forecasts": fcount,
        "settlements": scount,
        "copy_sha": "MATCH",
        "sqlite_backup_restore": "PASS",
        "sqlite_integrity": "PASS",
        "immutable_trigger_test_on_restored_copy": "PASS",
        "offsite_backup_of_current_live_sqlite": "NOT_INDEPENDENTLY_VERIFIED",
        "model_promoted": False,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True, ensure_ascii=False))
