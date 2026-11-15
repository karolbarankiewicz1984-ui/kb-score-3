"""Read-only operational M0 audit; never a forecast, source backfill or calibration."""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
import argparse,hashlib,json,math,sqlite3
from src.kb3_step16_m0_720_eight_forward import MODEL,trained_params,hashobj,stamp,LEAD,HORIZON
from src.kb3_step16_m0_720_calibration import eligible_settlements
from scripts.step16_m0_offline_readonly_audit import metrics
from src.kb3_pit_ledger import as_utc

ROOT=Path(__file__).resolve().parents[1]
SCOPES={'ESP','ITA','GER','FRA','NED','BEL','TUR','POL'}

def need(ok,why):
    if not ok:raise ValueError(why)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(db_path,*,root=ROOT,at=None,forecast_horizon=HORIZON):
    # Only exact historical-report replay may inject its contemporaneous selection horizon.
    need(isinstance(forecast_horizon,timedelta) and timedelta(hours=1)<=forecast_horizon<=timedelta(days=7),'AUDIT_HORIZON_INVALID')
    at=at or datetime.now(timezone.utc);root=Path(root);path=Path(db_path)
    need(at.tzinfo is not None and at.utcoffset()==timedelta(0),'UTC_REQUIRED')
    before=sha(path);params,param_sha,manifest_sha=trained_params()
    reasons=Counter();decisions=[];score_rows=[]
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        need(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall(),'SOURCE_INTEGRITY')
        meta=db.execute('SELECT model,parameters_sha256,manifest_sha256 FROM model_meta').fetchall()
        need([tuple(x) for x in meta]==[(MODEL,param_sha,manifest_sha)],'FROZEN_PARAMS_CHANGED')
        forecasts=[dict(x) for x in db.execute('SELECT * FROM forecasts ORDER BY kickoff_utc,id')]
        settlements={x['forecast_id']:dict(x) for x in db.execute('SELECT * FROM settlements')}
        proofs={x['forecast_id']:dict(x) for x in db.execute('SELECT * FROM m0720_github_push_proofs')}
        calibrators=[dict(x) for x in db.execute('SELECT * FROM m0720_calibrators')]
        reviews=[dict(x) for x in db.execute('SELECT * FROM m0720_holdout_reviews')]
        seen=set()
        for f in forecasts:
            key=(f['league'],f['native_match_id']);need(key not in seen and key[0] in SCOPES,'DUPLICATE_OR_PROTECTED_MATCH')
            seen.add(key);reason=None;p=json.loads(f['payload_json']);s=settlements.get(f['id']);proof=proofs.get(f['id'])
            identity=(p.get('forecast_sha256')==f['id']==hashobj({k:v for k,v in p.items() if k!='forecast_sha256'})
                and p.get('model_version')==f['model']==MODEL and p.get('params_sha256')==f['params_sha256']==param_sha
                and p.get('manifest_sha256')==manifest_sha and p.get('league_country')==f['league']
                and p.get('provider_match_id')==f['native_match_id'] and p.get('home_team_id')==f['home_team_id']
                and p.get('away_team_id')==f['away_team_id'] and p.get('kickoff_utc')==f['kickoff_utc']
                and p.get('generated_at_utc')==f['captured_at_utc'] and p.get('phase')=='EARLY')
            ko,created=as_utc(f['kickoff_utc']),as_utc(f['captured_at_utc'])
            if not identity:reason='INVALID_FROZEN_IDENTITY_OR_HASH'
            elif not created<ko-LEAD:reason='FROZEN_TOO_LATE'
            elif s is None:
                reason=('FUTURE_KICKOFF' if ko>at else 'RESULT_MATURITY_PENDING' if ko+timedelta(hours=3)>at else 'PROVIDER_RESULT_LOOKUP_REQUIRED')
            elif (s['league'],s['native_match_id'])!=key or s['outcome']!=('1' if s['score_home']>s['score_away'] else '2' if s['score_home']<s['score_away'] else 'X'):
                reason='INVALID_SETTLEMENT_IDENTITY_OR_LABEL'
            elif not ko+timedelta(hours=3)<=as_utc(s['settled_utc'])<=as_utc(s['observed_utc'])<=at:
                reason='RESULT_TIME_NOT_ELIGIBLE'
            elif proof is None:reason='HOST_PROOF_MISSING'
            else:
                body={k:v for k,v in proof.items() if k!='proof_id'}
                valid=(proof['proof_id']==hashobj(body) and proof['original_forecast_sha256']==f['id']
                    and proof['model']==MODEL and proof['source'] in ('GITHUB_SERVER_PUSH_EVENT_PLUS_HISTORICAL_DB_BYTES','GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES')
                    and created<=as_utc(proof['github_server_event_utc'])<=ko-LEAD)
                if not valid:reason='HOST_PROOF_HASH_OR_TIME_INVALID'
                else:
                    try:metrics([{'p':p['p_1x2'],'y':s['outcome'],'ll':s['log_loss'],'bs':s['brier_sum3']}])
                    except ValueError:reason='STORED_SCORE_OR_PROBABILITY_INVALID'
                    else:
                        reason='ELIGIBLE_SETTLED'
                        score_rows.append({'p':p['p_1x2'],'y':s['outcome'],'ll':s['log_loss'],'bs':s['brier_sum3']})
            reasons[reason]+=1
            decisions.append({'forecast_id':f['id'],'league':f['league'],'native_match_id':f['native_match_id'],
                'kickoff_utc':f['kickoff_utc'],'captured_at_utc':f['captured_at_utc'],'reason':reason})
        invalid=sum(v for k,v in reasons.items() if k.startswith(('INVALID_','FROZEN_TOO_LATE','HOST_PROOF_HASH','STORED_SCORE')))
        if not invalid:
            official=eligible_settlements(db,at=at)
            need({x['fid'] for x in official}=={x['forecast_id'] for x in decisions if x['reason']=='ELIGIBLE_SETTLED'},'OFFICIAL_ELIGIBILITY_DISAGREES')
    receipts=[]
    for p in (root/'data/pit_sidecar/m0_720_eight').glob('*/*/RECEIPT.json'):
        doc=json.loads(p.read_text())
        need(doc.get('report_sha256')==hashobj({k:v for k,v in doc.items() if k!='report_sha256'}),'RECEIPT_SHA_CHANGED')
        receipts.append((p,doc))
    last_forecast=max((doc for _,doc in receipts if doc['mode']=='forecast'),key=lambda x:as_utc(x['run_utc']),default=None)
    inventories=[]
    for p in (root/'data/pit_sidecar/step17_native_xg_eight').glob('*/XG_READINESS_RECEIPT.json'):
        doc=json.loads(p.read_text())
        if doc.get('real_missing_last5_predecessor_ids') is not None:inventories.append((p,doc))
    inventory=max(inventories,key=lambda x:as_utc(x[1]['observed_at_utc']),default=None)
    opportunity={'status':'ORIGINAL_FULL_FORECAST_LISTING_UNAVAILABLE_ENCRYPTED_RAW_NOT_DECRYPTED',
                 'global_qualified_but_missed_count':None,'no_retroactive_forecasts_created':True}
    if inventory and last_forecast:
        p,doc=inventory;details=[]
        for x in doc['real_missing_last5_predecessor_ids']:
            key=(x['country'],x['target_provider_match_id']);ko=as_utc(x['kickoff_utc'])
            hours=int(forecast_horizon.total_seconds()//3600)
            reason=('ALREADY_FROZEN' if key in seen else f'OUTSIDE_LAST_M0_{hours}H_HORIZON'
                    if ko>as_utc(last_forecast['run_utc'])+forecast_horizon else 'OBSERVED_UNFROZEN_NEEDS_ORIGINAL_M0_SOURCE_REVIEW')
            details.append({'league':key[0],'native_match_id':key[1],'kickoff_utc':x['kickoff_utc'],'reason':reason})
        opportunity.update({'separate_inventory_source':str(p.relative_to(root)),
            'separate_inventory_observed_at_utc':doc['observed_at_utc'],
            'last_M0_source_cutoff_utc':last_forecast['run_utc'],
            'separate_inventory_reason_counts':dict(Counter(x['reason'] for x in details)),
            'separate_inventory_details':details,'separate_inventory_is_not_M0_eligibility_proof':True})
    actions_path=root/'docs/audits/M0_720_ACTIONS_OBSERVED_2026-11-04.json'
    action_audit=None
    if actions_path.exists():
        actions=json.loads(actions_path.read_text());matched=[]
        for run in actions['runs']:
            matching=[doc for _,doc in receipts if as_utc(run['created_at'])<=as_utc(doc['run_utc'])<=as_utc(run['updated_at'])]
            matched.append({**run,'matched_committed_receipts':[{'mode':d['mode'],'run_utc':d['run_utc'],'network_calls':d['network_calls'],
                'new_forecasts':d.get('new_forecasts',0),'new_settlements':d.get('new_settlements',0)} for d in matching]})
        action_audit={**actions,'runs':matched,'observed_mode_counts':dict(Counter(
            d['mode'] for r in matched for d in r['matched_committed_receipts'])),
            'source_call_counter_is_historical_SDK_invocations_not_verified_physical_HTTP':True}
    post_fit=[]
    if calibrators:
        need(len(calibrators)==1,'MULTIPLE_CALIBRATORS_IN_SINGLE_COHORT')
        c=calibrators[0];payload=json.loads(c['payload_json'])
        need(c['production_approved']==0 and c['candidate_sha256']==hashobj(payload),'CALIBRATOR_STATE_DRIFT')
        fit_ids=set(payload.get('training_forecast_ids',[]))
        eligible_ids={x['forecast_id'] for x in decisions if x['reason']=='ELIGIBLE_SETTLED'}
        post_fit=[f['id'] for f in forecasts if f['id'] in eligible_ids and f['id'] not in fit_ids
                  and as_utc(f['captured_at_utc'])>as_utc(c['fitted_at_utc'])
                  and as_utc(f['kickoff_utc'])>as_utc(c['fitted_at_utc'])]
    need(sha(path)==before,'ORIGINAL_DATABASE_MUTATED')
    result={'schema':'kb3-m0720-operations-readonly-audit-v1','checked_at_utc':stamp(at),'source_sqlite_sha256':before,
        'model':MODEL,'parameters_sha256':param_sha,'manifest_sha256':manifest_sha,
        'counts':{'frozen_forecasts':len(forecasts),'raw_settlements':len(settlements),'host_attested_forecasts':len(proofs),
            'eligible_settled_total':len(score_rows),
            'eligible_FIT_candidates':len(score_rows) if not calibrators else 100,
            'missing_to_initial_FIT100':max(0,100-len(score_rows)) if not calibrators else 0,
            'calibrators':len(calibrators),'HOLDOUT_reviews':len(reviews),'new_post_fit_HOLDOUT':len(post_fit),
            'missing_post_fit_HOLDOUT50':max(0,50-len(post_fit)),
            'required_independent_HOLDOUT':50},'qualification_partition':dict(reasons),'forecast_decisions':decisions,
        'pooled_verified_metrics':metrics(score_rows),'opportunity_audit':opportunity,'actions_evidence':action_audit,
        'read_only':True,'provider_calls':0,'model_or_calibration_changed':False,
        'upstream_host_proofs_rechecked_locally_not_artifact_bytes_reauthenticated':True,
        'formal_GATE16':'PENDING','formal_100_plus_50_acceptance':False}
    result['report_sha256']=hashobj(result)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=ROOT/'data/forward_m0_720_eight/kb3_forward_eight.sqlite')
    p.add_argument('--root',type=Path,default=ROOT,help='Exact immutable snapshot root for historical verification')
    p.add_argument('--out',type=Path);p.add_argument('--verify-report',type=Path)
    p.add_argument('--historical-horizon-hours',type=int,default=None,
        help='Only when re-verifying the immutable 04 Nov original report; never changes live selection')
    a=p.parse_args()
    need(a.historical_horizon_hours is None or (a.verify_report is not None and
          a.historical_horizon_hours==96),'HISTORIC_HORIZON_OVERRIDE_NOT_PERMITTED')
    if a.verify_report:
        expected=json.loads(a.verify_report.read_text())
        need(expected['report_sha256']==hashobj({k:v for k,v in expected.items() if k!='report_sha256'}),'AUDIT_REPORT_SHA_CHANGED')
        need(sha(a.db)==expected['source_sqlite_sha256'],'AUDIT_HISTORICAL_SOURCE_SHA_MISMATCH')
        historical=timedelta(hours=a.historical_horizon_hours) if a.historical_horizon_hours is not None else HORIZON
        actual=audit(a.db,root=a.root,at=as_utc(expected['checked_at_utc']),forecast_horizon=historical)
        need(actual==expected,'AUDIT_SOURCE_OR_RESULTS_CHANGED')
        print('M0_720_READONLY_REPORT_VERIFIED',expected['report_sha256']);return
    need(a.out is not None,'OUT_OR_VERIFY_REQUIRED')
    need(not a.out.exists(),'APPEND_ONLY_AUDIT_REPORT')
    result=audit(a.db);a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'counts':result['counts'],'partition':result['qualification_partition'],'metrics':result['pooled_verified_metrics']},sort_keys=True))
if __name__=='__main__':main()
