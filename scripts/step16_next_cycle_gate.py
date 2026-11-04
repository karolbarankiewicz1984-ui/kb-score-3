"""Read-only Step16/17 post-merge cycle gate, fail closed when next source missing."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
from scripts.step16_17_acceleration_audit import (
    ROOT,M0,XG,open_readonly,audit_m0,audit_xg,require,utc)
BASELINE_MERGE_UTC="2026-11-01T20:23:03Z"
def latest(parent, pattern):
    return sorted(parent.glob(pattern))
def after_merge_run(receipts,merge_at,flag):
    qualifying=[]
    for path in receipts:
        try:
            doc=json.loads(path.read_text())
            when=doc.get(flag)
            if when and utc(when)>utc(merge_at):
                qualifying.append((utc(when),path,doc))
        except (ValueError,KeyError,TypeError):
            continue
    return sorted(qualifying,key=lambda x:x[0])
def run(root=ROOT,*,now=None,merge=BASELINE_MERGE_UTC):
    root=Path(root)
    now=now or datetime.now(timezone.utc)
    require(now.tzinfo is not None and now.utcoffset().total_seconds()==0,"UTC_REQUIRED")
    mrdir=root/"data/pit_sidecar/m0_720_eight"
    xrdir=root/"data/pit_sidecar/step17_native_xg_eight"
    forecasts=after_merge_run(latest(mrdir,"*/forecast*/RECEIPT.json"),merge,"run_utc")
    captures=after_merge_run(latest(xrdir,"*/XG_READINESS_RECEIPT.json"),merge,"observed_at_utc")
    with open_readonly(root/"data/forward_m0_720_eight/kb3_forward_eight.sqlite") as db:
        m0=audit_m0(db,now=now)
    last_settle=after_merge_run(latest(mrdir,"*/settle-*/RECEIPT.json"),merge,"run_utc")
    if last_settle:
        official=last_settle[-1][2]["calibration_readiness"]["eligible_settled_unique"]
        require(official<=m0["counts"]["host_attested_settled"],"ELIGIBLE_COUNT_EXCEEDS_REAL_SETTLED")
    else:official=None
    xg_latest=latest(xrdir,"*/XG_READINESS_RECEIPT.json")
    with open_readonly(root/"data/forward_step17_xg_eight/observed_xg.sqlite") as db:
        xg=audit_xg(db,json.loads(xg_latest[-1].read_text()))
    m=forecasts[-1][2] if forecasts else {}
    x=captures[-1][2] if captures else {}
    full_m0=bool(m and "ned_bel_historical_phase_native_id_review" in m)
    full_xg=bool(x and "real_missing_last5_predecessor_ids" in x
                 and "last5_priority_shadow_comparison" in x)
    if x:
        require(x["last5_priority_shadow_comparison"]["additional_api_calls"]==0
                and x["network_calls"]<=33,"SHADOW_API_BUDGET_DRIFT")
        inventory=x["real_missing_last5_predecessor_ids"]
        require(len(inventory)==x["future_form5_coverage"]["future_targets_scanned"],
                "XG_INVENTORY_COVERAGE_DRIFT")
    if m:
        require(m["network_calls"]==17 and m["production_approved"] is False,
            "M0_NEXT_CAPTURE_UNSAFE")
    return {"schema":"kb3-postmerge-next-cycle-readiness-v1",
     "checked_at_utc":now.isoformat(),
     "source": "REAL_REPO_COMMITTED_RECEIPTS_AND_SQLITE_NO_NETWORK",
     "m0_eligible_fit":official,
     "m0_total_host_attested":m0["counts"]["host_attested_forecasts"],
     "m0_total_settled":m0["counts"]["host_attested_settled"],
     "xg_verified_pairs":xg["verified_native_xg_pairs"],
     "xg_complete_last5":xg["observed_last5_complete_targets"],
     "m0_postfix_forecast_new_relevant_receipt":bool(forecasts),
     "xg_postfix_new_real_capture_receipt":bool(captures),
     "m0_native_phase_id_evidence_live":full_m0,
     "xg_native_missing_ids_and_priority_shadow_live":full_xg,
     "m0_after_merge_proof":"NEW_RECEIPT_PRESENT_BUT_NEW_FORECAST_HOST_ATTESTATION_STILL_REQUIRED" if full_m0 else "PENDING_NEXT_REAL_FORECAST",
     "xg_after_merge_proof":"PASS" if full_xg else "PENDING_NEXT_REAL_CAPTURE",
     "no_ex_post_forecasts_created":True,
     "original_m0_or_model_changed":False,
     "gate16":"PENDING","gate17":"PENDING"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    dest=Path(args.out)
    require(not dest.exists(),"AUDIT_APPEND_ONLY")
    report=run()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
