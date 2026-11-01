"""NED/BEL native fixture-ID phase hints: research, no training promotion."""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter
from src.kb3_step16_m0_720_eight_forward import hashobj,require
KEYS=("round","stage","phase","competition_phase")
def classify(hints):
    values=[str(hints.get(k) or "").lower() for k in KEYS]
    regular=any("regular" in x for x in values)
    extra=any(any(t in x for t in ("play-off","playoff","postseason","relegation","final","qualification")) for x in values)
    if regular and extra:return "CONFLICTING_PROVIDER_HINTS"
    if extra:return "NONREGULAR_HINT_REQUIRES_REVIEW"
    if regular:return "REGULAR_HINT_REQUIRES_REVIEW"
    return "UNKNOWN_PHASE_REQUIRES_REVIEW"
def audit(report):
    data=report.get("ned_bel_historical_phase_native_id_review")
    if data is None:
        return {"status":"PENDING_NEXT_REAL_FORECAST","fixture_id_review_complete":False,
                "research_only":True,"training_allowed":False}
    require(report.get("mode")=="forecast" and
        report.get("original_2026_27_Premier_League_TEST_accessed") is False,
        "NOT_NATIVE_M0_SOURCE")
    require(set(data)=={"NED","BEL"},"PHASE_COUNTRIES_INVALID")
    results={}
    for country in ("NED","BEL"):
        obj=data[country]; rows=obj.get("fixture_rows",[])
        shape=report["season_shapes"][country+"/2025/2026"]
        require(len(rows)==shape["all"]==obj.get("native_fixture_rows"),
            "NATIVE_FIXTURE_ROW_MISMATCH")
        ids=[r["fixture_id"] for r in rows]
        require(len(set(ids))==len(ids) and
                hashobj(sorted(ids))==shape["id_sha256"],
                "NATIVE_FIXTURE_IDS_UNVERIFIED")
        require(obj.get("any_phase_pass_or_training_approval") is False,
                "UNAUTHORIZED_PHASE_APPROVAL")
        state=Counter()
        for row in rows:
            require(row["formal_phase_reviewed"] is False,
                "SOURCE_ROW_FALSELY_REVIEWED")
            hints=row.get("provider_stage_hints")
            require(isinstance(hints,dict) and set(hints)==set(KEYS),
                "NATIVE_STAGE_HINT_SCHEMA_INVALID")
            state[classify(hints)]+=1
        n=shape["teams"]
        results[country]={"native_fixture_rows":len(ids),
            "reference_double_round_robin":n*(n-1),
            "extra_count_is_not_phase_proof":len(ids)-n*(n-1),
            "hint_distribution":dict(state),"all_native_ids_hash_match":True,
            "phase_by_native_id_approved":False}
    return {"schema":"kb3-phase-native-ids-adjudication-gate-v1",
      "status":"SOURCE_HINTS_NOT_FINAL_REVIEW","results":results,
      "fixture_id_review_complete":False,"training_allowed":False,
      "research_only":True,"test_2026_27_accessed":False}
def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();dst=Path(a.out)
    require(not dst.exists(),"APPEND_ONLY_REPORT")
    val=audit(json.loads(Path(a.source).read_text()))
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(val,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(val,sort_keys=True))
if __name__=="__main__":main()
