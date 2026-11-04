"""Bounded transport retry with future-call reserves and one receipt per response."""
import math,time
from scripts.pitchapi_step06_audit import to_plain
from src.kb3_pit_ledger import utc_now
from src.kb3_pitch_uefa_evidence import add_observation

class RequestBudget:
    def __init__(self,cap,receipts,errors):
        self.cap=cap;self.receipts=receipts;self.errors=errors
        self.calls=0;self.retries=0;self.cache={};self.failures=[]

    def call(self,resource,fn,*args,reserve=0,**kwargs):
        if resource in self.cache:return self.cache[resource]
        if type(reserve) is not int or reserve<0:raise ValueError('INVALID_REQUEST_RESERVE')
        for attempt in range(2):
            if self.calls+reserve>=self.cap:
                self.errors['RETRY_OR_CALL_DEFERRED_FOR_BUDGET']+=1
                break
            started=utc_now();self.calls+=1
            if attempt:self.retries+=1
            try:payload=to_plain(fn(*args,**kwargs))
            except Exception as exc:
                self.errors[type(exc).__name__]+=1
                response=getattr(exc,'response',None)
                status=getattr(response,'status_code',getattr(exc,'status_code',None))
                if isinstance(status,int) and (400<=status<500 and status!=429):break
                delay=getattr(exc,'retry_after',None)
                delay=float(delay) if type(delay) in (int,float) and math.isfinite(delay) and delay>=0 else .25
                if delay>2:
                    self.errors['LONG_RETRY_AFTER_DEFERRED']+=1
                    break
                if attempt==0 and self.calls+reserve<self.cap:time.sleep(delay)
                continue
            ended=utc_now()
            if not isinstance(payload,dict):
                self.errors['NON_OBJECT_SOURCE_PAYLOAD']+=1
                break
            add_observation(self.receipts,resource=resource,payload=payload,started=started,completed=ended)
            result=(payload,self.receipts[-1]);self.cache[resource]=result
            return result
        self.failures.append(resource)
        return None,None
