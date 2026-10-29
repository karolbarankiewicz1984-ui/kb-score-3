"""Separate Step17 8-league native observed xG as-of research, no training."""
import json,os
from datetime import datetime,timezone
from src.kb3_step17_xg_capture import run,ARCHIVE,DB
def main():
    now=datetime.now(timezone.utc)
    if (ARCHIVE/now.date().isoformat()/"XG_READINESS_RECEIPT.json").is_file():
        print("STEP17_XG_RESEARCH_ALREADY_CAPTURED_TODAY")
        return
    secret=os.getenv("PITCHAPI_API_KEY","")
    if not secret:raise SystemExit("EXISTING_PITCHAPI_SECRET_NOT_CONFIGURED")
    from pitchapi import PitchAPI
    result=run(client=PitchAPI(api_key=secret),now=now)
    public={k:result[k] for k in (
        "schema","network_calls","hard_limit_calls","leagues",
        "prior_matches_selected","new_shots_stats_xg_verified",
        "cumulative_verified_xg_matches","future_form5_coverage",
        "training_ready","trained_xg_catboost_exists","gate17","report_sha256")}
    print("STEP17_XG_REAL_OBSERVED_SHADOW",json.dumps(public,sort_keys=True))
if __name__=="__main__":main()
