"""Step17 forward source provenance and genuine same-fixture settled comparison.

Only GitHub HOST server-created Actions artifact containing original immutable
M0+Challenger SQLite bytes attests the new challengers. No self-declared dates,
git author timestamps, after-the-fact challenger backfill or future outcomes.
No new provider requests / training / production activation / protected TEST.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import io,json,sqlite3,tempfile,zipfile
from src.kb3_step16_m0_720_eight_forward import MODEL,ROOT,LEAD,require,hashobj,trained_params,connect_db,stamp
from src.kb3_pit_ledger import as_utc
from src.kb3_step16_m0_720_calibration import (
   _gh_json,_gh_artifact_zip,ensure_schema)
from src.kb3_step17_forward_challengers import ELO,CAT,CBM_SHA,VERSIONS,SCHEMA as CHALLENGER_SCHEMA
from src.kb3_step17_engine_comparison import compare

REPO="karolbarankiewicz1984-ui/kb-score-3"
ARTIFACT_NAME="KB3_STEP16_M0_720_EIGHT_LEAGUE_FREEZE_SETTLEMENT_SOURCE_EVIDENCE"
PROOF_SCHEMA="""
CREATE TABLE IF NOT EXISTS step17_challenger_host_proofs(
 proof_sha256 TEXT PRIMARY KEY,
 challenger_sha256 TEXT NOT NULL UNIQUE REFERENCES step17_frozen_challengers(challenger_sha256),
 source_m0_forecast_sha256 TEXT NOT NULL REFERENCES forecasts(id),
 github_artifact_id TEXT NOT NULL,
 github_server_artifact_created_utc TEXT NOT NULL,
 model_version TEXT NOT NULL,
 attestation_source TEXT NOT NULL CHECK(attestation_source='GITHUB_HOST_ARTIFACT_ARCHIVED_EXACT_ORIGINAL_CHALLENGER_SQLITE'),
 audited_at_utc TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS step17_proofs_no_update BEFORE UPDATE ON step17_challenger_host_proofs
 BEGIN SELECT RAISE(ABORT,'STEP17_CHALLENGER_PROOF_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS step17_proofs_no_delete BEFORE DELETE ON step17_challenger_host_proofs
 BEGIN SELECT RAISE(ABORT,'STEP17_CHALLENGER_PROOF_IMMUTABLE'); END;
"""

def ensure(db):
    ensure_schema(db)
    db.executescript(CHALLENGER_SCHEMA)
    db.executescript(PROOF_SCHEMA)
    require(db.execute("PRAGMA foreign_key_check").fetchall()==[],
            "STEP17_PROOF_FOREIGN_KEY_DRIFT")

def _archived_challengers(blob):
    """Read exact zip bytes, including their original M0 parents and immutable children."""
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names=[x for x in z.namelist() if x.endswith("/kb3_forward_eight.sqlite")
                   or x=="kb3_forward_eight.sqlite"]
            require(len(names)==1,"STEP17_GITHUB_ARTIFACT_DB_MISSING")
            require(0<z.getinfo(names[0]).file_size<=80*1024*1024,
                    "STEP17_GITHUB_ARTIFACT_DB_OVERSIZED")
            raw=z.read(names[0])
    except (zipfile.BadZipFile,RuntimeError,ValueError) as exc:
        raise ValueError("STEP17_GITHUB_ARTIFACT_INVALID_ZIP") from exc
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"historic.sqlite";p.write_bytes(raw)
        try:
            with sqlite3.connect("file:"+str(p)+"?immutable=1",uri=True) as db:
                require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                        "STEP17_HISTORIC_DB_INVALID")
                parent=db.execute("SELECT model,parameters_sha256,manifest_sha256 FROM model_meta").fetchall()
                params,sha,manifest=trained_params()
                require(parent==[(MODEL,sha,manifest)],"STEP17_HISTORIC_M0_MODEL_DRIFT")
                if not db.execute("""SELECT 1 FROM sqlite_master
                         WHERE type='table' AND name='step17_frozen_challengers'""").fetchone():
                    return {}
                rows=db.execute("""SELECT c.challenger_sha256,c.payload_json,c.source_m0_forecast_sha256,
                       f.payload_json FROM step17_frozen_challengers c
                       JOIN forecasts f ON f.id=c.source_m0_forecast_sha256""").fetchall()
                verified={}
                for chid,childjson,parentid,parentjson in rows:
                    child=json.loads(childjson);original=json.loads(parentjson)
                    require(original.get("forecast_sha256")==parentid and
                        hashobj({k:v for k,v in original.items() if k!="forecast_sha256"})==parentid,
                        "STEP17_HISTORIC_M0_ROW_TAMPERED")
                    require(child.get("challenger_sha256")==chid and
                        hashobj({k:v for k,v in child.items() if k!="challenger_sha256"})==chid
                        and child.get("source_m0_forecast_sha256")==parentid
                        and child.get("feature_sha256")==original.get("feature_sha256")
                        and child.get("frozen_at_utc")==original.get("generated_at_utc")
                        and child.get("source_chain_sha256")==original.get("source_chain_sha256")
                        and child.get("kickoff_utc")==original.get("kickoff_utc")
                        and child.get("engine") in VERSIONS and
                        child.get("model_version")==VERSIONS[child["engine"]],
                        "STEP17_HISTORIC_CHALLENGER_TAMPERED")
                    verified[chid]=(parentid,child["frozen_at_utc"],
                                    child["kickoff_utc"],child["model_version"])
                return verified
        except sqlite3.DatabaseError as exc:
            raise ValueError("STEP17_HISTORIC_SQLITE_READ_FAIL") from exc

def audit_challengers(db_path,*,token,now,max_artifacts=12):
    require(now.tzinfo is not None and now.utcoffset()==timedelta(0),
            "STEP17_AUDIT_UTC_REQUIRED")
    with connect_db(db_path) as db:
        ensure(db)
        pending=db.execute("""SELECT c.challenger_sha256,c.source_m0_forecast_sha256,
                    c.frozen_at_utc,c.kickoff_utc,c.model_version,
                    p.github_event_id,p.github_server_event_utc
          FROM step17_frozen_challengers c
          JOIN m0720_github_push_proofs p ON p.forecast_id=c.source_m0_forecast_sha256
          WHERE c.challenger_sha256 NOT IN
                (SELECT challenger_sha256 FROM step17_challenger_host_proofs)
            AND p.source='GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES'
          ORDER BY c.kickoff_utc,c.challenger_sha256""").fetchall()
    if not pending or not token:
        return {"state":"NO_PENDING_ATTESTED_M0_PARENTS" if not pending else "NO_GITHUB_TOKEN",
                "unattested_challengers_with_qualified_m0_parent":len(pending),
                "new_github_proofs":0,"errors":0}
    by_artifact=defaultdict(list)
    for row in pending:
        if row[5].startswith("actions-artifact:"):
            by_artifact[row[5].split(":",1)[1]].append(row)
    added=0;errors=0;examined=0
    for aid,items in sorted(by_artifact.items()):
        if examined>=max_artifacts:break
        examined+=1
        try:
            meta=_gh_json(f"https://api.github.com/repos/{REPO}/actions/artifacts/{aid}",token)
            require(str(meta.get("id"))==aid and meta.get("name")==ARTIFACT_NAME
                    and meta.get("expired") is False,"STEP17_UNTRUSTED_ARTIFACT_METADATA")
            server=as_utc(meta["created_at"])
            require(server<=now,"STEP17_FUTURE_HOST_ARTIFACT")
            data=_gh_artifact_zip(meta["archive_download_url"],token)
            originals=_archived_challengers(data)
            with connect_db(db_path) as db:
                ensure(db)
                for chid,parentid,created,kick,version,sourceaid,sourcets in items:
                    if not (as_utc(created)<=server<=as_utc(kick)-LEAD
                            and stamp(server)==stamp(as_utc(sourcets))):
                        continue
                    if originals.get(chid)!=(parentid,created,kick,version):
                        continue
                    entry={"challenger_sha256":chid,"source_m0_forecast_sha256":parentid,
                           "github_artifact_id":aid,
                           "github_server_artifact_created_utc":stamp(server),
                           "model_version":version,
                           "attestation_source":"GITHUB_HOST_ARTIFACT_ARCHIVED_EXACT_ORIGINAL_CHALLENGER_SQLITE",
                           "audited_at_utc":stamp(now)}
                    proof_sha=hashobj(entry)
                    db.execute("""INSERT OR IGNORE INTO step17_challenger_host_proofs
                         (proof_sha256,challenger_sha256,source_m0_forecast_sha256,
                          github_artifact_id,github_server_artifact_created_utc,
                          model_version,attestation_source,audited_at_utc)
                         VALUES(?,?,?,?,?,?,?,?)""",
                         (proof_sha,chid,parentid,aid,entry["github_server_artifact_created_utc"],
                          version,entry["attestation_source"],entry["audited_at_utc"]))
                    added+=1
                db.commit()
        except (OSError,ValueError,KeyError,TypeError,sqlite3.DatabaseError) as exc:
            errors+=1
    with connect_db(db_path) as db:
        ensure(db)
        overall=db.execute("SELECT COUNT(*) FROM step17_challenger_host_proofs").fetchone()[0]
    return {"state":"ACTUAL_GITHUB_SERVER_ARTIFACT_VERIFICATION",
            "new_github_proofs":added,"total_verified_challenger_forecasts":overall,
            "artifacts_examined":examined,"unverified_pending":max(0,len(pending)-added),
            "errors":errors,"on_missing_archive_never_infer_frozen_time":True}

def paired_settled_report(db_path):
    """Only same original M0 forecast, settled truth, attested *each* model."""
    with connect_db(db_path) as db:
        ensure(db)
        sql="""SELECT f.id,f.league,f.native_match_id,f.kickoff_utc,f.captured_at_utc,
                  f.payload_json,s.outcome,s.observed_utc,
                  c.challenger_sha256,c.model_version,c.engine,c.payload_json
            FROM forecasts f
            JOIN settlements s ON s.forecast_id=f.id
            JOIN m0720_github_push_proofs p ON p.forecast_id=f.id
            JOIN step17_frozen_challengers c ON c.source_m0_forecast_sha256=f.id
            JOIN step17_challenger_host_proofs pr ON pr.challenger_sha256=c.challenger_sha256
            ORDER BY f.kickoff_utc,f.id,c.engine"""
        rows=db.execute(sql).fetchall()
    models={"ELO_ONLY":ELO,"M0_ELO_POISSON_720TRAIN":MODEL,
            "CATBOOST_NO_XG":CAT,"CATBOOST_WITH_XG":None,"ENSEMBLE":None}
    games={}
    for fid,league,mid,kick,captured,fjson,y,obs,child_id,version,engine,cjson in rows:
        f=json.loads(fjson);c=json.loads(cjson)
        require(hashobj({k:v for k,v in f.items() if k!="forecast_sha256"})==fid
                and hashobj({k:v for k,v in c.items() if k!="challenger_sha256"})==child_id
                and c["source_m0_forecast_sha256"]==fid
                and c["model_version"]==version==models[engine],
                "STEP17_PAIR_SHA_OR_MODEL_CHANGED")
        key=(league,mid)
        if key not in games:
            games[key]={"fixture_id":mid,"league":league,
               "kickoff_utc":kick,"outcome_1x2":y,
               "result_observed_utc":obs,"predictions":{
                  "M0_ELO_POISSON_720TRAIN":{
                   "model_version":MODEL,"p_1x2":f["p_1x2"],
                   "frozen_at_utc":captured,"horizon":"EARLY_90MIN_OR_MORE",
                   "github_server_artifact_verified":True,
                   "forecast_hash_verified":True}}}
        require(games[key]["outcome_1x2"]==y and
                games[key]["kickoff_utc"]==kick,"STEP17_INCONSISTENT_SETTLEMENT")
        require(engine not in games[key]["predictions"],"STEP17_DUPLICATE_ENGINE_FOR_MATCH")
        games[key]["predictions"][engine]={
            "model_version":version,"p_1x2":c["p_1x2"],
            "frozen_at_utc":c["frozen_at_utc"],"horizon":"EARLY_90MIN_OR_MORE",
            "github_server_artifact_verified":True,
            "forecast_hash_verified":True}
    payload={"schema":"kb3-step17-paired-engine-input-v1",
        "evaluation_domain":"FORWARD_GITHUB_HOST_ATTESTED","market":"1X2_90MIN",
        "horizon":"EARLY_90MIN_OR_MORE","candidate_versions":models,
        "protected_test_opened":False,
        "games":list(games.values())}
    report=compare(payload,replicates=1200)
    report["scope_note"]="ONLY_PAIRS_WITH_BOTH_ORIGINAL_FORECAST_AND_REAL_GITHUB_ARTIFACT_PROOFS_AND_RESULTS"
    report["production_approved"]=False
    return report
