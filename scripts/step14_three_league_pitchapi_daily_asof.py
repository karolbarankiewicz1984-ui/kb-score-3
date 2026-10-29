"""Daily prospective as-observed source capture for 3 independently audited leagues.

No forecast fit/settlement/calibration. 4 next matches/league, prior 15 games
per team across 2025/26+2026/27; retrieve up to 6 previously UNSAMPLED
finished predecessors per league/day (shots + stats) with true UTC/hash chain.
Entire raw response RSA AES-GCM sealed in GitHub private repo. The public
non-identifying receipt contains match ID SHA256 only; it never claims 121+38
M0 features or PitchAPI original historic first published_at are verified.
"""
from __future__ import annotations
import argparse,hashlib,json,os,time,shutil
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.pitchapi_step06_audit import to_plain
from scripts.step14_three_league_pitchapi_actual_audit import (
    CURRENT,PREVIOUS,LEAGUES,ThreeLeagueError,select_three,coverage)
from src.kb3_pitch_native import check_season
from src.kb3_step14_pitchapi_xg_semantics import (
    parse_native_shots,parse_native_team_stats,SemanticAuditError)
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_pit_ledger import as_utc,utc_now

ROOT=Path(__file__).resolve().parents[1]
MAX_PRIORS_PER_LEAGUE=6
MAX_CALLS=7+2*3*MAX_PRIORS_PER_LEAGUE  # 43
SCHEMA="kb3-pitchapi-three-league-prospective-daily-incremental-shot-stats-v1"
class DailyLeagueError(ThreeLeagueError):pass

def opaque_hash(country,match_id):
    return hashlib.sha256((country+"|"+match_id).encode("ascii")).hexdigest()

def already_sampled(base):
    seen=set()
    for path in sorted(Path(base).glob("*/THREE_LEAGUE_DAILY_RECEIPT.json")):
        r=json.loads(path.read_text(encoding="utf8"))
        if r.get("schema")!=SCHEMA or r.get("source_payloads_RSA_sealed") is not True:
            raise DailyLeagueError("UNRECOGNIZED_PREVIOUS_OBSERVATION_RECEIPT")
        for match in r.get("sampled",[]):
            if match.get("state")=="SOURCE_STATS_XG_VERIFIED":
                seen.add((match["country"],match["native_match_id_sha256"]))
    return seen

def candidate_predecessors(current,old,now,seen,country):
    future=sorted([m for m in current if m["status"] in ("upcoming","not_started","scheduled")
                   and as_utc(m["time_utc"])>now],
                  key=lambda m:(m["time_utc"],m["id"]))[:4]
    if not future:raise DailyLeagueError("NO_FUTURE_TARGET_"+country)
    completed=[m for m in current+old if m["status"]=="finished"
        and as_utc(m["time_utc"])+timedelta(hours=3)<=now]
    wanted={}
    for target in future:
        for side in ("home_team","away_team"):
            tid=target[side]["id"]
            preceding=sorted((p for p in completed
                if p["id"]!=target["id"] and tid in
                (p["home_team"]["id"],p["away_team"]["id"])
                and as_utc(p["time_utc"])<as_utc(target["time_utc"])),
                key=lambda m:(m["time_utc"],m["id"]),reverse=True)[:15]
            for p in preceding:
                wanted[p["id"]]=p
    # Chronologically old-to-new gives a reproducible no-duplication backfill.
    candidates=sorted((m for m in wanted.values()
        if (country,opaque_hash(country,m["id"])) not in seen),
        key=lambda m:(m["time_utc"],m["id"]))
    return future,candidates[:MAX_PRIORS_PER_LEAGUE],len(wanted),len(candidates)

def capture(*,root,key,public_pem,client_factory=None,now=None,
            sleep_between_calls=0.15):
    if not isinstance(key,str) or not key.strip():
        raise DailyLeagueError("PITCHAPI_EXISTING_SECRET_MISSING")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory=PitchAPI
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise DailyLeagueError("UTC_REQUIRED")
    base=Path(root)
    day=now.date().isoformat();dest=base/day
    if dest.exists():raise DailyLeagueError("IMMUTABLE_UTC_DAY_ALREADY_SAVED")
    previous_seen=already_sampled(base)
    dest.mkdir(parents=True,exist_ok=False)
    try:
        client=client_factory(api_key=key)
        receipts=[];calls=0;failures=Counter()
        def call(resource,method,*args,**kwargs):
            nonlocal calls
            if calls>=MAX_CALLS:raise DailyLeagueError("MAX_43_REQUESTS_EXCEEDED")
            calls+=1
            if sleep_between_calls:time.sleep(sleep_between_calls)
            start=utc_now()
            try:r=to_plain(method(*args,**kwargs))
            except Exception as e:
                failures[type(e).__name__]+=1
                return None
            end=utc_now()
            if not isinstance(r,dict):failures["NON_OBJECT"]+=1;return None
            add_observation(receipts,resource=resource,payload=r,
                            started=start,completed=end)
            return r
        catalog=call("pitchapi:catalog",client.leagues.list)
        if catalog is None:raise DailyLeagueError("CURRENT_CATALOG_SOURCE_FAILED")
        chosen=select_three(catalog)
        leagues=[];sampled=[]
        for title,country,expected,lid in chosen:
            current=call("pitchapi:pilot_daily:"+country+":"+CURRENT,
                client.leagues.matches,lid,season=CURRENT,status="all")
            old=call("pitchapi:pilot_daily:"+country+":"+PREVIOUS,
                client.leagues.matches,lid,season=PREVIOUS)
            if current is None or old is None:raise DailyLeagueError("CURRENT_OR_PREV_LEAGUE_SOURCE_FAILED_"+country)
            c=current.get("matches");p=old.get("matches")
            summary,_=coverage(c,p,now,expected,title)
            futures,prior,needed,unseen=candidate_predecessors(c,p,now,previous_seen,country)
            summary["prior_unique_matches_needed_for_four_targets"]=needed
            summary["as_of_now_new_unsampled_prior_matches"]=unseen
            summary["new_prior_matches_selected_today"]=len(prior)
            summary["report_status"]="PROSPECTIVE_SOURCE_CAPTURE_ONLY_NOT_M0_MODEL"
            summary["original_provider_first_published_at"]=None
            leagues.append(summary)
            for m in prior:
                mid=m["id"];h=m["home_team"]["id"];a=m["away_team"]["id"]
                digest=opaque_hash(country,mid)
                shots=call("pitchapi:shots:"+mid,client.matches.shots,mid)
                stats=call("pitchapi:stats:"+mid,client.matches.stats,mid)
                state="NO_COMPLETE_SHOT_AND_STATS_SOURCE"
                if shots is not None and stats is not None:
                    try:
                        a_xg,b_xg,nsh,nsa=parse_native_shots(shots,mid,h,a)
                        s_h,s_a=parse_native_team_stats(stats,mid,h,a)
                        if not all(x>=0 for x in (a_xg,b_xg,s_h,s_a)):
                            raise SemanticAuditError("NEGATIVE_XG")
                        state="SOURCE_STATS_XG_VERIFIED"
                    except SemanticAuditError as e:
                        state="SCHEMA_REJECTED_"+str(e)[:50]
                sampled.append({"country":country,
                    "native_match_id_sha256":digest,
                    "state":state,
                    "original_first_published_at_utc":None,
                    "valid_for_2023_25_original_M1":False})
        if not receipts or not any(x["state"]=="SOURCE_STATS_XG_VERIFIED" for x in sampled):
            raise DailyLeagueError("NO_AUTHENTIC_FINISHED_XG_SOURCE_OBTAINED")
        sealed=seal(receipts,public_pem,
            dest/"THREE_LEAGUE_DAILY_SOURCE.enc",
            dest/"THREE_LEAGUE_DAILY_SOURCE.manifest.json")
        # Compute the 121+38 observed-before-kickoff features from these
        # same network receipts, then transactionally prepare append-only SQLite.
        from src.kb3_three_league_sqlite_forward_features import commit_sqlite
        ledger=Path("data/forward_m0/kb3_forward_m0.sqlite")
        staging=dest/"STAGING_FORWARD_M0.sqlite"
        if ledger.exists():shutil.copy2(ledger,staging)
        feature_audit=commit_sqlite(staging,receipts,cutoff_utc=utc_now(),
            raw_cipher_sha=sealed["ciphertext_sha256"],
            raw_chain_sha=sealed["proof"]["final_chain_sha256"])
        report={"schema":SCHEMA,
            "utc_day":day,"observation_start_utc":receipts[0]["started_at_utc"],
            "observation_end_utc":receipts[-1]["completed_at_utc"],
            "leagues":leagues,"sampled":sampled,
            "newly_verified_match_shot_stat_pairs":sum(
                x["state"]=="SOURCE_STATS_XG_VERIFIED" for x in sampled),
            "source_receipt_count":len(receipts),
            "source_payloads_RSA_sealed":True,
            "source_ciphertext_sha256":sealed["ciphertext_sha256"],
            "source_chain_sha256":sealed["proof"]["final_chain_sha256"],
            "previous_successful_source_shot_stats_count":len(previous_seen),
            "provider_calls":calls,"hard_api_calls_ceiling":MAX_CALLS,
            "failed_provider_request_count":sum(failures.values()),
            "any_results_or_xg_values_exported_in_plain_json":False,
            "this_is_not_121_plus_38_feature_matrix":True,
            "three_league_M0_predictions_started":False,
            "original_Premier_League_2026_27_TEST_not_accessed":True,
            "frozen_M0_feature_snapshots":feature_audit["frozen_feature_snapshots_today"],
            "M0_feature_fields":feature_audit["numeric_fields_per_snapshot"],
            "M0_missing_flags":feature_audit["missing_flags_per_snapshot"],
            "feature_sqlite_ledger_sha256":hashlib.sha256(staging.read_bytes()).hexdigest(),
            "M0_feature_snapshot_schema":feature_audit["schema"],
            "M0_features_observed_pre_kickoff_not_original_first_publication":True,
            "model_fit_or_calibration_performed":False,
            "original_pitchapi_published_at_2023_25_proven":False,
            "gate14_pass":False}
        (dest/"THREE_LEAGUE_DAILY_RECEIPT.json").write_text(
            json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n",
            encoding="utf8")
        ledger.parent.mkdir(parents=True,exist_ok=True)
        os.replace(staging,ledger)
        return report
    except BaseException:
        shutil.rmtree(dest,ignore_errors=True)
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",default="data/pit_sidecar/pitchapi_three_league_daily")
    p.add_argument("--public-key",
        default="config/step11_archive_recipient_public.pem")
    a=p.parse_args()
    now=datetime.now(timezone.utc)
    d=Path(a.base)/now.date().isoformat()
    if d.exists():
        print("THREE_LEAGUE_DAILY_CAPTURE_ALREADY_ARCHIVED",now.date().isoformat())
        return
    try:
        report=capture(root=a.base,key=os.environ.get("PITCHAPI_API_KEY",""),
            public_pem=a.public_key,now=now)
        print(json.dumps({"state":"THREE_LEAGUE_REAL_ASOF_SOURCE_ARCHIVED",
            "leagues":[{"league":x["league"],
                        "new_samples":x["new_prior_matches_selected_today"],
                        "needed":x["prior_unique_matches_needed_for_four_targets"]} for x in report["leagues"]],
            "verified_xg_pairs":report["newly_verified_match_shot_stat_pairs"],
            "calls":report["provider_calls"],"encrypted":True,
            "frozen_M0_feature_snapshots":report["frozen_M0_feature_snapshots"],
            "M0_not_yet_enabled":True,"gate14_pass":False},sort_keys=True))
    except Exception as e:
        print("THREE_LEAGUE_DAILY_SOURCE_BLOCKED",type(e).__name__,
              str(e) if isinstance(e,DailyLeagueError) else "OPAQUE")
        raise SystemExit(3)
if __name__=="__main__":main()
