"""No-write SQLite audit; output is a NEW report, never a modified ledger."""
import argparse
import json
import os
from pathlib import Path
from src.kb3_model_comparison_v3 import ledger_games, compare_games, add_v3_frozen_games


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--v3-frozen-samples',type=Path)
    p.add_argument('--v3-model-dir',type=Path)
    p.add_argument('--v3-manifest-sha256')
    a=p.parse_args()
    games,audit=ledger_games(a.db)
    if a.v3_frozen_samples:
        if not a.v3_model_dir or not a.v3_manifest_sha256:
            p.error('--v3-model-dir and --v3-manifest-sha256 required')
        from src.kb3_catboost_research_v3 import GithubArchives
        games=add_v3_frozen_games(games,json.loads(a.v3_frozen_samples.read_text()),
            GithubArchives(os.environ.get('GITHUB_TOKEN')),a.v3_model_dir,a.v3_manifest_sha256)
    result={**compare_games(games),'source_audit':audit}
    with a.output.open('x') as handle:json.dump(result,handle,sort_keys=True,indent=2)
    print(json.dumps(dict(coverage=result['coverage'],source_audit=audit),sort_keys=True))


if __name__=='__main__':main()
