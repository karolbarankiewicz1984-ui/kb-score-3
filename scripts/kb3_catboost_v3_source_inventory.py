"""Read-only inventory of historical SQLite clocks, NOT historical PIT certification."""
import argparse
import json
from pathlib import Path
import sqlite3
from src.kb3_catboost_research_v3 import file_sha


def inventory(path):
    path=Path(path).resolve();before=file_sha(path)
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        integrity=db.execute('PRAGMA integrity_check').fetchall()
        assert integrity==[('ok',)]
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        counts={t:db.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
        columns={t:[r[1] for r in db.execute('PRAGMA table_info("'+t.replace('"','""')+'")')] for t in tables}
    assert before==file_sha(path)
    return dict(schema='kb3-v3-source-inventory',sqlite_sha256=before,integrity='ok',
        table_counts=counts,columns=columns,source_unchanged=True,
        admitted_v3_training_rows=0,
        reason='Historical observations collected after target cutoff do not establish old prematch availability; no V3 archived-input/native-byte evidence bundle supplied',
        model_status='NOT_TRAINED')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,required=True);a=p.parse_args()
    print(json.dumps(inventory(a.db),sort_keys=True))
