"""Read-only, strict same-fixture Step17 challenger audit on stored M0 data.

Reuses the production-independent paired comparison function only on a TEMP
COPY of SQLite: the original ledger is never opened for writing, no API call,
no backfill, no fitting or calibration, and no protected TEST access.
No forward performance is declared if no host-attested triplet is settled.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile

from src.kb3_step16_m0_720_eight_forward import DB, MODEL
from src.kb3_step17_challenger_provenance import paired_settled_report

ENGINES = ("ELO_ONLY", "CATBOOST_NO_XG")
PAIR_KEYS = (
    "M0_ELO_POISSON_720TRAIN__vs__ELO_ONLY",
    "M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG",
    "ELO_ONLY__vs__CATBOOST_NO_XG",
)

class PairedReadOnlyError(ValueError):
    pass

def file_sha256(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def assess(db_path=DB):
    source=Path(db_path).resolve()
    if not source.is_file():
        raise PairedReadOnlyError("FROZEN_M0_DB_MISSING")
    before=file_sha256(source)
    with sqlite3.connect(source.as_uri()+"?mode=ro&immutable=1",uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise PairedReadOnlyError("SOURCE_SQLITE_INTEGRITY_FAILED")
        tables={x[0] for x in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"model_meta","forecasts","settlements",
                "m0720_github_push_proofs"} <= tables:
            raise PairedReadOnlyError("ORIGINAL_PROOF_SCHEMA_MISSING")
        models=db.execute("SELECT model FROM model_meta").fetchall()
        if models != [(MODEL,)]:
            raise PairedReadOnlyError("M0_RESEARCH_MODEL_CHANGED")
        originals=db.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]
        outcomes=db.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
        children=db.execute("SELECT COUNT(*) FROM step17_frozen_challengers").fetchone()[0] \
            if "step17_frozen_challengers" in tables else 0
        host_children=db.execute("SELECT COUNT(*) FROM step17_challenger_host_proofs").fetchone()[0] \
            if "step17_challenger_host_proofs" in tables else 0
    # The existing comparator's schema ensure() writes only into an isolated copy,
    # never to the frozen original or forecasts collected by GitHub Actions.
    with tempfile.TemporaryDirectory(prefix="kb3-step17-readonly-") as folder:
        copy=Path(folder)/"research_snapshot.sqlite"
        shutil.copyfile(source,copy)
        benchmark=paired_settled_report(copy)
    if file_sha256(source)!=before:
        raise PairedReadOnlyError("FROZEN_SOURCE_CHANGED_DURING_AUDIT")
    pairs=benchmark["fair_same_game_pairwise"]
    if not all(key in pairs for key in PAIR_KEYS):
        raise PairedReadOnlyError("PAIRED_THREE_MODEL_KEYS_MISSING")
    paired_n={key:pairs[key]["common_n"] for key in PAIR_KEYS}
    if len(set(paired_n.values()))!=1:
        # A partial pair may be useful as diagnostic, but never masquerade as
        # a full three-engine side-by-side result.
        all_three=min(paired_n.values())
    else:
        all_three=next(iter(paired_n.values()))
    return {
        "schema":"kb3-step17-offline-three-engine-readonly-v1",
        "source_m0_sha256":before,
        "total_original_m0_forecasts":originals,
        "total_recorded_settlements":outcomes,
        "total_challenger_forecast_rows":children,
        "host_attested_challenger_rows":host_children,
        "same_fixture_attested_settled_triplets":all_three,
        "pairwise_common_n":paired_n,
        "pairwise_evaluation":{key:pairs[key] for key in PAIR_KEYS},
        "full_five_common_fixtures":benchmark["full_five_common_fixtures"],
        "comparison_input_sha256":benchmark["input_sha256"],
        "performance_claim_allowed":all_three>0,
        "winner_auto_selected":False,
        "gate17":"PENDING",
        "no_provider_calls":True,
        "no_new_forecasts_or_backfill":True,
        "source_db_unchanged":True,
        "protected_test_accessed":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=DB)
    args=p.parse_args()
    print(json.dumps(assess(args.db),sort_keys=True,ensure_ascii=False))

if __name__=="__main__":
    main()
