"""KB3 M1-R: actual 1140 retrospective TRAIN/VALIDATION feature reconstruction.

Research ONLY. Future target result never becomes a feature; all predecessor
results are released at kickoff+48h. Uses original exact PitchAPI fixture IDs
and locked 760/380 split, no 2026/27 TEST. Stable 121+38 names and explicit
missingness. Historical score data collected now are NOT mislabeled as PIT.
Optional old FPL/Opta vs FPL-Core xG5 stay in a separate, source-labelled
research overlay and NEVER substitute original PitchAPI xG.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,os
from collections import Counter,defaultdict
from datetime import timedelta
from heapq import heappush,heappop
from pathlib import Path
from src.kb3_features import EloParameters,elo_probability
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from scripts.step14_elo_2023_2026_native_replay_and_extended_crosswalk import (
    validated_events,_valid_safe)
from scripts.step14_full_1140_native_public_pit_lineage import native_three_seasons
from scripts.step14_fpl_core_2025_independent_asof import _utc

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-m1r-1140-three-seasons-relaxed-48h-121x38-research-only-v1"
LAG=timedelta(hours=48)
XG_MATRIX="data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_1140x159_2026-10-29.jsonl.gz"
XG_SUMMARY="data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_RESEARCH_SUMMARY_2026-10-29.json"
class M1RRecomputeError(ValueError):pass

def _avg(items):
    return round(sum(items)/len(items),6) if items else None

def _finite(v):
    return type(v) in (float,int) and math.isfinite(v)

def recompute(events,*,minimum_previous=3,expected=None):
    """Source scores are consumed ONLY after their 48h release timestamps."""
    if not 1<=minimum_previous<=15:raise M1RRecomputeError("INVALID_MINIMUM")
    ordered=sorted(events,key=lambda e:(e["kickoff"],e["fixture_id"]))
    if expected is not None and len(ordered)!=expected:
        raise M1RRecomputeError("NOT_EXPECTED_EVENT_COUNT")
    if len({e["fixture_id"] for e in ordered})!=len(ordered):
        raise M1RRecomputeError("DUPLICATE_FIXTURE_ID")
    params=EloParameters()
    elo={};last_year={};games=defaultdict(list);upcoming=[]
    rows=[];lag_attested=0
    def rating(tid,year):
        prev=last_year.get(tid)
        if prev is not None and year<prev:raise M1RRecomputeError("ELO_NONMONOTONIC_YEAR")
        v=elo.get(tid,params.initial)
        if prev is None:
            last_year[tid]=year
        elif prev<year:
            v=params.initial+(v-params.initial)*params.season_retention**(year-prev)
            elo[tid]=v;last_year[tid]=year
        return v
    def incorporate(p):
        nonlocal lag_attested
        h,a=p["home_id"],p["away_id"]
        rh,ra=rating(h,p["year"]),rating(a,p["year"])
        score=1.0 if p["gh"]>p["ga"] else .0 if p["gh"]<p["ga"] else .5
        delta=params.k*(score-elo_probability(rh,ra,params))
        elo[h]=rh+delta;elo[a]=ra-delta
        for tid,venue,gf,ga,opp in ((h,True,p["gh"],p["ga"],ra),
                                    (a,False,p["ga"],p["gh"],rh)):
            if games[tid] and games[tid][-1]["ko"]>p["kickoff"]:
                raise M1RRecomputeError("PREDECESSORS_NONMONOTONIC")
            games[tid].append({"ko":p["kickoff"],"id":p["fixture_id"],
                 "season":p["year"],"home":venue,"gf":gf,"ga":ga,
                 "points":3 if gf>ga else 1 if gf==ga else 0,
                 "opponent_elo":opp})
        lag_attested+=1
    for target in ordered:
        ko=target["kickoff"]
        while upcoming and upcoming[0][0]<=ko:
            _,_,prev=heappop(upcoming)
            if prev["kickoff"]+LAG>ko:
                raise M1RRecomputeError("FUTURE_MATCH_RESULT_LEAK")
            incorporate(prev)
        vals={key:None for key in EXPECTED_FEATURES}
        mask={key:None for key in EXPECTED_MISSING}
        rh,ra=rating(target["home_id"],target["year"]),rating(target["away_id"],target["year"])
        vals["home_elo"]=round(rh,5)
        vals["away_elo"]=round(ra,5)
        vals["elo_home_minus_away"]=round(rh-ra,5)
        predecessor_ids=set()
        for side,tid,is_home in (("home",target["home_id"],True),("away",target["away_id"],False)):
            previous=games[tid]
            if any(g["ko"]+LAG>ko or g["id"]==target["fixture_id"] for g in previous):
                raise M1RRecomputeError("TARGET_OR_UNRELEASED_SCORE_IN_FEATURE")
            predecessor_ids.update(g["id"] for g in previous)
            vals[side+"_elo_games_available"]=len(previous)
            vals[side+"_prior_seasons_games_available"]=sum(g["season"]<target["year"] for g in previous)
            vals[side+"_games_available"]=len(previous)
            vals[side+"_days_since_last_kickoff"]=round((ko-previous[-1]["ko"]).total_seconds()/86400,4) if previous else None
            mask[side+"_days_since_last_kickoff"]=not bool(previous)
            venue=[g for g in previous if g["home"]==is_home]
            vals[side+"_venue_games_available"]=len(venue)
            for scope,group_all in (("all",previous),("venue",venue)):
                for window in (5,10,15):
                    latest=group_all[-window:]
                    n=len(latest)
                    stem=f"{side}_{scope}_{window}"
                    vals[stem+"_n"]=n
                    for metric in ("points","gf","ga","opponent_elo"):
                        vals[stem+"_"+metric+"_avg"]=_avg([x[metric] for x in latest])
                    # This BASE variant deliberately excludes provider-mismatched
                    # xG. An old source's missing xG is NOT zero xG.
                    for metric in ("xg","xga"):
                        vals[stem+"_"+metric+"_n"]=0
                        vals[stem+"_"+metric+"_avg"]=None
                        mask[stem+"_"+metric]=True
                    mask[stem+"_history"]=n<window
        if set(vals)!=EXPECTED_FEATURES or set(mask)!=EXPECTED_MISSING:
            raise M1RRecomputeError("ORIGINAL_121_38_SCHEMA_CHANGED")
        if any(v is not None and not _finite(v) for v in vals.values()):
            raise M1RRecomputeError("INVALID_NUMERIC_FEATURE")
        if any(type(v) is not bool for v in mask.values()):
            raise M1RRecomputeError("INVALID_MISSINGNESS_FLAG")
        if target["fixture_id"] in predecessor_ids:
            raise M1RRecomputeError("TARGET_RESULT_LEAK")
        eligible=all(vals[f"{side}_all_5_n"]>=minimum_previous for side in ("home","away"))
        rows.append({"fixture_id":target["fixture_id"],
           "season":target["season"],"partition":target["partition"],
           "kickoff_utc":ko.isoformat().replace("+00:00","Z"),
           "source_class":"B_RECONSTRUCTED_PREDECESSORS_NOT_OLD_PIT",
           "original_PitchAPI_historic_first_published_at_proven":False,
           "previous_score_release_lag_hours":48,
           "minimum_previous_per_team":minimum_previous,
           "m1r_base_eligible":eligible,
           "ineligible_reason":None if eligible else "COLD_START_FEWER_THAN_3_PRIORS_FOR_ONE_SIDE",
           "m1r_BASE_121_numeric_features":vals,
           "m1r_BASE_38_missing_flags":mask,
           "xg_old_source_separate_overlay":None,
           "original_M1_159_PIT_certified":False})
        heappush(upcoming,(ko+LAG,target["fixture_id"],target))
    while upcoming:
        _,_,prev=heappop(upcoming);incorporate(prev)
    if lag_attested!=len(events) or len(rows)!=len(events):
        raise M1RRecomputeError("NOT_ALL_EVENTS_REPLAYED")
    return rows

def xg_overlay(root,rows):
    """Overlay non-PitchAPI older public xG from prior audited immutable v2.
    Overlay is not part of BASE's 121 feature values, so cannot sneak into
    production original CatBoost. No unlabeled xG values are manufactured.
    """
    root=Path(root)
    report=json.loads((root/XG_SUMMARY).read_text())
    if (report.get("TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5")!=40
        or report.get("original_380_VALIDATION_ALTERNATIVE_xG5_preserved")!=107
        or report.get("GATE14")!="PENDING"):
        raise M1RRecomputeError("FPL74_V2_XG_SOURCE_REPORT_CHANGED")
    p=root/XG_MATRIX
    compressed=p.read_bytes()
    if hashlib.sha256(compressed).hexdigest()!=report["matrix_gzip_sha256"]:
        raise M1RRecomputeError("ORIGINAL_ALTERNATIVE_XG_BLOB_CHANGED")
    with gzip.open(p,"rt",encoding="utf8") as stream:
        old=[json.loads(s) for s in stream if s.strip()]
    idx={r["fixture_id"]:r for r in old}
    if len(idx)!=1140 or len(old)!=1140 or len(rows)!=1140:
        raise M1RRecomputeError("ALTER_SOURCE_1140_JOIN_NOT_BIJECTIVE")
    count=Counter()
    for r in rows:
        historic=idx.get(r["fixture_id"])
        if (historic is None or historic["partition"]!=r["partition"] or
            historic["kickoff_utc"]!=r["kickoff_utc"]):
            raise M1RRecomputeError("ALTERNATIVE_XG_NATIVE_ID_TIME_DRIFT")
        source=historic["history_public_asof_source"]
        if (not source.get("witness_utc") or
            not source["status"].startswith("PINNED")):
            continue
        if _utc(source["witness_utc"])>=_utc(r["kickoff_utc"]):
            raise M1RRecomputeError("ALTERNATIVE_XG_SOURCE_NOT_PREMATCH")
        provider=("FPL_OPTA_PLAYER_XG" if r["partition"]=="TRAIN" else "FPL_CORE_ALTERNATIVE_XG")
        v=historic["public_source_research_121_numeric_features"]
        f=historic["public_source_research_38_missing_flags"]
        # Preserve partial history, but the prior source might have used
        # <48h preceding games. Do NOT assume 48h compatible without an
        # independent per-predecessor check. Separate research only.
        partial={}
        for side in ("home","away"):
            stem=f"{side}_all_5"
            n=v.get(stem+"_xg_n")
            na=v.get(stem+"_xga_n")
            avg=v.get(stem+"_xg_avg");aga=v.get(stem+"_xga_avg")
            if (type(n) is int and type(na) is int and
                3<=n<=5 and 3<=na<=5 and _finite(avg) and _finite(aga)):
                partial[side]={"xg_n":n,"xga_n":na,
                                "xg_avg":avg,"xga_avg":aga}
        if not partial:continue
        r["xg_old_source_separate_overlay"]={
          "source":provider,"source_SHA":source["sha"],
          "source_witness_utc":source["witness_utc"],
          "valid_xg_sides":partial,
          "NOT_48h_predecessor_compatibility_certified":True,
          "NOT_original_PitchAPI_xG":True,
          "prohibited_in_BASE_fit":True}
        count["targets_with_at_least_one_optional_xg3_"+r["partition"]]+=1
        if len(partial)==2:
            count["targets_with_both_optional_xg3_"+r["partition"]]+=1
        if len(partial)==2 and all(x["xg_n"]==5 and x["xga_n"]==5 for x in partial.values()):
            count["targets_with_both_full_xg5_"+r["partition"]]+=1
    return dict(count)

def run(root=ROOT,*,native_override=None,expected=1140):
    root=Path(root)
    safe=_valid_safe(root)
    if native_override is None:
        native,calls=native_three_seasons(key=os.environ.get("PITCHAPI_API_KEY",""))
    else:native=native_override;calls=0
    events,seasoncounts,stable=validated_events(
        {f"{int(season[:4])}/{int(season[:4])+1}":games for season,games in native.items()},safe)
    result=recompute(events,minimum_previous=3,expected=expected)
    overlay=xg_overlay(root,result) if expected==1140 else {}
    byrole=Counter(x["partition"] for x in result)
    allowed=Counter(x["partition"] for x in result if x["m1r_base_eligible"])
    per_season=Counter(x["season"] for x in result if x["m1r_base_eligible"])
    cold={k:byrole[k]-allowed[k] for k in ("TRAIN","VALIDATION")}
    if expected==1140 and (byrole!={"TRAIN":760,"VALIDATION":380} or
        len({x["fixture_id"] for x in result})!=1140):
        raise M1RRecomputeError("FROZEN_760_380_SCOPE_CHANGED")
    report={"schema":SCHEMA,
      "status":"RESEARCH_FEATURE_RECONSTRUCTION_ONLY",
      "recomputed_original_fixture_rows":len(result),
      "original_760_TRAIN_380_VALIDATION_counts":dict(byrole),
      "season_counts":seasoncounts,
      "stable_native_ids_crossseasons":stable,
      "real_PitchAPI_API_calls":calls,
      "historical_predecessor_score_lag_hours":48,
      "minimum_predecessor_matches_per_team":3,
      "m1r_BASE_eligible_by_partition":dict(allowed),
      "m1r_BASE_cold_start_by_partition":cold,
      "m1r_BASE_eligible_by_season":dict(per_season),
      "m1r_BASE_is_Elo_FORM_without_xG":True,
      "partial_FORM5_10_15_and_missingness_preserved":True,
      "historic_121_features_and_38_missing_flags_per_match":True,
      "xg_from_previous_old_FPL74_v2_separate_overlay":overlay,
      "xg_same_provider_and_48h_coherence_not_automatically_certified":True,
      "no_target_scores_in_research_matrix":True,
      "all_predecessors_only_before_target_by_at_least_48h":True,
      "current_historical_sources_not_claimed_as_historic_PIT":True,
      "no_training_or_validation_fit":True,
      "original_CatBoost_M1_trained":False,
      "original_M1_Gate14":"PENDING",
      "M1_R_research_data_readiness_only":True,
      "original_2026_27_TEST_examined":False,
      "original_model_split_weights_predictions_modified":False}
    return report,result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",required=True)
    p.add_argument("--matrix",required=True)
    args=p.parse_args()
    out=Path(args.summary);gz=Path(args.matrix)
    if out.exists() or gz.exists():raise M1RRecomputeError("APPEND_ONLY_NO_OVERWRITE")
    report,rows=run()
    out.parent.mkdir(parents=True,exist_ok=True);gz.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(gz,"wt",encoding="utf8",compresslevel=7) as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n")
    report["matrix_gzip_sha256"]=hashlib.sha256(gz.read_bytes()).hexdigest()
    report["matrix_rows"]=len(rows)
    out.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"recomputed":len(rows),
      "TRAIN_BASE_eligible":report["m1r_BASE_eligible_by_partition"].get("TRAIN",0),
      "VALIDATION_BASE_eligible":report["m1r_BASE_eligible_by_partition"].get("VALIDATION",0),
      "TRAIN_cold":report["m1r_BASE_cold_start_by_partition"]["TRAIN"],
      "VALIDATION_cold":report["m1r_BASE_cold_start_by_partition"]["VALIDATION"],
      "original_GATE14":"PENDING"},sort_keys=True))
if __name__=="__main__":main()
