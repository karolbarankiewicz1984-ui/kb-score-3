"""Read-only, version-separated comparison of genuine frozen 1X2 forecasts.

Uses existing score_predictions and paired ISO-week bootstrap. Each pair and
all-model intersection has its own cohort SHA; no marginal-score comparison.
The ledger adapter consumes existing audited host proofs, never creates proofs.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import json
import sqlite3

from src.kb3_features import digest
from src.kb3_p1_shared_asof_features_v2 import need, when, MIN_LEAD, RESULT_MIN_LAG, LEAGUES
from src.kb3_step17_engine_comparison import paired_ci, loss, LABELS
from src.kb3_step14_m1_math_calibration import score_predictions
from src.kb3_step16_m0_720_eight_forward import MODEL as M0
from src.kb3_step17_forward_challengers import ELO, CAT, CBM_SHA, hashobj
from scripts.kb3_p1_prospective_six_train import MODEL as SIX
from scripts.kb3_shadow_first_real_checkpoint import PIN_SHA
from src.kb3_catboost_research_v3 import MODEL as NEW, file_sha

VERSIONS = {'M0':M0, 'ELO_ONLY':ELO, 'CATBOOST_M1R':CAT,
            'CATBOOST_SHADOW_SIX':SIX, 'CATBOOST_ASOF_V3':NEW}


def _hashed(row, key, expected=None):
    need(row.get(key)==hashobj({k:v for k,v in row.items() if k!=key}),
         'IMMUTABLE_RECORD_SHA_MISMATCH:'+key)
    if expected is not None: need(row[key]==expected, 'RECORD_IDENTITY_DRIFT')


def _proof(row, hashkey, source, generated, kickoff):
    _hashed(row,hashkey)
    sourcekey = 'source' if hashkey=='proof_id' else 'attestation_source'
    need(row[sourcekey]==source, 'UNTRUSTED_HOST_PROOF_SOURCE')
    clock = row.get('github_server_event_utc',row.get('github_server_artifact_created_utc'))
    need(when(generated)<=when(clock)<=when(kickoff)-MIN_LEAD, 'LATE_HOST_PROOF')
    audited = row.get('audit_utc',row.get('audited_at_utc'))
    need(when(clock)<=when(audited), 'HOST_PROOF_AUDITED_BEFORE_CREATION')


def ledger_games(path):
    """Immutable offline snapshot only. Refuses WAL sidecars and checks all FKs."""
    path=Path(path).resolve()
    need(path.is_file(), 'FROZEN_LEDGER_MISSING')
    need(not Path(str(path)+'-wal').exists(), 'OFFLINE_SQLITE_SNAPSHOT_REQUIRED')
    before=file_sha(path)
    games=[]
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        need([r[0] for r in db.execute('PRAGMA integrity_check')]==['ok'], 'SQLITE_INTEGRITY_FAILED')
        need(not db.execute('PRAGMA foreign_key_check').fetchall(), 'SQLITE_FOREIGN_KEYS_FAILED')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def rows(table):
            return [dict(r) for r in db.execute('SELECT * FROM '+table)] if table in tables else []
        m0proof={r['forecast_id']:r for r in rows('m0720_github_push_proofs')}
        settled={r['forecast_id']:r for r in rows('settlements')}
        children=defaultdict(list)
        for r in rows('step17_frozen_challengers'):children[r['source_m0_forecast_sha256']].append(r)
        proofs={r['challenger_sha256']:r for r in rows('step17_challenger_host_proofs')}
        six=defaultdict(list)
        for r in rows('kb3_p1_shadow_six_new_only'):six[r['source_m0_forecast_sha256']].append(r)
        sixproof={r['shadow_sha256']:r for r in rows('kb3_p1_shadow_six_host_proofs')}
        for f in rows('forecasts'):
            fid=f['id']
            if fid not in m0proof or fid not in settled:continue
            p=json.loads(f['payload_json']);mp=m0proof[fid];s=settled[fid]
            _hashed(p,'forecast_sha256',fid)
            need(p['model_version']==M0 and f['model']==M0 and
                 (f['league'],f['native_match_id'],f['kickoff_utc'],f['captured_at_utc'])==
                 (p['league_country'],p['provider_match_id'],p['kickoff_utc'],p['feature_cutoff_utc']),
                 'M0_IDENTITY_OR_VERSION_DRIFT')
            need(mp['forecast_id']==mp['original_forecast_sha256']==fid and mp['model']==M0,
                 'M0_HOST_PROOF_IDENTITY_DRIFT')
            _proof(mp,'proof_id','GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES',
                   p['generated_at_utc'],p['kickoff_utc'])
            need((s['league'],s['native_match_id'])==(f['league'],f['native_match_id']), 'SETTLEMENT_IDENTITY_DRIFT')
            y='1' if s['score_home']>s['score_away'] else 'X' if s['score_home']==s['score_away'] else '2'
            need(all(type(s[k]) is int and 0<=s[k]<=30 for k in ('score_home','score_away')),
                 'INVALID_SETTLEMENT_SCORE')
            original_settlement={
                'forecast_id':fid,'league':s['league'],'native_match_id':s['native_match_id'],
                'score_home':s['score_home'],'score_away':s['score_away'],'outcome':s['outcome'],
                'observed_utc':s['observed_utc'],'source_chain_sha256':s['provider_source_chain_sha256'],
                'log_loss':s['log_loss'],'brier_sum3':s['brier_sum3']}
            need(hashobj(original_settlement)==s['settlement_sha256'],'SETTLEMENT_SHA_MISMATCH')
            need(y==s['outcome'] and when(s['observed_utc'])>=when(f['kickoff_utc'])+RESULT_MIN_LAG,
                 'SETTLEMENT_SCORE_OR_TIME_DRIFT')
            ll,bs,_=loss(p['p_1x2'],y)
            need(abs(ll-s['log_loss'])<1e-9 and abs(bs-s['brier_sum3'])<1e-9,'SETTLEMENT_METRIC_DRIFT')
            rec=dict(fixture_id=f['native_match_id'],league=f['league'],kickoff_utc=f['kickoff_utc'],
                     outcome_1x2=y,result_observed_utc=s['observed_utc'],predictions={})
            def add(name,child,sha,generated,feature,source):
                need(name not in rec['predictions'], 'DUPLICATE_MODEL_FIXTURE')
                need(feature==p['feature_sha256'] and source==p['source_chain_sha256'], 'PARENT_SOURCE_DRIFT')
                rec['predictions'][name]=dict(model_version=VERSIONS[name],p_1x2=child['p_1x2'],
                    forecast_sha256=sha,feature_cutoff_utc=p['feature_cutoff_utc'],frozen_at_utc=generated,
                    github_server_artifact_verified=True,forecast_hash_verified=True,
                    horizon='EARLY_90MIN_OR_MORE')
            add('M0',p,fid,p['generated_at_utc'],p['feature_sha256'],p['source_chain_sha256'])
            for c in children[fid]:
                cid=c['challenger_sha256']
                if cid not in proofs:continue
                child=json.loads(c['payload_json']);pr=proofs[cid]
                _hashed(child,'challenger_sha256',cid)
                name={'ELO_ONLY':'ELO_ONLY','CATBOOST_NO_XG':'CATBOOST_M1R'}[c['engine']]
                need(c['model_version']==child['model_version']==pr['model_version']==VERSIONS[name]
                     and c['source_m0_forecast_sha256']==child['source_m0_forecast_sha256']==pr['source_m0_forecast_sha256']==fid
                     and (child['league_country'],child['provider_match_id'],child['kickoff_utc'])==
                     (p['league_country'],p['provider_match_id'],p['kickoff_utc']), 'CHALLENGER_VERSION_OR_PARENT_DRIFT')
                need(name!='CATBOOST_M1R' or child['model_bytes_sha256']==CBM_SHA,'M1R_BYTES_DRIFT')
                _proof(pr,'proof_sha256','GITHUB_HOST_ARTIFACT_ARCHIVED_EXACT_ORIGINAL_CHALLENGER_SQLITE',
                       child['frozen_at_utc'],p['kickoff_utc'])
                add(name,child,cid,child['frozen_at_utc'],child['feature_sha256'],child['source_chain_sha256'])
            for c in six[fid]:
                cid=c['id']
                if cid not in sixproof:continue
                child=json.loads(c['payload_json']);pr=sixproof[cid]
                _hashed(child,'shadow_sha256',cid)
                need(child['model_version']==c['model_version']==SIX and child['model_bytes_sha256']==PIN_SHA
                     and child['source_m0_forecast_sha256']==pr['source_m0_forecast_sha256']==fid
                     and child['original_feature_cutoff_utc']==p['feature_cutoff_utc']
                     and (child['league_country'],child['provider_match_id'],child['kickoff_utc'])==
                     (p['league_country'],p['provider_match_id'],p['kickoff_utc']), 'SIX_VERSION_OR_PARENT_DRIFT')
                _proof(pr,'proof_sha256','GITHUB_HOST_ARCHIVED_ORIGINAL_SHADOW_SIX_SQLITE_BYTES',
                       child['shadow_generated_at_utc'],p['kickoff_utc'])
                add('CATBOOST_SHADOW_SIX',child,cid,child['shadow_generated_at_utc'],child['feature_sha256'],child['source_chain_sha256'])
            games.append(rec)
    need(file_sha(path)==before,'SOURCE_LEDGER_CHANGED')
    return games,dict(sqlite_sha256=before,integrity_check='ok',foreign_key_check=[],
                      source_unchanged=True,existing_audited_host_proofs=True)


def scores(rows, name):
    if not rows:return None
    result=score_predictions([r['predictions'][name]['p_1x2'] for r in rows],
                             [r['outcome_1x2'] for r in rows])
    reliability={}
    for label in LABELS:
        bins=defaultdict(list)
        for r in rows:
            p=r['predictions'][name]['p_1x2'][label]
            bins[min(9,int(p*10))].append((p,int(r['outcome_1x2']==label)))
        reliability[label]=[dict(bin=b,n=len(vals),mean_probability=sum(x[0] for x in vals)/len(vals),
            observed_frequency=sum(x[1] for x in vals)/len(vals)) for b,vals in sorted(bins.items())]
    return {**result,'classwise_reliability_10bins':reliability}


def compare_games(games, versions=None, replicates=1200):
    versions=VERSIONS if versions is None else versions
    need(versions and all(isinstance(v,str) and v for v in versions.values()),'VERSION_REGISTRY_REQUIRED')
    seen=set()
    for row in games:
        ident=(row['league'],row['fixture_id'])
        need(ident not in seen and row['league'] in LEAGUES,'DUPLICATE_OR_PROTECTED_FIXTURE')
        seen.add(ident)
        need(when(row['result_observed_utc'])>=when(row['kickoff_utc'])+RESULT_MIN_LAG,'RESULT_NOT_POSTMATCH')
        need(set(row['predictions'])<=set(versions),'UNKNOWN_MODEL')
        cutoffs=set()
        for name,p in row['predictions'].items():
            need(p['model_version']==versions[name], 'MIXED_MODEL_VERSIONS')
            need(p.get('github_server_artifact_verified') is True and
                 p.get('forecast_hash_verified') is True,'UNATTESTED_FORWARD_PREDICTION')
            need(p.get('horizon')=='EARLY_90MIN_OR_MORE','MIXED_HORIZONS')
            from src.kb3_step17_engine_comparison import prob
            prob(p['p_1x2'])
            cutoff=when(p['feature_cutoff_utc']);frozen=when(p['frozen_at_utc'])
            need(cutoff<=frozen<=when(row['kickoff_utc'])-MIN_LEAD,'LATE_OR_PRE_CUTOFF_FORECAST')
            cutoffs.add(cutoff)
        need(len(cutoffs)<=1,'DIFFERENT_FEATURE_CUTOFFS_FOR_SAME_FIXTURE')
    def cohort(rows):
        return digest(sorted((r['league'],r['fixture_id']) for r in rows))
    def summary(rows,names):
        return dict(common_n=len(rows),cohort_sha256=cohort(rows),
            scores={e:scores(rows,e) for e in names},
            per_league={league:{e:scores([r for r in rows if r['league']==league],e) for e in names}
                        for league in sorted({r['league'] for r in rows})})
    pairs={}
    for left,right in combinations(versions,2):
        rows=[r for r in games if left in r['predictions'] and right in r['predictions']]
        deltas={}
        for metric in ('top1_accuracy','brier_sum3','log_loss'):
            ci=paired_ci(rows,left,right,metric,replicates=replicates) if rows else dict(ci95=None,status='NO_COMMON_FORECASTS')
            delta=(scores(rows,left)[metric]-scores(rows,right)[metric]) if rows else None
            deltas[metric]={**ci,'delta_left_minus_right':delta}
        deltas['top1_ece_10bins']=dict(
            delta_left_minus_right=(scores(rows,left)['top1_ece_10bins']-
                                   scores(rows,right)['top1_ece_10bins']) if rows else None,
            ci95=None,status='DESCRIPTIVE_CALIBRATION_DIFFERENCE')
        pairs[left+'__vs__'+right]={**summary(rows,(left,right)),'paired_deltas':deltas}
    common=[r for r in games if set(r['predictions'])==set(versions)]
    available=[e for e in versions if any(e in r['predictions'] for r in games)]
    current=[r for r in games if all(e in r['predictions'] for e in available)] if available else []
    return dict(schema='kb3-frozen-model-comparison-v3',model_versions=versions,
        model_limitations={'CATBOOST_M1R':'Historical 48h vs forward 3h; TRAIN/FORWARD semantics unproven',
            'CATBOOST_SHADOW_SIX':'6 features; trained on reconstructed history, original historical PIT unproven',
            'CATBOOST_ASOF_V3':'New research version; requires admitted training and genuinely archived future forecasts'},
        input_sha256=digest(games),all_registered_models=summary(common,versions),
        available_model_intersection=summary(current,available),
        coverage={e:sum(e in r['predictions'] for r in games) for e in versions},
        pairwise=pairs,uncertainty='paired whole ISO-week bootstrap, >=8 weeks; serial/team dependence may persist across weeks',
        research_only=True,champion_changed=False,new_catboost_improves='NOT_ESTABLISHED')


def add_v3_frozen_games(games, samples, archives, directory, expected_manifest_sha256):
    """Optional future V3 input, independent archive verification, no scoring/backfill."""
    from src.kb3_catboost_research_v3 import load_model, verified_frozen_forecast
    _,manifest=load_model(directory,expected_manifest_sha256)
    by_id={(r['league'],r['fixture_id']):r for r in games}
    seen=set()
    for sample in samples:
        p,y=verified_frozen_forecast(sample,archives,manifest)
        key=(p['league'],p['fixture_id'])
        need(key not in seen,'DUPLICATE_V3_FROZEN_FIXTURE');seen.add(key)
        if key in by_id:
            row=by_id[key]
            need(row['outcome_1x2']==y and row['kickoff_utc']==p['kickoff_utc'],
                 'V3_SAME_FIXTURE_SETTLEMENT_DRIFT')
        else:
            row=dict(league=p['league'],fixture_id=p['fixture_id'],kickoff_utc=p['kickoff_utc'],
                outcome_1x2=y,result_observed_utc=sample['label']['observed_utc'],predictions={})
            by_id[key]=row
        need('CATBOOST_ASOF_V3' not in row['predictions'],'DUPLICATE_MODEL_FIXTURE')
        row['predictions']['CATBOOST_ASOF_V3']=dict(model_version=NEW,p_1x2=p['p_1x2'],
            forecast_sha256=p['forecast_sha256'],feature_cutoff_utc=p['feature_cutoff_utc'],
            frozen_at_utc=p['generated_at_utc'],github_server_artifact_verified=True,
            forecast_hash_verified=True,horizon='EARLY_90MIN_OR_MORE')
    return list(by_id.values())
