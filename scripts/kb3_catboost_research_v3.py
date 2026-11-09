"""Isolated CLI; no schedule, provider API, production/M0 database or TEST."""
import argparse
import json
import os
from pathlib import Path
from src.kb3_catboost_research_v3 import (
    CONTRACT_SHA, MODEL, GithubArchives, contract, fit, shadow, evaluate_frozen_holdout,
)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['readiness','fit','shadow','holdout'])
    parser.add_argument('--samples',type=Path)
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--model-dir',type=Path)
    parser.add_argument('--manifest-sha256')
    args=parser.parse_args()
    c=contract()
    if args.command=='readiness':
        print(json.dumps(dict(model_version=MODEL,feature_contract_sha256=CONTRACT_SHA,
            feature_count=c['feature_count'],status='NOT_TRAINED',
            blocking_reason='NO_ADMITTED_INDEPENDENTLY_ARCHIVED_V3_DATASET_SUPPLIED',
            training_on_reconstructed_history_allowed=False,production_approved=False,
            paid_api_calls=0)))
        return
    if not args.samples or not args.output:parser.error('--samples and --output required')
    samples=json.loads(args.samples.read_text())
    archives=GithubArchives(os.environ.get('GITHUB_TOKEN'))
    if args.command=='fit':
        if not args.plan:parser.error('--plan required')
        fit(samples,json.loads(args.plan.read_text()),archives,args.output)
    else:
        if not args.model_dir or not args.manifest_sha256:
            parser.error('--model-dir and --manifest-sha256 required')
        if args.command=='holdout':
            evaluate_frozen_holdout(samples,archives,args.model_dir,args.manifest_sha256,args.output)
        else:
            record=shadow(samples,archives,args.model_dir,args.manifest_sha256)
            with args.output.open('x') as handle:json.dump(record,handle,sort_keys=True,indent=2)


if __name__=='__main__':main()
