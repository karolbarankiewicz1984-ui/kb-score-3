"""Synthetic source fixtures only: never real PIT, production fits or forecasts."""
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from src.kb3_features import digest
from src.kb3_p1_shared_asof_features_v2 import build_shared_features, SharedAsOfError
from src.kb3_catboost_research_v3 import (
    contract,vector,verified_view,verified_label,split,fit,load_model,shadow,
    GithubArchives,evaluate_frozen_holdout,CONTRACT_SHA,
)


def stamp(dt):return dt.isoformat().replace('+00:00','Z')


class SyntheticArchives:
    """Test adapter. Production CLI uses only independently fetched GitHub data."""
    def __init__(self):self.docs={}
    def add(self,doc,created):
        raw=json.dumps(doc,sort_keys=True).encode();sha=hashlib.sha256(raw).hexdigest()
        ref=dict(artifact_id=str(len(self.docs)+1),member='source.json',sha256=sha)
        self.docs[ref['artifact_id']]=(copy.deepcopy(doc),created)
        return ref
    def read(self,ref):return copy.deepcopy(self.docs[ref['artifact_id']])


def sample(store,index=0,kickoff=None):
    ko=kickoff or datetime(2025,1,10,20,tzinfo=timezone.utc)+timedelta(days=index)
    cutoff=ko-timedelta(hours=2);observed=cutoff-timedelta(minutes=20)
    target=dict(league='ESP',fixture_id='target'+str(index),home_team_id='A',away_team_id='B',
                kickoff_utc=stamp(ko),season_start_year=2025)
    rows=[]
    for n in range(6):
        rows.append(dict(league='ESP',fixture_id='old'+str(index)+'_'+str(n),
            home_team_id='A' if n%2 else 'B',away_team_id='C'+str(n),season_start_year=2025,
            kickoff_utc=stamp(ko-timedelta(days=8+n)),status='FINISHED',
            goals_home_90=(index+n)%4,goals_away_90=n%3))
    def native(row,target=False):
        return dict(id=row['fixture_id'],time_utc=row['kickoff_utc'],
            home_team={'id':row['home_team_id']},away_team={'id':row['away_team_id']},
            status='scheduled' if target else 'finished',
            score_home=None if target else row['goals_home_90'],
            score_away=None if target else row['goals_away_90'])
    raw=dict(matches=[native(target,True)]+[native(r) for r in rows])
    ref=store.add(raw,observed+timedelta(minutes=1))
    receipt=dict(source_class='NETWORK_OBSERVED',observed_completed_at_utc=stamp(observed),
                 captured_at_utc=stamp(observed),source_sha256=ref['sha256'])
    for r in rows:r['result_receipt']=copy.deepcopy(receipt)
    inp=dict(target=target,cutoff_utc=stamp(cutoff),target_receipt=copy.deepcopy(receipt),predecessor_rows=rows)
    inp_ref=store.add(inp,cutoff-timedelta(minutes=1))
    label_raw=native(target,True);label_raw.update(status='finished',score_home=[2,1,0][index%3],score_away=1)
    label_at=ko+timedelta(hours=4)
    label_ref=store.add(dict(matches=[label_raw]),label_at)
    return dict(input=inp,input_archive=inp_ref,source_archives={ref['sha256']:ref},
        label=dict(outcome_1x2=['1','X','2'][index%3],observed_utc=stamp(label_at),archive=label_ref))


PLAN=dict(train_end_utc='2025-01-20T00:00:00Z',validation_start_utc='2025-02-01T00:00:00Z',
          validation_end_utc='2025-02-20T00:00:00Z',holdout_start_utc='2025-03-01T00:00:00Z')


class ContractTests(unittest.TestCase):
    def setUp(self):self.store=SyntheticArchives();self.s=sample(self.store)
    def test_exact_contract_and_train_forward_parity(self):
        self.assertEqual(contract()['feature_count'],87)
        self.assertEqual(digest(contract()),CONTRACT_SHA)
        a=build_shared_features(purpose='TRAIN',**self.s['input'])
        b=verified_view(self.s,self.store,'FORWARD')
        self.assertEqual(vector(a),vector(b))
        self.assertEqual(len(vector(a)),87)
        self.assertTrue(any(v is None for v in vector(a)))
    def test_recomputed_input_is_not_old_byte_evidence(self):
        self.s['input']['predecessor_rows'][0]['goals_home_90']=9
        with self.assertRaisesRegex(SharedAsOfError,'ARCHIVED_INPUT_BYTES_DIFFER'):
            verified_view(self.s,self.store)
    def test_late_archive_rejects_plausible_declared_old_clocks(self):
        aid=self.s['input_archive']['artifact_id'];doc,_=self.store.docs[aid]
        self.store.docs[aid]=(doc,datetime(2026,1,1,tzinfo=timezone.utc))
        with self.assertRaisesRegex(SharedAsOfError,'ARCHIVE_NOT_AVAILABLE_AT_CUTOFF'):
            verified_view(self.s,self.store)
    def test_native_score_cannot_be_substituted(self):
        ref=next(iter(self.s['source_archives'].values()))
        self.store.docs[ref['artifact_id']][0]['matches'][1]['score_home']=19
        with self.assertRaisesRegex(SharedAsOfError,'SOURCE_SCORE_DRIFT'):
            verified_view(self.s,self.store)
    def test_native_target_already_finished_refused(self):
        ref=next(iter(self.s['source_archives'].values()))
        self.store.docs[ref['artifact_id']][0]['matches'][0]['status']='finished'
        with self.assertRaisesRegex(SharedAsOfError,'TARGET_SOURCE_ALREADY_FINISHED'):
            verified_view(self.s,self.store)
    def test_label_is_separate_and_late_train_label_rejected(self):
        old=vector(verified_view(self.s,self.store))
        self.s['label']['outcome_1x2']='X'
        self.assertEqual(old,vector(verified_view(self.s,self.store)))
        with self.assertRaisesRegex(SharedAsOfError,'LABEL_SCORE_MISMATCH'):
            verified_label(self.s,self.store,self.s['input']['target'])
        self.s['label']['outcome_1x2']='1'
        with self.assertRaisesRegex(SharedAsOfError,'ARCHIVE_NOT_AVAILABLE_AT_CUTOFF'):
            verified_label(self.s,self.store,self.s['input']['target'],'2025-01-10T21:00:00Z')
    def test_split_protected_duplicates_embargo_holdout_and_ties(self):
        valid=sample(self.store,20,datetime(2025,2,2,20,tzinfo=timezone.utc))
        self.assertEqual([len(x) for x in split([self.s,valid],PLAN)],[1,1])
        for change,error in [({'league':'ENG'},'PROTECTED'),({'kickoff_utc':'2025-03-02T20:00:00Z'},'HOLDOUT')]:
            bad=copy.deepcopy(self.s);bad['input']['target'].update(change)
            with self.assertRaisesRegex(SharedAsOfError,error):split([bad,valid],PLAN)
        with self.assertRaisesRegex(SharedAsOfError,'DUPLICATE'):split([self.s,self.s,valid],PLAN)
        bad=copy.deepcopy(PLAN);bad['validation_start_utc']=bad['train_end_utc']
        with self.assertRaisesRegex(SharedAsOfError,'EMBARGO'):split([self.s,valid],bad)
        bad=sample(self.store,22,datetime(2025,1,24,20,tzinfo=timezone.utc))
        with self.assertRaisesRegex(SharedAsOfError,'EMBARGO'):split([self.s,bad,valid],PLAN)
    def test_hash_and_order_tampering_rejected(self):
        v=verified_view(self.s,self.store);v['features']['home_elo']+=100
        with self.assertRaisesRegex(SharedAsOfError,'HASH'):vector(v)
        with patch('src.kb3_catboost_research_v3.CONTRACT_SHA','0'*64):
            with self.assertRaisesRegex(SharedAsOfError,'CONTRACT_SHA'):contract()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.raw=json.dumps({'matches':[]}).encode();buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('s.json',self.raw)
        self.zip=buf.getvalue();self.meta=dict(id=12,expired=False,created_at='2025-01-01T00:00:00Z',
            archive_download_url='https://api.github.com/repos/karolbarankiewicz1984-ui/kb-score-3/actions/artifacts/12/zip',
            digest='sha256:'+hashlib.sha256(self.zip).hexdigest())
        self.ref=dict(artifact_id=12,member='s.json',sha256=hashlib.sha256(self.raw).hexdigest())
    def test_real_reader_verifies_metadata_zip_and_member_and_caches(self):
        with patch('src.kb3_step16_m0_720_calibration._gh_json',return_value=self.meta) as meta,patch(
            'src.kb3_step16_m0_720_calibration._gh_artifact_zip',return_value=self.zip) as raw:
            store=GithubArchives('test-token');self.assertEqual(store.read(self.ref)[0],{'matches':[]})
            store.read(self.ref);self.assertEqual(meta.call_count,1);self.assertEqual(raw.call_count,1)
    def test_archive_or_member_tamper_and_foreign_url_fail(self):
        for key,value,error in [('digest','sha256:'+'0'*64,'ARCHIVE_SHA'),
                                ('archive_download_url','https://other.invalid','FOREIGN'),('expired',True,'UNAVAILABLE')]:
            meta={**self.meta,key:value}
            with patch('src.kb3_step16_m0_720_calibration._gh_json',return_value=meta),patch(
                'src.kb3_step16_m0_720_calibration._gh_artifact_zip',return_value=self.zip):
                with self.assertRaisesRegex(SharedAsOfError,error):GithubArchives('test').read(self.ref)
        with patch('src.kb3_step16_m0_720_calibration._gh_json',return_value=self.meta),patch(
            'src.kb3_step16_m0_720_calibration._gh_artifact_zip',return_value=self.zip):
            with self.assertRaisesRegex(SharedAsOfError,'MEMBER_SHA'):
                GithubArchives('test').read({**self.ref,'sha256':'0'*64})


class ActualCatBoostPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=SyntheticArchives()
        self.samples=[sample(self.store,i) for i in range(6)]+[
            sample(self.store,i+20,datetime(2025,2,2+i,20,tzinfo=timezone.utc)) for i in range(3)]
        self.out=Path(self.tmp.name)/'new-model'
    def test_real_fit_validation_independence_manifest_shadow_and_frozen_holdout(self):
        m,_=fit(self.samples,PLAN,self.store,self.out)
        self.assertEqual((m['train_n'],m['validation_n'],m['holdout_n_used']),(6,3,0))
        first,loaded=load_model(self.out,m['manifest_sha256'])
        altered=copy.deepcopy(self.samples)
        for s in altered[6:]:
            ref=s['label']['archive'];raw,_=self.store.docs[ref['artifact_id']]
            raw['matches'][0].update(score_home=0,score_away=3);s['label']['outcome_1x2']='2'
        m2,_=fit(altered,PLAN,self.store,Path(self.tmp.name)/'second')
        second,_=load_model(Path(self.tmp.name)/'second',m2['manifest_sha256'])
        self.assertEqual(list(first.get_feature_importance()),list(second.get_feature_importance()))
        import numpy as np
        np.testing.assert_array_equal(first.predict_proba([[0.]*87]),second.predict_proba([[0.]*87]))
        ko=datetime.now(timezone.utc)+timedelta(days=2)
        future=sample(self.store,90,ko);now=ko-timedelta(hours=2)+timedelta(minutes=2)
        rec=shadow(future,self.store,self.out,m['manifest_sha256'],clock=lambda:now)
        self.assertFalse(rec['github_server_artifact_verified'])
        with self.assertRaisesRegex(SharedAsOfError,'NOT_NEW_PREMATCH'):
            shadow(future,self.store,self.out,m['manifest_sha256'],clock=lambda:ko)
        # Genuine frozen holdout path tested using synthetic archive and clock.
        # Label archive is after match but before the injected evaluation clock.
        forecast_ref=self.store.add(rec,now+timedelta(minutes=1))
        hs=dict(target=future['input']['target'],forecast_archive=forecast_ref,label=future['label'])
        class EvalClock:
            @staticmethod
            def now(tz):return ko+timedelta(days=1)
        with patch('src.kb3_catboost_research_v3.datetime',EvalClock):
            report=evaluate_frozen_holdout([hs],self.store,self.out,m['manifest_sha256'],Path(self.tmp.name)/'review.json')
            from src.kb3_model_comparison_v3 import add_v3_frozen_games,compare_games
            games=add_v3_frozen_games([],[hs],self.store,self.out,m['manifest_sha256'])
            self.assertEqual(compare_games(games)['coverage']['CATBOOST_ASOF_V3'],1)
        self.assertEqual(report['metrics']['n'],1)
        doc,_=self.store.docs[forecast_ref['artifact_id']]
        self.store.docs[forecast_ref['artifact_id']]=(doc,ko+timedelta(minutes=1))
        with patch('src.kb3_catboost_research_v3.datetime',EvalClock):
            with self.assertRaisesRegex(SharedAsOfError,'NOT_FROZEN_PREMATCH'):
                evaluate_frozen_holdout([hs],self.store,self.out,m['manifest_sha256'],Path(self.tmp.name)/'late.json')
        with self.assertRaisesRegex(SharedAsOfError,'OUTPUT_REPLACE'):
            fit(self.samples,PLAN,self.store,self.out)
        manifest_path=self.out/'manifest.json';damaged=json.loads(manifest_path.read_text());damaged['fixed_params']['depth']=5
        manifest_path.write_text(json.dumps(damaged))
        with self.assertRaisesRegex(SharedAsOfError,'MANIFEST_SHA'):
            load_model(self.out,m['manifest_sha256'])
    def test_unattested_data_never_creates_model(self):
        self.samples[0]['input_archive']['artifact_id']='missing'
        with self.assertRaises(KeyError):fit(self.samples,PLAN,self.store,self.out)
        self.assertFalse(self.out.exists())


if __name__=='__main__':unittest.main()
