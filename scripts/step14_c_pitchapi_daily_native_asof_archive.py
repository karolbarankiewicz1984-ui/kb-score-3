"""C: daily authentic PitchAPI native as-observed pre-match evidence.

Scheduled runner uses EXISTING PITCHAPI_API_KEY and repo's PUBLIC RSA PEM,
NO owner action or private key. Store current league fixture snapshot plus
at most TWO earlier completed match shots+stats, with source payload hashes,
actual start/completion UTC and encrypted immutable originals in private repo.
This does NOT invent an original provider first-published clock, or any
2023-25 historical PIT. Future targets never have outcome fields exported.
"""
from __future__ import annotations
import argparse,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_pit_ledger import utc_now,as_utc
from src.kb3_pitch_native import check_season
from src.kb3_step14_pitchapi_xg_semantics import parse_native_shots,parse_native_team_stats
from scripts.pitchapi_step06_audit import norm,to_plain

ROOT=Path(__file__).resolve().parents[1]
SEASON="2026/2027"
BUDGET=6 # catalogue + fixtures + 2*(shots + stats)
MAX_PRIOR=2
MAX_TARGETS=4
SCHEMA="kb3-step14-C-prospective-PitchAPI-real-as-observed-receipt-v1"
class CaptureError(ValueError):pass

def select_targets_and_predecessors(matches,now):
    """Only genuine future fixture IDs as targets, genuine finished as prior."""
    if not isinstance(matches,list):raise CaptureError("NATIVE_MATCHES_NOT_LIST")
    candidates=[];past=[]
    for m in matches:
        if not isinstance(m,dict):raise CaptureError("NATIVE_ROW_NOT_OBJECT")
        ko=as_utc(m["time_utc"])
        home=m["home_team"]["id"];away=m["away_team"]["id"]
        if home==away:raise CaptureError("NATIVE_SAME_TEAM")
        if m["status"] in ("upcoming","not_started","scheduled"):
            if ko>now:
                if m.get("score_home") is not None or m.get("score_away") is not None:
                    raise CaptureError("FUTURE_HAS_RESULT")
                candidates.append(m)
        elif m["status"]=="finished" and ko+timedelta(hours=3)<=now:
            past.append(m)
    targets=sorted(candidates,key=lambda m:(m["time_utc"],m["id"]))[:MAX_TARGETS]
    if not targets:
        return [],[]
    involved={m[x]["id"] for m in targets for x in ("home_team","away_team")}
    earlier=sorted((m for m in past if m["home_team"]["id"] in involved
                    or m["away_team"]["id"] in involved),
                   key=lambda m:(m["time_utc"],m["id"]),reverse=True)
    latest=[]
    for m in earlier:
        if m["id"] in {x["id"] for x in latest}:raise CaptureError("DUPLICATE_PRIOR")
        if not all(m["time_utc"]<t["time_utc"] for t in targets):
            # Only select predecessors chronologically before all targets.
            continue
        latest.append(m)
        if len(latest)>=MAX_PRIOR:break
    return targets,latest

def capture(*,dest,public_key,key,client_factory=None,now=None):
    if not isinstance(key,str) or not key.strip():raise CaptureError("CONFIGURED_PITCHAPI_KEY_MISSING")
    from pitchapi import PitchAPI
    if client_factory is None:client_factory=PitchAPI
    now=now or datetime.now(timezone.utc)
    if now.utcoffset()!=timedelta(0):raise CaptureError("UTC_REQUIRED")
    target=Path(dest)
    if target.exists():raise CaptureError("APPEND_ONLY_TARGET_EXISTS")
    target.mkdir(parents=True,exist_ok=False)
    import shutil
    try:
        cli=client_factory(api_key=key)
        receipts=[];calls=0
        def call(resource,fn,*args,**kwargs):
            nonlocal calls
            if calls>=BUDGET:raise CaptureError("PITCHAPI_DAILY_CALL_BUDGET_EXCEEDED")
            calls+=1
            start=utc_now()
            try:response=to_plain(fn(*args,**kwargs))
            except Exception:
                raise CaptureError("PITCHAPI_SDK_REQUEST_BLOCKED") from None
            end=utc_now()
            if not isinstance(response,dict):raise CaptureError("PITCHAPI_RESPONSE_NOT_OBJECT")
            add_observation(receipts,resource=resource,payload=response,
                started=start,completed=end)
            return response
        cat=call("pitchapi:catalog",cli.leagues.list)
        leagues=cat.get("leagues")
        if not isinstance(leagues,list):raise CaptureError("PITCH_CATALOG_NOT_LIST")
        selected=[x for x in leagues if norm(x.get("name")).replace(" ","")=="premierleague"
            and str(x.get("country_code","")).upper()=="ENG"
            and SEASON in (x.get("seasons") or [])]
        if len(selected)!=1:raise CaptureError("PREMIER_LEAGUE_2026_ID_NOT_UNIQUE")
        resp=call("pitchapi:live:premier-league:2026-27:all",
            cli.leagues.matches,selected[0]["id"],season=SEASON,status="all")
        matches=resp.get("matches")
        check_season(matches,SEASON,expected_count=380,require_upcoming=True)
        targets,prior=select_targets_and_predecessors(matches,now)
        if not targets:
            raise CaptureError("NO_FUTURE_TARGETS_IN_2026_27_SEASON")
        checked=[]
        for match in prior:
            mid=match["id"];home=match["home_team"]["id"];away=match["away_team"]["id"]
            shots=call("pitchapi:shots:"+mid,cli.matches.shots,mid)
            stats=call("pitchapi:stats:"+mid,cli.matches.stats,mid)
            xh,xa,sh,sa=parse_native_shots(shots,mid,home,away)
            h,a=parse_native_team_stats(stats,mid,home,away)
            checked.append({"shot_count":sh+sa,
                "PitchAPI_shots_and_fullmatch_stats_same_native_fixture_teams":True,
                "numeric_shot_sum_and_stats_available":True})
        if calls> BUDGET:raise CaptureError("OVER_BUDGET")
        enc=target/"KB3_PITCH_NATIVE_ASOF.enc"
        manifest=target/"KB3_PITCH_NATIVE_ASOF.manifest.json"
        seal_info=seal(receipts,public_key,enc,manifest)
        report={"schema":SCHEMA,"season":SEASON,
             "captured_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
             "real_network_observation_started_utc":receipts[0]["started_at_utc"],
             "real_network_observation_ended_utc":receipts[-1]["completed_at_utc"],
             "source_archive_chain_sha256":seal_info["proof"]["final_chain_sha256"],
             "ciphertext_sha256":seal_info["ciphertext_sha256"],
             "fixture_source_snapshot_sha256":receipts[1]["payload_sha256"],
             "future_target_schedules_in_sealed_original":len(targets),
             "finished_prior_match_shot_stats_pairs_observed":len(checked),
             "native_shot_stat_side_identity_checked":len(checked),
             "provider_call_count":calls,"provider_call_hard_ceiling":BUDGET,
             "target_results_written_as_public_values":False,
             "full_source_payloads_encrypted_with_existing_owner_PUBLIC_key":True,
             "owner_private_RSA_key_needed_in_Github":False,
             "provider_original_first_publication_known":False,
             "captured_asof_later_future_targets_only":True,
             "old_2023_2025_original_PIT_recovered":False,
             "real_train_M1_allowed":False,"gate14_pass":False}
        (target/"KB3_PITCH_NATIVE_ASOF_RECEIPT.json").write_text(
             json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
        return report
    except BaseException:
        shutil.rmtree(target,ignore_errors=True)
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",default="data/pit_sidecar/step14_pitchapi_native")
    p.add_argument("--public-key",default="config/step11_archive_recipient_public.pem")
    args=p.parse_args()
    key=os.environ.get("PITCHAPI_API_KEY","")
    today=datetime.now(timezone.utc).date().isoformat()
    dest=Path(args.base)/today
    if dest.exists():
        print("C_ALREADY_ARCHIVED_ON_THIS_UTC_DAY",today)
        return
    try:
        r=capture(dest=dest,public_key=args.public_key,key=key)
        print(json.dumps({"state":"REAL_NATIVE_PITCHAPI_ASOF_CAPTURE_SEALED",
            "utc_day":today,"future_targets":r["future_target_schedules_in_sealed_original"],
            "prior_shot_stats":r["finished_prior_match_shot_stats_pairs_observed"],
            "actual_api_calls":r["provider_call_count"],
            "ciphertext_SHA256":r["ciphertext_sha256"],
            "provider_original_first_publication_known":False,
            "gate14_pass":False},sort_keys=True))
    except Exception as e:
        print("C_NATIVE_PIT_CAPTURE_BLOCKED",type(e).__name__)
        raise SystemExit(3)
if __name__=="__main__":main()
