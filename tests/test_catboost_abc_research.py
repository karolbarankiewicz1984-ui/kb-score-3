"""Causal reconstruction, exact paired cohorts, model contracts and frozen-proof boundaries."""
import copy,json,math,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from src.kb3_catboost_research_data import (
    feature_row,strict_xg,load_sources,ResearchDataError,CONTRACT,DOMAIN,digest,
)
from src.kb3_catboost_abc_research import (
    catalog,validate_examples,split_window,train_columns,vector,fit_window,experiment,
    comparison,compare_original_m0,PARAMS,FOLDS,VALIDATION,M0,
)

def iso(t):return t.isoformat().replace('+00:00','Z')
def fixture(i,scope='ESP'):
    return {'scope':scope,'season':'2024/2025','match_id':f'm_{i:06d}',
        'kickoff_utc':iso(datetime(2024,8,1,tzinfo=timezone.utc)+timedelta(days=7*i)),
        'home_team_id':'t_000001','away_team_id':'t_000002',
        'goals_home_90':i%3,'goals_away_90':i%2,
        'listing_observed_at':'2026-11-03T12:00:00Z','listing_sha256':'a'*64}

def observation():
    return {'xg_status':'VERIFIED','xg_home':.4,'xg_away':.7,
        'actual_observed_at':'2026-11-03T12:00:00Z',
        'items':[{'group':'Expected goals (xG)','key':'expected_goals','home':'.4','away':'.7'},
                 {'group':'Shots','key':'total_shots','home':'1','away':'1'},
                 {'group':'Top stats','key':'total_shots','home':'1','away':'1'},
                 {'group':'Other','key':'fouls','home':'0','away':None}]}

def rehash(row):
    row['feature_sha256']=digest({k:v for k,v in row.items() if k not in ('y','feature_sha256')})
    return row

def examples(n=130):
    rows=[]
    for i in range(n):
        ko=datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(days=3*i)
        a={k:float(i%7+1) for k in catalog('A')}
        a['num:home_elo']=1500.+i%7;a['num:away_elo']=1450.+i%5
        b={**a,**{k:(None if i%4==0 else float(i%3)) for k in catalog('B')-catalog('A')}}
        c={**b,**{k:None for k in catalog('C')-catalog('B')}}
        rows.append(rehash({'scope':'ESP','match_id':f'm_{i:06d}',
            'kickoff_utc':iso(ko),'feature_cutoff_utc':iso(ko-timedelta(minutes=90)),
            'actual_latest_source_observed_at':'2026-11-03T12:00:00Z',
            'source_observed_after_cutoff':True,'original_pit_certified':False,
            'availability_class':DOMAIN,'contract':CONTRACT,'complete_xg5_both':i%4!=0,
            'features':{'A':a,'B':b,'C':c},'y':('1','X','2')[i%3]}))
    return rows

class FakeModel:
    fits=[]
    def __init__(self,**kwargs):self.kwargs=kwargs;self.classes_=['2','1','X']
    def fit(self,x,**kwargs):
        self.fits.append((self.kwargs,x,x.get_label(),kwargs));return self
    def predict_proba(self,x):return [[.2,.6,.2] for _ in range(x.num_row())]

class FeatureSafetyTests(unittest.TestCase):
    def history(self):
        fs=[fixture(i) for i in range(20)]
        obs={('ESP',f['match_id']):observation() for f in fs}
        return fs,obs

    def test_reconstruction_uses_exact_five_and_preserves_first_observed_clock(self):
        fs,obs=self.history();r=feature_row(fs[19],fs,obs)
        self.assertEqual(r['prior5_ids']['home'],[f'm_{i:06d}' for i in range(14,19)])
        self.assertEqual(r['features']['B']['home_xg5_xg_for'],.4)
        self.assertTrue(r['complete_xg5_both'])
        self.assertTrue(r['source_observed_after_cutoff'])
        self.assertFalse(r['original_pit_certified'])
        self.assertEqual(r['actual_latest_source_observed_at'],'2026-11-03T12:00:00Z')

    def test_missing_last5_is_not_cherry_picked_from_older_verified_games(self):
        fs,obs=self.history();del obs[('ESP','m_000017')]
        r=feature_row(fs[19],fs,obs)
        self.assertFalse(r['complete_xg5_both'])
        self.assertIsNone(r['features']['B']['home_xg5_xg_for'])
        self.assertIn('m_000017',r['prior5_ids']['home'])
        self.assertNotIn('m_000013',r['prior5_ids']['home'])

    def test_zero_and_missing_statistics_are_distinct(self):
        fs,obs=self.history();r=feature_row(fs[19],fs,obs)
        self.assertEqual(r['features']['C']['home_fouls_5'],0)
        self.assertIsNone(r['features']['C']['away_fouls_5'])
        self.assertEqual(vector(r,'C',['home_fouls_5']),[0.])
        self.assertTrue(math.isnan(vector(r,'C',['away_fouls_5'])[0]))

    def test_target_score_is_not_part_of_features(self):
        fs,obs=self.history();before=feature_row(fs[19],fs,obs)
        fs[19]['goals_home_90']=25;fs[19]['goals_away_90']=0
        self.assertEqual(feature_row(fs[19],fs,obs),before)

    def test_future_and_same_kickoff_results_cannot_change_target(self):
        fs,obs=self.history();before=feature_row(fs[19],fs,obs)
        same=fixture(99);same['kickoff_utc']=fs[19]['kickoff_utc']
        self.assertEqual(feature_row(fs[19],fs+[same,fixture(100)],obs),before)

    def test_recent_match_without_three_hour_lag_is_excluded(self):
        fs,obs=self.history();r=feature_row(fs[19],fs,obs)
        recent=fixture(99);recent['kickoff_utc']=iso(datetime.fromisoformat(fs[19]['kickoff_utc'].replace('Z','+00:00'))-timedelta(hours=2))
        self.assertEqual(feature_row(fs[19],fs+[recent],obs),r)

    def test_shared_training_and_inference_definition_is_deterministic(self):
        fs,obs=self.history()
        a=feature_row(fs[19],fs,obs);b=feature_row(fs[19],fs,obs,cutoff=a['feature_cutoff_utc'])
        self.assertEqual(a['feature_sha256'],b['feature_sha256'])
        ko=datetime.fromisoformat(fs[19]['kickoff_utc'].replace('Z','+00:00'))
        with self.assertRaisesRegex(ResearchDataError,'LATE_CUTOFF'):feature_row(fs[19],fs,obs,cutoff=iso(ko))

    def test_mirrored_pitchapi_counts_require_consistency_with_shots(self):
        row=observation()
        self.assertTrue(strict_xg(row,{'shots_home':1,'shots_away':1})[0])
        self.assertFalse(strict_xg(row,{'shots_home':2,'shots_away':1})[0])
        row['items'][2]['home']='2'
        self.assertFalse(strict_xg(row,{'shots_home':1,'shots_away':1})[0])

    def test_missing_duplicate_unknown_and_fractional_count_are_quarantined(self):
        for action in ('missing','duplicate','unknown','fractional','negative'):
            row=observation()
            if action=='missing':row['items']=row['items'][:1]
            if action=='duplicate':row['items'].append(copy.deepcopy(row['items'][1]))
            if action=='unknown':row['items'][1]['group']='Other'
            if action=='fractional':row['items'][1]['home']='1.5'
            if action=='negative':row['items'][1]['home']='-1'
            with self.subTest(action=action):self.assertFalse(strict_xg(row,{'shots_home':1,'shots_away':1})[0])

    def test_invalid_xg_and_wrong_projected_xg_never_enter(self):
        for value in (None,True,float('nan'),-1,31):
            row=observation();row['xg_home']=value
            self.assertFalse(strict_xg(row,{'shots_home':1,'shots_away':1})[0])
        row=observation();row['items'][0]['home']='.8'
        self.assertFalse(strict_xg(row,{'shots_home':1,'shots_away':1})[0])

    def test_elo_and_base_features_do_not_receive_any_xg(self):
        fs,obs=self.history();row=feature_row(fs[19],fs,obs)
        self.assertEqual(set(row['features']['A']),catalog('A'))
        self.assertTrue(all('xg' not in n.lower() for n in row['features']['A']))
        self.assertEqual({k:row['features']['B'][k] for k in catalog('A')},row['features']['A'])

class TrainingMethodTests(unittest.TestCase):
    def test_calendar_folds_are_disjoint_and_inside_train(self):
        rows=examples(240);seen=set()
        for start,end in FOLDS:
            train,test,_=split_window(rows,start,end)
            self.assertLessEqual(end,VALIDATION[0])
            ids={r['match_id'] for r in test};self.assertFalse(ids&seen);seen|=ids
            if train and test:self.assertLess(train[-1]['kickoff_utc'],test[0]['kickoff_utc'])

    def test_tied_kickoffs_never_cross_boundaries_and_train_labels_need_lag(self):
        rows=examples();start='2025-09-01T00:00:00Z'
        r=copy.deepcopy(rows[0]);r['match_id']='m_tied1';r['kickoff_utc']=start
        r['feature_cutoff_utc']='2025-08-31T22:30:00Z';rehash(r)
        q=copy.deepcopy(r);q['match_id']='m_tied2';rehash(q)
        rows=sorted(rows+[r,q],key=lambda r:(r['kickoff_utc'],r['scope'],r['match_id']))
        tr,te,_=split_window(rows,start,'2026-01-01T00:00:00Z')
        self.assertFalse({'m_tied1','m_tied2'}&{r['match_id'] for r in tr})
        self.assertTrue({'m_tied1','m_tied2'}<={r['match_id'] for r in te})

    def test_only_train_selects_columns_even_when_validation_column_changes(self):
        rows=examples();name='num:home_all_5_gf_avg'
        for r in rows[:80]:
            for v in ('A','B','C'):r['features'][v][name]=1.
            rehash(r)
        before=train_columns(rows[:80],'A')
        for r in rows[80:]:
            for v in ('A','B','C'):r['features'][v][name]=999.
            rehash(r)
        self.assertEqual(train_columns(rows[:80],'A'),before)
        self.assertNotIn(name,before)

    def test_all_null_columns_are_dropped_without_zero_imputation(self):
        rows=examples();names=train_columns(rows[:80],'C')
        self.assertNotIn('home_fouls_15',names)
        self.assertTrue(math.isnan(vector(rows[0],'C',['home_fouls_15'])[0]))

    def test_no_reserved_english_data_or_fake_pit_accepted(self):
        for action in ('scope','pit','label'):
            rows=examples()
            if action=='scope':rows[0]['scope']='ENG'
            if action=='pit':rows[0]['original_pit_certified']=True
            if action=='label':rows[0]['features']['A']['target_score']=4
            rehash(rows[0])
            with self.assertRaises(ResearchDataError):validate_examples(rows)

    def test_duplicate_reordered_and_tampered_examples_fail(self):
        rows=examples()
        for bad in (rows+[rows[-1]],list(reversed(rows))):
            with self.assertRaises(ResearchDataError):validate_examples(bad)
        rows[0]['features']['B']['home_xg5_xg_for']=100
        with self.assertRaisesRegex(ResearchDataError,'HASH_MISMATCH'):validate_examples(rows)

    def test_different_base_across_variants_is_rejected(self):
        rows=examples();rows[0]['features']['B']['num:home_elo']=1800.;rehash(rows[0])
        with self.assertRaisesRegex(ResearchDataError,'BASE_FEATURE_DRIFT'):validate_examples(rows)

    def test_three_actual_fit_calls_share_train_rows_and_no_eval_set(self):
        rows=examples();FakeModel.fits=[]
        report,preds=fit_window(rows[:80],rows[80:],model_factory=FakeModel)
        self.assertEqual(len(FakeModel.fits),3)
        for params,x,y,kw in FakeModel.fits:
            self.assertEqual(params,PARAMS);self.assertEqual(x.num_row(),80)
            self.assertEqual(y,[r['y'] for r in rows[:80]])
            self.assertFalse(kw)
            self.assertGreaterEqual(len(x.get_feature_names()),5)
        self.assertEqual(len(preds),50)
        self.assertEqual(preds[0]['predictions']['B']['p_1x2'],{'1':.6,'X':.2,'2':.2})
        self.assertTrue(all(report['metrics'][v]['n']==50 for v in (M0,'A','B','C')))
        self.assertEqual(report['per_league']['ESP']['A']['n'],50)

    def test_fit_before_m0_training_end_is_forbidden(self):
        rows=examples()
        for r in rows[80:]:
            r['kickoff_utc']='2025-05-01T12:00:00Z';r['feature_cutoff_utc']='2025-05-01T10:30:00Z';rehash(r)
        with self.assertRaises(ResearchDataError):fit_window(rows[:80],rows[80:],model_factory=FakeModel)

    def test_small_samples_report_exact_shortfalls_and_no_fake_fit(self):
        report,preds=experiment(examples(30),fit=True,model_factory=FakeModel)
        self.assertFalse(preds)
        self.assertEqual(report['status'],'NO_GO_NO_MODELS_FITTED')
        for fold in report['walk_forward']:
            self.assertEqual(fold['status'],'NO_GO_TOO_FEW_ROWS')
            self.assertEqual(fold['missing_train'],80-fold['train_n'])
        self.assertEqual(report['frozen_forward_comparison']['missing_matches'],100)
        rows=examples(240)
        for row in rows:row['y']='1'
        report,preds=experiment(rows,fit=True,model_factory=FakeModel)
        self.assertFalse(preds)
        self.assertTrue(all(w['status'].startswith('NO_GO_') for w in report['walk_forward']))
        self.assertTrue(any(w['status']=='NO_GO_TRAIN_MISSING_OUTCOME_CLASS' for w in report['walk_forward']))

    def test_preflight_does_not_fit_and_validation_is_disclosed_as_reused(self):
        FakeModel.fits=[];report,preds=experiment(examples(240),fit=False,model_factory=FakeModel)
        self.assertFalse(FakeModel.fits);self.assertFalse(preds)
        self.assertFalse(report['validation']['independent_untouched_confirmation'])
        self.assertEqual(report['GATE17'],'PENDING')
        self.assertFalse(report['champion_promotion_authorized'])

    def test_ci_research_requires_explicit_manual_input_and_cannot_publish_main(self):
        path=Path(__file__).resolve().parents[1]/'.github/workflows/kb3-catboost-abc-research.yml'
        text=path.read_text()
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.run_research_fit == true",text)
        self.assertIn('default: false',text)
        self.assertIn('contents: read',text)
        self.assertIn('${RUNNER_TEMP}/abc-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}',text)
        self.assertNotIn('secrets.',text)
        self.assertNotIn('git push',text)

    def test_small_paired_sample_is_inconclusive_with_missing_count(self):
        r={'kickoff_utc':'2026-01-01T12:00:00Z','outcome_1x2':'1',
           'predictions':{'A':{'p_1x2':{'1':.6,'X':.2,'2':.2}},M0:{'p_1x2':{'1':.5,'X':.3,'2':.2}}}}
        comp=comparison([r],'A',M0)
        self.assertEqual(comp['missing_matches'],99);self.assertEqual(comp['missing_weeks'],7)
        self.assertIn('INCONCLUSIVE',comp['conclusion'])

class ReadOnlySourceTests(unittest.TestCase):
    def seed(self,path,scope='ESP'):
        from scripts.kb3_historical_pitchapi_backfill import SQL
        from src.kb3_historical_feature_quality import FIXTURE_SQL
        fs=[fixture(i,scope) for i in range(20)]
        with sqlite3.connect(path) as db:
            db.executescript(SQL+FIXTURE_SQL)
            for f in fs:
                db.execute('INSERT INTO finished_fixture_index VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (scope,f['season'],f['match_id'],f['kickoff_utc'],f['home_team_id'],f['away_team_id'],f['goals_home_90'],f['goals_away_90'],f['listing_observed_at'],'a'*64,None))
                db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (scope,f['season'],f['match_id'],f['kickoff_utc'],f['home_team_id'],f['away_team_id'],f['goals_home_90'],f['goals_away_90'],'2026-11-03T12:00:00Z',None,json.dumps(observation()['items']),3,'VERIFIED',.4,.7,1,1,'a'*64,'b'*64,'c'*64,1))

    def test_source_unchanged_and_invalid_count_quarantined_without_rewriting(self):
        from src.kb3_catboost_research_data import file_sha
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'source.sqlite';self.seed(path)
            before=file_sha(path);fs,obs,audit=load_sources(path)
            self.assertEqual(before,file_sha(path));self.assertEqual(audit['source_checks']['CONSISTENT_ARCHIVED_PAIR'],20)
            self.assertTrue(obs[('ESP','m_000000')]['xg_status']=='VERIFIED')
            with sqlite3.connect(path) as db:
                db.execute('DROP TRIGGER observations_no_update')
                db.execute("UPDATE observations SET shots_home=2 WHERE match_id='m_000000'")
            before=file_sha(path);_,obs,audit=load_sources(path)
            self.assertEqual(before,file_sha(path));self.assertEqual(audit['source_checks']['COUNT_CONFLICT'],1)
            self.assertIsNone(obs[('ESP','m_000000')]['xg_home'])
            with sqlite3.connect(path) as db:self.assertEqual(db.execute("SELECT xg_status FROM observations WHERE match_id='m_000000'").fetchone()[0],'VERIFIED')

    def test_protected_scope_and_source_identity_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'source.sqlite';self.seed(path,'ENG')
            with self.assertRaisesRegex(ResearchDataError,'PROTECTED_ENG'):load_sources(path)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'source.sqlite';self.seed(path)
            with sqlite3.connect(path) as db:
                db.execute('DROP TRIGGER observations_no_update');db.execute("UPDATE observations SET away_team_id='OTHER'")
            with self.assertRaisesRegex(ResearchDataError,'IDENTITY_DRIFT'):load_sources(path)

class OriginalFreezeBoundaryTests(unittest.TestCase):
    def setup_records(self,path):
        p={'league_country':'ESP','provider_match_id':'m_000001','kickoff_utc':'2026-11-05T18:00:00Z',
           'feature_cutoff_utc':'2026-11-05T12:00:00Z','home_team_id':'H','away_team_id':'A'}
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE forecasts(id TEXT,payload_json TEXT)')
            db.execute('INSERT INTO forecasts VALUES(?,?)',('m0',json.dumps(p)))
        r={'source_m0_forecast_sha256':'m0','variant':'A','scope':'ESP','match_id':'m_000001',
           'kickoff_utc':p['kickoff_utc'],'home_team_id':'H','away_team_id':'A',
           'feature_cutoff_utc':p['feature_cutoff_utc'],'source_last_observed_utc':'2026-11-05T11:00:00Z',
           'training_data_max_kickoff_utc':'2026-11-01T12:00:00Z','trained_at_utc':'2026-11-04T12:00:00Z',
           'generated_at_utc':'2026-11-05T12:01:00Z','availability_class':'ORIGINAL_FROZEN_PREMATCH',
           'feature_contract':CONTRACT,'model_version':'ABC_RESEARCH_V1','model_sha256':'b'*64,
           'p_1x2':{'1':.6,'X':.2,'2':.2}}
        r['prediction_sha256']=digest(r)
        settled=[{'id':'m0','label':'1','p':{'1':.5,'X':.3,'2':.2}}]
        return r,patch('src.kb3_step16_progressive_shadow.verified_rows',return_value=settled)

    def attest(self,r):return {'archived_payload_sha256':digest(r),'archive_sha256':'a'*64,'server_created_utc':'2026-11-05T12:02:00Z'}

    def test_same_original_fixture_and_externally_attested_payload_can_be_paired(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m0.sqlite';r,context=self.setup_records(p)
            with context:out=compare_original_m0(p,[r],attest=self.attest)
            self.assertEqual(out['models']['A']['comparison']['common_n'],1)
            self.assertEqual(out['models']['A']['comparison']['missing_matches'],99)
            self.assertIsNone(out['models']['B']['metrics'])

    def test_no_boolean_or_hash_alone_substitutes_for_independent_attestation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m0.sqlite';r,context=self.setup_records(p)
            with context,self.assertRaisesRegex(ResearchDataError,'ATTESTATION_VALIDATOR'):compare_original_m0(p,[r])

    def test_replay_late_model_future_source_and_wrong_team_never_join_freezes(self):
        for action in ('replay','late_model','future_source','wrong_team'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as td:
                p=Path(td)/'m0.sqlite';r,context=self.setup_records(p)
                if action=='replay':r['availability_class']=DOMAIN
                if action=='late_model':r['trained_at_utc']='2026-11-06T12:00:00Z'
                if action=='future_source':r['source_last_observed_utc']='2026-11-05T13:00:00Z'
                if action=='wrong_team':r['away_team_id']='OTHER'
                r['prediction_sha256']=digest({k:v for k,v in r.items() if k!='prediction_sha256'})
                with context,self.assertRaises(ResearchDataError):compare_original_m0(p,[r],attest=self.attest)

if __name__=='__main__':unittest.main()
