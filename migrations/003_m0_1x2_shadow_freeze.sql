-- 003: research-only M0 Elo+Poisson 1/X/2 immutable genuine prematch forecasts.
-- Do not misrepresent observed source data as the historic originally published
-- training PIT which legacy original predictions table strictly requires.
CREATE TABLE IF NOT EXISTS m0_shadow_1x2_forecasts (
 forecast_id TEXT PRIMARY KEY,
 feature_snapshot_id TEXT NOT NULL UNIQUE REFERENCES feature_snapshots(feature_snapshot_id),
 fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
 model_version_id TEXT NOT NULL REFERENCES model_versions(model_version_id),
 league_country TEXT NOT NULL CHECK(league_country IN ('ESP','ITA','GER')),
 provider_match_id TEXT NOT NULL,
 kickoff_utc TEXT NOT NULL,
 feature_cutoff_utc TEXT NOT NULL,
 generated_at_utc TEXT NOT NULL,
 p_1 REAL NOT NULL CHECK(p_1>0 AND p_1<1),
 p_x REAL NOT NULL CHECK(p_x>0 AND p_x<1),
 p_2 REAL NOT NULL CHECK(p_2>0 AND p_2<1),
 expected_home_goals REAL NOT NULL CHECK(expected_home_goals>0),
 expected_away_goals REAL NOT NULL CHECK(expected_away_goals>0),
 feature_sha256 TEXT NOT NULL,
 parameter_sha256 TEXT NOT NULL,
 prediction_payload_sha256 TEXT NOT NULL UNIQUE,
 source_chain_sha256 TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'SHADOW_UNFITTED_NOT_FOR_BETTING'
   CHECK(status='SHADOW_UNFITTED_NOT_FOR_BETTING'),
 calibration_status TEXT NOT NULL DEFAULT 'NONE'
   CHECK(calibration_status='NONE'),
 phase TEXT NOT NULL DEFAULT 'EARLY' CHECK(phase='EARLY'),
 CHECK(abs(p_1+p_x+p_2-1.0)<0.0000000001),
 UNIQUE(league_country,provider_match_id,phase)
);
CREATE TRIGGER IF NOT EXISTS m0_shadow_validate_before_insert
 BEFORE INSERT ON m0_shadow_1x2_forecasts
 BEGIN
 SELECT CASE WHEN
  NOT EXISTS(SELECT 1 FROM feature_snapshots fs
     JOIN fixtures f ON f.fixture_id=fs.fixture_id
     JOIN m0_forward_feature_records mr ON mr.feature_snapshot_id=fs.feature_snapshot_id
     WHERE fs.feature_snapshot_id=NEW.feature_snapshot_id
       AND fs.fixture_id=NEW.fixture_id AND fs.model_version_id=NEW.model_version_id
       AND fs.feature_hash=NEW.feature_sha256
       AND mr.provider_match_id=NEW.provider_match_id
       AND mr.league_country=NEW.league_country
       AND mr.signed_source_chain_sha256=NEW.source_chain_sha256
       AND fs.observed_cutoff_utc=NEW.feature_cutoff_utc
       AND f.kickoff_utc=NEW.kickoff_utc
       AND fs.availability_class='NOT_VERIFIED'
       AND mr.eligible_for_original_M1=0)
  OR julianday(NEW.generated_at_utc) IS NULL
  OR julianday(NEW.feature_cutoff_utc) IS NULL
  OR julianday(NEW.kickoff_utc) IS NULL
  OR julianday(NEW.generated_at_utc)<julianday(NEW.feature_cutoff_utc)
  OR julianday(NEW.generated_at_utc)>=julianday(NEW.kickoff_utc)-90.0/1440.0
  OR julianday('now')>=julianday(NEW.kickoff_utc)-90.0/1440.0
  OR julianday(NEW.generated_at_utc)>julianday('now')+3.0/86400.0
  THEN RAISE(ABORT,'M0_SHADOW_PREMATCH_FORECAST_CUTOFF_VIOLATION')
  END;
 END;
CREATE TRIGGER IF NOT EXISTS m0_shadow_no_update BEFORE UPDATE ON m0_shadow_1x2_forecasts
 BEGIN SELECT RAISE(ABORT,'M0_SHADOW_FORECAST_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_shadow_no_delete BEFORE DELETE ON m0_shadow_1x2_forecasts
 BEGIN SELECT RAISE(ABORT,'M0_SHADOW_FORECAST_IMMUTABLE'); END;
