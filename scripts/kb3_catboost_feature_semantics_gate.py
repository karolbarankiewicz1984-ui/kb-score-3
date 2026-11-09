"""Fail-closed research gate for historical CatBoost vs live forward semantics.

The frozen 85-feature M1-R was trained with a historical 48-hour selection
window; the Step16 forward source uses a 3-hour result maturity rule.
Identical column names/order do NOT establish identical as-of semantics.
This gate never modifies frozen forecasts, model weights or protected TEST.
"""
from __future__ import annotations
import json

SCHEMA = "kb3-catboost-feature-semantics-gate-v1"
TRAIN = {"model": "CATBOOST_NO_XG_M1R_85", "historical_result_lag_hours": 48,
         "source": "RECONSTRUCTED_HISTORICAL"}
FORWARD = {"model": "CATBOOST_NO_XG_M1R_85", "result_maturity_hours": 3,
           "source": "OBSERVED_AT_NOT_CERTIFIED"}


def assess(train=TRAIN, forward=FORWARD):
    train_lag = train.get("historical_result_lag_hours")
    forward_lag = forward.get("result_maturity_hours")
    same_lag = (type(train_lag) in (int, float)
                and type(forward_lag) in (int, float)
                and train_lag == forward_lag)
    certified = (train.get("independent_pit_certified") is True
                 and forward.get("independent_pit_certified") is True)
    parity = same_lag and certified and (
        train.get("shared_feature_contract_sha256") is not None
        and train.get("shared_feature_contract_sha256")
        == forward.get("shared_feature_contract_sha256"))
    return {"schema": SCHEMA, "model": "CATBOOST_NO_XG_M1R_85",
            "train_result_lag_hours": train_lag,
            "forward_result_lag_hours": forward_lag,
            "same_asof_semantics_proven": bool(parity),
            "independent_pit_certified": bool(certified),
            "champion_eligible": False,
            "research_shadow_only": True,
            "blocking_reasons": [] if parity else [
                "P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS",
                "SHARED_CONTRACT_AND_INDEPENDENT_PIT_NOT_BOTH_PROVEN"],
            "required_action": "NEW_MODEL_RETRAIN_ON_SHARED_ASOF_V2_AND_FORWARD_PARITY_TESTS",
            "old_model_weights_unchanged": True,
            "no_backdated_forecasts": True}


if __name__ == "__main__":
    print(json.dumps(assess(), sort_keys=True))
