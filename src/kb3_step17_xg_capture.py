"""Step17 separate eight-league *real* native PitchAPI xG research intake.

One previous match per league/run, each with authentic team stats xG and shot
sum side identity. Original raw is AES-GCM/RSA sealed; SQLite is append-only.
Never trains or claims a CatBoost with xG from sparse/retrospective evidence.
The 2026/27 English Premier League protected TEST is never requested.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib,json,math,os,shutil,sqlite3
from scripts.pitchapi_step06_audit import to_plain
from scripts.step14_three_league_pitchapi_actual_audit import PREVIOUS,CURRENT
from src.kb3_step16_m0_720_eight_forward import (
    ROOT,EIGHT,select_eight,validate_season,stamp,hashobj,require,LEAD)
from src.kb3_pit_ledger import utc_now,as_utc
from src.kb3_pitch_uefa_evidence import add_observation,seal
from src.kb3_step14_pitchapi_xg_semantics import (
    parse_native_shots,parse_native_team_stats,SemanticAuditError)
from src.kb3_pitch_source_pair import validate_pair,validate_receipts

DB=ROOT/"data/forward_step17_xg_eight/observed_xg.sqlite"
ARCHIVE=ROOT/"data/pit_sidecar/step17_native_xg_eight"
CATBOOST_XG_STATUS="NO_TRAINED_XG_CATBOOST_NOT_PRODUCTION"
# 2026-11-01 source-quality note: retain strict exact-last5, original
# provider receipts, immutable database and unchanged 33-call cap;
# experimental priority selection is isolated in draft PR #125.
MAX_PAIRS_PER_LEAGUE=1
MAX_CALLS=1+8*2+8*2  # 33; 17 fixture/catalog + 16 shots/stats
MAX_SEMANTIC_ABS_DELTA=0.15  # max mismatch shots sum vs All-team expected_goals
CANDIDATE_HOURS=96
XG_SCHEMA="""
CREATE TABLE IF NOT EXISTS observed_native_xg(
 country TEXT NOT NULL CHECK(country IN ('ESP','ITA','GER','FRA','NED','BEL','TUR','POL')),
 provider_match_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL,
 home_team_id TEXT NOT NULL,away_team_id TEXT NOT NULL,
 stats_xg_home REAL NOT NULL CHECK(stats_xg_home BETWEEN 0 AND 30),
 stats_xg_away REAL NOT NULL CHECK(stats_xg_away BETWEEN 0 AND 30),
 shots_xg_home REAL NOT NULL CHECK(shots_xg_home BETWEEN 0 AND 30),
 shots_xg_away REAL NOT NULL CHECK(shots_xg_away BETWEEN 0 AND 30),
 shots_home INTEGER NOT NULL CHECK(shots_home>=0),
 shots_away INTEGER NOT NULL CHECK(shots_away>=0),
 observed_utc TEXT NOT NULL,
 source_shots_sha256 TEXT NOT NULL,source_stats_sha256 TEXT NOT NULL,
 source_chain_sha256 TEXT NOT NULL,
 source_published_at_utc TEXT,
 PRIMARY KEY(country,provider_match_id),
 CHECK(source_published_at_utc IS NULL),
 CHECK(julianday(observed_utc)>=julianday(kickoff_utc)+3.0/24.0)
);
CREATE TRIGGER IF NOT EXISTS xg_observations_no_update BEFORE UPDATE ON observed_native_xg
 BEGIN SELECT RAISE(ABORT,'STEP17_XG_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS xg_observations_no_delete BEFORE DELETE ON observed_native_xg
 BEGIN SELECT RAISE(ABORT,'STEP17_XG_IMMUTABLE'); END;
"""
def connect(path=DB):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    db.executescript(XG_SCHEMA)
    require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
            "XG_DB_CORRUPTION")
    return db

def fixture_groups(receipts):
    out={}
    for item in receipts:
        parts=item["resource"].split(":")
        if len(parts)==5 and parts[:3]==["pitchapi","step17xg","fixtures"]:
            key=(parts[3],parts[4])
            require(key not in out,"DUPLICATE_FIXTURES")
            out[key]=item
    require(len(out)==16,"REQUIRE_EXACT_EIGHT_SEASON_PAIRS")
    return out

def rank_sources(grouped,known,now):
    """Choose only latest finished exact-match priors for upcoming teams.

    No future result, no 2026/27 Premier League, no hidden xG imputation.
    """
    selected=[];all_fixtures={}
    for c,title,_ in EIGHT:
        previous=grouped[(c,PREVIOUS)]["payload"]["matches"]
        current=grouped[(c,CURRENT)]["payload"]["matches"]
        validate_season(previous,current=False)
        validate_season(current,current=True)
        require(not {m["id"] for m in previous}&{m["id"] for m in current},
                "NATIVE_XG_CROSS_SEASON_COLLISION")
        history=[m for m in previous+current
                 if m["status"]=="finished"
                 and as_utc(m["time_utc"])+timedelta(hours=3)<=now]
        target=sorted((m for m in current
            if m["status"] in ("scheduled","not_started","upcoming")
            and m.get("score_home") is None and m.get("score_away") is None
            and now+LEAD<as_utc(m["time_utc"])<=now+timedelta(hours=CANDIDATE_HOURS)),
            key=lambda m:(m["time_utc"],m["id"]))[:10]
        team_targets={m[side]["id"] for m in target for side in ("home_team","away_team")}
        relevant=sorted((m for m in history
            if (c,m["id"]) not in known
            and (m["home_team"]["id"] in team_targets or
                 m["away_team"]["id"] in team_targets)),
            key=lambda m:(m["time_utc"],m["id"]),reverse=True)
        selected.extend((c,m) for m in relevant[:MAX_PAIRS_PER_LEAGUE])
        all_fixtures[c]={"history":history,"future":target}
    require(len(selected)<=8,"XG_CANDIDATE_CAP_EXCEEDED")
    return selected,all_fixtures

def parse_pair(shots,stats,*,match,country,shot_receipt,stat_receipt):
    mid=match["id"];home=match["home_team"]["id"];away=match["away_team"]["id"]
    sh,sa,nh,na,h,a=validate_pair(shots,stats,mid,home,away)
    for kind,receipt in (("shots",shot_receipt),("stats",stat_receipt)):
        require(receipt.get("resource")=="pitchapi:step17xg:"+kind+":"+mid,
                "XG_RECEIPT_RESOURCE_MISMATCH")
    observed=validate_receipts(shots,stats,match,shot_receipt,stat_receipt)
    require(as_utc(match["time_utc"])+timedelta(hours=3)<=observed,
            "XG_NOT_PUBLISHED_AFTER_FINISH")
    return {"country":country,"provider_match_id":mid,
       "kickoff_utc":match["time_utc"],"home_team_id":home,"away_team_id":away,
       "stats_xg_home":h,"stats_xg_away":a,"shots_xg_home":sh,"shots_xg_away":sa,
       "shots_home":nh,"shots_away":na,"observed_utc":stamp(observed),
       "source_shots_sha256":shot_receipt["payload_sha256"],
       "source_stats_sha256":stat_receipt["payload_sha256"],
       "source_chain_sha256":stat_receipt["chain_sha256"],
       "source_published_at_utc":None,
       "_source_pair":{"shots":shots,"stats":stats,"match":match,
                       "shot_receipt":shot_receipt,"stat_receipt":stat_receipt}}

def store_samples(db_path,samples):
    with connect(db_path) as db:
        for s in samples:
            pair=s.get("_source_pair")
            require(isinstance(pair,dict),"XG_ORIGINAL_SOURCE_PAIR_REQUIRED")
            checked=parse_pair(country=s["country"],**pair)
            require({k:v for k,v in checked.items() if k!="_source_pair"}==
                    {k:v for k,v in s.items() if k!="_source_pair"},"XG_SAMPLE_SOURCE_DRIFT")
            db.execute("""INSERT INTO observed_native_xg(
               country,provider_match_id,kickoff_utc,home_team_id,away_team_id,
               stats_xg_home,stats_xg_away,shots_xg_home,shots_xg_away,
               shots_home,shots_away,observed_utc,source_shots_sha256,
               source_stats_sha256,source_chain_sha256,source_published_at_utc)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (s["country"],s["provider_match_id"],s["kickoff_utc"],
                s["home_team_id"],s["away_team_id"],s["stats_xg_home"],s["stats_xg_away"],
                s["shots_xg_home"],s["shots_xg_away"],s["shots_home"],s["shots_away"],
                s["observed_utc"],s["source_shots_sha256"],s["source_stats_sha256"],
                s["source_chain_sha256"],None))
        require(db.execute("PRAGMA foreign_key_check").fetchall()==[],"XG_DB_FK")
        total=db.execute("SELECT COUNT(*) FROM observed_native_xg").fetchone()[0]
        db.commit()
    return total

def future_xg_coverage(db_path,groups,at):
    """LAST FIVE actual predecessor matches each side, not last five *available*.

    Prevents optimistic omission of earlier matches with missing xG.
    """
    with connect(db_path) as db:
        obs={(r[0],r[1]):r for r in db.execute("""SELECT country,provider_match_id,
           home_team_id,away_team_id,stats_xg_home,stats_xg_away,observed_utc
           FROM observed_native_xg""")}
    result={};complete=0;total=0;missing_by_country=Counter()
    for c,part in groups.items():
        for m in part["future"]:
            total+=1
            cutoff=at
            missing=0
            sides={}
            for side,tid in (("home",m["home_team"]["id"]),("away",m["away_team"]["id"])):
                prior=sorted((p for p in part["history"]
                  if p["id"]!=m["id"] and tid in (p["home_team"]["id"],p["away_team"]["id"])
                  and as_utc(p["time_utc"])+timedelta(hours=3)<=cutoff
                  and as_utc(p["time_utc"])<as_utc(m["time_utc"])),
                  key=lambda p:(p["time_utc"],p["id"]),reverse=True)[:5]
                vals=[]
                for p in prior:
                    v=obs.get((c,p["id"]))
                    if not v or as_utc(v[6])>cutoff:continue
                    if tid==v[2]:vals.append((v[4],v[5]))
                    elif tid==v[3]:vals.append((v[5],v[4]))
                missing+=5-len(vals)
                sides[side]={"prior5_exists":len(prior)==5,
                    "actual_verified_xg_in_last5":len(vals),
                    "missing_last5":5-len(vals),
                    "mean_xg_for":sum(x[0] for x in vals)/5 if len(vals)==5 else None,
                    "mean_xg_against":sum(x[1] for x in vals)/5 if len(vals)==5 else None}
            if missing==0:complete+=1
            else:missing_by_country[c]+=1
            result[(c,m["id"])]={"eligible_for_forward_xg_feature":missing==0,
                                  "home":sides["home"],"away":sides["away"]}
    return {"future_targets_scanned":total,
            "complete_last5_both_team_xg":complete,
            "missing_by_country":dict(missing_by_country),
            "research_only_no_fitted_xg_model":True},result

def missing_last5_predecessor_ids(db_path,groups,at):
    """Identify actual previous-five fixture IDs per team from observed source.

    Read-only diagnostics; not an alternative to true xG, not historical PIT.
    Excludes future/unfinished/too-fresh predecessors and preserves missing IDs.
    """
    with connect(db_path) as db:
        known={(c,mid):as_utc(observed) for c,mid,observed in db.execute(
            "SELECT country,provider_match_id,observed_utc FROM observed_native_xg")}
    output=[]
    for country in sorted(groups):
        part=groups[country]
        for target in part["future"]:
            if (target.get("status") not in ("scheduled","not_started","upcoming")
                or target.get("score_home") is not None or target.get("score_away") is not None
                or not at+LEAD<as_utc(target["time_utc"])<=at+timedelta(hours=CANDIDATE_HOURS)):
                continue
            item={"country":country,"target_provider_match_id":target["id"],
                  "kickoff_utc":target["time_utc"],"teams":{}}
            for side in ("home_team","away_team"):
                team=target[side]["id"]
                actual=sorted((m for m in part["history"] if
                     m["id"]!=target["id"] and
                     as_utc(m["time_utc"])+timedelta(hours=3)<=at and
                     as_utc(m["time_utc"])<as_utc(target["time_utc"]) and
                     team in (m["home_team"]["id"],m["away_team"]["id"])),
                     key=lambda m:(m["time_utc"],m["id"]),reverse=True)[:5]
                missing=[m["id"] for m in actual if
                    (country,m["id"]) not in known or known[(country,m["id"])]>at]
                item["teams"][side]={"native_team_id":team,
                   "actual_last5_provider_ids":[m["id"] for m in actual],
                   "missing_native_xg_provider_ids":missing,
                   "fewer_than_five_finished_predecessors":len(actual)<5,
                   "exact_last5_verified":len(actual)==5 and not missing}
            item["both_teams_last5_verified"]=all(
                item["teams"][side]["exact_last5_verified"] for side in ("home_team","away_team"))
            output.append(item)
    return output

def run(*,client,db_path=DB,archive=ARCHIVE,now=None,public_key=None):
    now=now or datetime.now(timezone.utc)
    require(now.utcoffset()==timedelta(0),"XG_RUN_UTC_REQUIRED")
    day=now.date().isoformat();dest=Path(archive)/day
    require(not dest.exists(),"XG_DAILY_RUN_ALREADY_SAVED")
    known=set()
    if Path(db_path).exists():
        with connect(db_path) as db:
            known={(x[0],x[1]) for x in db.execute(
                "SELECT country,provider_match_id FROM observed_native_xg")}
    receipts=[];errors=Counter();calls=0
    def call(resource,method,*args,**kwargs):
        nonlocal calls
        require(calls<MAX_CALLS,"XG_PITCHAPI_BUDGET_EXCEEDED")
        calls+=1;start=utc_now()
        try:data=to_plain(method(*args,**kwargs))
        except Exception as e:
            errors[type(e).__name__]+=1
            return None
        end=utc_now()
        if not isinstance(data,dict):
            errors["NON_OBJECT"]+=1;return None
        add_observation(receipts,resource=resource,payload=data,started=start,completed=end)
        return data
    catalog=call("pitchapi:step17xg:catalog",client.leagues.list)
    require(catalog is not None,"XG_CATALOG_UNAVAILABLE")
    selected=select_eight(catalog)
    for c,title,lid in selected:
        for season in (PREVIOUS,CURRENT):
            got=call("pitchapi:step17xg:fixtures:"+c+":"+season,
                     client.leagues.matches,lid,season=season,
                     **({"status":"all"} if season==CURRENT else {}))
            require(got is not None,"XG_FIXTURE_SEASON_UNAVAILABLE_"+c)
    cutoff=datetime.now(timezone.utc)
    grouped=fixture_groups(receipts)
    picks,groups=rank_sources(grouped,known,cutoff)
    # Actual paid API selection remains the unmodified baseline selector.
    # Side-by-side hypothetical shadow is computed from SAME authentic fixtures;
    # it does not obtain extra data or claim observed experimental results.
    from src.kb3_step17_xg_priority_research import (
        ranked_eight,compare_counterfactual_selection)
    priority_picks,priority_meta=ranked_eight(
        groups,known,cutoff,budget=8,per_league=MAX_PAIRS_PER_LEAGUE)
    theoretical=compare_counterfactual_selection(
        groups,known,cutoff,picks,priority_picks)
    require(priority_meta["max_provider_calls"]<=MAX_CALLS
        and len(priority_picks)<=8,"RESEARCH_XG_SHADOW_BUDGET_EXCEEDED")
    baseline_ids={(c,m["id"]) for c,m in picks}
    alternative_ids={(c,m["id"]) for c,m in priority_picks}
    candidates=[];semantic_errors=Counter()
    for c,m in picks:
        mid=m["id"]
        shot=call("pitchapi:step17xg:shots:"+mid,client.matches.shots,mid)
        shotreceipt=receipts[-1] if shot is not None else None
        stat=call("pitchapi:step17xg:stats:"+mid,client.matches.stats,mid)
        statreceipt=receipts[-1] if stat is not None else None
        if shot is None or stat is None:continue
        try:
            candidates.append(parse_pair(shot,stat,match=m,country=c,
                  shot_receipt=shotreceipt,stat_receipt=statreceipt))
        except (SemanticAuditError,ValueError) as e:
            semantic_errors[type(e).__name__+":"+str(e)[:60]]+=1
    require(calls<=MAX_CALLS and len(candidates)<=8,"XG_PROVIDER_CALLS_EXCEEDED")
    dest.mkdir(parents=True,exist_ok=False)
    staged=dest/"STAGED_XG.sqlite"
    if Path(db_path).exists():shutil.copy2(db_path,staged)
    try:
        sealed=seal(receipts,public_key or ROOT/"config/step11_archive_recipient_public.pem",
              dest/"XG_SOURCE.enc",dest/"XG_SOURCE.manifest.json")
        count=store_samples(staged,candidates)
        cutoff=datetime.now(timezone.utc)
        coverage,_=future_xg_coverage(staged,groups,cutoff)
        missing_ids=missing_last5_predecessor_ids(staged,groups,cutoff)
        require(len(missing_ids)==coverage["future_targets_scanned"] and
                sum(int(x["both_teams_last5_verified"]) for x in missing_ids)==
                  coverage["complete_last5_both_team_xg"],
                "XG_MISSING_IDS_AND_STRICT_COVERAGE_DISAGREE")
        report={"schema":"kb3-step17-native-xg-eight-asof-shadow-v1",
         "observed_at_utc":stamp(cutoff),
         "network_calls":calls,"hard_limit_calls":MAX_CALLS,
         "leagues":list(c for c,_,_ in EIGHT),
         "prior_matches_selected":len(picks),
         "new_shots_stats_xg_verified":len(candidates),
         "cumulative_verified_xg_matches":count,
         "xg_semantic_errors":dict(semantic_errors),
         "provider_error_types":dict(errors),
         "future_form5_coverage":coverage,
         "last5_priority_shadow_comparison":{
             "source":"IDENTICAL_REAL_FIXTURES_SAME_OBSERVATION_CUTOFF",
             "baseline_selected_count":len(picks),
             "priority_selected_count":len(priority_picks),
             "overlap_exact_native_pairs":len(baseline_ids & alternative_ids),
             "priority_different_native_pairs":len(alternative_ids-baseline_ids),
             "theoretical_if_all_success":theoretical,
             "priority_meta":priority_meta,
             "observed_baseline_complete_last5_after_real_capture":
                  coverage["complete_last5_both_team_xg"],
             "priority_real_outcome_verified":False,
             "priority_live_activated":False,
             "additional_api_calls":0,
             "research_not_training":True},
         "real_missing_last5_predecessor_ids":missing_ids,
         "missing_id_inventory_source":"SAME_AUTHENTIC_FIXTURE_GROUPS_NO_EXTRA_API",
         "encrypted_source_sha256":sealed["ciphertext_sha256"],
         "source_chain_sha256":sealed["proof"]["final_chain_sha256"],
         "original_provider_published_at_not_known":True,
         "current_2026_capture_is_NOT_historic_2023_25_PIT":True,
         "training_ready":False,"trained_xg_catboost_exists":False,
         "original_m0_modified":False,
         "original_catboost_noxg_modified":False,
         "protected_premier_league_TEST_2026_27_requested":False,
         "auto_promotion":False,"gate17":"PENDING"}
        report["report_sha256"]=hashobj(report)
        with (dest/"XG_READINESS_RECEIPT.json").open("x",encoding="utf8") as f:
            json.dump(report,f,sort_keys=True,indent=2,ensure_ascii=False);f.write("\n")
        Path(db_path).parent.mkdir(parents=True,exist_ok=True)
        os.replace(staged,db_path)
        return report
    except BaseException:
        shutil.rmtree(dest,ignore_errors=True)
        raise
