"""Read-only prefilter for GitHub archive metadata against a TARGET forecast cutoff.

Artifact creation is necessary, never sufficient: independently verify ZIP SHA,
native member bytes, fixture identity, source observed/captured clocks and
predecessor result maturity before admitting any sample. No network or fitting.
"""
from datetime import datetime,timezone
import json

def utc(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    d=datetime.fromisoformat(value.replace("Z","+00:00"))
    if d.utcoffset().total_seconds()!=0:
        raise ValueError("UTC_REQUIRED")
    return d

def classify(artifacts, targets):
    out=[]
    for t in targets:
        cutoff=utc(t["feature_cutoff_utc"])
        if not t.get("fixture_id") or not t.get("league"):
            raise ValueError("TARGET_IDENTITY_REQUIRED")
        for a in artifacts:
            created=utc(a["created_at"])
            if not isinstance(a.get("id"),int) or a["id"]<=0:
                raise ValueError("ARTIFACT_ID_REQUIRED")
            candidate=not a.get("expired",False) and created<=cutoff
            out.append(dict(fixture_id=t["fixture_id"],league=t["league"],
                feature_cutoff_utc=t["feature_cutoff_utc"],
                artifact_id=a["id"],artifact_name=a["name"],
                artifact_created_at_utc=a["created_at"],
                metadata_time_candidate=candidate,
                formally_training_eligible=False,
                required_next_proofs=[
                    "archive ZIP SHA256 and native response member SHA256",
                    "provider observed/captured clocks before target cutoff",
                    "predecessor fixture identity and results maturity",
                    "independent host archive provenance and immutable feature contract"]))
    return {"schema":"kb3-v3-github-archive-target-cutoff-prefilter-v1",
            "rows":out,"formally_admitted":0,
            "metadata_alone_cannot_certify_pit":True,
            "production_approved":False}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--artifacts",required=True)
    p.add_argument("--targets",required=True)
    args=p.parse_args()
    with open(args.artifacts) as f:a=json.load(f)
    with open(args.targets) as f:t=json.load(f)
    print(json.dumps(classify(a,t),ensure_ascii=False,indent=2))
