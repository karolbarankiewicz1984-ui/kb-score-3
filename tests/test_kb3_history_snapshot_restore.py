"""Offline fixtures: corrupt snapshot must never replace an existing database."""
import gzip,hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from scripts.kb3_restore_history_snapshot import restore

class SnapshotRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.target=root/'restore.sqlite';self.source=root/'source.sqlite.gz'
        seed=root/'seed.sqlite'
        with sqlite3.connect(seed) as db:
            db.execute('create table observations(id text primary key)');db.execute("insert into observations values('synthetic')")
        raw=seed.read_bytes();packed=gzip.compress(raw);self.source.write_bytes(packed)
        self.meta=dict(schema='kb3-history-compressed-sqlite-v1',raw_bytes=len(raw),
            compressed_bytes=len(packed),compressed_sha256=hashlib.sha256(packed).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest())
        self.manifest=self.source.with_name(self.source.name+'.manifest.json');self.manifest.write_text(json.dumps(self.meta))
    def test_verified_restore_and_idempotent_read(self):
        original=self.source.read_bytes();result=restore(self.source,self.target)
        self.assertTrue(result['restored_new']);self.assertFalse(restore(self.source,self.target)['restored_new'])
        self.assertEqual(original,self.source.read_bytes())
    def test_existing_different_bytes_never_overwritten(self):
        self.target.write_bytes(b'KEEP')
        with self.assertRaisesRegex(ValueError,'NO_OVERWRITE'):restore(self.source,self.target)
        self.assertEqual(self.target.read_bytes(),b'KEEP')
    def test_corrupt_hash_has_no_output(self):
        self.meta['raw_sha256']='0'*64;self.manifest.write_text(json.dumps(self.meta))
        with self.assertRaisesRegex(ValueError,'RAW_SNAPSHOT_SHA'):restore(self.source,self.target)
        self.assertFalse(self.target.exists())

if __name__=='__main__':unittest.main()
