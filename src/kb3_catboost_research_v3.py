"""Independent research CatBoost: shared v2 features, verified sources, no M0 writes.

Archive verification reuses existing GitHub clients. Declarations of PIT/sha
alone never admit a row. Original provider first publication is NOT certified.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import io
import json
import math
import zipfile

from src.kb3_features import digest, EloParameters
from src.kb3_p1_shared_asof_features_v2 import (
    build_shared_features, compare_same_asof, when, digest_required, need,
)
from src.kb3_step17_engine_comparison import LABELS, prob
from src.kb3_step14_m1_math_calibration import score_predictions

ROOT = Path(__file__).resolve().parents[1]
REPO = 'karolbarankiewicz1984-ui/kb-score-3'
MODEL = 'KB3_CATBOOST_SHARED_ASOF_87_RESEARCH_V3'
CONTRACT_SHA = '0c4347e58af678f44a1ca7ad042633b8825be885f3225dbed669a8896ba33eca'
PARAMS = dict(iterations=180, depth=3, learning_rate=.035, l2_leaf_reg=8.,
              random_seed=20261109, loss_function='MultiClass', nan_mode='Min',
              thread_count=1, verbose=False, allow_writing_files=False)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract():
    c = json.loads((ROOT/'contracts/kb3_catboost_asof_v3.json').read_text())
    need(digest(c) == CONTRACT_SHA, 'FEATURE_CONTRACT_SHA_MISMATCH')
    for name, sha in c['implementation_sha256'].items():
        need(file_sha(ROOT/name) == sha, 'FEATURE_IMPLEMENTATION_DRIFT:'+name)
    return c


def vector(view):
    c = contract()
    need(view['schema'] == c['builder'], 'SHARED_V2_REQUIRED')
    # Verify the canonical snapshot hash, including lineage and availability.
    other = {**view, 'purpose': 'FORWARD' if view['purpose']=='TRAIN' else 'TRAIN'}
    compare_same_asof(view, other) if view['purpose']=='TRAIN' else compare_same_asof(other, view)
    need(view['elo_parameters'] == c['elo_parameters'], 'ELO_PARAMETERS_DRIFT')
    values = []
    cutoff = when(view['feature_cutoff_utc'])
    for spec in c['features']:
        kind, key = spec['name'].split(':')
        source = view['features'] if kind=='num' else view['missing_flags']
        need(key in source, 'FEATURE_MISSING:'+key)
        clock_key = key if kind=='num' else 'missing:'+key
        clock = view['feature_availability'][clock_key]['latest_required_observed_at_utc']
        need(when(clock) <= cutoff, 'FEATURE_AVAILABLE_AFTER_CUTOFF:'+key)
        value = source[key]
        if kind=='miss':
            need(type(value) is bool, 'MISSING_MASK_NOT_BOOLEAN')
            value = int(value)
        elif value is None:
            need(spec['nullable'], 'NON_NULLABLE_FEATURE:'+key)
        else:
            need(type(value) in (int,float) and math.isfinite(value), 'INVALID_FEATURE:'+key)
            value = float(value)
        values.append(value)
    return values


class GithubArchives:
    """Trusted read adapter: independent metadata, SHA ZIP, exact member bytes.

    Instantiate only with the existing GitHub token, never provider credentials.
    Cache each artifact once. Caller refs cannot supply trusted metadata/clocks.
    """
    def __init__(self, token):
        need(bool(token), 'GITHUB_EVIDENCE_TOKEN_REQUIRED')
        self.token, self.cache = token, {}

    def read(self, ref):
        from src.kb3_step16_m0_720_calibration import _gh_json, _gh_artifact_zip
        aid = str(ref['artifact_id'])
        need(aid.isdigit(), 'ARTIFACT_ID_INVALID')
        if aid not in self.cache:
            url = f'https://api.github.com/repos/{REPO}/actions/artifacts/{aid}'
            meta = _gh_json(url, self.token)
            need(str(meta.get('id')) == aid and meta.get('expired') is False,
                 'EVIDENCE_ARTIFACT_UNAVAILABLE')
            expected = url+'/zip'
            need(meta.get('archive_download_url') == expected, 'FOREIGN_ARCHIVE_URL')
            raw = _gh_artifact_zip(expected, self.token)
            need(meta.get('digest') == 'sha256:'+hashlib.sha256(raw).hexdigest(),
                 'EVIDENCE_ARCHIVE_SHA_MISMATCH')
            self.cache[aid] = (raw, meta['created_at'])
        raw, created = self.cache[aid]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            name = ref['member']
            matches = [x for x in archive.infolist() if x.filename == name]
            need(len(matches)==1 and 0 < matches[0].file_size <= 16*1024*1024,
                 'EVIDENCE_MEMBER_INVALID')
            member = archive.read(matches[0])
        need(hashlib.sha256(member).hexdigest() == digest_required(ref['sha256']),
             'EVIDENCE_MEMBER_SHA_MISMATCH')
        return json.loads(member), when(created)


def _archived(ref, archives, *, deadline, not_before=None):
    doc, created = archives.read(ref)
    need(created <= deadline and (not_before is None or not_before <= created),
         'ARCHIVE_NOT_AVAILABLE_AT_CUTOFF')
    return doc


def verified_view(sample, archives, purpose='TRAIN'):
    """Rebuild from bytes attested before cutoff, never an imported vector.

    Source files are native PitchAPI leagues.matches JSON {matches:[...]};
    IDs, time, teams, status and 90min score must match the normalized input.
    The complete normalized input itself also needs independent old byte proof.
    """
    contract()
    inp = sample['input']
    cutoff = when(inp['cutoff_utc'])
    doc = _archived(sample['input_archive'], archives, deadline=cutoff)
    need(doc == inp, 'ARCHIVED_INPUT_BYTES_DIFFER')
    target = inp['target']
    # Shared v2 blocks protected/unknown leagues, labels, wrong clocks etc.
    view = build_shared_features(purpose=purpose, **inp)
    refs = sample['source_archives']
    def source(receipt):
        sha = digest_required(receipt['source_sha256'])
        need(sha in refs and refs[sha]['sha256']==sha, 'RAW_SOURCE_ARCHIVE_MISSING')
        observed = when(receipt['observed_completed_at_utc'])
        captured = when(receipt.get('captured_at_utc', receipt['observed_completed_at_utc']))
        need(observed <= captured <= cutoff, 'SOURCE_CAPTURE_AFTER_CUTOFF')
        raw = _archived(refs[sha], archives, deadline=cutoff, not_before=captured)
        need(isinstance(raw,dict) and isinstance(raw.get('matches'),list),
             'NATIVE_MATCHES_SOURCE_REQUIRED')
        return raw['matches']
    def match(row, receipt, is_target=False):
        matches = [m for m in source(receipt) if str(m.get('id'))==str(row['fixture_id'])]
        need(len(matches)==1, 'SOURCE_FIXTURE_ID_NOT_UNIQUE')
        m = matches[0]
        need(m['time_utc']==row['kickoff_utc'] and
             str(m['home_team']['id'])==str(row['home_team_id']) and
             str(m['away_team']['id'])==str(row['away_team_id']), 'SOURCE_IDENTITY_DRIFT')
        if is_target:
            need(m.get('status') in ('scheduled','not_started','upcoming') and
                 m.get('score_home') is None and m.get('score_away') is None,
                 'TARGET_SOURCE_ALREADY_FINISHED')
        else:
            need(m.get('status')=='finished' and
                 type(m.get('score_home')) is int and type(m.get('score_away')) is int and
                 (m['score_home'],m['score_away']) == (row['goals_home_90'],row['goals_away_90']),
                 'SOURCE_SCORE_DRIFT')
    match(target, inp['target_receipt'], True)
    for row in inp['predecessor_rows']:
        need(all(row.get(k) is None for k in ('xgh','xga','xgh_receipt','xga_receipt')),
             'V3_NO_XG_CONTRACT')
        match(row, row['result_receipt'])
    vector(view)
    return view


def verified_label(sample, archives, target, deadline=None):
    label = sample['label']
    observed = when(label['observed_utc'])
    need(observed >= when(target['kickoff_utc'])+timedelta(hours=3), 'LABEL_NOT_MATURE')
    end = when(deadline) if deadline else datetime.now(timezone.utc)
    need(end<=datetime.now(timezone.utc),'LABEL_KNOWLEDGE_DEADLINE_IN_FUTURE')
    raw = _archived(label['archive'], archives, deadline=end, not_before=observed)
    matches = [m for m in raw['matches'] if str(m.get('id'))==str(target['fixture_id'])]
    need(len(matches)==1, 'LABEL_FIXTURE_NOT_UNIQUE')
    m = matches[0]
    need(m['time_utc']==target['kickoff_utc'] and
         str(m['home_team']['id'])==str(target['home_team_id']) and
         str(m['away_team']['id'])==str(target['away_team_id']) and
         m['status']=='finished', 'LABEL_IDENTITY_DRIFT')
    gh, ga = m.get('score_home'), m.get('score_away')
    need(all(type(v) is int and 0<=v<=30 for v in (gh,ga)), 'LABEL_90MIN_SCORE_REQUIRED')
    y = '1' if gh>ga else 'X' if gh==ga else '2'
    need(label['outcome_1x2']==y, 'LABEL_SCORE_MISMATCH')
    return y, observed


def split(samples, plan):
    """Fixed date boundaries, seven day embargo, HOLDOUT never read at fit."""
    keys = ('train_end_utc','validation_start_utc','validation_end_utc','holdout_start_utc')
    a,b,c,d = [when(plan[k]) for k in keys]
    need(a+timedelta(days=7)<=b<c and c+timedelta(days=7)<=d, 'SPLIT_EMBARGO_INVALID')
    train, valid, seen = [], [], set()
    for sample in samples:
        target = sample['input']['target']
        need(target['league'] in contract()['leagues'], 'PROTECTED_OR_UNKNOWN_LEAGUE')
        key = (target['league'],str(target['fixture_id']))
        need(key not in seen, 'DUPLICATE_SPLIT_FIXTURE')
        seen.add(key)
        cutoff = when(sample['input']['cutoff_utc'])
        kickoff = when(target['kickoff_utc'])
        need(kickoff < d, 'HOLDOUT_INPUT_FORBIDDEN_AT_FIT')
        if kickoff < a:
            need(cutoff < a, 'TRAIN_FEATURE_AFTER_BOUNDARY')
            train.append(sample)
        elif b <= cutoff and kickoff < c:
            valid.append(sample)
        else:
            need(False, 'SAMPLE_IN_EMBARGO_OR_UNASSIGNED')
    need(train and valid, 'INSUFFICIENT_VERIFIED_TRAIN_VALIDATION')
    return train, valid


def _matrix(views):
    return [[float('nan') if x is None else x for x in vector(v)] for v in views]


def fit(samples, plan, archives, output):
    """Actual fit on TRAIN only; VALIDATION never used for stopping/selection.

    Validation predictions are retrospective diagnostics, never frozen forward
    predictions. HOLDOUT labels/data are not accepted by this entry point.
    """
    out = Path(output)
    need(not out.exists(), 'OUTPUT_REPLACE_FORBIDDEN')
    train, valid = split(samples, plan)
    train_views = [verified_view(s,archives) for s in train]
    valid_views = [verified_view(s,archives) for s in valid]
    train_y = [verified_label(s,archives,s['input']['target'],plan['train_end_utc'])[0] for s in train]
    valid_y = [verified_label(s,archives,s['input']['target'])[0] for s in valid]
    need(set(train_y)==set(LABELS), 'TRAIN_REQUIRES_ALL_1X2_CLASSES')
    from catboost import CatBoostClassifier, Pool, __version__
    need(__version__=='1.2.8', 'CATBOOST_VERSION_DRIFT')
    clf = CatBoostClassifier(**PARAMS)
    names = [s['name'] for s in contract()['features']]
    clf.fit(Pool(_matrix(train_views),label=train_y,feature_names=names))
    p = _predict(clf,valid_views)
    out.mkdir(parents=True,exist_ok=False)
    clf.save_model(str(out/'model.cbm'))
    now = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    manifest = dict(schema='kb3-catboost-research-manifest-v3',model_version=MODEL,
        feature_contract_sha256=CONTRACT_SHA, feature_names=names, fixed_params=PARAMS,
        catboost_version=__version__, model_binary_sha256=file_sha(out/'model.cbm'),
        split_plan=plan, split_plan_sha256=digest(plan),
        train_n=len(train),validation_n=len(valid),holdout_n_used=0,
        training_source_sha256=digest(train), validation_source_sha256=digest(valid),
        training_feature_hashes=[v['canonical_features_sha256'] for v in train_views],
        validation_feature_hashes=[v['canonical_features_sha256'] for v in valid_views],
        source_archives=[s['input_archive'] for s in train+valid],
        source_manifest_sha256=digest(samples), training_code_sha256=file_sha(Path(__file__)),
        trained_at_utc=now, production_approved=False, research_only=True,
        original_provider_first_publication_certified=False, independent_archived_bytes_verified=True)
    manifest['manifest_sha256'] = digest(manifest)
    (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    report = dict(schema='kb3-v3-retrospective-validation-only',
                  metrics=score_predictions(p,valid_y), forward_frozen_predictions=0,
                  no_holdout_used=True, champion_eligible=False)
    (out/'validation.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    return manifest, report


def load_model(directory, expected_manifest_sha256):
    contract()
    directory = Path(directory)
    m = json.loads((directory/'manifest.json').read_text())
    need(digest({k:v for k,v in m.items() if k!='manifest_sha256'}) ==
         m.get('manifest_sha256') == digest_required(expected_manifest_sha256),
         'MODEL_MANIFEST_SHA_MISMATCH')
    need(m['model_version']==MODEL and m['feature_contract_sha256']==CONTRACT_SHA and
         m['fixed_params']==PARAMS and m['production_approved'] is False and
         m['research_only'] is True and m['holdout_n_used']==0 and
         m['independent_archived_bytes_verified'] is True and
         digest(m['split_plan'])==m['split_plan_sha256'] and
         m['training_code_sha256']==file_sha(Path(__file__)) and
         m['feature_names']==[s['name'] for s in contract()['features']] and
         file_sha(directory/'model.cbm')==m['model_binary_sha256'], 'MODEL_BYTES_OR_CONTRACT_DRIFT')
    from catboost import CatBoostClassifier
    clf=CatBoostClassifier(); clf.load_model(str(directory/'model.cbm'))
    need(list(clf.feature_names_)==m['feature_names'] and set(map(str,clf.classes_))==set(LABELS),
         'MODEL_CLASS_OR_FEATURE_ORDER_DRIFT')
    return clf,m


def _predict(clf, views):
    classes = list(map(str,clf.classes_))
    need(set(classes)==set(LABELS), 'MODEL_CLASSES_DRIFT')
    result = [{k:float(row[classes.index(k)]) for k in LABELS}
              for row in clf.predict_proba(_matrix(views))]
    for p in result: prob(p)
    return result


def shadow(sample, archives, directory, expected_manifest_sha256, *, clock=None):
    """New prematch only; returns UNATTESTED candidate. Never touches M0 DB.

    Archive this exact output before kickoff-90m via existing host byte proof
    process; comparison MUST reject it until independently host-attested.
    """
    now = (clock or (lambda:datetime.now(timezone.utc)))()
    cutoff = when(sample['input']['cutoff_utc'])
    kickoff = when(sample['input']['target']['kickoff_utc'])
    need(now.utcoffset()==timedelta(0) and cutoff<=now<=cutoff+timedelta(minutes=45)
         and now < kickoff-timedelta(minutes=90), 'SHADOW_NOT_NEW_PREMATCH')
    clf,m=load_model(directory,expected_manifest_sha256)
    need(when(m['trained_at_utc'])<=cutoff, 'MODEL_TRAINED_AFTER_FEATURE_CUTOFF')
    view=verified_view(sample,archives,'FORWARD')
    record=dict(schema='kb3-v3-shadow-candidate',model_version=MODEL,
        model_manifest_sha256=m['manifest_sha256'],model_bytes_sha256=m['model_binary_sha256'],
        feature_contract_sha256=CONTRACT_SHA, feature_sha256=view['canonical_features_sha256'],
        league=view['league'], fixture_id=str(view['target_fixture_id']),
        kickoff_utc=view['target_kickoff_utc'],feature_cutoff_utc=view['feature_cutoff_utc'],
        generated_at_utc=now.isoformat().replace('+00:00','Z'),p_1x2=_predict(clf,[view])[0],
        github_server_artifact_verified=False,research_only=True,production_approved=False)
    record['forecast_sha256']=digest(record)
    return record


def evaluate_frozen_holdout(samples, archives, directory, expected_manifest_sha256, output):
    """Evaluate ONLY independently archived genuine V3 forecasts, never backpredict.

    Input is a separate HOLDOUT collection. Neither fitting nor validation reads
    it. An exclusive output path prevents overwriting an earlier holdout review.
    """
    out=Path(output)
    need(not out.exists(),'OUTPUT_REPLACE_FORBIDDEN')
    _,m=load_model(directory,expected_manifest_sha256)
    probabilities=[];labels=[];ids=set();hashes=[]
    for sample in samples:
        p,y=verified_frozen_forecast(sample,archives,m,require_holdout=True)
        key=(p['league'],p['fixture_id'])
        need(key not in ids,'DUPLICATE_HOLDOUT_FIXTURE');ids.add(key)
        prob(p['p_1x2']);probabilities.append(p['p_1x2']);labels.append(y);hashes.append(p['forecast_sha256'])
    need(probabilities,'NO_FROZEN_HOLDOUT_FORECASTS')
    report=dict(schema='kb3-v3-frozen-holdout-review',model_version=MODEL,
                model_manifest_sha256=expected_manifest_sha256,forecast_hashes=hashes,
                metrics=score_predictions(probabilities,labels),research_only=True,
                champion_eligible=False)
    with out.open('x') as handle:json.dump(report,handle,sort_keys=True,indent=2)
    return report


def verified_frozen_forecast(sample, archives, manifest, *, require_holdout=False):
    """Trusted adapter for comparisons/holdout: exact forecast bytes + real host clock."""
    target=sample['target'];m=manifest
    need(target['league'] in contract()['leagues'],'PROTECTED_OR_UNKNOWN_LEAGUE')
    p,created=archives.read(sample['forecast_archive'])
    need(p.get('forecast_sha256')==digest({k:v for k,v in p.items() if k!='forecast_sha256'}),
         'HOLDOUT_FORECAST_SHA_MISMATCH')
    need(p['model_version']==MODEL and p['model_manifest_sha256']==m['manifest_sha256']
         and p['model_bytes_sha256']==m['model_binary_sha256'] and
         p['feature_contract_sha256']==CONTRACT_SHA and p['research_only'] is True
         and p['production_approved'] is False and
         (p['league'],p['fixture_id'],p['kickoff_utc'])==
         (target['league'],str(target['fixture_id']),target['kickoff_utc']), 'HOLDOUT_MODEL_OR_FIXTURE_DRIFT')
    cutoff=when(p['feature_cutoff_utc'])
    if require_holdout:
        need(when(m['split_plan']['holdout_start_utc'])<=cutoff,'HOLDOUT_BEFORE_RESERVED_WINDOW')
    need(when(m['trained_at_utc'])<=cutoff<=when(p['generated_at_utc'])<=
         created<=when(p['kickoff_utc'])-timedelta(minutes=90),'HOLDOUT_NOT_FROZEN_PREMATCH')
    y,_=verified_label(sample,archives,target)
    prob(p['p_1x2'])
    return p,y
