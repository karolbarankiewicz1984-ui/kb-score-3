"""Block network, real-source fits and evidence writes; allow named synthetic regressions."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import unittest
from urllib.parse import urlsplit,unquote

root = Path.cwd().resolve()
sys.path[:0] = [str(root), str(root / 'tests')]
def denied(*args, **kwargs):
    raise RuntimeError('OFFLINE_AUDIT_NETWORK_OR_FIT_BLOCKED')
socket.socket.connect = denied
socket.socket.connect_ex = denied
socket.create_connection = denied
try:
    from catboost import CatBoost, CatBoostClassifier, CatBoostRegressor
    original_classifier_fit = CatBoostClassifier.fit
    def synthetic_regression_fit(self,*args,**kwargs):
        # Existing tests explicitly generate these fixtures in memory. All other
        # fits (including the new real-source experiment) remain forbidden here.
        allowed={('src.kb3_step14_synthetic','run_synthetic_catboost'),
                 ('src.kb3_step14_m1_xg_comparison','run_demo'),
                 ('test_step14_public_research','test_real_research_catboost_not_production')}
        frame=sys._getframe(1)
        while frame is not None:
            if (frame.f_globals.get('__name__'),frame.f_code.co_name) in allowed:
                return original_classifier_fit(self,*args,**kwargs)
            frame=frame.f_back
        return denied()
    CatBoost.fit = denied
    CatBoostClassifier.fit = synthetic_regression_fit
    CatBoostRegressor.fit = denied
except ImportError:
    pass
protected = [root / x for x in ('data', 'models', 'config')]
original_connect=sqlite3.connect
def readonly_protected_connect(database,*args,**kwargs):
    if isinstance(database,(str,os.PathLike)) and str(database)!=':memory:':
        raw=os.fspath(database)
        candidate=Path(unquote(urlsplit(raw).path) if raw.startswith('file:') else raw).resolve()
        if any(candidate==p or p in candidate.parents for p in protected):
            if len(args)>=7:raise RuntimeError('OFFLINE_AUDIT_SQLITE_POSITIONAL_URI_UNSUPPORTED')
            database=candidate.as_uri()+'?mode=ro';kwargs['uri']=True
    return original_connect(database,*args,**kwargs)
sqlite3.connect=readonly_protected_connect
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1:3]
        writes = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writes and any(path == p or p in path.parents for p in protected):
            raise RuntimeError('OFFLINE_AUDIT_EVIDENCE_WRITE_BLOCKED')
sys.addaudithook(audit)
suite = unittest.defaultTestLoader.discover('tests', pattern=sys.argv[1] if len(sys.argv)>1 else 'test_*.py')
def cases(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):
            yield from cases(item)
        else:
            yield item
ids=[case.id() for case in cases(suite)]
if len(ids)!=len(set(ids)):
    raise RuntimeError('OFFLINE_AUDIT_DUPLICATE_TEST_IDS')
result = unittest.TextTestRunner(verbosity=2).run(suite)
print('AUDIT_RESULT', json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
      'errors': len(result.errors), 'skipped': len(result.skipped)}))
sys.exit(not result.wasSuccessful())
