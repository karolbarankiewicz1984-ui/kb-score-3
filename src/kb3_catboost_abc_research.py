"""Fixed A/B/C walk-forward experiment and exact-game M0 comparison, no production writes."""
from __future__ import annotations
from collections import Counter
from datetime import timedelta
from pathlib import Path
import json,math
from src.kb3_catboost_research_data import (
    CONTRACT,DOMAIN,SCOPES,STATS,need,digest,_utc,load_sources,examples_from_sources,
)
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING
from src.kb3_step16_m0_720_eight_forward import trained_params
from src.kb3_step13_baseline import forecast
from src.kb3_step17_engine_comparison import paired_ci,prob
from scripts.step14_m1r_train_real_catboost_720_evaluate_374 import _score

PARAMS={'iterations':175,'depth':3,'learning_rate':.035,'l2_leaf_reg':8.0,
        'loss_function':'MultiClass','random_seed':20261103,'thread_count':2,
        'nan_mode':'Min','verbose':False,'allow_writing_files':False}
FOLDS=(('2025-07-01T00:00:00Z','2025-11-01T00:00:00Z'),
       ('2025-11-01T00:00:00Z','2026-02-01T00:00:00Z'),
       ('2026-02-01T00:00:00Z','2026-05-01T00:00:00Z'))
VALIDATION=('2026-05-01T00:00:00Z','2026-11-03T00:00:00Z')
MIN_TRAIN=80;MIN_EVAL=25;MIN_PAIRED=100;MIN_WEEKS=8
M0_CUTOFF='2025-07-01T00:00:00Z'
M0='M0_FIXED720_REPLAY'
VARIANTS=('A','B','C')

def catalog(variant):
    a={'num:'+k for k in EXPECTED_FEATURES if 'xg' not in k.lower()}
    a|={'miss:'+k for k in EXPECTED_MISSING if 'xg' not in k.lower()}
    if variant=='A':return a
    a|={f'{s}_xg5_{f}' for s in ('home','away') for f in ('xg_for','xg_against')}
    if variant=='B':return a
    need(variant=='C','UNKNOWN_VARIANT')
    a|={f'{s}_{f}_{n}' for s in ('home','away') for f in STATS for n in (5,10,15)}
    a|={f'{s}_xg{n}_{f}' for s in ('home','away') for f in ('xg_for','xg_against') for n in (10,15)}
    return a

def key(row):return row['scope'],row['match_id']

def validate_examples(rows):
    need(len({key(r) for r in rows})==len(rows),'DUPLICATE_EXAMPLE')
    need(rows==sorted(rows,key=lambda r:(_utc(r['kickoff_utc']),r['scope'],r['match_id'])),'NOT_CHRONOLOGICAL')
    for r in rows:
        need(r['scope'] in SCOPES and r['y'] in ('1','X','2'),'PROTECTED_SCOPE_OR_LABEL')
        need(r['contract']==CONTRACT and r['availability_class']==DOMAIN and r['original_pit_certified'] is False,'RECONSTRUCTION_CANNOT_BECOME_ORIGINAL_PIT')
        need(_utc(r['feature_cutoff_utc'])<=_utc(r['kickoff_utc'])-timedelta(minutes=90),'LATE_FEATURE_CUTOFF')
        need(digest({k:v for k,v in r.items() if k not in ('y','feature_sha256')})==r['feature_sha256'],'FEATURE_HASH_MISMATCH')
        for v in VARIANTS:
            values=r['features'][v]
            need(set(values)==catalog(v),'UNAPPROVED_FEATURE_SCHEMA')
            need(all(x is None or type(x) in (int,float) and math.isfinite(x) for x in values.values()),'BAD_FEATURE_NUMBER')
        need(all(r['features']['A'][n]==r['features']['B'][n] for n in catalog('A')) and
             all(r['features']['B'][n]==r['features']['C'][n] for n in catalog('B')),'BASE_FEATURE_DRIFT')

def split_window(rows,start,end):
    need(_utc(start)>=_utc(M0_CUTOFF) and _utc(start)<_utc(end),'M0_FIT_NOT_BEFORE_EVALUATION')
    test=[r for r in rows if _utc(start)<=_utc(r['kickoff_utc'])<_utc(end)]
    boundary=min((_utc(r['feature_cutoff_utc']) for r in test),default=_utc(start)-timedelta(minutes=90))
    before=[r for r in rows if _utc(r['kickoff_utc'])<_utc(start)]
    train=[r for r in before if _utc(r['kickoff_utc'])+timedelta(hours=3)<=boundary]
    need(not {key(r) for r in train}&{key(r) for r in test},'PARTITION_OVERLAP')
    if train and test:need(max(_utc(r['kickoff_utc']) for r in train)<min(_utc(r['kickoff_utc']) for r in test),'SPLIT_TIED_KICKOFF')
    return train,test,len(before)-len(train)

def train_columns(train,variant):
    """No validation input is accepted by this selector."""
    return [name for name in sorted(catalog(variant))
            if len({r['features'][variant][name] for r in train})>1
            and any(r['features'][variant][name] is not None for r in train)]

def vector(row,variant,names):
    need(row['contract']==CONTRACT and set(names)<=catalog(variant),'MODEL_CONTRACT_MISMATCH')
    return [float('nan') if row['features'][variant][n] is None else float(row['features'][variant][n]) for n in names]

def scores(rows,engine):
    if not rows:return None
    return _score([r['predictions'][engine]['p_1x2'] for r in rows],[r['outcome_1x2'] for r in rows])

def comparison(rows,left,right):
    n=len(rows);weeks=len({_utc(r['kickoff_utc']).isocalendar()[:2] for r in rows})
    out={'common_n':n,'weeks':weeks,'missing_matches':max(0,MIN_PAIRED-n),
         'missing_weeks':max(0,MIN_WEEKS-weeks),'same_fixture_sample':True}
    out['deltas']={m:paired_ci(rows,left,right,m) for m in ('brier_sum3','log_loss','top1_accuracy')} if rows else {}
    if n<MIN_PAIRED or weeks<MIN_WEEKS:
        out['conclusion']='INCONCLUSIVE_TOO_FEW_MATCHES_OR_WEEKS'
    elif all(out['deltas'][m]['ci95'][1]<0 for m in ('brier_sum3','log_loss')):
        out['conclusion']='BETTER_ON_THIS_RETROSPECTIVE_SAMPLE'
    elif all(out['deltas'][m]['ci95'][0]>0 for m in ('brier_sum3','log_loss')):
        out['conclusion']='WORSE_ON_THIS_RETROSPECTIVE_SAMPLE'
    else:out['conclusion']='NO_CONFIRMED_IMPROVEMENT'
    return out

def coverage(rows):
    return {'n':len(rows),'complete_xg5_both':sum(r['complete_xg5_both'] for r in rows),
            'leagues':dict(sorted(Counter(r['scope'] for r in rows).items())),
            'missing_fraction_by_variant':{v:{name:(sum(r['features'][v][name] is None for r in rows)/len(rows) if rows else None)
                for name in sorted(catalog(v))} for v in VARIANTS}}

def fit_window(train,test,*,model_factory=None,model_dir=None,token='window'):
    from catboost import Pool
    validate_examples(sorted(train+test,key=lambda r:(_utc(r['kickoff_utc']),r['scope'],r['match_id'])))
    need(all(_utc(r['kickoff_utc'])>=_utc(M0_CUTOFF) for r in test),'M0_TRAINING_OVERLAP')
    need(len(train)>=MIN_TRAIN and len(test)>=MIN_EVAL,'TOO_FEW_CHRONOLOGICAL_ROWS')
    need(set(r['y'] for r in train)=={'1','X','2'},'TRAIN_MISSING_OUTCOME_CLASS')
    need(max(_utc(r['kickoff_utc'])+timedelta(hours=3) for r in train)<=min(_utc(r['feature_cutoff_utc']) for r in test),'TRAIN_LABEL_NOT_AVAILABLE')
    params,psha,manifest=trained_params()
    if model_factory is None:
        from catboost import CatBoostClassifier
        model_factory=CatBoostClassifier
    result=[]
    for row in test:
        p=forecast(row['features']['A']['num:home_elo'],row['features']['A']['num:away_elo'],params)['p_1x2']
        result.append({'scope':row['scope'],'fixture_id':row['match_id'],'kickoff_utc':row['kickoff_utc'],
            'feature_cutoff_utc':row['feature_cutoff_utc'],'feature_sha256':row['feature_sha256'],
            'outcome_1x2':row['y'],'complete_xg5_both':row['complete_xg5_both'],
            'predictions':{M0:{'p_1x2':p}}})
    models={}
    for variant in VARIANTS:
        names=train_columns(train,variant);need(len(names)>=5,'INSUFFICIENT_VARIABLE_TRAIN_FEATURES')
        model=model_factory(**PARAMS)
        # Never pass eval_set, validation labels, early stopping or validation-driven selection.
        model.fit(Pool([vector(r,variant,names) for r in train],
                       label=[r['y'] for r in train],feature_names=names))
        classes=[str(c) for c in model.classes_];need(len(classes)==3 and set(classes)=={'1','X','2'},'MODEL_CLASS_ORDER_INVALID')
        predictions=model.predict_proba(Pool([vector(r,variant,names) for r in test],feature_names=names))
        need(len(predictions)==len(test),'MODEL_PREDICTION_COUNT')
        for record,values in zip(result,predictions):
            need(len(values)==3,'MODEL_PREDICTION_SHAPE')
            p={c:float(values[classes.index(c)]) for c in ('1','X','2')};prob(p)
            record['predictions'][variant]={'p_1x2':p}
        models[variant]={'selected_feature_count':len(names),'selected_features':names,
            'xg_columns_selected':[n for n in names if 'xg' in n.lower()],
            'feature_names_sha256':digest(names),'feature_contract':CONTRACT,'classes':classes,
            'train_n':len(train),'fit_labels_last_kickoff':train[-1]['kickoff_utc']}
        if model_dir is not None:
            import hashlib
            path=Path(model_dir)/(token+'_'+variant+'.cbm');need(not path.exists(),'APPEND_ONLY_MODEL_EXISTS')
            path.parent.mkdir(parents=True,exist_ok=True);model.save_model(str(path))
            models[variant]['model_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    metrics={v:scores(result,v) for v in (M0,)+VARIANTS}
    per_league={s:{v:scores([r for r in result if r['scope']==s],v) for v in (M0,)+VARIANTS}
                for s in sorted({r['scope'] for r in result})}
    full=[r for r in result if r['complete_xg5_both']]
    return {'models':models,'metrics':metrics,'per_league':per_league,
        'paired_vs_m0':{v:comparison(result,v,M0) for v in VARIANTS},
        'complete_xg5_sample':{'n':len(full),'metrics':{v:scores(full,v) for v in (M0,)+VARIANTS},
            'B_vs_A':comparison(full,'B','A'),'C_vs_A':comparison(full,'C','A')},
        'M0_parameter_sha256':psha,'M0_manifest_sha256':manifest},result

def experiment(rows,*,fit=False,model_factory=None,model_dir=None):
    validate_examples(rows)
    output={'schema':'kb3-catboost-abc-walkforward-research-v1','feature_contract':CONTRACT,
        'availability_class':DOMAIN,'original_pit_certified':False,'parameters':PARAMS,
        'parameter_selection':'FIXED_BEFORE_FIT_NO_VALIDATION_TUNING','minimums':{'train':MIN_TRAIN,'eval':MIN_EVAL,'paired':MIN_PAIRED,'weeks':MIN_WEEKS},
        'protected_ENG_or_reserved_validation_used':False,'GATE17':'PENDING',
        'production_model_changed':False,'champion_promotion_authorized':False,
        'walk_forward':[],'frozen_forward_comparison':{'common_n':0,'missing_matches':MIN_PAIRED,
            'missing_weeks':MIN_WEEKS,'conclusion':'NO_ORIGINAL_FROZEN_ABC_FORECASTS'},
        'example_manifest_sha256':digest([(r['scope'],r['match_id'],r['feature_sha256']) for r in rows])}
    pooled=[];predictions=[]
    for name,(start,end) in [(f'fold{i}',window) for i,window in enumerate(FOLDS,1)]+[('validation',VALIDATION)]:
        train,test,embargo=split_window(rows,start,end)
        record={'evaluation_start':start,'evaluation_end_exclusive':end,'train_n':len(train),'eval_n':len(test),
            'embargoed_labels':embargo,'train_coverage':coverage(train),'eval_coverage':coverage(test),
            'train_ids_sha256':digest([key(r) for r in train]),'eval_ids_sha256':digest([key(r) for r in test]),
            'train_last_kickoff':train[-1]['kickoff_utc'] if train else None,
            'eval_first_cutoff':test[0]['feature_cutoff_utc'] if test else None}
        if len(train)<MIN_TRAIN or len(test)<MIN_EVAL:
            record.update(status='NO_GO_TOO_FEW_ROWS',missing_train=max(0,MIN_TRAIN-len(train)),missing_eval=max(0,MIN_EVAL-len(test)))
        elif set(r['y'] for r in train)!={'1','X','2'}:
            record.update(status='NO_GO_TRAIN_MISSING_OUTCOME_CLASS',missing_classes=sorted({'1','X','2'}-{r['y'] for r in train}))
        elif not fit:record['status']='PREFLIGHT_ELIGIBLE_UNFITTED'
        else:
            fitted,scored=fit_window(train,test,model_factory=model_factory,model_dir=model_dir,token=name)
            record.update(status='EXECUTED',**fitted)
            predictions.extend(dict(r,partition=name) for r in scored)
            if name!='validation':pooled.extend(scored)
        if name=='validation':
            record['independent_untouched_confirmation']=False
            record['limitation']='RETROSPECTIVE_REUSED_PERIOD_OVERLAPS_PRIOR_PR141'
            output['validation']=record
        else:output['walk_forward'].append(record)
    if pooled:
        need(len({(r['scope'],r['fixture_id']) for r in pooled})==len(pooled),'OVERLAPPING_EVALUATION_FOLDS')
        output['walk_forward_aggregate']={'n':len(pooled),'metrics':{v:scores(pooled,v) for v in (M0,)+VARIANTS},
            'paired_vs_m0':{v:comparison(pooled,v,M0) for v in VARIANTS}}
    output['status']=('EXECUTED_RESEARCH_ONLY' if predictions else 'NO_GO_NO_MODELS_FITTED') if fit else 'PREFLIGHT_ONLY'
    output['report_sha256']=digest(output)
    return output,predictions

def run(path,rechecks=None,*,fit=False,model_dir=None,frozen_db=None):
    from src.kb3_catboost_research_data import file_sha
    fixtures,observed,audit=load_sources(path,rechecks)
    rows,excluded=examples_from_sources(fixtures,observed)
    report,predictions=experiment(rows,fit=fit,model_dir=model_dir)
    report['source']=audit;report['excluded_examples']=excluded
    if frozen_db is not None:
        before_frozen=file_sha(frozen_db)
        report['original_frozen_m0_comparison']=compare_original_m0(frozen_db,[])
        need(file_sha(frozen_db)==before_frozen,'ORIGINAL_FORECAST_SOURCE_CHANGED')
        report['original_frozen_m0_comparison']['source_sha256']=before_frozen
    need(file_sha(path)==audit['source_sha256'],'SOURCE_MUTATED_DURING_FIT')
    if rechecks is not None:need(file_sha(rechecks)==audit['recheck_sha256'],'OVERLAY_MUTATED_DURING_FIT')
    report.pop('report_sha256');report['report_sha256']=digest(report)
    return report,predictions

def compare_original_m0(db_path,challengers,*,attest=None):
    """Pair future original forecasts only; an independent archive validator is mandatory.

    `attest(record)` must authenticate exact original hosted artifact bytes and
    return their payload hash and GitHub server-created clock. This function
    never manufactures attestations or backfills predictions.
    """
    from src.kb3_step16_progressive_shadow import verified_rows
    from src.kb3_catboost_research_data import readonly
    settled={r['id']:r for r in verified_rows(db_path)}
    with readonly(db_path) as db:
        parents={fid:json.loads(raw) for fid,raw in db.execute('SELECT id,payload_json FROM forecasts') if fid in settled}
    merged={};versions={v:set() for v in VARIANTS};seen=set()
    for child in challengers:
        need(callable(attest),'INDEPENDENT_ATTESTATION_VALIDATOR_REQUIRED')
        variant=child['variant'];need(variant in VARIANTS,'UNKNOWN_VARIANT')
        parent_id=child['source_m0_forecast_sha256']
        need((parent_id,variant) not in seen,'DUPLICATE_FROZEN_PREDICTION');seen.add((parent_id,variant))
        need(child['prediction_sha256']==digest({k:v for k,v in child.items() if k!='prediction_sha256'}),'FROZEN_PAYLOAD_CHANGED')
        need(child['availability_class']=='ORIGINAL_FROZEN_PREMATCH' and child['feature_contract']==CONTRACT,'REPLAY_CANNOT_JOIN_ORIGINAL_FREEZE')
        proof=attest(child)
        need(proof.get('archived_payload_sha256')==digest(child)
             and isinstance(proof.get('archive_sha256'),str) and len(proof['archive_sha256'])==64,
             'ORIGINAL_ARTIFACT_BYTES_NOT_ATTESTED')
        if parent_id not in settled:continue
        p=parents[parent_id];row=settled[parent_id]
        need((child['scope'],child['match_id'],child['kickoff_utc'],child['home_team_id'],child['away_team_id'])==
             (p['league_country'],p['provider_match_id'],p['kickoff_utc'],p['home_team_id'],p['away_team_id']),'FROZEN_FIXTURE_IDENTITY_MISMATCH')
        cutoff=_utc(p['feature_cutoff_utc']);ko=_utc(p['kickoff_utc'])
        need(child['feature_cutoff_utc']==p['feature_cutoff_utc'] and
             _utc(child['source_last_observed_utc'])<=cutoff and
             _utc(child['training_data_max_kickoff_utc'])+timedelta(hours=3)<=_utc(child['trained_at_utc'])<=cutoff and
             cutoff<=_utc(child['generated_at_utc'])<=_utc(proof['server_created_utc'])<=ko-timedelta(minutes=90),
             'LATE_MODEL_SOURCE_OR_FORECAST')
        need(isinstance(child['model_version'],str) and len(child['model_version'])>=8 and
             isinstance(child['model_sha256'],str) and len(child['model_sha256'])==64,'UNVERSIONED_MODEL')
        versions[variant].add((child['model_version'],child['model_sha256']))
        need(len(versions[variant])==1,'MIXED_FROZEN_MODEL_VERSIONS')
        prob(child['p_1x2'])
        entry=merged.setdefault(parent_id,{'scope':p['league_country'],'fixture_id':p['provider_match_id'],
            'kickoff_utc':p['kickoff_utc'],'outcome_1x2':row['label'],
            'predictions':{M0:{'p_1x2':row['p']}}})
        entry['predictions'][variant]={'p_1x2':child['p_1x2']}
    out={'availability_class':'ORIGINAL_FROZEN_PREMATCH','verified_settled_M0':len(settled),
         'independent_artifact_validator_required':True,'models':{},'GATE17':'PENDING',
         'production_approved':False}
    for variant in VARIANTS:
        paired=[r for r in merged.values() if variant in r['predictions']]
        comp=comparison(paired,variant,M0)
        comp['conclusion']=comp['conclusion'].replace('RETROSPECTIVE_SAMPLE','ORIGINAL_FROZEN_SAMPLE')
        out['models'][variant]={'metrics':scores(paired,variant),'M0_same_matches':scores(paired,M0),'comparison':comp}
    return out
