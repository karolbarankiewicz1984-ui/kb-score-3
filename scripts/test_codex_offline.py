"""Run existing unittest suites with network, model fit and evidence writes blocked."""
import json
import os
from pathlib import Path
import socket
import sys
import unittest

root = Path.cwd().resolve()
sys.path[:0] = [str(root), str(root / 'tests')]
def denied(*args, **kwargs):
    raise RuntimeError('OFFLINE_AUDIT_NETWORK_OR_FIT_BLOCKED')
socket.socket.connect = denied
socket.socket.connect_ex = denied
socket.create_connection = denied
try:
    from catboost import CatBoost
    CatBoost.fit = denied
except ImportError:
    pass
protected = [root / x for x in ('data', 'models', 'config')]
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
