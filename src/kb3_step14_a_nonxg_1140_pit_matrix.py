"""A: genuine frozen 1,140 x 73 non-xG field-level original PIT gap matrix.

The only available native-safe historic manifest contains match ID, kickoff and
partition; NO native TEAM pair, no original per-stat historical publication
receipts or cutoff. Public snapshots are time-qualified *possibilities*, NEVER
certification of native feature. No TEST labels/rows, TRAIN target scores,
odds or CatBoost. Matrix gzip artifact and small summary remain independent.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step14_native_team_crosswalk import SAFE_SHA\nfrom src.kb3_split import sha
from src.kb3_step14_multiseason_pit import SOURCES,utc
from src.kb3_step14_owner_elo_2023_to_2024 import FULL_2023
from scripts.step14_multiseason_owner_native_join_local import ADDITIONAL_2023

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-A-1140-by-73-nonxg-field-level-pit-readiness-v1"
ROW_STATUS="NO_NATIVE_PER_FIELD_HISTORIC_PUBLISHED_AND_CAPTURED_RECEIPT"
SOURCES_CLOCKED=tuple(sorted((SOURCES[0],ADDITIONAL_2023,FULL_2023,SOURCES[1],SOURCES[2]),
                             key=lambda x:x["push"]))
class MatrixError(ValueError):pass

def _nonxg(name):
    return not (name.endswith("_xg_n") or name.endswith("_xg_avg")
                or name.endswith("_xga_n") or name.endswith("_xga_avg"))

def construct(safe):
    if (not isinstance(safe,dict) or safe.get("schema")!="kb3-step12-methodology-v1"
        or safe.get("projection_sha256")!=SAFE_SHA
        or sha({k:v for k,v in safe.items() if k!="projection_sha256"})!=SAFE_SHA
        or safe.get("training_allowed") is not False
        or safe.get("partition_counts")!={"TRAIN":760,"VALIDATION":380,"TEST":380}):
        raise MatrixError("FROZEN_ORIGINAL_SPLIT_HASH_INVALID")
    ix={}
    for item in safe["fixtures"]:
        role=item.get("partition")
        if role=="TEST":continue
        if (role not in ("TRAIN","VALIDATION")
            or set(item)!={"fixture_id","kickoff_utc","partition"}
            or item["fixture_id"] in ix):
            raise MatrixError("BAD_OR_DUPLICATE_FROZEN_MATCH")
        ix[item["fixture_id"]]=(item["kickoff_utc"],role)
    fields=sorted(x for x in EXPECTED_FEATURES if _nonxg(x))
    flags=sorted(x for x in EXPECTED_MISSING if not (x.endswith("_xg") or x.endswith("_xga")))
    if len(fields)!=73 or len(flags)!=14 or len(ix)!=1140:
        raise MatrixError("UNEXPECTED_FROZEN_73_14_1140_CONTRACT")
    if any("xg" in x or "xga" in x for x in fields+flags):
        raise MatrixError("XG_FIELD_LEAKED_IN_NOXG_VIEW")
    rows=[];public_counts=Counter();parts=Counter()
    for native_id,(kickoff,partition) in ix.items():
        if partition not in ("TRAIN","VALIDATION"):raise MatrixError("HOLDOUT_ROW_FORBIDDEN")
        ko=utc(kickoff)
        # Hypothetical availability clock for inspection, NEVER treated as
        # an actual historic source capture or original feature cutoff.
        cutoff=(ko-timedelta(minutes=1)).isoformat().replace("+00:00","Z")
        public=[{"provider":x.get("provider","FPL"),
                 "commit":x["commit"],"independent_gharchive_event":x.get("event",x.get("event_id"))}
                for x in SOURCES_CLOCKED if utc(x["push"])<utc(cutoff)]
        parts[partition]+=1;public_counts[len(public)]+=1
        rows.append({"native_fixture_id":native_id,"partition":partition,
                     "kickoff_utc":kickoff,
                     "candidate_cutoff_utc_NOT_ORIGINAL":cutoff,
                     "public_older_snapshot_count_NOT_NATIVE_RECEIPTS":len(public),
                     "original_cutoff":None,
                     "original_team_identity_proof":False,
                     "original_feature_availability":{
                        f:ROW_STATUS for f in fields},
                     "original_missing_flag_availability":{
                        f:ROW_STATUS for f in flags},
                     "eligible_no_xg_original_M1":False})
    if parts!={"TRAIN":760,"VALIDATION":380}:
        raise MatrixError("ORIGINAL_CHRONOLOGICAL_SPLIT_CHANGED")
    summary={"schema":SCHEMA,"original_source_safe_projection_sha256":safe["projection_sha256"],
             "partition_counts":dict(parts),"rows_in_matrix":len(rows),
             "non_xg_numeric_fields_per_row":len(fields),
             "non_xg_missing_flags_per_row":len(flags),
             "non_xg_frozen_numeric_field_names":fields,
             "non_xg_frozen_missing_flag_names":flags,
             "original_native_field_time_source_proof_count":0,
             "non_xg_field_evidence_slots":len(rows)*(len(fields)+len(flags)),
             "non_xg_qualified_field_slots":0,
             "candidate_external_independently_pushed_source_count_by_row":
                 dict(sorted(public_counts.items())),
             "independent_public_snapshot_does_not_establish_native_feature_pit":True,
             "original_feature_cutoffs_missing":1140,
             "non_xg_real_train_rows_allowed":0,
             "non_xg_real_validation_rows_allowed":0,
             "no_xg_catboost_fitted":False,
             "train_target_result_labels_examined":False,"test_rows_read":False,
             "model_architecture_or_split_changed":False,
             "gate14_pass":False,"training_allowed":False}
    return summary,rows

def main():
    p=argparse.ArgumentParser();p.add_argument("--summary",required=True)
    p.add_argument("--matrix",required=True);a=p.parse_args()
    safe=json.loads((ROOT/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
    report,rows=construct(safe)
    summary=Path(a.summary);matrix=Path(a.matrix)
    summary.parent.mkdir(parents=True,exist_ok=True);matrix.parent.mkdir(parents=True,exist_ok=True)
    # No original match outcome data or provider secrets are ever in report.
    if summary.exists() or matrix.exists():raise MatrixError("APPEND_ONLY_OUTPUT_ALREADY_EXISTS")
    payload=json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    summary.write_text(payload,encoding="utf8")
    with gzip.open(matrix,"wt",encoding="utf8",compresslevel=9) as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps({"rows":len(rows),"numeric":len(report["non_xg_frozen_numeric_field_names"]),
                      "flags":len(report["non_xg_frozen_missing_flag_names"]),
                      "field_slots":report["non_xg_field_evidence_slots"],
                      "original_PIT_qualified_rows":0,"no_xg_M1_fit":False,
                      "source_candidate_count_by_row":report["candidate_external_independently_pushed_source_count_by_row"]},
                     sort_keys=True))
if __name__=="__main__":main()
