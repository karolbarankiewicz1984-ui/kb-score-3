-- KB Score 3.0: migration 001 / SQLite >= 3.35
-- Schema for historical data, immutable predictions and append-only audit trails.
PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY CHECK(version > 0),
  name TEXT NOT NULL,
  applied_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS providers (
  provider_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  terms_review_status TEXT NOT NULL DEFAULT 'PENDING'
     CHECK(terms_review_status IN ('PENDING','APPROVED','RESTRICTED')),
  created_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS competitions (
  competition_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT,
  type TEXT NOT NULL DEFAULT 'LEAGUE',
  UNIQUE(name, country, type)
);
CREATE TABLE IF NOT EXISTS seasons (
  season_id INTEGER PRIMARY KEY,
  competition_id INTEGER NOT NULL REFERENCES competitions(competition_id),
  start_year INTEGER NOT NULL CHECK(start_year BETWEEN 1900 AND 2200),
  season_label TEXT NOT NULL,
  UNIQUE(competition_id, start_year)
);
CREATE TABLE IF NOT EXISTS teams (
  team_id INTEGER PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  country TEXT
);
CREATE TABLE IF NOT EXISTS team_provider_map (
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  external_team_id TEXT NOT NULL,
  team_id INTEGER NOT NULL REFERENCES teams(team_id),
  valid_from_utc TEXT NOT NULL,
  valid_to_utc TEXT,
  PRIMARY KEY(provider_id, external_team_id, valid_from_utc),
  CHECK(valid_to_utc IS NULL OR valid_to_utc > valid_from_utc)
);
CREATE TABLE IF NOT EXISTS team_aliases (
  alias_id INTEGER PRIMARY KEY,
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  team_id INTEGER NOT NULL REFERENCES teams(team_id),
  alias TEXT NOT NULL,
  valid_from_utc TEXT NOT NULL,
  valid_to_utc TEXT,
  verified_utc TEXT,
  CHECK(valid_to_utc IS NULL OR valid_to_utc > valid_from_utc),
  UNIQUE(provider_id, alias, valid_from_utc)
);
CREATE TABLE IF NOT EXISTS fixtures (
  fixture_id INTEGER PRIMARY KEY,
  season_id INTEGER NOT NULL REFERENCES seasons(season_id),
  home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
  away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
  kickoff_utc TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN (
    'SCHEDULED','LIVE','FINISHED','POSTPONED','ABANDONED','AWARDED','CANCELLED','UNKNOWN'
  )),
  goals_home_90 INTEGER CHECK(goals_home_90 IS NULL OR goals_home_90 >= 0),
  goals_away_90 INTEGER CHECK(goals_away_90 IS NULL OR goals_away_90 >= 0),
  result_source TEXT,
  created_utc TEXT NOT NULL,
  updated_utc TEXT NOT NULL,
  CHECK(home_team_id <> away_team_id),
  UNIQUE(season_id, home_team_id, away_team_id, kickoff_utc)
);
CREATE INDEX IF NOT EXISTS idx_fixtures_kickoff ON fixtures(kickoff_utc);
CREATE INDEX IF NOT EXISTS idx_fixtures_season ON fixtures(season_id, status);
CREATE TABLE IF NOT EXISTS fixture_revisions (
  revision_id INTEGER PRIMARY KEY,
  fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
  observed_at_utc TEXT NOT NULL,
  prior_kickoff_utc TEXT,
  new_kickoff_utc TEXT,
  prior_status TEXT,
  new_status TEXT,
  reason TEXT NOT NULL,
  source_provider_id INTEGER REFERENCES providers(provider_id)
);
CREATE TABLE IF NOT EXISTS source_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  endpoint_label TEXT NOT NULL,
  captured_at_utc TEXT NOT NULL,
  published_at_utc TEXT,
  source_data_hash TEXT NOT NULL,
  availability_class TEXT NOT NULL CHECK(availability_class IN (
    'VERIFIED_PREMATCH','RETROSPECTIVE','NOT_VERIFIED'
  )),
  provider_terms_version TEXT
);
-- No unsafe auto-promotion of REVIEW entries from step 07:
CREATE TABLE IF NOT EXISTS fixture_provider_map (
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  provider_fixture_id TEXT NOT NULL,
  fixture_id INTEGER REFERENCES fixtures(fixture_id),
  match_quality TEXT NOT NULL CHECK(match_quality IN ('STRICT','REVIEW','UNMATCHED')),
  review_status TEXT NOT NULL CHECK(review_status IN ('APPROVED','PENDING','REJECTED')),
  source_snapshot_id TEXT REFERENCES source_snapshots(snapshot_id),
  kickoff_utc TEXT,
  reviewed_at_utc TEXT,
  reviewer_ref TEXT,
  notes TEXT,
  PRIMARY KEY(provider_id, provider_fixture_id),
  CHECK(
    (match_quality = 'STRICT' AND review_status = 'APPROVED' AND fixture_id IS NOT NULL)
    OR
    (match_quality <> 'STRICT' AND fixture_id IS NULL AND review_status IN ('PENDING','REJECTED'))
  )
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_map_fixture_provider_approved
  ON fixture_provider_map(provider_id, fixture_id)
  WHERE match_quality='STRICT' AND review_status='APPROVED';
CREATE INDEX IF NOT EXISTS idx_map_review_queue
  ON fixture_provider_map(review_status, match_quality);
CREATE TABLE IF NOT EXISTS match_stat_observations (
  stat_id INTEGER PRIMARY KEY,
  fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
  team_id INTEGER NOT NULL REFERENCES teams(team_id),
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  snapshot_id TEXT NOT NULL REFERENCES source_snapshots(snapshot_id),
  metric TEXT NOT NULL,
  numeric_value REAL,
  unit TEXT,
  missing_reason TEXT,
  observed_at_utc TEXT NOT NULL,
  CHECK((numeric_value IS NOT NULL AND missing_reason IS NULL)
    OR (numeric_value IS NULL AND missing_reason IS NOT NULL)),
  UNIQUE(fixture_id, team_id, provider_id, snapshot_id, metric)
);
CREATE TABLE IF NOT EXISTS match_events (
  event_id INTEGER PRIMARY KEY,
  fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  snapshot_id TEXT NOT NULL REFERENCES source_snapshots(snapshot_id),
  provider_event_id TEXT,
  minute INTEGER CHECK(minute IS NULL OR minute >= 0),
  event_type TEXT NOT NULL,
  team_id INTEGER REFERENCES teams(team_id),
  details_hash TEXT,
  UNIQUE(provider_id, fixture_id, provider_event_id)
);
CREATE TABLE IF NOT EXISTS odds_snapshots (
  odds_id INTEGER PRIMARY KEY,
  fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
  provider_id INTEGER NOT NULL REFERENCES providers(provider_id),
  bookmaker TEXT NOT NULL,
  market TEXT NOT NULL,
  selection TEXT NOT NULL,
  line TEXT NOT NULL DEFAULT 'NONE',
  decimal_odds REAL NOT NULL CHECK(decimal_odds > 1.0),
  captured_at_utc TEXT NOT NULL,
  source_published_at_utc TEXT,
  snapshot_id TEXT REFERENCES source_snapshots(snapshot_id),
  UNIQUE(fixture_id, provider_id, bookmaker, market, selection, line, captured_at_utc)
);
CREATE INDEX IF NOT EXISTS idx_odds_exact_market ON odds_snapshots(fixture_id, market, selection, line);
CREATE TABLE IF NOT EXISTS model_versions (
  model_version_id TEXT PRIMARY KEY,
  family TEXT NOT NULL,
  code_sha TEXT NOT NULL,
  training_hash TEXT,
  created_at_utc TEXT NOT NULL,
  approval_status TEXT NOT NULL DEFAULT 'EXPERIMENT'
    CHECK(approval_status IN ('EXPERIMENT','CHALLENGER','CHAMPION','RETIRED'))
);
CREATE TABLE IF NOT EXISTS training_runs (
  run_id TEXT PRIMARY KEY,
  model_version_id TEXT NOT NULL REFERENCES model_versions(model_version_id),
  started_at_utc TEXT NOT NULL,
  finished_at_utc TEXT,
  data_hash TEXT NOT NULL,
  split_hash TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  outcome TEXT CHECK(outcome IN ('RUNNING','PASS','FAIL'))
);
CREATE TABLE IF NOT EXISTS feature_snapshots (
  feature_snapshot_id TEXT PRIMARY KEY,
  fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
  model_version_id TEXT NOT NULL REFERENCES model_versions(model_version_id),
  observed_cutoff_utc TEXT NOT NULL,
  generated_at_utc TEXT NOT NULL,
  feature_hash TEXT NOT NULL,
  missing_flags_json TEXT NOT NULL DEFAULT '{}',
  availability_class TEXT NOT NULL CHECK(availability_class IN (
    'VERIFIED_PREMATCH','RETROSPECTIVE','NOT_VERIFIED'
  ))
);
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id TEXT PRIMARY KEY,
  fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
  model_version_id TEXT NOT NULL REFERENCES model_versions(model_version_id),
  feature_snapshot_id TEXT NOT NULL REFERENCES feature_snapshots(feature_snapshot_id),
  mode TEXT NOT NULL CHECK(mode IN ('LIVE','HISTORICAL_REPLAY','SHADOW')),
  phase TEXT NOT NULL CHECK(phase IN ('EARLY','FINAL_PREMATCH','BACKTEST')),
  market TEXT NOT NULL,
  selection TEXT NOT NULL,
  line TEXT NOT NULL DEFAULT 'NONE',
  p_raw REAL NOT NULL CHECK(p_raw >= 0 AND p_raw <= 1),
  p_cal REAL CHECK(p_cal IS NULL OR (p_cal >= 0 AND p_cal <= 1)),
  generated_at_utc TEXT NOT NULL,
  freeze_hash TEXT NOT NULL,
  CHECK((mode='HISTORICAL_REPLAY' AND phase='BACKTEST') OR
    (mode IN ('LIVE','SHADOW') AND phase IN ('EARLY','FINAL_PREMATCH')))
);
CREATE INDEX IF NOT EXISTS idx_predictions_event ON predictions(fixture_id, market);
CREATE TABLE IF NOT EXISTS prediction_publications (
  publication_id TEXT PRIMARY KEY,
  prediction_id TEXT NOT NULL UNIQUE REFERENCES predictions(prediction_id),
  published_at_utc TEXT NOT NULL,
  published_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settlements (
  settlement_id TEXT PRIMARY KEY,
  prediction_id TEXT NOT NULL REFERENCES predictions(prediction_id),
  outcome TEXT NOT NULL CHECK(outcome IN ('WIN','LOSS','PUSH','VOID')),
  settled_at_utc TEXT NOT NULL,
  source_snapshot_id TEXT REFERENCES source_snapshots(snapshot_id),
  supersedes_settlement_id TEXT REFERENCES settlements(settlement_id),
  reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_settlements_prediction ON settlements(prediction_id, settled_at_utc);
CREATE TABLE IF NOT EXISTS quality_audits (
  audit_id TEXT PRIMARY KEY,
  dataset_version TEXT NOT NULL,
  league TEXT,
  season_start_year INTEGER,
  observed_at_utc TEXT NOT NULL,
  checked_count INTEGER NOT NULL DEFAULT 0 CHECK(checked_count >= 0),
  error_count INTEGER NOT NULL DEFAULT 0 CHECK(error_count >= 0),
  report_sha256 TEXT NOT NULL,
  result TEXT NOT NULL CHECK(result IN ('PASS','WARN','FAIL'))
);
-- No UPDATE/DELETE of a frozen prediction or a published prediction.
CREATE TRIGGER IF NOT EXISTS trg_predictions_immutable_update
  BEFORE UPDATE ON predictions BEGIN SELECT RAISE(ABORT,'PREDICTION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_predictions_immutable_delete
  BEFORE DELETE ON predictions BEGIN SELECT RAISE(ABORT,'PREDICTION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_publications_immutable_update
  BEFORE UPDATE ON prediction_publications BEGIN SELECT RAISE(ABORT,'PUBLICATION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_publications_immutable_delete
  BEFORE DELETE ON prediction_publications BEGIN SELECT RAISE(ABORT,'PUBLICATION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_settlements_immutable_update
  BEFORE UPDATE ON settlements BEGIN SELECT RAISE(ABORT,'SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_settlements_immutable_delete
  BEFORE DELETE ON settlements BEGIN SELECT RAISE(ABORT,'SETTLEMENT_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_revisions_immutable_update
  BEFORE UPDATE ON fixture_revisions BEGIN SELECT RAISE(ABORT,'REVISION_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS trg_revisions_immutable_delete
  BEFORE DELETE ON fixture_revisions BEGIN SELECT RAISE(ABORT,'REVISION_IMMUTABLE'); END;
-- A live prediction must be created AND timestamped before the actual kickoff;
-- historical replays are explicitly labeled and not eligible for live performance claims.
CREATE TRIGGER IF NOT EXISTS trg_prediction_before_kickoff
  BEFORE INSERT ON predictions
  WHEN NEW.mode IN ('LIVE','SHADOW')
  BEGIN
    SELECT CASE WHEN
      (SELECT fixture_id FROM feature_snapshots
          WHERE feature_snapshot_id=NEW.feature_snapshot_id) <> NEW.fixture_id
      OR (SELECT model_version_id FROM feature_snapshots
          WHERE feature_snapshot_id=NEW.feature_snapshot_id) <> NEW.model_version_id
      OR julianday(NEW.generated_at_utc) IS NULL
      OR julianday((SELECT kickoff_utc FROM fixtures WHERE fixture_id=NEW.fixture_id)) IS NULL
      OR julianday(NEW.generated_at_utc) >=
         julianday((SELECT kickoff_utc FROM fixtures WHERE fixture_id=NEW.fixture_id))
      OR julianday('now') >=
         julianday((SELECT kickoff_utc FROM fixtures WHERE fixture_id=NEW.fixture_id))
      OR julianday(NEW.generated_at_utc) > julianday('now')
      OR julianday((SELECT observed_cutoff_utc FROM feature_snapshots
          WHERE feature_snapshot_id=NEW.feature_snapshot_id)) >
         julianday(NEW.generated_at_utc)
      OR (SELECT availability_class FROM feature_snapshots
          WHERE feature_snapshot_id=NEW.feature_snapshot_id) <> 'VERIFIED_PREMATCH'
    THEN RAISE(ABORT,'LIVE_PREDICTION_CUTOFF_VIOLATION') END;
  END;
CREATE TRIGGER IF NOT EXISTS trg_publication_before_kickoff
  BEFORE INSERT ON prediction_publications
  BEGIN
    SELECT CASE WHEN
      (SELECT mode FROM predictions WHERE prediction_id=NEW.prediction_id) <> 'LIVE'
      OR julianday(NEW.published_at_utc) >=
         julianday((SELECT f.kickoff_utc FROM fixtures f
          JOIN predictions p ON p.fixture_id=f.fixture_id
          WHERE p.prediction_id=NEW.prediction_id))
      OR julianday('now') >=
         julianday((SELECT f.kickoff_utc FROM fixtures f
          JOIN predictions p ON p.fixture_id=f.fixture_id
          WHERE p.prediction_id=NEW.prediction_id))
    THEN RAISE(ABORT,'PUBLICATION_CUTOFF_VIOLATION') END;
  END;
INSERT OR IGNORE INTO schema_migrations(version,name,applied_utc)
  VALUES (1,'001_initial_schema',strftime('%Y-%m-%dT%H:%M:%fZ','now'));
COMMIT;
