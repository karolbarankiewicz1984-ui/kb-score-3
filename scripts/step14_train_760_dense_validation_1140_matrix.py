"""Step14 phases 1-3: exact original 760 TRAIN historical source + dense VALIDATION.

Original TRAIN labels, original TEST, target xG, odds never read. All earlier
FT values come ONLY from independently timestamped immutable PUBLIC source
versions with their source bytes verified, not today's retrospective scores.
Separately join native 2026 Elo replay (19 fields) without converting it to PIT.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,math,os
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step14_multiseason_pit import fetch,raw_url,parse_openfootball
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources,old_source_rows
from scripts.step14_fpl_core_2025_independent_asof import _name,_utc
from scripts.step14_2025_expand_witnessed_form5_asof import source_at_version
from scripts.step14_2025_dense_25_historical_witnesses import SOURCE_LIST
from scripts.step14_fplcore_2025_extended_field_recovery import _candidate
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import _valid_safe
from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from src.kb3_step14_native_team_crosswalk import canonical_team_name

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-full-760-train-plus-dense-validation-public-PIT-research-159-field-v1"
DENSE="data/audits/STEP14_2025_FPLCORE_DENSE_25_INDEPENDENT_ASOF_2026-10-29.json"
ELO="data/audits/STEP14_2023_TO_2026_NATIVE_1140_RETRO_ELO_PLUS_2025_WITNESSED_2026-10-29.json"
ALIAS={"luton":"luton town","sheffield utd":"sheffield united",
       "ipswich":"ipswich town","leicester":"leicester city",
       "newcastle":"newcastle united","west ham":"west ham united",
       "manchester utd":"manchester united"}
class RecoverError(ValueError): pass

def _team(rawname):
    canonical=_name(rawname)
    return ALIAS.get(canonical,canonical)

def _source_rows(source,fetcher=fetch):
    """Preserve authenticated original source: old FT never inferred/filled."""
    raw=fetcher(raw_url(source),limit=3_000_001)
    import hashlib
    if hashlib.sha256(raw).hexdigest()!=source["sha"]:
        raise RecoverError("PINNED_HISTORIC_SOURCE_HASH_MISMATCH")
    # existing fail-closed reader validates FPL old GW count/clock or OF grid
    old_source_rows(source,fetcher=lambda url,**kwargs:raw)
    stamped=_utc(source["push"])
    old={}
    schedules={}
    if source.get("provider")=="FPL":
        season=source["season"]
        nameurl=f"https://raw.githubusercontent.com/{source['repo']}/{source['commit']}/data/{season}/teams.csv"
        teams_raw=fetcher(nameurl,limit=100_001)
        names={}
        for row in csv.DictReader(io.StringIO(teams_raw.decode("utf-8-sig"))):
            ident=str(row["id"]);name=_team(row["name"])
            if ident in names or name in names.values():raise RecoverError("HISTORIC_FPL_TEAM_ALIAS_AMBIGUOUS")
            names[ident]=name
        if len(names)!=20:raise RecoverError("HISTORIC_FPL_TEAM_COUNT_NOT_20")
        rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline="")))
        for row in rows:
            if not row["kickoff_time"]:continue
            ko=_utc(row["kickoff_time"])
            try:key=(names[row["team_h"]],names[row["team_a"]],ko.isoformat())
            except KeyError as exc:raise RecoverError("UNKNOWN_FPL_TEAM_ID") from exc
            if key in schedules:raise RecoverError("DUPLICATE_SOURCE_FIXTURE")
            finished=row["finished"]=="True"
            if finished:
                if (stamped-ko).total_seconds()<3*3600:raise RecoverError("OLD_FT_BEFORE_RESULT_LAG")
                try:h,a=int(row["team_h_score"]),int(row["team_a_score"])
                except (ValueError,TypeError) as exc:raise RecoverError("INVALID_HISTORIC_PUBLIC_SCORE") from exc
                if not (0<=h<=30 and 0<=a<=30):raise RecoverError("HISTORIC_PUBLIC_SCORE_OUT_OF_RANGE")
                old[key]={"home":key[0],"away":key[1],"kickoff":ko,
                          "home_goals":h,"away_goals":a,
                          "home_xg":None,"away_xg":None}
            elif row["team_h_score"] or row["team_a_score"]:
                raise RecoverError("FUTURE_MATCH_HAS_SCORE")
            schedules[key]=finished
    elif source.get("provider")=="OpenFootball":
        parsed=parse_openfootball(raw,source)
        doc=json.loads(raw)["matches"]
        for m,p in zip(doc,parsed):
            if p["kickoff"] is None:continue
            ko=p["kickoff"];key=(_team(p["home"]),_team(p["away"]),ko.isoformat())
            if key in schedules:raise RecoverError("DUPLICATE_OLD_PUBLIC_EVENT")
            finished=p["ft_published"]
            if finished:
                if (stamped-ko).total_seconds()<3*3600:raise RecoverError("OLD_OF_RESULT_BEFORE_LAG")
                score=m["score"]["ft"]
                if not (isinstance(score,list) and len(score)==2 and all(type(x) is int and 0<=x<=30 for x in score)):
                    raise RecoverError("OLD_OF_FT_BAD")
                old[key]={"home":key[0],"away":key[1],"kickoff":ko,
                          "home_goals":score[0],"away_goals":score[1],
                          "home_xg":None,"away_xg":None}
            schedules[key]=finished
    else:raise RecoverError("UNSUPPORTED_HISTORIC_SOURCE")
    return {"source":source,"commit":source["commit"],"witness":source["push"],
            "past":old,"schedules":schedules,
            "source_raw_sha256":source["sha"],
            "source_time_independently_verified":True}

def _original_schedule(native,allowed):
    """Full current native ID+side+kickoff graph only. NO native scores read."""
    rows={};part=Counter();per_season=defaultdict(list)
    for season,fixtures in native.items():
        if season not in ("2023-24","2024-25","2025-26") or len(fixtures)!=380:
            raise RecoverError("UNEXPECTED_SEASON_OR_COUNT")
        for item in fixtures:
            ident=item["id"];expected=allowed.get(ident)
            if expected is None or item["time_utc"]!=expected[0]:
                raise RecoverError("FROZEN_ORIGINAL_NATIVE_MATCH_ID_KICKOFF_DRIFT")
            role=expected[1]
            if role!=("VALIDATION" if season=="2025-26" else "TRAIN"):
                raise RecoverError("ORIGINAL_SPLIT_ROLE_CHANGED")
            home=_team(item["home_team"]["name"]);away=_team(item["away_team"]["name"])
            if home==away:raise RecoverError("NATIVE_SELF_MATCH")
            kickoff=_utc(item["time_utc"])
            key=(home,away,kickoff.isoformat())
            if key in rows:raise RecoverError("CANONICAL_SOURCE_IDENTITY_NOT_UNIQUE")
            row={"native_fixture_id":ident,"season":season,"role":role,"key":key,
                 "home":home,"away":away,"ko":kickoff}
            rows[key]=row;per_season[season].append(row)
            part[role]+=1
    if part!={"TRAIN":760,"VALIDATION":380}:raise RecoverError("NOT_760_380")
    return rows,per_season

def _train_recover(originals,old_sources):
    indexed={r["key"]:r for r in originals}
    selected=None
    for src in old_sources:
        if src["source"]["season"]!=originals[0]["season"]:raise RecoverError("WRONG_OLD_SEASON")
        if selected is None or _utc(src["witness"])>_utc(selected["witness"]):
            selected=src
    return indexed

def _best_public_candidate(target,schedule,versions):
    best=None
    for src in versions:
        if not _utc(src["witness"])<target["ko"]:continue
        if src["schedules"].get(target["key"]) is not False:
            continue  # Source must actually show this FUTURE fixture unplayed.
        doc=_candidate(target,schedule,src["past"],src)
        vals=doc["research_features_not_native_PitchAPI"]
        sides=all(vals.get(f"{side}_all_5_points_avg") is not None
                  for side in ("home","away"))
        # Count strict 5 predecessors, never look at target labels.
        numeric=doc["non_null_numeric_source_field_count"]
        if not sides:continue
        if best is None or (_utc(src["witness"]),numeric)>(_utc(best[0]["witness"]),best[1]["non_null_numeric_source_field_count"]):
            best=(src,doc)
    return best

def _asof_values(target,all_matches,src,doc):
    values=doc["research_features_not_native_PitchAPI"]
    flags=doc["research_missing_flags_not_native_PitchAPI"]
    # Historical FPL fixture CSV does not include xG. It cannot assert
    # measured "0 xG observations": no native/alternative xG at all.
    for side in ("home","away"):
        for venue in ("all","venue"):
            for n in (5,10,15):
                stem=f"{side}_{venue}_{n}"
                for end in ("xg_n","xg_avg","xga_n","xga_avg"):
                    values[f"{stem}_{end}"]=None
                for end in ("xg","xga"):
                    flags[f"{stem}_{end}"]=None
    for name in values:
        if name.endswith("opponent_elo_avg") or name in ("elo_home_minus_away","home_elo","away_elo",
                "home_elo_games_available","away_elo_games_available",
                "home_prior_seasons_games_available","away_prior_seasons_games_available"):
            values[name]=None
    assert set(values)==EXPECTED_FEATURES and set(flags)==EXPECTED_MISSING
    return values,flags

def run(root=ROOT,*,native_override=None,old_sources_override=None):
    root=Path(root)
    safe=_valid_safe(root)
    if native_override is None:
        native,api_calls=native_three_seasons(key=os.environ.get("PITCHAPI_API_KEY",""))
    else:native=native_override;api_calls=0
    allrows,seasons=_original_schedule(native,safe)
    elo=json.loads((root/ELO).read_text())
    if (elo.get("original_native_1140_full_chronological_Elo_replay_rows")!=1140
        or elo.get("GATE14")!="PENDING"):raise RecoverError("OLD_ELO_REPLAY_NOT_PINNED")
    elo_index={r["original_native_match_id"]:r for r in elo["research_elo_feature_rows"]}
    if len(elo_index)!=1140 or any(x["native_fixture_id"] not in elo_index for x in allrows.values()):
        raise RecoverError("MISSING_ORIGINAL_ELO_REPLAY_MATCH")
    if old_sources_override is None:
        chosen=[s for s in independently_pinned_sources() if s["season"] in ("2023-24","2024-25")]
        # For exact old SHA, also re-check original clock/pin and sha again.
        with ThreadPoolExecutor(max_workers=6) as p:
            old_src=list(p.map(_source_rows,chosen))
    else:old_src=old_sources_override
    by_season=defaultdict(list)
    for old in old_src:by_season[old["source"]["season"]].append(old)
    if old_sources_override is None and len(old_src)!=12:
        raise RecoverError("NOT_TWELVE_PINNED_TRAIN_OLD_PUBLIC_SOURCES")
    dense=json.loads((root/DENSE).read_text())
    if (dense.get("independent_GitHub_server_witnessed_old_versions")!=25
        or not dense.get("all_original_57_preserved")
        or dense.get("GATE14")!="PENDING"):raise RecoverError("DENSE_SOURCE_PROOF_CHANGED")
    older_target={(t["target_public_home"],t["target_public_away"],_utc(t["target_kickoff_utc"]).isoformat()):t
                  for t in dense["targets"]}
    if len(older_target)!=dense["historically_public_source_FORM5_targets"]:
        raise RecoverError("DENSE_SOURCE_TARGET_DUPLICATE")
    dense_commits={x["evidence_source_commit"] for x in dense["targets"]}
    selected={v[0]:v for v in SOURCE_LIST}
    if not dense_commits<=set(selected):raise RecoverError("UNPINNED_DENSE_SOURCE_COMMIT")
    # Strictly pinned source and old prior rows for each used actual target.
    dense_maps={}
    public_validation=[]
    from scripts.step14_fpl_core_2025_independent_asof import _reference
    public_ref=_reference(root/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json")
    validation_ref={r["key"]:r for r in public_ref}
    for sha in sorted(dense_commits):
        proof,eligible,past=source_at_version(selected[sha],public_ref,include_predecessors=True)
        dense_maps[sha]={"source":selected[sha],"commit":sha,
                         "witness":proof["witness"]["server_created_at_utc"],
                         "past":past}
    output=[];part=Counter();full5=Counter();source_fields=Counter();bad_native=0
    used_validation=set();source_targets=Counter()
    for season in ("2023-24","2024-25","2025-26"):
        current=seasons[season]
        versions=by_season.get(season,[])
        for t in sorted(current,key=lambda x:(x["ko"],x["native_fixture_id"])):
            vals={name:None for name in EXPECTED_FEATURES}
            masks={name:None for name in EXPECTED_MISSING}
            native=t["native_fixture_id"];role=t["role"]
            source={"status":"NO_QUALIFIED_OLD_PUBLIC_F5","sha":None,"witness_utc":None}
            if role=="TRAIN":
                chosen=_best_public_candidate(t,current,versions)
                if chosen is not None:
                    s,doc=chosen
                    vals,masks=_asof_values(t,current,s,doc)
                    source={"status":"PINNED_HISTORIC_PUBLIC_F5_NO_XG",
                            "sha":s["commit"],"witness_utc":s["witness"],
                            "provider":s["source"].get("provider","FPL")}
            else:
                key=t["key"]
                old=older_target.get(key)
                if old is not None:
                    src=dense_maps[old["evidence_source_commit"]]
                    reference=validation_ref.get(key)
                    if reference is None:raise RecoverError("DENSE_NATIVE_CROSSWALK_NOT_EXACT")
                    d=_candidate(reference,public_ref,src["past"],src)
                    vals=d["research_features_not_native_PitchAPI"]
                    masks=d["research_missing_flags_not_native_PitchAPI"]
                    # Each candidate is source-backed in exact old version.
                    for side in ("home","away"):
                        if vals.get(f"{side}_all_5_xg_avg") is None:
                            raise RecoverError("DENSE_XG5_FROZEN_SOURCE_MISMATCH")
                        for suffix in ("points_avg","gf_avg","ga_avg","xg_avg","xga_avg"):
                            targetval=old["prematch_public_FORM5"][side][
                                ("alternative_"+suffix) if suffix.startswith("xg") else suffix]
                            got=vals[f"{side}_all_5_{suffix}"]
                            if got is None or abs(targetval-got)>0.00001:
                                raise RecoverError("2025_OLD_PREMATCH_NUMERIC_SOURCE_CHANGED")
                    used_validation.add(native)
                    source={"status":"PINNED_HISTORIC_ALTERNATIVE_PUBLIC_F5_XG5",
                            "sha":src["commit"],"witness_utc":src["witness"],
                            "provider":"FPL-Core-Insights"}
            if set(vals)!=EXPECTED_FEATURES or set(masks)!=EXPECTED_MISSING:
                raise RecoverError("FEATURE_SCHEMA_121_38_CHANGED")
            if source["witness_utc"] and _utc(source["witness_utc"])>=t["ko"]:
                raise RecoverError("LEAKED_POST_TARGET_SOURCE")
            if source["witness_utc"]:
                full5[role]+=1
                source_targets[(role,source["status"])]+=1
            part[role]+=1
            source_fields[role]+=sum(v is not None for v in vals.values())
            e=elo_index[native]
            if e["original_partition"]!=role or _utc(e["kickoff_utc"])!=t["ko"]:
                raise RecoverError("ELO_UNTRUSTED_NATIVE_FIXTURE_JOIN")
            separate=e["research_only_retrospective_19_Elo_field_values"]
            if len(separate)!=19:raise RecoverError("ELO_19_CONTRACT_CHANGED")
            if any(vals[name] is not None for name in separate):
                raise RecoverError("RETROSPECTIVE_ELO_MUST_NOT_OVERWRITE_HISTORIC_SOURCE_FIELDS")
            output.append({"fixture_id":native,"partition":role,"season":season,
                "kickoff_utc":t["ko"].isoformat().replace("+00:00","Z"),
                "history_public_asof_source":source,
                "public_source_research_121_numeric_features":vals,
                "public_source_research_38_missing_flags":masks,
                "separate_2026_retrospective_native_19_Elo_NOT_historic_PIT":separate,
                "original_native_121_plus_38_certified":False})
    if (part!={"TRAIN":760,"VALIDATION":380}
        or len(output)!=1140 or len(used_validation)!=len(dense["targets"])):
        raise RecoverError("ORIGINAL_TRAIN_VALIDATION_OR_DENSE_COVERAGE_MISMATCH")
    counts={k:sum(1 for row in output if row["partition"]==k
              and row["history_public_asof_source"]["status"].startswith("PINNED"))
            for k in ("TRAIN","VALIDATION")}
    reported={
      "schema":SCHEMA,"original_frozen_760_TRAIN_380_VALIDATION":dict(part),
      "real_api_requests":api_calls,"original_native_exact_ID_sides_and_time":len(output),
      "historic_train_source_versions_verified":len(old_src),
      "historic_validation_source_versions_verified":25,
      "distinct_original_TRAIN_with_historical_public_result_FORM5":counts["TRAIN"],
      "distinct_original_VALIDATION_with_historical_alternative_xG5":counts["VALIDATION"],
      "new_validation_targets_beyond_prior_57":counts["VALIDATION"]-57,
      "public_source_nonnull_numeric_slots_by_partition":dict(source_fields),
      "public_source_numerics_are_alternative_to_original_PitchAPI":True,
      "nineteen_native_Elo_fields_retro_2026_not_historic_asof":True,
      "original_PitchAPI_xG_first_published_UTC_per_match":None,
      "original_159_contract_complete_PIT_TRAIN":0,
      "original_159_contract_complete_PIT_VALIDATION":0,
      "official_fit_M1_allowed":False,"original_M1_trained":False,"GATE14":"PENDING",
      "TEST_examined":False,"original_TRAIN_target_scores_read":False,
      "model_or_split_modified":False}
    return reported,output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--matrix",required=True)
    a=p.parse_args()
    out=Path(a.out);matrix=Path(a.matrix)
    if out.exists() or matrix.exists():raise RecoverError("APPEND_ONLY_NO_OVERWRITE")
    doc,rows=run()
    out.parent.mkdir(parents=True,exist_ok=True);matrix.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(matrix,"wt",encoding="utf8",compresslevel=7) as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n")
    doc["matrix_gzip_sha256"]=hashlib.sha256(matrix.read_bytes()).hexdigest()
    doc["matrix_rows"]=len(rows)
    out.write_text(json.dumps(doc,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print(json.dumps({"train":doc["distinct_original_TRAIN_with_historical_public_result_FORM5"],
         "validation":doc["distinct_original_VALIDATION_with_historical_alternative_xG5"],
         "train_total":760,"validation_total":380,
         "original_PIT_fit_allowed":False,"gate14":"PENDING"},sort_keys=True))
if __name__=="__main__":main()
