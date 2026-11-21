"""One-call public-metadata probe for the actual PitchAPI league catalogue.

No fixtures, match outcomes, model fit, archives, or secret-bearing output.
This is a diagnostic check, never a substitute for provenance gates.
"""
from __future__ import annotations

import json
import os
from src.kb3_step16_m0_720_eight_forward import EIGHT, Research720Error, select_eight
from scripts.step16_additional_leagues_audit import norm
from scripts.pitchapi_step06_audit import to_plain


def check_catalog(catalog):
    expected = {country for country, _, _ in EIGHT}
    summary = {"schema": "kb3-8league-catalog-preflight-v1",
               "research_only": True, "provider_requests": 1,
               "no_fixture_or_result_requests": True, "countries": {}, "validated": False}
    for country in sorted(expected):
        candidates = [x for x in catalog.get("leagues", [])
                      if isinstance(x,dict) and str(x.get("country_code","")).upper()==country]
        # Metadata only: never log untrusted full JSON / IDs / credentials.
        summary["countries"][country] = [
            {"name_norm": norm(x.get("name",""))[:80],
             "both_seasons": all(s in (x.get("seasons") or []) for s in ("2025/2026","2026/2027")),
             "is_free": x.get("is_free") is True}
            for x in candidates[:12]]
    try:
        selected = select_eight(catalog)
    except Research720Error as exc:
        summary["error_code"] = str(exc)[:160]
        summary["capture_detail"] = getattr(exc, "capture_detail", None)
    else:
        summary["validated"] = len(selected)==8
    return summary


def main():
    key = os.getenv("PITCHAPI_API_KEY","")
    if not key:
        raise SystemExit("CATALOG_PROBE_SECRET_MISSING")
    from pitchapi import PitchAPI
    try:
        catalogue = to_plain(PitchAPI(api_key=key,max_retries=0).leagues.list())
    except Exception as exc:
        print("CATALOG_PROBE_NETWORK_ERROR",type(exc).__name__)
        raise SystemExit(2)
    if not isinstance(catalogue,dict) or not isinstance(catalogue.get("leagues"),list):
        raise SystemExit("CATALOG_PROBE_SCHEMA_INVALID")
    report = check_catalog(catalogue)
    print("CATALOG_PROBE_DIAGNOSTIC",json.dumps(report,sort_keys=True,ensure_ascii=False))
    if not report["validated"]:
        raise SystemExit(3)


if __name__=="__main__":
    main()
