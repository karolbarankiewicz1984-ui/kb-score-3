"""Step13 / task 2: offline leakage review, no provider calls/outcome reads.

Audits original frozen first snapshot and static provider-query boundary.
Checks the launch scripts' SDK method selections; further runtime tests
fail closed on future scores, unexpected validation training, and fixture drift.
"""
from __future__ import annotations
import argparse,ast,json
from pathlib import Path
from src.kb3_split import sha,freeze_manifest,timestamp
from src.kb3_step13_baseline import BaselineSafetyError
from src.kb3_step13_forward_score import SOURCE_FILE,SOURCE_HASH

SCHEMA="kb3-step13-prospective-leakage-audit-v1"
SCRIPTS=("scripts/step13_prematch_forward_once.py",)
ALLOWED_TRAIN={"2023/2024","2024/2025"}

def source_policy_scan(path):
    src=Path(path).read_text(encoding="utf8")
    tree=ast.parse(src)
    # Source must call the same SDK only as "client.leagues.matches";
    # forbid status=all, to avoid accidental TEST scores in the forward pilot.
    queries=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or node.func.attr!="matches":
            continue
        kws={k.arg:k.value for k in node.keywords}
        if "status" not in kws or not isinstance(kws["status"],ast.Constant):
            raise BaselineSafetyError("STEP13_LEAK_QUERY_WITHOUT_LITERAL_STATUS")
        queries.append(kws["status"].value)
    if sorted(queries)!=["played","upcoming"]:
        raise BaselineSafetyError("STEP13_LEAK_PROVIDER_QUERY_POLICY_CHANGED")
    if not all(s in src for s in ("TRAIN_SEASONS","TARGET_SEASON","train_only","status=\"upcoming\"")):
        raise BaselineSafetyError("STEP13_LEAK_SOURCE_GATES_MISSING")
    return queries

def audit():
    from src.kb3_step13_forward_score import _check_snapshot
    snapshot=json.loads(Path(SOURCE_FILE).read_text(encoding="utf8"))
    records=_check_snapshot(snapshot)
    if len(records)!=10 or len({(f["home_team_id"],f["away_team_id"],f["kickoff_utc"]) for f in records.values()})!=10:
        raise BaselineSafetyError("STEP13_LEAK_DUPLICATE_TARGET")
    if (snapshot["historical_train_seasons"]!=sorted(ALLOWED_TRAIN) or
        snapshot["provider_request_policy"]!="2_FINISHED_HISTORICAL_TRAIN_LISTS_PLUS_1_UPCOMING_ONLY_TEST_SCHEDULE" or
        snapshot["provider_requests"]!=3 or
        snapshot["rating_limitation"]!="OUTDATED_ELO_AS_OF_2025_07_01_NO_CURRENT_SEASON_RESULTS" or
        snapshot["historical_2023_2026_prematch_pit_certified"] is not False or
        snapshot["no_odds_or_market_inputs"] is not True):
        raise BaselineSafetyError("STEP13_LEAK_PROVENANCE_CHANGED")
    safe=json.loads(Path("data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json").read_text())
    if safe["partition_counts"]!={"TRAIN":760,"VALIDATION":380,"TEST":380}:
        raise BaselineSafetyError("STEP13_LEAK_SPLIT_CHANGED")
    frozen={f["fixture_id"]:f for f in safe["fixtures"] if f["partition"]=="TEST"}
    if set(records)-set(frozen):
        raise BaselineSafetyError("STEP13_LEAK_NOT_TEST_FIXTURE")
    for fid,row in records.items():
        if row["scores_at_source"]!={"home":None,"away":None}:
            raise BaselineSafetyError("STEP13_LEAK_TEST_LABEL_IN_PREMATCH")
        if timestamp(row["kickoff_utc"])!=timestamp(frozen[fid]["kickoff_utc"]):
            raise BaselineSafetyError("STEP13_LEAK_KICKOFF_CHANGED")
    reads=source_policy_scan(SCRIPTS[0])
    result={
        "schema":SCHEMA,
        "snapshot_sha256":SOURCE_HASH,
        "train_input_seasons":list(snapshot["historical_train_seasons"]),
        "train_scores_permitted":760,
        "validation_scores_permitted":0,
        "test_scores_permitted":0,
        "test_metadata_only_future_targets":10,
        "test_other_outcomes_read":0,
        "frozen_fixture_ids_match_safe_test_partition":True,
        "all_frozen_provider_scores_null":True,
        "query_statuses_static":sorted(reads),
        "query_policy":"TRAIN_PLAYED_PLUS_TEST_UPCOMING_ONLY",
        "original_provider_publication_time_verified":False,
        "historical_pit_proven":False,
        "source_code_query_scan_is_not_a_runtime_trace":True,
        "data_inspected":"ORIGINAL_PREDICTION_JSON_AND_SPLIT_METADATA_ONLY",
        "result_labels_read":0,
        "network_calls":0,
        "training_allowed":False,"gate13_pass":False,
    }
    result["report_sha256"]=sha(result)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    z=p.parse_args()
    r=audit()
    freeze_manifest(r,z.output)
    print("STEP13_PREMATCH_STATIC_AND_FROZEN_DATA_LEAKAGE_AUDIT_PASS",r["report_sha256"])
if __name__=="__main__":main()
