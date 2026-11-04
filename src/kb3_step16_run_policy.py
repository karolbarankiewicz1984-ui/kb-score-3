"""Local M0 attempt policy; no API, forecasts, or independently attested proof."""
from datetime import timedelta
from pathlib import Path
import hashlib,json
from src.kb3_pit_ledger import as_utc,canonical

MODEL='M0_ELO_POISSON_RESEARCH_720TRAIN_V1'
MAX_FORECAST_ATTEMPTS=3
FORECAST_GAP=timedelta(hours=2)
FAILED_ATTEMPT_GAP=timedelta(minutes=5)
SETTLEMENT_GAP=timedelta(hours=5)

def read_clock(path,mode,now):
    doc=json.loads(Path(path).read_text())
    if doc.get('model_version')!=MODEL or doc.get('mode')!=mode:raise ValueError('RUN_METADATA_DRIFT')
    key='attempt_sha256' if Path(path).name=='ATTEMPT.json' else 'report_sha256'
    expected=hashlib.sha256(canonical({k:v for k,v in doc.items() if k!=key})).hexdigest()
    if doc.get(key)!=expected:raise ValueError('RUN_METADATA_SHA_CHANGED')
    clock=as_utc(doc['run_utc'])
    if clock>now:raise ValueError('FUTURE_RUN_CLOCK')
    return clock

def forecast_state(sources,forecasts,now):
    day=now.date().isoformat();attempts=[];completed=[];invalid=[]
    for folder in sorted((Path(sources)/day).glob('forecast*')):
        if not folder.is_dir():continue
        receipt=folder/'RECEIPT.json';attempt=folder/'ATTEMPT.json'
        try:
            path=attempt if attempt.exists() else receipt
            clock=read_clock(path,'forecast',now)
            attempts.append(clock)
            if receipt.exists():completed.append(read_clock(receipt,'forecast',now))
        except (OSError,ValueError,KeyError,TypeError):invalid.append(str(folder))
    legacy=Path(forecasts)/day/'FROZEN_M0_720_EIGHT.json'
    if legacy.exists():
        try:
            clock=read_clock(legacy,'forecast',now)
            if clock not in completed:
                attempts.append(clock);completed.append(clock)
        except (OSError,ValueError,KeyError,TypeError):invalid.append(str(legacy))
    return {'attempts':sorted(set(attempts)),'completed':sorted(set(completed)),
            'invalid':invalid}

def forecast_due(sources,forecasts,now):
    state=forecast_state(sources,forecasts,now)
    if state['invalid']:return False,'LOCAL_FORECAST_METADATA_REVIEW_REQUIRED'
    if len(state['attempts'])>=MAX_FORECAST_ATTEMPTS:return False,'FORECAST_ATTEMPT_DAILY_CAP'
    if state['completed'] and now-state['completed'][-1]<FORECAST_GAP:return False,'FORECAST_ALREADY_RECENT'
    if state['attempts'] and now-state['attempts'][-1]<FAILED_ATTEMPT_GAP:return False,'FORECAST_RETRY_BACKOFF'
    return True,'MISSING_OR_NEW_INTRADAY_FORECAST'

def latest_settlement(sources,now):
    times=[]
    for lookback in range(3):
        day=(now.date()-timedelta(days=lookback)).isoformat()
        for path in (Path(sources)/day).glob('settle-*/RECEIPT.json'):
            try:times.append(read_clock(path,'settle',now))
            except (OSError,ValueError,KeyError,TypeError):continue
    return max(times,default=None)
