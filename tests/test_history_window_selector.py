"""Synthetic adversarial contracts; effectiveness evidence comes from logged replay."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from collections import Counter

from src.kb3_history_window_selector import WindowGraph,select_window_batch,load_snapshot
from src.kb3_history_request_budget import RequestBudget
from scripts.kb3_historical_pitchapi_backfill import capture,select_batch,BackfillError
from src.kb3_historical_feature_quality import rolling_window
from scripts.history_selector_ab import logged_replay
from src.kb3_pitch_uefa_evidence import add_observation as real_add,verify_receipts as real_verify
from scripts.kb3_history_accelerated import drive
from scripts.kb3_history_issue_recheck import recheck,candidates
from test_kb3_history_accelerated import fake_quality
from test_kb3_history_issue_recheck import row as issue_row
from scripts.kb3_historical_pitchapi_backfill import put_rows
from test_kb3_historical_pitchapi_backfill import game,stats,shots

def history(count=16,scope='ESP'):
    start=datetime(2025,7,1,12,tzinfo=timezone.utc);rows=[]
    for i in range(count):
        f=game('m_'+str(i).zfill(6),(start+timedelta(days=i)).isoformat().replace('+00:00','Z'))
        if i%2:f['home_team'],f['away_team']=f['away_team'],f['home_team']
        rows.append(f)
    return {(scope,'2025/2026'):rows}
def keys(rows,scope='ESP'):return {(scope,m['id']) for m in rows}

class WindowSelectionTests(unittest.TestCase):
    def test_complementary_pair_bundle_closes_both_sides(self):
        g=history(7);rows=next(iter(g.values()));known=keys(rows)-keys(rows[3:5])
        picked,report=WindowGraph(g).select(known,known,2)
        self.assertEqual({m['id'] for _,_,m in picked},{rows[3]['id'],rows[4]['id']})
        self.assertGreater(report['optimistic_after']['complete_pairs']['all']['5'],report['before']['complete_pairs']['all']['5'])
        self.assertIsNone(report['observed_gain'])

    def test_true_last_five_never_replace_missing_by_sixth(self):
        g=history(7);rows=next(iter(g.values()));graph=WindowGraph(g,targets={('ESP',rows[6]['id'])})
        known=keys(rows);verified=known-{('ESP',rows[4]['id'])}
        self.assertEqual(graph.coverage(known,verified)['complete_pairs']['all']['5'],0)
        w=next(w for w in graph.windows if w.n==5 and w.mode=='all')
        self.assertNotIn(('ESP',rows[0]['id']),w.requires)
        self.assertNotIn(('ESP',rows[6]['id']),w.requires)

    def test_cross_season_keeps_native_team_history(self):
        g=history(6);rows=next(iter(g.values()))
        for i,f in enumerate(rows):f['time_utc']=f'2025-06-{25+i:02d}T12:00:00Z'
        rows[-1]['time_utc']='2025-07-01T12:00:00Z'
        g={('ESP','2024/2025'):rows[:5],('ESP','2025/2026'):rows[5:]}
        graph=WindowGraph(g,targets={('ESP',rows[-1]['id'])})
        self.assertEqual(graph.coverage(keys(rows),keys(rows))['complete_pairs']['all']['5'],1)

    def test_venue_is_home_and_away_separately(self):
        g=history(13);rows=next(iter(g.values()));graph=WindowGraph(g,targets={('ESP',rows[-1]['id'])})
        venue=next(w for w in graph.windows if w.mode=='venue' and w.n==5)
        self.assertEqual(venue.requires, frozenset(keys([rows[i] for i in (2,4,6,8,10)])))
        self.assertNotEqual(venue.requires,next(w for w in graph.windows if w.mode=='all' and w.n==5).requires)

    def test_three_hour_lag_and_tied_kickoffs(self):
        g=history(7);rows=next(iter(g.values()));rows[-1]['time_utc']=rows[-2]['time_utc']
        graph=WindowGraph(g,targets=keys(rows[-2:]))
        self.assertTrue(all(not (w.requires&keys(rows[-2:])) for w in graph.windows))
        rows[-2]['time_utc']='2025-07-06T10:00:01Z';rows[-1]['time_utc']='2025-07-06T13:00:00Z'
        graph=WindowGraph(g,targets=keys(rows[-1:]))
        self.assertTrue(all(('ESP',rows[-2]['id']) not in w.requires for w in graph.windows))
        rows[-2]['time_utc']='2025-07-06T10:00:00Z'
        graph=WindowGraph(g,targets=keys(rows[-1:]))
        self.assertIn(('ESP',rows[-2]['id']),next(w for w in graph.windows if w.mode=='all' and w.n==5).requires)

    def test_no_target_label_or_input_mutation_affects_ranking(self):
        g=history(10);original=deepcopy(g);rows=next(iter(g.values()));known=keys(rows[:4]+rows[-1:])
        first,_=select_window_batch(g,known,known,4)
        self.assertEqual(g,original)
        for row in next(iter(g.values())):row['score_home']=0;row['score_away']=0
        second,_=select_window_batch(g,known,known,4)
        self.assertEqual([x[2]['id'] for x in first],[x[2]['id'] for x in second])

    def test_unverified_existing_source_goes_to_recheck(self):
        g=history(7);rows=next(iter(g.values()));known=keys(rows);verified=known-keys(rows[4:5])
        graph=WindowGraph(g);picked,report=graph.select(known,verified,4)
        self.assertEqual(picked,[])
        self.assertTrue(any(k.endswith('XG_REQUIRES_SOURCE_RECHECK') for k in report['before']['missing_reason_window_counts']))

    def test_candidate_filter_never_removes_history_or_invents_known(self):
        g=history(7);rows=next(iter(g.values()));graph=WindowGraph(g,targets=keys(rows[-1:]))
        known=keys(rows[:3]);allowed=keys(rows[4:5]);picked,report=graph.select(known,known,2,allowed)
        self.assertEqual({m['id'] for _,_,m in picked},{rows[4]['id']})
        self.assertEqual(report['optimistic_after']['complete_pairs']['all']['5'],0)
        self.assertEqual(len(known),3)

    def test_original_and_filtered_baseline_match_with_full_candidates(self):
        g=history(20);rows=next(iter(g.values()));known=keys(rows[-2:])
        self.assertEqual(select_batch(g,known,8),select_batch(g,known,8,candidate_keys=keys(rows)))

    def test_balanced_eight_league_rotation_excludes_ucl(self):
        scopes=('ESP','ITA','GER','FRA','NED','BEL','TUR','POL');groups={};known=set()
        for i,scope in enumerate(scopes):
            g=history(140,scope);groups.update(g);rows=next(iter(g.values()))
            count=100 if scope in ('BEL','ESP') else (0 if scope=='ITA' else 3)
            known|=keys(rows[:count],scope)
        picked,report=select_window_batch(groups,known,known,48)
        self.assertEqual(len(picked),48);self.assertEqual({s for s,_,_ in picked},{'ITA'})
        following=known|{(s,m['id']) for s,_,m in picked}
        picked2,_=select_window_batch(groups,following,following,48)
        self.assertNotEqual({s for s,_,_ in picked2},{'ITA'})

    def test_duplicate_cross_season_and_eng_and_future_rejected(self):
        g=history(6);rows=next(iter(g.values()))
        for bad in ({**g,('ESP','2024/2025'):rows}, {('ENG','2025/2026'):rows}, {('UCL','2025/2026'):rows}):
            with self.assertRaises(ValueError):WindowGraph(bad)
        rows[-1]['status']='scheduled'
        with self.assertRaisesRegex(ValueError,'UNFINISHED'):WindowGraph(g)

    def test_coverage_matches_existing_rolling_window(self):
        g=history(35);rows=next(iter(g.values()));graph=WindowGraph(g,targets=keys(rows[-1:]))
        fixtures=[{'scope':'ESP','match_id':f['id'],'kickoff_utc':f['time_utc'],
                   'home_team_id':f['home_team']['id'],'away_team_id':f['away_team']['id'],
                   'goals_home_90':f['score_home'],'goals_away_90':f['score_away']} for f in rows[:-1]]
        known=keys(rows[:-1]);verified=known-keys(rows[4:5])
        observed={k:{'xg_status':'VERIFIED','xg_home':0.,'xg_away':0.,'items':[]} for k in verified}
        cov=graph.coverage(known,verified)
        for mode in ('all','venue'):
            for n in (5,10,15):
                complete=all(rolling_window(fixtures,observed,rows[-1][side+'_team']['id'],n,None if mode=='all' else side)['xg_complete'] for side in ('home','away'))
                self.assertEqual(cov['complete_pairs'][mode][str(n)],int(complete))

    def test_replay_outcomes_not_visible_to_selector(self):
        g=history(10);rows=next(iter(g.values()));known=keys(rows[:4]);pool=keys(rows[4:])
        a={k:'VERIFIED' for k in pool};b={k:'XG_SHOTS_STATS_DISAGREE' for k in pool}
        left=logged_replay(g,known,known,pool,a,variant='window-yield')
        right=logged_replay(g,known,known,pool,b,variant='window-yield')
        self.assertEqual(left['selections'],right['selections'])
        self.assertNotEqual(left['checkpoints'][0]['verified_xg_in_selected'],right['checkpoints'][0]['verified_xg_in_selected'])

class RequestRetryTests(unittest.TestCase):
    def setUp(self):
        p=patch('src.kb3_history_request_budget.add_observation',side_effect=lambda *a,**kw:real_add(*a,**kw,origin='SYNTHETIC_TEST'))
        p.start();self.addCleanup(p.stop)
        p=patch('src.kb3_history_request_budget.time.sleep');p.start();self.addCleanup(p.stop)
    def test_transient_then_success_single_receipt_and_memoized_resource(self):
        receipts=[];errors=Counter();b=RequestBudget(5,receipts,errors)
        fn=Mock(side_effect=[TimeoutError(),{'real_response_for_synthetic_test':1}])
        first=b.call('pitchapi:test:resource',fn,reserve=1);second=b.call('pitchapi:test:resource',fn,reserve=1)
        self.assertEqual(fn.call_count,2);self.assertEqual((b.calls,b.retries,len(receipts)),(2,1,1))
        self.assertEqual(first,second)

    def test_auth_error_not_retried_or_attested(self):
        error=RuntimeError();error.status_code=401
        fn=Mock(side_effect=error);receipts=[];b=RequestBudget(5,receipts,Counter())
        self.assertEqual(b.call('r',fn),(None,None));self.assertEqual(fn.call_count,1)
        self.assertEqual(receipts,[])

    def test_reserve_preserves_one_call_for_every_remaining_source(self):
        receipts=[];b=RequestBudget(150,receipts,Counter())
        for i in range(37):b.call('pitchapi:test:listing'+str(i),lambda:{'matches':[]},reserve=96)
        for i in range(96):
            fn=Mock(side_effect=[TimeoutError(),{'data':i}])
            b.call('pitchapi:test:pair'+str(i),fn,reserve=95-i)
            self.assertGreaterEqual(fn.call_count,1)
        self.assertEqual(b.calls,150);self.assertEqual(b.retries,17)
        self.assertEqual(len(receipts),54)

    def test_exhausted_transport_and_nonobject_are_not_evidence(self):
        receipts=[];b=RequestBudget(5,receipts,Counter())
        self.assertEqual(b.call('missing',Mock(side_effect=TimeoutError())),(None,None))
        self.assertEqual(b.call('bad',lambda:[]),(None,None))
        self.assertEqual(receipts,[]);self.assertEqual(b.calls,3)

    def test_real_sdk_transport_exact_http_attempts(self):
        import httpx
        from pitchapi import PitchAPI
        count=[]
        def handler(request):
            count.append(request.method)
            return httpx.Response(503,json={'error':{'code':'SERVER_ERROR','message':'synthetic'}}) if len(count)==1 else httpx.Response(200,json={'data':{'leagues':[]}})
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client=PitchAPI(api_key='synthetic_test_key_not_a_secret',max_retries=0,_http_client=http)
            b=RequestBudget(3,[],Counter())
            result,receipt=b.call('pitchapi:test:transport',client._get,'/leagues')
            self.assertIsNotNone(result);self.assertIsNotNone(receipt)
            self.assertEqual((len(count),b.calls,b.retries),(2,2,1))

    def test_long_retry_after_deferred_and_short_delay_honored(self):
        error=RuntimeError();error.status_code=429;error.retry_after=60
        fn=Mock(side_effect=error);b=RequestBudget(5,[],Counter())
        self.assertEqual(b.call('pitchapi:test:rate',fn),(None,None))
        self.assertEqual(fn.call_count,1);self.assertEqual(b.errors['LONG_RETRY_AFTER_DEFERRED'],1)
        error.retry_after=1
        fn=Mock(side_effect=[error,{'data':[]}]);b.call('pitchapi:test:short',fn)
        from src.kb3_history_request_budget import time
        time.sleep.assert_called_with(1.)

class CaptureRetryIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Real AES/RSA in temporary files, explicitly synthetic receipt origins.
        for p in (patch('src.kb3_history_request_budget.add_observation',side_effect=lambda *a,**kw:real_add(*a,**kw,origin='SYNTHETIC_TEST')),
                  patch('src.kb3_pitch_uefa_evidence.verify_receipts',side_effect=lambda receipts:real_verify(receipts,allow_synthetic=True))):
            p.start();self.addCleanup(p.stop)
        p=patch('src.kb3_history_request_budget.time.sleep');p.start();self.addCleanup(p.stop)
    def client(self,shots_fn):
        return SimpleNamespace(leagues=SimpleNamespace(list=Mock(return_value={'leagues':[]}),
            matches=Mock(return_value={'matches':[game()]})),
            matches=SimpleNamespace(stats=Mock(side_effect=lambda _:stats()),shots=shots_fn))
    def capture(self,client,folder,token):
        with patch('scripts.kb3_historical_pitchapi_backfill.select_scopes',return_value=([('ESP','l_Aa1234','2025/2026')],'SYNTHETIC')):
            return capture(client=client,root=folder/'archive',db_path=folder/'db.sqlite',run_token=token,max_matches=1)

    def test_real_encryption_retry_and_same_token_fail_before_api(self):
        client=self.client(Mock(side_effect=[TimeoutError(),shots()]))
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);report=self.capture(client,folder,'retry-1')
            self.assertEqual((report['new_match_stats'],report['new_native_xg_verified'],report['request_retries']),(1,1,1))
            self.assertEqual((report['provider_requests'],report['successful_response_receipts']),(5,4))
            before=hashlib.sha256((folder/'db.sqlite').read_bytes()).hexdigest()
            calls=client.leagues.list.call_count
            with self.assertRaisesRegex(BackfillError,'ALREADY_EXISTS'):self.capture(client,folder,'retry-1')
            self.assertEqual(client.leagues.list.call_count,calls)
            self.assertEqual(hashlib.sha256((folder/'db.sqlite').read_bytes()).hexdigest(),before)
            self.assertEqual(len(list((folder/'archive').glob('*/run-*/HISTORICAL_SOURCE.enc'))),1)

    def test_failed_shots_keeps_pair_eligible_for_later_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            first=self.capture(self.client(Mock(side_effect=TimeoutError())),folder,'retry-2')
            self.assertEqual(first['new_match_stats'],0)
            self.assertEqual(first['deferred_pairs'][0]['reason'],'SHOTS_REQUEST_UNAVAILABLE')
            with sqlite3.connect(folder/'db.sqlite') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM observations').fetchone()[0],0)
            second=self.capture(self.client(Mock(return_value=shots())),folder,'retry-3')
            self.assertEqual(second['new_match_stats'],1)
            with sqlite3.connect(folder/'db.sqlite') as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM observations').fetchone()[0],1)
                self.assertIsNone(db.execute('SELECT provider_first_published_at_utc FROM observations').fetchone()[0])

    def test_seal_failure_never_publishes_source_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            with patch('scripts.kb3_historical_pitchapi_backfill.seal',side_effect=RuntimeError('synthetic seal failure')):
                with self.assertRaises(RuntimeError):self.capture(self.client(Mock(return_value=shots())),folder,'retry-4')
            self.assertFalse((folder/'db.sqlite').exists())

    def test_default_selector_unchanged_and_invalid_policy_before_api(self):
        client=self.client(Mock(return_value=shots()))
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);report=self.capture(client,folder,'retry-5')
            self.assertEqual(report['selector'],'current');self.assertIsNone(report['selector_planning'])
            with self.assertRaisesRegex(BackfillError,'UNKNOWN_HISTORY_SELECTOR'):
                capture(client=client,db_path=folder/'db.sqlite',root=folder/'archive',run_token='bad',selector='bad')
            self.assertEqual(client.leagues.list.call_count,1)

    def test_default_sdk_hidden_retries_rejected_before_http(self):
        import httpx
        from pitchapi import PitchAPI
        handler=Mock(return_value=httpx.Response(500))
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            client=PitchAPI(api_key='synthetic_test_key_not_a_secret',_http_client=http)
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(BackfillError,'SDK_RETRIES_MUST_BE_ZERO'):
                    self.capture(client,Path(tmp),'sdk-default')
            self.assertEqual(handler.call_count,0)

    def test_incomplete_recheck_transport_does_not_suppress_future_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);put_rows(folder/'db.sqlite',[issue_row()])
            client=self.client(Mock(side_effect=TimeoutError()))
            client.matches.events=Mock(side_effect=TimeoutError())
            with patch('src.kb3_pitch_uefa_evidence.verify_receipts',side_effect=lambda receipts:real_verify(receipts,allow_synthetic=True)):
                report=recheck(client,db_path=folder/'db.sqlite',issue_db=folder/'issues.sqlite',root=folder/'archives',run_token='partial-xg')
            self.assertEqual(report['xg_reviewed'],0)
            self.assertEqual(report['error_types']['XG_INCOMPLETE_PAIR_DEFERRED'],1)
            self.assertEqual(len(candidates(folder/'db.sqlite',folder/'issues.sqlite')[0]),1)
            with sqlite3.connect(folder/'issues.sqlite') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM issue_rechecks').fetchone()[0],0)

    @patch('scripts.kb3_history_accelerated.assess_and_cache',side_effect=fake_quality)
    @patch('scripts.kb3_history_accelerated.recheck',return_value={'status':'NO_NEW_ISSUES'})
    @patch('scripts.kb3_history_accelerated.capture')
    def test_driver_retries_zero_success_nonempty_selection_and_keeps_policy(self,cap,recheck_mock,quality):
        base={'new_native_xg_verified':0,'provider_requests':10,'cumulative_match_stats':0,
              'source_ciphertext_sha256':'a'*64,'selected_match_count':1}
        cap.side_effect=[dict(base,new_match_stats=0),dict(base,new_match_stats=1)]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            report=drive(object(),run_token='retry-driver',db=p/'db',archive=p/'archive',issues_db=p/'issues',batches=2,selector='window-yield')
        self.assertEqual(report['completed_batches'],2);self.assertEqual(cap.call_count,2)
        self.assertTrue(all(c.kwargs['selector']=='window-yield' for c in cap.call_args_list))

    def test_workflow_schedule_retains_current_and_pr_does_not_get_secrets(self):
        path=Path(__file__).resolve().parents[1]/'.github/workflows/kb3-historical-pitchapi-backfill.yml'
        text=path.read_text()
        self.assertIn("HISTORY_SELECTOR: ${{ inputs.selector || 'current' }}",text)
        self.assertIn("github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",text)

if __name__=='__main__':unittest.main()
