"""Restore an existing compressed history snapshot for offline audit/test use.

Reuses kb3-history-compressed-sqlite-v1 and storage.file_hash. Does not rebuild
history, rewrite a snapshot, call APIs or overwrite a different existing DB.
"""
import argparse
import gzip
import json
from pathlib import Path
import sqlite3
from src.kb3_storage import file_hash


def restore(source, target=None):
    source=Path(source)
    target=Path(target) if target else source.with_suffix('')
    meta=json.loads(source.with_name(source.name+'.manifest.json').read_text())
    if (meta.get('schema')!='kb3-history-compressed-sqlite-v1' or
        type(meta.get('raw_bytes')) is not int or not 0<meta['raw_bytes']<=256*1024*1024 or
        source.stat().st_size!=meta.get('compressed_bytes') or
        file_hash(source)!=meta.get('compressed_sha256')):
        raise ValueError('COMPRESSED_SNAPSHOT_SHA_OR_SIZE_MISMATCH')
    created=False
    try:
        if not target.exists():
            with gzip.open(source,'rb') as packed:
                raw=packed.read(meta['raw_bytes']+1)
            if len(raw)!=meta['raw_bytes']:
                raise ValueError('RAW_SNAPSHOT_SIZE_MISMATCH')
            import hashlib
            if hashlib.sha256(raw).hexdigest()!=meta.get('raw_sha256'):
                raise ValueError('RAW_SNAPSHOT_SHA_MISMATCH')
            with target.open('xb') as output:
                created=True
                output.write(raw)
        if target.stat().st_size!=meta['raw_bytes'] or file_hash(target)!=meta.get('raw_sha256'):
            raise ValueError('EXISTING_SNAPSHOT_DIFFERS_NO_OVERWRITE')
        with sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True) as db:
            if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('RESTORED_SNAPSHOT_SQLITE_INTEGRITY_FAILURE')
        return dict(schema=meta['schema'],restored_new=created,sqlite_sha256=meta['raw_sha256'],
                    integrity='ok',source_compressed_unchanged=True)
    except BaseException:
        if created:target.unlink(missing_ok=True)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--target',type=Path);a=p.parse_args()
    print(json.dumps(restore(a.source,a.target),sort_keys=True))
