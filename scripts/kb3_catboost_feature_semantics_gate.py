"""Fail-closed research gate for historical CatBoost vs live forward semantics.

The frozen 85-feature M1-R was trained with a historical 48-hour selection
window; the Step16 forward source uses a 3-hour result maturity rule.
Identical column names/order do NOT establish identical as-of semantics.
This gate never modifies frozen forecasts, model weights or protected TEST.
"""
from __future__ import annotations
import json
import math
import re
from src.kb3_features import digest

SCHEMA = "kb3-catboost-feature-semantics-gate-v2"
TRAIN = {"model": "CATBOOST_NO_XG_M1R_85", "historical_result_lag_hours": 48,
         "source": "RECONSTRUCTED_HISTORICAL"}
FORWARD = {"model": "CATBOOST_NO_XG_M1R_85", "result_maturity_hours": 3,
           "source": "OBSERVED_AT_NOT_CERTIFIED"}


def assess(train=TRAIN, forward=FORWARD, *, contract_document=None,
           train_manifest=None, forward_manifest=None):
    train_lag = train.get("historical_result_lag_hours")
    forward_lag = forward.get("result_maturity_hours")
    same_lag = (type(train_lag) in (int, float)
                and type(forward_lag) in (int, float)
                and math.isfinite(train_lag) and math.isfinite(forward_lag)
                and train_lag >= 0 and train_lag == forward_lag)
    certified = (train.get("independent_pit_certified") is True
                 and forward.get("independent_pit_certified") is True)
    sha = train.get("shared_feature_contract_sha256")
    def safe_digest(value):
        try:
            return digest(value)
        except (TypeError, ValueError):
            return None
    real_sha = isinstance(sha, str) and re.fullmatch(r"[a-f0-9]{64}", sha)
    contract_ok = bool(real_sha and isinstance(contract_document, dict)
        and safe_digest(contract_document) == sha == forward.get("shared_feature_contract_sha256")
        and contract_document.get("result_min_lag_hours") == train_lag)
    def manifest_ok(m):
        return (isinstance(m, dict) and m.get("feature_contract_sha256") == sha
                and m.get("manifest_sha256") is not None
                and m.get("manifest_sha256") == safe_digest({
                    k:v for k,v in m.items() if k != "manifest_sha256"}))
    manifests_ok = manifest_ok(train_manifest) and manifest_ok(forward_manifest)
    parity = same_lag and certified and contract_ok and manifests_ok
    reasons = []
    if not same_lag:
        reasons.append("P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS")
    if not (certified and contract_ok and manifests_ok):
        reasons.append("SHARED_CONTRACT_AND_INDEPENDENT_PIT_NOT_BOTH_PROVEN")
    return {"schema": SCHEMA, "model": "CATBOOST_NO_XG_M1R_85",
            "train_result_lag_hours": train_lag,
            "forward_result_lag_hours": forward_lag,
            "same_asof_semantics_proven": bool(parity),
            "independent_pit_certified": bool(certified),
            "contract_sha256_verified": contract_ok,
            "manifest_sha256_verified": manifests_ok,
            "evidence_scope": "METADATA_DIAGNOSTIC_NOT_SOURCE_BYTE_ATTESTATION",
            "champion_eligible": False,
            "research_shadow_only": True,
            "blocking_reasons": reasons,
            "required_action": "NEW_MODEL_RETRAIN_ON_SHARED_ASOF_V2_AND_FORWARD_PARITY_TESTS",
            "old_model_weights_unchanged": True,
            "no_backdated_forecasts": True}


if __name__ == "__main__":
    print(json.dumps(assess(), sort_keys=True))
