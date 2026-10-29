"""Actual PitchAPI three-season 1140-event deterministic Elo REPLAY + source joins.

3h scoreboard availability lag is a SIMULATION over retrospectively retrieved
2026 native FT, NOT proof that old source was really published at that time.
No 2026/27 TEST, training, M1 modification, predictions or bookmaker data.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from heapq import heappop,heappush
import argparse,json,math,os
from pathlib import Path
from src.kb3_features import EloParameters,elo_probability
from src.kb3_step14_native_team_crosswalk import canonical_team_name
from src.kb3_pitch_native import check_season
from src.kb3_split import sha
from scripts.pitchapi_step06_audit import norm,to_plain
from scripts.step14_fpl_core_2025_independent_asof import _name,_utc

ROOT=Path(__file__).resolve().parents[1]
SAFE="data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
EXPANDED="data/audits/STEP14_2025_FPLCORE_EXPANDED_14_WITNESSED_VERSIONS_2026-10-29.json"
SCHEMA="kb3-step14-retrospective-native-three-season-1140-Elo-plus-witnessed-2025-crosswalk-v1"
SEASONS=(("2023/2024","2023-24","TRAIN",2023),
         ("2024/2025","2024-25","TRAIN",2024),
         ("2025/2026","2025-26","VALIDATION",2025))
LAG=timedelta(hours=3)
class EloReconstructionError(ValueError):pass

def _valid_safe(base=ROOT):
    original=json.loads((Path(base)/SAFE).read_text(encoding="utf8"))
    if (original.get("projection_sha256")!="3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7"
        or original.get("training_allowed") is not False
        or sha({k:v for k,v in original.items() if k!="projection_sha256"})!=original["projection_sha256"]):
        raise EloReconstructionError("UNTRUSTED_OR_CHANGED_SAFE_SPLIT")
    allowed={x["fixture_id"]:(x["kickoff_utc"],x["partition"])
             for x in original["fixtures"] if x["partition"] in ("TRAIN","VALIDATION")}
    if len(allowed)!=1140: raise EloReconstructionError("WRONG_TRAIN_VALIDATION_SCOPE")
    return allowed

def select_league(catalog):
    if not isinstance(catalog,dict) or not isinstance(catalog.get("leagues"),list):
        raise EloReconstructionError("MISSING_PITCH_CATALOG")
    found=[z for z in catalog["leagues"] if
        norm(z.get("name")).replace(" ","")=="premierleague"
        and str(z.get("country_code","")).upper()=="ENG"
        and all(s[0] in (z.get("seasons") or []) for s in SEASONS)]
    if len(found)!=1:raise EloReconstructionError("NO_SINGLE_ENGLISH_2023_TO_2026_LEAGUE")
    return found[0]["id"]

def validated_events(by_season,original):
    out=[]
    count={}
    sides={}
    all_ids=set()
    for slug,public,role,year in SEASONS:
        source=by_season[slug]
        checked=check_season(source,slug,expected_count=380)
        if any(x.get("status")!="finished" for x in source):
            raise EloReconstructionError("NOT_ALL_ORIGINAL_NATIVE_FT_FINAL_"+public)
        teams=set()
        for m in source:
            ident=m.get("id")
            if ident in all_ids or original.get(ident)!= (m.get("time_utc"),role):
                raise EloReconstructionError("NATIVE_1140_ID_OR_KICKOFF_OR_PARTITION_DRIFT")
            all_ids.add(ident)
            home,away=m["home_team"]["id"],m["away_team"]["id"]
            if home==away:raise EloReconstructionError("DUPLICATE_NATIVE_TEAM")
            teams.update((home,away))
            h,a=m.get("score_home"),m.get("score_away")
            if not(type(h) is int and type(a) is int and 0<=h<=30 and 0<=a<=30):
                raise EloReconstructionError("UNVERIFIED_OR_MISSING_SCORE")
            out.append({"fixture_id":ident,"season":public,"year":year,
                "partition":role,"home_id":home,"away_id":away,
                "home_name":_name(m["home_team"]["name"]),
                "away_name":_name(m["away_team"]["name"]),
                "kickoff":_utc(m["time_utc"]),"gh":h,"ga":a})
        if len(teams)!=20:raise EloReconstructionError("NOT_20_NATIVE_TEAMS_"+public)
        sides[public]=teams
        count[public]=len(source)
    if set(original)!=all_ids:raise EloReconstructionError("MISSING_FROZEN_1140_OR_EXTRA_FIXTURES")
    return out,count,{"2023_to_2024":len(sides["2023-24"]&sides["2024-25"]),
                      "2024_to_2025":len(sides["2024-25"]&sides["2025-26"])}

def _elo_fields_for(rec,ratings,lastyear,history,games,params):
    year=rec["year"]
    def rating(tid):
        # Use provisional model original lazy inter-season retention.
        if tid in lastyear and year<lastyear[tid]:raise EloReconstructionError("NONMONOTONIC_TEAM_YEAR")
        v=ratings.get(tid,params.initial)
        if tid in lastyear and year>lastyear[tid]:
            v=params.initial+(v-params.initial)*params.season_retention**(year-lastyear[tid])
            ratings[tid]=v
            lastyear[tid]=year
        elif tid not in lastyear:
            ratings[tid]=v
            lastyear[tid]=year
        return v
    home,away=rec["home_id"],rec["away_id"]
    h,a=rating(home),rating(away)
    values={"home_elo":round(h,5),"away_elo":round(a,5),
            "elo_home_minus_away":round(h-a,5)}
    for side,tid,wanted in (("home",home,True),("away",away,False)):
        prior=history[tid]
        values[side+"_elo_games_available"]=games[tid]
        values[side+"_prior_seasons_games_available"]=sum(x["year"]<year for x in prior)
        for scope in ("all","venue"):
            available=[x for x in prior if scope=="all" or x["home"]==wanted]
            for n in (5,10,15):
                group=available[-n:]
                values[f"{side}_{scope}_{n}_opponent_elo_avg"]=(
                    round(sum(x["opponent_elo"] for x in group)/len(group),6)
                    if group else None)
    if len(values)!=19:raise EloReconstructionError("NOT_19_ELO_FIELDS")
    return values

def replay(events,params=None):
    params=params or EloParameters()
    ratings={};lastyear={};history=defaultdict(list);games=defaultdict(int)
    pending=[];out=[];updates=Counter(); snapshots={}
    # Events arrive at kickoff. Only a match that ended at least 3h ago
    # can be counted in ANY later target's feature snapshot.
    def finish(m):
        h,a=m["home_id"],m["away_id"]
        rh=rating_for(h,m["year"])
        ra=rating_for(a,m["year"])
        prob=elo_probability(rh,ra,params)
        actual=1 if m["gh"]>m["ga"] else 0 if m["gh"]<m["ga"] else .5
        delta=params.k*(actual-prob)
        # Previous games cannot overlap for same team; apply symmetrically.
        ratings[h]=rh+delta; ratings[a]=ra-delta
        games[h]+=1;games[a]+=1
        history[h].append({"year":m["year"],"home":True,"opponent_elo":ra})
        history[a].append({"year":m["year"],"home":False,"opponent_elo":rh})
        updates[m["season"]]+=1
    def rating_for(tid,year):
        old=lastyear.get(tid)
        if old is not None and year<old:raise EloReconstructionError("REVERSE_YEAR")
        val=ratings.get(tid,params.initial)
        if old is None:
            lastyear[tid]=year
        elif old<year:
            val=params.initial+(val-params.initial)*params.season_retention**(year-old)
            ratings[tid]=val;lastyear[tid]=year
        return val
    ordered=sorted(events,key=lambda x:(x["kickoff"],x["fixture_id"]))
    by_time=defaultdict(list)
    for e in ordered:by_time[e["kickoff"]].append(e)
    for now,group in sorted(by_time.items()):
        while pending and pending[0][0]<=now:
            _,_,old=heappop(pending)
            finish(old)
        for rec in group:
            v=_elo_fields_for(rec,ratings,lastyear,history,games,params)
            # No target outcome, no target xG, no season-2026/27 TEST.
            out.append({"original_native_match_id":rec["fixture_id"],
                "original_partition":rec["partition"],"season":rec["season"],
                "kickoff_utc":rec["kickoff"].isoformat().replace("+00:00","Z"),
                "original_native_home_team_id":rec["home_id"],
                "original_native_away_team_id":rec["away_id"],
                "research_only_retrospective_19_Elo_field_values":v,
                "source_was_2026_retrospective_PitchAPI_FT_not_historic_receipt":True,
                "native_original_121_38_pit_certified":False})
        for rec in group:
            heappush(pending,(rec["kickoff"]+LAG,rec["fixture_id"],rec))
    while pending:
        _,_,old=heappop(pending);finish(old)
    if sum(updates.values())!=1140 or len(out)!=1140:
        raise EloReconstructionError("NOT_ALL_1140_ELO_UPDATES_AND_SNAPSHOTS")
    return out,dict(updates),dict(ratings),dict(games)

def validate_expansion(rows,root=ROOT):
    path=Path(root)/EXPANDED
    data=json.loads(path.read_text(encoding="utf8"))
    if (data.get("GATE14")!="PENDING"
        or not data.get("original_confirmed_18_preserved")
        or data.get("old_historic_GitHub_server_source_clocks_verified") is not True
        or data.get("full_native_121_38_M1_PIT_rows_certified")!=0):
        raise EloReconstructionError("UNTRUSTED_NEW_PUBLIC_HISTORIC_RECONSTRUCTION")
    bykey={(r["home_name"],r["away_name"],r["kickoff"].isoformat()):r
           for r in rows if r["season"]=="2025-26"}
    if len(bykey)!=380:raise EloReconstructionError("NATIVE_2025_SCHEDULE_NOT_UNIQUE")
    matched=[];unmatched=[]
    for target in data["targets"]:
        key=(_name(target["target_public_home"]),_name(target["target_public_away"]),
             _utc(target["target_kickoff_utc"]).isoformat())
        row=bykey.get(key)
        if row is None:
            unmatched.append({"public_pair":[key[0],key[1]],
                              "kickoff_utc":target["target_kickoff_utc"],
                              "reason":"NO_EXACT_NATIVE_PAIR_AND_KICKOFF"})
            continue
        if _utc(target["source_publication_witness_utc"])>=row["kickoff"]:
            raise EloReconstructionError("OLD_SOURCE_NOT_BEFORE_NATIVE_TARGET")
        matched.append({"native_fixture_id":row["fixture_id"],
            "native_home_team_id":row["home_id"],"native_away_team_id":row["away_id"],
            "native_kickoff_utc":target["target_kickoff_utc"],
            "source_SHA":target["evidence_source_commit"],
            "source_server_witness_utc":target["source_publication_witness_utc"],
            "original_native_159_PIT_eligible":False})
    if len(matched)+len(unmatched)!=len(data["targets"]):raise EloReconstructionError("SOME_PUBLIC_TARGETS_DROPPED")
    if len(matched)!=len({x["native_fixture_id"] for x in matched}):
        raise EloReconstructionError("PUBLIC_TO_NATIVE_DUPLICATE")
    return data,matched,unmatched

def run(*,api_key,provider_factory=None,root=ROOT):
    if not isinstance(api_key,str) or not api_key.strip():raise EloReconstructionError("PITCHAPI_KEY_MISSING")
    if provider_factory is None:
        from pitchapi import PitchAPI
        provider_factory=PitchAPI
    allowed=_valid_safe(root)
    provider=provider_factory(api_key=api_key)
    n=0
    def request(fn,*args,**kw):
        nonlocal n
        if n>=4:raise EloReconstructionError("PITCHAPI_CALL_BUDGET_EXCEEDED")
        n+=1
        try:return to_plain(fn(*args,**kw))
        except Exception:raise EloReconstructionError("PITCHAPI_REAL_SDK_REQUEST_FAILED") from None
    lid=select_league(request(provider.leagues.list))
    seasons={}
    for season,_,_,_ in SEASONS:
        payload=request(provider.leagues.matches,lid,season=season)
        seasons[season]=payload["matches"]
    events,counts,stable=validated_events(seasons,allowed)
    historic,updates,ratings,games=replay(events)
    observed,matched,unmatched=validate_expansion(events,root)
    keys={x["original_native_match_id"]:x for x in historic}
    for x in matched:
        if x["native_fixture_id"] not in keys:raise EloReconstructionError("VALIDATION_ELO_ROW_MISSING")
    param=EloParameters()
    return {"schema":SCHEMA,"status":"RESEARCH_FULL_RETROSPECTIVE_REPLAY",
      "real_pitchapi_API_calls":n,"real_2023_24_2024_25_2025_26_fixtures":counts,
      "elo_match_updates":updates,"native_team_ids_stable_adjacent_seasons":stable,
      "elo_parameters":{"initial":param.initial,"k":param.k,"scale":param.scale,
                        "home_advantage":param.home_advantage,
                        "season_retention":param.season_retention},
      "simulated_result_lag_hours":3,
      "original_native_1140_full_chronological_Elo_replay_rows":len(historic),
      "original_native_2025_26_validation_Elo_replay_rows":sum(x["original_partition"]=="VALIDATION" for x in historic),
      "full_3_season_Elo_is_retrospective_2026_native_data":True,
      "historic_source_first_published_receipts_per_match_NOT_proven":True,
      "historically_witnessed_public_new_FORM5_total":observed["total_distinct_prematch_public_FORM5_targets"],
      "historically_witnessed_public_new_FORM5_beyond_previous_18":observed["new_unique_targets_beyond_original_18"],
      "witnessed_public_fixture_exact_native_2025_joins":len(matched),
      "witnessed_public_without_exact_native_pair":[] if not unmatched else unmatched,
      "strict_new_public_native_crosswalk":matched,
      "research_elo_feature_rows":historic,
      "no_test_2026_27_examined":True,
      "no_original_M1_fitted":True,
      "original_159_full_feature_PIT_validation_rows_certified":0,
      "original_159_full_feature_PIT_train_rows_certified":0,
      "GATE14":"PENDING"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    dest=Path(args.out)
    if dest.exists():raise EloReconstructionError("NO_OVERWRITE")
    report=run(api_key=os.environ.get("PITCHAPI_API_KEY",""))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({"native_full_retro_Elo":report["original_native_1140_full_chronological_Elo_replay_rows"],
                       "2025_26_public_targets":report["historically_witnessed_public_new_FORM5_total"],
                       "new_beyond_18":report["historically_witnessed_public_new_FORM5_beyond_previous_18"],
                       "exact_native_joins":report["witnessed_public_fixture_exact_native_2025_joins"],
                       "not_matched":len(report["witnessed_public_without_exact_native_pair"]),
                       "GATE14":"PENDING"},sort_keys=True))

if __name__=="__main__":
    main()
