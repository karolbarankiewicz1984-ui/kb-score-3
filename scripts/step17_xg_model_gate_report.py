"""Freeze actual historical evidence gate for research CatBoost with native xG."""
from __future__ import annotations
import json
from pathlib import Path
from src.kb3_step17_xg_model_gate import actual_readiness
OUT=Path("data/audits/STEP17_CATBOOST_XG_TRAINING_GATE_2026-10-29.json")
def main():
    report=actual_readiness()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if OUT.exists():
        assert json.loads(OUT.read_text())==report,"IMMUTABLE_XG_GATE_DRIFT"
    else:
        with OUT.open("x",encoding="utf8") as f:
            json.dump(report,f,sort_keys=True,ensure_ascii=False,indent=2);f.write("\n")
    print("STEP17_XG_TRAINING_GATE",json.dumps({k:report[k] for k in (
       "engine","status","model_fitted","native_PitchAPI_2023_25_asof_qualified_TRAIN",
       "native_PitchAPI_2023_25_asof_qualified_VALIDATION",
       "historical_alternative_FPL_player_xg5_complete_TRAIN_760","gate17",
       "readiness_sha256")},sort_keys=True))
if __name__=="__main__":main()
