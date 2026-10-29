-- 004: settle genuine already-frozen research M0 1/X/2 and preserve audit history.
-- NEVER modifies m0_shadow_1x2_forecasts nor original strict PIT predictions.
CREATE TABLE IF NOT EXISTS m0_shadow_result_sources (
 source_id TEXT PRIMARY KEY,
 league_country TEXT NOT NULL CHECK(league_country IN ('ESP','ITA','GER')),
 season TEXT NOT NULL CHECK(season='2026/2027'),
 captured_at_utc TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL,
 chain_sha256 TEXT NOT NULL,
 original_published_at_utc TEXT CHECK(original_published_at_utc IS NULL)
);
CREATE TRIGGER IF NOT EXISTS m0_result_sources_no_update
 BEFORE UPDATE ON m0_shadow_result_sources
 BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_SOURCE_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_result_sources_no_delete
 BEFORE DELETE ON m0_shadow_result_sources
 BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_SOURCE_IMMUTABLE'); END;

CREATE TABLE IF NOT EXISTS m0_shadow_1x2_settlements (
 settlement_id TEXT PRIMARY KEY,
 forecast_id TEXT NOT NULL UNIQUE REFERENCES m0_shadow_1x2_forecasts(forecast_id),
 source_id TEXT NOT NULL REFERENCES m0_shadow_result_sources(source_id),
 observed_at_utc TEXT NOT NULL,
 provider_match_id TEXT NOT NULL,
 league_country TEXT NOT NULL CHECK(league_country IN ('ESP','ITA','GER')),
 kickoff_utc TEXT NOT NULL,
 home_goals_90 INTEGER NOT NULL CHECK(home_goals_90 BETWEEN 0 AND 30),
 away_goals_90 INTEGER NOT NULL CHECK(away_goals_90 BETWEEN 0 AND 30),
 result_1x2 TEXT NOT NULL CHECK(result_1x2 IN ('1','X','2')),
 log_loss REAL NOT NULL CHECK(log_loss>=0),
 brier_sum3 REAL NOT NULL CHECK(brier_sum3>=0 AND brier_sum3<=2),
 top1_correct INTEGER NOT NULL CHECK(top1_correct IN (0,1)),
 audit_sha256 TEXT NOT NULL UNIQUE,
 CHECK((home_goals_90>away_goals_90 AND result_1x2='1') OR
       (home_goals_90=away_goals_90 AND result_1x2='X') OR
       (home_goals_90<away_goals_90 AND result_1x2='2'))
);
CREATE TRIGGER IF NOT EXISTS m0_settlement_before_insert
 BEFORE INSERT ON m0_shadow_1x2_settlements
 BEGIN SELECT CASE WHEN
  NOT EXISTS (
    SELECT 1 FROM m0_shadow_1x2_forecasts p
    JOIN m0_shadow_result_sources s ON s.source_id=NEW.source_id
    WHERE p.forecast_id=NEW.forecast_id
      AND p.league_country=NEW.league_country
      AND p.provider_match_id=NEW.provider_match_id
      AND p.kickoff_utc=NEW.kickoff_utc
      AND s.league_country=NEW.league_country
      AND s.captured_at_utc=NEW.observed_at_utc
      AND julianday(p.generated_at_utc)<julianday(p.kickoff_utc)-90.0/1440.0
      AND julianday(p.feature_cutoff_utc)<julianday(p.generated_at_utc))
   OR julianday(NEW.observed_at_utc)<julianday(NEW.kickoff_utc)+3.0/24.0
   OR julianday(NEW.observed_at_utc)>julianday('now')+3.0/86400.0
   OR julianday(NEW.kickoff_utc) IS NULL
   OR julianday(NEW.observed_at_utc) IS NULL
  THEN RAISE(ABORT,'M0_NOT_FINISHED_OR_WRONG_PREMATCH_FORECAST') END; END;
CREATE TRIGGER IF NOT EXISTS m0_settlement_no_update
 BEFORE UPDATE ON m0_shadow_1x2_settlements
 BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_settlement_no_delete
 BEFORE DELETE ON m0_shadow_1x2_settlements
 BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_IMMUTABLE'); END;

CREATE TABLE IF NOT EXISTS m0_shadow_calibration_candidates (
 candidate_id TEXT PRIMARY KEY,
 model_version_id TEXT NOT NULL,
 parameter_sha256 TEXT NOT NULL,
 phase TEXT NOT NULL DEFAULT 'EARLY' CHECK(phase='EARLY'),
 scope TEXT NOT NULL DEFAULT 'ESP_ITA_GER' CHECK(scope='ESP_ITA_GER'),
 fit_cutoff_utc TEXT NOT NULL,
 created_at_utc TEXT NOT NULL,
 fit_n INTEGER NOT NULL CHECK(fit_n>=100),
 temperature REAL NOT NULL CHECK(temperature>=0.1 AND temperature<=10),
 fit_records_sha256 TEXT NOT NULL,
 fit_log_loss_raw REAL NOT NULL,
 fit_log_loss_calibrated REAL NOT NULL,
 status TEXT NOT NULL DEFAULT 'CANDIDATE_NOT_ACTIVATED'
   CHECK(status='CANDIDATE_NOT_ACTIVATED'),
 UNIQUE(model_version_id,parameter_sha256,phase,scope)
);
CREATE TRIGGER IF NOT EXISTS m0_candidate_no_update
 BEFORE UPDATE ON m0_shadow_calibration_candidates
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_FIT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_candidate_no_delete
 BEFORE DELETE ON m0_shadow_calibration_candidates
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_FIT_IMMUTABLE'); END;

CREATE TABLE IF NOT EXISTS m0_shadow_calibration_evaluations (
 evaluation_id TEXT PRIMARY KEY,
 candidate_id TEXT NOT NULL UNIQUE REFERENCES m0_shadow_calibration_candidates(candidate_id),
 created_at_utc TEXT NOT NULL,
 holdout_n INTEGER NOT NULL CHECK(holdout_n>=50),
 holdout_records_sha256 TEXT NOT NULL,
 raw_log_loss REAL NOT NULL,
 calibrated_log_loss REAL NOT NULL,
 raw_brier_sum3 REAL NOT NULL,
 calibrated_brier_sum3 REAL NOT NULL,
 raw_ece REAL NOT NULL,
 calibrated_ece REAL NOT NULL,
 recommended_for_manual_review INTEGER NOT NULL CHECK(recommended_for_manual_review IN (0,1)),
 automatic_activation INTEGER NOT NULL DEFAULT 0 CHECK(automatic_activation=0)
);
CREATE TRIGGER IF NOT EXISTS m0_evaluation_no_update
 BEFORE UPDATE ON m0_shadow_calibration_evaluations
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_EVALUATION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_evaluation_no_delete
 BEFORE DELETE ON m0_shadow_calibration_evaluations
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_EVALUATION_IMMUTABLE'); END;
