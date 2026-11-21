"""Read-only research audit of genuine V3-R forecasts and M0 market settlements.
No network, no fit, no promotion, no input mutations. Run from repository root.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import sqlite3

LEAGUES = frozenset(("BEL", "ESP", "FRA", "GER", "ITA", "NED", "POL", "TUR"))
OUTCOMES = ("1", "X", "2")
DB = Path("data/forward_m0_720_eight/kb3_forward_eight.sqlite")


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def utc(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(d.tzinfo is not None and d.utcoffset().total_seconds() == 0, "UTC_REQUIRED")
    return d


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def valid_prob(p):
    return type(p) in (float, int) and math.isfinite(p) and 0 <= p <= 1


def probs(p):
    need(set(p) == set(OUTCOMES) and all(valid_prob(v) for v in p.values())
         and abs(sum(p.values())-1) < 1e-9, "INVALID_1X2")
    return p


def band(p):
    need(valid_prob(p), "INVALID_PROBABILITY")
    return "under60" if p < .6 else "60-70" if p < .7 else "70-80" if p < .8 else "80-90" if p < .9 else "90-100"


def bands(rows):
    out = {k: {"rows": 0, "wins": 0, "losses": 0, "pushes": 0, "sum_p": 0.0}
           for k in ("under60", "60-70", "70-80", "80-90", "90-100")}
    # A push has no conditional win probability in the immutable settlement ledger.
    # Record it separately rather than silently imputing zero or a probability band.
    out["unbinned_push"] = {"rows": 0, "wins": 0, "losses": 0, "pushes": 0, "sum_p": 0.0}
    for p, label in rows:
        need(label in ("WIN", "LOSS", "PUSH"), "UNKNOWN_SETTLEMENT")
        b = out["unbinned_push"] if p is None and label == "PUSH" else out[band(p)]
        b["rows"] += 1
        if label == "PUSH":
            b["pushes"] += 1
        else:
            b["wins" if label == "WIN" else "losses"] += 1
            b["sum_p"] += p
    for b in out.values():
        n = b["wins"] + b["losses"]
        b["hit_rate"] = b["wins"]/n if n else None
        b["mean_probability_no_push"] = b.pop("sum_p")/n if n else None
    return out


def score(rows, model):
    if not rows:
        return {"n": 0, "top1_accuracy": None, "brier_sum3": None, "log_loss": None}
    hit = brier = ll = 0
    for r in rows:
        p, y = probs(r[model]), r["outcome"]
        hit += max(OUTCOMES, key=p.get) == y
        brier += sum((p[k]-(y == k))**2 for k in OUTCOMES)
        ll -= math.log(max(p[y], 1e-15))
    n = len(rows)
    return {"n": n, "top1_correct": hit, "top1_accuracy": hit/n,
            "brier_sum3": brier/n, "log_loss": ll/n}


def compare(rows):
    return {k: score(rows, k) for k in ("M0", "V3R")}


def read_database(root):
    file = (root/DB).resolve()
    need(file.is_file(), "M0_DATABASE_MISSING")
    db = sqlite3.connect(file.as_uri()+"?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        need(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "DB_INTEGRITY")
        need(not db.execute("PRAGMA foreign_key_check").fetchall(), "DB_FOREIGN_KEYS")
        rows = db.execute("""SELECT f.id,f.league,f.native_match_id,f.kickoff_utc,
            f.captured_at_utc,f.payload_json,
            p.github_server_event_utc AS parent_host_utc,
            s.settlement_sha256,s.score_home,s.score_away,s.outcome,s.observed_utc
            FROM forecasts f LEFT JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
            LEFT JOIN settlements s ON s.forecast_id=f.id""").fetchall()
        out = {}
        for x in rows:
            need(x["league"] in LEAGUES, "PROTECTED_OR_UNKNOWN_LEAGUE")
            need(x["id"] not in out, "DUPLICATE_PARENT_OR_PROOF")
            out[x["id"]] = dict(x)
        return out
    finally:
        db.close()


def audit(root, now):
    root = Path(root)
    parents = read_database(root)
    v3r_files = sorted((root/"data/v3r_shadow/forecasts").glob("*/*.json"))
    market_files = sorted((root/"data/test_markets/settlements").glob("*.json"))
    paired, state, seen = [], Counter(), set()
    for file in v3r_files:
        f = load(file)
        need(f["league"] in LEAGUES and f["league"] == file.parent.name, "V3R_LEAGUE")
        need(f["provider_match_id"] == file.stem, "V3R_FILENAME")
        need(f.get("research_only") is True and f.get("production_approved") is False
             and f.get("target_result_used") is False, "V3R_NOT_RESEARCH_ONLY")
        need(f.get("missing_value_policy") == "NAN_NOT_ZERO_AND_RETRY", "V3R_MISSING_POLICY")
        fid = f["source_m0_forecast_sha256"]
        need(fid not in seen, "V3R_DUPLICATE_PARENT")
        seen.add(fid)
        parent = parents.get(fid)
        need(parent is not None, "V3R_PARENT_MISSING")
        need((parent["league"], parent["native_match_id"], parent["kickoff_utc"]) ==
             (f["league"], f["provider_match_id"], f["kickoff_utc"]), "V3R_PARENT_DRIFT")
        generated, kick = utc(f["generated_at_utc"]), utc(f["kickoff_utc"])
        need(generated < kick, "V3R_NOT_PREMATCH")
        probs(f["p_1x2"])
        if generated > now:
            state["not_yet_captured_at_cutoff"] += 1
            continue
        if not parent["settlement_sha256"] or utc(parent["observed_utc"]) > now:
            state["future" if kick > now else "awaiting_verified_result"] += 1
            continue
        need(utc(parent["observed_utc"]) > kick, "RESULT_BEFORE_KICKOFF")
        if not parent["parent_host_utc"] or utc(parent["parent_host_utc"]) >= kick:
            state["missing_m0_pregame_host_proof"] += 1
            continue
        original = json.loads(parent["payload_json"])
        need(original["forecast_sha256"] == fid, "M0_HASH_REFERENCE_DRIFT")
        y = "1" if parent["score_home"] > parent["score_away"] else "2" if parent["score_home"] < parent["score_away"] else "X"
        need(y == parent["outcome"], "OUTCOME_DRIFT")
        paired.append({"league": f["league"], "match_id": f["provider_match_id"],
                       "parent_sha256": fid, "v3r_sha256": f["forecast_sha256"],
                       "kickoff_utc": f["kickoff_utc"], "outcome": y,
                       "score": [parent["score_home"], parent["score_away"]],
                       "M0": probs(original["p_1x2"]), "V3R": probs(f["p_1x2"]),
                       "missing_optional": len(f["missing_optional_features"]),
                       "v3r_host_attestation_pending": f.get("independent_host_publication_proof_pending")})
        state["paired_descriptive"] += 1
    market_rows, family, exact_markets = [], defaultdict(list), defaultdict(list)
    market_fixtures = 0
    for file in market_files:
        s = load(file)
        fid = s["original_m0_forecast_sha256"]
        need(fid == file.stem and fid in parents, "MARKET_PARENT_DRIFT")
        parent = parents[fid]
        need(s.get("real_fully_finished_result_only") is True and s.get("production_approved") is False
             and s["original_m0_settlement_sha256"] == parent["settlement_sha256"]
             and s["result_home_90min"] == parent["score_home"]
             and s["result_away_90min"] == parent["score_away"]
             and s["original_result_observed_at_utc"] == parent["observed_utc"], "MARKET_RESULT_DRIFT")
        need(utc(parent["observed_utc"]) > utc(parent["kickoff_utc"]), "MARKET_RESULT_BEFORE_KICK")
        if utc(parent["observed_utc"]) > now:
            continue
        freeze = load(root/"data/test_markets/freezes"/file.name)
        proof = load(root/"data/test_markets/host_proofs"/file.name)
        need(freeze["freeze_sha256"] == s["origin_market_freeze_sha256"] == proof["market_freeze_sha256"]
             and proof["original_m0_forecast_sha256"] == fid
             and freeze["original_m0_forecast_sha256"] == fid
             and proof.get("strict_before_kickoff_minus_90min") is True
             and utc(proof["github_host_artifact_created_utc"]) < utc(parent["kickoff_utc"]),
             "MARKET_HOST_PROOF_MISMATCH")
        rows = s["market_rows"]
        need(len(rows) == s["market_count"] == 28, "MARKET_ROWS_INCOMPLETE")
        need(len({(r["family"], r["line"], r["side"], r["selection"]) for r in rows}) == len(rows),
             "MARKET_ROWS_DUPLICATE")
        market_fixtures += 1
        for r in rows:
            p, label = r["p_win_conditional_no_push"], r["settlement"]
            item = (p, label)
            market_rows.append(item)
            family[r["family"]].append(item)
            exact_markets["/".join(str(r[k]) for k in ("family", "line", "side", "selection"))].append(item)
    return {"schema": "kb3-forward-research-audit-v1", "cutoff_utc": now.isoformat(),
            "research_only": True, "production_approved": False, "official_fit_increment": 0,
            "independent_v3r_attestation_performed": False, "protected_test_accessed": False,
            "v3r_total_files": len(v3r_files), "v3r_states": dict(state),
            "M0_total_forecasts": len(parents),
            "M0_settled_at_cutoff": sum(bool(p["settlement_sha256"]) and utc(p["observed_utc"]) <= now for p in parents.values()),
            "paired_1x2": compare(paired),
            "paired_per_league": {l: compare([r for r in paired if r["league"] == l]) for l in sorted(LEAGUES)},
            "paired_rows": paired,
            "paired_top1_bands": {k: bands([(max(r[k].values()), "WIN" if max(OUTCOMES, key=r[k].get) == r["outcome"] else "LOSS") for r in paired]) for k in ("M0", "V3R")},
            "paired_1x_bands": {k: bands([(r[k]["1"]+r[k]["X"], "WIN" if r["outcome"] != "2" else "LOSS") for r in paired]) for k in ("M0", "V3R")},
            "market_settled_fixtures": market_fixtures, "market_positions": len(market_rows),
            "market_bands": bands(market_rows),
            "market_family_bands": {k: bands(v) for k,v in sorted(family.items())},
            "exact_market_bands": {k: bands(v) for k,v in sorted(exact_markets.items())},
            "roi": None, "limitations": ["V3R independent host publication not certified.",
            "Correlated and opposite selections; no independence or odds assumptions.",
            "No production promotion, thresholds, fitting or changes to saved inputs."]}


def self_test():
    assert [band(p) for p in (0,.599,.6,.699,.7,.799,.8,.899,.9,1)] == [
        "under60","under60","60-70","60-70","70-80","70-80","80-90","80-90","90-100","90-100"]
    b = bands([(.8,"WIN"),(.85,"LOSS"),(.88,"PUSH")])["80-90"]
    assert b["rows"] == 3 and b["wins"] == b["losses"] == b["pushes"] == 1 and b["hit_rate"] == .5
    p = bands([(None,"PUSH"),(.8,"WIN")])["unbinned_push"]
    assert p["rows"] == p["pushes"] == 1 and p["hit_rate"] is None
    for outcome in ("WIN", "LOSS"):
        try:
            bands([(None,outcome)])
        except ValueError:
            pass
        else:
            raise AssertionError("missing probability on a resolved win/loss")
    m = score([{"M0":{"1":.7,"X":.2,"2":.1},"outcome":"1"}],"M0")
    assert m["top1_accuracy"] == 1 and abs(m["brier_sum3"]-.14) < 1e-9
    assert score([],"M0")["brier_sum3"] is None
    print("offline arithmetic self-test PASS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--cutoff-utc")
    p.add_argument("--output", type=Path)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        self_test()
        return
    if not a.output:
        p.error("--output is required")
    now = utc(a.cutoff_utc) if a.cutoff_utc else datetime.now(timezone.utc)
    report = audit(a.root, now)
    # Never overwrite any existing snapshot or source file.
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")
    print("research paired", report["paired_1x2"]["M0"]["n"],
          "market fixtures", report["market_settled_fixtures"])


if __name__ == "__main__":
    main()
