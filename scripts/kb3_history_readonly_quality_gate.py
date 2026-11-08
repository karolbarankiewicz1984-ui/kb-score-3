"""Read-only historical coverage and provenance audit. Never certifies retrospective PIT."""
from __future__ import annotations
import argparse,hashlib,json,sqlite3
from pathlib import Path

DEFAULT=Path('data/research/historical_multistat/observations.sqlite')
def audit(path=DEFAULT):
    path=Path(path)
    if not path.is_file(): raise ValueError('HISTORICAL_DB_MISSING')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('HISTORICAL_DB_INTEGRITY_FAILED')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'observations','finished_fixture_index'}<=tables:
            raise ValueError('HISTORICAL_REQUIRED_TABLES_MISSING')
        fixtures=dict(db.execute('SELECT scope,COUNT(*) FROM finished_fixture_index GROUP BY scope'))
        observations=dict(db.execute('SELECT scope,COUNT(*) FROM observations GROUP BY scope'))
        original_proofs=db.execute('SELECT COUNT(*) FROM observations WHERE provider_first_published_at_utc IS NOT NULL').fetchone()[0]
        rows={scope:{'indexed_finished':n,'observed_stats':observations.get(scope,0),
             'missing_stats':max(0,n-observations.get(scope,0)),
             'observed_coverage':observations.get(scope,0)/n if n else None}
             for scope,n in sorted(fixtures.items())}
        if 'ENG' in fixtures or 'ENG' in observations:
            raise ValueError('PROTECTED_ENG_IN_HISTORICAL_DB')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise ValueError('SOURCE_CHANGED_DURING_AUDIT')
    return {'schema':'kb3-historical-coverage-provenance-audit-v1',
            'source_sha256':digest,'total_indexed_finished':sum(fixtures.values()),
            'total_observed_stats':sum(observations.values()),'by_scope':rows,
            'provider_first_publication_proof_rows':original_proofs,
            'retrospective_pit_certified':False,'training_approved':False,
            'source_unchanged':True,'protected_test_accessed':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=DEFAULT)
    p.add_argument('--output',type=Path)
    args=p.parse_args();result=audit(args.db)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\\n')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
