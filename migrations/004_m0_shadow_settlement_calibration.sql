-- Append-only actual observed result/metrics for shadow M0 1X2.
CREATE TABLE IF NOT EXISTS m0_shadow_settlements (
 forecast_id TEXT PRIMARY KEY REFERENCES m0_shadow_1x2_forecasts(forecast_id),
 result_1x2 TEXT NOT NULL CHECK(result_1x2 IN ('1','X','2')),
 goals_home_90 INTEGER NOT NULL CHECK(goals_home_90>=0),
 goals_away_90 INTEGER NOT NULL CHECK(goals_away_90>=0),
 source_observed_utc TEXT NOT NULL,
 result_kickoff_utc TEXT NOT NULL,
 source_season TEXT NOT NULL CHECK(source_season='2026/2027'),
 source_payload_sha256 TEXT NOT NULL,
 source_chain_sha256 TEXT NOT NULL,
 log_loss REAL NOT NULL CHECK(log_loss>=0),
 brier_sum3 REAL NOT NULL CHECK(brier_sum3>=0 AND brier_sum3<=2),
 settled_at_utc TEXT NOT NULL,
 settlement_sha256 TEXT NOT NULL UNIQUE,
 FOREIGN KEY(forecast_id) REFERENCES m0_shadow_1x2_forecasts(forecast_id)
);
CREATE TRIGGER IF NOT EXISTS m0_settlement_insert_guard
BEFORE INSERT ON m0_shadow_settlements BEGIN
 SELECT CASE WHEN NOT EXISTS (
   SELECT 1 FROM m0_shadow_1x2_forecasts p
   WHERE p.forecast_id=NEW.forecast_id
     AND p.kickoff_utc=NEW.result_kickoff_utc
     AND julianday(p.generated_at_utc)<julianday(p.kickoff_utc)-90.0/1440.0
     AND p.calibration_status='NONE'
 ) OR julianday(NEW.source_observed_utc)<julianday(NEW.result_kickoff_utc)+3.0/24.0
 OR julianday(NEW.settled_at_utc)<julianday(NEW.source_observed_utc)
 OR julianday('now')<julianday(NEW.result_kickoff_utc)+3.0/24.0
 THEN RAISE(ABORT,'M0_SETTLEMENT_TEMPORAL_OR_FORECAST_ID_FAIL') END;
END;
CREATE TRIGGER IF NOT EXISTS m0_settlement_no_update BEFORE UPDATE ON m0_shadow_settlements
BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_settlement_no_delete BEFORE DELETE ON m0_shadow_settlements
BEGIN SELECT RAISE(ABORT,'M0_SETTLEMENT_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS m0_shadow_calibration_audits (
 audit_id TEXT PRIMARY KEY,
 observed_at_utc TEXT NOT NULL,
 engine TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase='EARLY'),
 resolved_unique_matches INTEGER NOT NULL CHECK(resolved_unique_matches>=0),
 minimum_fit INTEGER NOT NULL CHECK(minimum_fit=100),
 minimum_later_holdout INTEGER NOT NULL CHECK(minimum_later_holdout=50),
 state TEXT NOT NULL CHECK(state IN ('COLLECTING','FITTED_AWAIT_HOLDOUT','EVALUATED_NO_AUTO_APPROVAL')),
 report_sha256 TEXT NOT NULL UNIQUE,
 report_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS m0_calib_no_update BEFORE UPDATE ON m0_shadow_calibration_audits
BEGIN SELECT RAISE(ABORT,'M0_CALIB_AUDIT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_calib_no_delete BEFORE DELETE ON m0_shadow_calibration_audits
BEGIN SELECT RAISE(ABORT,'M0_CALIB_AUDIT_IMMUTABLE'); END;
