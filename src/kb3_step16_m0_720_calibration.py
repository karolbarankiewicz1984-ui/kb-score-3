"""Step16 eight-league M0-720: host-time GitHub push proof + immutable 100/50.

Only a real GitHub PushEvent (server-side created_at), containing the exact
historical SQLite forecast payload in the event HEAD commit, can qualify a
forecast for calibration. Source-provided generated_at is NOT a proof.
A missing/expired/unavailable event is an honest PENDING, never invented.
No connection to protected PL TEST, no production approval.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib,json,os,sqlite3,subprocess,tempfile,urllib.request,urllib.error
from src.kb3_step16_m0_720_eight_forward import (
    MODEL,DB,LEAD,ROOT,Research720Error,hashobj,require,stamp,trained_params,
    connect_db)
from src.kb3_pit_ledger import as_utc
from src.kb3_step14_m1_math_calibration import (
    fit_temperature,score_predictions,evaluate_calibrated_holdout)

REPO="karolbarankiewicz1984-ui/kb-score-3"
GIT_PATH="data/forward_m0_720_eight/kb3_forward_eight.sqlite"
MAX_EVENT_PAGES=3
MIN_FIT=100
MIN_HOLDOUT=50
CALIBRATION_SCOPE="ESP_ITA_GER_FRA_NED_BEL_TUR_POL_POOLED_RESEARCH"
PROOF_SQL="""
CREATE TABLE IF NOT EXISTS m0720_github_push_proofs (
 proof_id TEXT PRIMARY KEY,
 forecast_id TEXT NOT NULL UNIQUE REFERENCES forecasts(id),
 model TEXT NOT NULL CHECK(model='M0_ELO_POISSON_RESEARCH_720TRAIN_V1'),
 github_event_id TEXT NOT NULL,
 github_commit_sha TEXT NOT NULL,
 github_server_event_utc TEXT NOT NULL,
 original_forecast_sha256 TEXT NOT NULL,
 source TEXT NOT NULL CHECK(source IN ('GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES',
   'GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES')),
 audit_utc TEXT NOT NULL,
 CHECK(length(github_commit_sha)=40),
 CHECK(length(original_forecast_sha256)=64)
);
CREATE TRIGGER IF NOT EXISTS m0720_proof_no_update BEFORE UPDATE ON m0720_github_push_proofs
 BEGIN SELECT RAISE(ABORT,'PUSH_PROOF_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0720_proof_no_delete BEFORE DELETE ON m0720_github_push_proofs
 BEGIN SELECT RAISE(ABORT,'PUSH_PROOF_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS m0720_calibrators (
 candidate_sha256 TEXT PRIMARY KEY,
 model TEXT NOT NULL CHECK(model='M0_ELO_POISSON_RESEARCH_720TRAIN_V1'),
 scope TEXT NOT NULL CHECK(scope='ESP_ITA_GER_FRA_NED_BEL_TUR_POL_POOLED_RESEARCH'),
 phase TEXT NOT NULL CHECK(phase='EARLY'),
 fitted_at_utc TEXT NOT NULL,
 temperature REAL NOT NULL CHECK(temperature BETWEEN 0.1 AND 10),
 sample_n INTEGER NOT NULL CHECK(sample_n=100),
 sample_ids_sha256 TEXT NOT NULL,
 raw_log_loss REAL NOT NULL,
 fit_log_loss REAL NOT NULL,
 payload_json TEXT NOT NULL,
 production_approved INTEGER NOT NULL DEFAULT 0 CHECK(production_approved=0),
 UNIQUE(model,scope,phase)
);
CREATE TRIGGER IF NOT EXISTS m0720_calibrator_no_update BEFORE UPDATE ON m0720_calibrators
 BEGIN SELECT RAISE(ABORT,'M0720_CALIBRATOR_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0720_calibrator_no_delete BEFORE DELETE ON m0720_calibrators
 BEGIN SELECT RAISE(ABORT,'M0720_CALIBRATOR_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS m0720_holdout_reviews (
 review_sha256 TEXT PRIMARY KEY,
 candidate_sha256 TEXT NOT NULL UNIQUE REFERENCES m0720_calibrators(candidate_sha256),
 reviewed_at_utc TEXT NOT NULL,
 holdout_n INTEGER NOT NULL CHECK(holdout_n=50),
 forecast_ids_sha256 TEXT NOT NULL,
 raw_log_loss REAL NOT NULL,
 calibrated_log_loss REAL NOT NULL,
 raw_brier_sum3 REAL NOT NULL,
 calibrated_brier_sum3 REAL NOT NULL,
 payload_json TEXT NOT NULL,
 production_approved INTEGER NOT NULL DEFAULT 0 CHECK(production_approved=0)
);
CREATE TRIGGER IF NOT EXISTS m0720_holdout_no_update BEFORE UPDATE ON m0720_holdout_reviews
 BEGIN SELECT RAISE(ABORT,'M0720_HOLDOUT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0720_holdout_no_delete BEFORE DELETE ON m0720_holdout_reviews
 BEGIN SELECT RAISE(ABORT,'M0720_HOLDOUT_IMMUTABLE'); END;
"""

def ensure_schema(db):
    # Older deployed 29 October schema allowed only PushEvent. GitHub's own
    # bot push is absent from /events; Actions artifact is valid host evidence.
    # Only re-create this strictly EMPTY audit table (never touch predictions,
    # settlements or nonempty evidence). A populated legacy schema fails closed.
    old=db.execute("""SELECT sql FROM sqlite_master WHERE type='table'
                      AND name='m0720_github_push_proofs'""").fetchone()
    if old is not None and "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES" not in old[0]:
        count=db.execute("SELECT COUNT(*) FROM m0720_github_push_proofs").fetchone()[0]
        require(count==0,"NONEMPTY_LEGACY_PROOF_SCHEMA_NEEDS_REVIEW")
        db.execute("DROP TABLE m0720_github_push_proofs")
    db.executescript(PROOF_SQL)
    require(db.execute("PRAGMA foreign_key_check").fetchall()==[],
            "CALIBRATION_FOREIGN_KEY_FAILURE")

def github_events(token,*,max_pages=MAX_EVENT_PAGES):
    """Never infer push time from user-editable Git commit author/committer date."""
    if not token:
        return [],"NO_GITHUB_EVENTS_API_TOKEN"
    found=[]
    try:
        for page in range(1,max_pages+1):
            url=f"https://api.github.com/repos/{REPO}/events?per_page=100&page={page}"
            req=urllib.request.Request(url,headers={
                "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
                "X-GitHub-Api-Version":"2022-11-28","User-Agent":"KB3-M0-720-Step16-audit"})
            with urllib.request.urlopen(req,timeout=15) as reply:
                result=json.load(reply)
            if not isinstance(result,list):
                return [],"GITHUB_EVENTS_API_NONLIST"
            for e in result:
                if e.get("type")=="PushEvent" and e.get("repo",{}).get("name")==REPO:
                    sha=(e.get("payload") or {}).get("head")
                    created=e.get("created_at")
                    if (isinstance(sha,str) and len(sha)==40 and
                        isinstance(created,str) and e.get("id")):
                        found.append({"event_id":str(e["id"]),"head":sha,
                                      "event_utc":created})
            if len(result)<100:break
        return found,"GITHUB_PUSH_EVENTS_RETRIEVED"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return [],"GITHUB_EVENTS_UNAVAILABLE_"+type(exc).__name__

def historical_snapshot_at_commit(commit_sha,*,repo_root=ROOT):
    """Read *actual* bytes archived in remote revision, never current working DB."""
    require(isinstance(commit_sha,str) and len(commit_sha)==40 and
            all(c in "0123456789abcdef" for c in commit_sha.lower()),
            "INVALID_GIT_COMMIT_SHA")
    cmd=["git","show",commit_sha+":"+GIT_PATH]
    out=subprocess.run(cmd,cwd=repo_root,stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL,timeout=18)
    if out.returncode or not out.stdout:
        return {}
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"historic.sqlite"
        p.write_bytes(out.stdout)
        uri="file:"+str(p)+"?immutable=1"
        try:
            with sqlite3.connect(uri,uri=True) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                    return {}
                rows=db.execute("""SELECT f.id,f.payload_json,f.kickoff_utc,
                       f.captured_at_utc,f.params_sha256 FROM forecasts f
                    JOIN model_meta m ON m.model=f.model
                    WHERE f.model=? AND f.params_sha256=m.parameters_sha256""",
                    (MODEL,)).fetchall()
                verified={}
                for fid,payload,kick,captured,params in rows:
                    item=json.loads(payload)
                    if (item.get("forecast_sha256")==fid
                        and item.get("params_sha256")==params
                        and hashobj({k:v for k,v in item.items()
                                    if k!="forecast_sha256"})==fid):
                        verified[fid]=(kick,captured,params)
                return verified
        except (sqlite3.DatabaseError,ValueError,KeyError):
            return {}

def inspect_event_proofs(db_path,events,*,now,repo_root=ROOT):
    """Identify server-attested pushes containing exact original immutable rows."""
    require(now.tzinfo is not None and now.utcoffset()==timedelta(0),
            "PROOF_AUDIT_UTC_REQUIRED")
    candidates=[]
    with connect_db(db_path) as db:
        ensure_schema(db)
        pending=db.execute("""SELECT id,kickoff_utc,captured_at_utc,params_sha256
                   FROM forecasts WHERE id NOT IN
                   (SELECT forecast_id FROM m0720_github_push_proofs)""").fetchall()
    checked={}
    for e in events:
        try:
            event_time=as_utc(e["event_utc"])
        except (KeyError,ValueError,TypeError):
            continue
        if event_time>now or not e.get("event_id"):
            continue
        sha=e["head"]
        snapshot=historical_snapshot_at_commit(sha,repo_root=repo_root)
        if snapshot:checked[e["event_id"]]=(event_time,sha,snapshot)
    for fid,kick,captured,params in pending:
        if as_utc(captured)>=as_utc(kick)-LEAD:
            continue
        valid=[]
        for eid,(ts,sha,snapshot) in checked.items():
            if snapshot.get(fid)==(kick,captured,params) and (
                as_utc(captured)<=ts<=as_utc(kick)-LEAD):
                valid.append((ts,eid,sha))
        if valid:
            ts,eid,sha=min(valid)
            rec={"forecast_id":fid,"model":MODEL,"github_event_id":eid,
                 "github_commit_sha":sha,"github_server_event_utc":stamp(ts),
                 "original_forecast_sha256":fid,
                 "source":"GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES",
                 "audit_utc":stamp(now)}
            candidates.append(rec|{"proof_id":hashobj(rec)})
    return candidates,{"events_considered":len(events),"historic_versions_verified":len(checked),
                       "existing_unproven":len(pending),
                       "new_verified_proof_candidates":len(candidates)}

def append_proofs(db_path,proofs,*,now):
    with connect_db(db_path) as db:
        ensure_schema(db)
        for p in proofs:
            orig={k:v for k,v in p.items() if k!="proof_id"}
            require(p["proof_id"]==hashobj(orig) and
                    p["source"] in ("GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES",
                        "GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES")
                    and p["model"]==MODEL and p["forecast_id"]==p["original_forecast_sha256"],
                    "UNVERIFIED_PUSH_PROOF")
            row=db.execute("""SELECT kickoff_utc,captured_at_utc FROM forecasts
                              WHERE id=?""",(p["forecast_id"],)).fetchone()
            require(row is not None and as_utc(row[1])<=as_utc(p["github_server_event_utc"])
                    <=as_utc(row[0])-LEAD and as_utc(p["audit_utc"])<=now,
                    "GITHUB_PUBLICATION_NOT_BEFORE_KICKOFF")
            db.execute("""INSERT OR IGNORE INTO m0720_github_push_proofs(
                proof_id,forecast_id,model,github_event_id,github_commit_sha,
                github_server_event_utc,original_forecast_sha256,source,audit_utc)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (p["proof_id"],p["forecast_id"],p["model"],p["github_event_id"],
                 p["github_commit_sha"],p["github_server_event_utc"],p["original_forecast_sha256"],
                 p["source"],p["audit_utc"]))
        db.commit()
        total=db.execute("SELECT COUNT(*) FROM m0720_github_push_proofs").fetchone()[0]
    return total

def eligible_settlements(db,*,at):
    """No duplicate fixtures, protected TEST, swapped parameters or after-the-fact proof."""
    rows=db.execute("""SELECT f.id,f.league,f.native_match_id,
                f.kickoff_utc,f.captured_at_utc,f.payload_json,
                s.outcome,s.observed_utc,p.github_server_event_utc,
                s.log_loss,s.brier_sum3
             FROM forecasts f JOIN settlements s ON s.forecast_id=f.id
             JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
             WHERE f.model=? ORDER BY f.kickoff_utc,f.id""",(MODEL,)).fetchall()
    output=[];seen=set();expected_params=db.execute(
        "SELECT parameters_sha256 FROM model_meta WHERE model=?",(MODEL,)).fetchone()
    require(expected_params is not None,"MISSING_FROZEN_MODEL_META")
    for fid,league,mid,kick,captured,payload,label,settled,published,ll,bs in rows:
        if (league,mid) in seen:
            raise Research720Error("DUPLICATE_VERIFIED_RESULT")
        seen.add((league,mid))
        item=json.loads(payload)
        require(item["forecast_sha256"]==fid and
                hashobj({k:v for k,v in item.items() if k!="forecast_sha256"})==fid
                and item["params_sha256"]==expected_params[0]
                and item["model_version"]==MODEL
                and item.get('league_country')==league and item.get('provider_match_id')==mid
                and item.get('kickoff_utc')==kick and item.get('generated_at_utc')==captured
                and item["phase"]=="EARLY"
                and league in ("ESP","ITA","GER","FRA","NED","BEL","TUR","POL"),
                "VERSION_COHORT_OR_FROZEN_PROBABILITIES_CHANGED")
        if not (as_utc(captured)<=as_utc(published)<=as_utc(kick)-LEAD and
                as_utc(kick)+timedelta(hours=3)<=as_utc(settled)<=at):
            continue
        output.append({"fid":fid,"league":league,"kick":kick,"captured":captured,
                       "settled":settled,"p":item["p_1x2"],"y":label,
                       "ll":ll,"bs":bs})
    return output

def calibrate_if_eligible(db_path=DB,*,now=None):
    now=now or datetime.now(timezone.utc)
    require(now.utcoffset()==timedelta(0),"UTC_REQUIRED_FOR_CALIBRATION")
    with connect_db(db_path) as db:
        ensure_schema(db)
        rows=eligible_settlements(db,at=now)
        by_league=defaultdict(list)
        for x in rows:by_league[x["league"]].append(x)
        league_scores={}
        for league,items in sorted(by_league.items()):
            league_scores[league]=score_predictions(
                [x["p"] for x in items],[x["y"] for x in items])
        cohort_metrics=(score_predictions([x["p"] for x in rows],
                  [x["y"] for x in rows]) if rows else None)
        pending_raw=db.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
        candidate=db.execute("SELECT candidate_sha256,fitted_at_utc,temperature,payload_json FROM m0720_calibrators").fetchone()
        fitted=False;reviewed=False
        if candidate is None and len(rows)>=MIN_FIT:
            sample=rows[:MIN_FIT]
            temp=fit_temperature([x["p"] for x in sample],
                    [x["y"] for x in sample],min_rows=MIN_FIT)
            # Real completion clock, never a source cutoff from before fitting.
            fitted_utc=stamp(max(now,datetime.now(timezone.utc)))
            rec={"model":MODEL,"scope":CALIBRATION_SCOPE,
                 "phase":"EARLY","fitted_at_utc":fitted_utc,
                 "training_ids_sha256":hashobj([x["fid"] for x in sample]),
                 'training_forecast_ids':[x['fid'] for x in sample],
                 "fitted_temperature":float(temp["temperature"]),
                 "training_count":MIN_FIT,
                 "training_last_kickoff_utc":sample[-1]["kick"],
                 "training_last_settlement_utc":max(x["settled"] for x in sample),
                 "training_log_loss_raw":temp["calibration_log_loss_raw"],
                 "training_log_loss_calibrated":temp["calibration_log_loss_fitted"],
                 "no_future_test_outcomes_used":True,
                 "production_approved":False}
            cid=hashobj(rec)
            db.execute("""INSERT INTO m0720_calibrators(
                  candidate_sha256,model,scope,phase,fitted_at_utc,temperature,
                  sample_n,sample_ids_sha256,raw_log_loss,fit_log_loss,payload_json)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                  (cid,MODEL,CALIBRATION_SCOPE,"EARLY",fitted_utc,
                   temp["temperature"],MIN_FIT,rec["training_ids_sha256"],
                   rec["training_log_loss_raw"],rec["training_log_loss_calibrated"],
                   json.dumps(rec,sort_keys=True)))
            db.commit()
            candidate=(cid,fitted_utc,temp["temperature"],json.dumps(rec,sort_keys=True))
            fitted=True
        after=[];review=None
        if candidate:
            cid,fitted_at,temperature,candidate_payload=candidate
            rec=json.loads(candidate_payload)
            require(cid==hashobj(rec) and rec["model"]==MODEL and
                    rec["scope"]==CALIBRATION_SCOPE and
                    rec["fitted_at_utc"]==fitted_at,
                    "IMMUTABLE_CALIBRATOR_SHA_CHANGED")
            # New predictions AND new kickoffs after T is fitted.
            fit_ids=rec.get('training_forecast_ids',[])
            if fit_ids:
                require(len(fit_ids)==len(set(fit_ids))==MIN_FIT and hashobj(fit_ids)==rec['training_ids_sha256'],
                        'IMMUTABLE_FIT_MEMBERSHIP_CHANGED')
            after=[x for x in rows if as_utc(x["captured"])>as_utc(fitted_at)
                   and as_utc(x["kick"])>as_utc(fitted_at)
                   and x['fid'] not in fit_ids]
            review=db.execute("SELECT review_sha256 FROM m0720_holdout_reviews WHERE candidate_sha256=?",(cid,)).fetchone()
            if review is None and len(after)>=MIN_HOLDOUT:
                sample=after[:MIN_HOLDOUT]
                metrics=evaluate_calibrated_holdout(
                    [x["p"] for x in sample],[x["y"] for x in sample],
                    {"temperature":float(temperature)})
                body={"candidate_sha256":cid,"model":MODEL,"scope":CALIBRATION_SCOPE,
                      "phase":"EARLY","reviewed_at_utc":stamp(now),
                      "holdout_n":MIN_HOLDOUT,
                      "holdout_ids_sha256":hashobj([x["fid"] for x in sample]),
                      'holdout_forecast_ids':[x['fid'] for x in sample],
                      "holdout_first_captured_utc":sample[0]["captured"],
                      "holdout_raw":metrics["raw"],"holdout_calibrated":metrics["calibrated"],
                      "training_rows_read_by_holdout":False,
                      "production_approved":False}
                rid=hashobj(body)
                db.execute("""INSERT INTO m0720_holdout_reviews(
                     review_sha256,candidate_sha256,reviewed_at_utc,holdout_n,
                     forecast_ids_sha256,raw_log_loss,calibrated_log_loss,
                     raw_brier_sum3,calibrated_brier_sum3,payload_json)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",
                     (rid,cid,body["reviewed_at_utc"],MIN_HOLDOUT,
                      body["holdout_ids_sha256"],metrics["raw"]["log_loss"],
                      metrics["calibrated"]["log_loss"],metrics["raw"]["brier_sum3"],
                      metrics["calibrated"]["brier_sum3"],json.dumps(body,sort_keys=True)))
                db.commit();reviewed=True
        proof_n=db.execute("SELECT COUNT(*) FROM m0720_github_push_proofs").fetchone()[0]
        review_exists=db.execute("SELECT COUNT(*) FROM m0720_holdout_reviews").fetchone()[0]
        return {"model":MODEL,"gate16":"PENDING",
                "production_approved":False,"model_parameters_modified":False,
                "settled_total":pending_raw,
                "git_server_push_verified_forecasts":proof_n,
                "eligible_settled_unique":len(rows),
                "eligible_per_league":{k:len(v) for k,v in by_league.items()},
                "per_league_scores":league_scores,
                "pooled_scores":cohort_metrics,
                "fit_minimum":MIN_FIT,"holdout_minimum":MIN_HOLDOUT,
                "calibrator_first_fit_just_written":fitted,
                "calibrator_exists":bool(candidate),
                "calibrator_temperature":candidate[2] if candidate else None,
                "post_fit_newly_created_settled_verified":len(after),
                "holdout_first_review_just_written":reviewed,
                "holdout_review_exists":bool(review_exists),
                "missing_to_fit":max(0,MIN_FIT-len(rows)) if not candidate else 0,
                "missing_post_fit_holdout":(max(0,MIN_HOLDOUT-len(after)) if candidate else MIN_HOLDOUT),
                "original_premier_league_TEST_accessed":False}


# Fallback when GitHub does not surface bot-generated PushEvents: GitHub itself
# stamps the uploaded Actions artifact before kickoff. Its *exact binary SQLite*
# must contain the original forecast ID and unaltered payload. The run/zip
# metadata is retrieved from GitHub API, not local Git commit timestamps.
def _gh_json(url,token,*,timeout=15):
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"KB3-Step16-M0-artifact-auditor"})
    with urllib.request.urlopen(req,timeout=timeout) as reply:
        return json.load(reply)

def _gh_artifact_zip(url,token,*,limit=30*1024*1024):
    from urllib.parse import urlparse
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            return None
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "User-Agent":"KB3-Step16-M0-artifact-auditor"})
    opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req,timeout=20) as reply:
            data=reply.read(limit+1)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301,302,303,307,308):
            raise
        target=exc.headers.get("Location","")
        u=urlparse(target)
        require(u.scheme=="https" and bool(u.hostname)
                and u.hostname.lower() not in ("localhost","127.0.0.1","::1"),
                "UNTRUSTED_GITHUB_ARTIFACT_REDIRECT")
        # Follow signed GitHub-selected storage URL *without* bearer credentials.
        with urllib.request.urlopen(
                urllib.request.Request(target,headers={"User-Agent":"KB3-Step16-auditor"}),
                timeout=30) as response:
            data=response.read(limit+1)
    require(0<len(data)<=limit,"GITHUB_ARTIFACT_SIZE_LIMIT")
    return data

def _zip_frozen_rows(blob,*,max_uncompressed=80*1024*1024):
    import io,zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            names=[n for n in archive.namelist()
                   if n.endswith("/kb3_forward_eight.sqlite") or
                      n=="kb3_forward_eight.sqlite"]
            require(len(names)==1,"NO_UNIQUE_GITHUB_ARCHIVED_EIGHT_LEAGUE_DB")
            meta=archive.getinfo(names[0])
            require(0<meta.file_size<=max_uncompressed,
                    "GITHUB_ARCHIVED_SQLITE_TOO_LARGE")
            data=archive.read(names[0])
            require(len(data)==meta.file_size,
                    "GITHUB_ARCHIVED_SQLITE_TRUNCATED")
    except (zipfile.BadZipFile,RuntimeError,ValueError) as exc:
        raise Research720Error("GITHUB_ARTIFACT_ZIP_INVALID") from exc
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder)/"historic.sqlite"
        p.write_bytes(data)
        try:
            with sqlite3.connect("file:"+str(p)+"?immutable=1",uri=True) as db:
                require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                        "GITHUB_ARCHIVED_SQLITE_INTEGRITY_FAIL")
                model,params,manifest=db.execute(
                    "SELECT model,parameters_sha256,manifest_sha256 FROM model_meta").fetchone()
                expected,sha,msha=trained_params()
                require(model==MODEL and params==sha and manifest==msha,
                        "GITHUB_ARCHIVED_MODEL_VERSION_OR_SHA_DIFFER")
                rows=db.execute("""SELECT id,payload_json,kickoff_utc,
                         captured_at_utc,params_sha256 FROM forecasts
                         WHERE model=?""",(MODEL,)).fetchall()
                found={}
                for fid,payload,kick,captured,p_sha in rows:
                    obj=json.loads(payload)
                    require(obj.get("forecast_sha256")==fid and
                        hashobj({k:v for k,v in obj.items() if k!="forecast_sha256"})==fid
                        and obj.get("params_sha256")==p_sha==sha
                        and obj.get("model_version")==MODEL,
                        "GITHUB_ARCHIVED_FORECAST_SHA_TAMPERED")
                    found[fid]=(kick,captured,p_sha)
                return found
        except (sqlite3.DatabaseError,ValueError,TypeError) as exc:
            raise Research720Error("GITHUB_ARCHIVED_SQLITE_INVALID") from exc

def github_actions_artifact_proofs(db_path,*,token,now,max_runs=60):
    """GitHub server-upload timestamp + SHA-verified forecast in archived Actions ZIP.

    Exclude PR jobs; archive expires after retention. Missing/unauthorized results
    are reported PENDING, never replaced with invented commit times or outcomes.
    """
    require(now.tzinfo is not None and now.utcoffset()==timedelta(0),
            "GITHUB_ARTIFACT_PROOF_UTC_REQUIRED")
    if not token:
        return [],{"state":"NO_GITHUB_ACTIONS_API_TOKEN",
                    "runs_checked":0,"artifacts_examined":0,"verified":0}
    with connect_db(db_path) as db:
        ensure_schema(db)
        pending=db.execute("""SELECT id,kickoff_utc,captured_at_utc,params_sha256
                   FROM forecasts WHERE id NOT IN
                   (SELECT forecast_id FROM m0720_github_push_proofs)""").fetchall()
    if not pending:
        return [],{"state":"NO_NEW_UNATTESTED_FORECASTS",
                    "runs_checked":0,"artifacts_examined":0,"verified":0}
    url=f"https://api.github.com/repos/{REPO}/actions/workflows/kb3-step16-m0-720-eight-forward.yml/runs?per_page=100"
    try:
        data=_gh_json(url,token)
        runs=data.get("workflow_runs",[])
        require(isinstance(runs,list),"GITHUB_ACTIONS_RUNS_BAD_FORMAT")
    except (urllib.error.URLError,TimeoutError,OSError,ValueError,Research720Error) as e:
        return [],{"state":"GITHUB_ACTIONS_RUNS_UNAVAILABLE_"+type(e).__name__,
                    "runs_checked":0,"artifacts_examined":0,"verified":0}
    selected=[];n_artifacts=0;blocked=0;unproven={x[0]:x for x in pending}
    # Earlier proofs have priority, even when later uploaded artifacts contain
    # the same existing immutable forecasts.
    valid_runs=sorted((x for x in runs
         if x.get("status")=="completed" and x.get("conclusion")=="success"
         and x.get("event") in ("push","schedule","workflow_dispatch")
         and x.get("path")==".github/workflows/kb3-step16-m0-720-eight-forward.yml"
         and isinstance(x.get("head_sha"),str) and len(x["head_sha"])==40),
         key=lambda z:(z.get("created_at",""),z.get("id",0)))[:max_runs]
    for run in valid_runs:
        if not unproven:break
        try:
            rstart=as_utc(run["created_at"])
            rend=as_utc(run["updated_at"])
            if rstart>now or rend>now+timedelta(minutes=1):continue
            artifacts=_gh_json(f"https://api.github.com/repos/{REPO}/actions/runs/{run['id']}/artifacts?per_page=100",token).get("artifacts",[])
            for art in artifacts:
                if art.get("name")!="KB3_STEP16_M0_720_EIGHT_LEAGUE_FREEZE_SETTLEMENT_SOURCE_EVIDENCE" or art.get("expired") is True:continue
                server=as_utc(art["created_at"])
                if not rstart<=server<=rend+timedelta(minutes=1):
                    continue
                applicable={fid:row for fid,row in unproven.items()
                    if as_utc(row[2])<=server<=as_utc(row[1])-LEAD}
                if not applicable:continue
                n_artifacts+=1
                archive=_gh_artifact_zip(art["archive_download_url"],token)
                actual=_zip_frozen_rows(archive)
                for fid,row in applicable.items():
                    if actual.get(fid)==(row[1],row[2],row[3]):
                        p={"forecast_id":fid,"model":MODEL,
                           "github_event_id":"actions-artifact:"+str(art["id"]),
                           "github_commit_sha":run["head_sha"],
                           "github_server_event_utc":stamp(server),
                           "original_forecast_sha256":fid,
                           "source":"GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES",
                           "audit_utc":stamp(now)}
                        selected.append(p|{"proof_id":hashobj(p)})
                        del unproven[fid]
        except (urllib.error.URLError,TimeoutError,OSError,
                Research720Error,KeyError,TypeError,ValueError) as exc:
            blocked+=1
            continue
    return selected,{"state":"GITHUB_ARTIFACT_AUDIT_COMPLETED",
                      "runs_checked":len(valid_runs),
                      "artifacts_examined":n_artifacts,
                      "artifact_errors":blocked,
                      "verified":len(selected),
                      "still_unproven":len(unproven),
                      "server_created_at_used_not_git_author_timestamp":True}
