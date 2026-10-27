"""Step14 A: historical git-commit *candidate* discovery for 60 safe fixtures.

Do not claim Git author/committer date is a cryptographic publication proof.
Do not claim a season-level public file contains the *correct PitchAPI fixture*
without independently validated team/fixture crosswalk. No PIT training release.
Uses only historical file commit metadata; no match score/odds fetched.
"""
import json
from pathlib import Path
from datetime import datetime,timedelta,timezone
import urllib.request

PILOT="data/research/STEP14_PIT_PILOT_40_TRAIN_20_VALIDATION_2026-10-27.json"
PUBLIC_REPO="openfootball/football.json"
SEASONS=("2023-24","2024-25","2025-26")
MAX_PAGES=3

class ArchiveProbeError(ValueError):pass

def _utc(s):
    try:
        t=datetime.fromisoformat(s.replace("Z","+00:00"))
    except (AttributeError,ValueError) as exc:
        raise ArchiveProbeError("INVALID_TIME") from exc
    if t.tzinfo is None or t.utcoffset()!=timedelta(0):
        raise ArchiveProbeError("NOT_UTC")
    return t

def validate_roster(roster,safe):
    from src.kb3_split import sha
    if roster.get("schema")!="kb3-step14-historical-candidate-pilot-v1" or roster.get("training_allowed") is not False:
        raise ArchiveProbeError("ROSTER_NOT_FROZEN")
    if safe.get("schema")!="kb3-step12-methodology-v1" or safe.get("training_allowed") is not False:
        raise ArchiveProbeError("UNSAFE_BASE")
    if sha({k:v for k,v in safe.items() if k!="projection_sha256"}) != "3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7":
        raise ArchiveProbeError("SAFE_MANIFEST_CHANGED")
    expected={r["fixture_id"]:r for r in safe["fixtures"] if r["partition"] in ("TRAIN","VALIDATION")}
    sample=roster["fixtures"]
    if len(sample)!=60 or len({r["fixture_id"] for r in sample})!=60:
        raise ArchiveProbeError("PILOT_COUNT_OR_DUPLICATE")
    counts={x:0 for x in SEASONS}
    for r in sample:
        if set(r)!={"fixture_id","kickoff_utc","partition","season"}:
            raise ArchiveProbeError("SAMPLE_TAINT")
        base=expected.get(r["fixture_id"])
        if base is None or base["partition"]!=r["partition"] or base["kickoff_utc"]!=r["kickoff_utc"]:
            raise ArchiveProbeError("SAMPLE_NOT_OFFICIAL_TRAIN_VALID")
        season=r["season"]
        if season not in SEASONS or (r["partition"]=="VALIDATION")!=(season=="2025-26"):
            raise ArchiveProbeError("ROLE_OR_SEASON_CHANGED")
        day=_utc(r["kickoff_utc"])
        if not (int(season[:4])==day.year or int(season[:4])+1==day.year):
            raise ArchiveProbeError("SEASON_WRONG_DATE")
        counts[season]+=1
    if counts!={x:20 for x in SEASONS}:
        raise ArchiveProbeError("NOT_STRATIFIED_20_PER_SEASON")
    return sample

def commits_for_season(season,fetcher=None):
    if season not in SEASONS:
        raise ArchiveProbeError("NOT_ALLOWED_SEASON")
    if fetcher is None:
        def fetcher(url):
            req=urllib.request.Request(url,headers={"User-Agent":"KB3-research-archive-probe"})
            with urllib.request.urlopen(req,timeout=20) as f:
                return json.loads(f.read(500_000))
    collected=[]
    for page in range(1,MAX_PAGES+1):
        url=f"https://api.github.com/repos/openfootball/football.json/commits?path={season}%2Fen.1.json&per_page=100&page={page}"
        data=fetcher(url)
        if type(data) is not list:
            raise ArchiveProbeError("GITHUB_API_REJECTED")
        for obj in data:
            sha=obj.get("sha")
            stamp=obj.get("commit",{}).get("committer",{}).get("date")
            if type(sha) is not str or len(sha)!=40 or not all(x in "0123456789abcdef" for x in sha):
                raise ArchiveProbeError("BAD_PUBLIC_COMMIT_SHA")
            collected.append((stamp,sha))
        if len(data)<100:
            break
    if not collected:
        return []
    return sorted({(_utc(t),s) for t,s in collected},reverse=True)

def scan(roster,safe,metadata):
    pilot=validate_roster(roster,safe)
    if set(metadata)!=set(SEASONS):
        raise ArchiveProbeError("METADATA_SOURCE_INCOMPLETE")
    candidate_counts={s:0 for s in SEASONS}
    matches=[]
    for r in pilot:
        cutoff=_utc(r["kickoff_utc"])-timedelta(hours=48)
        found=next(((dt,sha) for dt,sha in metadata[r["season"]] if dt<cutoff),None)
        if found:
            candidate_counts[r["season"]]+=1
        matches.append({
            "fixture_id":r["fixture_id"],
            "kickoff_utc":r["kickoff_utc"],
            "partition":r["partition"],"season":r["season"],
            "github_commit_date_candidate_before_cutoff": bool(found),
            "candidate_commit_sha":found[1] if found else None,
            "candidate_commit_timestamp_utc":found[0].isoformat().replace("+00:00","Z") if found else None,
            "snapshot_content_match_verified":False,
            "pitchapi_fixture_crosswalk_verified":False,
            "historical_public_availability_independently_proven":False,
            "admitted_to_m1_train":False,
        })
    return {"schema":"kb3-step14-archived-snapshot-candidates-v1",
        "evidence_class":"GITHUB_COMMIT_METADATA_ONLY_NOT_INDEPENDENT_PUBLICATION_OR_FIXTURE_PROOF",
        "sample_count":60,"sample_counts":{"TRAIN":40,"VALIDATION":20},
        "public_commit_candidates_by_season":candidate_counts,
        "total_commit_date_candidates":sum(candidate_counts.values()),
        "independently_pit_certified_rows":0,
        "eligible_real_train_rows":0,
        "new_provider_api_calls":0,
        "test_rows_read":0,"historical_pit_certified":False,
        "gate14_pass":False,"candidate_records":matches}

def run(root=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    roster=json.loads((root/PILOT).read_text(encoding="utf-8"))
    safe=json.loads((root/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text(encoding="utf-8"))
    metadata={s:commits_for_season(s) for s in SEASONS}
    return scan(roster,safe,metadata)

if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("--out",required=True)
    args=a.parse_args()
    result=run()
    target=Path(args.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("sample_counts","public_commit_candidates_by_season",
        "total_commit_date_candidates","independently_pit_certified_rows","eligible_real_train_rows")},sort_keys=True))
