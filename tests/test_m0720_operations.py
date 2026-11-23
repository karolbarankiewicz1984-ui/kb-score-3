"""Synthetic regressions only; actual counts come from the read-only audit."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from contextlib import ExitStack
import hashlib,json,math,shutil,sqlite3,tempfile,unittest
from zoneinfo import ZoneInfo

from src.kb3_step16_m0_720_eight_forward import (
    MODEL,EIGHT,make_forecasts,trained_params,stamp,hashobj,freeze_sqlite,settle_sqlite,
    run,collect_receipts,Research720Error,DB,
)
from src.kb3_step16_run_policy import forecast_due,forecast_state
from scripts.step16_m0_mode_guard import select,FORECAST_CRONS,SETTLE_CRONS
from src.kb3_step16_m0_720_calibration import calibrate_if_eligible,append_proofs
from scripts.audit_m0720_operations import audit
from test_step16_m0_720_eight_forward import fake_receipts
from test_step16_m0_720_calibration import sample,add_synthetic_settlements_and_host_proofs

NOW=datetime(2026,11,4,6,tzinfo=timezone.utc)
def sources(at=NOW):
    rows=deepcopy(fake_receipts())
    for r in rows:
        r['completed_at_utc']=stamp(at-timedelta(minutes=5))
        for i,m in enumerate(r['payload']['matches']):
            if m['status']!='finished':
                j=i-250
                m['time_utc']=stamp(NOW+timedelta(hours=5+j) if j<8 else NOW+timedelta(days=20+j//10))
    return rows
def build(data=None,**kwargs):
    p,sha,manifest=trained_params()
    return make_forecasts(data or sources(),cutoff=NOW,params=p,param_sha=sha,manifest_sha=manifest,**kwargs)
def write_meta(path,at,mode='forecast',attempt=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    d={'model_version':MODEL,'mode':mode,'run_utc':stamp(at)}
    key='attempt_sha256' if attempt else 'report_sha256';d[key]=hashobj(d)
    path.write_text(json.dumps(d))
def fake_seal(receipts,pub,out,manifest):
    # Mock publication fixture, explicitly not a cryptographic/network proof.
    Path(out).write_bytes(b'SYNTHETIC_TEST_ONLY')
    value={'ciphertext_sha256':hashlib.sha256(Path(out).read_bytes()).hexdigest(),
           'proof':{'final_chain_sha256':receipts[-1]['chain_sha256']},'origin':'SYNTHETIC_TEST'}
    Path(manifest).write_text(json.dumps(value));return value
class FakeChallengers:
    def records(self,feature,parent):return []
def fake_children(db,records,*,new_m0_ids):
    return {'new_challengers':2*len(new_m0_ids),'new_common_fixture_pairs':len(new_m0_ids)}

class SelectionTests(unittest.TestCase):
    def test_known_fixtures_do_not_consume_new_quota(self):
        data=sources();current=next(x['payload']['matches'] for x in data if ':ESP:2026/' in x['resource'])
        for i in range(250,275):current[i]['time_utc']=stamp(NOW+timedelta(hours=5+i-250))
        before,_,_=build(data);known={(x['league_country'],x['provider_match_id']) for x in before}
        diag={};after,per,_=build(data,known_fixtures=known,diagnostics=diag)
        self.assertEqual(per['ESP'],10)
        self.assertFalse(known&{(x['league_country'],x['provider_match_id']) for x in after})
        self.assertEqual(diag['reason_counts']['ESP']['ALREADY_FROZEN'],10)
        self.assertEqual(diag['reason_counts']['ESP']['NEW_ELIGIBLE_OVER_QUOTA'],5)

    def test_diagnostics_partition_all_current_rows_without_changing_predictions(self):
        data=sources();diag={};a,_,_=build(data);b,_,_=build(data,diagnostics=diag)
        self.assertEqual(a,b)
        for c,_,_ in EIGHT:
            n=len(next(x['payload']['matches'] for x in data if x['resource']==f'pitchapi:m0720:fixtures:{c}:2026/2027'))
            self.assertEqual(sum(diag['reason_counts'][c].values()),n)

    def test_each_missing_history_side_is_reported(self):
        data=sources();current=next(x['payload']['matches'] for x in data if ':ESP:2026/' in x['resource'])
        current[250]['home_team']['id']='synthetic-new-home'
        current[251]['away_team']['id']='synthetic-new-away'
        current[252]['home_team']['id']='synthetic-new-home2';current[252]['away_team']['id']='synthetic-new-away2'
        diag={};build(data,diagnostics=diag)
        for reason in ('HOME_HISTORY5_SHORT','AWAY_HISTORY5_SHORT','BOTH_HISTORY5_SHORT'):
            self.assertEqual(diag['reason_counts']['ESP'][reason],1)

    def test_ninety_minutes_and_7_day_exact_boundaries(self):
        data=sources();current=next(x['payload']['matches'] for x in data if ':ESP:2026/' in x['resource'])
        current[250]['time_utc']=stamp(NOW+timedelta(minutes=90))
        current[251]['time_utc']=stamp(NOW+timedelta(days=7))
        current[252]['time_utc']=stamp(NOW+timedelta(days=7,seconds=1))
        diag={};items,_,_=build(data,diagnostics=diag);ids={x['provider_match_id'] for x in items}
        self.assertNotIn(current[250]['id'],ids);self.assertIn(current[251]['id'],ids)
        self.assertNotIn(current[252]['id'],ids)
        self.assertEqual(diag['reason_counts']['ESP']['INSIDE_90MIN_OR_PAST'],1)
        self.assertGreaterEqual(diag['reason_counts']['ESP']['OUTSIDE_7D'],1)

    def test_processing_delay_never_generates_a_late_target(self):
        data=sources();diag={};items,_,_=build(data,diagnostics=diag,wall_clock=lambda:NOW+timedelta(hours=3,minutes=30))
        first={r['payload']['matches'][250]['id'] for r in data if r['resource'].endswith('2026/2027')}
        self.assertFalse(first&{x['provider_match_id'] for x in items})
        self.assertEqual(sum(c.get('TOO_LATE_DURING_BUILD',0) for c in diag['reason_counts'].values()),8)

class ScheduleTests(unittest.TestCase):
    def test_intraday_runs_have_gap_and_three_attempt_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'sources';dest=Path(tmp)/'forecasts'
            self.assertTrue(forecast_due(source,dest,NOW)[0])
            for hour in (0,3,6):
                at=NOW+timedelta(hours=hour);d=source/at.date().isoformat()/('forecast-'+at.strftime('%H%M%S%f'))
                write_meta(d/'ATTEMPT.json',at,attempt=True);write_meta(d/'RECEIPT.json',at)
                if hour==0:
                    self.assertFalse(forecast_due(source,dest,at+timedelta(hours=1))[0])
                    self.assertTrue(forecast_due(source,dest,at+timedelta(hours=2))[0])
            self.assertEqual(forecast_due(source,dest,NOW+timedelta(hours=9)),(False,'FORECAST_ATTEMPT_DAILY_CAP'))

    def test_failed_attempt_can_retry_without_daily_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'sources';dest=Path(tmp)/'forecasts'
            d=source/NOW.date().isoformat()/'forecast-060000000000'
            write_meta(d/'ATTEMPT.json',NOW,attempt=True)
            self.assertFalse(forecast_due(source,dest,NOW+timedelta(minutes=4))[0])
            self.assertTrue(forecast_due(source,dest,NOW+timedelta(minutes=5))[0])

    def test_legacy_mirror_does_not_double_count_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'sources';dst=Path(tmp)/'forecasts';day=NOW.date().isoformat()
            write_meta(src/day/'forecast'/'RECEIPT.json',NOW)
            write_meta(dst/day/'FROZEN_M0_720_EIGHT.json',NOW)
            self.assertEqual(len(forecast_state(src,dst,NOW)['attempts']),1)
            self.assertTrue(forecast_due(src,dst,NOW+timedelta(hours=3))[0])

    def test_corrupt_marker_is_local_review_not_a_new_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'sources';dst=Path(tmp)/'forecasts';p=src/NOW.date().isoformat()/'forecast-060000'/'ATTEMPT.json'
            p.parent.mkdir(parents=True);p.write_text('{}')
            self.assertEqual(forecast_due(src,dst,NOW),(False,'LOCAL_FORECAST_METADATA_REVIEW_REQUIRED'))

    def test_day_boundary_gives_new_daily_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'sources';dst=Path(tmp)/'forecasts'
            for i in range(3):write_meta(src/'2026-11-03'/f'forecast-{i}'/'ATTEMPT.json',NOW-timedelta(hours=10-i),attempt=True)
            self.assertTrue(forecast_due(src,dst,NOW)[0])

    def test_all_three_settlement_slots_and_push_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);at=NOW.replace(hour=8,minute=17)
            write_meta(root/'data/pit_sidecar/m0_720_eight'/at.date().isoformat()/'settle-081700000000'/'RECEIPT.json',at,mode='settle')
            self.assertEqual(select(event='schedule',cron=SETTLE_CRONS[0],user_mode='',now=at+timedelta(hours=6),root=root)[0],'settle')
            self.assertEqual(select(event='push',cron='',user_mode='',now=at+timedelta(hours=10),root=root)[0],'skip')

    def test_utc_schedule_warsaw_dst_and_naive_clock(self):
        self.assertEqual(NOW.replace(hour=6,minute=21).astimezone(ZoneInfo('Europe/Warsaw')).hour,7)
        self.assertEqual(NOW.replace(month=7,hour=6,minute=21).astimezone(ZoneInfo('Europe/Warsaw')).hour,8)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'UTC_REQUIRED'):
                select(event='schedule',cron=FORECAST_CRONS[0],user_mode='',now=NOW.replace(tzinfo=None),root=root)

class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'ledger.sqlite';self.item=build()[0][0]
        _,self.sha,self.manifest=trained_params()
        freeze_sqlite(self.db,[self.item],param_sha=self.sha,manifest_sha=self.manifest,now=NOW)
        self.ko=datetime.fromisoformat(self.item['kickoff_utc'].replace('Z','+00:00'))
        self.result={'id':self.item['provider_match_id'],'time_utc':self.item['kickoff_utc'],'status':'finished',
            'home_team':{'id':self.item['home_team_id']},'away_team':{'id':self.item['away_team_id']},'score_home':0,'score_away':0}
    def settle(self,result=None,at=None):
        return settle_sqlite(self.db,{(self.item['league_country'],self.item['provider_match_id']):result or self.result},
            observed_at=at or self.ko+timedelta(hours=3),source_chain_sha='a'*64)

    def test_zero_result_and_exact_three_hour_boundary_scores(self):
        self.assertEqual(self.settle(at=self.ko+timedelta(hours=3)-timedelta(microseconds=1))['new_settlements'],0)
        out=self.settle();self.assertEqual(out['new_settlements'],1)
        p=self.item['p_1x2'];self.assertAlmostEqual(out['metrics']['log_loss'],-math.log(p['X']))
        self.assertAlmostEqual(out['metrics']['brier_sum3'],sum((p[k]-int(k=='X'))**2 for k in ('1','X','2')))

    def test_wrong_match_id_never_settles(self):
        bad=deepcopy(self.result);bad['id']='different-native-id'
        out=self.settle(bad);self.assertEqual(out['settlement_reason_counts'],{'RESULT_NATIVE_MATCH_ID_MISMATCH':1})
        self.assertEqual(out['total_settlements'],0)

    def test_utc_spelling_same_instant_is_accepted(self):
        self.result['time_utc']=self.ko.isoformat()
        self.assertEqual(self.settle()['new_settlements'],1)

    def test_changed_kickoff_swapped_teams_and_bad_score_stay_pending(self):
        for key,value,reason in [('time_utc',stamp(self.ko+timedelta(days=1)),'KICKOFF_CHANGED_REVIEW_REQUIRED'),
                                  ('score_home',None,'RESULT_SCORE_INVALID'),('score_away',True,'RESULT_SCORE_INVALID'),('status','postponed','RESULT_NOT_FINISHED')]:
            bad=deepcopy(self.result);bad[key]=value
            self.assertIn(reason,self.settle(bad)['settlement_reason_counts'])
        bad=deepcopy(self.result);bad['home_team'],bad['away_team']=bad['away_team'],bad['home_team']
        self.assertIn('RESULT_TEAM_SIDE_MISMATCH',self.settle(bad)['settlement_reason_counts'])
        self.assertEqual(self.settle()['new_settlements'],1)

    def test_changed_kickoff_emits_both_verified_clocks_but_never_settles(self):
        for days in (1, -1):
            changed=deepcopy(self.result)
            revised=self.ko+timedelta(days=days)
            changed['time_utc']=stamp(revised)
            result=self.settle(changed,at=self.ko+timedelta(days=4))
            self.assertEqual(result['new_settlements'],0)
            self.assertEqual(result['total_settlements'],0)
            self.assertEqual(result['not_yet_settled'],1)
            self.assertEqual(result['settlement_reason_counts'],
                             {'KICKOFF_CHANGED_REVIEW_REQUIRED':1})
            decision=result['settlement_decisions'][0]
            self.assertEqual(decision['original_kickoff_utc'],
                             self.item['kickoff_utc'])
            self.assertEqual(decision['provider_reported_kickoff_utc'],
                             stamp(revised))
            self.assertEqual(decision['kickoff_delta_minutes'],days*1440)
            self.assertEqual(decision['original_forecast_capture_utc'],
                             self.db_capture())
            self.assertTrue(decision['provider_home_id_matches_original'])
            self.assertTrue(decision['provider_away_id_matches_original'])
            self.assertTrue(decision['manual_review_required'])
            self.assertFalse(decision['automatic_settlement_permitted'])
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM settlements').fetchone()[0],0)
            self.assertEqual(json.loads(db.execute(
                'SELECT payload_json FROM forecasts').fetchone()[0]),self.item)

    def db_capture(self):
        with sqlite3.connect(self.db) as db:
            return db.execute('SELECT captured_at_utc FROM forecasts').fetchone()[0]

    def test_repeat_and_duplicate_forecast_never_change_original(self):
        self.settle();self.assertEqual(self.settle()['new_settlements'],0)
        changed=deepcopy(self.item);changed['generated_at_utc']=stamp(NOW+timedelta(minutes=1));changed['forecast_sha256']=hashobj({k:v for k,v in changed.items() if k!='forecast_sha256'})
        self.assertEqual(freeze_sqlite(self.db,[changed],param_sha=self.sha,manifest_sha=self.manifest,now=NOW),(0,1))
        with sqlite3.connect(self.db) as db:
            self.assertEqual(json.loads(db.execute('SELECT payload_json FROM forecasts').fetchone()[0]),self.item)

class PublicationTests(unittest.TestCase):
    def context(self,tmp,data=None,clock=None):
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch('src.kb3_step16_m0_720_eight_forward.collect_receipts',return_value=(data or sources(),list(EIGHT),17)))
        stack.enter_context(patch('src.kb3_step16_m0_720_eight_forward.seal',side_effect=fake_seal))
        stack.enter_context(patch('src.kb3_step17_forward_challengers.Challengers',FakeChallengers))
        stack.enter_context(patch('src.kb3_step17_forward_challengers.freeze_new_challengers',side_effect=fake_children))
        return {'mode':'forecast','client':object(),'now':NOW,'root':Path(tmp)/'source','forecast_root':Path(tmp)/'forecast',
                'db_path':Path(tmp)/'db.sqlite','clock':clock or (lambda:NOW)}

    def test_two_runs_same_day_append_new_games_preserving_old_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.context(tmp);first=run(**args);self.assertEqual(first['new_forecasts'],64)
            before=[]
            with sqlite3.connect(args['db_path']) as db:before=db.execute('SELECT id,payload_json FROM forecasts ORDER BY id').fetchall()
            args['now']=NOW+timedelta(hours=3);args['clock']=lambda:NOW+timedelta(hours=3)
            data=sources(args['now'])
            for r in data:
                if r['resource'].endswith('2026/2027'):r['payload']['matches'][258]['time_utc']=stamp(NOW+timedelta(hours=14))
            with patch('src.kb3_step16_m0_720_eight_forward.collect_receipts',return_value=(data,list(EIGHT),17)):
                second=run(**args)
            self.assertEqual(second['new_forecasts'],8);self.assertEqual(second['total_forecasts'],72)
            with sqlite3.connect(args['db_path']) as db:
                self.assertTrue(set(before)<=set(db.execute('SELECT id,payload_json FROM forecasts')))
            self.assertEqual(len(list(Path(args['forecast_root']).glob('*/*/FROZEN_M0_720_EIGHT.json'))),2)

    def test_failed_api_has_no_freeze_and_can_retry_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.context(tmp);error=Research720Error('PROVIDER_CAPTURE_FAILED')
            error.capture_detail={'resource':'pitchapi:m0720:catalog','network_calls':1,'error_type':'TimeoutError'}
            error.partial_receipts=[]
            with patch('src.kb3_step16_m0_720_eight_forward.collect_receipts',side_effect=error):
                with self.assertRaises(Research720Error):run(**args)
            self.assertFalse(args['db_path'].exists());self.assertFalse(list(args['root'].glob('*/*/RECEIPT.json')))
            self.assertTrue(list(args['root'].glob('*/*/FAILURE.json')))
            args['now']=NOW+timedelta(minutes=6);args['clock']=lambda:NOW+timedelta(minutes=6)
            self.assertEqual(run(**args)['new_forecasts'],64)

    def test_publish_error_after_mirror_cannot_modify_database_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.context(tmp);shutil.copy2(DB,args['db_path']);before=Path(args['db_path']).read_bytes()
            with patch('src.kb3_step16_m0_720_eight_forward.os.replace',side_effect=OSError('synthetic publish failure')):
                with self.assertRaises(OSError):run(**args)
            self.assertEqual(args['db_path'].read_bytes(),before)
            self.assertFalse(list(args['root'].glob('*/*/RECEIPT.json')))
            self.assertFalse(list(args['forecast_root'].glob('*/*/FROZEN_M0_720_EIGHT.json')))

    def test_expired_final_publication_rolls_back_all_new_forecasts(self):
        import src.kb3_step16_m0_720_eight_forward as module
        real_freeze=module.freeze_sqlite
        with tempfile.TemporaryDirectory() as tmp:
            state={'clock':NOW};args=self.context(tmp,clock=lambda:state['clock'])
            def delayed(*a,**kw):
                result=real_freeze(*a,**kw);state['clock']=NOW+timedelta(hours=4);return result
            with patch.object(module,'freeze_sqlite',side_effect=delayed):
                with self.assertRaisesRegex(Research720Error,'PUBLICATION_DEADLINE'):run(**args)
            self.assertFalse(args['db_path'].exists())

    def test_default_sdk_retries_rejected_before_any_provider_call(self):
        client=SimpleNamespace(_max_retries=2,leagues=SimpleNamespace(list=Mock()))
        with tempfile.TemporaryDirectory() as tmp:
            args=self.context(tmp);args['client']=client
            with self.assertRaisesRegex(Research720Error,'SDK_RETRIES'):run(**args)
        client.leagues.list.assert_not_called()

    def test_provider_exception_records_type_and_never_secret_text(self):
        client=SimpleNamespace(leagues=SimpleNamespace(list=Mock(side_effect=TimeoutError('synthetic-sensitive-text'))))
        with self.assertRaises(Research720Error) as error:collect_receipts(client,mode='forecast',now=NOW)
        self.assertNotIn('synthetic-sensitive',str(error.exception))
        self.assertEqual(error.exception.capture_detail['network_calls'],1)

class CalibrationPartitionTests(unittest.TestCase):
    def test_prefit_predictions_settled_later_are_not_holdout(self):
        from test_step16_m0_720_calibration import NOW as base_now
        _,sha,manifest=trained_params()
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'calibration.sqlite';first=[sample(i,sha,manifest,before=True) for i in range(100)]
            freeze_sqlite(db,first,param_sha=sha,manifest_sha=manifest,now=base_now)
            append_proofs(db,add_synthetic_settlements_and_host_proofs(db,first,now=base_now),now=base_now)
            fitted=calibrate_if_eligible(db,now=base_now);self.assertTrue(fitted['calibrator_exists'])
            with sqlite3.connect(db) as cn:
                candidate=json.loads(cn.execute('SELECT payload_json FROM m0720_calibrators').fetchone()[0])
                self.assertEqual(len(set(candidate['training_forecast_ids'])),100)
            before=[sample(i,sha,manifest,before=False) for i in range(100,150)]
            for i,x in enumerate(before):
                x['generated_at_utc']=stamp(base_now-timedelta(hours=1)) if i<25 else candidate['fitted_at_utc']
                x['kickoff_utc']=stamp(base_now+timedelta(days=2))
                x['forecast_sha256']=hashobj({k:v for k,v in x.items() if k!='forecast_sha256'})
            freeze_sqlite(db,before,param_sha=sha,manifest_sha=manifest,now=base_now)
            later=base_now+timedelta(days=4)
            append_proofs(db,add_synthetic_settlements_and_host_proofs(db,before,now=later),now=later)
            report=calibrate_if_eligible(db,now=later)
            self.assertEqual(report['post_fit_newly_created_settled_verified'],0)
            self.assertFalse(report['holdout_review_exists']);self.assertEqual(report['missing_post_fit_holdout'],50)

if __name__=='__main__':unittest.main()
