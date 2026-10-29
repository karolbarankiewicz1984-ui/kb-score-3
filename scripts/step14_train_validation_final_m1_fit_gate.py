"""Step14 phase 4 strict production CatBoost M1 GATE14 admission audit.

Reads real 1140 compressed research matrix but NEVER trains/changes weights.
Original PitchAPI-native field-level original publication receipts mandatory;
alternative public source or 2026 replay cannot meet original signed contract.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math
from collections import Counter
from pathlib import Path
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from scripts.step14_train_760_dense_validation_1140_matrix import SCHEMA as SRC_SCHEMA

SCHEMA="kb3-step14-complete-760-380-external-source-121-38-final-M1-fit-gate-v1"
class GateReject(ValueError): pass

def evaluate(report,rows,compressed):
    if report.get("schema")!=SRC_SCHEMA or report.get("matrix_gzip_sha256")!=hashlib.sha256(compressed).hexdigest():
        raise GateReject("GATE_SOURCE_SHA_NOT_ORIGINAL_MATRIX")
    if len(rows)!=1140:raise GateReject("NOT_ORIGINAL_1140_FROZEN")
    parts=Counter();ident=set();public=Counter();non_null=Counter()
    missing_native=Counter();missing_pitchapi=Counter()
    for row in rows:
        role=row.get("partition")
        if role not in ("TRAIN","VALIDATION"):raise GateReject("ORIGINAL_TEST_ROW_NOT_ALLOWED")
        fid=row.get("fixture_id")
        if not isinstance(fid,str) or fid in ident:raise GateReject("DUPLICATE_OR_UNTRUSTED_NATIVE_ID")
        ident.add(fid);parts[role]+=1
        if row.get("original_native_121_plus_38_certified") is not False:
            raise GateReject("FAKE_NATIVE_PIT_ELIGIBILITY")
        v=row["public_source_research_121_numeric_features"]
        m=row["public_source_research_38_missing_flags"]
        if set(v)!=EXPECTED_FEATURES or set(m)!=EXPECTED_MISSING:
            raise GateReject("WRONG_ORIGINAL_121_38_CONTRACT")
        elo=row["separate_2026_retrospective_native_19_Elo_NOT_historic_PIT"]
        if len(elo)!=19 or any(v[k] is not None for k in elo):
            raise GateReject("RETROSPECTIVE_ELO_LEAKED_INTO_HISTORIC_PIT")
        src=row["history_public_asof_source"]
        if src.get("witness_utc"):
            from scripts.step14_fpl_core_2025_independent_asof import _utc
            if _utc(src["witness_utc"])>=_utc(row["kickoff_utc"]):
                raise GateReject("POSTMATCH_SOURCE_LOOKAHEAD")
            public[role]+=1
        elif src.get("status")!="NO_QUALIFIED_OLD_PUBLIC_F5":
            raise GateReject("MISSING_SOURCE_WITNESS")
        non_null[role]+=sum(x is not None for x in v.values())
        if role=="TRAIN":
            # FPL fixtures have no team xG; zero is not equivalent to no
            # evidence. They must NEVER become valid native-source data.
            if any(v[k] is not None for k in EXPECTED_FEATURES
                   if k.endswith(("_xg_n","_xg_avg","_xga_n","_xga_avg"))):
                raise GateReject("FABRICATED_TRAIN_XG_FIELD")
        if any(not isinstance(x,(bool,type(None))) for x in m.values()):
            raise GateReject("INVALID_MISSING_MASK")
    if parts!={"TRAIN":760,"VALIDATION":380}:
        raise GateReject("SAFE_TRAIN_VALIDATION_SPLIT_CHANGED")
    if report.get("distinct_original_TRAIN_with_historical_public_result_FORM5")!=public["TRAIN"]:
        raise GateReject("TRAIN_SOURCE_COUNT_CHANGED")
    if report.get("distinct_original_VALIDATION_with_historical_public_result_FORM5")!=public["VALIDATION"]:
        raise GateReject("VALIDATION_SOURCE_COUNT_CHANGED")
    complete_xg5=sum(row["partition"]=="VALIDATION" and
        row["history_public_asof_source"]["status"]=="PINNED_HISTORIC_ALTERNATIVE_PUBLIC_F5_XG5"
        for row in rows)
    if report.get("distinct_original_VALIDATION_with_historical_alternative_xG5")!=complete_xg5:
        raise GateReject("VALIDATION_ALTERNATIVE_XG5_COUNT_CHANGED")
    if (report.get("original_159_contract_complete_PIT_TRAIN")!=0
        or report.get("original_159_contract_complete_PIT_VALIDATION")!=0
        or report.get("official_fit_M1_allowed") is not False
        or report.get("GATE14")!="PENDING"):
        raise GateReject("ORIGINAL_M1_GATE_MUST_REMAIN_BLOCKED")
    return {"schema":SCHEMA,
      "phases_1_2_3_completed":True,
      "phase_4_real_M1_fit_admission_review_completed":True,
      "original_TRAIN_total":parts["TRAIN"],"original_VALIDATION_total":parts["VALIDATION"],
      "native_fixture_IDs_unique":len(ident),
      "historically_published_alternative_TRAIN_FORM5":public["TRAIN"],
      "historically_published_alternative_VALIDATION_FORM5":public["VALIDATION"],
      "historically_published_alternative_VALIDATION_FORM5_xG5":complete_xg5,
      "public_research_nonnull_numeric_by_partition":dict(non_null),
      "original_121_features_per_row":121,
      "original_38_missing_flags_per_row":38,
      "all_1140_retrospective_19_Elo_separated_from_hist_public":True,
      "original_team_xG_first_publication_receipts_verified":0,
      "native_2023_2026_per_field_capture_and_published_at_verified":False,
      "original_159_field_complete_per_match_TRAIN":0,
      "original_159_field_complete_per_match_VALIDATION":0,
      "no_train_and_validation_original_fit_admission":True,
      "CatBoost_original_M1_fitted":False,
      "CatBoost_original_M1_metrics_real":None,
      "alternative_research_data_are_not_automatically_production_features":True,
      "next_blockers":["original PitchAPI per-match 121+38 field capture and publication receipts",
                       "historically valid original team-level xG for TRAIN",
                       "sufficient original TRAIN and VALIDATION native as-of rows"],
      "protected_TEST_2026_27_used":False,
      "production_model_unchanged":True,
      "GATE14":"PENDING"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matrix",required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();dest=Path(a.out)
    if dest.exists():raise GateReject("APPEND_ONLY")
    compressed=Path(a.matrix).read_bytes()
    with gzip.open(a.matrix,"rt",encoding="utf8") as stream:
        rows=[json.loads(line) for line in stream if line.strip()]
    source=json.loads(Path(a.source).read_text(encoding="utf8"))
    audit=evaluate(source,rows,compressed)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(audit,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print(json.dumps({"phases_1_2_3":True,"gate14":"PENDING",
       "TRAIN_public_FORM5":audit["historically_published_alternative_TRAIN_FORM5"],
       "VALIDATION_public_XG5":audit["historically_published_alternative_VALIDATION_FORM5_xG5"],
       "original_CatBoost_fitted":False},sort_keys=True))
if __name__=="__main__":main()
