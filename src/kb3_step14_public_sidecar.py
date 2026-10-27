"""KB3 Step14 C: append-only independent public schedule observation sidecar.

This stores ONLY future schedule metadata, never historical/present scores,
odds, TEST labels, xG or model features; it does NOT replace PitchAPI.
Source observed_at is measured by our network request at capture time.
The raw response checksum is AUDIT-ONLY and MUST NOT enter model features.
1 public GET/day via free CC0 OpenFootball; never calls paid sport API.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone, date
from hashlib import sha256
import json
from pathlib import Path
import urllib.request
from src.kb3_split import sha

SOURCE="https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.1.json"
SCHEMA="kb3-step14-free-future-schedule-sidecar-v1"


class SidecarError(ValueError):pass


def clean_future_schedule(public_blob, observed_at):
    if type(public_blob) is not bytes or not 1000<len(public_blob)<2_000_000:
        raise SidecarError("SOURCE_BYTES_INVALID")
    if type(observed_at) is not datetime or observed_at.utcoffset()!=timedelta(0):
        raise SidecarError("CLOCK_MUST_BE_UTC")
    doc=json.loads(public_blob)
    if type(doc) is not dict or type(doc.get("matches")) is not list:
        raise SidecarError("EXPECTED_PUBLIC_MATCH_LIST")
    # Only process whitelisted TARGET-FREE fields from fixtures.
    rows=[]
    seen=set()
    for game in doc["matches"]:
        if type(game) is not dict:
            raise SidecarError("INVALID_PUBLIC_GAME")
        day=date.fromisoformat(game["date"])
        if day<=observed_at.date()+timedelta(days=2):
            continue
        h,a=game.get("team1"),game.get("team2")
        if not all(type(x) is str and 0<len(x)<=120 for x in (h,a)) or h==a:
            raise SidecarError("INVALID_PUBLIC_TEAMS")
        t=game.get("time")
        if t is not None and (type(t) is not str or len(t)>8):
            raise SidecarError("INVALID_PUBLIC_TIME")
        key=(day.isoformat(),h,a)
        if key in seen:
            raise SidecarError("DUPLICATE_UPCOMING_GAME")
        seen.add(key)
        # no game['score']/labels, and no provider/PitchAPI target IDs
        rows.append({"date":day.isoformat(),"time_provider_local_unverified":t,
                     "home_team_public_name":h,"away_team_public_name":a})
    rows.sort(key=lambda x:(x["date"],x["home_team_public_name"],x["away_team_public_name"]))
    record={
        "schema":SCHEMA,
        "source":SOURCE,
        "observed_at_utc":observed_at.isoformat().replace("+00:00","Z"),
        "source_blob_sha256_AUDIT_ONLY_NO_MODEL_INPUT":sha256(public_blob).hexdigest(),
        "target_free_projection_sha256":sha(rows),
        "matches_future_min_3_calendar_days":len(rows),
        "fixtures_target_free_only":rows,
        "pitchapi_primary_source_unchanged":True,
        "pitchapi_crosswalk_verified":False,
        "model_features_included":False,
        "match_results_read_or_recorded":False,
        "test_labels_read":False,
        "eligible_training_examples":0,
        "historical_pit_certified":False,
        "training_allowed":False,
        "gate14_pass":False,
        "independently_audited_historical_publication":False,
    }
    record["receipt_sha256"]=sha(record)
    return record


def collect(blob_reader=None,now=None):
    if blob_reader is None:
        def blob_reader(url):
            req=urllib.request.Request(url,headers={"User-Agent":"KB3-target-free-sidecar"})
            with urllib.request.urlopen(req,timeout=25) as response:
                return response.read(2_000_000+1)
    blob=blob_reader(SOURCE)
    # Observation is recorded only AFTER the public HTTP response completes.\n    observed_at=datetime.now(timezone.utc) if now is None else now
    return clean_future_schedule(blob,observed_at)


def store_once(record,directory):
    base=Path(directory)
    day=record["observed_at_utc"][:10]
    if sha({k:v for k,v in record.items() if k!="receipt_sha256"})!=record["receipt_sha256"]:
        raise SidecarError("RECEIPT_TAMPERED")
    base.mkdir(parents=True,exist_ok=True)
    dest=base/f"{day}.json"
    if dest.exists():
        old=json.loads(dest.read_text(encoding="utf-8"))
        if old.get("receipt_sha256")==record["receipt_sha256"]:
            return str(dest),False
        raise SidecarError("APPEND_ONLY_DATE_ALREADY_CAPTURED")
    # exclusive-create; no overwrites.
    with dest.open("x",encoding="utf-8") as handle:
        json.dump(record,handle,sort_keys=True,ensure_ascii=False,indent=2)
        handle.write("\n")
    return str(dest),True


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--directory",required=True)
    x=p.parse_args()
    snapshot=collect()
    out,created=store_once(snapshot,x.directory)
    print(json.dumps({"record":out,"created":created,
                      "future_schedule_entries":snapshot["matches_future_min_3_calendar_days"],
                      "score_fields_exported":0,"training_allowed":False},
                     sort_keys=True))
