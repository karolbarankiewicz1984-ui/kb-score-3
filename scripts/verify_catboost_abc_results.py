"""Independent standard-library verification of exported A/B/C probabilities and metrics."""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime,timedelta
from pathlib import Path

ENGINES=('M0_FIXED720_REPLAY','A','B','C')
def need(ok,message):
    if not ok:raise ValueError(message)
def load_json(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_scores(rows,metrics):
    need(bool(rows),'EMPTY_EVALUATION')
    for engine in ENGINES:
        pairs=[(x['predictions'][engine]['p_1x2'],x['outcome_1x2']) for x in rows]
        need(all(set(p)=={'1','X','2'} and all(0<v<1 for v in p.values()) and abs(sum(p.values())-1)<1e-12 for p,_ in pairs),'INVALID_PROBABILITIES')
        brier=math.fsum(math.fsum((p[c]-int(y==c))**2 for c in ('1','X','2')) for p,y in pairs)/len(rows)
        loss=math.fsum(-math.log(p[y]) for p,y in pairs)/len(rows)
        accuracy=sum(max(('1','X','2'),key=p.get)==y for p,y in pairs)/len(rows)
        bins=collections.defaultdict(list)
        for p,y in pairs:
            top=max(('1','X','2'),key=p.get)
            bins[min(4,int(p[top]*5))].append((p[top],int(top==y)))
        ece=sum(len(b)/len(rows)*abs(sum(v[0] for v in b)/len(b)-sum(v[1] for v in b)/len(b)) for b in bins.values())
        for name,value in (('brier_multiclass_sum3',brier),('log_loss',loss),('top1_accuracy',accuracy),('top1_ece_5_bins',ece)):
            need(abs(metrics[engine][name]-value)<1e-12,'METRIC_MISMATCH:'+engine+':'+name)
        need(metrics[engine]['n']==len(rows),'METRIC_DENOMINATOR_MISMATCH')

def verify(report_path,predictions_path,models=None):
    report=load_json(report_path)
    expected=hashlib.sha256(json.dumps({k:v for k,v in report.items() if k!='report_sha256'},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    need(report['report_sha256']==expected,'REPORT_SHA_MISMATCH')
    rows=[json.loads(s) for s in gzip.decompress(Path(predictions_path).read_bytes()).decode().splitlines()]
    need(len({(r['scope'],r['fixture_id']) for r in rows})==len(rows),'DUPLICATE_SCORED_FIXTURE')
    need(all(r['scope'] in ('ESP','ITA','GER','FRA','NED','BEL','TUR','POL') for r in rows),'FORBIDDEN_SCOPE')
    windows=[(f'fold{i}',f) for i,f in enumerate(report['walk_forward'],1)]+[('validation',report['validation'])]
    checked=0;model_count=0
    for token,part in windows:
        selected=[r for r in rows if r['partition']==token]
        if part['status']!='EXECUTED':need(not selected,'UNFITTED_WINDOW_HAS_PREDICTIONS');continue
        need(len(selected)==part['eval_n'],'EVALUATION_COUNT_MISMATCH')
        last=datetime.fromisoformat(part['train_last_kickoff'].replace('Z','+00:00'))
        cutoff=datetime.fromisoformat(part['eval_first_cutoff'].replace('Z','+00:00'))
        need(last+timedelta(hours=3)<=cutoff,'TRAIN_LABEL_LEAK')
        check_scores(selected,part['metrics']);checked+=len(selected)
        for league,scores in part['per_league'].items():check_scores([r for r in selected if r['scope']==league],scores)
        if models is not None:
            for variant in ('A','B','C'):
                need(sha(Path(models)/(token+'_'+variant+'.cbm'))==part['models'][variant]['model_sha256'],'MODEL_SHA_MISMATCH')
                model_count+=1
    need(checked==len(rows),'UNACCOUNTED_PREDICTIONS')
    pooled=[r for r in rows if r['partition']!='validation']
    if pooled:check_scores(pooled,report['walk_forward_aggregate']['metrics'])
    return {'status':'PASS','prediction_rows':len(rows),'models_sha256_verified':model_count,
            'all_metrics_independently_recomputed':True,'per_league_metrics_verified':True,
            'predictions_sha256':sha(predictions_path),'report_sha256':report['report_sha256']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True)
    p.add_argument('--predictions',type=Path,required=True);p.add_argument('--models',type=Path)
    a=p.parse_args();print(json.dumps(verify(a.report,a.predictions,a.models),indent=2))
if __name__=='__main__':main()
