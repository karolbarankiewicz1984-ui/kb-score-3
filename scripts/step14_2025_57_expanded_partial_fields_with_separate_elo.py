"""Join 57 witnessed source FORM5/10/15 with separate 1140 native retro Elo.

No production features or training. Separate original-publication-proof status
for public xG/FT vs 2026 retrospective reconstructed Elo for each field family.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from scripts.step14_2025_expand_witnessed_form5_asof import (
    ALL,source_at_version,SCHEMA as PUBLIC_SCHEMA)
from scripts.step14_fplcore_2025_extended_field_recovery import _candidate
from scripts.step14_fpl_core_2025_independent_asof import _reference,_utc
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import (
    SCHEMA as ELO_SCHEMA,EXPANDED)
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING

ROOT=Path(__file__).resolve().parents[1]
ELOFILE="data/audits/STEP14_2023_TO_2026_NATIVE_1140_RETRO_ELO_PLUS_2025_WITNESSED_2026-10-29.json"
SCHEMA="kb3-step14-57-old-asof-public-research-features-separate-19-retro-Elo-v1"
class Coverage57Error(ValueError): pass

def audit(root=ROOT):
    root=Path(root)
    public=json.loads((root/EXPANDED).read_text(encoding="utf8"))
    elo=json.loads((root/ELOFILE).read_text(encoding="utf8"))
    if public.get("schema")!=PUBLIC_SCHEMA or not public.get("old_historic_GitHub_server_source_clocks_verified") or public["GATE14"]!="PENDING":
        raise Coverage57Error("UNTRUSTED_HISTORIC_PUBLIC_CANDIDATES")
    if elo.get("schema")!=ELO_SCHEMA or elo.get("GATE14")!="PENDING" or elo.get("original_native_1140_full_chronological_Elo_replay_rows")!=1140:
        raise Coverage57Error("UNTRUSTED_RETRO_ELO_SOURCE")
    index={r["original_native_match_id"]:r for r in elo["research_elo_feature_rows"]}
    matched={}
    for entry in elo["strict_new_public_native_crosswalk"]:
        key=(entry["native_fixture_id"],entry["native_kickoff_utc"])
        if key in matched or entry["native_fixture_id"] not in index:
            raise Coverage57Error("NATIVE_TARGET_DUPLICATE_OR_UNKNOWN")
        matched[key]=entry
    no_score=_reference(root/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json")
    ref={(r["home"],r["away"],r["ko"].isoformat()):r for r in no_score}
    selected_sources={x["evidence_source_commit"] for x in public["targets"]}
    lookup={x[0]:x for x in ALL}
    if not selected_sources<=set(lookup):raise Coverage57Error("UNPINNED_SOURCE")
    prior={}
    for commit in sorted(selected_sources):
        proof,valid,past=source_at_version(lookup[commit],no_score,include_predecessors=True)
        prior[commit]={"witness":proof["witness"]["server_created_at_utc"],
                       "commit":commit,"past":past,
                       "quarantined":proof["quarantined_gameweeks"]}
    by_pairtime={}
    for entry in elo["strict_new_public_native_crosswalk"]:
        v=index[entry["native_fixture_id"]]
        key=(v["original_native_match_id"],v["kickoff_utc"])
        if key in by_pairtime:raise Coverage57Error("DUPLICATE_NATIVE_ELO")
        by_pairtime[key]=(entry,v)
    rows=[]
    for target in public["targets"]:
        stem=(target["target_public_home"],target["target_public_away"],
              _utc(target["target_kickoff_utc"]).isoformat())
        original=ref.get(stem)
        if original is None:raise Coverage57Error("WITNESSED_PUBLIC_TARGET_NOT_REFERENCE")
        src=prior[target["evidence_source_commit"]]
        extra=_candidate(original,no_score,src["past"],src)
        # The 57 new source features must reproduce the already independently
        # reconstructed FORM5 average from its unique pinned old SHA.
        for side in ("home","away"):
            for key in ("points_avg","gf_avg","ga_avg","xg_avg","xga_avg"):
                label="alternative_"+key if key.startswith("xg") else key
                a=target["prematch_public_FORM5"][side][label]
                b=extra["research_features_not_native_PitchAPI"][f"{side}_all_5_{key}"]
                if a is None or b is None or abs(a-b)>0.00001:
                    raise Coverage57Error("FORM5_DID_NOT_REPRODUCE_FROZEN_OLD_SHA")
        native=[m for m in elo["strict_new_public_native_crosswalk"] if
                m["native_kickoff_utc"]==target["target_kickoff_utc"]
                and m["source_SHA"]==target["evidence_source_commit"]
                and m.get("public_pair")==[target["target_public_home"],target["target_public_away"]]]
        if len(native)!=1:
            raise Coverage57Error("MISSING_UNIQUE_NATIVE_SIDE_TIME_ELO_JOIN")
        n=native[0];e=index[n["native_fixture_id"]]
        if e["original_partition"]!="VALIDATION" or e["kickoff_utc"]!=n["native_kickoff_utc"]:
            raise Coverage57Error("ELO_SNAPSHOT_NOT_NATIVE_VALIDATION")
        vals=e["research_only_retrospective_19_Elo_field_values"]
        if len(vals)!=19:raise Coverage57Error("RETRO_ELO_19_FIELDS_CHANGED")
        if any(extra["research_features_not_native_PitchAPI"][k] is not None for k in vals):
            raise Coverage57Error("RETRO_ELO_SILENTLY_OVERWROTE_PUBLIC_FIELD")
        rows.append({
          "native_original_validation_fixture_id":n["native_fixture_id"],
          "native_kickoff_utc":n["native_kickoff_utc"],
          "historically_witnessed_source_SHA":target["evidence_source_commit"],
          "historically_witnessed_source_asof_utc":target["source_publication_witness_utc"],
          "public_source_research_partial_121_values":extra["research_features_not_native_PitchAPI"],
          "public_source_research_partial_38_masks":extra["research_missing_flags_not_native_PitchAPI"],
          "2026_retrospective_native_19_Elo_values_NOT_original_historical_source":vals,
          "public_numeric_non_null":extra["non_null_numeric_source_field_count"],
          "public_flags_non_null":extra["non_null_missing_flag_source_count"],
          "original_159_PitchAPI_PIT_eligible":False})
    if len(rows)!=len(public["targets"]) or len({x["native_original_validation_fixture_id"] for x in rows})!=len(rows):
        raise Coverage57Error("UNIQUE_CROSSWALK_NOT_COMPLETE")
    fieldnames={k for x in rows for k,v in x["public_source_research_partial_121_values"].items() if v is not None}
    fieldflags={k for x in rows for k,v in x["public_source_research_partial_38_masks"].items() if v is not None}
    return {"schema":SCHEMA,"public_witnessed_2025_native_fixture_rows":len(rows),
        "new_native_rows_over_original_18":len(rows)-18,
        "source_research_numeric_fields_with_at_least_one_value":len(fieldnames),
        "source_research_flags_with_at_least_one_value":len(fieldflags),
        "total_source_numeric_nonnull":sum(x["public_numeric_non_null"] for x in rows),
        "total_source_missing_flag_nonnull":sum(x["public_flags_non_null"] for x in rows),
        "2026_retrospective_Elo_field_names_per_native_match":19,
        "public_research_field_names":sorted(fieldnames),
        "separate_sources_and_no_fake_PIT_promotion":True,
        "TEST_2026_27_examined":False,
        "original_121_plus_38_PIT_eligible":0,
        "training_allowed":False,
        "GATE14":"PENDING","rows":rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise Coverage57Error("APPEND_ONLY")
    result=audit()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({"total_native_targets":result["public_witnessed_2025_native_fixture_rows"],
        "source_numeric_fields":result["source_research_numeric_fields_with_at_least_one_value"],
        "source_numeric_slots":result["total_source_numeric_nonnull"],
        "source_flag_slots":result["total_source_missing_flag_nonnull"],
        "separate_retro_Elo_fields":19,"original_M1_allowed":False},sort_keys=True))

if __name__=="__main__":
    main()
