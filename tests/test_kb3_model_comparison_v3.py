"""Synthetic metric/cohort tests. Real ledger verification is a separate audit."""
import copy
from datetime import datetime,timedelta,timezone
import unittest
from src.kb3_model_comparison_v3 import compare_games
from src.kb3_p1_shared_asof_features_v2 import SharedAsOfError


def rows(weeks=1):
    result=[]
    for i in range(weeks):
        kickoff=datetime(2025,1,4,20,tzinfo=timezone.utc)+timedelta(weeks=i)
        cutoff=kickoff-timedelta(hours=2)
        result.append(dict(fixture_id=str(i),league='ESP',kickoff_utc=kickoff.isoformat().replace('+00:00','Z'),
            result_observed_utc=(kickoff+timedelta(hours=4)).isoformat().replace('+00:00','Z'),outcome_1x2='1',
            predictions={e:dict(model_version=e+'_VERSION',p_1x2={'1':p,'X':.2,'2':.8-p},
            feature_cutoff_utc=cutoff.isoformat().replace('+00:00','Z'),
            frozen_at_utc=cutoff.isoformat().replace('+00:00','Z'),horizon='EARLY_90MIN_OR_MORE',
            github_server_artifact_verified=True,forecast_hash_verified=True)
            for e,p in [('A',.6),('B',.3)]}))
    return result


class FairComparisonTests(unittest.TestCase):
    versions={'A':'A_VERSION','B':'B_VERSION'}
    def test_exact_metrics_calibration_and_small_sample_no_fake_ci(self):
        report=compare_games(rows(),self.versions)
        pair=report['pairwise']['A__vs__B'];self.assertEqual(pair['common_n'],1)
        self.assertAlmostEqual(pair['scores']['A']['brier_sum3'],.24)
        self.assertEqual(pair['scores']['A']['top1_accuracy'],1)
        self.assertEqual(pair['scores']['B']['top1_accuracy'],0)
        self.assertAlmostEqual(pair['scores']['A']['classwise_reliability_10bins']['1'][0]['observed_frequency'],1.)
        for m in ('top1_accuracy','brier_sum3','log_loss'):
            d=pair['paired_deltas'][m]
            self.assertIsNone(d['ci95']);self.assertEqual(d['status'],'INSUFFICIENT_INDEPENDENT_WEEKS')
        self.assertAlmostEqual(pair['paired_deltas']['top1_ece_10bins']['delta_left_minus_right'],-.1)
        self.assertAlmostEqual(pair['paired_deltas']['brier_sum3']['delta_left_minus_right'],-.54)
    def test_no_union_or_marginal_metrics_as_fair_comparison(self):
        data=rows(3);del data[0]['predictions']['B'];del data[2]['predictions']['A']
        report=compare_games(data,self.versions)
        self.assertEqual(report['coverage'],{'A':2,'B':2})
        self.assertEqual(report['pairwise']['A__vs__B']['common_n'],1)
        self.assertEqual(report['all_registered_models']['common_n'],1)
    def test_week_blocks_preserve_same_match_pairs_and_missing_new_model(self):
        data=rows(10)
        report=compare_games(data,{**self.versions,'C':'C_VERSION'},replicates=100)
        self.assertEqual(report['all_registered_models']['common_n'],0)
        self.assertEqual(report['available_model_intersection']['common_n'],10)
        delta=report['pairwise']['A__vs__B']['paired_deltas']['brier_sum3']
        self.assertEqual(delta['week_blocks'],10)
        self.assertAlmostEqual(delta['ci95'][0],delta['delta_left_minus_right'])
        self.assertFalse(report['champion_changed'])
    def test_mixed_versions_unattested_late_and_protected_refused(self):
        for field,value,error in [('model_version','another','MIXED_MODEL_VERSIONS'),
            ('github_server_artifact_verified',False,'UNATTESTED'),
            ('frozen_at_utc','2025-01-04T20:00:00Z','LATE'),
            ('feature_cutoff_utc','2025-01-04T17:59:00Z','DIFFERENT_FEATURE_CUTOFFS')]:
            data=rows();data[0]['predictions']['A'][field]=value
            with self.assertRaisesRegex(SharedAsOfError,error):compare_games(data,self.versions)
        data=rows();data[0]['league']='ENG'
        with self.assertRaisesRegex(SharedAsOfError,'PROTECTED'):compare_games(data,self.versions)
        with self.assertRaisesRegex(SharedAsOfError,'DUPLICATE'):compare_games(rows()+rows(),self.versions)


class LedgerAdapterTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        import sqlite3
        import json
        from pathlib import Path
        from src.kb3_model_comparison_v3 import M0,hashobj
        from src.kb3_step17_engine_comparison import loss
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'synthetic.sqlite'
        p=dict(model_version=M0,league_country='ESP',provider_match_id='synthetic',
               kickoff_utc='2025-01-04T20:00:00Z',feature_cutoff_utc='2025-01-04T18:00:00Z',
               generated_at_utc='2025-01-04T18:00:00Z',feature_sha256='a'*64,
               source_chain_sha256='b'*64,p_1x2={'1':.6,'X':.2,'2':.2})
        fid=hashobj(p);p['forecast_sha256']=fid
        proof=dict(forecast_id=fid,model=M0,original_forecast_sha256=fid,
            source='GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES',
            github_server_event_utc='2025-01-04T18:01:00Z',audit_utc='2025-01-05T01:00:00Z')
        proof['proof_id']=hashobj(proof)
        ll,bs,_=loss(p['p_1x2'],'1')
        s=dict(forecast_id=fid,league='ESP',native_match_id='synthetic',score_home=2,score_away=1,
               outcome='1',observed_utc='2025-01-05T01:00:00Z',source_chain_sha256='c'*64,log_loss=ll,brier_sum3=bs)
        sh=hashobj(s);s['provider_source_chain_sha256']=s.pop('source_chain_sha256');s['settlement_sha256']=sh
        f=dict(id=fid,model=M0,league='ESP',native_match_id='synthetic',kickoff_utc=p['kickoff_utc'],
               captured_at_utc=p['feature_cutoff_utc'],payload_json=json.dumps(p))
        with sqlite3.connect(self.path) as db:
            for name,data in [('forecasts',f),('settlements',s),('m0720_github_push_proofs',proof)]:
                db.execute('CREATE TABLE '+name+' ('+','.join(k+(' INTEGER' if type(v) is int else ' REAL' if type(v) is float else ' TEXT') for k,v in data.items())+')')
                db.execute('INSERT INTO '+name+' VALUES('+','.join('?' for _ in data)+')',list(data.values()))
    def test_read_only_adapter_keeps_original_bytes_and_validates_scores(self):
        from src.kb3_model_comparison_v3 import ledger_games,file_sha
        before=file_sha(self.path);games,audit=ledger_games(self.path)
        self.assertEqual(len(games),1);self.assertEqual(before,file_sha(self.path))
        self.assertTrue(audit['source_unchanged'])
    def test_corrupt_proof_rejected_without_repairing_or_rewriting(self):
        import sqlite3
        from src.kb3_model_comparison_v3 import ledger_games,file_sha
        with sqlite3.connect(self.path) as db:db.execute("UPDATE m0720_github_push_proofs SET proof_id='forged'")
        before=file_sha(self.path)
        with self.assertRaisesRegex(SharedAsOfError,'SHA_MISMATCH'):ledger_games(self.path)
        self.assertEqual(before,file_sha(self.path))


if __name__=='__main__':unittest.main()
