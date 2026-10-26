"""KB3 Step11: audit observed-at features from already restored PIT evidence.

No network, no encryption keys read, no training. Requires an independently
verified decrypted SQLite ledger; sanitized count/hash report only.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from src.kb3_observed_features import load_observed_features


def sanitize(v):
    f=v["features"]
    return {
      "schema":"kb3-step11-observed-feature-audit-v1",
      "source_fixture_id":v["fixture_id"],
      "cutoff_utc":v["feature_cutoff_utc"],
      "mode":v["mode"],
      "availability_class":v["availability_class"],
      "accepted_predecessor_count":v["accepted_predecessor_count"],
      "home_form_games_available":f["home_games_available"],
      "away_form_games_available":f["away_games_available"],
      "home_last5_xg_observations":f["home_all_5_xg_n"],
      "away_last5_xg_observations":f["away_all_5_xg_n"],
      "source_capture_sha256":v["source_evidence"]["asof_capture_chain_sha256"],
      "feature_sha256":v["sha256"],
      "provider_original_publication_known":False,
      "historical_backtest_certified":False,
      "training_allowed":False,
      "forecast_generated":False
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--restored-pit-db",required=True)
    p.add_argument("--fixture-id",type=int,required=True)
    p.add_argument("--cutoff",required=True)
    p.add_argument("--review-manifest")
    p.add_argument("--crosswalk")
    p.add_argument("--strict-xg-db")
    p.add_argument("--strict-xg-manifest")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=load_observed_features(
        a.restored_pit_db,a.fixture_id,a.cutoff,
        review_manifest_path=a.review_manifest,
        reviewed_crosswalk_path=a.crosswalk,
        strict_xg_db_path=a.strict_xg_db,
        strict_xg_manifest_path=a.strict_xg_manifest)
    if out["mode"]!="observed" or out["training_allowed"]:
        raise RuntimeError("INVALID_OBSERVED_MODE")
    result=sanitize(out)
    dest=Path(a.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x",encoding="utf8") as fd:
        json.dump(result,fd,sort_keys=True,ensure_ascii=False,indent=2)
        fd.write("\n")
    print("STEP11_OBSERVED_FEATURE_AUDIT",json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
