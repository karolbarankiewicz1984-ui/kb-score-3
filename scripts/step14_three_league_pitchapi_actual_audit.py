"""Real PitchAPI three-league prospective PIT source audit and safe first collector.

Three distinct 2026/27 leagues OUTSIDE the frozen Premier League TEST:
Spain LaLiga, Italy Serie A and Germany Bundesliga. All sources are actual
network-observed UTC responses, with 2025/26 predecessor seasons for form15.
No new keys, payments, odds, CatBoost fit, forecast, original GATE14 claims
or PL 2026/27 test results used in the pilot.

The compact JSON is a NON-IDENTIFYING coverage/eligibility audit. Native raw
catalogue, fixtures and sampled shot/team stats are only stored RSA-sealed.
"""
from __future__ import annotations
import argparse,json,os,shutil
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_pitch_native import check_season
from src.kb3_pit_ledger import as_utc,utc_now,hexdigest,canonical
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_step14_pitchapi_xg_semantics import parse_native_shots,parse_native_team_stats
from scripts.pitchapi_step06_audit import norm,to_plain

ROOT=Path(__file__).resolve().parents[1]
CURRENT="2026/2027"
PREVIOUS="2025/2026"
# Country+name form an exact, independently required composite identity.
LEAGUES=(
 ("ESP",("laliga","laligaeasports","laligaea","primera division"),380,"LaLiga"),
 ("ITA",("seriea",),380,"Serie A"),
 ("GER",("bundesliga",),306,"Bundesliga"),
)
LIMIT=13  # catalogue + 3 current + 3 previous + 3 shots + 3 stats
SCHEMA="kb3-step14-three-league-real-pitchapi-2026-27-feasibility-and-observed-sources-v1"
class ThreeLeagueError(ValueError):pass
def _norm(s):
    return "".join(c for c in norm(s or "") if c.isalnum())

def select_three(catalog):
    if not isinstance(catalog,dict) or not isinstance(catalog.get("leagues"),list):
        raise ThreeLeagueError("NO_VALID_PITCH_LEAGUE_CATALOG")
    out=[]
    for country,names,expected,title in LEAGUES:
        found=[x for x in catalog["leagues"]
            if isinstance(x,dict) and str(x.get("country_code","")).upper()==country
            and _norm(x.get("name")) in names
            and CURRENT in (x.get("seasons") or [])
            and PREVIOUS in (x.get("seasons") or [])]
        if len(found)!=1:
            raise ThreeLeagueError("LEAGUE_UNAVAILABLE_OR_AMBIGUOUS_"+country)
        if not isinstance(found[0].get("id"),str) or not found[0]["id"].startswith("l_"):
            raise ThreeLeagueError("LEAGUE_ID_INVALID_"+country)
        out.append((title,country,expected,found[0]["id"]))
    if len({x[3] for x in out})!=3:raise ThreeLeagueError("LEAGUE_DUPLICATE_ID")
    return out

def coverage(current,previous,now,expected,title):
    c=check_season(current,CURRENT,expected_count=expected,require_upcoming=True)
    p=check_season(previous,PREVIOUS,expected_count=expected)
    if any(x.get("status")!="finished" for x in previous):
        raise ThreeLeagueError("PREVIOUS_SEASON_NOT_SETTLED_"+title)
    if len({m["id"] for m in current+previous})!=2*expected:
        raise ThreeLeagueError("MATCH_ID_CROSS_SEASON_DUPLICATE_"+title)
    future=sorted([m for m in current if m["status"] in ("upcoming","not_started","scheduled")
                    and as_utc(m["time_utc"])>now],key=lambda x:(x["time_utc"],x["id"]))
    if not future:raise ThreeLeagueError("NO_PROSPECTIVE_TARGET_"+title)
    targets=future[:4]
    past=sorted([m for m in current+previous if m["status"]=="finished"
                  and as_utc(m["time_utc"])+timedelta(hours=3)<=now],
                key=lambda x:(x["time_utc"],x["id"]))
    if not past:raise ThreeLeagueError("NO_FINISHED_PREDECESSOR_"+title)
    ids={m["id"] for m in targets}
    per_target=[];eligible=[]
    for target in targets:
        ko=as_utc(target["time_utc"])
        home=target["home_team"]["id"];away=target["away_team"]["id"]
        previous_by_side=[]
        for tid in (home,away):
            previous_by_side.append([m for m in past if m["id"] not in ids
                and tid in (m["home_team"]["id"],m["away_team"]["id"])
                and as_utc(m["time_utc"])<ko])
        per_target.append([min(15,len(v)) for v in previous_by_side])
        eligible.extend([m for h in previous_by_side for m in h])
    # One actual representative match per league for testing both API stats.
    unique={m["id"]:m for m in eligible}
    if not unique:raise ThreeLeagueError("NO_RELEVANT_COMPLETED_PREDECESSOR_"+title)
    sample=max(unique.values(),key=lambda m:(m["time_utc"],m["id"]))
    short=[n for counts in per_target for n in counts]
    return {"league":title,
            "season":CURRENT,"previous_season":PREVIOUS,
            "fixtures_this_season":c["fixtures"],
            "finished_this_season":c["status_counts"].get("finished",0),
            "future_fixtures_remaining":len(future),
            "previous_season_finished_fixtures":p["status_counts"].get("finished",0),
            "different_team_ids_this_season":c["unique_team_ids"],
            "next_four_upcoming_test_targets":len(targets),
            "target_team_sides_with_prior_5_of_5":sum(n>=5 for n in short),
            "target_team_sides_with_prior_10_of_10":sum(n>=10 for n in short),
            "target_team_sides_with_prior_15_of_15":sum(n>=15 for n in short),
            "target_team_sides_considered":len(short),
            "prior_match_count_min_capped_at15":min(short),
            "prior_match_count_max_capped_at15":max(short),
            "future_scores_are_not_pre_match_features":True,
            "provider_original_published_at":None},sample

def analyze(catalog,season_payloads,now):
    selected=select_three(catalog)
    summary=[];samples=[]
    for title,country,expected,lid in selected:
        k=(country,CURRENT);old=(country,PREVIOUS)
        if k not in season_payloads or old not in season_payloads:
            raise ThreeLeagueError("MISSING_REQUIRED_SEASON_"+country)
        s,sample=coverage(season_payloads[k],season_payloads[old],now,expected,title)
        summary.append(s);samples.append((title,sample))
    return summary,samples,selected

def collect(*,dest,key,public_pem,client_factory=None,now=None):
    if not isinstance(key,str) or not key.strip():
        raise ThreeLeagueError("EXISTING_PITCHAPI_SECRET_MISSING")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):
        raise ThreeLeagueError("AUDIT_CLOCK_MUST_BE_UTC")
    target=Path(dest)
    if target.exists():raise ThreeLeagueError("IMMUTABLE_AUDIT_ALREADY_PRESENT")
    target.mkdir(parents=True,exist_ok=False)
    try:
        cli=client_factory(api_key=key)
        receipts=[];n=0
        def call(resource,method,*args,**kwargs):
            nonlocal n
            if n>=LIMIT:raise ThreeLeagueError("AUDIT_CALL_HARD_CAP_EXCEEDED")
            n+=1
            start=utc_now()
            try:payload=to_plain(method(*args,**kwargs))
            except Exception as e:
                raise ThreeLeagueError("PITCH_SDK_"+type(e).__name__) from None
            end=utc_now()
            if not isinstance(payload,dict):
                raise ThreeLeagueError("NON_JSON_PITCHAPI_RESPONSE")
            add_observation(receipts,resource=resource,payload=payload,
                            started=start,completed=end)
            return payload
        catalog=call("pitchapi:catalog",cli.leagues.list)
        chosen=select_three(catalog)
        season_payloads={}
        for title,country,expected,lid in chosen:
            for season in (CURRENT,PREVIOUS):
                response=call("pitchapi:pilot:"+country+":"+season,
                    cli.leagues.matches,lid,season=season,
                    **({"status":"all"} if season==CURRENT else {}))
                season_payloads[(country,season)]=response.get("matches")
        summaries,samples,_=analyze(catalog,season_payloads,now)
        for title,sample in samples:
            mid=sample["id"];home=sample["home_team"]["id"]
            away=sample["away_team"]["id"]
            shots=call("pitchapi:shots:"+mid,cli.matches.shots,mid)
            stats=call("pitchapi:stats:"+mid,cli.matches.stats,mid)
            a,b,nh,na=parse_native_shots(shots,mid,home,away)
            sh,sa=parse_native_team_stats(stats,mid,home,away)
            for row in summaries:
                if row["league"]==title:
                    row["real_completed_prior_match_shots_checked"]=nh+na
                    row["real_completed_prior_shots_xg_status"]="VALID_NATIVE_MATCH_TEAM_XG"
                    row["real_completed_prior_fullmatch_stats_xg_status"]="VALID_NATIVE_MATCH_TEAM_XG"
                    row["shot_xg_and_stats_xg_absolute_differences_are_not_exported"]=True
                    row["native_xg_both_sides_nonnegative"]=all(x>=0 for x in (a,b,sh,sa))
                    break
        if n!=LIMIT or len(receipts)!=LIMIT:
            raise ThreeLeagueError("NOT_ALL_THREE_LIVE_STATS_CHECKED")
        enc=target/"THREE_LEAGUE_ORIGINAL_PITCHAPI.enc"
        manifest=target/"THREE_LEAGUE_ORIGINAL_PITCHAPI.manifest.json"
        metadata=seal(receipts,public_pem,enc,manifest)
        report={"schema":SCHEMA,"real_observation_UTC":utc_now(),
            "observed_started_UTC":receipts[0]["started_at_utc"],
            "observed_completed_UTC":receipts[-1]["completed_at_utc"],
            "leagues":summaries,"all_three_catalogue_current_and_prior_season_match":True,
            "provider_calls":n,"api_call_ceiling":LIMIT,
            "original_data_is_RSA_AES_GCM_sealed":True,
            "source_receipt_chain_sha256":metadata["proof"]["final_chain_sha256"],
            "encrypted_source_sha256":metadata["ciphertext_sha256"],
            "read_only_audit_no_fixture_scores_or_xg_values_in_report":True,
            "prematch_feature_M0_ready":False,
            "daily_full_5_10_15_xg_history_collector_ready":False,
            "official_Premier_League_TEST_touched":False,
            "model_fit_or_calibration_performed":False,
            "original_2023_25_PitchAPI_published_at_proven":False,
            "original_Gate14_PIT_qualified":False,
            "no_new_paid_subscription":True}
        (target/"THREE_LEAGUE_AUDIT.json").write_text(
            json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf8")
        return report
    except BaseException:
        shutil.rmtree(target,ignore_errors=True)
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument("--base",
        default="data/pit_sidecar/pitchapi_three_league_audit")
    p.add_argument("--public-key",
        default="config/step11_archive_recipient_public.pem")
    args=p.parse_args()
    day=datetime.now(timezone.utc).date().isoformat()
    target=Path(args.base)/day
    if target.exists():
        print("THREE_LEAGUE_AUDIT_UTC_DAY_ALREADY_SAVED",day)
        return
    try:
        report=collect(dest=target,
            key=os.environ.get("PITCHAPI_API_KEY",""),
            public_pem=args.public_key)
        print(json.dumps({"state":"THREE_REAL_LEAGUES_SOURCE_AUDIT_COMPLETE",
            "league_coverages":[{"league":x["league"],
                                  "fixtures":x["fixtures_this_season"],
                                  "upcoming":x["future_fixtures_remaining"],
                                  "form15_ready_sides":x["target_team_sides_with_prior_15_of_15"],
                                  "side_count":x["target_team_sides_considered"],
                                  "xg_status":x["real_completed_prior_fullmatch_stats_xg_status"]}
                for x in report["leagues"]],
            "calls":report["provider_calls"],"encrypted":True,
            "training_allowed":False,"calibration_done":False},sort_keys=True))
    except Exception as e:
        print("THREE_LEAGUE_PITCHAPI_AUDIT_BLOCKED",type(e).__name__,
              str(e) if isinstance(e,ThreeLeagueError) else "OPAQUE")
        raise SystemExit(3)
if __name__=="__main__":main()
