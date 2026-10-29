"""GATE14 isolation review after 74 FPL alternative xG historic revisions.

A proven FPL player xG sum never proves original PitchAPI native team xG.
This isolated research gate cannot fit or silently change the baseline M1.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json
from collections import Counter
from pathlib import Path
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from scripts.step14_fpl74_asof_train_xg_recovery import SCHEMA
from scripts.step14_fpl_core_2025_independent_asof import _utc

GATE_SCHEMA="kb3-step14-74-FPL-old-player-xg-independent-research-only-gate-v1"
class Gate74Error(ValueError):pass

def audit(source,rows,bytes_):
    if source.get("schema")!=SCHEMA or source.get("matrix_gzip_sha256")!=hashlib.sha256(bytes_).hexdigest():
        raise Gate74Error("WRONG_SOURCE_OR_CHANGED_MATRIX_HASH")
    ids=set();counts=Counter();public=Counter();player_xg5=Counter();maskcounts=Counter()
    for x in rows:
        ident=x.get("fixture_id")
        if not isinstance(ident,str) or ident in ids:raise Gate74Error("INVALID_OR_DUPLICATE_ORIGINAL_FIXTURE")
        ids.add(ident)
        part=x.get("partition")
        if part not in ("TRAIN","VALIDATION"):raise Gate74Error("TEST_MUST_NOT_BE_EXAMINED")
        counts[part]+=1
        if x.get("original_native_121_plus_38_certified") is not False:
            raise Gate74Error("ORIGINAL_PIT_FALSE_PROMOTION")
        val=x["public_source_research_121_numeric_features"]
        flag=x["public_source_research_38_missing_flags"]
        elo=x["separate_2026_retrospective_native_19_Elo_NOT_historic_PIT"]
        if set(val)!=EXPECTED_FEATURES or set(flag)!=EXPECTED_MISSING or len(elo)!=19:
            raise Gate74Error("121_38_OR_19_FIELDS_CHANGED")
        if any(val[k] is not None for k in elo):
            raise Gate74Error("2026_RECONSTRUCTED_ELO_LEAKED_INTO_OLD_SOURCE")
        if any(v is not None and type(v) is not bool for v in flag.values()):
            raise Gate74Error("MISSING_MASK_NOT_BOOLEAN")
        src=x["history_public_asof_source"]
        if src["status"].startswith("PINNED"):
            if not src.get("witness_utc") or _utc(src["witness_utc"])>=_utc(x["kickoff_utc"]):
                raise Gate74Error("NOT_INDEPENDENTLY_OLD_PUBLIC")
            public[part]+=1
        if part=="TRAIN":
            hasxg=any(val[k] is not None for k in EXPECTED_FEATURES
                if k.endswith(("_xg_avg","_xga_avg")))
            if hasxg and (src.get("provider")!="vaastav_FPL_OPTA_PLAYER_XG_NOT_PITCHAPI"
                          or not src.get("external_xG_definition_is_NOT_original_PitchAPI")
                          or not src.get("FPL_player_xG_original_blob_sha256")):
                raise Gate74Error("TEAM_XG_SOURCE_SEMANTICS_FABRICATED")
            if src["status"]=="PINNED_GHARCHIVE_FPL_PLAYER_XG5_ALTERNATIVE_RESEARCH":
                for side in ("home","away"):
                    for suffix in ("xg_avg","xga_avg"):
                        if val[f"{side}_all_5_{suffix}"] is None:
                            raise Gate74Error("FALSE_COMPLETE_FPL_SOURCE_XG5")
                player_xg5[part]+=1
        maskcounts[part]+=sum(v is not None for v in flag.values())
    if counts!={"TRAIN":760,"VALIDATION":380}:
        raise Gate74Error("ORIGINAL_FROZEN_SPLIT_CHANGED")
    if (public["TRAIN"]!=source["original_760_TRAIN_public_FORM5_total_after_74"]
        or public["VALIDATION"]!=109
        or player_xg5["TRAIN"]!=source["TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5"]):
        raise Gate74Error("EVIDENCE_COUNTS_NOT_REPRODUCED")
    if (source.get("original_native_159_PIT_TRAIN_eligible")!=0
        or source.get("original_native_159_PIT_VALIDATION_eligible")!=0
        or source.get("GATE14")!="PENDING"
        or source.get("CatBoost_M1_original_fitted") is not False
        or source.get("TEST_2026_27_read") is not False):
        raise Gate74Error("ORIGINAL_GATE14_UNLAWFULLY_CHANGED")
    return {"schema":GATE_SCHEMA,
      "all_74_revisions_considered":True,
      "original_760_TRAIN":760,"original_380_VALIDATION":380,
      "real_historic_external_public_FORM5_TRAIN":public["TRAIN"],
      "real_historic_external_public_FORM5_VALIDATION":public["VALIDATION"],
      "real_historic_ALTERNATIVE_FPL_player_xG5_TRAIN":player_xg5["TRAIN"],
      "real_historic_ALTERNATIVE_FPLCore_xG5_VALIDATION":107,
      "source_alternative_FPL_xG_not_original_PitchAPI":True,
      "original_121_plus_38_native_PIT_TRAIN":0,
      "original_121_plus_38_native_PIT_VALIDATION":0,
      "original_CatBoost_M1_training_allowed":False,
      "original_CatBoost_M1_fitted":False,
      "model_or_split_changed":False,"TEST_2026_27_examined":False,
      "original_GATE14":"PENDING",
      "next_evidence_needed":"native PitchAPI first-published-at snapshots and original xG semantics or formally separate alternative research contract"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--matrix",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise Gate74Error("APPEND_ONLY_GATE")
    compressed=Path(a.matrix).read_bytes()
    with gzip.open(a.matrix,"rt",encoding="utf8") as f:
        matrix=[json.loads(s) for s in f if s.strip()]
    source=json.loads(Path(a.source).read_text())
    result=audit(source,matrix,compressed)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"TRAIN":result["real_historic_external_public_FORM5_TRAIN"],
        "TRAIN_FPL_xG5":result["real_historic_ALTERNATIVE_FPL_player_xG5_TRAIN"],
        "VALIDATION_FORM5":109,"GATE14":"PENDING","original_fit":False},sort_keys=True))
if __name__=="__main__":main()
