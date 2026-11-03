"""Read-only A/B/C feature contract; reconstructed history never becomes original PIT."""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import timedelta
from pathlib import Path
import hashlib,json,math,re,sqlite3
from src.kb3_features import _compose_features,EloParameters
from src.kb3_historical_feature_quality import _load_records,_utc,raw_stat,rolling_window

SCOPES=frozenset(('ESP','ITA','GER','FRA','NED','BEL','TUR','POL'))
DOMAIN='HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT'
CONTRACT='kb3-catboost-abc-shared-cutoff90-resultlag3h-v1'
LAG=timedelta(hours=3)
LEAD=timedelta(minutes=90)
STATS=('total_shots','ShotsOnTarget','ShotsOffTarget','fouls','corners','yellow_cards',
       'red_cards','Offsides','passes','accurate_passes','interceptions','clearances',
       'keeper_saves','big_chance','shots_inside_box','shots_outside_box','touches_opp_box')
class ResearchDataError(ValueError):pass
def need(ok,code):
    if not ok:raise ResearchDataError(code)
def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def readonly(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)

def strict_xg(row,meta):
    """Authenticate consistency of archived projections; not raw receipt reauthentication."""
    if row['xg_status']!='VERIFIED':return False,'SOURCE_UNVERIFIED'
    items=[i for i in row['items'] if i.get('key')=='total_shots']
    groups=[i.get('group') for i in items]
    if not all(isinstance(g,str) for g in groups) or (sorted(groups)!=['Shots','Top stats'] and groups!=['Shots']):
        return False,'COUNT_FIELDS_AMBIGUOUS'
    counts=(raw_stat(row,'total_shots','home'),raw_stat(row,'total_shots','away'))
    if any(v is None or v<0 or not float(v).is_integer() for v in counts):
        return False,'COUNT_MISSING_OR_INVALID'
    if counts!=(meta['shots_home'],meta['shots_away']):return False,'COUNT_CONFLICT'
    xg=(row['xg_home'],row['xg_away'])
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=30 for v in xg):
        return False,'XG_MISSING_OR_INVALID'
    independent=(raw_stat(row,'expected_goals','home'),raw_stat(row,'expected_goals','away'))
    if any(v is None for v in independent) or any(abs(a-b)>.02 for a,b in zip(xg,independent)):
        return False,'XG_PROJECTED_STATS_CONFLICT'
    if any(n==0 and v!=0 for n,v in zip(counts,xg)):return False,'EMPTY_SIDE_NONZERO_XG'
    return True,'CONSISTENT_ARCHIVED_PAIR'

def load_sources(path,rechecks=None):
    """Use originals and an optional independently keyed card overlay, never cache."""
    before=file_sha(path);audit=Counter()
    with readonly(path) as db:
        need(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SOURCE_CORRUPT')
        need(db.execute("SELECT COUNT(*) FROM finished_fixture_index WHERE scope='ENG'").fetchone()[0]==0
             and db.execute("SELECT COUNT(*) FROM observations WHERE scope='ENG'").fetchone()[0]==0,'PROTECTED_ENG_SOURCE')
        fixtures,observed,_,_=_load_records(db)
        need('ENG' not in fixtures and not any(k[0]=='ENG' for k in observed),'PROTECTED_ENG_SOURCE')
        meta={}
        for row in db.execute('SELECT scope,match_id,shots_home,shots_away,source_observed_at_utc,provider_first_published_at_utc,stats_payload_sha256,shots_payload_sha256,source_chain_sha256,research_only,goals_home_90,goals_away_90 FROM observations'):
            scope,mid,nh,na,clock,pub,stsha,shsha,chain,research,gh,ga=row
            need(research==1 and pub is None,'FALSE_ORIGINAL_PIT')
            need(all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in (stsha,chain)),'INVALID_SOURCE_HASH')
            if shsha is not None:need(bool(re.fullmatch('[0-9a-f]{64}',shsha)),'INVALID_SHOT_HASH')
            meta[(scope,mid)]={'shots_home':nh,'shots_away':na,'observed_at':clock,
                               'stats_sha256':stsha,'shots_sha256':shsha,'chain_sha256':chain,
                               'goals_home':gh,'goals_away':ga}
        # Read original listing clocks rather than making up old publication dates.
        listing={(s,m):(clock,sha,pub) for s,m,clock,sha,pub in db.execute(
            'SELECT scope,match_id,listing_observed_at_utc,source_listing_sha256,original_provider_first_published_utc FROM finished_fixture_index')}
    index={}
    for scope,seq in fixtures.items():
        if scope not in SCOPES:
            audit['excluded_scope_fixtures']+=len(seq);continue
        for f in seq:
            key=(scope,f['match_id']);need(key not in index,'DUPLICATE_FIXTURE')
            need(f['home_team_id']!=f['away_team_id'],'SAME_TEAM')
            need(all(type(f[k]) is int and 0<=f[k]<=30 for k in ('goals_home_90','goals_away_90')),'INVALID_RESULT')
            clock,sha,pub=listing[key]
            need(pub is None and bool(re.fullmatch('[0-9a-f]{64}',sha)),'UNPROVEN_LISTING_PIT')
            need(_utc(f['kickoff_utc'])+LAG<=_utc(clock),'LISTING_BEFORE_RESULT')
            f['listing_observed_at']=clock;f['listing_sha256']=sha
            index[key]=f
    output={}
    for key,row in observed.items():
        if key[0] not in SCOPES:continue
        f=index.get(key);need(f is not None,'OBSERVATION_WITHOUT_FIXTURE')
        need(all(row[k]==f[k] for k in ('season','kickoff_utc','home_team_id','away_team_id')),'OBSERVATION_IDENTITY_DRIFT')
        m=meta[key]
        need((m['goals_home'],m['goals_away'])==(f['goals_home_90'],f['goals_away_90']),'SOURCE_RESULT_CONFLICT')
        need(_utc(m['observed_at'])>=_utc(f['kickoff_utc'])+LAG,'STATS_BEFORE_RESULT')
        valid,reason=strict_xg(row,m);audit[reason]+=1
        if valid:need(m['shots_sha256'] is not None,'MISSING_INDEPENDENT_SHOTS_SHA')
        if not valid:row.update(xg_status='QUARANTINED',xg_home=None,xg_away=None)
        row['actual_observed_at']=m['observed_at']
        row['source_stats_sha256']=m['stats_sha256'];row['source_shots_sha256']=m['shots_sha256']
        # Invalid numeric statistics remain NULL, never negative counts or zero.
        for item in row['items']:
            if item.get('key') in STATS:
                for side in ('home','away'):
                    val=raw_stat({'items':[item]},item['key'],side)
                    if val is not None and val<0:item[side]=None;audit['negative_stat_quarantined']+=1
        output[key]=row
    recheck_sha=None
    if rechecks is not None:
        recheck_sha=file_sha(rechecks)
        with readonly(rechecks) as db:
            for s,m,status,clock,chain,sha,h,a,yh,ya,pub in db.execute('SELECT scope,match_id,status,observed_at_utc,source_chain_sha256,source_payload_sha256,native_home_team_id,native_away_team_id,yellow_events_home,yellow_events_away,original_provider_first_published_at_utc FROM issue_rechecks WHERE issue_type=\'YELLOW_CARDS\''):
                if status!='EVENT_YELLOW_CONFIRMED' or (s,m) not in output:continue
                f=index[(s,m)];row=output[(s,m)]
                need((h,a)==(f['home_team_id'],f['away_team_id']),'OVERLAY_TEAM_DRIFT')
                need(pub is None and all(re.fullmatch('[0-9a-f]{64}',x or '') for x in (chain,sha)),'OVERLAY_PROVENANCE_INVALID')
                need(_utc(clock)>=_utc(f['kickoff_utc'])+LAG,'OVERLAY_TOO_EARLY')
                need(all(type(v) is int and 0<=v<=30 for v in (yh,ya)),'OVERLAY_CARDS_INVALID')
                for side,value in (('home',yh),('away',ya)):
                    if raw_stat(row,'yellow_cards',side) is None:
                        row.setdefault('research_overrides',{}).setdefault('yellow_cards',{})[side]=float(value)
                        row['actual_observed_at']=max(row['actual_observed_at'],clock)
                        audit['card_sides_recovered']+=1
        need(file_sha(rechecks)==recheck_sha,'OVERLAY_SOURCE_CHANGED')
    need(file_sha(path)==before,'SOURCE_CHANGED')
    return fixtures,output,{'source_sha256':before,'recheck_sha256':recheck_sha,
        'fixture_count':len(index),'source_observations':len(output),'source_checks':dict(sorted(audit.items())),
        'raw_encrypted_receipts_reauthenticated':False,'original_pit_certified':False}

def feature_row(target,fixtures,observed,*,cutoff=None):
    """Shared function for research TRAIN and inference; never reads target goals."""
    scope=target['scope'];need(scope in SCOPES,'FORBIDDEN_SCOPE')
    kickoff=_utc(target['kickoff_utc']);cutoff=_utc(cutoff) if cutoff is not None else kickoff-LEAD
    need(cutoff<=kickoff-LEAD,'LATE_CUTOFF')
    history=[f for f in fixtures if f['scope']==scope and f['match_id']!=target['match_id']
             and _utc(f['kickoff_utc'])+LAG<=cutoff]
    history.sort(key=lambda f:(f['kickoff_utc'],f['match_id']))
    need(len({f['match_id'] for f in history})==len(history),'DUPLICATE_HISTORY')
    replay=[]
    for f in history:
        replay.append({'fixture_id':f['match_id'],'season_start_year':int(f['season'][:4]),
            'home_team_id':f['home_team_id'],'away_team_id':f['away_team_id'],
            'kickoff_utc':f['kickoff_utc'],'date':_utc(f['kickoff_utc']),
            'goals_home_90':f['goals_home_90'],'goals_away_90':f['goals_away_90'],
            'snapshot_id':f.get('listing_sha256','SYNTHETIC'),'published_at_utc':None,
            'captured_at_utc':f.get('listing_observed_at'),'result_provider_name':'PitchAPI',
            'result_record_updated_at_utc':None,
            'xgh':None,'xga':None,'xgh_source':None,'xga_source':None})
    base=_compose_features({'home_team_id':target['home_team_id'],'away_team_id':target['away_team_id'],
        'season_start_year':int(target['season'][:4])},replay,cutoff=cutoff,kickoff=kickoff,
        target_id=target['match_id'],mode='replay',params=EloParameters(),excluded=defaultdict(int))
    a={'num:'+k:v for k,v in base['features'].items() if 'xg' not in k.lower()}
    a.update({'miss:'+k:int(v) for k,v in base['missing_flags'].items() if 'xg' not in k.lower()})
    b=dict(a);c=None;complete=True;windows={};prior_ids={}
    for side in ('home','away'):
        team=target[side+'_team_id']
        priors=[f for f in history if team in (f['home_team_id'],f['away_team_id'])]
        prior_ids[side]=[f['match_id'] for f in priors[-5:]]
        for n in (5,10,15):windows[(side,n)]=rolling_window(history,observed,team,n)
        summary=windows[(side,5)]
        need(summary['actual_predecessors']==5,'FORM5_HISTORY_INCOMPLETE')
        complete=complete and summary['xg_complete']
        for field in ('xg_for','xg_against'):b[f'{side}_xg5_{field}']=summary['metrics'][field]['mean']
    c=dict(b)
    for side in ('home','away'):
        for n in (5,10,15):
            summary=windows[(side,n)]
            for field in STATS:c[f'{side}_{field}_{n}']=summary['metrics'][field]['mean']
            if n>5:
                for field in ('xg_for','xg_against'):c[f'{side}_xg{n}_{field}']=summary['metrics'][field]['mean']
    source_times=[_utc(f['listing_observed_at']) for f in history if f.get('listing_observed_at')]
    source_times.extend(_utc(observed[(scope,f['match_id'])]['actual_observed_at'])
        for f in history if (scope,f['match_id']) in observed and observed[(scope,f['match_id'])].get('actual_observed_at'))
    out={'contract':CONTRACT,'availability_class':DOMAIN,'original_pit_certified':False,
        'scope':scope,'match_id':target['match_id'],'kickoff_utc':target['kickoff_utc'],
        'feature_cutoff_utc':cutoff.isoformat().replace('+00:00','Z'),
        'actual_latest_source_observed_at':max(source_times).isoformat().replace('+00:00','Z') if source_times else None,
        'source_observed_after_cutoff':any(t>cutoff for t in source_times),
        'prior5_ids':prior_ids,'complete_xg5_both':bool(complete),'features':{'A':a,'B':b,'C':c}}
    out['feature_sha256']=digest(out)
    return out

def examples_from_sources(fixtures,observed):
    rows=[];excluded=Counter()
    for scope in sorted(fixtures):
        if scope not in SCOPES:continue
        for target in fixtures[scope]:
            try:features=feature_row(target,fixtures[scope],observed)
            except ResearchDataError as exc:
                if str(exc)!='FORM5_HISTORY_INCOMPLETE':raise
                excluded[str(exc)]+=1;continue
            gh,ga=target['goals_home_90'],target['goals_away_90']
            # Labels are attached after the target-independent feature builder.
            rows.append({**features,'y':'1' if gh>ga else '2' if gh<ga else 'X'})
    rows.sort(key=lambda r:(r['kickoff_utc'],r['scope'],r['match_id']))
    return rows,dict(excluded)
