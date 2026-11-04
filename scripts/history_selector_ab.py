"""Read-only logged-source A/B plus explicitly optimistic real-ID fetch plans."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip,hashlib,json
from pathlib import Path
from src.kb3_history_window_selector import (
    WindowGraph,load_snapshot,sha,DOMAIN,POLICY,as_utc,
)
from scripts.kb3_historical_pitchapi_backfill import select_batch

ROOT=Path(__file__).resolve().parents[1]

def need(ok,why):
    if not ok:raise ValueError(why)

def logged_replay(groups,initial_known,initial_verified,pool,outcomes,*,variant):
    """Outcomes are only revealed after selection; same history and candidate IDs."""
    graph=WindowGraph(groups);known=set(initial_known);verified=set(initial_verified)
    checkpoints=[];selections=[];read_units=0
    for batch in range(1,6):
        if variant=='current':picked=select_batch(groups,known,48,candidate_keys=pool)
        else:picked,_=graph.select(known,verified,48,pool)
        keys={(s,m['id']) for s,_,m in picked}
        need(len(keys)==len(picked) and keys<=pool-known,'INVALID_REPLAY_SELECTION')
        if not picked:break
        known|=keys
        # This is the only reveal of the actual held-back xG outcome.
        verified|={k for k in keys if outcomes[k]=='VERIFIED'}
        read_units+=2*len(keys)
        selections.extend({'scope':s,'season':se,'match_id':m['id']} for s,se,m in picked)
        checkpoints.append({'batch':batch,'source_pairs_read':len(selections),
            'successful_archived_endpoint_read_units':read_units,
            'verified_xg_in_selected':len(verified-initial_verified),
            'selected_leagues':dict(sorted(Counter(s for s,_ in keys).items())),
            'all_indexed_targets':graph.coverage(known,verified),
            'fixed_original_observed_targets':graph.coverage(known,verified,initial_known)})
    return {'selector':variant,'checkpoints':checkpoints,'selections':selections,
            'new_provider_calls':0,'live_increment_measured':False}

def optimistic_plan(groups,known,verified,variant):
    graph=WindowGraph(groups);known=set(known);verified=set(verified);batches=[]
    for i in range(1,6):
        if variant=='current':picked=select_batch(groups,known,48);detail=None
        else:picked,detail=graph.select(known,verified,48)
        keys={(s,m['id']) for s,_,m in picked}
        need(not keys&known,'PLAN_DUPLICATE_SOURCE')
        if not keys:break
        known|=keys;verified|=keys  # Explicit ceiling ONLY; never written to source DB.
        batches.append({'batch':i,'pairs':len(keys),'pair_endpoint_request_budget':2*len(keys),
            'maximum_total_requests':150,'leagues':dict(sorted(Counter(s for s,_ in keys).items())),
            'selection':[{'scope':s,'season':se,'match_id':m['id'],'kickoff_utc':m['time_utc']} for s,se,m in picked],
            'planning_details':detail,
            'if_all_selected_sources_validate':graph.coverage(known,verified)})
    return {'selector':variant,'only_a_theoretical_ceiling_not_observed_gain':True,
            'new_provider_calls':0,'batches':batches}

def matched_prefixes(graph,initial,verified,pool_outcomes,replays):
    """Equal endpoint-read costs, including a possibly partial last batch."""
    maximum=min(len(r['selections']) for r in replays)
    budgets=sorted({n for n in (48,96,144,192,240,maximum) if 0<n<=maximum})
    output=[]
    for n in budgets:
        part={'source_pairs_each':n,'successful_archived_endpoint_read_units_each':2*n,'models':{}}
        for run in replays:
            prefix=run['selections'][:n];selected={(x['scope'],x['match_id']) for x in prefix}
            now_verified=verified|{k for k in selected if pool_outcomes[k]=='VERIFIED'}
            touched=next(i+1 for i,c in enumerate(run['checkpoints']) if c['source_pairs_read']>=n)
            part['models'][run['selector']]={'catalogue_batches_touched':touched,
                'all_indexed_targets':graph.coverage(initial|selected,now_verified),
                'fixed_original_observed_targets':graph.coverage(initial|selected,now_verified,initial)}
        output.append(part)
    return output

def audit(db,archive,token,*,with_plan=True):
    groups,known,verified,observed,source=load_snapshot(db)
    paths=sorted(Path(archive).glob('*/run-'+token+'-b*/HISTORICAL_BACKFILL_REPORT.json'))
    need(len(paths)==5,'FIVE_RECORDED_BATCH_REPORTS_REQUIRED')
    reports=[json.loads(p.read_text()) for p in paths]
    start=min(as_utc(r['started_utc']) for r in reports);end=max(as_utc(r['ended_utc']) for r in reports)
    initial={k for k in known if as_utc(observed[k]['clock'])<start}
    pool={k for k in known if start<=as_utc(observed[k]['clock'])<=end}
    need(len(pool)==sum(r['new_match_stats'] for r in reports)==240,'LOGGED_POOL_COUNT_MISMATCH')
    need(all(observed[k]['shots_sha256'] is not None for k in pool),'LOGGED_PAIR_SOURCE_MISSING')
    outcomes={k:observed[k]['status'] for k in pool}
    graph=WindowGraph(groups)
    result={'schema':'kb3-history-selector-logged-ab-v1','selector_policy':POLICY,
        'availability_class':DOMAIN,'source':source,'replay_run_token':token,
        'source_report_sha256':{p.parent.name:sha(p) for p in paths},
        'new_provider_calls':0,'existing_m0_modified':False,'protected_TEST_used':False,
        'raw_receipts_reauthenticated':False,'official_training_approved':False,
        'baseline':{'observed_targets':graph.coverage(known,verified,known),
                    'all_indexed_targets':graph.coverage(known,verified)},
        'replay_contract':{'initial_observations':len(initial),'recorded_candidate_pairs':len(pool),
            'initial_recorded_verified_xg':len(verified&initial),'recorded_candidate_statuses':dict(Counter(outcomes.values())),
            'same_candidate_IDs_and_history':True,'outcomes_hidden_until_selection':True,
            'recorded_original_provider_requests':sum(r['provider_requests'] for r in reports),
            'actual_new_selector_live_gain':None,
            'limitation':'CLOSED_WORLD_LOGGED_SUPPORT_SELECTED_BY_OLD_COLLECTOR_NOT_FUTURE_LIVE_CAUSAL_PROOF'},
        'replay_before_all_targets':graph.coverage(initial,verified&initial),
        'replay_before_fixed_original_targets':graph.coverage(initial,verified&initial,initial),
        'replay':[logged_replay(groups,initial,verified&initial,pool,outcomes,variant=v) for v in ('current','window-yield')]}
    result['equal_source_pair_budgets']=matched_prefixes(graph,initial,verified&initial,outcomes,result['replay'])
    result['full_recorded_pool_control']=graph.coverage(initial|pool,(verified&initial)|{k for k in pool if outcomes[k]=='VERIFIED'})
    for run in result['replay']:
        if len(run['selections'])==len(pool):
            need(run['checkpoints'][-1]['all_indexed_targets']==result['full_recorded_pool_control'],
                 'IDENTICAL_SOURCE_POOL_CHANGED_COVERAGE')
    if with_plan:result['optimistic_next_5x48']=[optimistic_plan(groups,known,verified,v) for v in ('current','window-yield')]
    need(sha(db)==source['sqlite_sha256'],'ORIGINAL_SOURCE_MUTATED')
    result['report_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=ROOT/'data/research/historical_multistat/observations.sqlite')
    p.add_argument('--archive',type=Path,default=ROOT/'data/pit_sidecar/historical_multistat')
    p.add_argument('--replay-run',default='41692857683-1');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--no-plan',action='store_true');args=p.parse_args()
    need(not args.out.exists(),'APPEND_ONLY_REPORT_EXISTS')
    result=audit(args.db,args.archive,args.replay_run,with_plan=not args.no_plan)
    raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('xb') as f:f.write(gzip.compress(raw,mtime=0) if str(args.out).endswith('.gz') else raw)
    for run in result['replay']:
        print(json.dumps({'selector':run['selector'],'checkpoints':[
            (c['source_pairs_read'],c['all_indexed_targets']['complete_pairs']) for c in run['checkpoints']]},sort_keys=True),flush=True)
    print('REPORT_SHA256',result['report_sha256'])

if __name__=='__main__':main()
