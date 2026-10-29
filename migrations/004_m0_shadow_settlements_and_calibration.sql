-- Step 14 research M0: append-only 1/X/2 outcome evaluation.
-- Separate from production M1 predictions, historical GATE14 and TEST.
CREATE TABLE IF NOT EXISTS m0_shadow_1x2_settlements (
 settlement_id TEXT PRIMARY KEY,
 forecast_id TEXT NOT NULL UNIQUE REFERENCES m0_shadow_1x2_forecasts(forecast_id),
 league_country TEXT NOT NULL CHECK(league_country IN ('ESP','ITA','GER')),
 provider_match_id TEXT NOT NULL,
 frozen_kickoff_utc TEXT NOT NULL,
 actual_result_observed_at_utc TEXT NOT NULL,
 source_snapshot_sha256 TEXT NOT NULL,
 observed_score_home INTEGER NOT NULL CHECK(observed_score_home BETWEEN 0 AND 30),
 observed_score_away INTEGER NOT NULL CHECK(observed_score_away BETWEEN 0 AND 30),
 outcome_1x2 TEXT NOT NULL CHECK(outcome_1x2 IN ('1','X','2')),
 log_loss REAL NOT NULL CHECK(log_loss>=0),
 brier_sum3 REAL NOT NULL CHECK(brier_sum3>=0 AND brier_sum3<=2),
 settlement_sha256 TEXT NOT NULL UNIQUE,
 UNIQUE(league_country,provider_match_id)
);
CREATE TRIGGER IF NOT EXISTS m0_settle_no_update BEFORE UPDATE ON m0_shadow_1x2_settlements
 BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_settle_no_delete BEFORE DELETE ON m0_shadow_1x2_settlements
 BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_settle_guard BEFORE INSERT ON m0_shadow_1x2_settlements
 BEGIN SELECT CASE WHEN
  NOT EXISTS (
    SELECT 1 FROM m0_shadow_1x2_forecasts p
     WHERE p.forecast_id=NEW.forecast_id
     AND p.league_country=NEW.league_country
     AND p.provider_match_id=NEW.provider_match_id
     AND p.kickoff_utc=NEW.frozen_kickoff_utc
     AND julianday(p.generated_at_utc)<julianday(p.kickoff_utc)-90.0/1440.0
     AND p.status='SHADOW_UNFITTED_NOT_FOR_BETTING'
  )
  OR julianday(NEW.actual_result_observed_at_utc)<
      julianday(NEW.frozen_kickoff_utc)+3.0/24.0
  OR julianday(NEW.actual_result_observed_at_utc)>julianday('now')+3.0/86400.0
  OR julianday('now')<julianday(NEW.frozen_kickoff_utc)+3.0/24.0
  THEN RAISE(ABORT,'M0_SETTLEMENT_TIME_OR_FROZEN_FORECAST_INVALID') END;
 END;
-- Immutable candidate: fit uses only past already settled records and
-- cannot be overwritten by later outcomes. Never activates production.
CREATE TABLE IF NOT EXISTS m0_shadow_calibration_candidates (
 candidate_id TEXT PRIMARY KEY,
 model_version_id TEXT NOT NULL REFERENCES model_versions(model_version_id),
 phase TEXT NOT NULL CHECK(phase='EARLY'),
 scope TEXT NOT NULL CHECK(scope='ESP_ITA_GER_POOLED_RESEARCH'),
 calibration_cutoff_utc TEXT NOT NULL,
 fitted_at_utc TEXT NOT NULL,
 fitted_temperature REAL NOT NULL CHECK(fitted_temperature BETWEEN 0.1 AND 10),
 fitting_sample_size INTEGER NOT NULL CHECK(fitting_sample_size>=100),
 training_forecast_ids_sha256 TEXT NOT NULL,
 raw_fit_log_loss REAL NOT NULL,
 calibrated_fit_log_loss REAL NOT NULL,
 candidate_payload_sha256 TEXT NOT NULL UNIQUE,
 production_approved INTEGER NOT NULL DEFAULT 0 CHECK(production_approved=0),
 UNIQUE(model_version_id,phase,scope)
);
CREATE TRIGGER IF NOT EXISTS m0_cal_candidate_no_update BEFORE UPDATE ON m0_shadow_calibration_candidates
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_FIT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_cal_candidate_no_delete BEFORE DELETE ON m0_shadow_calibration_candidates
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_FIT_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS m0_shadow_calibration_holdout_reviews (
 review_id TEXT PRIMARY KEY,
 candidate_id TEXT NOT NULL UNIQUE REFERENCES m0_shadow_calibration_candidates(candidate_id),
 reviewed_at_utc TEXT NOT NULL,
 independent_post_fit_matches INTEGER NOT NULL CHECK(independent_post_fit_matches>=50),
 holdout_forecast_ids_sha256 TEXT NOT NULL,
 raw_log_loss REAL NOT NULL,
 calibrated_log_loss REAL NOT NULL,
 raw_brier_sum3 REAL NOT NULL,
 calibrated_brier_sum3 REAL NOT NULL,
 raw_ece_top1 REAL NOT NULL,
 calibrated_ece_top1 REAL NOT NULL,
 improvement_confirmed INTEGER NOT NULL CHECK(improvement_confirmed IN (0,1)),
 approved_for_production INTEGER NOT NULL DEFAULT 0 CHECK(approved_for_production=0),
 review_sha256 TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS m0_cal_review_no_update BEFORE UPDATE ON m0_shadow_calibration_holdout_reviews
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_REVIEW_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_cal_review_no_delete BEFORE DELETE ON m0_shadow_calibration_holdout_reviews
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_REVIEW_IMMUTABLE'); END;
