"""Read-only assessment of original Step16 M0 TRAIN720 frozen forecast ledger.

No API requests, training, calibration, schema modifications or forecast writes.
Queries only server-attested AND settled match rows, as required by original
100+50 contract. Outputs None for quality metrics if zero eligible matches.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import math
import sqlite3

from src.kb3_step16_m0_720_eight_forward import DB, MODEL
from src.kb3_step16_m0_720_calibration import (
    MIN_FIT, MIN_HOLDOUT, eligible_settlements,
)

LEAGUES = ("ESP","ITA","GER","FRA","NED","BEL","TUR","POL")


class ReadOnlyM0Error(ValueError):
    pass


def check(ok, why):
    if not ok:
        raise ReadOnlyM0Error(why)


def metrics(rows):
    """Independent recomputation from frozen 1X2; no calibrator evaluated."""
    if not rows:
        return None
    log_losses, briers, successes = [], [], []
    bins = defaultdict(list)
    for r in rows:
        p, y = r["p"], r["y"]
        check(isinstance(p,dict) and set(p)=={"1","X","2"} and y in p,
              "BAD_1X2_CONTRACT")
        check(all(type(v) in (int,float) and math.isfinite(v) and 0 < v < 1
                  for v in p.values()) and abs(math.fsum(p.values())-1)<1e-9,
              "BAD_FROZEN_PROBABILITIES")
        ll = -math.log(p[y])
        brier = math.fsum((p[k]-int(k==y))**2 for k in ("1","X","2"))
        check(abs(ll-r["ll"])<1e-9 and abs(brier-r["bs"])<1e-9,
              "PERSISTED_SCORE_DISAGREES_WITH_RECALCULATION")
        top = max(("1","X","2"),key=lambda k:p[k])
        correct = int(top==y)
        confidence = p[top]
        b = min(4,int(confidence*5))
        bins[b].append((confidence,correct))
        log_losses.append(ll)
        briers.append(brier)
        successes.append(correct)
    n=len(rows)
    return {
        "n":n,
        "brier_sum3":math.fsum(briers)/n,
        "log_loss":math.fsum(log_losses)/n,
        "top1_accuracy":sum(successes)/n,
        "top1_ece_5_bins":math.fsum(
            len(group)/n*abs(math.fsum(x[0] for x in group)/len(group) -
                             sum(x[1] for x in group)/len(group))
            for group in bins.values()),
    }


def assess(db_path=DB, *, at=None):
    at = at or datetime.now(timezone.utc)
    check(at.tzinfo is not None and at.utcoffset()==timedelta(0),
          "AUDIT_REQUIRES_UTC")
    path = Path(db_path).resolve()
    check(path.is_file(), "ORIGINAL_M0_DB_MISSING")
    uri = path.as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri,uri=True) as db:
        check(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
              "FROZEN_SQLITE_NOT_INTEGRAL")
        tables={row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        check({"model_meta","forecasts","settlements",
               "m0720_github_push_proofs"} <= tables,
              "SOURCE_OR_HOST_PROOF_TABLE_MISSING")
        meta=db.execute("SELECT model,parameters_sha256 FROM model_meta").fetchall()
        check(len(meta)==1 and meta[0][0]==MODEL and
              len(meta[0][1])==64, "FROZEN_M0_MODEL_CHANGED")
        byleague={c:0 for c in LEAGUES}
        for c,n in db.execute("SELECT league,COUNT(*) FROM forecasts GROUP BY league"):
            check(c in byleague, "UNAPPROVED_FORECAST_LEAGUE")
            byleague[c]=n
        total=sum(byleague.values())
        raw=db.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
        proven=db.execute(
            "SELECT COUNT(*) FROM m0720_github_push_proofs").fetchone()[0]
        check(raw<=total and proven<=total, "LEDGER_COUNTS_INVALID")
        eligible=eligible_settlements(db,at=at)
        by=defaultdict(list)
        for item in eligible:
            by[item["league"]].append(item)
        check(len(eligible)<=raw and len(eligible)<=proven,
              "INELIGIBLE_FORECAST_ACCEPTED")
        return {
            "schema":"kb3-step16-m0-720-offline-readonly-eligibility-v1",
            "model":MODEL,
            "status":"READ_ONLY_AUDIT_NO_TRAINING_NO_CALIBRATION",
            "total_frozen_forecasts":total,
            "by_league_frozen":byleague,
            "raw_settlements":raw,
            "server_attested_forecasts":proven,
            "eligible_settled_unique":len(eligible),
            "by_league_eligible":{c:len(by[c]) for c in LEAGUES},
            "pooled":metrics(eligible),
            "by_league_scores":{c:metrics(by[c]) for c in LEAGUES},
            "needed_for_initial_fit":max(0,MIN_FIT-len(eligible)),
            "future_holdout_minimum":MIN_HOLDOUT,
            "provider_requests":0,
            "fit_or_calibration_executed":False,
            "production_changed":False,
            "sealed_test_accessed":False,
            "formal_gate16":"PENDING",
        }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=DB)
    args=p.parse_args()
    print(json.dumps(assess(args.db),sort_keys=True,ensure_ascii=False))


if __name__=="__main__":
    main()
