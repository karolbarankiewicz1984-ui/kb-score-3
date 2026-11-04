"""Offline research entrypoint. No API, no implicit fit, no main/model publication."""
import argparse,gzip,json
from pathlib import Path
from src.kb3_catboost_abc_research import run
from src.kb3_catboost_research_data import need

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',type=Path,default=ROOT/'data/research/historical_multistat/observations.sqlite')
    parser.add_argument('--rechecks',type=Path,default=ROOT/'data/research/historical_multistat/issue_rechecks.sqlite')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--predictions',type=Path)
    parser.add_argument('--model-dir',type=Path)
    parser.add_argument('--frozen-m0-db',type=Path,default=ROOT/'data/forward_m0_720_eight/kb3_forward_eight.sqlite')
    parser.add_argument('--fit',action='store_true')
    args=parser.parse_args()
    need(not args.out.exists(),'APPEND_ONLY_REPORT_EXISTS')
    if args.predictions:need(not args.predictions.exists(),'APPEND_ONLY_PREDICTIONS_EXIST')
    report,predictions=run(args.db,args.rechecks,fit=args.fit,model_dir=args.model_dir,frozen_db=args.frozen_m0_db)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x') as f:json.dump(report,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    if args.predictions:
        args.predictions.parent.mkdir(parents=True,exist_ok=True)
        raw=''.join(json.dumps(r,sort_keys=True,allow_nan=False)+'\n' for r in predictions).encode()
        with args.predictions.open('xb') as f:f.write(gzip.compress(raw,mtime=0))
    print(json.dumps({'status':report['status'],'source':report['source'],
        'walk_forward':[(r['train_n'],r['eval_n'],r['status']) for r in report['walk_forward']],
        'validation':{k:report['validation'].get(k) for k in ('train_n','eval_n','status','metrics')},
        'GATE17':report['GATE17']},sort_keys=True))

if __name__=='__main__':main()
