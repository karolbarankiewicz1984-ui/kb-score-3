"""Phase 2: expand 2025/26 real old-server-clock source snapshots to 25.

All 25 pinned SHAs are corroborated by an independently timestamped,
successful GitHub Actions MAIN run with that exact head_sha. Do not use git
committer dates to authorize features. Original 57 are invariant.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from scripts.step14_2025_expand_witnessed_form5_asof import (
    ALL as OLD,source_at_version,ROOT,_utc)
from scripts.step14_fpl_core_2025_independent_asof import _reference
from scripts.step14_fplcore_native_2025_crosswalk_semantics import load_public

SCHEMA="kb3-step14-2025-26-25-independent-server-witnessed-revisions-v1"
NEW=(
 ("951d97b588a4a588d2d65b2f218d38acf5de8544",18144710019,6,"2025-09-30T22:05:50Z"),
 ("69c717029c58e58aaf14290d01210c4e78b0748a",18636725725,8,"2025-10-19T22:05:11Z"),
 ("c96dd29d782fc31d6a4c0ef68a162d11b4093e4f",18986309168,10,"2025-10-31T22:05:38Z"),
 ("950fac82faad98ef5e67d10d3aebef5d3aa826f4",19325164110,13,"2025-11-13T08:24:58Z"),
 ("fe803fcd79108b0819cf89e680b47ed78010e5bf",19789908678,14,"2025-11-29T22:05:13Z"),
 ("88e0fd0d6ddd125ff930676138b4b5072331b578",20551180109,18,"2025-12-28T08:24:55Z"),
 ("8b67991e3c4d1e2ba95f6db007b326722185be8b",21202396013,22,"2026-01-21T08:25:33Z"),
 ("f16072e7b83fec120803f6590c6ef166e80ebd8f",21509363516,23,"2026-01-30T08:26:17Z"),
 ("d56093e92dbd0860d36dfe5055ff52abada3fce5",22783984313,29,"2026-03-06T22:08:35Z"),
 ("537907bee7a3cb1223c4e160c57fa7c9a74f87b4",23286219110,30,"2026-03-19T08:26:52Z"),
 ("2a8c0981a65931fcb54fe4e29ffbe26477da232c",24126202779,32,"2026-04-08T08:39:54Z"),
)
SOURCE_LIST=tuple(sorted((*OLD,*NEW),key=lambda s:_utc(s[3])))
if len(SOURCE_LIST)!=25 or len({x[0] for x in SOURCE_LIST})!=25:
    raise ValueError("DENSE_HISTORICAL_SOURCE_SET_AMBIGUOUS")
class DenseError(ValueError): pass

def run(root=ROOT):
    root=Path(root)
    old=json.loads((root/"data/audits/STEP14_2025_FPLCORE_EXPANDED_14_WITNESSED_VERSIONS_2026-10-29.json").read_text())
    if old.get("historical_versions_count")!=14 or old.get("total_distinct_prematch_public_FORM5_targets")!=57:
        raise DenseError("ORIGINAL_57_AUDIT_NOT_IMMUTABLE")
    pub,_=load_public(root)
    ref=_reference(root/"data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json")
    rows={}
    versions=[]
    for s in SOURCE_LIST:
        evidence,eligible=source_at_version(s,ref)
        versions.append(evidence)
        for t in eligible:
            key=(t["target_public_home"],t["target_public_away"],t["target_kickoff_utc"])
            if key not in rows or _utc(rows[key]["source_publication_witness_utc"])<_utc(t["source_publication_witness_utc"]):
                rows[key]=t
    previous={(t["target_public_home"],t["target_public_away"],t["target_kickoff_utc"]) for t in old["targets"]}
    first18={(t["target_public_home"],t["target_public_away"],t["target_kickoff_utc"]) for t in pub["candidates"]}
    if not previous<=set(rows) or not first18<=set(rows):
        raise DenseError("PREVIOUSLY_PROVEN_57_OR_18_MISSING")
    sortedrows=sorted(rows.values(),key=lambda t:(t["target_kickoff_utc"],t["target_public_home"],t["target_public_away"]))
    return {"schema":SCHEMA,"all_original_57_preserved":True,
      "independent_GitHub_server_witnessed_old_versions":len(versions),
      "new_historical_source_versions":len(NEW),
      "historically_public_source_FORM5_targets":len(sortedrows),
      "historically_public_source_xg5_complete_targets":sum(all(
          not t["prematch_public_FORM5"][side]["alternative_xg_missing"] for side in ("home","away"))
          for t in sortedrows),
      "new_distinct_targets_beyond_57":len(sortedrows)-57,
      "new_distinct_targets_beyond_original_18":len(sortedrows)-18,
      "source_original_xg_definition_is_not_proven_PitchAPI":True,
      "source_provider_first_published_time_PitchAPI_is_unverified":True,
      "provider_original_121_plus_38_PIT_certified":0,
      "original_M1_fit_allowed":False,"TEST_2026_27_examined":False,"GATE14":"PENDING",
      "source_versions":versions,"targets":sortedrows}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    dest=Path(p.parse_args().out)
    if dest.exists():raise DenseError("NO_REPORT_OVERWRITE")
    report=run()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"old_sources":report["independent_GitHub_server_witnessed_old_versions"],
      "targets":report["historically_public_source_FORM5_targets"],
      "new_over_57":report["new_distinct_targets_beyond_57"],
      "xg5":report["historically_public_source_xg5_complete_targets"],
      "official_M1_FIT":False},sort_keys=True))
if __name__=="__main__":main()
