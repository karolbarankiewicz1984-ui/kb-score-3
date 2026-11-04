"""Research-only prospective CatBoost shadow scorer for NEW M0 capture moments.

No M0 write/parameter change; separate immutable shadow table. The only legal
scoring point is the ORIGINAL live feature_state during a NEW M0 forecast run.
Never reconstruct after kickoff or invent attestation of historical/publication
clocks. Requires exact research 6-field CatBoost bytes & immutable manifest.
Not wired into a scheduled production workflow by this file.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import hashlib,json,math,sqlite3
from pathlib import Path

from src.kb3_step16_m0_720_eight_forward import (
    MODEL as M0,LEAD,hashobj,require,stamp
)
from src.kb3_pit_ledger import as_utc
from scripts.kb3_p1_prospective_six_train import (
    CONTRACT,MODEL,FORWARD_KEYS
)
from src.kb3_step17_engine_comparison import prob
from scripts.kb3_p1_historical_eligibility_split import hash_json

SCHEMA_VERSION="kb3-catboost-prospective-six-shadow-v1"
MAX_CAPTURE_DELAY=timedelta(minutes=45)
DB_SCHEMA="""
CREATE TABLE IF NOT EXISTS kb3_p1_shadow_six_new_only (
 id TEXT PRIMARY KEY,
 source_m0_forecast_sha256 TEXT NOT NULL REFERENCES forecasts(id),
 model_version TEXT NOT NULL,
 model_bytes_sha256 TEXT NOT NULL,
 manifest_sha256 TEXT NOT NULL,
 league TEXT NOT NULL CHECK(league IN ('ESP','ITA','GER','FRA','NED','BEL','TUR','POL')),
 native_match_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL,
 original_feature_cutoff_utc TEXT NOT NULL,
 shadow_generated_at_utc TEXT NOT NULL,
 feature_sha256 TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 UNIQUE(source_m0_forecast_sha256,model_version),
 UNIQUE(league,native_match_id,model_version),
 CHECK(julianday(shadow_generated_at_utc)<julianday(kickoff_utc)-90.0/1440.0)
);
CREATE TRIGGER IF NOT EXISTS kb3_p1_six_no_update
 BEFORE UPDATE ON kb3_p1_shadow_six_new_only
 BEGIN SELECT RAISE(ABORT,'KB3_SHADOW_SIX_IMMUTABLE_UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS kb3_p1_six_no_delete
 BEFORE DELETE ON kb3_p1_shadow_six_new_only
 BEGIN SELECT RAISE(ABORT,'KB3_SHADOW_SIX_IMMUTABLE_DELETE'); END;
"""


class ShadowSafetyError(ValueError):pass
def need(ok,reason):
    if not ok:raise ShadowSafetyError(reason)


def make_vector(feature_state):
    need(isinstance(feature_state,dict) and
         feature_state.get("availability_class")=="OBSERVED_AT_NOT_CERTIFIED"
         and feature_state.get("row_payload_at_snapshot_proven") is True
         and feature_state.get("target_prematch_snapshot_certified") is False
         and feature_state.get("training_allowed") is False,
         "UNVERIFIED_OR_RECONSTRUCTED_FORWARD_FEATURES")
    view=feature_state.get("features")
    need(isinstance(view,dict) and
         feature_state.get("feature_availability") is not None
         and feature_state.get("source_evidence") is not None,
         "SOURCE_RECEIPTS_NOT_IN_FORWARD_FEATURES")
    need(view.get("home_all_5_n")==5 and view.get("away_all_5_n")==5
         and feature_state.get("accepted_predecessor_count",0)>=5,
         "MISSING_LAST5_HISTORY")
    vals=[]
    for key in FORWARD_KEYS:
        v=view.get(key)
        need(type(v) in (int,float) and math.isfinite(v),
             "SIX_FORWARD_REAL_GOAL_FORM_FEATURE_UNAVAILABLE:"+key)
        vals.append(float(v))
    need(len(vals)==6,"SIX_FEATURE_SHAPE_DRIFT")
    # These are the only six values model is allowed to receive.
    return vals


def check_model_manifest(manifest,binary_path,clf=None):
    need(isinstance(manifest,dict) and
         manifest.get("schema")==CONTRACT and
         manifest.get("model_version")==MODEL and
         manifest.get("feature_names")==list(FORWARD_KEYS)
         and manifest.get("source_reconstructed_feature_names") ==
             [f"{s}_{n}" for s in ("home","away")
              for n in ("goals_for","goals_against","points")]
         and manifest.get("training_rows")==1007 and
         manifest.get("validation_rows")==376 and
         manifest.get("features_count")==6 and
         manifest.get("production_approved") is False and
         manifest.get("formal_asof_v2_trained") is False and
         manifest.get("trained_on_reconstructed_history") is True,
         "UNEXPECTED_MODEL_MANIFEST_OR_FALSE_PIT")
    canonical={k:v for k,v in manifest.items() if k!="manifest_sha256"}
    need(hash_json(canonical)==manifest.get("manifest_sha256"),
         "MANIFEST_IMMUTABLE_HASH_INVALID")
    binary_path=Path(binary_path)
    need(binary_path.is_file(),"SHADOW_MODEL_BINARY_NOT_FOUND")
    digest=hashlib.sha256(binary_path.read_bytes()).hexdigest()
    need(digest==manifest.get("model_binary_sha256"),
         "SHADOW_MODEL_BYTES_NOT_PINNED")
    if clf is None:
        from catboost import CatBoostClassifier
        clf=CatBoostClassifier()
        clf.load_model(str(binary_path))
    need(list(clf.feature_names_)==list(FORWARD_KEYS) and
         set(map(str,clf.classes_))=={"1","X","2"},
         "CATBOOST_BINARY_FEATURES_OR_CLASS_LABELS_MISMATCH")
    return clf,digest


class ShadowSix:
    def __init__(self,*,manifest_file,model_file,clock=None):
        self.manifest=json.loads(Path(manifest_file).read_text())
        self.model,self.model_sha=check_model_manifest(
            self.manifest,model_file)
        self.class_order=[str(v) for v in self.model.classes_]
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def records(self,feature_state,parent):
        """For direct use as an engine on NEW in-memory M0 feature snapshots.

        A record is an UNATTESTED candidate until the original shadow SQLITE
        bytes have a separately verified GitHub server-created artifact.
        """
        need(isinstance(parent,dict) and
             parent.get("model_version")==M0 and
             parent.get("production_approved") is False and
             parent.get("training_allowed") is False and
             parent.get("phase")=="EARLY" and
             parent.get("forecast_sha256")==hashobj({
                 k:v for k,v in parent.items() if k!="forecast_sha256"}),
             "NOT_ORIGINAL_IMMUTABLE_RESEARCH_M0_PARENT")
        cutoff=as_utc(parent["feature_cutoff_utc"])
        ko=as_utc(parent["kickoff_utc"])
        observed=self.clock()
        need(observed.utcoffset()==timedelta(0),
             "HOST_UTC_CLOCK_REQUIRED")
        need(parent["generated_at_utc"]==parent["feature_cutoff_utc"]
             and feature_state.get("feature_cutoff_utc")==parent["feature_cutoff_utc"]
             and feature_state.get("kickoff_utc")==parent["kickoff_utc"]
             and feature_state.get("fixture_id")==parent["provider_match_id"]
             and parent["feature_sha256"]==feature_state.get("sha256"),
             "M0_FEATURE_AND_ASOF_DRIFT")
        need(cutoff<=observed<=cutoff+MAX_CAPTURE_DELAY and
             observed < ko-LEAD,
             "SHADOW_NOT_GENERATED_WITH_NEW_EARLY_PARENT")
        values=make_vector(feature_state)
        result=self.model.predict_proba([values])
        need(len(result)==1 and len(result[0])==3,
             "NOT_1X2_PROBABILITY_VECTOR")
        pred={k:float(result[0][self.class_order.index(k)])
              for k in ("1","X","2")}
        prob(pred)
        record={
          "schema":SCHEMA_VERSION,"engine":"CATBOOST_SHADOW_SIX",
          "model_version":MODEL,
          "model_bytes_sha256":self.model_sha,
          "model_manifest_sha256":self.manifest["manifest_sha256"],
          "source_m0_forecast_sha256":parent["forecast_sha256"],
          "league_country":parent["league_country"],
          "provider_match_id":parent["provider_match_id"],
          "kickoff_utc":parent["kickoff_utc"],
          "original_feature_cutoff_utc":parent["feature_cutoff_utc"],
          "shadow_generated_at_utc":stamp(observed),
          "source_chain_sha256":parent["source_chain_sha256"],
          "feature_sha256":parent["feature_sha256"],
          "six_feature_values_sha256":hashobj({
               "feature_names":list(FORWARD_KEYS),"values":values}),
          "p_1x2":pred,
          "target_result_used":False,
          "source_class":"NETWORK_OBSERVED_PROVIDER_FIRST_PUBLICATION_UNPROVEN",
          "model_history_original_pit_certified":False,
          "shadow_host_artifact_verified":False,
          "research_only":True,"official_fit_eligible":False,
          "production_approved":False,
          "gate16":"PENDING","gate17":"PENDING",
        }
        record["shadow_sha256"]=hashobj(record)
        return [record]


def freeze_only_new_m0(db_path,records,*,new_m0_ids):
    """Append separate shadow rows; verify EXACT newly inserted M0 parents.

    Store in the SAME *staging* SQLite as M0 for later bytes+host artifact
    provenance, but never modify its forecast, settlement or step17 tables.
    Existing pre-match M0 rows can NEVER acquire a shadow prediction by replay.
    """
    need(isinstance(new_m0_ids,set),"SET_OF_NEW_M0_PARENT_IDS_REQUIRED")
    need(len(records)==len({r["source_m0_forecast_sha256"] for r in records}),
         "DUPLICATE_SHADOW_PARENTS")
    appended=skipped=0
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(DB_SCHEMA)
        for r in records:
            need(r.get("shadow_sha256")==hashobj({
                k:v for k,v in r.items() if k!="shadow_sha256"})
                and r["schema"]==SCHEMA_VERSION
                and r["model_version"]==MODEL
                and r["research_only"] is True
                and r["production_approved"] is False
                and r["official_fit_eligible"] is False
                and r["shadow_host_artifact_verified"] is False,
                "TAMPERED_OR_PROMOTED_SHADOW_ROW")
            parentid=r["source_m0_forecast_sha256"]
            if parentid not in new_m0_ids:
                skipped+=1
                continue
            old=db.execute("""SELECT league,native_match_id,kickoff_utc,
                      captured_at_utc,source_chain_sha256,payload_json
                      FROM forecasts WHERE id=?""",(parentid,)).fetchone()
            need(old is not None,"PARENT_M0_NOT_PRESENT")
            league,mid,kick,cutoff,chain,raw=old
            p=json.loads(raw)
            need(p["forecast_sha256"]==parentid and
                 hashobj({k:v for k,v in p.items() if k!="forecast_sha256"})==parentid,
                 "M0_PARENT_BYTES_HASH_INVALID")
            need((league,mid,kick,cutoff,chain,p["feature_sha256"]) == (
                 r["league_country"],r["provider_match_id"],r["kickoff_utc"],
                 r["original_feature_cutoff_utc"],r["source_chain_sha256"],
                 r["feature_sha256"]), "M0_PARENT_IDENTITY_OR_FEATURE_DRIFT")
            need(as_utc(r["shadow_generated_at_utc"]) < as_utc(kick)-LEAD
                 and as_utc(cutoff)<=as_utc(r["shadow_generated_at_utc"]),
                 "NOT_TRUE_EARLY_NEW_SHADOW")
            db.execute("""INSERT INTO kb3_p1_shadow_six_new_only(
                   id,source_m0_forecast_sha256,model_version,
                   model_bytes_sha256,manifest_sha256,league,native_match_id,
                   kickoff_utc,original_feature_cutoff_utc,shadow_generated_at_utc,
                   feature_sha256,payload_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (r["shadow_sha256"],parentid,MODEL,r["model_bytes_sha256"],
                  r["model_manifest_sha256"],league,mid,kick,cutoff,
                  r["shadow_generated_at_utc"],r["feature_sha256"],
                  json.dumps(r,sort_keys=True,allow_nan=False)))
            appended+=1
        need(db.execute("PRAGMA foreign_key_check").fetchall()==[],
             "SHADOW_PARENT_FOREIGN_KEY_FAILURE")
        db.commit()
        total=db.execute("SELECT COUNT(*) FROM kb3_p1_shadow_six_new_only").fetchone()[0]
    return {"added":appended,"total":total,"skipped_old_m0":skipped,
            "host_verified":0,"official_fit_increment":0,
            "research_only":True}
