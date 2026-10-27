"""Independent archival-publication probe: Wayback capture time is NOT Git committer time.

CDX metadata alone does not prove historical file content equality.
We never mark a PitchAPI row PIT-certified unless capture bytes match pinned
historical blob and both source identities are independently reconciled.
"""
from __future__ import annotations
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
import json

SEASONS=("2024-25","2025-26")

def scan_wayback(fetch=None):
    if fetch is None:
        def fetch(url):
            req=Request(url,headers={"User-Agent":"KB3-historical-PIT-research"})
            with urlopen(req,timeout=12) as r:
                return r.read(160_000)
    out={}
    for season in SEASONS:
        public_url=f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/en.1.json"
        params={"url":public_url,"output":"json","fl":"timestamp,original,digest,statuscode",
                "filter":"statuscode:200","from":season[:4],"to":str(int(season[:4])+2)}
        endpoint="https://web.archive.org/cdx/search/cdx?"+urlencode(params)
        item={"source_url":public_url,"provider":"Internet Archive CDX",
              "lookup_attempted":True,"cdx_capture_count_reported":None,
              "earliest_capture_timestamp_utc":None,
              "timestamp_independent_of_git_commit":False,
              "historical_capture_payload_sha256_matches_pinned_blob":False,
              "pitchapi_crosswalk_verified":False,"official_m1_eligible":False}
        try:
            payload=fetch(endpoint)
            j=json.loads(payload)
            if not isinstance(j,list) or not j:
                item["lookup_status"]="EMPTY_OR_UNEXPECTED_CDX"
            else:
                records=[x for x in j[1:] if isinstance(x,list) and len(x)>=4
                         and x[0].isdigit() and len(x[0])==14 and x[3]=="200"]
                item["cdx_capture_count_reported"]=len(records)
                if records:
                    earliest=min(x[0] for x in records)
                    time=datetime.strptime(earliest,"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                    item["earliest_capture_timestamp_utc"]=time.isoformat().replace("+00:00","Z")
                    item["timestamp_independent_of_git_commit"]=True
                item["lookup_status"]="CDX_METADATA_RECEIVED"
        except Exception as exc:
            item["lookup_status"]="LOOKUP_UNAVAILABLE"
            item["error_type"]=type(exc).__name__
        out[season]=item
    return {"schema":"kb3-step14-independent-archival-capture-probe-v1",
            "source":"Internet Archive CDX", "seasons":out,
            "independent_capture_matched_to_historical_blobs":False,
            "official_train_eligible":0,"gate14_pass":False}


if __name__=="__main__":
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    q=p.parse_args()
    result=scan_wayback()
    path=Path(q.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({s:{"status":v["lookup_status"],"capture_count":v["cdx_capture_count_reported"],
                         "earliest":v["earliest_capture_timestamp_utc"]}
                      for s,v in result["seasons"].items()},sort_keys=True))
