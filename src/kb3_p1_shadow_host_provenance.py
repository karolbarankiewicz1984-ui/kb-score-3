"""Host-attested append-only CatBoost shadow proof + paired settled research.

NEVER use local git author dates or mutable SQLite clocks as proof. Require a
GitHub server-created M0 workflow artifact with matching original ZIP SQLite
bytes archived before the match's 90-minute deadline.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from collections import defaultdict
from pathlib import Path
import io,json,sqlite3,tempfile,zipfile

from src.kb3_p1_prospective_shadow_six_v1 import (
    DB_SCHEMA,MODEL,SCHEMA_VERSION
)
from src.kb3_p1_shadow_live_gate import pinned_model_details
from src.kb3_step16_m0_720_eight_forward import (
    ROOT,MODEL as M0,LEAD,hashobj,require,trained_params,stamp
)
from src.kb3_pit_ledger import as_utc
from src.kb3_step16_m0_720_calibration import (
    _gh_json,_gh_artifact_zip,ensure_schema
)
from src.kb3_step17_challenger_provenance import (
    REPO,ARTIFACT_NAME
)
from src.kb3_step14_m1_math_calibration import score_predictions
from src.kb3_step17_engine_comparison import prob

PROOF_SCHEMA="""
CREATE TABLE IF NOT EXISTS kb3_p1_shadow_six_host_proofs (
 proof_sha256 TEXT PRIMARY KEY,
 shadow_sha256 TEXT NOT NULL UNIQUE
   REFERENCES kb3_p1_shadow_six_new_only(id),
 source_m0_forecast_sha256 TEXT NOT NULL REFERENCES forecasts(id),
 github_artifact_id TEXT NOT NULL,
 github_server_artifact_created_utc TEXT NOT NULL,
 attestation_source TEXT NOT NULL
 CHECK(attestation_source='GITHUB_HOST_ARCHIVED_ORIGINAL_SHADOW_SIX_SQLITE_BYTES'),
 audited_at_utc TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS kb3_p1_shadow_proofs_no_update
 BEFORE UPDATE ON kb3_p1_shadow_six_host_proofs
 BEGIN SELECT RAISE(ABORT,'SHADOW_HOST_PROOF_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS kb3_p1_shadow_proofs_no_delete
 BEFORE DELETE ON kb3_p1_shadow_six_host_proofs
 BEGIN SELECT RAISE(ABORT,'SHADOW_HOST_PROOF_IMMUTABLE'); END;
"""

def _shadow_present(db):
    return db.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='kb3_p1_shadow_six_new_only'"
    ).fetchone()[0]==1


def ensure(db):
    ensure_schema(db)
    db.executescript(DB_SCHEMA)
    db.executescript(PROOF_SCHEMA)
    require(db.execute("PRAGMA foreign_key_check").fetchall()==[],
            "SHADOW_PROVENANCE_FK_CORRUPTION")


def _archived_shadow(artifact_zip):
    """Extract EXACT original parent+shadow bytes, never reconstruct predictions."""
    with zipfile.ZipFile(io.BytesIO(artifact_zip)) as z:
        names=[n for n in z.namelist() if n.endswith("/kb3_forward_eight.sqlite")
               or n=="kb3_forward_eight.sqlite"]
        require(len(names)==1,"SHADOW_ORIGINAL_DB_NOT_IN_HOST_ARTIFACT")
        info=z.getinfo(names[0])
        require(0<info.file_size<=80*1024*1024,"SHADOW_ARCHIVE_DB_TOO_LARGE")
        content=z.read(names[0])
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"original.sqlite"
        p.write_bytes(content)
        with sqlite3.connect("file:"+str(p)+"?immutable=1",uri=True) as db:
            require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                    "SHADOW_ORIGINAL_SQLITE_INVALID")
            if not _shadow_present(db):
                return {}
            meta=db.execute("SELECT model,parameters_sha256,manifest_sha256 "
                            "FROM model_meta").fetchall()
            _,sha,manifest=trained_params()
            require(meta==[(M0,sha,manifest)],
                    "SHADOW_ORIGINAL_PARENT_MODEL_CHANGED")
            pin=pinned_model_details()
            rows=db.execute("""
              SELECT s.id,s.payload_json,s.source_m0_forecast_sha256,
                     f.payload_json
              FROM kb3_p1_shadow_six_new_only s
              JOIN forecasts f ON f.id=s.source_m0_forecast_sha256""").fetchall()
            out={}
            for childsha,sjson,parentid,pjson in rows:
                child=json.loads(sjson);parent=json.loads(pjson)
                require(
                  parent.get("forecast_sha256")==parentid and
                  hashobj({k:v for k,v in parent.items()
                           if k!="forecast_sha256"})==parentid and
                  child.get("shadow_sha256")==childsha and
                  hashobj({k:v for k,v in child.items()
                           if k!="shadow_sha256"})==childsha,
                  "SHADOW_ARCHIVED_EXACT_PAYLOAD_SHA_INVALID")
                require(
                  child.get("source_m0_forecast_sha256")==parentid and
                  child.get("schema")==SCHEMA_VERSION and
                  child.get("model_version")==MODEL and
                  child.get("model_bytes_sha256")==pin["model_sha256"] and
                  child.get("model_manifest_sha256")==pin["manifest_sha256"] and
                  child.get("feature_sha256")==parent["feature_sha256"] and
                  child.get("source_chain_sha256")==parent["source_chain_sha256"] and
                  child.get("original_feature_cutoff_utc")==parent["feature_cutoff_utc"] and
                  child.get("kickoff_utc")==parent["kickoff_utc"] and
                  child.get("shadow_host_artifact_verified") is False and
                  child.get("production_approved") is False,
                  "SHADOW_ARCHIVED_MODEL_OR_PARENT_MISMATCH")
                require(as_utc(child["shadow_generated_at_utc"]) <
                        as_utc(child["kickoff_utc"])-LEAD,
                        "SHADOW_ARCHIVED_TOO_LATE")
                prob(child["p_1x2"])
                out[childsha]=(parentid,child["shadow_generated_at_utc"],
                               child["kickoff_utc"],
                               child["model_bytes_sha256"])
            return out


def audit_shadow(db_path,*,token,now,max_artifacts=12):
    require(now.utcoffset()==timedelta(0),"SHADOW_AUDIT_UTC_CLOCK_REQUIRED")
    with sqlite3.connect(db_path) as db:
        if not _shadow_present(db):
            return {"state":"SHADOW_DISABLED_OR_NO_NEW_ROWS",
                    "new_host_proofs":0,"matched":0,"verified":0,
                    "artifact_checks":0}
        db.execute("PRAGMA foreign_keys=ON")
        ensure(db)
        pending=db.execute("""
          SELECT s.id,s.source_m0_forecast_sha256,s.shadow_generated_at_utc,
                 s.kickoff_utc,s.model_bytes_sha256,p.github_event_id,
                 p.github_server_event_utc
          FROM kb3_p1_shadow_six_new_only s
          JOIN m0720_github_push_proofs p
               ON p.forecast_id=s.source_m0_forecast_sha256
          WHERE p.source='GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES'
          AND s.id NOT IN
             (SELECT shadow_sha256 FROM kb3_p1_shadow_six_host_proofs)
          ORDER BY s.kickoff_utc,s.id
        """).fetchall()
    if not pending or not token:
        return {
          "state":"NO_PENDING_ATTESTED_M0_PARENTS" if not pending
                  else "PENDING_NO_GITHUB_READ_TOKEN",
          "pending":len(pending),"new_host_proofs":0,
          "artifact_checks":0,"errors":0}
    by_artifact=defaultdict(list)
    for row in pending:
        if str(row[5]).startswith("actions-artifact:"):
            by_artifact[str(row[5]).split(":",1)[1]].append(row)
    added=0;checks=0;errors=0
    for artifact_id,rows in sorted(by_artifact.items()):
        if checks>=max_artifacts:break
        checks+=1
        try:
            meta=_gh_json(
                f"https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}",
                token)
            require(str(meta.get("id"))==artifact_id and
                    meta.get("name")==ARTIFACT_NAME and
                    meta.get("expired") is False,
                    "SHADOW_UNTRUSTED_GITHUB_HOST_ARTIFACT")
            server=as_utc(meta["created_at"])
            require(server<=now,"SHADOW_ARTIFACT_CREATED_IN_FUTURE")
            archived=_archived_shadow(_gh_artifact_zip(
                meta["archive_download_url"],token))
            with sqlite3.connect(db_path) as db:
                db.execute("PRAGMA foreign_keys=ON")
                ensure(db)
                for childid,parentid,created,kick,bytes_sha,aid,eventtime in rows:
                    if not (as_utc(created)<=server<=as_utc(kick)-LEAD
                            and stamp(server)==stamp(as_utc(eventtime))):
                        continue
                    if archived.get(childid)!=(parentid,created,kick,bytes_sha):
                        continue
                    proof={
                        "shadow_sha256":childid,
                        "source_m0_forecast_sha256":parentid,
                        "github_artifact_id":artifact_id,
                        "github_server_artifact_created_utc":stamp(server),
                        "attestation_source":
                          "GITHUB_HOST_ARCHIVED_ORIGINAL_SHADOW_SIX_SQLITE_BYTES",
                        "audited_at_utc":stamp(now)}
                    proofsha=hashobj(proof)
                    db.execute("""INSERT OR IGNORE INTO kb3_p1_shadow_six_host_proofs
                        (proof_sha256,shadow_sha256,source_m0_forecast_sha256,
                        github_artifact_id,github_server_artifact_created_utc,
                        attestation_source,audited_at_utc)
                        VALUES (?,?,?,?,?,?,?)""",
                        (proofsha,childid,parentid,artifact_id,
                         proof["github_server_artifact_created_utc"],
                         proof["attestation_source"],proof["audited_at_utc"]))
                    added+=1
                db.commit()
        except (ValueError,KeyError,TypeError,sqlite3.DatabaseError,
                OSError,zipfile.BadZipFile):
            errors+=1
    with sqlite3.connect(db_path) as db:
        verified=db.execute(
            "SELECT COUNT(*) FROM kb3_p1_shadow_six_host_proofs").fetchone()[0]
    return {"state":"GITHUB_HOST_ARTIFACT_CHECK",
            "new_host_proofs":added,"verified":verified,
            "pending_before_checks":len(pending),
            "artifact_checks":checks,"errors":errors,
            "no_local_timestamp_used_as_proof":True}


def paired_settled_shadow(db_path):
    """Same actual M0 and CBM shadow, settled and both host-verified, or none."""
    with sqlite3.connect(db_path) as db:
        if not _shadow_present(db):
            return {"paired_settled_host_attested":0,
                    "state":"SHADOW_NOT_ENABLED",
                    "official_fit_increment":0}
        ensure(db)
        rows=db.execute("""
          SELECT f.id,f.payload_json,s.outcome,
                 c.id,c.payload_json
          FROM forecasts f
          JOIN settlements s ON s.forecast_id=f.id
          JOIN m0720_github_push_proofs mp ON mp.forecast_id=f.id
          JOIN kb3_p1_shadow_six_new_only c
                 ON c.source_m0_forecast_sha256=f.id
          JOIN kb3_p1_shadow_six_host_proofs pr
                 ON pr.shadow_sha256=c.id
          WHERE mp.source='GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES'
          ORDER BY f.league,f.native_match_id
        """).fetchall()
    parent_probs=[];shadow_probs=[];outcomes=[];ids=set()
    for parentid,pjson,y,shadowid,cjson in rows:
        p=json.loads(pjson);c=json.loads(cjson)
        require(parentid==p["forecast_sha256"] and
                shadowid==c["shadow_sha256"] and
                hashobj({k:v for k,v in p.items() if k!="forecast_sha256"})==parentid and
                hashobj({k:v for k,v in c.items() if k!="shadow_sha256"})==shadowid and
                c["source_m0_forecast_sha256"]==parentid and
                c["feature_sha256"]==p["feature_sha256"],
                "SHADOW_PAIR_HASH_OR_SOURCE_CHANGED")
        require(y in ("1","X","2") and parentid not in ids,
                "SHADOW_PAIR_DUPLICATE_OR_RESULT_INVALID")
        ids.add(parentid)
        prob(p["p_1x2"]);prob(c["p_1x2"])
        parent_probs.append(p["p_1x2"])
        shadow_probs.append(c["p_1x2"])
        outcomes.append(y)
    if not rows:
        return {"paired_settled_host_attested":0,
                "state":"NO_PAIRED_SETTLED_HOST_ATTESTED_MATCHES_YET",
                "official_fit_increment":0}
    return {"paired_settled_host_attested":len(rows),
            "m0_metrics":score_predictions(parent_probs,outcomes),
            "shadow_metrics":score_predictions(shadow_probs,outcomes),
            "descriptive_research_only":True,
            "no_auto_champion":True,
            "official_fit_increment":0}
