"""Independent stdlib audit: archived IDs/statuses and naive predecessor counting.

Does not import either selector, use their cache, make API calls or certify raw PIT.
"""
import argparse,gzip,hashlib,json,sqlite3
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCOPES={'ESP','ITA','GER','FRA','NED','BEL','TUR','POL'}
def need(ok,code):
    if not ok:raise ValueError(code)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clock(raw):return datetime.fromisoformat(raw.replace('Z','+00:00'))

def verify(report_path,db_path,archive):
    raw=Path(report_path).read_bytes();report=json.loads(gzip.decompress(raw) if str(report_path).endswith('.gz') else raw)
    payload={k:v for k,v in report.items() if k!='report_sha256'}
    need(report['schema'] in ('kb3-history-selector-logged-ab-v1','kb3-history-selector-planning-only-v1'),'UNSUPPORTED_REPORT_SCHEMA')
    need(hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==report['report_sha256'],'REPORT_SHA_MISMATCH')
    need(sha(db_path)==report['source']['sqlite_sha256'],'SOURCE_SHA_MISMATCH')
    with sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro',uri=True) as db:
        need(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SOURCE_CORRUPT')
        rows=db.execute('SELECT scope,season,match_id,kickoff_utc,home_team_id,away_team_id FROM finished_fixture_index ORDER BY kickoff_utc,match_id').fetchall()
        sources=db.execute('SELECT scope,match_id,xg_status,source_observed_at_utc FROM observations').fetchall()
    need(not any(x[0]=='ENG' for x in rows+sources),'PROTECTED_ENG_SOURCE')
    fixtures={};by_scope=defaultdict(list)
    for scope,season,mid,ko,home,away in rows:
        if scope not in SCOPES:continue
        row={'key':(scope,mid),'season':season,'ko':clock(ko),'h':home,'a':away}
        need(row['key'] not in fixtures,'DUPLICATE_FIXTURE')
        fixtures[row['key']]=row;by_scope[scope].append(row)
    # Independent, deliberately simple scan instead of selector's team/bisect index.
    windows=[]
    for key,target in fixtures.items():
        prior=[r for r in by_scope[key[0]] if r['ko']+timedelta(hours=3)<=target['ko'] and r['key']!=key]
        for mode in ('all','venue'):
            sides=[]
            for side in ('h','a'):
                team=target[side]
                sides.append([r['key'] for r in prior if
                    (team in (r['h'],r['a']) if mode=='all' else r[side]==team)])
            for n in (5,10,15):
                req=set(sides[0][-n:]+sides[1][-n:]) if all(len(s)>=n for s in sides) else None
                windows.append((key,mode,str(n),req))
    known={(s,m) for s,m,_,_ in sources if s in SCOPES}
    verified={(s,m) for s,m,status,_ in sources if s in SCOPES and status=='VERIFIED'}
    reports=[]
    for name,expected in report.get('source_report_sha256',{}).items():
        paths=list(Path(archive).glob('*/'+name+'/HISTORICAL_BACKFILL_REPORT.json'))
        need(len(paths)==1 and sha(paths[0])==expected,'SOURCE_BATCH_REPORT_CHANGED')
        reports.append(json.loads(paths[0].read_text()))
    initial=set();pool=set()
    if 'replay' in report:
        need(bool(reports),'LOGGED_BATCH_REPORTS_MISSING')
        start=min(clock(r['started_utc']) for r in reports);end=max(clock(r['ended_utc']) for r in reports)
        initial={(s,m) for s,m,_,t in sources if s in SCOPES and clock(t)<start}
        pool={(s,m) for s,m,_,t in sources if s in SCOPES and start<=clock(t)<=end}
        need(len(pool)==240,'LOGGED_POOL_MISMATCH')
    checked=0
    def check(expected,now_verified,targets=None):
        nonlocal checked
        counts={mode:{str(n):0 for n in (5,10,15)} for mode in ('all','venue')}
        league=defaultdict(Counter)
        for key,mode,n,req in windows:
            if targets is not None and key not in targets:continue
            if req is not None and req<=now_verified:
                counts[mode][n]+=1;league[key[0]][mode+':'+n]+=1
        need(expected['complete_pairs']==counts,'COMPLETE_WINDOW_COUNT_MISMATCH')
        need(expected['target_count']==len(fixtures if targets is None else set(fixtures)&targets),'TARGET_POPULATION_CHANGED')
        need(expected['by_scope']=={s:dict(c) for s,c in league.items()},'LEAGUE_WINDOW_COUNT_MISMATCH')
        checked+=1
    check(report['baseline']['observed_targets'],verified,known)
    check(report['baseline']['all_indexed_targets'],verified)
    if 'replay' in report:
        check(report['replay_before_all_targets'],verified&initial)
        check(report['replay_before_fixed_original_targets'],verified&initial,initial)
    selections={}
    for run in report.get('replay',[]):
        seq=[(x['scope'],x['match_id']) for x in run['selections']]
        need(len(seq)==len(set(seq)) and set(seq)<=pool,'DUPLICATE_OR_UNRECORDED_REPLAY_SOURCE')
        need(all(fixtures[(x['scope'],x['match_id'])]['season']==x['season'] for x in run['selections']),'REPLAY_SEASON_DRIFT')
        selections[run['selector']]=seq
        last=0
        for i,c in enumerate(run['checkpoints'],1):
            n=c['source_pairs_read'];need(c['batch']==i<=5 and 0<n-last<=48,'BATCH_LIMIT')
            need(c['successful_archived_endpoint_read_units']==2*n,'UNEQUAL_SOURCE_READ_COST')
            subset=set(seq[:n]);v=(verified&initial)|(verified&subset)
            check(c['all_indexed_targets'],v);check(c['fixed_original_observed_targets'],v,initial)
            last=n
    for c in report.get('equal_source_pair_budgets',[]):
        n=c['source_pairs_each'];need(c['successful_archived_endpoint_read_units_each']==2*n,'PREFIX_COST_MISMATCH')
        for selector,score in c['models'].items():
            subset=set(selections[selector][:n]);need(len(subset)==n,'UNEQUAL_PREFIX_SIZE')
            v=(verified&initial)|(verified&subset)
            check(score['all_indexed_targets'],v);check(score['fixed_original_observed_targets'],v,initial)
    if 'full_recorded_pool_control' in report:check(report['full_recorded_pool_control'],verified)
    planned=0
    for run in report.get('optimistic_next_5x48',[]):
        need(run['only_a_theoretical_ceiling_not_observed_gain'] is True,'OPTIMISTIC_PLAN_CANNOT_BE_OBSERVED_GAIN')
        seen=set(known);v=set(verified)
        for i,b in enumerate(run['batches'],1):
            seq=b['selection'];keys={(x['scope'],x['match_id']) for x in seq}
            need(i<=5 and 1<=len(seq)<=48 and len(keys)==len(seq) and not keys&seen and keys<=set(fixtures),'PLAN_ID_OR_LIMIT_FAILURE')
            for x in seq:
                f=fixtures[(x['scope'],x['match_id'])]
                need(x['season']==f['season'] and clock(x['kickoff_utc'])==f['ko'],'PLAN_IDENTITY_DRIFT')
            need(b['pair_endpoint_request_budget']==2*len(keys) and b['maximum_total_requests']==150,'PLAN_BUDGET_FAILURE')
            seen|=keys;v|=keys;check(b['if_all_selected_sources_validate'],v);planned+=len(keys)
    need(report['new_provider_calls']==0 and report['raw_receipts_reauthenticated'] is False,'FALSE_LIVE_OR_RAW_CERTIFICATION')
    need(sha(db_path)==report['source']['sqlite_sha256'],'SOURCE_MUTATED')
    return {'status':'PASS','independent_naive_window_count_checks':checked,
        'logged_candidate_pairs':len(pool),'real_ID_plan_entries_checked':planned,
        'source_unchanged':True,'report_sha256':report['report_sha256'],
        'not_live_effectiveness_proof':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True)
    p.add_argument('--db',type=Path,default=ROOT/'data/research/historical_multistat/observations.sqlite')
    p.add_argument('--archive',type=Path,default=ROOT/'data/pit_sidecar/historical_multistat')
    a=p.parse_args();print(json.dumps(verify(a.report,a.db,a.archive),indent=2))
if __name__=='__main__':main()
