-- 002: append-only observed-at features for the 3-league M0 SHADOW pilot.
-- Not original M1 PIT admission: source first publication times UNKNOWN.
CREATE TABLE IF NOT EXISTS m0_forward_feature_records (
  record_id TEXT PRIMARY KEY,
  feature_snapshot_id TEXT NOT NULL UNIQUE REFERENCES feature_snapshots(feature_snapshot_id),
  league_country TEXT NOT NULL CHECK(league_country IN ('ESP','ITA','GER')),
  provider_match_id TEXT NOT NULL,
  provider_home_team_id TEXT NOT NULL,
  provider_away_team_id TEXT NOT NULL,
  snapshot_day_utc TEXT NOT NULL,
  kickoff_original_utc TEXT NOT NULL,
  captured_before_kickoff_utc TEXT NOT NULL,
  signed_source_chain_sha256 TEXT NOT NULL,
  source_ciphertext_sha256 TEXT NOT NULL,
  feature_payload_json TEXT NOT NULL,
  numeric_fields INTEGER NOT NULL CHECK(numeric_fields=121),
  missing_flag_fields INTEGER NOT NULL CHECK(missing_flag_fields=38),
  source_xg_count INTEGER NOT NULL CHECK(source_xg_count >= 0),
  eligible_for_original_M1 INTEGER NOT NULL DEFAULT 0 CHECK(eligible_for_original_M1=0),
  -- Every daily snapshot is immutable. Multiple days can observe same fixture.
  UNIQUE(league_country,provider_match_id,snapshot_day_utc)
);
CREATE TRIGGER IF NOT EXISTS m0_freeze_no_update BEFORE UPDATE ON m0_forward_feature_records
 BEGIN SELECT RAISE(ABORT,'M0_FEATURE_FREEZE_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_freeze_no_delete BEFORE DELETE ON m0_forward_feature_records
 BEGIN SELECT RAISE(ABORT,'M0_FEATURE_FREEZE_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_snapshots_no_update BEFORE UPDATE ON feature_snapshots
 BEGIN SELECT RAISE(ABORT,'M0_FEATURE_SNAPSHOT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_snapshots_no_delete BEFORE DELETE ON feature_snapshots
 BEGIN SELECT RAISE(ABORT,'M0_FEATURE_SNAPSHOT_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS m0_forward_sources (
  source_id TEXT PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
  country TEXT NOT NULL CHECK(country IN ('ESP','ITA','GER')),
  season TEXT NOT NULL,
  actual_completed_utc TEXT NOT NULL,
  network_response_sha256 TEXT NOT NULL,
  raw_provider_first_published_at_utc TEXT
);
CREATE TRIGGER IF NOT EXISTS m0_source_no_update BEFORE UPDATE ON m0_forward_sources
 BEGIN SELECT RAISE(ABORT,'M0_SOURCE_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_source_no_delete BEFORE DELETE ON m0_forward_sources
 BEGIN SELECT RAISE(ABORT,'M0_SOURCE_IMMUTABLE'); END;
