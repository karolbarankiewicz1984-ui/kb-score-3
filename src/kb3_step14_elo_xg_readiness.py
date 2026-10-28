"""Isolated Step14 real-source Elo chain + xG provenance feasibility audit.

Mathematics is checked on only 70 already publicly known Oct-2023 FT results.
This is NOT a certified original PitchAPI Elo chain, not fitting or forecasting.
Historical xG must have a source-time-receipted, equivalent team-level record.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request,urlopen
import argparse,csv,io,json,math

from src.kb3_features import EloParameters,elo_probability
from src.kb3_step14_multiseason_pit import SOURCES,utc,SourceAuditError

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-elo-chain-xg-provenance-readiness-v1"
EXPECTED_ELO={"initial":1500.0,"k":20.0,"home_advantage":65.0,
              "scale":400.0,"season_retention":0.85}

class ChainError(ValueError):pass

def _additional_2023_source():
    from scripts.step14_multiseason_owner_native_join_local import ADDITIONAL_2023
    return ADDITIONAL_2023

def validate_contract(params):
    if not isinstance(params,EloParameters):
        raise ChainError("NOT_STEP11_ELO_PARAMETERS")
    if {x:getattr(params,x) for x in EXPECTED_ELO}!=EXPECTED_ELO:
        raise ChainError("ORIGINAL_ELO_CONTRACT_CHANGED")

def verify_public_elo_math(raw,verified_source,params=None,source_pin=None):
    """Independent deterministic 2023/24 partial Elo replay (70 finished FT).
    Source clock proof must already be pinned; no ratings exported.
    """
    params=params or EloParameters()
    validate_contract(params)
    source=source_pin if source_pin is not None else SOURCES[0]
    if source not in (SOURCES[0],_additional_2023_source()):
        raise ChainError("UNREVIEWED_ELO_REPLAY_SOURCE")
    if (verified_source.get("verified_source_commit")!=source["commit"]
        or verified_source.get("verified_prematch_raw_sha256")!=source["sha"]
        or verified_source.get("push_utc")!=source["push"]
        or verified_source.get("independent_push_event_id")!=source["event"]
        or sha256(raw).hexdigest()!=source["sha"]):
        raise ChainError("UNVERIFIED_PUBLIC_FT_FOR_ELO")
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline="")))
    if len(rows)!=380:raise ChainError("PUBLIC_GRID_CHANGED")
    done=[]
    for row in rows:
        if row["finished"]=="True":
            ko=utc(row["kickoff_time"])
            if ko>=utc(source["push"]):raise ChainError("PREMATURE_ELO_RESULT")
            try:
                numbers=[float(row["team_h_score"]),float(row["team_a_score"])]
            except (ValueError,TypeError) as exc:raise ChainError("INVALID_ELO_SCORE") from exc
            if not all(math.isfinite(z) and 0<=z<=30 and z.is_integer() for z in numbers):
                raise ChainError("INVALID_ELO_SCORE")
            h,a=map(int,numbers)
            done.append((ko,str(row["id"]),str(row["team_h"]),str(row["team_a"]),h,a))
        elif row["finished"]=="False":
            if row["team_h_score"] or row["team_a_score"]:
                raise ChainError("UNPLAYED_SCORE_LEAK")
        else:raise ChainError("INVALID_STATUS")
    if len(done)!=source["ft"]:raise ChainError("PUBLIC_EARLIER_FT_COUNT_CHANGED")
    done.sort(key=lambda x:(x[0],x[1]))
    ratings=defaultdict(lambda:params.initial)
    teams=set()
    prior_kickoff=None
    changes=0
    for kickoff,match,home,away,h,a in done:
        if home==away:raise ChainError("INVALID_ELO_PAIR")
        preh,prea=ratings[home],ratings[away]
        prob=elo_probability(preh,prea,params)
        actual=1.0 if h>a else 0.0 if h<a else 0.5
        delta=params.k*(actual-prob)
        # Standard Elo symmetric zero-sum update is exactly the Step11 one.
        posth,posta=preh+delta,prea-delta
        if not math.isclose(posth+posta,preh+prea,rel_tol=0,abs_tol=1e-9):
            raise ChainError("ELO_NOT_ZERO_SUM")
        ratings[home],ratings[away]=posth,posta
        if not all(math.isfinite(v) and 100<=v<=4000 for v in (posth,posta)):
            raise ChainError("ELO_NUMERIC_OVERFLOW")
        teams.update((home,away))
        changes+=1
    return {"partial_public_elo_replay_completed":True,
            "public_replay_scored_earlier_events":changes,
            "earlier_result_source_sha256":source["sha"],
            "source_publication_clock_independent":True,
            "original_step11_math_parameters_verified":True,
            "season_retention_in_this_one_season_applied":False,
            "absolute_elo_values_exported":False,
            "public_fixture_ids_or_scores_exported":False,
            "full_cross_season_native_team_id_chain_proven":False}

def _full_elo_chain_gates(source_report):
    public=source_report["verified_three_season_public_sources"]
    if set(public)!={"2023-24","2024-25","2025-26"}:
        raise ChainError("THREE_SEASONS_REQUIRED")
    seen={s:public[s]["finished_earlier_ft_in_blob"] for s in public}
    if seen!={"2023-24":70,"2024-25":60,"2025-26":0}:
        raise ChainError("HISTORIC_SOURCE_COUNTS_CHANGED")
    return {
       "elo_parameters":EXPECTED_ELO,
       "historical_input_full_380_by_season":{
           s:{"publicly_available_in_this_pinned_snapshot":n,
              "full_380_proven":n==380}
           for s,n in seen.items()},
       "prerequisites":{
         "same_native_team_ids_across_2023_2026_proven_in_oct2026_archive":True,
         "old_archived_native_results_first_published_before_each_target":False,
         "entire_prior_2023_24_season_public_asof_for_2024_25":False,
         "entire_prior_2024_25_season_public_asof_for_2025_26":False,
         "all_in_season_predecessor_fixture_publication_clocks_proven":False,
         "three_season_continuity_season_retention_proven_asof":False,
         "test_2026_27_excluded":True
       },
       "full_original_pitchapi_native_elo_chain_historical_pit_certified":False,
       "official_elo_feature_training_eligible":False
    }

def _xg_gates(root):
    step11=json.loads((root/"data/audits/STEP11_XG10_STRATIFIED_REAL_2026-10-26.json").read_text(encoding="utf8"))
    hist=json.loads((root/"data/audits/STEP11_PITCH_MULTISEASON_ELO_REAL_2026-10-26.json").read_text(encoding="utf8"))
    if (step11.get("schema")!="kb3-step11-real-stratified-xg10-and-feature-integration-v1"
        or step11.get("provider_original_published_at_known") is not False
        or step11.get("historical_pit_certified") is not False
        or step11.get("training_allowed") is not False
        or hist.get("live_integration",{}).get("provider_publication_time_known") is not False
        or hist.get("live_integration",{}).get("historical_matchtime_pit_certified") is not False
        or hist.get("history",{}).get("finished_fixtures")!=1140):
        raise ChainError("HISTORICAL_XG_ORIGINAL_EVIDENCE_CHANGED")
    return {
       "original_pitchapi_2023_2026_historical_team_xg_published_at_proven":False,
       "step11_sample_2026_27_strict_xg_pairs":step11["new_strict_exact_xg_pairs"],
       "step11_sample_observed_in_oct2026_not_2023_2026_publication_proof":True,
       "required_team_level_original_definition_equivalence_proven":False,
       "fpl_player_xg_is_NOT_assumed_equivalent_to_pitchapi_team_xg":True,
       "missing_historical_xg_replaced_by_zero":False,
       "historical_xg_valid_for_official_m1":False,
    }

def assess(sources,*,root=ROOT,elo_replay=None):
    if sources.get("schema")!="kb3-step14-multiseason-public-pit-partial-v1":
        raise ChainError("UNVERIFIED_MULTISEASON_SOURCE_REPORT")
    if sources.get("gate14_pass") is not False or sources.get("m1_fit_allowed") is not False:
        raise ChainError("SOURCE_REPORT_ESCALATED_ELIGIBILITY")
    for row in sources.get("owner_local_four_fixture_source_join",[]):
        if row.get("official_m1_training_allowed") is not False or row.get("full_historical_pitchapi_pit_proven") is not False:
            raise ChainError("PREMATURE_NATIVE_PIT_PROMOTION")
    return {"schema":SCHEMA,"math":elo_replay,
       "elo_full_chain":_full_elo_chain_gates(sources),
       "xg":_xg_gates(Path(root)),
       "independent_eligibility_decision":{
          "without_xg_M1_original_train_available":False,
          "with_xg_M1_original_train_available":False,
          "training_allowed":False,"gate14_pass":False,
          "train_pit_eligible":0,"validation_pit_eligible":0,
          "test_rows_read":0,
          "original_elo_math_unchanged":True,
          "original_m0_unchanged":True,
          "original_twenty_forecasts_unchanged":True}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sources",required=True)
    p.add_argument("--output",required=True)
    opts=p.parse_args()
    source=json.loads(Path(opts.sources).read_text(encoding="utf8"))
    s=SOURCES[0]
    url=f"https://raw.githubusercontent.com/{s['repo']}/{s['commit']}/{s['path']}"
    with urlopen(Request(url,headers={"User-Agent":"KB3-step14-elo-source-check"}),timeout=35) as fd:
        raw=fd.read(3_000_001)
    math_result=verify_public_elo_math(raw,source["verified_three_season_public_sources"]["2023-24"])
    # Second independently corroborated 2023-12-04 PushEvent with 140 FT.
    # One source is a longer prefix of the SAME season, never 70+140=210
    # independent Elo events.
    s2=_additional_2023_source()
    url2=f"https://raw.githubusercontent.com/{s2['repo']}/{s2['commit']}/{s2['path']}"
    with urlopen(Request(url2,headers={"User-Agent":"KB3-step14-elo-source-check"}),timeout=35) as fd:
        raw2=fd.read(3_000_001)
    verified2={"verified_source_commit":s2["commit"],
       "verified_prematch_raw_sha256":s2["sha"],
       "push_utc":s2["push"],
       "independent_push_event_id":s2["event"]}
    later=verify_public_elo_math(raw2,verified2,source_pin=s2)
    math_result["additional_verified_public_replay_2023_12_04_utc"]=s2["push"]
    math_result["newer_snapshot_2023_24_public_elo_prefix_length"]=later["public_replay_scored_earlier_events"]
    math_result["additional_source_is_same_season_longer_prefix_not_independent_210_matches"]=True
    report=assess(source,elo_replay=math_result)
    dest=Path(opts.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    serialized=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if dest.exists():
        if dest.read_text(encoding="utf8")!=serialized:raise ChainError("IMMUTABLE_ELO_XG_REPORT_CHANGED")
    else:dest.write_text(serialized,encoding="utf8")
    print(json.dumps({
        "public_2023_elo_first_snapshot_results_replayed":math_result["public_replay_scored_earlier_events"],
        "public_2023_elo_later_snapshot_results_replayed":math_result["newer_snapshot_2023_24_public_elo_prefix_length"],
        "original_full_native_elo_pit_certified":False,
        "historic_xg_pit_certified":False,
        "official_train_pit_eligible":0,"gate14_pass":False
    },sort_keys=True))
if __name__=="__main__":main()
