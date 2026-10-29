"""Step17 genuine parallel no-refit challengers for newly frozen M0 720-TRAIN fixtures.

ELO ONLY derives 1X2 from PRE-fitted TRAIN draw prior and Elo expected points:
P(draw)=min(train_draw_fraction,2*min(EloExpected,1-EloExpected)*.999),
P(home)=EloExpected-P(draw)/2, P(away)=1-EloExpected-P(draw)/2.
Draw prior is 168/720 from frozen TRAIN only, not 374 validation.
CatBoost M1-R is loaded byte-identically from existing train-720 CBM, with
EXACT 85 feature names and order, no future xG, results or new fit.
Computation is at the *same source receipt cutoff* as original M0 freeze.
The research challengers are never production-approved.
"""
from __future__ import annotations
from datetime import timedelta
import hashlib,json,math,sqlite3
from pathlib import Path
from src.kb3_step13_baseline import elo_expected_home_points
from src.kb3_step16_m0_720_eight_forward import (
    MODEL as M0, ROOT, LEAD, hashobj, require,trained_params,stamp)
from src.kb3_pit_ledger import as_utc
from src.kb3_step17_engine_comparison import prob

ELO="KB3_STEP17_ELO_ONLY_TRAIN720_DRAW_V1"
CAT="KB3_STEP17_CATBOOST_M1R_BASE_TRAIN720_NOXG_V1"
VERSIONS={"ELO_ONLY":ELO,"CATBOOST_NO_XG":CAT}
TRAINED=ROOT/"data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json"
CBM=ROOT/"models/research/M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm"
CBM_SHA="07af285ff9dd45fa13dd54fd5e805270aff469434955cce998b601875f8fdab8"
ELO_DRAW_COUNT=168
ELO_TRAIN_N=720
SCHEMA="""
CREATE TABLE IF NOT EXISTS step17_frozen_challengers (
 challenger_sha256 TEXT PRIMARY KEY,
 source_m0_forecast_sha256 TEXT NOT NULL REFERENCES forecasts(id),
 engine TEXT NOT NULL CHECK(engine IN ('ELO_ONLY','CATBOOST_NO_XG')),
 model_version TEXT NOT NULL,
 model_bytes_sha256 TEXT NOT NULL,
 league TEXT NOT NULL CHECK(league IN ('ESP','ITA','GER','FRA','NED','BEL','TUR','POL')),
 provider_match_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL,
 frozen_at_utc TEXT NOT NULL,
 feature_sha256 TEXT NOT NULL,
 source_sha256 TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 UNIQUE(source_m0_forecast_sha256,engine),
 UNIQUE(engine,league,provider_match_id),
 CHECK(julianday(frozen_at_utc) < julianday(kickoff_utc)-90.0/1440.0)
);
CREATE TRIGGER IF NOT EXISTS step17_challengers_no_update BEFORE UPDATE ON step17_frozen_challengers
 BEGIN SELECT RAISE(ABORT,'STEP17_FROZEN_CHALLENGER_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS step17_challengers_no_delete BEFORE DELETE ON step17_frozen_challengers
 BEGIN SELECT RAISE(ABORT,'STEP17_FROZEN_CHALLENGER_IMMUTABLE'); END;
"""

def frozen_training_meta(root=ROOT):
    audit=json.loads((Path(root)/"data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json").read_text())
    require(audit.get("training")==720 and audit.get("validation")==374
            and audit.get("original_TEST_2026_27_never_requested") is True
            and audit.get("future_actual_PIT_certified") is False
            and audit.get("all_OPTIONAL_xg_and_source_overlay_excluded") is True,
            "CATBOOST_ORIGINAL_TRAINING_AUDIT_CHANGED")
    require(audit.get("training_labels_1X2_counts")=={"1":314,"2":238,"X":168}
            and audit.get("trained_model_sha256")==CBM_SHA
            and audit.get("frozen_feature_count")==85
            and len(audit.get("frozen_feature_names",[]))==85,
            "FROZEN_M1R_MODEL_OR_FEATURE_GATE_CHANGED")
    names=audit["frozen_feature_names"]
    require(len(set(names))==85 and all(n.startswith(("miss:","num:")) and
            not any(n.endswith(e) for e in
             ("_xg_n","_xg_avg","_xga_n","_xga_avg","_xg","_xga"))
             for n in names),"CATBOOST_XG_FEATURE_LEAKAGE")
    return audit,names,hashobj(audit)

def verify_catboost_binary(path=CBM):
    path=Path(path)
    require(path.is_file(),"CATBOOST_FITTED_BINARY_UNAVAILABLE")
    require(hashlib.sha256(path.read_bytes()).hexdigest()==CBM_SHA,
            "CATBOOST_BINARY_SHA_NOT_MATCH_TRAIN720")
    return CBM_SHA

def vector_of_frozen_features(features,names):
    require(features.get("training_allowed") is False
            and features.get("availability_class")=="OBSERVED_AT_NOT_CERTIFIED",
            "NOT_REAL_OBSERVED_PREMATCH_FEATURES")
    numeric=features.get("features");missing=features.get("missing_flags")
    require(isinstance(numeric,dict) and isinstance(missing,dict),
            "SOURCE_FEATURES_NOT_AVAILABLE")
    result=[]
    for name in names:
        kind,key=name.split(":",1)
        present=(numeric if kind=="num" else missing)
        require(key in present,"M1R_TRAIN_FEATURE_NOT_IN_FORWARD_"+key)
        value=present[key]
        if value is None:
            result.append(float("nan"))
        else:
            require(type(value) in (bool,int,float) and math.isfinite(value),
                    "M1R_INVALID_FLOAT_"+key)
            result.append(float(value))
    require(len(result)==85,"CATBOOST_NOT_85_TRAIN_ONLY")
    return result

def elo_only_probabilities(elo_h,elo_a,parameters):
    expected=elo_expected_home_points(elo_h,elo_a,parameters)
    draw=min(ELO_DRAW_COUNT/ELO_TRAIN_N,2*min(expected,1-expected)*0.999)
    p={"1":expected-draw/2,"X":draw,"2":1-expected-draw/2}
    prob(p)
    require(abs((p["1"]+0.5*p["X"])-expected)<1e-12,
            "ELO_EXPECTED_POINTS_NOT_PRESERVED")
    return p

class Challengers:
    def __init__(self,*,root=ROOT,catboost_model=None):
        self.root=Path(root)
        self.params,self.params_sha,self.m0_manifest_sha=trained_params(self.root)
        audit,self.names,self.audit_sha=frozen_training_meta(self.root)
        self.cbm_sha=verify_catboost_binary(
            self.root/"models/research/M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm")
        if catboost_model is None:
            from catboost import CatBoostClassifier
            clf=CatBoostClassifier()
            clf.load_model(str(self.root/"models/research/M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm"))
            self.catboost=clf
        else:
            self.catboost=catboost_model
        classes=[str(x) for x in self.catboost.classes_]
        require(len(classes)==3 and set(classes)=={"1","X","2"},"CATBOOST_CLASS_ORDER_CHANGED")
        names=list(self.catboost.feature_names_)
        require(names==self.names,"CATBOOST_BINARY_FEATURE_SCHEMA_DRIFT")
        self.class_order=classes
    def records(self,feature_state,parent):
        require(parent["model_version"]==M0
                and parent["params_sha256"]==self.params_sha
                and parent["manifest_sha256"]==self.m0_manifest_sha,
                "NO_SAME_MODEL_M0_SOURCE_PARENT")
        require(parent["feature_sha256"]==feature_state["sha256"]
                and parent["generated_at_utc"]==parent["feature_cutoff_utc"]
                and as_utc(parent["generated_at_utc"])<=
                    as_utc(parent["kickoff_utc"])-LEAD,
                "CHALLENGERS_NOT_SAME_PREMATCH_AS_M0")
        row=vector_of_frozen_features(feature_state,self.names)
        raw=self.catboost.predict_proba([row])
        require(len(raw)==1 and len(raw[0])==3,"CATBOOST_1X2_SHAPE_CHANGED")
        cp={c:float(raw[0][self.class_order.index(c)]) for c in ("1","X","2")}
        prob(cp)
        ep=elo_only_probabilities(parent["elo_home"],parent["elo_away"],self.params)
        common={"source_m0_forecast_sha256":parent["forecast_sha256"],
                "league_country":parent["league_country"],
                "provider_match_id":parent["provider_match_id"],
                "kickoff_utc":parent["kickoff_utc"],
                "frozen_at_utc":parent["generated_at_utc"],
                "source_chain_sha256":parent["source_chain_sha256"],
                "feature_sha256":feature_state["sha256"],
                "phase":"EARLY",
                "horizon":"EARLY_90MIN_OR_MORE",
                "source_class":"NETWORK_OBSERVED_PROVIDER_FIRST_PUBLICATION_UNPROVEN",
                "independent_github_host_artifact_verified_at_creation":False,
                "target_result_used":False,"production_approved":False}
        out=[]
        for engine,version,pred,bytes_sha in (
            ("ELO_ONLY",ELO,ep,self.params_sha),
            ("CATBOOST_NO_XG",CAT,cp,self.cbm_sha)):
            item={**common,"engine":engine,"model_version":version,
                  "model_bytes_sha256":bytes_sha,"p_1x2":pred,
                  "training_fixtures":720,"historical_native_PIT_certified":False,
                  "missing_xg_explicit":engine=="CATBOOST_NO_XG"}
            item["challenger_sha256"]=hashobj(item)
            out.append(item)
        return out

def freeze_new_challengers(db_path,records,*,new_m0_ids):
    """Append challengers *only* for M0 forecasts first frozen THIS RUN.
    NEVER backfill earlier matches with retrospectively computed challenger P.
    """
    new_m0_ids=set(new_m0_ids)
    require(len(records)==len({(r["source_m0_forecast_sha256"],r["engine"]) for r in records}),
            "CHALLENGER_DUPLICATE_ROWS")
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA)
        added=0;skipped=0;groups={}
        for row in records:
            sha=row["challenger_sha256"]
            require(sha==hashobj({k:v for k,v in row.items() if k!="challenger_sha256"}),
                    "CHALLENGER_IMMUTABLE_SHA_INVALID")
            require(row["engine"] in VERSIONS and row["model_version"]==VERSIONS[row["engine"]]
                    and row["phase"]=="EARLY" and row["production_approved"] is False,
                    "INVALID_STEP17_MODEL_POLICY")
            prob(row["p_1x2"])
            parent=row["source_m0_forecast_sha256"]
            if parent not in new_m0_ids:
                skipped+=1;continue
            p=db.execute("""SELECT league,native_match_id,kickoff_utc,captured_at_utc,
                         params_sha256,payload_json FROM forecasts WHERE id=?""",(parent,)).fetchone()
            require(p is not None,"STEP17_NO_ORIGINAL_M0_PARENT")
            league,mid,kick,created,params,payload=p
            item=json.loads(payload)
            require(item["forecast_sha256"]==parent and
                    hashobj({k:v for k,v in item.items() if k!="forecast_sha256"})==parent
                    and item["feature_sha256"]==row["feature_sha256"]
                    and item["source_chain_sha256"]==row["source_chain_sha256"]
                    and item["params_sha256"]==params
                    and (league,mid,kick,created)==(
                    row["league_country"],row["provider_match_id"],
                    row["kickoff_utc"],row["frozen_at_utc"]),
                    "STEP17_PARENT_OR_SOURCE_DRIFT")
            require(as_utc(created)<=as_utc(kick)-LEAD,"CHALLENGER_LATE_FREEZE")
            groups.setdefault(parent,set()).add(row["engine"])
            db.execute("""INSERT INTO step17_frozen_challengers(
                challenger_sha256,source_m0_forecast_sha256,engine,model_version,
                model_bytes_sha256,league,provider_match_id,kickoff_utc,frozen_at_utc,
                feature_sha256,source_sha256,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sha,parent,row["engine"],row["model_version"],row["model_bytes_sha256"],
                 league,mid,kick,created,row["feature_sha256"],row["source_chain_sha256"],
                 json.dumps(row,sort_keys=True,allow_nan=False)))
            added+=1
        require(all(e==set(VERSIONS) for e in groups.values()),"INCOMPLETE_ELO_CATBOOST_MATCH_PAIR")
        require(db.execute("PRAGMA foreign_key_check").fetchall()==[],
                "CHALLENGER_PARENT_SQLITE_FOREIGN_KEY_DRIFT")
        db.commit()
        total=db.execute("SELECT COUNT(*) FROM step17_frozen_challengers").fetchone()[0]
    return {"new_challengers":added,"total_challengers":total,
            "new_common_fixture_pairs":len(groups),"old_m0_not_backfilled":skipped,
            "trained_720_model_sha256":self_cmb_sha()}

def self_cmb_sha():
    return CBM_SHA
