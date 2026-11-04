"""Offline set-cover planner for real historical predecessor pairs, never PIT proof.

The optimistic assumption used to plan unknown fetches is kept separate from
recorded xG outcomes. Source acceptance and encrypted evidence are unchanged.
"""
from __future__ import annotations
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import hashlib
import math
import re
import sqlite3

from src.kb3_pit_ledger import as_utc
from src.kb3_pitch_native import MATCH_ID, TEAM_ID

SCOPES=frozenset(('ESP','ITA','GER','FRA','NED','BEL','TUR','POL'))
WINDOWS=(5,10,15)
WEIGHTS={'all':{5:16,10:8,15:4},'venue':{5:4,10:2,15:1}}
DOMAIN='HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT'
POLICY='closure-bundles-balanced-eight-v1'

def need(ok,code):
    if not ok:raise ValueError(code)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def readonly(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)

def load_snapshot(path):
    """Read archived projections; do not authenticate encrypted receipts or cache."""
    before=sha(path);groups=defaultdict(list);known=set();verified=set();observed={}
    with readonly(path) as db:
        need(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SOURCE_CORRUPT')
        need(db.execute("SELECT COUNT(*) FROM finished_fixture_index WHERE scope='ENG'").fetchone()[0]==0
             and db.execute("SELECT COUNT(*) FROM observations WHERE scope='ENG'").fetchone()[0]==0,'PROTECTED_ENG_SOURCE')
        for s,se,mid,ko,h,a,gh,ga,clock,pub in db.execute('SELECT scope,season,match_id,kickoff_utc,home_team_id,away_team_id,goals_home_90,goals_away_90,listing_observed_at_utc,original_provider_first_published_utc FROM finished_fixture_index'):
            need(pub is None and as_utc(ko)+timedelta(hours=3)<=as_utc(clock),'INVALID_LISTING_CLOCK')
            if s not in SCOPES:continue
            groups[(s,se)].append({'id':mid,'time_utc':ko,'status':'finished',
                'home_team':{'id':h},'away_team':{'id':a},'score_home':gh,'score_away':ga})
        graph=WindowGraph(groups)
        for s,se,mid,ko,h,a,status,xh,xa,clock,pub,research,st,sh,ch in db.execute('SELECT scope,season,match_id,kickoff_utc,home_team_id,away_team_id,xg_status,xg_home,xg_away,source_observed_at_utc,provider_first_published_at_utc,research_only,stats_payload_sha256,shots_payload_sha256,source_chain_sha256 FROM observations'):
            if s not in SCOPES:continue
            key=(s,mid);need(key in graph.fixtures,'OBSERVATION_WITHOUT_FIXTURE')
            season,m=graph.fixtures[key]
            need((se,as_utc(ko),h,a)==(season,as_utc(m['time_utc']),m['home_team']['id'],m['away_team']['id']),'SOURCE_IDENTITY_DRIFT')
            need(pub is None and research==1 and as_utc(ko)+timedelta(hours=3)<=as_utc(clock),'FALSE_HISTORICAL_PIT')
            need(all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in (st,ch)),'SOURCE_HASH_MISSING')
            known.add(key)
            if status=='VERIFIED':
                need(all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=30 for x in (xh,xa))
                     and isinstance(sh,str) and re.fullmatch('[0-9a-f]{64}',sh),'RECORDED_XG_INVALID')
                verified.add(key)
            observed[key]={'clock':clock,'status':status,'stats_sha256':st,'shots_sha256':sh}
    need(sha(path)==before,'SOURCE_CHANGED')
    return dict(groups),known,verified,observed,{'sqlite_sha256':before,
        'national_fixtures':len(graph.fixtures),'national_observations':len(known),
        'recorded_verified_xg':len(verified),'availability_class':DOMAIN,
        'xg_policy':'EXISTING_MAIN_STATUS_NOT_RAW_REAUTHENTICATED',
        'raw_receipts_reauthenticated':False,'original_pit_certified':False}

@dataclass(frozen=True)
class Window:
    scope:str
    target:str
    season:str
    mode:str
    n:int
    requires:frozenset
    shortfall:int

class WindowGraph:
    def __init__(self,groups,targets=None):
        self.fixtures={};team_rows=defaultdict(list)
        for (scope,season),rows in sorted(groups.items()):
            need(scope in SCOPES,'UNSUPPORTED_SCOPE')
            for m in rows:
                key=(scope,m['id']);need(key not in self.fixtures,'DUPLICATE_FIXTURE_ACROSS_SEASONS')
                h,a=m['home_team']['id'],m['away_team']['id']
                need(isinstance(m['id'],str) and MATCH_ID.fullmatch(m['id']) and h!=a
                     and all(isinstance(t,str) and TEAM_ID.fullmatch(t) for t in (h,a)),'BAD_NATIVE_IDENTITY')
                need(m.get('status')=='finished' and all(type(m.get(k)) is int and 0<=m[k]<=30
                     for k in ('score_home','score_away')),'UNFINISHED_OR_INVALID_RESULT')
                ko=as_utc(m['time_utc']);need(ko.year in (int(season[:4]),int(season[:4])+1),'SEASON_DRIFT')
                self.fixtures[key]=(season,m)
                for team,venue in ((h,'home'),(a,'away')):
                    team_rows[(scope,team,'all')].append((ko,key))
                    team_rows[(scope,team,venue)].append((ko,key))
        indexed={}
        for key,rows in team_rows.items():
            rows.sort();indexed[key]=([x[0] for x in rows],[x[1] for x in rows])
        if targets is None:targets=set(self.fixtures)
        need(set(targets)<=set(self.fixtures),'UNKNOWN_TARGET')
        self.targets=frozenset(targets);self.windows=[]
        for scope,mid in sorted(self.targets):
            season,m=self.fixtures[(scope,mid)];boundary=as_utc(m['time_utc'])-timedelta(hours=3)
            priors={}
            for side in ('home','away'):
                team=m[side+'_team']['id']
                for mode in ('all','venue'):
                    times,keys=indexed[(scope,team,'all' if mode=='all' else side)]
                    priors[(side,mode)]=keys[:bisect_right(times,boundary)]
            for mode in ('all','venue'):
                for n in WINDOWS:
                    home,away=(priors[(side,mode)][-n:] for side in ('home','away'))
                    self.windows.append(Window(scope,mid,season,mode,n,
                        frozenset(home+away),(n-len(home))+(n-len(away))))

    def coverage(self,known,verified,targets=None):
        need(set(verified)<=set(known),'VERIFIED_WITHOUT_OBSERVATION')
        totals={mode:{str(n):0 for n in WINDOWS} for mode in ('all','venue')}
        reasons=Counter();by_scope=defaultdict(Counter);by_season=defaultdict(Counter)
        for w in self.windows:
            if targets is not None and (w.scope,w.target) not in targets:continue
            label=w.mode+':'+str(w.n)
            if not w.shortfall and w.requires<=verified:
                totals[w.mode][str(w.n)]+=1
                by_scope[w.scope][label]+=1;by_season[w.scope+'/'+w.season][label]+=1
            else:
                if w.shortfall:reasons[label+':INSUFFICIENT_INDEXED_HISTORY']+=1
                if w.requires-known:reasons[label+':STATS_NOT_FETCHED']+=1
                if w.requires&(known-verified):reasons[label+':XG_REQUIRES_SOURCE_RECHECK']+=1
        return {'target_count':len(self.targets if targets is None else self.targets&set(targets)),
                'complete_pairs':totals,'by_scope':{s:dict(v) for s,v in sorted(by_scope.items())},
                'by_scope_season':{s:dict(v) for s,v in sorted(by_season.items())},
                'missing_reason_window_counts':dict(sorted(reasons.items())),
                'missing_reasons_can_overlap':True}

    def select(self,known,verified,limit=48,candidates=None):
        """Greedy complementary bundles, not a global optimum or observed gain."""
        need(type(limit) is int and 1<=limit<=48,'MATCH_BATCH_LIMIT')
        known=set(known);verified=set(verified)
        need(verified<=known and known<=set(self.fixtures),'UNKNOWN_SOURCE_KEY')
        eligible=set(self.fixtures)-known
        if candidates is not None:
            need(set(candidates)<=set(self.fixtures),'UNKNOWN_CANDIDATE')
            eligible&=set(candidates)
        counts=Counter(s for s,_ in known)
        scopes={s for s,_ in eligible};balanced=None
        if limit>=32 and len(scopes)>=3 and max(counts[s] for s in scopes)-min(counts[s] for s in scopes)>=64:
            balanced=min(scopes,key=lambda s:(counts[s],s))
            eligible={k for k in eligible if k[0]==balanced}
        usable=[w for w in self.windows if not w.shortfall and w.requires-verified
                and not w.requires&(known-verified) and w.requires-verified<=eligible]
        planned=set();trace=[]
        while eligible-planned and len(planned)<limit:
            remaining=limit-len(planned);deficits=Counter()
            for w in usable:
                missing=w.requires-verified-planned
                if missing:deficits[missing]+=WEIGHTS[w.mode][w.n]
            bundles=[d for d in deficits if len(d)<=remaining]
            if bundles:
                inverted=defaultdict(set)
                all_deficits=list(deficits)
                for i,d in enumerate(all_deficits):
                    for k in d:inverted[k].add(i)
                def gain(d):
                    nearby=set().union(*(inverted[k] for k in d))
                    return sum(deficits[all_deficits[i]] for i in nearby if all_deficits[i]<=d)
                def order(d):
                    g=gain(d)
                    return (-g/len(d),-g,len(d),tuple(sorted(d)))
                bundle=min(bundles,key=order);why='COMPLETE_PAIR_BUNDLE'
            else:
                progress=Counter()
                for d,weight in deficits.items():
                    for k in d:progress[k]+=weight/(len(d)*len(d))
                def order_key(k):
                    season,m=self.fixtures[k]
                    priority={'2025/2026':0,'2024/2025':1,'2026/2027':2,'2023/2024':3}.get(season,4)
                    return (-progress[k],priority,-as_utc(m['time_utc']).timestamp(),k)
                bundle=frozenset([min(eligible-planned,key=order_key)])
                why='PARTIAL_PROGRESS_OR_DENSE_FALLBACK'
            projected=sum(not w.shortfall and not w.requires<=verified|planned
                          and w.requires<=verified|planned|bundle for w in usable)
            for k in sorted(bundle):
                season,m=self.fixtures[k]
                trace.append({'scope':k[0],'match_id':k[1],'season':season,
                    'kickoff_utc':m['time_utc'],'reason':why,'bundle_cost_pairs':len(bundle),
                    'bundle_projected_closed_windows':projected})
            planned|=bundle
        selected=[(r['scope'],r['season'],self.fixtures[(r['scope'],r['match_id'])][1]) for r in trace]
        return selected,{'policy':POLICY,'balanced_scope':balanced,'selected_pairs':len(selected),
            'trace':trace,'assumption':'PLANNING_ONLY_ALL_SELECTED_PAIRS_VALIDATE',
            'before':self.coverage(known,verified),
            'optimistic_after':self.coverage(known|planned,verified|planned),
            'observed_gain':None,'source_acceptance_changed':False}

def select_window_batch(groups,known,verified,max_matches=48,*,candidate_keys=None,target_keys=None):
    domestic={key:rows for key,rows in groups.items() if key[0] in SCOPES}
    graph=WindowGraph(domestic,targets=target_keys)
    keys=set(graph.fixtures)
    return graph.select(set(known)&keys,set(verified)&keys,max_matches,candidate_keys)
