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
    "ELO_ONLY__vs__M0_ELO_POISSON_720TRAIN",
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

def three_way_count(db,tables):
    """SQL intersection, not a minimum/union of marginal pair counts."""
    required={"forecasts","settlements","m0720_github_push_proofs",
              "step17_frozen_challengers","step17_challenger_host_proofs"}
    if not required <= set(tables):
        return 0
    return db.execute("""
        SELECT COUNT(DISTINCT f.id)
        FROM forecasts f
        JOIN settlements s ON s.forecast_id=f.id
        JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
        JOIN step17_frozen_challengers elo
          ON elo.source_m0_forecast_sha256=f.id AND elo.engine='ELO_ONLY'
        JOIN step17_challenger_host_proofs ep
          ON ep.challenger_sha256=elo.challenger_sha256
        JOIN step17_frozen_challengers cat
          ON cat.source_m0_forecast_sha256=f.id AND cat.engine='CATBOOST_NO_XG'
        JOIN step17_challenger_host_proofs cp
          ON cp.challenger_sha256=cat.challenger_sha256
    """).fetchone()[0]

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
        all_three=three_way_count(db,tables)
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
    # Identical pairwise COUNTS do NOT imply the same three fixtures.
    # Count the exact full three-way intersection in immutable source SQLite.
    if any(all_three>v for v in paired_n.values()):
        raise PairedReadOnlyError("THREE_WAY_INTERSECTION_EXCEEDS_PAIR")
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
        "diagnostic_metrics_available":all_three>0,
        "performance_claim_allowed":False,  # no formal inference before 100+ weeks+gate16
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
